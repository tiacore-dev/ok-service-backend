engine = None
Session = None
Base = None


def set_db_globals(engine_instance, session_instance, base_instance):
    global engine, Session, Base  # pylint: disable=global-statement
    engine = engine_instance
    Session = session_instance
    Base = base_instance
