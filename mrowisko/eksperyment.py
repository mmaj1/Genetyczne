"""Zapis obserwacji eksperymentu, niezależny od interfejsu i wykresów."""

from dataclasses import dataclass, field
import math


def finite(value):
    return float(value) if math.isfinite(value) else None


@dataclass
class RoadClosure:
    edge: tuple[int, int]
    iteration: int
    old_tour: tuple[int, ...]
    old_length: float
    before: tuple
    started_compute: float
    after: list = field(default_factory=list)
    found_after: int | None = None
    attempts: int = 0
    recovery_seconds: float | None = None
    age: float = 0.0
    recovered_age: float = 0.0

    def record(self, iteration, length, compute_seconds):
        self.attempts = iteration - self.iteration
        self.after.append((iteration, finite(length)))
        if self.found_after is None and math.isfinite(length):
            self.found_after = self.attempts
            self.recovery_seconds = compute_seconds - self.started_compute


def race_data(race):
    return dict(
        kind='race', complete=race.done, points=[list(p) for p in race.points],
        blocked=[list(e) for e in sorted(race.blocked)], seed=race.seed, params=dict(race.params),
        steps=race.steps, aco_iterations=race.colony.iteration, budget=race.iterations,
        optimum=finite(race.optimum) if race.optimum is not None else None,
        optimum_known=race.optimum is not None, reference_seconds=race.reference_seconds,
        aco_history=[[i + 1, finite(v)] for i, v in enumerate(race.colony.history)],
        results=[dict(key=key, name=lane.name, length=finite(lane.length),
                      seconds=lane.compute_seconds, gap=race.gap(lane), done=lane.done,
                      tour=list(lane.tour) if lane.tour is not None else None,
                      history=[[step, finite(v)] for step, v in lane.history])
                 for key, lane in race.lanes.items()])


def colony_data(session):
    c = session.colony
    data = dict(kind='colony', complete=False, points=[list(p) for p in session.points],
                blocked=[list(e) for e in sorted(session.blocked)], seed=session.seed,
                params=dict(n_ants=c.n_ants, alpha=c.alpha, beta=c.beta, rho=c.rho, q=c.q, elite=c.elite),
                current_iteration=c.iteration, length=finite(c.best_length),
                tour=list(c.best_tour) if c.best_tour is not None else [],
                compute_seconds=session.compute_seconds,
                history=[[i + 1, finite(v)] for i, v in enumerate(c.history)])
    if session.closure:
        closure = session.closure
        data.update(kind='closure', complete=closure.found_after is not None,
                    edge=list(closure.edge), iteration_closed=closure.iteration,
                    before=[list(v) for v in closure.before], after=[list(v) for v in closure.after],
                    found_after=closure.found_after, attempts=closure.attempts,
                    recovery_seconds=closure.recovery_seconds, old_length=finite(closure.old_length),
                    old_tour=list(closure.old_tour))
    return data
