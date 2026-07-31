Tel Aviv bus dashboards
=======================

Two self-contained pages -- just open them in any browser, no server or install needed.
Keep both files in the same folder so the links between them work.

bunching-reasons.html
    Bus bunching by line, with every bunching event bucketed by cause: late departure /
    first 20% of the route / en route / origin outside the observed area. Planned vs
    effective gap (bunched buses counted as one arrival), planned vs actual passenger
    wait, Marey diagrams per line, filters by hour, city, operator and specific lines.
    Sample: 5 term-time weekdays (May 13, Jun 1, 2, 11, 14 -- 2026), ~100k tracked rides.

tlv-bus-speed.html
    Door-to-door bus speed on every street of Tel Aviv and the inner ring, by hour of
    day, measured from GPS pings of every bus. Includes the "bus-minutes lost" ranking
    that says where a bus lane would pay off.
    Sample: 10 weekdays (May-June 2026).

Method in one line: raw SIRI vehicle telemetry (Open Bus / hasadna.org.il) joined to the
GTFS timetable; positions ~once a minute per bus; each page documents its own method and
honest limits in the notes at the bottom.

Note: the "Grow the sample" button on the bunching page needs the original dashboard
server and will show a friendly error here -- everything else is fully interactive.
