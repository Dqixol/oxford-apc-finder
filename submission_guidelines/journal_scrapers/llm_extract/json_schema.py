"""Generates a JSON Schema for structured LLM output (vLLM's guided_json,
or any JSON-Schema-based constrained decoding) directly from
common/schema.py's dataclasses, so the two can never drift apart --
schema.py stays the single source of truth, this just reflects it.

Run directly to print the schema: `python json_schema.py`
Run with --inline to print the fully-expanded version (no $ref/$defs) --
use that one if your vLLM backend's guided-decoding implementation doesn't
handle $ref well (this varies by backend/version and we haven't been able
to test against your specific setup).
"""
from __future__ import annotations

import dataclasses
import sys
import typing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common import schema as schema_module  # noqa: E402

_PRIMITIVES = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
}


def _type_to_schema(tp: object, defs: dict) -> dict:
    origin = typing.get_origin(tp)

    if origin is typing.Union:  # covers Optional[X] == Union[X, None]
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return {"anyOf": [_type_to_schema(args[0], defs), {"type": "null"}]}
        return {"anyOf": [_type_to_schema(a, defs) for a in args] + [{"type": "null"}]}

    if origin in (list, typing.List):
        (item_type,) = typing.get_args(tp)
        return {"type": "array", "items": _type_to_schema(item_type, defs)}

    if tp is typing.Any:
        return {}  # unconstrained -- only SourcedValue.value uses this, deliberately (values vary: bool, list[str], str)

    if dataclasses.is_dataclass(tp):
        _add_dataclass_def(tp, defs)
        return {"$ref": f"#/$defs/{tp.__name__}"}

    return _PRIMITIVES.get(tp, {})


def _add_dataclass_def(cls: type, defs: dict) -> None:
    if cls.__name__ in defs:
        return
    defs[cls.__name__] = {}  # placeholder, guards against infinite recursion if a dataclass ever self-references
    hints = typing.get_type_hints(cls)
    properties = {}
    required = []
    for f in dataclasses.fields(cls):
        properties[f.name] = _type_to_schema(hints[f.name], defs)
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            required.append(f.name)
    defs[cls.__name__] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_json_schema(root_cls: type = schema_module.JournalRecord) -> dict:
    defs: dict[str, dict] = {}
    _add_dataclass_def(root_cls, defs)
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$ref": f"#/$defs/{root_cls.__name__}",
        "$defs": defs,
    }


def inline(schema: dict) -> dict:
    """Fully expands all $ref/$defs into nested objects -- a fallback for guided-decoding
    backends with poor $ref support. Produces a larger but self-contained schema."""
    defs = schema.get("$defs", {})

    def resolve(node, seen: frozenset[str]):
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].rsplit("/", 1)[-1]
                if name in seen:
                    return {}  # would recurse forever -- not expected in our schema, but don't hang if it happens
                return resolve(defs[name], seen | {name})
            return {k: resolve(v, seen) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v, seen) for v in node]
        return node

    root = resolve({"$ref": schema["$ref"]}, frozenset())
    root["$schema"] = schema["$schema"]
    return root


if __name__ == "__main__":
    import json

    schema = build_json_schema()
    if "--inline" in sys.argv:
        schema = inline(schema)
    print(json.dumps(schema, indent=2))
