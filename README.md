# Timetable Router

Find the earliest arrival over a schedule of fixed departures. The router handles overnight service times, trips that overtake each other, and transfer buffers that apply only when changing vehicles.

```sh
python router.py example.csv Harbor Airport --at 23:40 --transfer 5
python -m unittest -v
```

The included fixture arrives at `24:33` (00:33 the next day). With a three-minute buffer, the earlier express is reachable and arrives at `24:26`. Use Python 3.11 or newer.

## Input and output

Each CSV row has a trip ID, origin, destination, departure, and arrival. A trip ID identifies one vehicle run. Its legs must form a continuous sequence with positive travel times. Use service-day times, so `25:10` represents 01:10 on the next day. The CLI prints a JSON itinerary and uses exit status 1 when there is no route. The model covers one service day with a uniform transfer buffer and exact stop matches.

## How the scan works

The timetable sorts legs by departure. A leg is reachable when the traveler can board after the transfer buffer or is already on that vehicle. The algorithm retains the earliest arrival at each stop and the reachable path aboard each trip. The separate trip state preserves rides through a connection even when the earliest arrival at an intermediate stop came from a different vehicle.

Positive leg durations guarantee that a later-scanned departure cannot enable boarding a leg already processed. The query can end when the next departure is at or after the best arrival at the destination. Construction is O(C log C) for C connections, and each query is O(C) in the worst case. Itinerary links share predecessor objects and can use O(C) memory.

The test suite compares the scan against exhaustive enumeration on 150 seeded small timetables. A separate fixture tests a missed transfer and an uninterrupted ride on the same vehicle.
