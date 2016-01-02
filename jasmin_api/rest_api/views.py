from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class TestView(APIView):
    def get(self, request, format=None):
        return Response({'result': 'ok'})


STANDARD_PROMPT = 'jcli : '


class GroupViewSet(ViewSet):
    """ViewSet for managing *Jasmin* Groups (*not* Django auth groups)"""
    def list(self, request):
        telnet = request.telnet
        telnet.read_until(STANDARD_PROMPT)
        telnet.write('group -1')
        i, match, t = telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = match.group(0).split()
        if len(result) < 3:
            return Response({'groups': []})
        groups = result[1:-1]
        return Response(
            {
                'groups':
                    [
                        {
                            'name': g.lstrip('!#'), 'status': (
                                'disabled' if g[1] == '!' else 'active'
                            )
                        } for g in groups
                    ]
            }
        )
