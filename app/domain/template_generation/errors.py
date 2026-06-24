class TemplateError(Exception):
    """Base error for template generation failures."""


class TemplateGenerationError(TemplateError):
    """Raised when template generation fails."""
