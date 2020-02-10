import json
import os

METALCTL_BIN = os.environ.get("METALCTL_BIN", "metalctl")

AUTH_SPEC = dict(
    api_url=dict(type='str', required=False),
    api_hmac=dict(type='str', required=False),
)


def exec_metalctl(module, args):
    environ_update = dict()
    url = module.params.get("api_url")
    if url:
        environ_update["METALCTL_URL"] = url
    hmac = module.params.get("api_hmac")
    if hmac:
        environ_update["METALCTL_HMAC"] = hmac

    cmd = [METALCTL_BIN, "-o", "json"] + args
    _, out, err = module.run_command(cmd, check_rc=True, environ_update=environ_update)

    if err:
        module.fail_json(cmd=cmd, msg=err)
        return

    result = json.loads(out)

    return result
