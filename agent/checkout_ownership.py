"""Checkout ownership admission guards for runtime-owned jobs."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_PROTECTED_CANONICAL_CHECKOUTS = (
    "/Users/serg/AI/LOOP-ORDER-SYSTEM",
)

PROTECTED_CHECKOUTS_ENV = "HERMES_PROTECTED_CANONICAL_CHECKOUTS"
ENFORCE_CHECKOUT_OWNERSHIP_ENV = "HERMES_ENFORCE_CHECKOUT_OWNERSHIP"


def _configured_protected_roots() -> tuple[Path, ...]:
    raw_paths = list(DEFAULT_PROTECTED_CANONICAL_CHECKOUTS)
    extra = os.getenv(PROTECTED_CHECKOUTS_ENV, "")
    if extra:
        raw_paths.extend(p for p in extra.split(os.pathsep) if p.strip())

    roots: list[Path] = []
    for raw in raw_paths:
        try:
            roots.append(Path(raw).expanduser().resolve())
        except OSError:
            continue
    return tuple(roots)


def protected_canonical_checkout_for(path: str | os.PathLike[str]) -> Path | None:
    """Return the protected canonical root containing *path*, if any."""
    candidate = Path(path).expanduser().resolve()
    for root in _configured_protected_roots():
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        return root
    return None


def checkout_owner_guard_message(path: str | os.PathLike[str]) -> str | None:
    """Build the standard failure message for protected canonical workdirs."""
    root = protected_canonical_checkout_for(path)
    if root is None:
        return None
    return (
        "checkout_owner_guard=failed: refused runtime-owned mutation context "
        f"inside coordinator-owned canonical checkout {root}. "
        "Use a Multica runtime checkout or an agent-owned worktree instead."
    )


def assert_runtime_writable_workdir(path: str | os.PathLike[str]) -> None:
    """Raise before a runtime job uses a protected canonical checkout as cwd."""
    message = checkout_owner_guard_message(path)
    if message:
        raise PermissionError(message)


def checkout_ownership_enforced() -> bool:
    return os.getenv(ENFORCE_CHECKOUT_OWNERSHIP_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
