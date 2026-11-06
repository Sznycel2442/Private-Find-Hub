class PrivateFindHubError(Exception):
    pass


class AuthenticationRequiredError(PrivateFindHubError):
    pass


class DecryptionError(PrivateFindHubError):
    pass


class InvalidLocationError(PrivateFindHubError):
    pass


class NetworkPolicyError(PrivateFindHubError):
    pass


class ProtocolBlockedError(PrivateFindHubError):
    pass


class ProtocolChangedError(PrivateFindHubError):
    pass


class RateLimitedError(PrivateFindHubError):
    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("rate_limited")
        self.retry_after = retry_after


class TemporaryTransportError(PrivateFindHubError):
    pass

