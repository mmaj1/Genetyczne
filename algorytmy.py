"""Algorytmy rozwiązujące problem komiwojażera (TSP).

Punkt o indeksie 0 to mrowisko, pozostałe punkty to pożywienie.
Trasa to lista indeksów zaczynająca się od 0; powrót do mrowiska jest domyślny
(ostatni punkt łączy się z pierwszym).

Zawartość:
    - macierz odległości z obsługą zablokowanych ścieżek,
    - przegląd zupełny (brute force),
    - algorytm najbliższego sąsiada,
    - algorytm 2-opt,
    - algorytm mrówkowy (Ant System z wzmocnieniem najlepszej trasy).
"""

from dataclasses import dataclass

import itertools
import math
import time

import numpy as np

# Znacznik zablokowanej krawędzi; kolonia jawnie wyklucza ją z wyboru.
BLOCKED_PENALTY = 1e6

# Przegląd zupełny powyżej tej liczby punktów pożywienia trwałby zbyt długo.
BRUTE_FORCE_LIMIT = 10


def distance_matrix(points, blocked=()):
    """Zwraca macierz odległości euklidesowych między punktami.

    blocked - zbiór par (i, j) zablokowanych ścieżek (kolejność bez znaczenia).
    """
    pts = np.asarray(points, dtype=float)
    diff = pts[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    for i, j in blocked:
        dist[i, j] = dist[j, i] = BLOCKED_PENALTY
    return dist


def tour_length(tour, dist):
    """Długość zamkniętej trasy (z powrotem do punktu startowego)."""
    if not tour:
        return math.inf
    lengths = [dist[tour[k], tour[(k + 1) % len(tour)]] for k in range(len(tour))]
    return math.inf if any(d >= BLOCKED_PENALTY for d in lengths) else sum(lengths)


def tour_edges(tour):
    """Zbiór krawędzi trasy w postaci par (min, max)."""
    return {tuple(sorted((tour[k], tour[(k + 1) % len(tour)]))) for k in range(len(tour))}


def uses_blocked(tour, blocked):
    """Czy trasa przechodzi przez którąś z zablokowanych ścieżek."""
    blocked_set = {tuple(sorted(e)) for e in blocked}
    return bool(tour_edges(tour) & blocked_set)


@dataclass(frozen=True)
class Decision:
    """Wylosowany ruch i rozkład szans w momencie podjęcia decyzji."""
    source: int
    destination: int
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class Journey:
    """Ślad jednej mrówki; niepełna podróż oznacza utknięcie na blokadach."""
    tour: tuple[int, ...]
    decisions: tuple[Decision, ...]
    complete: bool


# ---------------------------------------------------------------------------
# Przegląd zupełny
# ---------------------------------------------------------------------------

def brute_force(dist):
    """Sprawdza wszystkie permutacje punktów pożywienia - wynik optymalny.

    Start jest zawsze w mrowisku (0). Trasy czytane w przeciwnym kierunku mają
    tę samą długość, więc rozważamy tylko permutacje, w których pierwszy
    odwiedzony punkt ma mniejszy indeks niż ostatni (o połowę mniej pracy).
    Złożoność: O(n!).
    """
    n = len(dist)
    if n <= 3:
        tour = list(range(n))
        return tour if math.isfinite(tour_length(tour, dist)) else None
    best_tour, best_len = None, math.inf
    for perm in itertools.permutations(range(1, n)):
        if perm[0] > perm[-1]:
            continue
        if dist[0, perm[0]] >= BLOCKED_PENALTY or dist[perm[-1], 0] >= BLOCKED_PENALTY:
            continue
        length = dist[0, perm[0]] + dist[perm[-1], 0]
        for a, b in zip(perm, perm[1:]):
            if dist[a, b] >= BLOCKED_PENALTY:
                break
            length += dist[a, b]
            if length >= best_len:
                break
        else:
            best_len, best_tour = length, [0, *perm]
    return best_tour


# ---------------------------------------------------------------------------
# Najbliższy sąsiad
# ---------------------------------------------------------------------------

def greedy_tour_steps(dist, start=0):
    """Heurystyka zachłanna: zawsze idź do najbliższego nieodwiedzonego punktu.

    Złożoność: O(n^2).
    """
    n = len(dist)
    tour = [start]
    yield list(tour)
    unvisited = set(range(n)) - {start}
    while unvisited:
        last = tour[-1]
        nxt = min(unvisited, key=lambda j: dist[last, j])
        tour.append(nxt)
        unvisited.remove(nxt)
        yield list(tour)


def _greedy_tour(dist, start=0):
    for tour in greedy_tour_steps(dist, start):
        pass
    return tour


def nearest_neighbor(dist, start=0):
    """Najbliższy sąsiad; None, jeżeli zachłanna trasa wpada na blokadę."""
    tour = _greedy_tour(dist, start)
    return tour if math.isfinite(tour_length(tour, dist)) else None


# ---------------------------------------------------------------------------
# 2-opt
# ---------------------------------------------------------------------------

def two_opt_steps(dist, tour=None):
    """Lokalne ulepszanie trasy: usuwa dwie krawędzie i łączy trasę na nowo.

    Jeśli zamiana krawędzi (a-b, c-d) na (a-c, b-d) skraca trasę, odwracamy
    fragment między b i c. Powtarzamy, dopóki istnieje poprawa.
    Trasą startową jest wynik algorytmu najbliższego sąsiada.
    """
    n = len(dist)
    tour = list(tour) if tour is not None else _greedy_tour(dist)
    yield list(tour)
    if n < 4:
        return
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            a, b = tour[i - 1], tour[i]
            for j in range(i + 1, n):
                c, d = tour[j], tour[(j + 1) % n]
                delta = dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
                if delta < -1e-9:
                    tour[i:j + 1] = reversed(tour[i:j + 1])
                    b = tour[i]
                    improved = True
                    yield list(tour)


def two_opt(dist, tour=None):
    """Końcowy wynik 2-opt; None, jeżeli nie uzyskano dopuszczalnej trasy."""
    for candidate in two_opt_steps(dist, tour):
        pass
    return candidate if math.isfinite(tour_length(candidate, dist)) else None


# ---------------------------------------------------------------------------
# Algorytm mrówkowy
# ---------------------------------------------------------------------------

class AntColony:
    """Algorytm mrówkowy dla problemu komiwojażera.

    Klasyfikacja: algorytmy inspirowane naturą -> inteligencja roju ->
    optymalizacja kolonią mrówek (ACO) -> Ant System ze strategią elitarną
    (Elitist Ant System, Dorigo i in. 1996).

    Reguła wyboru:  p_ij = tau_ij^alpha * eta_ij^beta / suma_l tau_il^alpha * eta_il^beta,
                    eta_ij = 1 / d_ij
    Aktualizacja:   tau_ij <- (1 - rho) * tau_ij + suma_k Q / L_k + e * Q / L_best

    Parametry:
        alpha    - waga feromonu w regule wyboru,
        beta     - waga widoczności (1 / odległość),
        rho      - współczynnik parowania feromonu (0..1),
        q        - ilość feromonu zostawiana przez mrówkę (dzielona przez długość trasy),
        n_ants   - liczba mrówek w jednej iteracji,
        elite    - dodatkowa waga feromonu na najlepszej dotąd trasie (0 = wyłączone).

    Obiekt działa krokowo: każde wywołanie iterate() to jedna iteracja, dzięki
    czemu interfejs może rysować postęp na bieżąco.
    """

    def __init__(self, dist, n_ants=20, alpha=1.0, beta=3.0, rho=0.3, q=1.0,
                 elite=1.0, seed=None):
        self.n_ants = n_ants
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.elite = elite
        self.rng = np.random.default_rng(seed)
        self.iteration = 0
        self.history = []  # najlepsza długość po każdej iteracji
        self.best_tour = None
        self.best_length = math.inf
        self.last_tours = []  # trasy mrówek z ostatniej iteracji
        self.set_distances(dist, reset_pheromone=True)

    def set_distances(self, dist, reset_pheromone=False):
        """Podmienia macierz odległości (np. po zablokowaniu ścieżki).

        Bez resetu feromonu kolonia zachowuje to, czego się już nauczyła, co
        pozwala badać, jak szybko znajduje trasę zastępczą.
        """
        self.dist = np.asarray(dist, dtype=float)
        n = len(self.dist)
        with np.errstate(divide="ignore"):
            self.eta = np.where(self.dist > 0, 1.0 / self.dist, 0.0)
        if reset_pheromone or not hasattr(self, "tau") or self.tau.shape != (n, n):
            # Początkowy feromon: odwrotność długości trasy najbliższego sąsiada.
            nn_len = tour_length(_greedy_tour(self.dist), self.dist)
            if not math.isfinite(nn_len):
                legal = self.dist[(self.dist > 0) & (self.dist < BLOCKED_PENALTY)]
                nn_len = n * float(legal.mean()) if legal.size else 1.0
            self.tau0 = 1.0 / max(n * nn_len, 1e-12) if n > 1 else 1.0
            self.tau = np.full((n, n), self.tau0)
        if self.best_tour is not None:
            # Najlepsza trasa mogła stracić ważność, więc liczymy ją od nowa.
            self.best_length = tour_length(self.best_tour, self.dist)
            if any(self.dist[a, b] >= BLOCKED_PENALTY for a, b in tour_edges(self.best_tour)):
                self.best_tour, self.best_length = None, math.inf

    def _weights(self):
        weights = (self.tau ** self.alpha) * (self.eta ** self.beta)
        weights[self.dist >= BLOCKED_PENALTY] = 0.0
        np.fill_diagonal(weights, 0.0)
        return weights

    def _probabilities(self, current, visited, weights):
        available = self.dist[current] < BLOCKED_PENALTY
        available = available.copy()
        available[[current, *visited]] = False
        w = np.where(available, weights[current], 0.0)
        total = w.sum()
        if total > 0:
            return w / total
        # Gdy wagi zanikną, losujemy tylko spośród dostępnych połączeń.
        count = available.sum()
        return available.astype(float) / count if count else np.zeros(len(w))

    def _construct_journey(self, weights, record=True):
        tour, decisions = [0], []
        for _ in range(len(self.dist) - 1):
            current = tour[-1]
            p = self._probabilities(current, tour, weights)
            if not p.any():
                return Journey(tuple(tour), tuple(decisions), False)
            nxt = int(np.searchsorted(np.cumsum(p), self.rng.random(), side="right"))
            if nxt >= len(p) or p[nxt] == 0:
                nxt = int(np.flatnonzero(p)[-1])
            if record:
                decisions.append(Decision(current, nxt, tuple(float(v) for v in p)))
            tour.append(nxt)
        complete = self.dist[tour[-1], 0] < BLOCKED_PENALTY
        if complete and record:
            decisions.append(Decision(tour[-1], 0, (1.0,) + (0.0,) * (len(self.dist) - 1)))
        return Journey(tuple(tour), tuple(decisions), complete)

    def probabilities(self, current, visited=()):
        """Prawdopodobieństwo wyboru każdego punktu przez mrówkę stojącą w `current`.

        Dokładnie reguła wyboru z budowy trasy:
            p(j) = tau[i,j]^alpha * eta[i,j]^beta / suma po nieodwiedzonych l.
        visited - punkty już odwiedzone (mają prawdopodobieństwo 0).
        """
        return self._probabilities(current, visited, self._weights())

    def construct_journeys(self):
        """Buduje podróże z niezmiennym zapisem rzeczywistych wyborów mrówek."""
        weights = self._weights()
        return [self._construct_journey(weights) for _ in range(self.n_ants)]

    def construct_tours(self):
        """Buduje trasy bez zapisu objaśnień (szybka ścieżka eksperymentów)."""
        weights = self._weights()
        journeys = [self._construct_journey(weights, record=False) for _ in range(self.n_ants)]
        return [list(j.tour) for j in journeys if j.complete]

    def iterate(self):
        """Wykonuje jedną iterację: budowa tras, parowanie, odkładanie feromonu."""
        n = len(self.dist)
        if n < 2:
            self.best_tour, self.best_length = list(range(n)), 0.0
            return self.best_tour
        return self.update_pheromone(self.construct_tours())

    def update_pheromone(self, tours):
        """Etap 2 iteracji: parowanie, odkładanie feromonu, wzmocnienie najlepszej trasy."""
        tours = [t for t in tours if len(t) == len(self.dist)
                 and all(self.dist[a, b] < BLOCKED_PENALTY for a, b in tour_edges(t))]
        lengths = [tour_length(t, self.dist) for t in tours]
        self.last_tours = tours

        if lengths:
            k = int(np.argmin(lengths))
            if lengths[k] < self.best_length:
                self.best_length, self.best_tour = lengths[k], tours[k]

        # Parowanie feromonu
        self.tau *= (1.0 - self.rho)
        # Każda mrówka zostawia feromon odwrotnie proporcjonalny do długości trasy
        for t, length in zip(tours, lengths):
            self._deposit(t, self.q / max(length, 1e-12))
        # Wzmocnienie najlepszej dotąd trasy (strategia elitarna)
        if self.elite > 0 and self.best_tour is not None:
            self._deposit(self.best_tour, self.elite * self.q / max(self.best_length, 1e-12))
        # Dolne ograniczenie, żeby żadna ścieżka nie zniknęła zupełnie
        np.maximum(self.tau, self.tau0 * 1e-3, out=self.tau)

        self.iteration += 1
        self.history.append(self.best_length)
        return self.best_tour

    def _deposit(self, tour, amount):
        a = np.asarray(tour)
        b = np.roll(a, -1)
        self.tau[a, b] += amount
        self.tau[b, a] += amount

    def run(self, iterations):
        for _ in range(iterations):
            self.iterate()
        return self.best_tour


def aco(dist, iterations=100, seed=None, **params):
    """Wygodna funkcja: uruchamia algorytm mrówkowy i zwraca najlepszą trasę."""
    return AntColony(dist, seed=seed, **params).run(iterations)


def timed(func, *args, **kwargs):
    """Uruchamia funkcję i zwraca (wynik, czas w sekundach)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    return result, time.perf_counter() - start
