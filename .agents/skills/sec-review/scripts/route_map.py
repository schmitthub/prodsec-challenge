#!/usr/bin/env python3
"""Emit a route map for the FastAPI app: one row per route with the facts a security
reviewer needs (params, dependencies, client-supplied identifiers).

Imports app.main, so run it from the repo root under the project env:
    uv run python .agents/skills/sec-review/scripts/route_map.py [--json out.json] [--md out.md]

Read-only; never mutates the app.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
from pathlib import Path

ID_LIKE = re.compile(r"(^|_)(id|ids|key|uuid|slug|name|path|url)$", re.IGNORECASE)


def _dep_names(dependant) -> list[str]:
    names: list[str] = []
    stack = list(dependant.dependencies)
    while stack:
        d = stack.pop()
        call = d.call
        if inspect.isfunction(call) or inspect.ismethod(call) or inspect.isclass(call):
            label = call.__qualname__
            mod = call.__module__
        else:  # callable instance, e.g. OAuth2PasswordBearer(...)
            label = f"{type(call).__name__}()"
            mod = type(call).__module__
        names.append(
            f"{mod}.{label}" if mod and not mod.startswith("fastapi") else label
        )
        stack.extend(d.dependencies)
    return sorted(set(names))


def _params(fields) -> list[str]:
    return [f.name for f in fields]


def _body_fields(dependant) -> list[str]:
    out: list[str] = []
    for f in dependant.body_params:
        ann = f.type_ if hasattr(f, "type_") else getattr(f, "annotation", None)
        model_fields = getattr(ann, "model_fields", None)
        if model_fields:
            out.extend(f"{f.name}.{k}" for k in model_fields)
        else:
            out.append(f.name)
    return out


def _location(endpoint) -> str:
    try:
        src = inspect.getsourcefile(endpoint) or inspect.getfile(endpoint)
        _, line = inspect.getsourcelines(endpoint)
        return f"{os.path.relpath(src)}:{line}"
    except (OSError, TypeError):
        return "?"


def build(app) -> list[dict]:
    from fastapi.routing import APIRoute

    rows: list[dict] = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        dep = r.dependant
        path_p = _params(dep.path_params)
        query_p = _params(dep.query_params)
        header_p = _params(dep.header_params)
        body_p = _body_fields(dep)
        deps = _dep_names(dep)
        client_ids = [
            p
            for p in path_p + query_p + header_p + body_p
            if ID_LIKE.search(p.split(".")[-1])
        ]
        rows.append(
            {
                "methods": sorted(m for m in r.methods if m != "HEAD"),
                "path": r.path,
                "handler": r.endpoint.__qualname__,
                "location": _location(r.endpoint),
                "path_params": path_p,
                "query_params": query_p,
                "header_params": header_p,
                "body_fields": body_p,
                "dependencies": deps,
                "authenticated": any(d.endswith("get_current_user") for d in deps),
                "client_supplied_id": client_ids,
                "response_model": getattr(
                    getattr(r, "response_model", None), "__name__", None
                ),
            }
        )
    rows.sort(key=lambda x: (x["path"], x["methods"]))
    return rows


def to_markdown(rows: list[dict]) -> str:
    head = (
        "| method | path | handler | authn | client_supplied_id | path | query | body | dependencies | response_model |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in rows:
        lines.append(
            "| {m} | `{p}` | `{h}` | {a} | {cid} | {pp} | {qp} | {bp} | {d} | {rm} |".format(
                m=",".join(r["methods"]),
                p=r["path"],
                h=r["location"],
                a="yes" if r["authenticated"] else "**no**",
                cid=", ".join(f"`{x}`" for x in r["client_supplied_id"]) or "—",
                pp=", ".join(r["path_params"]) or "—",
                qp=", ".join(r["query_params"]) or "—",
                bp=", ".join(r["body_fields"]) or "—",
                d=", ".join(x.rsplit(".", 1)[-1] for x in r["dependencies"]) or "—",
                rm=r["response_model"] or "—",
            )
        )
    note = (
        "\n\n`client_supplied_id` = any request parameter whose name looks like an identifier "
        "(id/key/uuid/slug/name/path/url). Every row with a value here is the access-control "
        "reviewer's worklist. `authn` = route depends on `get_current_user`.\n"
    )
    return "# Route map\n\n" + head + "\n".join(lines) + note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    args = ap.parse_args()

    sys.path.insert(0, os.getcwd())
    from app.main import app  # deferred: must run inside the project env

    rows = build(app)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2) + "\n")
    md = to_markdown(rows)
    if args.md:
        args.md.write_text(md)
    if not args.json and not args.md:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
