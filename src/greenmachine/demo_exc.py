"""Demonstration violation (GMR-003 criterion 7, exception-handling boundary)."""


def swallow() -> None:
    """Broad handler that silently discards every error."""
    try:
        raise ValueError("demo")
    except Exception:
        pass
