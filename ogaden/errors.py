"""Custom exception types for ogaden."""


class OgadenError(Exception):
    """Base exception for all ogaden errors."""


class FetchError(OgadenError):
    """Raised when fetching data from the exchange fails."""


class OrderError(OgadenError):
    """Raised when order execution fails."""


class ConfigError(OgadenError):
    """Raised when configuration is invalid."""
