# Planned vs. Actual Rides — "Worked example service by operator"

**Author:** example (`author="example"` in the registry)
**Code:** [analyses/example_service_by_operator.py](../analyses/example_service_by_operator.py)
**Cards:** `service-by-operator` ("Planned vs actual rides")
**Data:** Stride `/gtfs_rides_agg/group_by` (planned) vs. `/rides_execution/list` (actual)

## What it answers

- **How many scheduled rides actually ran?** Displays the daily volume of planned rides compared to observed runs for a chosen operator.

## Algorithm

1. **Window Setup:** Sets a recent date range based on user inputs.
2. **Fetch Planned Rollups:** `/gtfs_rides_agg/group_by` retrieves the count of scheduled departures for the operator over the selected days.
3. **Fetch Actual Rollups:** Bypasses `/gtfs_rides_agg`'s actual column (known to be broken) and counts the non-null `actual_start_time` rows through `/rides_execution/list`.
4. **Aggregate and Render:** Builds a comparative pandas DataFrame and exports it to a standard Recharts double-bar chart.

## Reasoning

This module was written as the foundational **worked example** for the hackathon repository. Its primary purpose was not to discover new transit insights, but to provide a clear, simple developer quickstart demonstrating how the `@analysis` registry, the FastAPI backend, and the React frontend contract tie together.

## Findings

### 1. Simple worked examples are critical for developer onboarding — **confidence: High**
Providing a fully functional, minimal template allowed developers with varying backgrounds (data science, frontend, backend) to immediately scaffold and register 17 distinct analyses within 2 days of hacking without encountering wiring issues.

## Criticism

**Sells aggregate analysis short.** Because it was written as a simple, high-level example, it lacks the geographic, stop-sequence, and temporal filters needed to diagnose *why* service was missed. It is a necessary developer scaffold but has low diagnostic value compared to the specialized segment and headway analyses.
