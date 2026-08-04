class MeasurementUnitError(Exception):
    pass


class MeasurementUnitValidationError(MeasurementUnitError):
    pass


class MeasurementUnitNotFoundError(MeasurementUnitError):
    pass
