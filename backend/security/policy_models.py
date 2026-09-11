from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Policy:
    """A single named, configurable rule."""
    key: str
    value: Any
    description: str = ""


@dataclass
class PolicyEvaluation:
    """Result of checking a value against a named policy."""
    policy_key: str
    passed: bool
    policy_value: Any
    actual_value: Any
    reason: str