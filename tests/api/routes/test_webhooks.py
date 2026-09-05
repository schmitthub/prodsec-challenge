import pytest
import requests
from fastapi.testclient import TestClient

from app.api.policies import webhooks
from app.core.config import settings

URL = f"{settings.API_V1_STR}/webhooks/vendor-preview"


@pytest.fixture(scope="module")
def allowed_url() -> str:
    hosts = sorted(settings.webhook_allowed_hosts)
    assert hosts, "WEBHOOK_ALLOWED_HOSTS must name at least one host for these tests"
    return f"https://{hosts[0]}/preview"


def _host(url: str) -> str:
    return url.removeprefix("https://").split("/")[0]


class _FakeResponse:
    def __init__(self, *, status_code: int, text: str, content_type: str) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = {"content-type": content_type}


@pytest.fixture
def outbound_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Stub the outbound fetch so tests never leave the process."""
    calls: list[tuple[str, dict]] = []

    def fake_get(url: str, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse(status_code=200, text="x" * 500, content_type="text/plain")

    monkeypatch.setattr(webhooks.requests, "get", fake_get)
    return calls


def test_member_is_forbidden(
    client: TestClient,
    member_token_headers: dict[str, str],
    outbound_calls,
    allowed_url: str,
) -> None:
    r = client.post(
        URL, json={"callback_url": allowed_url}, headers=member_token_headers
    )
    assert r.status_code == 403
    assert outbound_calls == []


def test_unauthenticated_is_rejected(
    client: TestClient, outbound_calls, allowed_url: str
) -> None:
    r = client.post(URL, json={"callback_url": allowed_url})
    assert r.status_code == 401
    assert outbound_calls == []


def test_staff_preview_allowed_host(
    client: TestClient,
    staff_token_headers: dict[str, str],
    outbound_calls,
    allowed_url: str,
) -> None:
    r = client.post(
        URL, json={"callback_url": allowed_url}, headers=staff_token_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status_code"] == 200
    assert body["content_type"] == "text/plain"
    assert len(body["preview"]) == 200

    ((url, kwargs),) = outbound_calls
    assert url == allowed_url
    assert kwargs["timeout"] == 2
    assert kwargs["allow_redirects"] is False


def test_staff_preview_allowed_host_is_case_insensitive(
    client: TestClient,
    staff_token_headers: dict[str, str],
    outbound_calls,
    allowed_url: str,
) -> None:
    r = client.post(
        URL,
        json={"callback_url": f"https://{_host(allowed_url).upper()}/preview"},
        headers=staff_token_headers,
    )
    assert r.status_code == 200
    assert len(outbound_calls) == 1


@pytest.mark.parametrize(
    "callback_url",
    [
        "https://not-on-the-list.example.com/x",
        "https://127.0.0.1/latest/meta-data/",
        "https://169.254.169.254/latest/meta-data/",
        "https://localhost/",
    ],
)
def test_staff_preview_disallowed_host(
    client: TestClient,
    staff_token_headers: dict[str, str],
    outbound_calls,
    callback_url: str,
) -> None:
    r = client.post(
        URL, json={"callback_url": callback_url}, headers=staff_token_headers
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "callback_url host is not allowed"
    assert outbound_calls == []


def test_staff_preview_lookalike_hosts_are_rejected(
    client: TestClient,
    staff_token_headers: dict[str, str],
    outbound_calls,
    allowed_url: str,
) -> None:
    host = _host(allowed_url)
    for candidate in (f"https://evil.{host}/", f"https://{host}.evil.example/"):
        r = client.post(
            URL, json={"callback_url": candidate}, headers=staff_token_headers
        )
        assert r.status_code == 400, candidate
    assert outbound_calls == []


def test_staff_preview_requires_https(
    client: TestClient,
    staff_token_headers: dict[str, str],
    outbound_calls,
    allowed_url: str,
) -> None:
    r = client.post(
        URL,
        json={"callback_url": allowed_url.replace("https://", "http://", 1)},
        headers=staff_token_headers,
    )
    assert r.status_code == 400
    assert outbound_calls == []


def test_staff_preview_reports_upstream_failure(
    client: TestClient,
    staff_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    allowed_url: str,
) -> None:
    def failing_get(*_args, **_kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(webhooks.requests, "get", failing_get)
    r = client.post(
        URL, json={"callback_url": allowed_url}, headers=staff_token_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status_code"] == 500
    assert body["content_type"] is None
    assert "boom" in body["preview"]


@pytest.mark.parametrize("bad", ["not a url", "ftp://x", "", None])
def test_invalid_callback_url_is_rejected(
    client: TestClient, staff_token_headers: dict[str, str], outbound_calls, bad
) -> None:
    r = client.post(URL, json={"callback_url": bad}, headers=staff_token_headers)
    assert r.status_code == 422
    assert outbound_calls == []
