class KimiError(Exception):
    """Базовая ошибка интеграции с Kimi API."""


class KimiConfigurationError(KimiError):
    """Не заданы обязательные настройки Kimi API."""


class KimiRequestError(KimiError):
    """Kimi API недоступен или вернул некорректный ответ."""


class SystemPromptMissingError(KimiError):
    """В системных настройках отсутствует промпт для модели."""
