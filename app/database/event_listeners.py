import json
import time
from uuid import UUID
import logging
from base64 import urlsafe_b64encode
from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from config import Config


logger = logging.getLogger('ok_service')

config = Config()
ORIGIN = config.ORIGIN

# Чтение приватного ключа из файла
with open("vapid_private_key.pem", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

VAPID_CLAIMS = {
    "sub": "mailto:your_email@example.com"
}

# ⚡ Диспетчер уведомлений
NOTIFICATION_HANDLERS = {}


def notify_on_project_works_change(target, event_name):
    """Обработчик уведомлений для ProjectWorks"""
    logger.info(
        f"[ProjectWorks] Изменение обнаружено (event: {event_name}): ID={target.project_work_id}")

    from app.database.managers.subscription_manager import SubscriptionsManager
    from app.database.managers.projects_managers import ProjectWorksManager

    db = SubscriptionsManager()
    project_manager = ProjectWorksManager()
    try:
        # Генерируем ссылку
        link = f"https://{ORIGIN}/projects/{target.project}"

        if event_name == 'insert':
            # ⚡ Обновляем target из БД, чтобы получить актуальные данные
            logger.info(
                f"[ProjectWorks] Обрабатываем вставку новой записи: {target.project_work_id}")

            user_id = project_manager.get_manager(target.project_work_id)
            if not user_id:
                logger.warning(
                    f"[ProjectWorks] Не найден user_id для {target.project_work_id}. Уведомление не отправлено.")
                return

            subscription = db.filter_by(user=user_id)
            message_data = {
                "title": "Добавлена новая проектная работа",
                "body": f"Создана новая проектная работа с ID: {target.project_work_id}",
                "url": link
            }

        elif event_name == 'update':

            logger.info(
                f"[ProjectWorks] Обрабатываем обновление записи: {target.project_work_id}")

            history = get_history(target, "signed")
            logger.debug(f"[ProjectWorks] История изменения signed: {history}")

            if history.has_changes and len(history.deleted) > 0 and len(history.added) > 0:
                if history.deleted[0] is False and history.added[0] is True:
                    user_id = project_manager.get_project_leader(
                        target.project_work_id)
                    if not user_id:
                        logger.warning(
                            f"[ProjectWorks] Не найден project_leader для {target.project_work_id}. Уведомление не отправлено.")
                        return

                    subscription = db.filter_by(user=user_id)
                    message_data = {
                        "title": "Проектная работа подписана",
                        "body": f"Проектная работа с ID: {target.project_work_id} была подписана",
                        "url": link
                    }
            else:

                logger.debug(
                    f"[ProjectWorks] Поле signed не изменилось с False → True. Уведомление не отправляется.")
                return
        send_push_notification(subscription, message_data)

    except Exception as ex:
        logger.error(
            f"[ProjectWorks] Ошибка при отправке уведомления: {ex}", exc_info=True)


def notify_on_shift_reports_change(target, event_name):
    """Обработчик уведомлений для ShiftReports"""
    logger.info(
        f"[ShiftReports] Изменение обнаружено (event: {event_name}): ID={target.shift_report_id}")

    from app.database.managers.subscription_manager import SubscriptionsManager
    from app.database.managers.shift_reports_managers import ShiftReportsManager

    db = SubscriptionsManager()
    shift_manager = ShiftReportsManager()

    try:
        link = f"https://{ORIGIN}/shifts/{target.shift_report_id}"

        if event_name == 'insert':

            logger.info(
                f"[ShiftReports] Обрабатываем вставку нового отчёта: {target.shift_report_id}")

            user_id = shift_manager.get_project_leader(
                target.shift_report_id)

            if not user_id:
                logger.warning(
                    f"[ShiftReports] Не найден user_id для {target.shift_report_id}. Уведомление не отправлено.")
                return

            subscription = db.filter_by(user=user_id)
            message_data = {
                "title": "Добавлен новый сменный отчёт",
                "body": f"Создан новый сменный отчёт ID: {target.shift_report_id}",
                "url": link
            }

        elif event_name == 'update':
            logger.info(
                f"[ShiftReports] Обрабатываем обновление сменного отчёта: {target.shift_report_id}")
            shift_report = shift_manager.get_by_id(
                target.shift_report_id)
            if shift_report:
                previous_signed = shift_report['signed']  # Старое значение
                current_signed = target.signed  # Новое значение
                if previous_signed is False and current_signed is True:
                    user_id = getattr(target, 'user', None)
                    if not user_id:
                        logger.warning(
                            f"[ShiftReports] Не найден user_id для {target.shift_report_id}. Уведомление не отправлено.")
                        return

                    subscription = db.filter_one_by_dict(user=UUID(user_id))
                    message_data = {
                        "title": "Сменный отчёт подписан",
                        "body": f"Сменный отчёт ID: {target.shift_report_id} был подписан",
                        "url": link
                    }
                else:
                    logger.debug(
                        f"[ShiftReports] Поле signed не изменилось с False → True. Уведомление не отправляется.")

        send_push_notification(subscription, message_data)

    except Exception as ex:
        logger.error(
            f"[ShiftReports] Ошибка при отправке уведомления: {ex}", exc_info=True)


def notify_on_change(mapper, connection, target, event_name):
    """Общий обработчик изменений"""
    table_name = target.__tablename__
    logger.info(
        f"[GLOBAL] Обработчик изменений вызван для таблицы {table_name}, event={event_name}")
    # 🔥 Добавляем небольшую задержку перед обработкой, чтобы БД успела закоммитить изменения
    time.sleep(0.5)
    handler = NOTIFICATION_HANDLERS.get(table_name)
    if handler:
        handler(target, event_name)
    else:
        logger.warning(
            f"[GLOBAL] Нет обработчика для таблицы {table_name}. Уведомления не отправлены.")


def send_push_notification(subscription_info, message_data):
    """Отправка WebPush-уведомления"""
    logger.debug(f"[WebPush] Подготовка к отправке: {message_data}")

    try:
        subscription_info_corrected = {
            "endpoint": subscription_info["endpoint"],
            "keys": {
                "p256dh": subscription_info["p256dh"],
                "auth": subscription_info["auth"]
            }
        }
        webpush(
            subscription_info=json.loads(
                subscription_info_corrected['subscription_data']),
            data=json.dumps(message_data),
            vapid_private_key=urlsafe_b64encode(
                private_key.private_numbers().private_value.to_bytes(
                    length=(private_key.key_size + 7) // 8,
                    byteorder="big"
                )
            ).decode('utf-8'),
            vapid_claims=VAPID_CLAIMS
        )
        logger.info(f"[WebPush] Уведомление успешно отправлено.")
    except WebPushException as ex:
        logger.error(f"[WebPush] Ошибка WebPush: {str(ex)}", exc_info=True)
    except Exception as e:
        logger.error(f"[WebPush] Неизвестная ошибка: {e}", exc_info=True)


# ⚡ Заполняем диспетчер
NOTIFICATION_HANDLERS["project_works"] = notify_on_project_works_change
NOTIFICATION_HANDLERS["shift_reports"] = notify_on_shift_reports_change


def setup_listeners():
    """Настройка слушателей событий с задержкой перед вызовом notify_on_change()"""
    from app.database.models import ProjectWorks, ShiftReports

    logger.info("[GLOBAL] Настройка слушателей событий")
    try:
        def delayed_notify(m, c, t, event_name):
            """Добавляем задержку перед вызовом notify_on_change()"""
            time.sleep(0.5)  # 🔥 Даем время БД на коммит
            notify_on_change(m, c, t, event_name)

        event.listen(ProjectWorks, 'after_insert', lambda m,
                     c, t: delayed_notify(m, c, t, "insert"))
        event.listen(ProjectWorks, 'after_update', lambda m,
                     c, t: delayed_notify(m, c, t, "update"))
        event.listen(ShiftReports, 'after_insert', lambda m,
                     c, t: delayed_notify(m, c, t, "insert"))
        event.listen(ShiftReports, 'after_update', lambda m,
                     c, t: delayed_notify(m, c, t, "update"))

        logger.info("[GLOBAL] Слушатели событий успешно настроены.")
    except Exception as e:
        logger.error(
            f"[GLOBAL] Ошибка настройки слушателей: {e}", exc_info=True)
