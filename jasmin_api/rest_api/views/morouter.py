from django.conf import settings
from django.http import JsonResponse

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import list_route

from rest_api.tools import set_ikeys, split_cols
from rest_api.exceptions import (JasminSyntaxError, JasminError,
                        UnknownError, MissingKeyError,
                        ObjectNotFoundError)

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
        routers = split_cols(results)
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

    def create(self, request):
        """Create MORouter.
        Required parameters: type, order, connectors,
        ---
        # YAML
        omit_serializer: true
        parameters:
        - name: type
          description: One of DefaultRoute, StaticMORoute, RandomRoundrobinMORoute
          required: true
          type: string
          paramType: form
        - name: order
          description: Router order, also used to identify router
          required: true
          type: string
          paramType: form
        - name: connectors
          description: List of connector identifiers. More than one only for RandomRoundrobinMORoute
          required: true
          type: string
          paramType: form
        - name: filters
          description: List of filters, required except for DefaultRoute
          required: false
          type: string
          paramType: form
        """
        telnet = request.telnet
        data = request.data
        try:
            rtype, connectors, order = \
                data['rtype'], data['connectors'], data['order']
        except IndexError:
            raise MissingKeyError('Missing parameter: type, order or connectors required')
        if rtype.lower() != 'defaultroute':
            try:
                filters = data['filters']
            except IndexError:
                raise MissingKeyError('%s router requires filters' % rtype)
        telnet.sendline('morouter -a')
        telnet.expect(r'Adding a new MO Route(.+)\n' + INTERACTIVE_PROMPT)
        ikeys = {
            'type': rtype, 'order': order, 
        }
        if rtype.lower() != 'defaultroute':
            raise NotImplementedError('Only default root works for now')
        set_ikeys(telnet, ikeys)
        telnet.sendline('persist\n')
        telnet.expect(r'.*' + STANDARD_PROMPT)
        telnet.expect(r'.*' + STANDARD_PROMPT)
        return JsonResponse({'user': self.get_user(telnet, uid)})
