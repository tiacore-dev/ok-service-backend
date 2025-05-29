from app.schemas.template_schemas import TemplateGenerateSchema
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
template_generate_model = generate_swagger_model(
    TemplateGenerateSchema(), "templateCreate"
)
