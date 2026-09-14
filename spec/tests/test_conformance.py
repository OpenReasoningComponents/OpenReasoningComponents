"""Conformance suite for OpenReasoningComponents (ORC).

Validates every ``*.json`` fixture in this directory against the canonical
``component.schema.json`` and asserts the verdict matches the fixture's
``valid``. This suite is implementation-independent: it exercises the published
schema directly, so a second-language consumer can run the same files.

Fixture-based, a common pattern for conformance suites (each fixture carries
``{description, data, valid}``), so a second-language consumer's suite can
follow the same shape without depending on this one's implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SPEC_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SPEC_DIR / "component.schema.json"
FIXTURE_DIR = SPEC_DIR / "tests"
EXAMPLES_PATH = SPEC_DIR.parent / "examples" / "components.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _make_validator() -> jsonschema.protocols.Validator:
    """Build a validator whose dialect is chosen from the schema's ``$schema``.

    Dispatching via ``validator_for`` means a second-language implementation and
    this one agree on dialect selection from the document alone.
    """
    schema = _load_schema()
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


def test_schema_is_itself_a_valid_json_schema() -> None:
    # Raises SchemaError if the schema is malformed.
    _make_validator()


@pytest.mark.parametrize("fixture_path", _fixture_paths(), ids=lambda p: p.stem)
def test_fixture_matches_expected_verdict(fixture_path: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert {"description", "data", "valid"} <= fixture.keys(), (
        f"{fixture_path.name} is missing required conformance keys"
    )

    validator = _make_validator()
    errors = list(validator.iter_errors(fixture["data"]))
    is_valid = not errors
    expected = fixture["valid"]

    assert is_valid == expected, (
        f"{fixture_path.name}: expected valid={expected}, got valid={is_valid}. "
        f"Errors: {[e.message for e in errors]}"
    )


def test_checked_in_examples_agree_with_schema() -> None:
    """examples/components.json is a batch of components, not one-manifest-per-file
    like ODS's examples/ directory, so it gets one test over every entry instead of a
    valid/ and invalid/ directory pair: every checked-in example is expected to be
    valid, since it's meant to double as documentation of the format.
    """
    validator = _make_validator()
    components = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    assert components, "examples/components.json should not be empty"
    for component in components:
        errors = list(validator.iter_errors(component))
        assert not errors, (
            f"{component.get('id', '<no id>')} should be valid. "
            f"Errors: {[e.message for e in errors]}"
        )
