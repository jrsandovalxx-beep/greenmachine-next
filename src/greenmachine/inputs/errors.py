"""Typed failure for the input contract (GMF-001).

A contract violation is a construction-time error with a message naming the
violated invariant — never a silently defaulted field.
"""

from __future__ import annotations


class InputContractError(ValueError):
    """An InputSnapshot construct violated a contract invariant."""
