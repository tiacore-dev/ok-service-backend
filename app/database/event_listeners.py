import json
import time
from uuid import UUID
import logging
from base64 import urlsafe_b64encode
from sqlalchemy import event
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
    "sub": "mailto:your-email@example.com",  # Замени на реальный email
    "aud": "https://fcm.googleapis.com",  # 👈 Должно совпадать с `endpoint`
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
    subscriptions = None  # ✅ ОБЪЯВЛЯЕМ ПЕРЕМЕННУЮ СРАЗУ
    message_data = None
    try:
        # Генерируем ссылку
        link = f"https://{ORIGIN}/projects/{target.project}"

        if event_name == 'insert':
            # ⚡ Обновляем target из БД, чтобы получить актуальные данные
            logger.info(
                f"[ProjectWorks] Обрабатываем вставку новой записи: {target.project_work_id}")

            user_id = project_manager.get_manager(target.project)
            if not user_id:
                logger.warning(
                    f"[ProjectWorks] Не найден user_id для {target.project_work_id}. Уведомление не отправлено.")
                return

            if user_id == str(target.created_by):
                logger.info(
                    f"[ProjectWorks] создан тем же пользователем user_id для {target.project_work_id}. Уведомление не отправлено.")
                return

            subscriptions = db.filter_by_dict(user=UUID(user_id))
            message_data = {
                "header": "Добавлена новая проектная работа",
                "text": f"Создана новая проектная работа с ID: {target.project_work_id}",
                "link": link
            }

        elif event_name == 'update':

            logger.info(
                f"[ProjectWorks] Обрабатываем обновление записи: {target.project_work_id}")
            project_work = project_manager.get_by_id(target.project_work_id)
            if project_work:
                previous_signed = project_work['signed']  # Старое значение
                current_signed = target.signed  # Новое значение
                if previous_signed is False and current_signed is True:
                    user_id = project_manager.get_project_leader(
                        target.project_work_id)
                    if not user_id:
                        logger.warning(
                            f"[ProjectWorks] Не найден project_leader для {target.project_work_id}. Уведомление не отправлено.")
                        return

                    subscriptions = db.filter_by_dict(user=UUID(user_id))
                    message_data = {
                        "header": "Проектная работа подписана",
                        "text": f"Проектная работа с ID: {target.project_work_id} была подписана",
                        "link": link
                    }
                else:

                    logger.debug(
                        "[ProjectWorks] Поле signed не изменилось с False → True. Уведомление не отправляется.")
                    return
        else:
            return
        send_push_notification(subscriptions, message_data)

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
    subscriptions = None  # ✅ ОБЪЯВЛЯЕМ ПЕРЕМЕННУЮ СРАЗУ
    message_data = None
    try:
        link = f"https://{ORIGIN}/shifts/{target.shift_report_id}"

        if event_name == 'insert':

            logger.info(
                f"[ShiftReports] Обрабатываем вставку нового отчёта: {target.shift_report_id}")

            user_id = shift_manager.get_project_leader(
                target.project)

            if not user_id:
                logger.warning(
                    f"[ShiftReports] Не найден user_id для {target.shift_report_id}. Уведомление не отправлено.")
                return

            if user_id == str(target.created_by):
                logger.info(
                    f"[ShiftReports] создан тем же пользователем user_id для {target.shift_report_id}. Уведомление не отправлено.")
                return

            subscriptions = db.filter_by_dict(user=UUID(user_id))
            message_data = {
                "header": "Добавлен новый сменный отчёт",
                "text": f"Создан новый сменный отчёт ID: {target.shift_report_id}",
                "link": link
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

                    subscriptions = db.filter_by_dict(user=UUID(user_id))
                    message_data = {
                        "header": "Сменный отчёт подписан",
                        "text": f"Сменный отчёт ID: {target.shift_report_id} был подписан",
                        "link": link
                    }
                else:
                    logger.debug(
                        "[ShiftReports] Поле signed не изменилось с False → True. Уведомление не отправляется.")
                    return
                update_conditions(shift_report, target)
        else:
            return

        send_push_notification(subscriptions, message_data)

    except Exception as ex:
        logger.error(
            f"[ShiftReports] Ошибка при отправке уведомления: {ex}", exc_info=True)


def update_conditions(shift_report, target):
    previous_extreme = shift_report['extreme_conditions']
    previous_night = shift_report['night_shift']
    current_extreme = target.extreme_conditions
    current_night = target.night_shift
    if previous_extreme != current_extreme or previous_night != current_night:
        from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
        details_manager = ShiftReportsDetailsManager()
        details_manager.recalculate_shift_details(
            shift_report['shift_report_id'])


def notify_on_change(_, __, target, event_name):
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


def send_push_notification(subscriptions, message_data):
    """Отправка WebPush-уведомления"""
    logger.debug(f"[WebPush] Подготовка к отправке: {message_data}")

    try:
        for subscription in subscriptions:
            subscription_info = {
                "endpoint": subscription['endpoint'], "keys": json.loads(subscription['keys'])}
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(message_data),
                vapid_private_key=urlsafe_b64encode(
                    private_key.private_numbers().private_value.to_bytes(
                        length=(private_key.key_size + 7) // 8,
                        byteorder="big"
                    )
                ).decode('utf-8'),
                vapid_claims=VAPID_CLAIMS
            )
            logger.info("[WebPush] Уведомление успешно отправлено.")
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

        event.listen(ProjectWorks, 'after_insert', lambda m,
                     c, t: notify_on_change(m, c, t, "insert"))
        event.listen(ProjectWorks, 'after_update', lambda m,
                     c, t: notify_on_change(m, c, t, "update"))
        event.listen(ShiftReports, 'after_insert', lambda m,
                     c, t: notify_on_change(m, c, t, "insert"))
        event.listen(ShiftReports, 'after_update', lambda m,
                     c, t: notify_on_change(m, c, t, "update"))

        logger.info("[GLOBAL] Слушатели событий успешно настроены.")
    except Exception as e:
        logger.error(
            f"[GLOBAL] Ошибка настройки слушателей: {e}", exc_info=True)
