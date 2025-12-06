import pytest
import requests
from click import ClickException

import cfmanager


class DummyResponse:
    """Simple stand-in for requests.Response used in unit tests."""

    def __init__(self, ok=True, status_code=200, json_data=None, text="", json_exception=False):
        self.ok = ok
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self._json_exception = json_exception

    def json(self):
        if self._json_exception:
            raise ValueError("Invalid JSON")
        return self._json_data


def test_get_api_token_prefers_cli_and_env(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "env-token")
    assert cfmanager.get_api_token("cli-token") == "cli-token"
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN")
    with pytest.raises(ClickException):
        cfmanager.get_api_token(None)


def test_create_dns_record_api_success(monkeypatch):
    response_payload = {"success": True, "result": {"id": "rec-123"}}

    def fake_post(url, json, headers, timeout):
        assert url.endswith("/zones/zone-1/dns_records")
        return DummyResponse(ok=True, status_code=200, json_data=response_payload)

    monkeypatch.setattr(cfmanager.requests, "post", fake_post)
    result = cfmanager.create_dns_record_api(
        zone_id="zone-1",
        api_token="token",
        hostname="example.com",
        record_type="A",
        value="1.1.1.1",
    )
    assert result == response_payload


def test_create_dns_record_api_http_error(monkeypatch):
    monkeypatch.setattr(
        cfmanager.requests,
        "post",
        lambda *args, **kwargs: DummyResponse(ok=False, status_code=500, text="boom"),
    )
    with pytest.raises(ClickException):
        cfmanager.create_dns_record_api("zone-1", "token", "host", "A", "1.1.1.1")


def test_create_dns_record_api_network_error(monkeypatch):
    def fake_post(*_args, **_kwargs):
        raise requests.exceptions.RequestException("network down")

    monkeypatch.setattr(cfmanager.requests, "post", fake_post)
    with pytest.raises(ClickException):
        cfmanager.create_dns_record_api("zone-1", "token", "host", "A", "1.1.1.1")


def test_list_dns_zones_api_paginates(monkeypatch):
    responses = [
        DummyResponse(
            json_data={
                "success": True,
                "result": [{"name": "a.com", "id": "1"}],
                "result_info": {"page": 1, "total_pages": 2},
            }
        ),
        DummyResponse(
            json_data={
                "success": True,
                "result": [{"name": "b.com", "id": "2"}],
                "result_info": {"page": 2, "total_pages": 2},
            }
        ),
    ]

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(cfmanager.requests, "get", fake_get)
    zones = cfmanager.list_dns_zones_api("token", items_per_page=1)
    assert zones == [("a.com", "1"), ("b.com", "2")]
    assert responses == []


def test_list_dns_zones_api_failure(monkeypatch):
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *args, **kwargs: DummyResponse(ok=True, json_data={"success": False, "errors": ["x"]}),
    )
    with pytest.raises(ClickException):
        cfmanager.list_dns_zones_api("token")


def test_get_zone_id_by_name_success(monkeypatch):
    payload = {
        "success": True,
        "result": [{"id": "zone-id", "name": "example.com"}],
        "result_info": {"page": 1, "total_pages": 1},
    }
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=True, json_data=payload),
    )
    assert cfmanager.get_zone_id_by_name("token", "example.com") == "zone-id"


def test_get_zone_id_by_name_not_found(monkeypatch):
    payload = {"success": True, "result": [], "result_info": {"page": 1, "total_pages": 1}}
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=True, json_data=payload),
    )
    with pytest.raises(ClickException):
        cfmanager.get_zone_id_by_name("token", "missing.com")


def test_find_dns_record_by_name_handles_multiple(monkeypatch):
    payload = {
        "success": True,
        "result": [
            {"name": "api.example.com", "type": "A", "content": "1.1.1.1", "id": "1"},
            {"name": "api.example.com", "type": "A", "content": "2.2.2.2", "id": "2"},
        ],
        "result_info": {"page": 1, "total_pages": 1},
    }
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=True, json_data=payload),
    )
    with pytest.raises(ClickException):
        cfmanager.find_dns_record_by_name("zone-id", "token", "api.example.com")


def test_find_dns_record_by_name_success(monkeypatch):
    payload = {
        "success": True,
        "result": [{"name": "api.example.com", "type": "A", "content": "1.1.1.1", "id": "1"}],
        "result_info": {"page": 1, "total_pages": 1},
    }
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=True, json_data=payload),
    )
    record = cfmanager.find_dns_record_by_name("zone-id", "token", "api.example.com")
    assert record["id"] == "1"
    assert record["content"] == "1.1.1.1"


def test_remove_dns_record_api_success(monkeypatch):
    payload = {"success": True, "result": {"id": "rec-1"}}
    monkeypatch.setattr(
        cfmanager.requests,
        "delete",
        lambda *a, **k: DummyResponse(ok=True, json_data=payload),
    )
    result = cfmanager.remove_dns_record_api("zone-id", "token", "rec-1")
    assert result == payload


def test_remove_dns_record_api_failure(monkeypatch):
    monkeypatch.setattr(
        cfmanager.requests,
        "delete",
        lambda *a, **k: DummyResponse(ok=True, json_data={"success": False}, text="err"),
    )
    with pytest.raises(ClickException):
        cfmanager.remove_dns_record_api("zone-id", "token", "rec-1")


def test_export_dns_zone_api(monkeypatch):
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=True, json_data=None, text="zone-data"),
    )
    assert cfmanager.export_dns_zone_api("zone-id", "token") == "zone-data"


def test_export_dns_zone_api_http_error(monkeypatch):
    monkeypatch.setattr(
        cfmanager.requests,
        "get",
        lambda *a, **k: DummyResponse(ok=False, status_code=500, text="err"),
    )
    with pytest.raises(ClickException):
        cfmanager.export_dns_zone_api("zone-id", "token")


def test_list_dns_records_api_paginates(monkeypatch):
    responses = [
        DummyResponse(
            json_data={
                "success": True,
                "result": [{"id": "1"}, {"id": "2"}],
                "result_info": {"page": 1, "total_pages": 2},
            }
        ),
        DummyResponse(
            json_data={
                "success": True,
                "result": [{"id": "3"}],
                "result_info": {"page": 2, "total_pages": 2},
            }
        ),
    ]

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(cfmanager.requests, "get", fake_get)
    records = cfmanager.list_dns_records_api("zone-id", "token", items_per_page=2)
    assert [rec["id"] for rec in records] == ["1", "2", "3"]
    assert responses == []


def test_log_api_invocation_wraps_request_exception(monkeypatch):
    calls = {}

    @cfmanager.log_api_invocation(lambda params: ("call-%s", (params["value"],)))
    def sample(value):
        calls["value"] = value
        raise requests.exceptions.RequestException("oops")

    with pytest.raises(ClickException):
        sample("x")
    assert calls["value"] == "x"
