class CityError(Exception):
    """Base error for city domain failures."""


class CityValidationError(CityError):
    """Raised when city data violates a domain invariant."""


class CityNotFoundError(CityError):
    """Raised when city cannot be found."""


class CityAlreadyExistsError(CityError):
    """Raised when city name already exists."""
