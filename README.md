# ambiguous_wall_time_utils

Detects naive ``datetime`` values that fall within a DST fall-back overlap and reports both possible UTC instant interpretations, given the pre- and post-transition UTC offsets.

## Usage

```python
from datetime import datetime, timedelta
from ambiguous_wall_time_utils import resolve_ambiguous, AmbiguityResult

# 01:30 local on 2023-11-05 in the US Eastern fall-back overlap.
local = datetime(2023, 11, 5, 1, 30, 0)
result = resolve_ambiguous(
    local,
    daylight_offset=timedelta(hours=-4),  # EDT, in effect before the transition
    standard_offset=timedelta(hours=-5),  # EST, in effect after
)

print(result.ambiguous)                  # True
print(result.pre_transition_utc)         # 2023-11-05 05:30:00+00:00
print(result.post_transition_utc)        # 2023-11-05 06:30:00+00:00
print(result.pre_transition_offset)      # -240  (minutes)
print(result.post_transition_offset)     # -300  (minutes)
```

The same values can also be built directly via ``AmbiguityResult.from_local``, which accepts ``None`` for either offset when only one interpretation is wanted.

## Why this exists

When clocks fall back at the end of Daylight Saving Time, a one-hour slice of local time repeats. A naive ``datetime`` stamped ``01:30`` on that day is genuinely ambiguous: it could refer to the first occurrence (under the daylight offset) or the second (under the standard offset). Code that blindly converts such a value to UTC silently picks one interpretation, and the wrong choice can mis-order logs, mis-bill a transaction, or mis-trigger a scheduled job.

The trade-off here is simplicity over completeness. The library does **not** ship a transition table for every IANA zone; instead, the caller supplies the two relevant UTC offsets. This keeps the implementation small, dependency-free, and deterministic, at the cost of requiring the caller to know when a fall-back occurs in the zone they care about. ``zoneinfo``-based transition lookups are deliberately out of scope.

## Edge you will hit

The resolver relies on you to pass the *correct* offset pair for the wall time in question. It does not validate that the naive datetime actually lies within a published DST transition for any specific zone; it only checks whether the two offsets you supply differ by a positive amount (the fall-back step). If you pass offsets that do not correspond to a real transition on that date, the result will still report ``ambiguous=True`` whenever the daylight offset is greater than the standard offset. The library treats offset pairs as authoritative, not calendar dates.

Naive ``fold`` is intentionally not consulted. Its behaviour across Python versions and datetime operations is inconsistent enough that relying on it would make the result non-deterministic across runtimes. Passing explicit offsets sidesteps that entirely.
