import json
import pytest
import os
import sys
import unittest

from freezegun import freeze_time

from seshypy.base_session import BaseSession


@pytest.mark.unit
class TestBaseSession(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        os.environ['AWS_ACCESS_KEY_ID'] = 'test'
        os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'

    @classmethod
    def teardown_class(cls):
        os.environ.pop('AWS_DEFAULT_REGION', None)
        os.environ.pop('AWS_SECRET_ACCESS_KEY', None)
        os.environ.pop('AWS_ACCESS_KEY_ID', None)

    @freeze_time('2020-02-02')
    def test_base_session_get(self):
        want = {
            'args': {},
            'headers': {
                'Accept': 'application/json',
                'Accept-Encoding': 'identity',
                'Authorization': 'AWS4-HMAC-SHA256 Credential=test/20200202/'
                'us-west-2/execute-api/aws4_request, SignedHeaders=host;'
                'x-amz-date, Signature=db7be03c558c367efbd8cf9d587a6e224'
                'e8380595801586fdeee3223560d7fc4',
                'Content-Type': 'application/json',
                'Host': 'httpbin.org',
                'X-Amz-Date': '20200202T000000Z',
            },
            'url': 'https://httpbin.org/get'
        }
        session = BaseSession(
            host='https://httpbin.org'
        )
        res = session.get(
            path='/get',
        )
        if sys.version_info[0] == 2:
            got = json.loads(res.content)
        else:
            got = json.loads(res.content.decode())
        got.pop('origin', None)
        assert got == want


if __name__ == '__main__':
    unittest.main()
