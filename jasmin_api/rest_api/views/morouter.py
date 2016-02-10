from django.conf import settings
from django.http import JsonResponse

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import list_route

STANDARD_PROMPT = settings.STANDARD_PROMPT


class MORouterViewSet(ViewSet):
    "Viewset for managing MO Routes"
    lookup_field = 'order'

    def list(self, request):
        "List MO routers. No paramaters"
        telnet = request.telnet
        telnet.sendline('morouter -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip().replace("\r", '').split("\n")
        if len(result) < 3:
            return JsonResponse({'morouters': []})
        results = [l for l in result[2:-2] if l]
        routers = []
        for l in results:
            raw_split = l.split()
            fields = [s for s in raw_split if (s and raw_split[0][0] == '#')]
            routers.append(fields)
        return JsonResponse(
            {
                'morouters':
                    [
                        {
                            'order': r[0].strip().lstrip('#'),
                            'type': r[1],
                            'connectors': [c.strip() for c in r[2].split(',')]
                        } for r in routers
                    ]
            }
        )

    @list_route(methods=['delete'])
    def flush(self, request):
        "Flush entire routing table"
        telnet = request.telnet
        telnet.sendline('morouter -f')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        telnet.sendline('persist\n')
        telnet.expect(r'.*' + STANDARD_PROMPT)
        return JsonResponse({'morouters': []})
