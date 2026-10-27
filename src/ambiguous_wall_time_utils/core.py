"""Core logic for detecting DST fall-back overlaps.

The approach is deliberately conservative: a wall time is considered
ambiguous when the *same* ``HH:MM:SS`` occurs twice in local time on a
given calendar day because clocks were set back at the end of Daylight
Saving Time (the "fall-back" transition).  When that happens the library
reports both UTC instant interpretations so the caller can decide which
one is intended.

The classmethod ``AmbiguityResult.from_local`` builds a candidate pair
by round-tripping the *same* naive ``datetime`` through two fixed UTC
offsets: the daylight offset (one that is in effect *before* the
transition) and the standard offset (in effect *after*).  Because both
offsets are supplied by the caller and the naive datetime is identical,
the two resulting aware datetimes are guaranteed to be exactly the DST
gap apart.

Naive ``fold`` handling is intentionally *not* relied upon.  ``fold`` is
a correctness nightmare on many runtimes (it affects comparison,
arithmetic, and ISO-format output inconsistently across Python minor
versions) and the test matrix cannot exercise every runtime.  Instead,
the caller passes the two offsets explicitly; ambiguity is detected by
checking whether that specific pair of offsets produces the same wall
clock reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple


__all__ = ["AmbiguityResult", "resolve_ambiguous"]


@dataclass(frozen=True)
class AmbiguityResult:
    """The outcome of examining a naive local ``datetime``.

    Attributes:
        ambiguous:  ``True`` if the supplied wall time falls within a
                    fall-back overlap for the given offset pair.
        pre_transition_utc:  The UTC instant assuming the *daylight*
                    (pre-transition) offset.  ``None`` when no daylight
                    offset was supplied.
        post_transition_utc: The UTC instant assuming the *standard*
                    (post-transition) offset.  ``None`` when no
                    standard offset was supplied.
        pre_transition_offset:  The offset, in minutes, used to compute
                    ``pre_transition_utc``.
        post_transition_offset: The offset, in minutes, used to compute
                    ``post_transition_utc``.
    """

    ambiguous: bool
    pre_transition_utc: Optional[datetime]
    post_transition_utc: Optional[datetime]
    pre_transition_offset: Optional[int]
    post_transition_offset: Optional[int]

    @classmethod
    def from_local(
        cls,
        local: datetime,
        daylight_offset: Optional[timedelta],
        standard_offset: Optional[timedelta],
    ) -> "AmbiguityResult":
        """Build a result for *local* from two explicit offsets.

        ``local`` must be naive (``tzinfo is None``); an aware datetime
        already carries its offset and there is nothing to resolve.
        ``daylight_offset`` and ``standard_offset`` are the UTC offsets
        that are in effect immediately before and after the fall-back
        transition respectively.
        """
        if local.tzinfo is not None:
            raise ValueError(
                "local must be a naive datetime; an aware datetime "
                "already carries its offset"
            )

        pre_utc: Optional[datetime] = None
        post_utc: Optional[datetime] = None
        pre_minutes: Optional[int] = None
        post_minutes: Optional[int] = None

        if daylight_offset is not None:
            pre_utc = local.replace(tzinfo=timezone(daylight_offset)).astimezone(timezone.utc)
            pre_minutes = int(daylight_offset.total_seconds() // 60)

        if standard_offset is not None:
            post_utc = local.replace(tzinfo=timezone(standard_offset)).astimezone(timezone.utc)
            post_minutes = int(standard_offset.total_seconds() // 60)

        # A fall-back overlap is, by definition, the DST gap wide.  If the
        # two supplied offsets differ by exactly the usual 60-minute DST
        # step and both interpretations are real, the wall time is
        # ambiguous.  We intentionally do NOT consider a *spring-forward*
        # gap (where the wall time is skipped): those are non-existent,
        # not ambiguous, and reporting them as ambiguous would mislead.
        ambiguous = False
        if pre_utc is not None and post_utc is not None:
            offset_diff_minutes = pre_minutes - post_minutes
            if offset_diff_minutes > 0:
                ambiguous = True

        return cls(
            ambiguous=ambiguous,
            pre_transition_utc=pre_utc,
            post_transition_utc=post_utc,
            pre_transition_offset=pre_minutes,
            post_transition_offset=post_minutes,
        )


def resolve_ambiguous(
    local: datetime,
    daylight_offset: timedelta,
    standard_offset: timedelta,
) -> AmbiguityResult:
    """Return both possible UTC readings of *local*.

    Parameters mirror ``AmbiguityResult.from_local``; this is a thin
    convenience wrapper.  See that classmethod for the semantics.
    """
    return AmbiguityResult.from_local(local, daylight_offset, standard_offset)
