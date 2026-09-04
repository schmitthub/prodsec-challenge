#!/usr/bin/env python3
"""Validate portable sec-review eval fixtures and grade normalized results."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
CASE_FORMAT = "sec-review-eval/v1"
RESULT_FORMAT = "sec-review-eval-result/v1"
CHECK_KINDS = {"output_regex", "agent_count", "agent_roles", "rubric"}
CASE_KEYS = {"format", "id", "tags", "limits", "prompt", "setup", "checks"}
RESULT_KEYS = {
    "format",
    "case",
    "run",
    "status",
    "final_output",
    "agents",
    "rubrics",
    "metrics",
}


class InvalidEval(ValueError):
    """Raised when an eval fixture or normalized result violates the contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidEval(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidEval(f"{path}: expected a JSON object")
    return value


def require_keys(value: dict[str, Any], keys: set[str], where: str) -> None:
    missing = sorted(keys - value.keys())
    if missing:
        raise InvalidEval(f"{where}: missing {', '.join(missing)}")


def require_only_keys(value: dict[str, Any], keys: set[str], where: str) -> None:
    unexpected = sorted(value.keys() - keys)
    if unexpected:
        raise InvalidEval(f"{where}: unexpected {', '.join(unexpected)}")


def referenced_file(base: Path, relative: Any, where: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise InvalidEval(f"{where}: expected a non-empty relative path")
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
        raise InvalidEval(f"{where}: missing referenced file {relative!r}")
    return candidate


def validate_case(path: Path) -> dict[str, Any]:
    case = load_json(path)
    require_keys(case, CASE_KEYS, str(path))
    require_only_keys(case, CASE_KEYS, str(path))
    if case["format"] != CASE_FORMAT:
        raise InvalidEval(f"{path}: unsupported format {case['format']!r}")
    if (
        not isinstance(case["id"], str)
        or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case["id"]) is None
        or case["id"] != path.parent.name
    ):
        raise InvalidEval(f"{path}: id must match its directory name")
    if not isinstance(case["tags"], list) or any(
        not isinstance(tag, str) or not tag for tag in case["tags"]
    ):
        raise InvalidEval(f"{path}: tags must contain non-empty strings")
    if len(case["tags"]) != len(set(case["tags"])):
        raise InvalidEval(f"{path}: tags must be unique")
    limits = case["limits"]
    if not isinstance(limits, dict):
        raise InvalidEval(f"{path}: limits must be an object")
    limit_keys = {"runs", "max_turns", "timeout_seconds"}
    require_keys(limits, limit_keys, f"{path}: limits")
    require_only_keys(limits, limit_keys, f"{path}: limits")
    if any(
        not isinstance(limits[key], int)
        or isinstance(limits[key], bool)
        or limits[key] < 1
        for key in limit_keys
    ):
        raise InvalidEval(f"{path}: limits must be positive integers")
    prompt_path = referenced_file(path.parent, case["prompt"], f"{path}: prompt")
    if not prompt_path.read_text().strip():
        raise InvalidEval(f"{path}: prompt must not be empty")
    setup = case["setup"]
    if not isinstance(setup, dict):
        raise InvalidEval(f"{path}: setup must be an object")
    require_keys(setup, {"path"}, f"{path}: setup")
    require_only_keys(setup, {"path"}, f"{path}: setup")
    referenced_file(path.parent, setup["path"], f"{path}: setup.path")
    checks = case["checks"]
    if not isinstance(checks, list) or not checks:
        raise InvalidEval(f"{path}: checks must be a non-empty array")
    ids: set[str] = set()
    for index, check in enumerate(checks):
        where = f"{path}: checks[{index}]"
        if not isinstance(check, dict):
            raise InvalidEval(f"{where}: expected an object")
        require_keys(check, {"id", "kind"}, where)
        if (
            not isinstance(check["id"], str)
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", check["id"]) is None
        ):
            raise InvalidEval(f"{where}: id must be lowercase kebab-case")
        if check["id"] in ids:
            raise InvalidEval(f"{where}: duplicate id {check['id']!r}")
        ids.add(check["id"])
        if check["kind"] not in CHECK_KINDS:
            raise InvalidEval(f"{where}: unsupported kind {check['kind']!r}")
        if check["kind"] == "output_regex":
            require_keys(check, {"pattern"}, where)
            require_only_keys(
                check, {"id", "kind", "pattern", "ignore_case", "negate"}, where
            )
            if any(
                key in check and not isinstance(check[key], bool)
                for key in ("ignore_case", "negate")
            ):
                raise InvalidEval(f"{where}: regex flags must be booleans")
            try:
                re.compile(check["pattern"])
            except (TypeError, re.error) as exc:
                raise InvalidEval(f"{where}: invalid regex: {exc}") from exc
        elif check["kind"] == "agent_count":
            require_only_keys(check, {"id", "kind", "min", "max"}, where)
            if "min" not in check and "max" not in check:
                raise InvalidEval(f"{where}: requires min or max")
            bounds = [check[key] for key in ("min", "max") if key in check]
            if any(
                not isinstance(bound, int) or isinstance(bound, bool) or bound < 0
                for bound in bounds
            ):
                raise InvalidEval(f"{where}: min and max must be non-negative integers")
            if check.get("min", 0) > check.get("max", sys.maxsize):
                raise InvalidEval(f"{where}: min must not exceed max")
        elif check["kind"] == "agent_roles":
            require_only_keys(check, {"id", "kind", "required", "forbidden"}, where)
            if "required" not in check and "forbidden" not in check:
                raise InvalidEval(f"{where}: requires required or forbidden roles")
            for key in ("required", "forbidden"):
                roles = check.get(key, [])
                if not isinstance(roles, list) or any(
                    not isinstance(role, str) or not role for role in roles
                ):
                    raise InvalidEval(f"{where}: {key} must contain non-empty strings")
                if len(roles) != len(set(roles)):
                    raise InvalidEval(f"{where}: {key} roles must be unique")
            if set(check.get("required", [])) & set(check.get("forbidden", [])):
                raise InvalidEval(f"{where}: a role cannot be required and forbidden")
        elif check["kind"] == "rubric":
            require_keys(check, {"path"}, where)
            require_only_keys(check, {"id", "kind", "path"}, where)
            rubric_path = referenced_file(path.parent, check["path"], where)
            if not rubric_path.read_text().strip():
                raise InvalidEval(f"{where}: missing or empty rubric {check['path']!r}")
    return case


def validate_result(result: dict[str, Any], case: dict[str, Any], path: Path) -> None:
    require_keys(
        result,
        {"format", "case", "run", "status", "final_output", "agents", "rubrics"},
        str(path),
    )
    require_only_keys(result, RESULT_KEYS, str(path))
    if result["format"] != RESULT_FORMAT:
        raise InvalidEval(f"{path}: unsupported format {result['format']!r}")
    if not isinstance(result["case"], str) or result["case"] != case["id"]:
        raise InvalidEval(f"{path}: result case does not match {case['id']!r}")
    if (
        not isinstance(result["run"], int)
        or isinstance(result["run"], bool)
        or result["run"] < 1
    ):
        raise InvalidEval(f"{path}: run must be a positive integer")
    if result["status"] not in {"completed", "timeout", "error"}:
        raise InvalidEval(f"{path}: unsupported run status {result['status']!r}")
    if not isinstance(result["final_output"], str):
        raise InvalidEval(f"{path}: final_output must be a string")
    if not isinstance(result["agents"], list) or any(
        not isinstance(agent, dict)
        or set(agent) != {"role"}
        or not isinstance(agent.get("role"), str)
        or not agent["role"]
        for agent in result["agents"]
    ):
        raise InvalidEval(f"{path}: agents must contain objects with string roles")
    roles = [agent["role"] for agent in result["agents"]]
    if len(roles) != len(set(roles)):
        raise InvalidEval(f"{path}: agent roles must be unique")
    if not isinstance(result["rubrics"], dict):
        raise InvalidEval(f"{path}: rubrics must be an object")
    for rubric_id, judgment in result["rubrics"].items():
        if (
            not isinstance(rubric_id, str)
            or not isinstance(judgment, dict)
            or set(judgment) != {"passed", "reason"}
            or not isinstance(judgment.get("passed"), bool)
            or not isinstance(judgment.get("reason"), str)
        ):
            raise InvalidEval(f"{path}: invalid rubric judgment {rubric_id!r}")
    if "metrics" in result:
        metrics = result["metrics"]
        allowed_metrics = {"wall_seconds", "input_tokens", "output_tokens"}
        if not isinstance(metrics, dict):
            raise InvalidEval(f"{path}: metrics must be an object")
        require_only_keys(metrics, allowed_metrics, f"{path}: metrics")
        for key, value in metrics.items():
            if (
                not isinstance(value, int | float)
                or isinstance(value, bool)
                or value < 0
                or (key != "wall_seconds" and not isinstance(value, int))
            ):
                raise InvalidEval(f"{path}: invalid metric {key!r}")


def grade(case: dict[str, Any], result: dict[str, Any]) -> list[tuple[str, bool, str]]:
    output = result["final_output"]
    roles = [agent["role"] for agent in result["agents"]]
    outcomes: list[tuple[str, bool, str]] = [
        (
            "run-status",
            result["status"] == "completed",
            f"status={result['status']}",
        )
    ]
    for check in case["checks"]:
        kind = check["kind"]
        if kind == "output_regex":
            flags = re.IGNORECASE if check.get("ignore_case", False) else 0
            matched = re.search(check["pattern"], output, flags) is not None
            passed = not matched if check.get("negate", False) else matched
            actual = "present" if matched else "absent"
            expected = "absent" if check.get("negate", False) else "present"
            detail = f"pattern {actual}; expected {expected}"
        elif kind == "agent_count":
            minimum = check.get("min", 0)
            maximum = check.get("max", sys.maxsize)
            passed = minimum <= len(roles) <= maximum
            detail = f"agents={len(roles)}, expected {minimum}..{maximum}"
        elif kind == "agent_roles":
            required = set(check.get("required", []))
            forbidden = set(check.get("forbidden", []))
            missing = sorted(required - set(roles))
            present_forbidden = sorted(forbidden & set(roles))
            passed = not missing and not present_forbidden
            detail = f"missing={missing}, forbidden_present={present_forbidden}"
        else:
            judgment = result["rubrics"].get(check["id"])
            if result["status"] != "completed" and judgment is None:
                outcomes.append(
                    (
                        check["id"],
                        False,
                        f"no judgment because status={result['status']}",
                    )
                )
                continue
            if not isinstance(judgment, dict) or not isinstance(
                judgment.get("passed"), bool
            ):
                raise InvalidEval(f"missing normalized rubric judgment {check['id']!r}")
            passed = judgment["passed"]
            detail = str(judgment.get("reason", ""))
        outcomes.append((check["id"], passed, detail))
    return outcomes


def validate_all() -> None:
    cases = sorted(EVALS_DIR.glob("*/case.json"))
    if not cases:
        raise InvalidEval("no case.json files found")
    for schema_name in ("case.schema.json", "result.schema.json"):
        load_json(EVALS_DIR / schema_name)
    for case_path in cases:
        validate_case(case_path)
    sys.stdout.write(f"valid: {len(cases)} portable eval cases\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    grade_parser = subparsers.add_parser("grade")
    grade_parser.add_argument("--case", required=True)
    grade_parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_all()
            return 0
        case_path = EVALS_DIR / args.case / "case.json"
        case = validate_case(case_path)
        result = load_json(args.result)
        validate_result(result, case, args.result)
        outcomes = grade(case, result)
    except InvalidEval as exc:
        sys.stderr.write(f"invalid: {exc}\n")
        return 2
    for check_id, passed, detail in outcomes:
        sys.stdout.write(f"{'PASS' if passed else 'FAIL'} {check_id}: {detail}\n")
    return 0 if all(passed for _, passed, _ in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
