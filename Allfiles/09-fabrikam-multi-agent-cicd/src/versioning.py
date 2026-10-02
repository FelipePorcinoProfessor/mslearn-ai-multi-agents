from __future__ import annotations

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version


def parse_version(value: str) -> Version:
    """Parse a strict three-component semantic version."""
    try:
        parsed = Version(value)
    except InvalidVersion as error:
        raise ValueError(f"Invalid agent version: {value}") from error

    if (
        len(parsed.release) != 3
        or parsed.is_prerelease
        or parsed.is_postrelease
        or parsed.is_devrelease
        or parsed.local is not None
        or str(parsed) != value
    ):
        raise ValueError(f"Agent version must use strict MAJOR.MINOR.PATCH: {value}")
    return parsed


def satisfies(version: str, requirement: str) -> bool:
    """Return whether a strict semantic version satisfies a dependency range."""
    return parse_version(version) in SpecifierSet(requirement)