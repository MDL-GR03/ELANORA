import pytest
from pydantic import ValidationError

from app.schema.protocol import ProtocolRules


def test_protocol_rules_reject_unknown_parent_tier() -> None:
    with pytest.raises(ValidationError, match="parent tiers must also be required"):
        ProtocolRules(
            required_tiers=["Hand repetition"],
            tier_parents={"Hand repetition": "Manual signs"},
        )


def test_protocol_rules_reject_parent_cycles() -> None:
    with pytest.raises(ValidationError, match="cannot contain cycles"):
        ProtocolRules(
            required_tiers=["Manual signs", "Hand repetition"],
            tier_parents={
                "Manual signs": "Hand repetition",
                "Hand repetition": "Manual signs",
            },
        )
