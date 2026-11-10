"""Find an earliest-arrival itinerary over a single service-day timetable."""

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


def parse_time(value):
    fields = value.split(":")
    if len(fields) != 2 or any(not field.isascii() or not field.isdecimal() for field in fields):
        raise ValueError(f"invalid service time {value!r}; use HH:MM")
    hour, minute = map(int, fields)
    if minute >= 60 or len(fields[1]) != 2:
        raise ValueError(f"invalid service time {value!r}; use HH:MM")
    return hour * 60 + minute


def format_time(minutes):
    hours, remainder = divmod(minutes, 60)
    return f"{hours:02}:{remainder:02}"


@dataclass(frozen=True, slots=True)
class Connection:
    trip: str
    origin: str
    destination: str
    depart: int
    arrive: int


@dataclass(frozen=True, slots=True)
class Leg:
    connection: Connection
    previous: "Leg | None"


def load_connections(path):
    fields = {"trip", "origin", "destination", "depart", "arrive"}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, strict=True)
        if set(rows.fieldnames or []) != fields or len(rows.fieldnames) != len(fields):
            raise ValueError("expected columns trip, origin, destination, depart, arrive")
        connections = []
        for row in rows:
            if set(row) != fields or any(not value for value in row.values()):
                raise ValueError(f"line {rows.line_num}: expected five nonempty fields")
            connections.append(Connection(
                row["trip"], row["origin"], row["destination"],
                parse_time(row["depart"]), parse_time(row["arrive"]),
            ))
        return connections


class Timetable:
    def __init__(self, connections):
        self.connections = sorted(connections, key=lambda connection: connection.depart)
        self.stops = set()
        previous = {}
        for edge in self.connections:
            if edge.arrive <= edge.depart:
                raise ValueError(f"trip {edge.trip}: each leg must take positive time")
            predecessor = previous.get(edge.trip)
            if predecessor and (predecessor.destination != edge.origin or predecessor.arrive > edge.depart):
                raise ValueError(f"trip {edge.trip}: legs must form a continuous, nonoverlapping sequence")
            previous[edge.trip] = edge
            self.stops.update((edge.origin, edge.destination))

    def route(self, origin, destination, start, transfer=0):
        if origin not in self.stops or destination not in self.stops:
            raise ValueError("origin and destination must be known stops")
        if transfer < 0:
            raise ValueError("transfer time must be nonnegative")
        if origin == destination:
            return []
        arrival = {origin: start}
        paths = {}
        onboard = {}
        for edge in self.connections:
            if edge.depart < start:
                continue
            if destination in arrival and edge.depart >= arrival[destination]:
                break
            if edge.trip in onboard:
                previous = onboard[edge.trip]
            else:
                ready = arrival.get(edge.origin)
                buffer = 0 if edge.origin == origin else transfer
                if ready is None or ready + buffer > edge.depart:
                    continue
                previous = paths.get(edge.origin)
            current = Leg(edge, previous)
            onboard[edge.trip] = current
            if edge.destination not in arrival or edge.arrive < arrival[edge.destination]:
                arrival[edge.destination] = edge.arrive
                paths[edge.destination] = current
        if destination not in paths:
            return None
        legs = []
        current = paths[destination]
        while current is not None:
            legs.append(current.connection)
            current = current.previous
        return list(reversed(legs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timetable", type=Path)
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("--at", required=True)
    parser.add_argument("--transfer", type=int, default=0, metavar="MINUTES")
    args = parser.parse_args()
    try:
        start = parse_time(args.at)
        path = Timetable(load_connections(args.timetable)).route(
            args.origin, args.destination, start, args.transfer
        )
    except (ValueError, OSError, csv.Error) as error:
        parser.error(str(error))
    if path is None:
        print(json.dumps({"reachable": False}))
        return 1
    legs = [asdict(leg) | {"depart": format_time(leg.depart), "arrive": format_time(leg.arrive)} for leg in path]
    print(json.dumps({
        "reachable": True,
        "arrival": format_time(path[-1].arrive if path else start),
        "legs": legs,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
