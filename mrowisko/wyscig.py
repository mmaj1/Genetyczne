"""Krokowy wyścig metod na niezmiennej kopii tego samego problemu."""

from dataclasses import dataclass, field
import math
import time

import algorytmy as alg


@dataclass
class RaceLane:
    name: str
    path: tuple[int, ...] = ()
    tour: tuple[int, ...] | None = None
    length: float = math.inf
    compute_seconds: float = 0.0
    done: bool = False
    history: list = field(default_factory=list)


class AlgorithmRace:
    """Wspólny krok prezentacji nie jest jednostką czasu obliczeń ani pracy."""

    def __init__(self, points, blocked, *, iterations=100, seed=7, **params):
        if iterations < 1:
            raise ValueError('Liczba iteracji musi być dodatnia.')
        self.points = tuple(tuple(p) for p in points)
        self.blocked = frozenset(blocked)
        self.dist = alg.distance_matrix(self.points, self.blocked)
        self.iterations, self.seed, self.params = iterations, seed, dict(params)
        self.colony = alg.AntColony(self.dist, seed=seed, **params)
        self.lanes = {key: RaceLane(name) for key, name in
                      (('aco', 'ACO'), ('nn', 'Najbliższy sąsiad'), ('2opt', '2-opt'))}
        self.steps = 0
        self.optimum = None
        self.reference_seconds = 0.0
        if len(points) - 1 <= alg.BRUTE_FORCE_LIMIT:
            start = time.perf_counter()
            self.optimum = alg.tour_length(alg.brute_force(self.dist), self.dist)
            self.reference_seconds = time.perf_counter() - start
        self._runners = {'aco': self._aco(), 'nn': alg.greedy_tour_steps(self.dist),
                         '2opt': self._two_opt()}

    def _aco(self):
        for _ in range(self.iterations):
            self.colony.iterate()
            yield self.colony.best_tour or ()

    def _two_opt(self):
        for path in alg.greedy_tour_steps(self.dist):
            yield path
        yield from alg.two_opt_steps(self.dist, path)

    @property
    def done(self):
        return all(lane.done for lane in self.lanes.values())

    def gap(self, lane):
        if self.optimum is None or not math.isfinite(self.optimum) or not math.isfinite(lane.length):
            return None
        if self.optimum == 0:
            return 0.0 if lane.length == 0 else None
        return max(0.0, 100 * (lane.length / self.optimum - 1))

    def advance(self):
        if self.done:
            return
        self.steps += 1
        for key, lane in self.lanes.items():
            if not lane.done:
                start = time.perf_counter()
                try:
                    lane.path = tuple(next(self._runners[key]))
                except StopIteration:
                    lane.done = True
                lane.compute_seconds += time.perf_counter() - start
                if len(lane.path) == len(self.points):
                    length = alg.tour_length(lane.path, self.dist)
                    if math.isfinite(length):
                        lane.tour, lane.length = lane.path, length
                    if key == 'nn':
                        lane.done = True
                if key == 'aco' and self.colony.iteration >= self.iterations:
                    lane.done = True
            lane.history.append((self.steps, lane.length))
