import pexpect

from django.conf import settings
from django.http import HttpResponseBadRequest, Http404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import detail_route, list_route


STANDARD_PROMPT = settings.STANDARD_PROMPT
INTERACTIVE_PROMPT = settings.INTERACTIVE_PROMPT


class TestView(APIView):
    def get(self, request, format=None):
        return Response({'result': 'ok'})


class GroupViewSet(ViewSet):
    """ViewSet for managing *Jasmin* user groups (*not* Django auth groups)"""
    lookup_field = 'gid'

    def list(self, request):
        """
        List groups. No request parameters provided or required.
        """
        telnet = request.telnet
        telnet.sendline('group -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip().replace("\r", '').split("\n")
        if len(result) < 3:
            return Response({'groups': []})
        groups = result[2:-2]
        return Response(
            {
                'groups':
                    [
                        {
                            'name': g.strip().lstrip('!#'), 'status': (
                                'disabled' if g[1] == '!' else 'active'
                            )
                        } for g in groups
                    ]
            }
        )

    def create(self, request):
        """Create a group.
        One POST parameter required, the group identifier (a string)
        ---
        # YAML
        omit_serializer: true
        parameters:
        - name: gid
          description: Group identifier
          required: true
          type: string
          paramType: form
        """
        telnet = request.telnet
        telnet.sendline('group -a')
        telnet.expect(r'Adding a new Group(.+)\n' + INTERACTIVE_PROMPT)
        if not 'gid' in request.POST:
            return HttpResponseBadRequest('Missing gid (group identifier)')
        telnet.sendline('gid ' + request.POST['gid'] + '\n')
        telnet.expect(INTERACTIVE_PROMPT)
        telnet.sendline('ok\n')
        matched_index = telnet.expect([
            r'.+Successfully added(.+)\[(.+)\][\n\r]+' + STANDARD_PROMPT,
            r'.+Error: (.+)[\n\r]+' + INTERACTIVE_PROMPT,
            r'.+(.*)(' + INTERACTIVE_PROMPT + '|' + STANDARD_PROMPT + ')',
        ])
        if matched_index == 0:
            gid = telnet.match.group(2).strip()
            telnet.sendline('persist\n')
            return Response({'name': gid})
        else:
            return HttpResponseBadRequest(telnet.match.group(1))

    def simple_group_action(self, telnet, action, gid):
        telnet.sendline('group -%s %s' % (action, gid))
        matched_index = telnet.expect([
            r'.+Successfully(.+)' + STANDARD_PROMPT,
            r'.+Unknown Group: (.+)' + STANDARD_PROMPT,
            r'.+(.*)' + STANDARD_PROMPT,
        ])
        if matched_index == 0:
            telnet.sendline('persist\n')
            return Response ({'name': gid})
        elif matched_index == 1:
            raise Http404()
        else:
            return HttpResponseBadRequest(telnet.match.group(1))

    def destroy(self, request, gid):
        """Delete a group.
        One POST parameter required, the group identifier (a string)
        HTTP codes indicate result as follows
        200: successful deletion
        404: nonexistent group
        400: other error
        """
        return self.simple_group_action(request.telnet, 'r', gid)

    @detail_route(methods=['patch'])
    def enable(self, request, gid):
        """Enable a group.
        One POST parameter required, the group identifier (a string)
        HTTP codes indicate result as follows
        200: successful enabled, or already enabled
        404: nonexistent group
        400: other error
        """
        return self.simple_group_action(request.telnet, 'e', gid)


    @detail_route(methods=['patch'])
    def disable(self, request, gid):
        """Disable a group.
        One POST parameter required, the group identifier (a string)
        HTTP codes indicate result as follows
        200: successful disable, or already disabled
        404: nonexistent group
        400: other error
        """
        return self.simple_group_action(request.telnet, 'd', gid)
