import json
import logging
from base64 import urlsafe_b64encode
from sqlalchemy import event
from cryptography.hazmat.primitives.serialization import load_pem_private_key


logger = logging.getLogger('ok_service')

# Чтение приватного ключа из файла
with open("vapid_private_key.pem", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

VAPID_CLAIMS = {
    "sub": "mailto:your_email@example.com"
}


def notify_on_change(mapper, connection, target):
    logger.debug(f"Изменение обнаружено в таблице: {target.__tablename__}")
    from app.database.managers.subscription_manager import SubscriptionsManager
    db = SubscriptionsManager()

    # Проверяем, есть ли поле user у измененной таблицы
    user_id = getattr(target, 'user', None)
    if not user_id:
        logger.warning(f"""Таблица {
                       target.__tablename__} не содержит поле 'user'. Уведомления не отправлены.""")
        return

    # Получаем подписчиков для таблицы
    try:
        subscription = db.filter_by(user=user_id)
        send_push_notification(subscription, target)
    except Exception as ex:
        logger.error(f"""Ошибка отправки уведомления для подписки {
                     subscription['subscription_id']}: {ex}""")
        return


def send_push_notification(subscription, target):
    from pywebpush import webpush, WebPushException

    data = {
        "title": f"Обновление в таблице {target.__tablename__}",
        "body": f"Изменения: {target.to_dict()}",
    }
    logger.debug(f"Подготовка к отправке уведомления: {data}")

    try:
        webpush(
            subscription_info=json.loads(subscription['subscription_data']),
            data=json.dumps(data),
            vapid_private_key=urlsafe_b64encode(
                private_key.private_numbers().private_value.to_bytes(
                    length=(private_key.key_size + 7) // 8,
                    byteorder="big"
                )
            ).decode('utf-8'),
            vapid_claims=VAPID_CLAIMS
        )
        logger.info(f"""Уведомление успешно отправлено для подписки {
                    subscription['subscription_id']}""")
    except WebPushException as ex:
        logger.error(f"Ошибка WebPush при отправке уведомления: {str(ex)}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке уведомления: {e}")


# Пример применения слушателя для событий в таблице
"""def setup_listeners():
    from app.database.models import Projects  # Ваша модель
    logger.info("Настройка слушателей событий для модели Projects.")
    try:
        event.listen(Projects, 'after_insert', notify_on_change)
        event.listen(Projects, 'after_update', notify_on_change)
        event.listen(Projects, 'after_delete', notify_on_change)
        logger.info("Слушатели событий успешно настроены.")
    except Exception as e:
        logger.error(f"Ошибка настройки слушателей событий: {e}")

    from app.database.models import ShiftReports
    logger.info("Настройка слушателей событий для модели ShiftReports.")
    try:
        event.listen(ShiftReports, 'after_insert', notify_on_change)
        event.listen(ShiftReports, 'after_update', notify_on_change)
        event.listen(ShiftReports, 'after_delete', notify_on_change)
        logger.info("Слушатели событий успешно настроены.")
    except Exception as e:
        logger.error(f"Ошибка настройки слушателей событий: {e}")
"""
