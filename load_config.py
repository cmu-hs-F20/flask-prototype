import jsonschema
import json


"""
    This config schema defines the required structure for a valid variable config file.
    See https://json-schema.org/understanding-json-schema/index.html for documentation
    on the JSON Schema standard.
"""
CONFIG_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "vars": {"type": "array", "contains": {"type": "string"}, "minItems": 1},
            "definition": {"type": "string", "minLength": 3},
            "description": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["name", "vars", "definition", "category"],
    },
}


def load_config(path: str) -> dict:
    """
    Validates and loads the variable config file stored in path.
    """

    try:
        with open(path, "r") as f:
            config = json.loads(f.read())
    except FileNotFoundError as e:
        print("Config file not found: '{}'".format(path))
        raise FileNotFoundError(e) from e

    try:
        jsonschema.validate(config, CONFIG_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        print("Failed to load config: {} is not a valid config".format(path))
        raise e

    return config


if __name__ == "__main__":
    load_config("vars.json")
