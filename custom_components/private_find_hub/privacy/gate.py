from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecorderPolicy(StrEnum):
    VERIFIED_EXCLUDED = "verified_excluded"
    INCLUDED = "included"
    UNVERIFIED = "unverified"


class PrivacyGateState(StrEnum):
    OPEN_VERIFIED = "open_verified"
    OPEN_ACKNOWLEDGED = "open_acknowledged"
    CLOSED_INCLUDED = "closed_recorder_included"
    CLOSED_UNVERIFIED = "closed_unverified"
    CLOSED_NO_ENTITIES = "closed_no_entities"


@dataclass(frozen=True, slots=True)
class PrivacyDecision:
    state: PrivacyGateState
    can_publish: bool
    recorder_policy: RecorderPolicy
    checked_entities: int


class PrivacyGate:
    def evaluate(
        self,
        policy: RecorderPolicy,
        acknowledged: bool,
        checked_entities: int,
    ) -> PrivacyDecision:
        if checked_entities == 0 and policy is not RecorderPolicy.VERIFIED_EXCLUDED:
            return PrivacyDecision(
                PrivacyGateState.CLOSED_NO_ENTITIES,
                False,
                policy,
                checked_entities,
            )
        if policy is RecorderPolicy.VERIFIED_EXCLUDED:
            return PrivacyDecision(
                PrivacyGateState.OPEN_VERIFIED,
                True,
                policy,
                checked_entities,
            )
        if policy is RecorderPolicy.INCLUDED:
            return PrivacyDecision(
                PrivacyGateState.CLOSED_INCLUDED,
                False,
                policy,
                checked_entities,
            )
        if acknowledged:
            return PrivacyDecision(
                PrivacyGateState.OPEN_ACKNOWLEDGED,
                True,
                policy,
                checked_entities,
            )
        return PrivacyDecision(
            PrivacyGateState.CLOSED_UNVERIFIED,
            False,
            policy,
            checked_entities,
        )

