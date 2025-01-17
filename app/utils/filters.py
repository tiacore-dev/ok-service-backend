def filter_model_fields(data, model):
    """Фильтрует данные, оставляя только те ключи, которые есть в модели SQLAlchemy."""
    valid_keys = {column.name for column in model.__table__.columns}
    return {key: value for key, value in data.items() if key in valid_keys}
