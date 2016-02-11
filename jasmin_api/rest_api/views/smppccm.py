from django.conf import settings
from django.http import JsonResponse

from rest_framework.viewsets import ViewSet
from rest_api.tools import set_ikeys, split_cols

STANDARD_PROMPT = settings.STANDARD_PROMPT


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

    def list(self, request):
        """List SMPP Client Connectors. No parameters
        Differs from slightly from telent CLI names and values:
        
        1. the "service" column is called "status"
        2. the cid is the full connector id of the form smpps(cid)
        """
        telnet = request.telnet
        telnet.sendline('smppccm -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip().replace("\r", '').split("\n")
        if len(result) < 3:
            return JsonResponse({'connectors': []})
        results = result[2:-2]
        connector_list = split_cols(results)
        connectors = []
        for raw_data in connector_list:
            if raw_data[0][0] == '#':
                cid = raw_data[0][1:]
                connector = self.get_smppccm(telnet, cid, True)
                connector.update(
                    cid = "smpps(%s)" % cid,
                    status = raw_data[1],
                    session = raw_data[2],
                    starts = raw_data[3],
                    stops = raw_data[4]
                )
                connectors.append(connector)
        return JsonResponse({'connectors': connectors})

    def create(request):
        """Create an SMPP Client Connector.
        Required parameter: cid (connector id)

        """

