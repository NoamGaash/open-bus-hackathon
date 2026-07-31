"""Tunable defaults for the whole package.

The numbers here are not arbitrary — most of them are dictated by limits of the public Stride API
that were measured against the live service (see
``docs/superpowers/specs/2026-07-30-bus-arrival-analysis-design.md``).
"""

from pathlib import Path
from zoneinfo import ZoneInfo

ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')

# The API rejects anything above this with "maximum limit per request is 15000 items".
MAX_SERVER_LIMIT = 15_000

# The API cancels queries past a 60s statement timeout. A whole day of GPS pings for one line
# exceeds it, so ping requests are chunked by ride id — measured at roughly 0.7s per ride.
RIDE_ID_CHUNK = 25

# A stop is considered visited only if the vehicle passed within this distance of it. Beyond it we
# assume a GPS gap or a skipped stop rather than an implausibly wide detour.
MAX_STOP_DISTANCE_M = 300.0

# Segments need several rides before a summary is worth plotting. Below this a segment is still
# shown, but marked as under-sampled rather than dropped - an invisible gap is worse than a flagged one.
DEFAULT_MIN_SAMPLES = 3

# Thresholds that decide whether a segment's number is trustworthy. All three are about the *method*
# rather than the traffic: how close the GPS got, how coarse the timing was, and whether the answer
# is physically believable.
#
# Beyond this closest-approach distance we cannot say the bus really served the stop.
TRUSTED_MATCH_DISTANCE_M = 150.0
# The gap between the two pings an arrival was interpolated from is that estimate's resolution.
# Past two minutes the derived time says little about a segment that is scheduled for one.
TRUSTED_RESOLUTION_S = 120.0
# Actual/planned ratios outside this band are almost always artifacts, not traffic.
PLAUSIBLE_RATIO_RANGE = (0.25, 4.0)
# Fraction of sampled rides that must yield a usable value before a segment counts as well covered.
TRUSTED_COVERAGE = 0.5

# Service hours worth analysing. Outside these there are too few rides to compare.
DEFAULT_HOUR_RANGE = (6, 21)

# Sampling caps that keep a run bounded. Defaults land at roughly 2-3 minutes per line.
DEFAULT_MAX_RIDES_PER_HOUR = 4
DEFAULT_MAX_RIDES = 200

# SIRI history is short - rides older than about a month return nothing at all - and the most
# recent days are still being ingested, so the default window ends a few days back.
DEFAULT_LAG_DAYS = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / 'output'
