import pexpect

from django.conf import settings
from django.http import HttpResponseBadRequest, Http404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.parsers import JSONParser
from rest_framework.decorators import detail_route, list_route, parser_classes
from rest_framework.exceptions import NotFound, APIException


STANDARD_PROMPT = settings.STANDARD_PROMPT
INTERACTIVE_PROMPT = settings.INTERACTIVE_PROMPT


class TestView(APIView):
    def get(self, request, format=None):
        return Response({'result': 'ok'})


class CanNotModifyError(APIException):
    status_code = 400
    default_detail = 'Can not modify a key'

class JasminSyntaxError(APIException):
    status_code = 400
    default_detail = 'Can not modify a key'

class JasminError(APIException):
    status_code = 400
    default_detail = 'Jasmin error'

class UnknownError(APIException):
    status_code = 404
    default_detail = 'object not known'


def set_ikeys(telnet, keys2vals):
    """set multiple keys for interactive command"""
    for key, val in keys2vals.items():
        telnet.sendline("%s %s" % (key, val))
        matched_index = telnet.expect([
            r'.*(Unknown .*)' + INTERACTIVE_PROMPT,
            r'(.*) can not be modified.*' + INTERACTIVE_PROMPT,
            r'(.*)' + INTERACTIVE_PROMPT
        ])
        result = telnet.match.group(1).strip()
        if matched_index == 0:
            raise UnknownError(detail=result)
        if matched_index == 1:
            raise CanNotModifyError(detail=result)
    telnet.sendline('ok')
    ok_index = telnet.expect([
        r'ok(.* syntax is invalid).*' + INTERACTIVE_PROMPT,
        r'.*' + STANDARD_PROMPT,
    ])
    if ok_index == 0:
        #remove whitespace and return error
        raise JasminSyntaxError(" ".join(telnet.match.group(1).split()))
    return


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
                                'disabled' if g[1] == '!' else 'enabled'
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
        if not 'gid' in request.data:
            return HttpResponseBadRequest('Missing gid (group identifier)')
        telnet.sendline('gid ' + request.data['gid'] + '\n')
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
        """Delete a group. One parameter required, the group identifier (a string)
        
        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent group
        - 400: other error
        """
        return self.simple_group_action(request.telnet, 'r', gid)

    @detail_route(methods=['patch'])
    def enable(self, request, gid):
        """Enable a group. One parameter required, the group identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent group
        - 400: other error
        """
        return self.simple_group_action(request.telnet, 'e', gid)


    @detail_route(methods=['patch'])
    def disable(self, request, gid):
        """Disable a group.
        
        One parameter required, the group identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent group
        - 400: other error
        """
        return self.simple_group_action(request.telnet, 'd', gid)


