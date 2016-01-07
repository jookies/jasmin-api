import pexpect

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
            telnet = pexpect.spawn(
                "telnet %s %s" %
                (settings.TELNET_HOST, settings.TELNET_PORT),
                timeout=settings.TELNET_TIMEOUT,
            )
            telnet.expect_exact('Username: ')
            telnet.sendline(settings.TELNET_USERNAME)
            telnet.expect_exact('Password: ')
            telnet.sendline(settings.TELNET_PW)
        except pexpect.EOF:
            return error_response('Unexpected response from Jasmin')
        except pexpect.TIMEOUT:
            return error_response('Connection to Jasmin timed out')
        try:
            telnet.expect_exact(settings.STANDARD_PROMPT)
        except pexpect.EOF:
            return error_response('Jasmin login failed')
        request.telnet = telnet
        return None

    def process_response(self, request, response):
        if hasattr(request, 'telnet'):
            try:
                request.telnet.sendline('quit')
            except pexpect.ExceptionPexpect:
                request.telnet.kill(9)
        return response
