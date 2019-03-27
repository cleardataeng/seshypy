import sys

from seshypy.version import VERSION


__version__ = VERSION

_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    import urllib
    urllib.quote_plus = urllib.quote

if is_py3:
    from copy import deepcopy
    import urllib.parse
    from requests_sigv4.sigv4request import requests
    import requests_aws_sign

    _urlencode = deepcopy(urllib.parse.urlencode)

    # patching urlencode in python3 as it has a default
    # quote_via=quote_plus as the default
    def new_urlencode(query, doseq=False, safe='',
                      encoding=None, errors=None, quote_via=None):
        return _urlencode(
            query, doseq, safe, encoding, errors, urllib.parse.quote)
    requests.models.urlencode = new_urlencode
    requests_aws_sign.requests_aws_sign.urlencode = new_urlencode
