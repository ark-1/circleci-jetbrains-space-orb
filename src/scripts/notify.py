import base64
import os
import subprocess
import json
from typing import Optional, List


def substitute_envs(s: str) -> str:
    import re
    return re.sub('\\${([\\w]+)}|\\$([\\w]+)', lambda match: os.getenv(match.group(1) or match.group(2)), s)


def build_message_body(custom: Optional[str], template: Optional[str]) -> str:
    if custom is not None:
        t2 = substitute_envs(custom)
    elif template is not None:
        template_value = os.getenv(template)
        if template_value is None or template_value == '':
            raise ValueError("No such template:", template)
        t2 = substitute_envs(template_value)
    else:
        raise ValueError("Error: No message template selected. "
                         "Select either a custom template "
                         "or one of the pre-included ones via the 'custom' or 'template' parameters.")
    print('Message body:')
    print(t2)
    return t2


def post_to_jb_space(msg: str, channels: List[str], members: List[str], client_id: bytes, client_secret: bytes,
                     space_url: str):
    if len(channels) == 0 and len(members) == 0:
        print('No channel was provided. Enter value for JB_SPACE_DEFAULT_CHANNEL env var, '
              '$JB_SPACE_DEFAULT_RECIPIENT_MEMBER env var, channel parameter, or recipient_member parameter')
        return

    auth_response = subprocess.check_output(
        'curl -s -f -X POST -H "Authorization: Basic ' +
        base64.b64encode(client_id + b':' + client_secret).decode('UTF-8') +
        '" -d "grant_type=client_credentials&scope=**" ' + space_url + '/oauth/token',
        shell=True, universal_newlines=True
    )
    token: Optional[str] = json.loads(auth_response)['access_token']
    if token is None:
        print("Cannot authenticate into JetBrains Space: ")
        return

    msg_loaded = json.loads(msg)

    def send_msg(recipient):
        body = json.dumps({'recipient': recipient, 'content': msg_loaded})
        subprocess.check_output(
            'curl -s -f -X POST -H "Authorization: Bearer ' + token + '" -d \'' + body.replace("'", "'\\''") +
            "' " + space_url + '/api/http/chats/messages/send-message',
            shell=True, universal_newlines=True
        )

    for i in channels:
        channel = substitute_envs(i)
        print('Sending to channel:', channel)
        send_msg({
            'className': 'MessageRecipient.Channel',
            'channel': {
                'className': 'ChatChannel.FromName',
                'name': channel
            }
        })

    for i in members:
        member = substitute_envs(i)
        print('Sending to member:', member)
        send_msg({
            'className': 'MessageRecipient.Member',
            'member': 'username:' + member
        })


def notify(custom: Optional[str], template: Optional[str], channels: List[str], members: List[str],
           client_id: bytes, client_secret: bytes, space_url: str, event: str,
           current_branch: str, branch_patterns: List[str]):
    with open('/tmp/JB_SPACE_JOB_STATUS', 'rt') as f:
        status = f.readline().strip()
    if status == event or event == "always":
        if not branch_filter(current_branch, branch_patterns):
            print("NO JB SPACE ALERT")
            print('Current branch does not match any item from the "branch_pattern" parameter')
            print('Current branch:', current_branch)
        else:
            print('Sending notification')
            post_to_jb_space(build_message_body(custom, template), channels, members,
                             client_id, client_secret, space_url)
    else:
        print("NO JB SPACE ALERT")
        print()
        print("This command is set to send an alert on:", event)
        print("Current status:", status)


def branch_filter(current_branch: str, branch_patterns: List[str]) -> bool:
    import re
    for i in branch_patterns:
        if re.fullmatch(i.strip(), current_branch):
            return True
    return False


def if_not_empty(s: Optional[str]) -> Optional[str]: return None if s is None or s == '' else s


def remove_prefixes(s: str, prefixes: List[str]) -> str:
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


if __name__ == '__main__':
    notify(
        custom=if_not_empty(os.getenv("JB_SPACE_PARAM_CUSTOM")),
        template=if_not_empty(os.getenv("JB_SPACE_PARAM_TEMPLATE")),
        channels=[i for i in (os.getenv("JB_SPACE_PARAM_CHANNEL") or '').split(',') if i != ''],
        members=[i for i in (os.getenv("JB_SPACE_PARAM_RECIPIENT_MEMBER") or '').split(',') if i != ''],
        client_id=bytes(os.getenv("JB_SPACE_CLIENT_ID"), 'UTF-8'),
        client_secret=bytes(os.getenv("JB_SPACE_CLIENT_SECRET"), 'UTF-8'),
        space_url='https://' + remove_prefixes(os.getenv("JB_SPACE_URL"), prefixes=['https://', 'http://']),
        event=os.getenv("JB_SPACE_PARAM_EVENT"),
        current_branch=os.getenv("CIRCLE_BRANCH"),
        branch_patterns=os.getenv("JB_SPACE_PARAM_BRANCH_PATTERN").split(',')
    )
