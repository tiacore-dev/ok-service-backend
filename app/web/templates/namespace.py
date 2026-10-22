from flask_restx import Namespace

template_ns = Namespace(
    "templates",
    path="/templates",
    description="Шаблоны и генерация документов: admin и manager",
)
