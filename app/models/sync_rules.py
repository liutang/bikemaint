"""Sync rules: which Strava rides count for a bike or part (specs/060-sync-rules).

Pure functions, no I/O. Sports, ride types and keywords are stored as comma-separated text.
A ride whose detail is unknown (imported before the details were stored) always matches that
filter, so nothing disappears silently.
"""

from __future__ import annotations

import re

SPORTS: dict[str, str] = {
    "Ride": "Ride",
    "GravelRide": "Gravel ride",
    "MountainBikeRide": "Mountain bike ride",
    "EBikeRide": "E-bike ride",
    "EMountainBikeRide": "E-mountain bike ride",
    "VirtualRide": "Virtual ride",
    "Handcycle": "Handcycle",
    "Velomobile": "Velomobile",
}
RIDE_TYPES: dict[str, str] = {"default": "Default", "race": "Race", "workout": "Workout"}


def sport_label(code: str | None) -> str:
    """A Strava sport type as a readable label (specs/083): the known list, else split at capitals."""
    if not code:
        return ""
    if code in SPORTS:
        return SPORTS[code]
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", code).split()
    return " ".join([words[0]] + [w.lower() for w in words[1:]]) if words else code

MAX_KEYWORDS = 10
MAX_KEYWORDS_LENGTH = 200


def ride_type_of(workout_type: int | None) -> str:
    """Strava's ride `workout_type` (10 default, 11 race, 12 workout) as our ride type."""
    return {11: "race", 12: "workout"}.get(workout_type or 0, "default")


def _split(text: str | None) -> list[str]:
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def ride_matches(
    sports: str | None,
    ride_types: str | None,
    keywords: str | None,
    sport_type: str | None,
    ride_type: str | None,
    name: str | None,
) -> bool:
    """True when a ride passes every filter that is filled in."""
    wanted_sports = _split(sports)
    if wanted_sports and sport_type is not None and sport_type not in wanted_sports:
        return False
    wanted_types = _split(ride_types)
    if wanted_types and ride_type is not None and ride_type not in wanted_types:
        return False
    words = [w.lower() for w in _split(keywords)]
    if words and name is not None and not any(w in name.lower() for w in words):
        return False
    return True


def clean_choices(chosen: list[str], allowed: dict[str, str]) -> str:
    """Validated choices in the allowed order, comma-joined; unknown ones are refused."""
    for item in chosen:
        if item not in allowed:
            raise ValueError(f"Unknown choice: {item}")
    return ",".join(key for key in allowed if key in chosen)


def clean_keywords(text: str) -> str:
    """Trimmed, lower-cased, de-duplicated keywords, comma-joined."""
    if len(text) > MAX_KEYWORDS_LENGTH:
        raise ValueError(f"Keep keywords under {MAX_KEYWORDS_LENGTH} characters.")
    seen: list[str] = []
    for word in _split(text):
        lowered = word.lower()
        if lowered not in seen:
            seen.append(lowered)
    if len(seen) > MAX_KEYWORDS:
        raise ValueError(f"Use at most {MAX_KEYWORDS} keywords.")
    return ",".join(seen)


from dataclasses import dataclass  # noqa: E402


@dataclass(frozen=True)
class SyncRule:
    sports: str = ""
    ride_types: str = ""
    keywords: str = ""

    @property
    def is_empty(self) -> bool:
        return not (self.sports or self.ride_types or self.keywords)

    def matches(self, sport_type, ride_type, name) -> bool:
        return ride_matches(self.sports, self.ride_types, self.keywords, sport_type, ride_type, name)
