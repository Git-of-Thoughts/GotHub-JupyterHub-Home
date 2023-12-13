class GothubKernelError(Exception):
    """Base class for exceptions in this module."""

    pass


class PleaseUpgradePlan(GothubKernelError):
    """Raised when the user's plan is not sufficient for the requested action."""

    pass
