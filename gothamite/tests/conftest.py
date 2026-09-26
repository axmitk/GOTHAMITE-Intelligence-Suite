import pytest
import requests


@pytest.fixture(autouse=True)
def enforce_test_isolation_and_block_live_server(monkeypatch):
    """
    Globally guarantees that test suites never touch a running live server or external network.
    
    1. Forces `frontend.api_client.check_api_online` to return False, ensuring frontend client
       code always routes through isolated in-memory test database fixtures rather than localhost.
    2. Blocks all outbound HTTP calls via `requests.Session.send` to prevent any test from
       accidentally leaking requests to a running backend container or port.
    """
    monkeypatch.setattr("frontend.api_client.check_api_online", lambda: False)

    def _fail_on_live_http(*args, **kwargs):
        raise RuntimeError(
            "Test isolation violation: live HTTP network call attempted during test run! "
            "Tests must strictly use isolated in-memory test fixtures."
        )

    monkeypatch.setattr(requests.Session, "send", _fail_on_live_http)
