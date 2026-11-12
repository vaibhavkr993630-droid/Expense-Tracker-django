"""
Caching for analytics results with the Django cache framework (`django.core.cache`).

Problem: results depend on the user and on query parameters (month, year, ...), and they must
become stale the moment that user's expenses change. Deleting "the right keys" would mean
guessing every parameter combination that was ever cached.

Solution: put a per-user *version* in every cache key. Whenever the user's expenses change we
store a new version, so all old entries are never looked up again and simply expire on their own.
"""

import time

from django.conf import settings
from django.core.cache import cache


def _version_key(user_id):
    return f"analytics:version:{user_id}"


def _current_version(user_id):
    # get_or_set: return the stored version, or store (and return) a new one. timeout=None = no expiry.
    # The version is a timestamp, so even if the cache evicts it, the next one differs from any old one.
    return cache.get_or_set(_version_key(user_id), time.time_ns, None)


def invalidate_user_analytics(user_id):
    """Make every cached analytics result of this user obsolete."""
    cache.set(_version_key(user_id), time.time_ns(), None)


def get_cached(user, name, params, compute):
    """Return the cached result for (user, name, params), computing and storing it on a miss."""
    param_part = ":".join(f"{key}={params[key]}" for key in sorted(params))
    key = f"analytics:{user.id}:{_current_version(user.id)}:{name}:{param_part}"
    result = cache.get(key)
    if result is None:
        result = compute()
        cache.set(key, result, settings.ANALYTICS_CACHE_TTL)
    return result
