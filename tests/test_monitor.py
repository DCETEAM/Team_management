"""Unit tests for monitor auth and idempotency helpers."""

import hashlib
import datetime
from src.models.monitor_models import _hash_token


def test_token_hash():
    token = "sample-token-for-test"
    assert _hash_token(token) == hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_idle_threshold_constant():
    from src.utils import monitor_settings as ms

    assert ms.IDLE_THRESHOLD_SECONDS == 30


def test_live_state_unknown_when_stale_heartbeat():
    from src.controllers import monitor_controller as mc

    ref = datetime.datetime(2026, 10, 29, 12, 0, 0)

    class FakeSession:
        ended_at = None
        last_heartbeat_at = ref - datetime.timedelta(seconds=500)
        status = "active"

    assert mc._live_state_for_session(FakeSession(), None, ref) == "unknown"
