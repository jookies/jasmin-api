import telnetlib
from socket import error as socket_error

from django.conf import settings
from django.http import JsonResponse


def error_response(msg):
    resp = JsonResponse({'detail': msg})
    resp.status = 500
    #resp.reason = msg
    return resp


class TelnetConnectionMiddleware(object):
    def process_request(self, request):
        """
        Add a telnet connection to all request paths that start with /api/
        assuming we only need to connect for these means we avoid unecessary
        overhead on any other functionality we add, and keeps URL path clear
        for it.
        """
        if not request.path.startswith('/api/'):
            return None
        try:
            telnet = telnetlib.Telnet(
                settings.TELNET_HOST,
                settings.TELNET_PORT,
                 timeout = 1
            )
        except socket_error:
            return error_response('Could not connect to Jasmin')
        try:
            telnet.read_until('Username: ')
            telnet.write(settings.TELNET_USERNAME + '\n')
            telnet.read_until('Password: ')
            telnet.write(settings.TELNET_PW + '\n')
        except (EOFError, socket_error):
            return error_response('Unexpected response from Jasmin')
        request.telnet = telnet
        print 'ADDED'
        return None

    def process_response(self, request, response):
        if hasattr(request, 'telnet'):
            request.telnet.close()
        return response
