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

import itertools
import math
import time

import numpy as np

# Długość "zablokowanej" krawędzi. Jest tak duża, że każdy algorytm jej unika,
# a jednocześnie skończona, więc obliczenia nie dają nieskończoności.
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
    return sum(dist[tour[k], tour[(k + 1) % len(tour)]] for k in range(len(tour)))


def tour_edges(tour):
    """Zbiór krawędzi trasy w postaci par (min, max)."""
    return {tuple(sorted((tour[k], tour[(k + 1) % len(tour)]))) for k in range(len(tour))}


def uses_blocked(tour, blocked):
    """Czy trasa przechodzi przez którąś z zablokowanych ścieżek."""
    blocked_set = {tuple(sorted(e)) for e in blocked}
    return bool(tour_edges(tour) & blocked_set)


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
        return list(range(n))
    best_tour, best_len = None, math.inf
    for perm in itertools.permutations(range(1, n)):
        if perm[0] > perm[-1]:
            continue
        length = dist[0, perm[0]] + dist[perm[-1], 0]
        for a, b in zip(perm, perm[1:]):
            length += dist[a, b]
            if length >= best_len:
                break
        else:
            best_len, best_tour = length, [0, *perm]
    return best_tour


# ---------------------------------------------------------------------------
# Najbliższy sąsiad
# ---------------------------------------------------------------------------

def nearest_neighbor(dist, start=0):
    """Heurystyka zachłanna: zawsze idź do najbliższego nieodwiedzonego punktu.

    Złożoność: O(n^2).
    """
    n = len(dist)
    tour = [start]
    unvisited = set(range(n)) - {start}
    while unvisited:
        last = tour[-1]
        nxt = min(unvisited, key=lambda j: dist[last, j])
        tour.append(nxt)
        unvisited.remove(nxt)
    return tour


# ---------------------------------------------------------------------------
# 2-opt
# ---------------------------------------------------------------------------

def two_opt(dist, tour=None):
    """Lokalne ulepszanie trasy: usuwa dwie krawędzie i łączy trasę na nowo.

    Jeśli zamiana krawędzi (a-b, c-d) na (a-c, b-d) skraca trasę, odwracamy
    fragment między b i c. Powtarzamy, dopóki istnieje poprawa.
    Trasą startową jest wynik algorytmu najbliższego sąsiada.
    """
    n = len(dist)
    tour = list(tour) if tour is not None else nearest_neighbor(dist)
    if n < 4:
        return tour
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
    return tour


# ---------------------------------------------------------------------------
# Algorytm mrówkowy
# ---------------------------------------------------------------------------

class AntColony:
    """Algorytm mrówkowy (Ant System) dla problemu komiwojażera.

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
            nn_len = tour_length(nearest_neighbor(self.dist), self.dist)
            self.tau0 = 1.0 / (n * nn_len) if n > 1 else 1.0
            self.tau = np.full((n, n), self.tau0)
        if self.best_tour is not None:
            # Najlepsza trasa mogła stracić ważność, więc liczymy ją od nowa.
            self.best_length = tour_length(self.best_tour, self.dist)

    def _construct_tour(self, weights):
        n = len(self.dist)
        tour = [0]
        visited = np.zeros(n, dtype=bool)
        visited[0] = True
        current = 0
        for _ in range(n - 1):
            w = weights[current] * ~visited
            total = w.sum()
            if total <= 0:
                # Wszystkie wagi zerowe - wybór losowy spośród nieodwiedzonych.
                choices = np.flatnonzero(~visited)
                nxt = int(self.rng.choice(choices))
            else:
                # Reguła ruletki: p(j) = w(j) / suma w
                nxt = int(np.searchsorted(np.cumsum(w), self.rng.random() * total))
                nxt = min(nxt, n - 1)
                if visited[nxt]:
                    nxt = int(np.flatnonzero(~visited)[0])
            tour.append(nxt)
            visited[nxt] = True
            current = nxt
        return tour

    def iterate(self):
        """Wykonuje jedną iterację: budowa tras, parowanie, odkładanie feromonu."""
        n = len(self.dist)
        if n < 2:
            self.best_tour, self.best_length = list(range(n)), 0.0
            return self.best_tour
        weights = (self.tau ** self.alpha) * (self.eta ** self.beta)
        tours = [self._construct_tour(weights) for _ in range(self.n_ants)]
        lengths = [tour_length(t, self.dist) for t in tours]

        k = int(np.argmin(lengths))
        if lengths[k] < self.best_length:
            self.best_length, self.best_tour = lengths[k], tours[k]

        # Parowanie feromonu
        self.tau *= (1.0 - self.rho)
        # Każda mrówka zostawia feromon odwrotnie proporcjonalny do długości trasy
        for t, length in zip(tours, lengths):
            self._deposit(t, self.q / length)
        # Wzmocnienie najlepszej dotąd trasy (strategia elitarna)
        if self.elite > 0 and self.best_tour is not None:
            self._deposit(self.best_tour, self.elite * self.q / self.best_length)
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
