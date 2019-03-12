from datetime import datetime, timedelta
import functools
import inspect

from requests_sigv4 import Sigv4Request
import boto3
import botocore
from botocore.credentials import RefreshableCredentials
from botocore.exceptions import UnknownServiceError
from dateutil.tz import tzutc


class Session(object):
    """AWS Session for CMDB access."""

    def __init__(
        self,
        role_arn=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        region=None,
    ):
        self.region = region
        self.role_arn = role_arn
        self.assumed = None
        self.passed = None
        self.resolved = None
        if all([aws_access_key_id, aws_secret_access_key]):
            self.passed = {'access_key': aws_access_key_id,
                           'secret_key': aws_secret_access_key}
        elif any([aws_access_key_id, aws_secret_access_key]):
            raise ValueError(
                'must provide both aws_access_key_id and aws_secret_key or neither')
        else:
            self._resolve()

        if self.role_arn:
            self.assumed = self._assume_role()

    def _resolve(self):
        """Resolve credentials.

        botocore.credentials.RefreshableCredentials has a _refresh() method, but it only
        works if the credentials have not yet expired yet. So when they do expire we need
        to call this method again to get new credentials.
        """
        session = botocore.session.Session()
        resolver = botocore.credentials.create_credential_resolver(session)
        self.resolved = resolver.load_credentials()
        if not self.resolved:
            raise EnvironmentError('no aws credentials found')

    def _assume_role(self):
        sts_kwargs = {'region_name': self.region}
        if self.passed:
            sts_kwargs['aws_access_key_id'] = self.passed['access_key']
            sts_kwargs['aws_secret_access_key'] = self.passed['secret_key']

        if self.resolved:
            # For Credentials, get_frozen_credentials prevents race conditions
            # when calling self.resolved.access_key|secret_key|token, which each
            # getter in the object attempts to refresh creds. So it is possible
            # to get mismatched credentials.
            frozen_credentials = self.resolved.get_frozen_credentials()
            sts_kwargs['aws_access_key_id'] = frozen_credentials.access_key
            sts_kwargs['aws_secret_access_key'] = frozen_credentials.secret_key
            sts_kwargs['aws_session_token'] = frozen_credentials.token

        sts = boto3.client('sts', **sts_kwargs)
        try:
            return sts.assume_role(RoleArn=self.role_arn,
                                   RoleSessionName='seshypy')
        except botocore.exceptions.ClientError as e:
            msg = 'Assume role failed with the following arguments ' \
                  'region_name: {0}, ' \
                  'aws_access_key_id: {1}, ' \
                  'aws_secret_access_key: {2}, ' \
                  'aws_session_token: {3}'
            e.args += (msg.format(
                sts_kwargs['region_name'],
                sts_kwargs['aws_access_key_id'],
                sts_kwargs['aws_secret_access_key'],
                sts_kwargs['aws_session_token']
            ),)
            raise

    def _verify_resolved(self):
        """Verify or update resolved credentials."""
        if (
            self.resolved and
            self.resolved is RefreshableCredentials and
            self.resolved.refresh_needed()
        ):
            self._resolve()

    def requests(self):
        """Return requester for other sessions."""
        kwargs = {'region': self.region}
        self._verify_resolved()
        if self.assumed:
            reset_time = datetime.now(tz=tzutc()) + timedelta(seconds=30)
            if self.assumed['Credentials']['Expiration'] < reset_time:
                self.assumed = self._assume_role()

            kwargs['access_key'] = self.assumed['Credentials']['AccessKeyId']
            kwargs['secret_key'] = self.assumed['Credentials']['SecretAccessKey']
            kwargs['session_token'] = self.assumed['Credentials']['SessionToken']
            kwargs['session_expires'] = self.assumed['Credentials']['Expiration']
            return Sigv4Request(**kwargs)

        kwargs['access_key'] = (self.passed['access_key']
                                if self.passed else self.resolved.access_key)
        kwargs['secret_key'] = (self.passed['secret_key']
                                if self.passed else self.resolved.secret_key)
        if self.resolved:
            kwargs['session_token'] = self.resolved.token

        return Sigv4Request(**kwargs)

    def __boto3_kwargs(self):
        """Get boto3 client or resource kwargs."""
        kwargs = {'region_name': self.region}
        self._verify_resolved()
        if self.assumed:
            reset_time = datetime.now(tz=tzutc()) + timedelta(seconds=30)
            if self.assumed['Credentials']['Expiration'] < reset_time:
                self.assumed = self._assume_role()
            kwargs['aws_access_key_id'] = self.assumed['Credentials']['AccessKeyId']
            kwargs['aws_secret_access_key'] = self.assumed['Credentials']['SecretAccessKey']
            kwargs['aws_session_token'] = self.assumed['Credentials']['SessionToken']
            return kwargs

        kwargs['aws_access_key_id'] = (
            self.passed['access_key']
            if self.passed else self.resolved.access_key
        )
        kwargs['aws_secret_access_key'] = (
            self.passed['secret_key']
            if self.passed else self.resolved.secret_key
        )
        return kwargs

    def client(self, *args, **kwargs):
        """Get a boto3 client."""
        return self.__persistent_methods(self.__client(*args, **kwargs))

    def resource(self, *args, **kwargs):
        """Get a boto3 resource."""
        return self.__persistent_methods(self.__resource(*args, **kwargs))

    def __client(self, *args, **kwargs):
        """Get a boto3 client."""
        kwargs.update(self.__boto3_kwargs())
        return boto3.client(*args, **kwargs)

    def __resource(self, *args, **kwargs):
        """Get a boto3 resource."""
        kwargs.update(self.__boto3_kwargs())
        return boto3.resource(*args, **kwargs)

    def __persistent_methods(self, obj):
        """Make all methods persistent.

        Args:
            obj (object): boto3.client or boto3.resource
        """
        for name, method in inspect.getmembers(obj, inspect.ismethod):
            setattr(obj, name, self.__persist(method))
        if hasattr(obj.meta, 'client'):
            for name, method in inspect.getmembers(obj.meta.client, inspect.ismethod):
                setattr(obj.meta.client, name, self.__persist(method))
        return obj

    def __persist(self, method):
        """Force all calls on methods to check credentials.

        Args:
            method (method): method to wrap with persistence

        Returns:
            method: method that knows to verify credentials before __call__
        """
        @functools.wraps(method)
        def new_and_call(*args, **kwargs):
            try:
                service = method.__self__.__class__.__name__.lower()
                client = self.__client(service)
            except UnknownServiceError:
                service = method.__self__.__class__.__name__.split('.')[0].lower()
                resource = self.__resource(service)
            try:
                return getattr(client, method.__name__)(*args, **kwargs)
            except UnboundLocalError:
                return getattr(resource, method.__name__)(*args, **kwargs)
        return new_and_call
