from flask_restx import Model, fields, marshal


class EmptyPreservingNested(fields.Nested):
    """Keep an explicitly empty summary instead of filling it with null fields."""

    def output(self, key, obj, ordered=False, **kwargs):
        value = fields.get_value(
            self.attribute if self.attribute is not None else key, obj
        )
        if value == {}:
            return {}
        return super().output(key, obj, ordered=ordered, **kwargs)


class NestedMap(fields.Nested):
    """Serialize a dictionary of modeled items without shared traversal state."""

    label = "Nested maps"

    def output(self, key, obj, ordered=False, **kwargs):
        value = fields.get_value(
            self.attribute if self.attribute is not None else key, obj
        )
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise fields.MarshallingError(f"{self.label} must be a dictionary")
        return {
            item_key: marshal(item, self.nested, ordered=ordered)
            for item_key, item in value.items()
        }

    def schema(self):
        model = self.nested
        if not isinstance(model, Model):
            raise fields.MarshallingError(f"{self.label} require a named Model")
        schema = fields.Raw.schema(self)
        schema["type"] = "object"
        schema["additionalProperties"] = {"$ref": f"#/definitions/{model.name}"}
        return schema
