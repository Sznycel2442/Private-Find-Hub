from custom_components.private_find_hub.privacy.gate import (
    PrivacyGate,
    PrivacyGateState,
    RecorderPolicy,
)


def test_recorder_inclusion_closes_gate_even_when_acknowledged() -> None:
    decision = PrivacyGate().evaluate(RecorderPolicy.INCLUDED, True, 8)
    assert decision.can_publish is False
    assert decision.state is PrivacyGateState.CLOSED_INCLUDED


def test_verified_exclusion_opens_gate() -> None:
    decision = PrivacyGate().evaluate(RecorderPolicy.VERIFIED_EXCLUDED, False, 8)
    assert decision.can_publish is True
    assert decision.state is PrivacyGateState.OPEN_VERIFIED


def test_unverified_policy_requires_acknowledgement() -> None:
    closed = PrivacyGate().evaluate(RecorderPolicy.UNVERIFIED, False, 8)
    opened = PrivacyGate().evaluate(RecorderPolicy.UNVERIFIED, True, 8)
    assert closed.can_publish is False
    assert opened.can_publish is True
    assert opened.state is PrivacyGateState.OPEN_ACKNOWLEDGED


def test_entity_registration_race_keeps_gate_closed() -> None:
    decision = PrivacyGate().evaluate(RecorderPolicy.UNVERIFIED, True, 0)
    assert decision.can_publish is False
    assert decision.state is PrivacyGateState.CLOSED_NO_ENTITIES

