# Judge Demo Script

## One-Line Pitch

Company shuttles run on fixed timetables, so employees still wait and vehicles still run half-empty. This MVP turns campus commuting into an on-demand pooled system that batches rider requests, assigns vans dynamically, and shows live ETAs to both employees and transport teams.

## Demo Setup

- Start the FastAPI backend and React frontend.
- Open `/rider` in one browser tab.
- Open `/ops` in another browser tab.
- If you want a clean slate first, use `Reset demo` on the operations page.

## Recommended Demo Flow

1. Show the rider screen.
   Explain that commuters pick a predefined pickup zone, choose the campus destination, and request an arrival time for the morning commute.

2. Submit one manual ride request.
   Highlight the estimated pickup time and the rider status card.

3. Switch to the operations dashboard.
   Show the demand queue and explain that requests can be batched every 1 to 2 minutes rather than forcing employees to wait for a fixed shuttle schedule.

4. Click `Load morning rush`.
   This seeds six rider requests across multiple pickup zones and immediately dispatches pooled vans.

5. Walk through the map.
   Point out the pickup zones, route lines, destination stops, and live van positions.

6. Call out the metrics.
   Focus on:
   - Active requests
   - Matched riders
   - Occupancy rate
   - Wait time saved vs. fixed schedules

7. Open an active route card.
   Explain how multiple nearby riders heading to the same campus are grouped into one van and given a shared route.

8. Return to the rider screen.
   Show the assigned van, pickup ETA, route progress, and trip state updates.

## What Judges Should Remember

- It solves a repeated daily pain point for corporate commuters.
- The MVP proves demand-responsive pooling with a simple, explainable heuristic.
- The dispatcher view makes operational savings visible, not just rider convenience.
- The product can expand later to multi-campus scheduling, richer routing, and driver navigation.

## Backup Demo Path

If the live manual flow is slow, use this sequence:

1. Reset demo.
2. Load morning rush.
3. Go straight to the operations dashboard map and metrics.
4. Open the rider tab to show one already-matched rider and ETA updates.
