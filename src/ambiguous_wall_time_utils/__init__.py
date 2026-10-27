# ambiguous_wall_time_utils
#
# Exposes the public API surface of the library at the package level so that
# callers can do:
#
#     from ambiguous_wall_time_utils import resolve_ambiguous, AmbiguityResult
#
# rather than reaching into submodules.  Keeping the re-export explicit here
# means the internal module layout can change without breaking downstream code.

from .core import resolve_ambiguous, AmbiguityResult

__all__ = ["resolve_ambiguous", "AmbiguityResult"]
