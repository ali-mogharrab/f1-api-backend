from django.conf import settings
from django.core.cache import caches
from rest_framework.throttling import SimpleRateThrottle


class AccountThrottle(SimpleRateThrottle):
    # Reuse the configurable shared cache, without adding infrastructure.
    cache = caches["ai"]

    def get_rate(self):
        return settings.AUTH_THROTTLE_RATES[self.scope]

    def get_cache_key(self, request, view):
        # Authenticated callers must not bypass the public account endpoint limits.
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginThrottle(AccountThrottle):
    scope = "login"


class RegistrationThrottle(AccountThrottle):
    scope = "registration"


class PasswordResetThrottle(AccountThrottle):
    scope = "password_reset"


class RefreshThrottle(AccountThrottle):
    scope = "token_refresh"