class UserViewSet(ViewSet):
    """ViewSet for managing *Jasmin* users (*not* Django auth users)"""
    lookup_field = 'uid'

    def get_user(self, telnet, uid, silent=False):
        """gets a single users data
        silent supresses Http404 exception if user not found"""
        telnet.sendline('user -s ' + uid)
        matched_index = telnet.expect([
                r'.+Unknown User:.*' + STANDARD_PROMPT,
                r'.+Usage: user.*' + STANDARD_PROMPT,
                r'(.+)\n' + STANDARD_PROMPT,
        ])
        if matched_index != 2:
            if silent:
                return
            else:
                raise Http404()
        result = telnet.match.group(1)
        user = {}
        for line in [l for l in result.splitlines() if l][1:]:
            d = [x for x in line.split() if x]
            if len(d) == 2:
                user[d[0]] = d[1]
            elif len(d) == 4:
                #Not DRY, could be more elegant
                if not d[0] in user:
                    user[d[0]] = {}
                if not d[1] in user[d[0]]:
                    user[d[0]][d[1]] = {}
                if not d[2] in user[d[0]][d[1]]:
                    user[d[0]][d[1]][d[2]] = {}
                user[d[0]][d[1]][d[2]] = d[3]
            #each line has two or four lines so above exhaustive
        return user

    def retrieve(self, request, uid):
        """Retrieve data for one user"""
        return Response({'user': self.get_user(request.telnet, uid)})

    def list(self, request):
        """List users. No parameters"""
        telnet = request.telnet
        telnet.sendline('user -l')
        telnet.expect([r'(.+)\n' + STANDARD_PROMPT])
        result = telnet.match.group(0).strip()
        if len(result) < 3:
            return Response({'users': []})
        #user_text = result[2:-2]
        results = [l for l in result.splitlines() if l]
        annotated_uids = [u.split(None, 1)[0][1:] for u in results[2:-2]]
        users = []
        for auid in annotated_uids:
            if auid[0] == '!':
                udata = self.get_user(telnet, auid[1:], True)
                udata['status'] = 'disabled'
            else:
                udata = self.get_user(telnet, auid, True)
                udata['status'] = 'enabled'
            users.append(udata)
        return Response(
            {
                #return users skipping None (== nonexistent user)
                'users': [u for u in users if u]
            }
        )

    def create(self, request):
        """Create a User.
        Required parameters: username, password, uid (user identifier), gid (group identifier), 
        ---
        # YAML
        omit_serializer: true
        parameters:
        - name: uid
          description: Username identifier
          required: true
          type: string
          paramType: form
        - name: gid
          description: Group identifier
          required: true
          type: string
          paramType: form
        - name: username
          description: Username
          required: true
          type: string
          paramType: form
        - name: password
          description: Password
          required: true
          type: string
          paramType: form
        """
        telnet = request.telnet
        data = request.data
        try:
            uid, gid, username, password = \
                data['uid'], data['gid'], data['username'], data['password']
        except IndexError:
            return HttpResponseBadRequest(
                'Missing parameter: uid, gid, username and password required')
        telnet.sendline('user -a')
        telnet.expect(r'Adding a new User(.+)\n' + INTERACTIVE_PROMPT)
        set_ikeys(
            telnet,
            {
                'uid': uid, 'gid': gid, 'username': username,
                'password': password
            }
        )
        telnet.sendline('persist\n')
        telnet.expect(r'.*' + STANDARD_PROMPT)
        telnet.expect(r'.*' + STANDARD_PROMPT)
        return Response({'user': self.get_user(telnet, uid)})

    @parser_classes((JSONParser,))
    def partial_update(self, request, uid):
        """Update some user attributes

        JSON requests only. The updates parameter is a list of lists.
        Each list is a list of valid arguments to user update. For example:

        * ["gid", "mygroup"] will set the user's group to mygroup
        * ["mt_messaging_cred", "authorization", "smpps_send", "False"]
        will remove the user privilege to send SMSs through the SMPP API.
        ---
        # YAML
        omit_serializer: true
        parameters:
        - name: updates
          description: Items to update
          required: true
          type: array
          paramType: body
        """
        telnet = request.telnet
        telnet.sendline('user -u ' + uid)
        matched_index = telnet.expect([
            r'.*Updating User(.*)' + INTERACTIVE_PROMPT,
            r'.*Unknown User: (.*)' + STANDARD_PROMPT,
            r'.+(.*)(' + INTERACTIVE_PROMPT + '|' + STANDARD_PROMPT + ')',
        ])
        if matched_index == 1:
            raise UnknownError(detail='Unknown user:' + uid)
        if matched_index != 0:
            raise JasminError(detail=" ".join(telnet.match.group(0).split()))
        updates = request.data
        if not ((type(updates) is list) and (len(updates) >= 1)):
            raise JasminSyntaxError('updates should be a list')
        for update in updates:
            if not ((type(update) is list) and (len(update) >= 1)):
                raise JasminSyntaxError("Not a list: %s" % update)
            telnet.sendline(" ".join([x for x in update]))
            matched_index = telnet.expect([
                r'.*(Unknown User key:.*)' + INTERACTIVE_PROMPT,
                r'.*(Error:.*)' + STANDARD_PROMPT,
                r'.*' + INTERACTIVE_PROMPT,
                r'.+(.*)(' + INTERACTIVE_PROMPT + '|' + STANDARD_PROMPT + ')',
            ])
            if matched_index != 2:
                raise JasminSyntaxError(
                    detail=" ".join(telnet.match.group(1).split()))
        telnet.sendline('ok')
        ok_index = telnet.expect([
            r'(.*)' + INTERACTIVE_PROMPT,
            r'.*' + STANDARD_PROMPT,
        ])
        if ok_index == 0:
            raise JasminSyntaxError(
                detail=" ".join(telnet.match.group(1).split()))
        telnet.sendline('persist\n')
        #Not sure why this needs to be repeated
        telnet.expect(r'.*' + STANDARD_PROMPT)
        telnet.expect(r'.*' + STANDARD_PROMPT)
        return Response({'user': self.get_user(telnet, uid)})

    def simple_user_action(self, telnet, action, uid, return_user=True):
        telnet.sendline('user -%s %s' % (action, uid))
        matched_index = telnet.expect([
            r'.+Successfully(.+)' + STANDARD_PROMPT,
            r'.+Unknown User: (.+)' + STANDARD_PROMPT,
            r'.+(.*)' + STANDARD_PROMPT,
        ])
        if matched_index == 0:
            telnet.sendline('persist\n')
            if return_user:
                telnet.expect(r'.*' + STANDARD_PROMPT)
                telnet.expect(r'.*' + STANDARD_PROMPT)
                return Response({'user': self.get_user(telnet, uid)})
            else:
                return Response({'uid': uid})
        elif matched_index == 1:
            raise UnknownError(detail='No use:' +  gid)
        else:
            return JasminError(telnet.match.group(1))

    def destroy(self, request, uid):
        """Delete a user. One parameter required, the user identifier (a string)
        
        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent user
        - 400: other error
        """
        return self.simple_user_action(
            request.telnet, 'r', uid, return_user=False)

    @detail_route(methods=['patch'])
    def enable(self, request, uid):
        """Enable a user. One parameter required, the user identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent user
        - 400: other error
        """
        return self.simple_user_action(request.telnet, 'e', uid)

    @detail_route(methods=['patch'])
    def disable(self, request, uid):
        """Disable a user.
        
        One parameter required, the user identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful deletion
        - 404: nonexistent user
        - 400: other error
        """
        return self.simple_user_action(request.telnet, 'd', uid)

    @detail_route(methods=['patch'])
    def smpp_unbind(self, request, uid):
        """Unbind user from smpp server
        
        One parameter required, the user identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful unbind
        - 404: nonexistent user
        - 400: other error
        """
        return self.simple_user_action(request.telnet, '-smpp-unbind', uid)

    @detail_route(methods=['patch'])
    def smpp_ban(self, request, uid):
        """Unbind and ban user from smpp server
        
        One parameter required, the user identifier (a string)

        HTTP codes indicate result as follows
        
        - 200: successful ban and unbind
        - 404: nonexistent user
        - 400: other error
        """
        return self.simple_user_action(request.telnet, '-smpp-ban', uid)
