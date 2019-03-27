import inspect
import logging
try:
    from urllib.parse import urlencode
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urllib import urlencode
    from urlparse import urljoin

import requests
from retrying import retry

from seshypy.session import Session
from seshypy.utils import safe_ttl_cache

log = logging.getLogger(__name__)


class BaseSession(object):
    """BaseSession from which each session derives.

    This object handles authentication (and keeping it alive), and requests.
    It uses the Session object for session handling.

    Args:
        host (str): api endpoint
        role_arn (optional[str]): arn for role to sts into
        aws_access_key_id (optional[str]): access key
        aws_secret_access_key (optional[str]): secret key
        region (optional[str]): api region (required if using access and secret keys)
        session (optional(session)): session to be shared across subclasses
        use_cache (optional[bool]): Use cache? Defaults to False
        cache_ttl (optional[int]): Duration cache lives. Defaults to 1200.
        cache_methods (optional[int]): List of methods to cache.
            Defaults provided by the inheriting classes.

    Returns:
        session instance

    Cache:
        The caching is provided by cachetools_. The defaults provided by each class
        or a list of method names passed in are wrapped by the ttl_cache method. By
        default this sets a ttl of 20 minutes, but this can be configured by passing
        in cache_ttl with the number of seconds you want the cache to live.

        You can disable cache entirely by passing in ``use_cache=False``.

        >>> cmdb = CMDBSession(use_cache=False, **cfg)

        Cache can be invalidated by calling the method ``cache_clear()`` on a given method.

        >>> cmdb.accounts.get_account.cache_clear()

    .. _cachetools:
        http://pythonhosted.org/cachetools/
    """

    def __init__(self, host, role_arn=None, aws_access_key_id=None,
                 aws_secret_access_key=None, region=None, session=None,
                 use_cache=True, cache_ttl=1200, cache_methods=None):
        self.host = host
        self.headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json',
        }
        if not session:
            session = Session(
                role_arn=role_arn,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region=region)
        self.session = session
        self.__use_cache = bool(use_cache)
        self.__cache_ttl = cache_ttl
        self.__cache_methods = cache_methods if cache_methods is not None else []
        if self.use_cache:
            for method_name in set(self.cache_methods):
                self.__enable_method_cache(method_name)

    def __enable_method_cache(self, method_name):
        """Enable cache for a method.

        Args:
            method_name (str): name of method for which to enable cache

        Returns:
            bool: True is success, False if failed
        """
        try:
            method = getattr(self, method_name)
            try:
                return not inspect.isfunction(method.cache_info)
            except AttributeError:
                setattr(
                    self, method_name,
                    safe_ttl_cache(ttl=self.cache_ttl)(method))
                return True
        except AttributeError:
            # method doesn't exist on initializing class
            return False

    @property
    def use_cache(self):
        """Boolean to use cache or not."""
        return self.__use_cache

    @property
    def cache_ttl(self):
        """Duration cache lives."""
        return self.__cache_ttl

    @property
    def cache_methods(self):
        """List of methods to cache."""
        return self.__cache_methods

    def make_api_gateway_call(self, method, path, headers=None, qstr_vals=None,
                              params=None, host=None, payload=None):
        """Make call to API Gateway.

        Args:
            method (str): HTTP method
            path (str): request path
            headers (optional[dict]): headers if provided else self.headers
            qstr_vals (optional[dict]): query string parameters to add
                deprecated: use params
            params (optional[dict]): query string parameters
            host (optional[str]): URL to host for request else self.host
            payload (optional[dict]): payload as dictionary

        Returns:
            response object
        """
        # This is to support older implementations using qstr_vals instead of params.
        params = params if params is not None else qstr_vals
        host = host if host else self.host
        headers = headers if headers else self.headers
        req = self.session.requests()
        url = urljoin(host, path)
        try:
            if method == 'POST':
                res = req.post(url, headers=headers,
                               json=payload, params=params)
            elif method == 'GET':
                res = req.get(url, headers=headers, params=params)
            elif method == 'PUT':
                res = req.put(url, headers=headers,
                              params=params, json=payload)
            elif method == 'DELETE':
                res = req.delete(url, headers=headers)
            else:
                raise ValueError('HTTP method {} not supported'.format(method))
            if res.status_code != 200 or not res.json():
                if res.status_code == 200 and not res.json() and method == 'GET':
                    # results are falsy; probably an empty list
                    extra_info = ('{} actually received 200, but the result was empty.'
                                  .format(__package__))
                    res.reason = 'Not Found; {}'.format(extra_info)
                    res.status_code = 404
                log.info(res)
                res.raise_for_status()
            log.info('request to %s', url)
            return res
        except requests.exceptions.RequestException as err:
            log.error(err)
            raise

    def get(self, path, host=None, headers=None, params=None):
        """GET from API Gateway.

        Args:
            path (str): request path
            headers (optional[dict]): headers if provided else self.headers
            params (optional[dict]): query string parameters
            host (optional[str]): URL to host for request else self.host

        Returns:
            response object
        """
        return self.make_api_gateway_call(
            'GET',
            path=path, host=host, headers=headers, params=params
        )

    def post(self, path, host=None, headers=None, params=None, payload=None):
        """POST to API Gateway.

        Args:
            path (str): request path
            host (optional[str]): URL to host for request else self.host
            headers (optional[dict]): headers if provided else self.headers
            params (optional[dict]): query string parameters
            payload (optional[dict]): payload as dictionary

        Returns:
            response object
        """
        return self.make_api_gateway_call(
            'POST',
            path=path, host=host, headers=headers, params=params, payload=payload
        )

    def put(self, path, host=None, headers=None, params=None, payload=None):
        """PUT to API Gateway.

        Args:
            path (str): request path
            host (optional[str]): URL to host for request else self.host
            headers (optional[dict]): headers if provided else self.headers
            params (optional[dict]): query string parameters
            payload (optional[dict]): payload as dictionary

        Returns:
            response object
        """
        return self.make_api_gateway_call(
            'PUT',
            path=path, host=host, headers=headers, params=params, payload=payload
        )

    def delete(self, path, host=None, headers=None):
        """DELETE from API Gateway.

        Args:
            path (str): request path
            host (optional[str]): URL to host for request else self.host
            headers (optional[dict]): headers if provided else self.headers

        Returns:
            response object
        """
        return self.make_api_gateway_call(
            'DELETE',
            path=path, host=host, headers=headers
        )

    def api_retrying(self, *args, **kwargs):
        """Wrap api calls with retrying.

        Args:
            all options provided by retrying library
                url: https://pypi.python.org/pypi/retrying

        Example::

            retrying_kwargs = {
                'retry_on_exception': lambda x: isinstance(x, ConnectionError),
                'stop_max_attempt_number': 3,
                'wait_exponential_multiplier': 1000,
                'wait_exponential_max': 10000
            }
            session.api_retrying(**retrying_kwargs)
        """
        self.make_api_gateway_call = retry(
            *args, **kwargs)(self.make_api_gateway_call)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass
