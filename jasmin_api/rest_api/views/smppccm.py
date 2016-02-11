from django.conf import settings
from django.http import JsonResponse

from rest_framework.viewsets import ViewSet
from rest_api.tools import set_ikeys, split_cols
from rest_api.exceptions import (
    JasminSyntaxError, ActionFailed, ObjectNotFoundError
)

STANDARD_PROMPT = settings.STANDARD_PROMPT
INTERACTIVE_PROMPT = settings.INTERACTIVE_PROMPT


class SMPPCCMViewSet(ViewSet):
    "Viewset for managing SMPP Client Connectors"
    lookup_field = 'cid'

    def get_smppccm(self, telnet, cid, silent=False):
        #Some of this could be abstracted out - similar pattern in users.py
        telnet.sendline('smppccm -s ' + cid)
        matched_index = telnet.expect([
                r'.+Unknown connector:.*' + STANDARD_PROMPT,
                r'.+Usage:.*' + STANDARD_PROMPT,
                r'(.+)\n' + STANDARD_PROMPT,
        ])
        if matched_index != 2:
            if silent:
                return
            else:
                raise ObjectNotFoundError('Unknown connector: %s' % cid)
        result = telnet.match.group(1)
        smppccm = {}
        for line in result.splitlines():
            d = [x for x in line.split() if x]
            if len(d) == 2:
                smppccm[d[0]] = d[1]
        return smppccm

    def get_connector_list(self, telnet):
        telnet.sendline('smppccm -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip().replace("\r", '').split("\n")
        if len(result) < 3:
            return []
        return split_cols(result[2:-2])

    def simple_smppccm_action(self, telnet, action, cid):
        telnet.sendline('smppccm -%s %s' % (action, cid))
        matched_index = telnet.expect([
            r'.+Successfully(.+)' + STANDARD_PROMPT,
            r'.+Unknown connector: (.+)' + STANDARD_PROMPT,
            r'.+(.*)' + STANDARD_PROMPT,
        ])
        if matched_index == 0:
            print 'persisting'
            telnet.sendline('persist\n')
            return JsonResponse({'name': cid})
        elif matched_index == 1:
            print 'not found'
            raise ObjectNotFoundError('Unknown SMPP Connector: %s' % cid)
        else:
            print 'other failure'
            print telnet.match.group(0)
            raise ActionFailed(telnet.match.group(1))

    def list(self, request):
        """List SMPP Client Connectors. No parameters
        Differs from slightly from telent CLI names and values:

        1. the "service" column is called "status"
        2. the cid is the full connector id of the form smpps(cid)
        """
        telnet = request.telnet
        connector_list = self.get_connector_list(telnet)
        connectors = []
        for raw_data in connector_list:
            if raw_data[0][0] == '#':
                cid = raw_data[0][1:]
                connector = self.get_smppccm(telnet, cid, True)
                connector.update(
                    cid=cid,
                    status=raw_data[1],
                    session=raw_data[2],
                    starts=raw_data[3],
                    stops=raw_data[4]
                )
                connectors.append(connector)
        return JsonResponse({'connectors': connectors})

    def retrieve(self, request, cid):
        """Retreive data for one connector
        Required parameter: cid (connector id)"""
        telnet = request.telnet
        connector = self.get_smppccm(telnet, cid, silent=False)
        connector_list = self.get_connector_list(telnet)
        list_data = next(
            (raw_data for raw_data in connector_list if
                raw_data[0] == '#' + cid),
            None
        )
        connector.update(
            cid=cid,
            status=list_data[1],
            session=list_data[2],
            starts=list_data[3],
            stops=list_data[4]
        )
        return JsonResponse({'connector': connector})

    def create(self, request):
        """Create an SMPP Client Connector.
        Required parameter: cid (connector id)
        ---
        # YAML
        omit_serializer: true
        parameters:
        - name: cid
          description: Connector identifier
          required: true
          type: string
          paramType: form
        """
        telnet = request.telnet
        telnet.sendline('smppccm -a')
        telnet.sendline('cid ' + request.data['cid'] + '\n')
        telnet.expect(INTERACTIVE_PROMPT)
        telnet.sendline('ok\n')
        matched_index = telnet.expect([
            r'.+Successfully added(.+)\[(.+)\][\n\r]+' + STANDARD_PROMPT,
            r'.+(Failed .+)[\n\r]+' + INTERACTIVE_PROMPT + '(.*)',
            r'.+(.*)(' + INTERACTIVE_PROMPT + '|' + STANDARD_PROMPT + ')',
        ])
        if matched_index == 0:
            cid = telnet.match.group(2).strip()
            telnet.sendline('persist\n')
            return JsonResponse({'cid': cid})
        else:
            raise ActionFailed(telnet.match.group(1))

    def destroy(self, request, cid):
        """Delete an smpp connector.
        One parameter required, the connector identifier

        HTTP codes indicate result as follows

        - 200: successful deletion
        - 404: nonexistent group
        - 400: other error
        """
        return self.simple_smppccm_action(request.telnet, 'r', cid)
