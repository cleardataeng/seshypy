from cachetools.func import ttl_cache
import logging
import functools

log = logging.getLogger(__name__)


def safe_ttl_cache(*args, **kwargs):
    """Return a ttl_cache wrapped function that can handle unhashable arguments.

    Notes:
        Do this by detecting this condition and returning the results of the
            correct method.

        The outside wrapper, safe_ttl_cache, must capture all arguments to be
            passed to the inner wrapper, wrapped. The mid wrapper,
            func_wrapper, is simply to capture the actual method to be
            fully wrapped.

        safe_ttl_cache shall not be called as a naked decorator. It can be
            called as in examples.

    Examples:
        >>> @safe_ttl_cache()
        >>> def what_you_want_cached(*args, **kwargs)
        >>>     pass

        >>> @safe_ttl_cache(ttl_cache_arguments=here)
        >>> def what_you_want_cached(*args, **kwargs)
        >>>    pass
    """
    def func_wrapper(method):
        ttl_method = ttl_cache(*args, **kwargs)(method)
        @functools.wraps(ttl_method)
        def wrapped(*in_args, **in_kwargs):
            try:
                return ttl_method(*in_args, **in_kwargs)
            except TypeError as err:
                if 'unhashable type' in err.args[0]:
                    log.warning('%s: Returning results without cache. Cannot '
                                'use cache with unhashable type in arguments',
                                method.__name__)
                    return ttl_method.__wrapped__(*in_args, **in_kwargs)
                raise
        return wrapped
    return func_wrapper
