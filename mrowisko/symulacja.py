"""Sesja symulacji niezależna od Pygame. Czas podawany jest w sekundach."""

from bisect import bisect_right
from dataclasses import dataclass
import math
import time

from algorytmy import AntColony, distance_matrix, tour_edges
from mrowisko.eksperyment import RoadClosure, finite, race_data, colony_data


@dataclass(frozen=True)
class AntState:
    index: int
    position: tuple[float, float]
    heading: float
    source: int
    destination: int
    probabilities: tuple[float, ...]
    visited: tuple[int, ...]
    step: int
    finished: bool
    trapped: bool


@dataclass(frozen=True)
class Improvement:
    previous: float
    current: float

    @property
    def percent(self):
        return 100 * (self.previous - self.current) / self.previous


class SimulationSession:
    """Steruje kolonią i odtwarzaniem jej rzeczywistych podróży.

    Jedna odległość odtwarzania daje wszystkim mrówkom tę samą prędkość.
    Wywołania update() w pauzie nie przesuwają żadnej mrówki.
    """

    def __init__(self, points, *, seed=None, **params):
        self.reset(points, seed=seed, **params)

    def reset(self, points, *, seed=None, blocked=(), **params):
        """Nowa plansza usuwa postęp, wybór mrówki i oczekujące podróże."""
        self.scenario = None
        self.points = [list(p) for p in points]
        self.blocked = {tuple(sorted(edge)) for edge in blocked}
        self.colony = AntColony(distance_matrix(points, self.blocked), seed=seed, **params)
        self.running = False
        self.followed = None
        self.journeys = None
        self.distance = 0.0
        self.paths = []
        self.completed = False
        self.improvement = None
        self.improvement_age = math.inf
        self.compute_seconds = 0.0
        self.seed = seed
        self.race = None
        self.race_mode = False
        self.race_elapsed = 0.0
        self.closure = None

    def start_race(self, *, iterations=100):
        from mrowisko.wyscig import AlgorithmRace
        c = self.colony
        self.race = AlgorithmRace(self.points, self.blocked, iterations=iterations,
                                  seed=self.seed if self.seed is not None else 7,
                                  n_ants=c.n_ants, alpha=c.alpha, beta=c.beta,
                                  rho=c.rho, q=c.q, elite=c.elite)
        self.race_mode = True
        self.race_elapsed = 0.0
        self.pause()

    def leave_race(self):
        self.race_mode = False
        self.pause()

    def experiment_data(self):
        """Niezależna kopia wyników do wykresów i eksportu, bez NaN/Infinity."""
        if self.race_mode and self.race:
            return race_data(self.race)
        if self.colony.history or self.closure:
            return colony_data(self)
        raise ValueError('Najpierw uruchom eksperyment.')

    def load_scenario(self, key, *, width=900, height=760):
        from mrowisko.scenariusze import SCENARIOS
        scenario = SCENARIOS[key]
        self.reset(scenario.board_points(width, height), seed=scenario.seed, **scenario.parameters)
        self.scenario = scenario

    def _begin(self):
        if self.journeys is not None and not self.completed:
            return
        self.completed = False
        start = time.perf_counter()
        self.journeys = self.colony.construct_journeys()
        self.compute_seconds += time.perf_counter() - start
        if self.followed is not None and self.followed >= len(self.journeys):
            self.followed = 0
        self.paths = []
        self.distance = 0.0
        for journey in self.journeys:
            cumulative = [0.0]
            for decision in journey.decisions:
                cumulative.append(cumulative[-1] + math.dist(
                    self.points[decision.source], self.points[decision.destination]))
            self.paths.append(cumulative)

    def follow(self, index):
        self._begin()
        if not 0 <= index < len(self.journeys):
            raise ValueError('Nie ma mrówki o tym numerze.')
        self.followed = index

    def play(self):
        self.running = True

    def pause(self):
        self.running = False

    def update(self, seconds, *, speed=240):
        self.improvement_age += max(0.0, seconds)
        if self.closure:
            self.closure.age += max(0, seconds)
            if self.closure.found_after is not None:
                self.closure.recovered_age += max(0, seconds)
        if self.race_mode:
            if self.running:
                self.race_elapsed += max(0, seconds) * max(0, speed) / 240
                while self.race_elapsed + 1e-12 >= .12 and not self.race.done:
                    self.race.advance()
                    self.race_elapsed = max(0, self.race_elapsed - .12)
                if self.race.done:
                    self.pause()
            return
        if self.running:
            self._begin()
            self._advance(self.distance + max(0.0, seconds) * max(0.0, speed))

    def _advance(self, distance):
        self.distance = min(distance, max(path[-1] for path in self.paths))
        if not self.completed and self.distance >= max(path[-1] for path in self.paths):
            previous = self.colony.best_length
            start = time.perf_counter()
            self.colony.update_pheromone([list(j.tour) for j in self.journeys if j.complete])
            self.compute_seconds += time.perf_counter() - start
            self._record_improvement(previous)
            self.completed = True

    def next_move(self):
        self.pause()
        self._begin()
        index = self.followed if self.followed is not None else 0
        self.followed = index
        cumulative = self.paths[index]
        step = bisect_right(cumulative, self.distance + 1e-8)
        target = cumulative[min(step, len(cumulative) - 1)]
        if target <= self.distance + 1e-8:
            target = max(path[-1] for path in self.paths)
        self._advance(target)

    def finish_iteration(self):
        """Dokańcza bieżącą rundę lub wykonuje jedną nową rundę."""
        self.pause()
        if self.race_mode:
            self.race.advance()
            return
        self._begin()
        self._advance(max(path[-1] for path in self.paths))

    def _record_improvement(self, previous):
        current = self.colony.best_length
        if math.isfinite(previous) and current < previous - 1e-9:
            self.improvement = Improvement(previous, current)
            self.improvement_age = 0.0
        if self.closure:
            self.closure.record(self.colony.iteration, current, self.compute_seconds)

    def iterate(self, count=1):
        """Szybkie pełne iteracje, bez odtwarzania podróży."""
        self.cancel_journeys()
        for _ in range(count):
            previous = self.colony.best_length
            start = time.perf_counter()
            self.colony.iterate()
            self.compute_seconds += time.perf_counter() - start
            self._record_improvement(previous)

    def cancel_journeys(self):
        """Odrzuca niezatwierdzoną iterację bez odkładania feromonu."""
        self.journeys = None
        self.paths = []
        self.distance = 0.0
        self.completed = False
        self.followed = None

    def toggle_block(self, edge):
        self.race = None
        self.race_mode = False
        edge = tuple(sorted(edge))
        adding = edge not in self.blocked
        c = self.colony
        closure = RoadClosure(edge, c.iteration, tuple(c.best_tour or ()), c.best_length,
                              tuple((i + 1, finite(v)) for i, v in enumerate(c.history)),
                              self.compute_seconds) if adding else None
        if edge in self.blocked:
            self.blocked.remove(edge)
        else:
            self.blocked.add(edge)
        self.cancel_journeys()
        self.improvement = None
        self.improvement_age = math.inf
        self.colony.set_distances(distance_matrix(self.points, self.blocked))
        self.closure = closure
        if closure:
            closure.record(c.iteration, c.best_length, self.compute_seconds)

    def block_best_route(self):
        """Zamyka najdłuższy odcinek najlepszej trasy; None, gdy brak trasy."""
        if not self.colony.best_tour:
            return None
        edge = max(sorted(tour_edges(self.colony.best_tour)),
                   key=lambda e: self.colony.dist[e[0], e[1]])
        self.toggle_block(edge)
        return edge

    @property
    def ants(self):
        if self.journeys is None:
            return ()
        result = []
        for index, (journey, cumulative) in enumerate(zip(self.journeys, self.paths)):
            step = min(bisect_right(cumulative, self.distance + 1e-8) - 1,
                       len(journey.decisions))
            finished = step == len(journey.decisions)
            if finished:
                point = 0 if journey.complete else journey.tour[-1]
                result.append(AntState(index, tuple(self.points[point]), 0, point, point,
                                       (), journey.tour, step, True, not journey.complete))
                continue
            decision = journey.decisions[step]
            a, b = self.points[decision.source], self.points[decision.destination]
            length = cumulative[step + 1] - cumulative[step]
            t = min(1, max(0, (self.distance - cumulative[step]) / max(length, 1e-12)))
            position = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            result.append(AntState(index, position, math.atan2(b[1] - a[1], b[0] - a[0]),
                                   decision.source, decision.destination, decision.probabilities,
                                   journey.tour[:step + 1], step, False, False))
        return tuple(result)
