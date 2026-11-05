#!/usr/bin/env python3
"""Validate generated fixtures with Draft 2020-12 and runtime snapshot invariants."""
import json
import hashlib
import pathlib
import sys
from urllib.parse import urlsplit

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    sys.exit("Install development checks: python3 -m pip install -r scripts/requirements-protocol.txt")

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "docs/schemas/retoob-feed-v1.schema.json").read_text())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(path):
    with path.open("rb") as stream:
        data = stream.read(10 * 1024 * 1024 + 1)
    require(len(data) <= 10 * 1024 * 1024, "feed exceeds 10 MiB")
    document = json.loads(data)
    errors = sorted(VALIDATOR.iter_errors(document), key=lambda error: str(list(error.path)))
    if errors:
        for error in errors:
            print(f"{path} {list(error.path)}: {error.message}", file=sys.stderr)
        raise ValueError("schema validation failed")
    require("next_url" not in document, "This offline validator requires a complete unpaginated snapshot")
    items = document["items"]
    require(document["_retoob"]["itemCount"] == len(items), "incorrect itemCount")
    pointer = document["_retoob"].get("schema")
    require(pointer is None or pointer == SCHEMA["$id"], f"Unknown schema URI {pointer!r}; use a reviewed pinned schema")
    require(len({i["id"] for i in items}) == len(items), "duplicate card permalink")
    for field in ("itemId", "contentKey"):
        require(len({i["_retoob"][field] for i in items}) == len(items), f"duplicate {field}")
    seen_recommendations = set()
    for item in items:
        profile = item["_retoob"]
        require(item["id"] == item["url"], "card ID must be its stable permalink")
        require((profile["sortAt"] is None) == (profile["dateBasis"] == "unknown"), "sortAt/dateBasis mismatch")
        for recommendation in profile["recommendations"]:
            require(recommendation["id"] not in seen_recommendations, "duplicate recommendation ID")
            seen_recommendations.add(recommendation["id"])
    print(f"Validated {path} ({len(items)} cards)")


def check_fixtures():
    paths = sorted((ROOT / "testdata/protocol/v1/outputs").glob("*.json"))
    if len(paths) < 2:
        sys.exit("Generate the two fixture feeds first: make fixtures")
    for path in paths:
        validate(path)

    scenario_dir = ROOT / "testdata/protocol/v1/scenarios"
    manifest = json.loads((scenario_dir / "manifest.json").read_text())
    for scenario in manifest["scenarios"]:
        for step in scenario["steps"]:
            label = step["validation"]
            if label == "no-body":
                assert step["status"] == 304 and "body" not in step, "304 must not carry a body"
                continue
            path = scenario_dir / step["body"]
            data = path.read_bytes()
            document = json.loads(data)
            if label in ("valid-feed", "invalid-feed"):
                errors = list(VALIDATOR.iter_errors(document))
                if label == "valid-feed":
                    assert not errors, f"{path}: {[e.message for e in errors]}"
                    assert len(data) <= 10 * 1024 * 1024, "page exceeds complete-feed budget"
                    assert len(document["items"]) <= document["_retoob"]["itemCount"], "page exceeds itemCount"
                    if "next_url" in document:
                        request = urlsplit(step["requestUrl"])
                        following = urlsplit(document["next_url"])
                        assert (following.scheme, following.netloc) == (request.scheme, request.netloc), "pagination changed origin"
                else:
                    assert errors, "malformed-page fixture unexpectedly satisfies the schema"
                expected_etag = '"' + hashlib.sha256(data).hexdigest() + '"'
                assert step["headers"]["ETag"] == expected_etag, "scenario ETag does not describe exact body bytes"
            elif label == "problem":
                assert document["status"] == step["status"], "problem status mismatch"
                assert isinstance(document["code"], str) and document["code"], "missing problem code"
                assert step["headers"]["Cache-Control"] == "no-store", "problem response is cacheable"
            else:
                raise ValueError(f"Unknown scenario validation label: {label}")
        print(f"Validated scenario {scenario['name']} ({len(scenario['steps'])} responses)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for name in sys.argv[1:]:
            validate(pathlib.Path(name))
    else:
        check_fixtures()
