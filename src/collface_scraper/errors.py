"""Stable, sanitized failures for command-line reporting."""


class CollFaceError(Exception):
    code = "collface_error"


class ConfigurationError(CollFaceError):
    code = "configuration_error"


class AuthenticationError(CollFaceError):
    code = "authentication_error"


class InteractiveAuthenticationRequired(AuthenticationError):
    code = "auth_unattended_blocked"


class AccessBlocked(CollFaceError):
    code = "access_blocked"


class DiscoveryError(CollFaceError):
    code = "discovery_error"


class ExtractionError(CollFaceError):
    code = "extraction_error"


class FetchError(CollFaceError):
    code = "fetch_error"


class StateMismatch(CollFaceError):
    code = "state_mismatch"

