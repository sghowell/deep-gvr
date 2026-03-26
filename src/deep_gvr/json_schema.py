from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SchemaValidationError(Exception):
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(path, f"value {instance!r} is not in enum {schema['enum']!r}")

    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(path, f"value {instance!r} does not equal const {schema['const']!r}")

    schema_type = schema.get("type")
    effective_type: str | None = None
    if schema_type is not None:
        _validate_type(instance, schema_type, path)
        allowed = [schema_type] if isinstance(schema_type, str) else list(schema_type)
        for item in allowed:
            if _matches_type(instance, item):
                effective_type = item
                break

    if effective_type == "object":
        _validate_object(instance, schema, path)
    elif effective_type == "array":
        _validate_array(instance, schema, path)
    elif effective_type == "string":
        if not isinstance(instance, str):
            raise SchemaValidationError(path, "expected string")
        min_length = schema.get("minLength")
        if min_length is not None and len(instance) < min_length:
            raise SchemaValidationError(path, f"string shorter than minLength {min_length}")
    elif effective_type == "integer" and isinstance(instance, bool):
        raise SchemaValidationError(path, "booleans are not valid integers")


def _validate_type(instance: Any, schema_type: str | list[str], path: str) -> None:
    allowed = [schema_type] if isinstance(schema_type, str) else list(schema_type)
    if any(_matches_type(instance, item) for item in allowed):
        return
    raise SchemaValidationError(path, f"expected type {allowed!r}, got {type(instance).__name__}")


def _matches_type(instance: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(instance, dict)
    if schema_type == "array":
        return isinstance(instance, list)
    if schema_type == "string":
        return isinstance(instance, str)
    if schema_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if schema_type == "number":
        return (isinstance(instance, int) and not isinstance(instance, bool)) or isinstance(instance, float)
    if schema_type == "boolean":
        return isinstance(instance, bool)
    if schema_type == "null":
        return instance is None
    return False


def _validate_object(instance: Any, schema: dict[str, Any], path: str) -> None:
    if not isinstance(instance, dict):
        raise SchemaValidationError(path, "expected object")

    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for key in required:
        if key not in instance:
            raise SchemaValidationError(path, f"missing required property {key!r}")

    additional = schema.get("additionalProperties", True)
    if additional is False:
        for key in instance:
            if key not in properties:
                raise SchemaValidationError(path, f"unexpected property {key!r}")
    elif isinstance(additional, dict):
        for key, value in instance.items():
            if key not in properties:
                validate(value, additional, f"{path}.{key}")

    for key, value in instance.items():
        if key in properties:
            validate(value, properties[key], f"{path}.{key}")


def _validate_array(instance: Any, schema: dict[str, Any], path: str) -> None:
    if not isinstance(instance, list):
        raise SchemaValidationError(path, "expected array")

    min_items = schema.get("minItems")
    if min_items is not None and len(instance) < min_items:
        raise SchemaValidationError(path, f"array shorter than minItems {min_items}")

    item_schema = schema.get("items")
    if item_schema is None:
        return

    for index, item in enumerate(instance):
        validate(item, item_schema, f"{path}[{index}]")
