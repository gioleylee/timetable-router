from random import Random
from unittest import TestCase

from router import Connection, Timetable, format_time, parse_time


def exhaustive(connections, stop, goal, time, transfer, previous_trip=None):
    if stop == goal:
        return time
    candidates = []
    for edge in connections:
        buffer = 0 if previous_trip in (None, edge.trip) else transfer
        if edge.origin == stop and edge.depart >= time + buffer:
            arrival = exhaustive(connections, edge.destination, goal, edge.arrive, transfer, edge.trip)
            if arrival is not None:
                candidates.append(arrival)
    return min(candidates, default=None)


class RouterTests(TestCase):
    def test_transfer_buffer_does_not_apply_when_staying_on_trip(self):
        first = Connection("local", "A", "B", 0, 10)
        second = Connection("local", "B", "C", 11, 20)
        express = Connection("express", "B", "C", 12, 17)
        schedule = Timetable([first, second, express])
        self.assertEqual(schedule.route("A", "C", 0, transfer=2), [first, express])
        self.assertEqual(schedule.route("A", "C", 0, transfer=3), [first, second])
        self.assertIsNone(schedule.route("A", "C", 1))

    def test_past_midnight_and_invalid_trip(self):
        self.assertEqual(format_time(parse_time("25:03")), "25:03")
        with self.assertRaises(ValueError):
            parse_time("24:60")
        with self.assertRaisesRegex(ValueError, "continuous"):
            Timetable([Connection("x", "A", "B", 0, 1), Connection("x", "C", "D", 2, 3)])

    def test_matches_exhaustive_search_on_random_small_schedules(self):
        rng = Random(42)
        for trial in range(150):
            connections = []
            for trip in range(6):
                stops = rng.sample("ABCD", 3)
                start = rng.randrange(10)
                middle = start + rng.randint(1, 5)
                connections += [
                    Connection(str(trip), stops[0], stops[1], start, middle),
                    Connection(str(trip), stops[1], stops[2], middle, middle + rng.randint(1, 5)),
                ]
            origin, goal = rng.sample("ABCD", 2)
            departure, buffer = rng.randrange(5), rng.randrange(4)
            timetable = Timetable(connections)
            if origin not in timetable.stops or goal not in timetable.stops:
                continue
            with self.subTest(trial=trial):
                itinerary = timetable.route(origin, goal, departure, buffer)
                self.assertEqual(itinerary[-1].arrive if itinerary else None,
                                 exhaustive(connections, origin, goal, departure, buffer))
