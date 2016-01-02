import pexpect

from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


STANDARD_PROMPT = settings.STANDARD_PROMPT


class TestView(APIView):
    def get(self, request, format=None):
        return Response({'result': 'ok'})


class GroupViewSet(ViewSet):
    """ViewSet for managing *Jasmin* Groups (*not* Django auth groups)"""
    def list(self, request):
        telnet = request.telnet
        telnet.sendline('group -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip().replace("\r", '').split("\n")
        print result
        if len(result) < 3:
            return Response({'groups': []})
        groups = result[2:-2]
        print groups
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
