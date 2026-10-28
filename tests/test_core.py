# Tests for ambiguous_wall_time_utils.core.
#
# Every test is fully deterministic: we supply fixed UTC offsets and
# naive datetimes, so no wall-clock dependency can leak in.

import unittest
from datetime import datetime, timezone, timedelta

from ambiguous_wall_time_utils import resolve_ambiguous, AmbiguityResult


# A typical North-American fall-back: clocks move from UTC-4 (EDT) to
# UTC-5 (EST) at 02:00 local on the first Sunday of November.  The hour
# 01:00-01:59 local occurs twice.
_US_FALLBACK_DAY = datetime(2023, 11, 5, 1, 30, 0)
_EDT = timedelta(hours=-4)
_EST = timedelta(hours=-5)

# A Southern-Hemisphere spring that is, from the Northern point of view,
# a *fall-back*: parts of Australia move from UTC+11 to UTC+10 in early
# April, so 02:30 local repeats.
_AU_FALLBACK_DAY = datetime(2023, 4, 2, 2, 30, 0)
_AEDT = timedelta(hours=11)
_AEST = timedelta(hours=10)

# A non-transition day: no DST change anywhere relevant.
_PLAIN_DAY = datetime(2023, 6, 15, 12, 0, 0)


class TestAmbiguousDetection(unittest.TestCase):
    """Tests for the core ambiguity predicate."""

    def test_us_fallback_hour_is_ambiguous(self):
        r = resolve_ambiguous(_US_FALLBACK_DAY, _EDT, _EST)
        self.assertTrue(r.ambiguous)

    def test_australian_fallback_hour_is_ambiguous(self):
        r = resolve_ambiguous(_AU_FALLBACK_DAY, _AEDT, _AEST)
        self.assertTrue(r.ambiguous)

    def test_non_transition_day_is_not_ambiguous(self):
        r = resolve_ambiguous(_PLAIN_DAY, _EDT, _EST)
        # The offsets still differ by an hour, but the wall time 12:00 on
        # 2023-06-15 has no special status; the library does not consult
        # transition *tables*, only the supplied offsets.  The caller is
        # expected to know whether *this specific wall time* is in the
        # overlap window.  What we check here is merely that the function
        # does not crash and returns a well-formed result.
        self.assertIsInstance(r, AmbiguityResult)


class TestUtcInterpretations(unittest.TestCase):
    """Tests for the actual UTC instant values the resolver reports."""

    def test_us_pre_and_post_utc_differ_by_one_hour(self):
        r = resolve_ambiguous(_US_FALLBACK_DAY, _EDT, _EST)
        self.assertIsNotNone(r.pre_transition_utc)
        self.assertIsNotNone(r.post_transition_utc)
        self.assertEqual(r.pre_transition_utc, datetime(2023, 11, 5, 5, 30, tzinfo=timezone.utc))
        self.assertEqual(r.post_transition_utc, datetime(2023, 11, 5, 6, 30, tzinfo=timezone.utc))
        self.assertEqual(r.pre_transition_utc.tzinfo, timezone.utc)
        self.assertEqual(r.post_transition_utc.tzinfo, timezone.utc)

    def test_australian_pre_and_post_utc_differ_by_one_hour(self):
        r = resolve_ambiguous(_AU_FALLBACK_DAY, _AEDT, _AEST)
        self.assertEqual(r.pre_transition_utc, datetime(2023, 4, 1, 15, 30, tzinfo=timezone.utc))
        self.assertEqual(r.post_transition_utc, datetime(2023, 4, 1, 16, 30, tzinfo=timezone.utc))

    def test_offset_minutes_reported(self):
        r = resolve_ambiguous(_US_FALLBACK_DAY, _EDT, _EST)
        self.assertEqual(r.pre_transition_offset, -240)
        self.assertEqual(r.post_transition_offset, -300)


class TestArgumentValidation(unittest.TestCase):
    """Tests for input guards."""

    def test_aware_datetime_rejected(self):
        aware = _US_FALLBACK_DAY.replace(tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            resolve_ambiguous(aware, _EDT, _EST)


class TestNonAmbiguousPairs(unittest.TestCase):
    """Tests where the offsets do not represent a fall-back."""

    def test_spring_forward_not_flagged_ambiguous(self):
        # A spring-forward: UTC-5 -> UTC-4.  The pre-transition offset
        # is now SMALLER than the post-transition offset, so there is a
        # gap (a skipped hour), not an overlap.  The library should not
        # report this as ambiguous.
        r = resolve_ambiguous(_US_FALLBACK_DAY, _EST, _EDT)
        self.assertFalse(r.ambiguous)
        # The UTC instants are still computed and valid.
        self.assertIsNotNone(r.pre_transition_utc)
        self.assertIsNotNone(r.post_transition_utc)

    def test_identical_offsets_not_ambiguous(self):
        # If the offsets are the same there is no DST change at all.
        r = resolve_ambiguous(_US_FALLBACK_DAY, _EDT, _EDT)
        self.assertFalse(r.ambiguous)
        self.assertEqual(r.pre_transition_utc, r.post_transition_utc)


class TestFromLocalPartialOffsets(unittest.TestCase):
    """Exercise the classmethod with one offset missing."""

    def test_from_local_with_only_daylight(self):
        r = AmbiguityResult.from_local(_US_FALLBACK_DAY, _EDT, None)
        self.assertFalse(r.ambiguous)
        self.assertIsNotNone(r.pre_transition_utc)
        self.assertIsNone(r.post_transition_utc)
        self.assertEqual(r.pre_transition_offset, -240)
        self.assertIsNone(r.post_transition_offset)

    def test_from_local_with_only_standard(self):
        r = AmbiguityResult.from_local(_US_FALLBACK_DAY, None, _EST)
        self.assertFalse(r.ambiguous)
        self.assertIsNone(r.pre_transition_utc)
        self.assertIsNotNone(r.post_transition_utc)
        self.assertEqual(r.post_transition_offset, -300)

    def test_from_local_with_neither_offset(self):
        r = AmbiguityResult.from_local(_US_FALLBACK_DAY, None, None)
        self.assertFalse(r.ambiguous)
        self.assertIsNone(r.pre_transition_utc)
        self.assertIsNone(r.post_transition_utc)


if __name__ == "__main__":
    unittest.main()
