# tests/test_location_request_high_traffic_stamp.py
"""Wire-shape tests for ``lastHighTrafficEnablingTime``.

``lastHighTrafficEnablingTime`` is a proto3 *message* field, so assigning
``seconds = 0`` still marks it present on the wire. Some tracker firmware
treats a present stamp as "high-traffic mode enabled" and emits an audible
chirp, so a background poll must omit the field entirely rather than send a
zero - or any other - stamp.
"""

from __future__ import annotations

import pytest

from custom_components.googlefindmy.NovaApi.ExecuteAction.LocateTracker.location_request import (
    create_location_request,
)
from custom_components.googlefindmy.ProtoDecoders import DeviceUpdate_pb2


def _locate_action(last_mode_switch: int | None, high_traffic: bool = False) -> object:
    """Build a request and return its decoded ``locateTracker`` action."""
    payload = create_location_request(
        "canonic-id",
        "fcm-token",
        "request-uuid",
        last_mode_switch=last_mode_switch,
        high_traffic=high_traffic,
    )
    request = DeviceUpdate_pb2.ExecuteActionRequest()
    request.ParseFromString(bytes.fromhex(payload))
    return request.action.locateTracker


@pytest.mark.parametrize(
    "last_mode_switch",
    [None, 0, 1_700_000_000],
    ids=["none", "zero", "switch-epoch"],
)
def test_field_absent_without_high_traffic(last_mode_switch: int | None) -> None:
    """Background poll -> the field must not appear on the wire at all.

    Includes a non-zero ``last_mode_switch``: the poll path legitimately carries
    the contributor-mode switch epoch, and that must still not stamp the field.
    """
    action = _locate_action(last_mode_switch)
    assert action.HasField("lastHighTrafficEnablingTime") is False


def test_field_present_with_stamp() -> None:
    """A manual locate stamps the field so the tracker advertises at high rate."""
    action = _locate_action(1_700_000_000, high_traffic=True)
    assert action.HasField("lastHighTrafficEnablingTime") is True
    assert action.lastHighTrafficEnablingTime.seconds == 1_700_000_000


def test_zero_stamp_is_not_merely_a_zero_value() -> None:
    """Regression: ``seconds = 0`` used to serialize as a *present* empty field.

    Guards the exact defect - the serialized bytes for "no stamp" must not carry
    field 2 at all (``12 00``), which is what a zero assignment produces.
    """
    payload = create_location_request(
        "canonic-id", "fcm-token", "request-uuid", last_mode_switch=0
    )  # high_traffic defaults to False
    assert "1200" not in payload.lower()
