"""Interaktywna wizualizacja algorytmu mrówkowego dla problemu komiwojażera.

Uruchomienie:
    python aplikacja.py          # pełny ekran
    python aplikacja.py --okno   # w oknie zamiast na pełnym ekranie

Obsługa (szczegóły w README.md):
    LPM na planszy    - dodaj punkt z pożywieniem / przeciągnij punkt lub mrowisko
    PPM na punkcie    - usuń punkt
    Spacja            - start / pauza algorytmu mrówkowego
    B                 - tryb blokowania ścieżek (kliknij odcinek, aby go zablokować)
    R / C             - losuj punkty / wyczyść planszę
    F11 / Esc         - pełny ekran albo okno / wyjście
"""

import math
import random
import sys
import time

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

import algorytmy as alg  # noqa: E402

# --- wymiary i kolory -------------------------------------------------------
# Wymiary logiczne. Na pełnym ekranie obraz jest skalowany do rozdzielczości
# monitora, a szerokość planszy dopasowuje się do proporcji ekranu (main()).
WIDTH, HEIGHT = 1280, 760
PANEL_W = 380
BOARD_W = WIDTH - PANEL_W
PANEL_X = BOARD_W
MARGIN = 40

BG_BOARD = (236, 226, 200)       # piasek
BG_PANEL = (40, 44, 52)
TEXT = (235, 235, 235)
TEXT_DARK = (40, 35, 30)
MUTED = (150, 155, 165)
BTN = (66, 72, 84)
BTN_HOVER = (86, 94, 110)
BTN_ACTIVE = (196, 132, 46)
ANTHILL = (120, 72, 36)
FOOD = (70, 150, 60)
BEST = (220, 40, 40)
PHEROMONE = (150, 70, 200)
BLOCKED = (200, 0, 0)
PROB = (230, 120, 0)             # prawdopodobieństwa wyboru (tryb W)
ANT = (35, 22, 12)               # mrówki (tryb animacji)

# Ile animowanych mrówek rysować najwyżej (przy 100 mrówkach plansza byłaby nieczytelna).
MAX_DRAWN_ANTS = 30

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dokumentacja", "obrazy")

# Treść panelu "Algorytm i wzory" (klawisz I).
INFO_GROUP = "Algorytmy inspirowane naturą  →  inteligencja roju  →  optymalizacja kolonią mrówek (ACO)"
INFO_VARIANT = "Ant System ze strategią elitarną (Elitist AS, Dorigo i in. 1996)"
INFO_SYMBOLS = [
    "τ – ilość feromonu na ścieżce,   η = 1/d – widoczność (bliżej = lepiej)",
    "α, β – wagi feromonu i odległości,   ρ – parowanie,   Q – ilość feromonu",
    "L_k – długość trasy mrówki k,   e – dodatkowa waga najlepszej dotąd trasy",
]
INFO_FALLBACK = [  # gdy brakuje obrazków wzorów
    "p_ij = τ_ij^α · η_ij^β / Σ_l τ_il^α · η_il^β",
    "τ_ij ← (1 − ρ) · τ_ij + Σ_k Q / L_k + e · Q / L_best",
]

COMPARE_COLORS = {
    "Algorytm mrówkowy": (220, 40, 40),
    "Najbliższy sąsiad": (30, 110, 220),
    "2-opt": (20, 150, 140),
    "Przegląd zupełny": (230, 150, 0),
}


def load_font(size, bold=False):
    return pygame.font.SysFont("segoeui,arial,dejavusans", size, bold=bold)


# --- proste kontrolki ---------------------------------------------------------

class Button:
    def __init__(self, rect, label, action, active=None):
        self.rect = pygame.Rect(rect)
        self.label = label          # tekst lub funkcja zwracająca tekst
        self.action = action
        self.active = active        # funkcja zwracająca True, gdy przycisk ma być podświetlony

    def draw(self, surf, font, mouse, small_font=None):
        if self.active and self.active():
            color = BTN_ACTIVE
        else:
            color = BTN_HOVER if self.rect.collidepoint(mouse) else BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        label = self.label() if callable(self.label) else self.label
        img = font.render(label, True, TEXT)
        if small_font and img.get_width() > self.rect.w - 8:  # wąski przycisk - mniejsza czcionka
            img = small_font.render(label, True, TEXT)
        surf.blit(img, img.get_rect(center=self.rect.center))

    def handle(self, pos):
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False


class Slider:
    def __init__(self, x, y, w, label, lo, hi, value, step, fmt, on_change=None):
        self.label, self.lo, self.hi, self.step, self.fmt = label, lo, hi, step, fmt
        self.value = value
        self.on_change = on_change
        self.track = pygame.Rect(x, y + 24, w, 6)
        self.dragging = False

    def _set_from_x(self, x):
        t = min(max((x - self.track.x) / self.track.w, 0.0), 1.0)
        raw = self.lo + t * (self.hi - self.lo)
        value = round(round(raw / self.step) * self.step, 4)
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    def draw(self, surf, font):
        text = f"{self.label}: {self.fmt.format(self.value)}"
        surf.blit(font.render(text, True, TEXT), (self.track.x, self.track.y - 24))
        pygame.draw.rect(surf, BTN, self.track, border_radius=3)
        t = (self.value - self.lo) / (self.hi - self.lo)
        filled = self.track.copy()
        filled.w = int(self.track.w * t)
        pygame.draw.rect(surf, BTN_ACTIVE, filled, border_radius=3)
        knob = (self.track.x + int(self.track.w * t), self.track.centery)
        pygame.draw.circle(surf, TEXT, knob, 8)

    def handle_down(self, pos):
        hit = self.track.inflate(16, 20)
        if hit.collidepoint(pos):
            self.dragging = True
            self._set_from_x(pos[0])
            return True
        return False

    def handle_motion(self, pos):
        if self.dragging:
            self._set_from_x(pos[0])

    def handle_up(self):
        self.dragging = False


# --- aplikacja ------------------------------------------------------------------

class App:
    def __init__(self, screen):
        self.screen = screen
        self.font = load_font(16)
        self.font_small = load_font(14)
        self.font_title = load_font(21, bold=True)
        self.clock = pygame.time.Clock()

        self.points = []            # [x, y]; indeks 0 = mrowisko
        self.blocked = set()        # zablokowane ścieżki (i, j), i < j
        self.colony = None
        self.running = False
        self.block_mode = False
        self.show_pheromone = True
        self.dragging = None
        self.moved = False
        self.aco_time = 0.0         # łączny czas obliczeń algorytmu mrówkowego
        self.compare = {}           # nazwa -> (trasa, długość, czas) albo komunikat
        self.overlay = None         # nazwa trasy z porównania rysowanej na planszy
        self.block_event = None     # informacje o ostatnim zablokowaniu ścieżki
        self.message = ""
        self.show_info = False      # panel "Algorytm i wzory" (I)
        self.prob_mode = False      # tryb prawdopodobieństw wyboru (W)
        self.prob_point = None      # punkt, w którym "stoi" mrówka w trybie W
        self.chain_mode = False     # tryb W: kolejne kroki 1, 2, 3... zamiast jednego (K)
        self.animate_ants = False   # animacja mrówek (A)
        self.pending_tours = None   # trasy budowane w trwającej iteracji (animacja)
        self.ant_paths = []         # (punkty trasy, skumulowane długości) dla animacji
        self.ant_t = 0.0            # postęp animacji iteracji: 0..1
        self._stop_after_iteration = False  # "Krok" w trybie animacji

        self.formula_imgs = self._load_formulas()
        self._build_panel()
        self.random_points()

    def _load_formulas(self):
        """Wczytuje obrazki wzorów (te same co w dokumentacji); brak plików = wzory tekstem."""
        imgs = []
        for name in ("wzor_p.png", "wzor_tau.png", "wzor_dtau.png"):
            try:
                img = pygame.image.load(os.path.join(IMG_DIR, name)).convert()
            except (pygame.error, FileNotFoundError):
                return []
            scale = 0.42
            size = (round(img.get_width() * scale), round(img.get_height() * scale))
            imgs.append(pygame.transform.smoothscale(img, size))
        return imgs

    # -- budowa panelu --
    def _build_panel(self):
        x0, w = PANEL_X + 20, WIDTH - PANEL_X - 40
        half = (w - 10) // 2
        y = 56
        rows = [
            (("Start", self.toggle_run), ("Krok", self.step)),
            (("Losuj punkty", self.random_points), ("Wyczyść", self.clear)),
            (("Reset feromonu", self.reset_colony), ("Blokowanie", self.toggle_block_mode)),
            (("Porównaj algorytmy", self.run_compare), ("Feromon", self.toggle_pheromone)),
            (("Wzory (I)", self.toggle_info), ("Wybór (W)", self.toggle_prob_mode),
             ("Kroki (K)", self.toggle_chain), ("Mrówki (A)", self.toggle_ants)),
        ]
        actives = {
            "Start": lambda: self.running,
            "Blokowanie": lambda: self.block_mode,
            "Feromon": lambda: self.show_pheromone,
            "Wzory (I)": lambda: self.show_info,
            "Wybór (W)": lambda: self.prob_mode,
            "Kroki (K)": lambda: self.prob_mode and self.chain_mode,
            "Mrówki (A)": lambda: self.animate_ants,
        }
        labels = {"Start": lambda: "Pauza" if self.running else "Start"}
        self.buttons = []
        for row in rows:
            bw = (w - 10 * (len(row) - 1)) // len(row)
            for k, (label, action) in enumerate(row):
                rect = (x0 + k * (bw + 10), y, bw, 32)
                self.buttons.append(Button(rect, labels.get(label, label), action, actives.get(label)))
            y += 40

        y += 6
        dy = 42
        self.s_points = Slider(x0, y, w, "Losowane punkty pożywienia", 3, 60, 15, 1, "{:.0f}")
        self.s_ants = Slider(x0, y + dy, w, "Liczba mrówek", 5, 100, 20, 1, "{:.0f}",
                             lambda v: self._set_param("n_ants", int(v)))
        self.s_alpha = Slider(x0, y + 2 * dy, w, "α (waga feromonu)", 0, 5, 1.0, 0.1, "{:.1f}",
                              lambda v: self._set_param("alpha", v))
        self.s_beta = Slider(x0, y + 3 * dy, w, "β (waga odległości)", 0, 10, 3.0, 0.1, "{:.1f}",
                             lambda v: self._set_param("beta", v))
        self.s_rho = Slider(x0, y + 4 * dy, w, "ρ (parowanie feromonu)", 0.01, 0.9, 0.3, 0.01, "{:.2f}",
                            lambda v: self._set_param("rho", v))
        self.s_speed = Slider(x0, y + 5 * dy, w, "Prędkość animacji", 1, 20, 1, 1, "{:.0f}")
        self.sliders = [self.s_points, self.s_ants, self.s_alpha, self.s_beta, self.s_rho, self.s_speed]
        self.chart_rect = pygame.Rect(x0, y + 6 * dy + 20, w, 80)
        self.table_y = self.chart_rect.bottom + 14
        self.table_rows = []

    def _set_param(self, name, value):
        if self.colony:
            setattr(self.colony, name, value)

    # -- dane i algorytm --
    def dist(self):
        return alg.distance_matrix(self.points, self.blocked)

    def reset_colony(self):
        """Tworzy nową kolonię (np. po zmianie punktów)."""
        self.colony = None
        self.aco_time = 0.0
        self.block_event = None
        self.pending_tours = None
        if self._stop_after_iteration:
            self._stop_after_iteration = self.running = False
        if len(self.points) >= 3:
            self.colony = alg.AntColony(
                self.dist(), n_ants=int(self.s_ants.value), alpha=self.s_alpha.value,
                beta=self.s_beta.value, rho=self.s_rho.value)

    def points_changed(self):
        self.compare, self.overlay = {}, None
        self.prob_point = None
        self.reset_colony()

    def random_points(self):
        n = int(self.s_points.value)
        self.points = [[BOARD_W / 2, HEIGHT / 2]]
        while len(self.points) < n + 1:
            p = [random.uniform(MARGIN, BOARD_W - MARGIN), random.uniform(MARGIN + 50, HEIGHT - MARGIN - 20)]
            if all(math.dist(p, q) > 35 for q in self.points):
                self.points.append(p)
        self.blocked.clear()
        self.message = f"Wylosowano {n} punktów pożywienia."
        self.points_changed()

    def clear(self):
        self.points = [[BOARD_W / 2, HEIGHT / 2]]
        self.blocked.clear()
        self.running = False
        self.message = "Plansza wyczyszczona - kliknij, aby dodać pożywienie."
        self.points_changed()

    def toggle_run(self):
        if self.colony is None:
            self.message = "Potrzebne są co najmniej 2 punkty pożywienia."
            return
        self.running = not self.running

    def step(self):
        if not self.colony:
            return
        if self.animate_ants:
            # Krok w trybie animacji: mrówki przechodzą całą iterację od nowa.
            if self.pending_tours is None:
                self._start_ant_iteration()
            self.running = True
            self.message = "Krok: mrówki przechodzą jedną iterację..."
            self._stop_after_iteration = True
        else:
            self._iterate(1)

    def toggle_block_mode(self):
        self.block_mode = not self.block_mode
        if self.block_mode:
            self.prob_mode = False
        self.message = ("Tryb blokowania: kliknij odcinek, aby go zablokować lub odblokować."
                        if self.block_mode else "Tryb edycji punktów.")

    def toggle_pheromone(self):
        self.show_pheromone = not self.show_pheromone

    def toggle_info(self):
        self.show_info = not self.show_info

    def toggle_prob_mode(self):
        self.prob_mode = not self.prob_mode
        if self.prob_mode:
            self.block_mode = False
            if self.prob_point is None and len(self.points) > 1:
                self.prob_point = 0
            self.message = "Tryb wyboru: kliknij punkt i zmieniaj α oraz β suwakami."
        else:
            self.message = "Tryb edycji punktów."

    def toggle_chain(self):
        """Tryb W: pokazuje całą najbardziej prawdopodobną trasę, krok po kroku."""
        if not self.prob_mode:
            self.toggle_prob_mode()
            self.chain_mode = True
        else:
            self.chain_mode = not self.chain_mode
        self.message = ("Kroki: najbardziej prawdopodobna trasa mrówki i szansa każdego kroku."
                        if self.chain_mode else "Tryb wyboru: tylko pierwszy krok.")

    def toggle_ants(self):
        self.animate_ants = not self.animate_ants
        self.pending_tours = None   # przerwana iteracja nie zostawia feromonu
        if self._stop_after_iteration:
            self._stop_after_iteration = self.running = False
        self.message = ("Animacja: feromon zmienia się, gdy wszystkie mrówki wrócą do mrowiska."
                        if self.animate_ants else "Animacja mrówek wyłączona.")

    def _iterate(self, count):
        self.pending_tours = None
        for _ in range(count):
            start = time.perf_counter()
            self.colony.iterate()
            self.aco_time += time.perf_counter() - start
            self._check_block_event()

    # -- animacja mrówek: iteracja rozłożona na wiele klatek --
    def _start_ant_iteration(self):
        """Etap 1: mrówki budują trasy; potem idą po nich przez kolejne klatki."""
        start = time.perf_counter()
        self.pending_tours = self.colony.construct_tours()
        self.aco_time += time.perf_counter() - start
        self.ant_t = 0.0
        self.ant_paths = []
        for tour in self.pending_tours[:MAX_DRAWN_ANTS]:
            pts = [self.points[k] for k in tour] + [self.points[tour[0]]]
            cum = [0.0]
            for a, b in zip(pts, pts[1:]):
                cum.append(cum[-1] + math.dist(a, b))
            self.ant_paths.append((pts, cum))

    def _finish_ant_iteration(self):
        """Etap 2: wszystkie mrówki wróciły - parowanie i odkładanie feromonu."""
        start = time.perf_counter()
        self.colony.update_pheromone(self.pending_tours)
        self.aco_time += time.perf_counter() - start
        self.pending_tours = None
        self._check_block_event()

    def _update_ants(self):
        if self.pending_tours is None:
            self._start_ant_iteration()
        # Prędkość 1: ok. 6 s na iterację (360 klatek), prędkość 20: ok. 0,3 s.
        self.ant_t += self.s_speed.value / 360
        if self.ant_t >= 1.0:
            self._finish_ant_iteration()
            if self._stop_after_iteration:
                self._stop_after_iteration = False
                self.running = False
                self.message = f"Iteracja {self.colony.iteration} zakończona - feromon zaktualizowany."

    def _check_block_event(self):
        """Sprawdza, czy po zablokowaniu ścieżki znaleziono już trasę zastępczą."""
        ev = self.block_event
        if ev and ev["found"] is None and self.colony.best_tour is not None \
                and not alg.uses_blocked(self.colony.best_tour, self.blocked):
            ev["found"] = self.colony.iteration - ev["iteration"]
            ev["seconds"] = self.aco_time - ev["aco_time"]
            word = "iteracji" if ev["found"] == 1 else "iteracjach"
            self.message = (f"Nowa trasa omijająca blokadę po {ev['found']} {word} "
                            f"({ev['seconds'] * 1000:.0f} ms obliczeń).")

    def run_compare(self):
        """Uruchamia wszystkie algorytmy dla bieżącej planszy i zapisuje wyniki."""
        if len(self.points) < 3:
            self.message = "Za mało punktów do porównania."
            return
        self._draw_busy("Liczę trasy wszystkimi algorytmami...")
        d = self.dist()
        n_food = len(self.points) - 1
        res = {}
        params = dict(n_ants=int(self.s_ants.value), alpha=self.s_alpha.value,
                      beta=self.s_beta.value, rho=self.s_rho.value)
        tour, t = alg.timed(alg.aco, d, 100, **params)
        res["Algorytm mrówkowy"] = (tour, alg.tour_length(tour, d), t)
        tour, t = alg.timed(alg.nearest_neighbor, d)
        res["Najbliższy sąsiad"] = (tour, alg.tour_length(tour, d), t)
        tour, t = alg.timed(alg.two_opt, d)
        res["2-opt"] = (tour, alg.tour_length(tour, d), t)
        if n_food <= alg.BRUTE_FORCE_LIMIT:
            tour, t = alg.timed(alg.brute_force, d)
            res["Przegląd zupełny"] = (tour, alg.tour_length(tour, d), t)
        else:
            res["Przegląd zupełny"] = f"tylko do {alg.BRUTE_FORCE_LIMIT} punktów"
        self.compare = res
        self.overlay = None
        self.message = "Porównanie gotowe (ACO: 100 iteracji). Kliknij wiersz tabeli, aby pokazać trasę."

    # -- obsługa planszy --
    def point_at(self, pos, radius=14):
        for i in range(len(self.points) - 1, -1, -1):
            if math.dist(pos, self.points[i]) <= radius:
                return i
        return None

    def remove_point(self, k):
        if k == 0:
            self.message = "Mrowiska nie można usunąć (można je przesunąć)."
            return
        self.points.pop(k)
        self.blocked = {(a - (a > k), b - (b > k)) for a, b in self.blocked if k not in (a, b)}
        self.points_changed()

    def edge_at(self, pos):
        """Znajduje odcinek planszy najbliższy kliknięciu."""
        def seg_dist(i, j):
            (x1, y1), (x2, y2) = self.points[i], self.points[j]
            dx, dy = x2 - x1, y2 - y1
            length2 = dx * dx + dy * dy or 1
            t = max(0, min(1, ((pos[0] - x1) * dx + (pos[1] - y1) * dy) / length2))
            return math.dist(pos, (x1 + t * dx, y1 + t * dy))

        # Najpierw odcinki najlepszej trasy i zablokowane, potem pozostałe.
        preferred = set(self.blocked)
        if self.colony and self.colony.best_tour:
            preferred |= alg.tour_edges(self.colony.best_tour)
        cand = [(seg_dist(*e), e) for e in preferred]
        if cand and min(cand)[0] < 12:
            return min(cand)[1]
        n = len(self.points)
        cand = [(seg_dist(i, j), (i, j)) for i in range(n) for j in range(i + 1, n)]
        if cand and min(cand)[0] < 8:
            return min(cand)[1]
        return None

    def toggle_block(self, edge):
        edge = tuple(sorted(edge))
        if edge in self.blocked:
            self.blocked.remove(edge)
            self.message = f"Odblokowano ścieżkę {edge[0]}-{edge[1]}."
            self.block_event = None
        else:
            self.blocked.add(edge)
            self.message = f"Zablokowano ścieżkę {edge[0]}-{edge[1]}. Kolonia szuka trasy zastępczej..."
            if self.colony:
                self.block_event = {"iteration": self.colony.iteration, "found": None,
                                    "aco_time": self.aco_time}
        self.compare, self.overlay = {}, None
        if self.colony:
            # Feromon zostaje - badamy, jak szybko kolonia się dostosuje.
            self.colony.set_distances(self.dist())
            self._check_block_event()

    def board_click(self, event):
        pos = event.pos
        if self.prob_mode and event.button == 1:
            k = self.point_at(pos)
            if k is not None:
                self.prob_point = k
            return
        if self.block_mode and event.button == 1:
            edge = self.edge_at(pos)
            if edge:
                self.toggle_block(edge)
            return
        k = self.point_at(pos)
        if event.button == 1:
            if k is None:
                self.points.append([float(pos[0]), float(pos[1])])
                self.points_changed()
            else:
                self.dragging, self.moved = k, False
        elif event.button == 3 and k is not None:
            self.remove_point(k)

    def table_click(self, pos):
        for rect, name in self.table_rows:
            if rect.collidepoint(pos) and isinstance(self.compare.get(name), tuple):
                self.overlay = None if self.overlay == name else name

    # -- pętla zdarzeń --
    def handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            keys = {pygame.K_SPACE: self.toggle_run, pygame.K_b: self.toggle_block_mode,
                    pygame.K_r: self.random_points, pygame.K_c: self.clear,
                    pygame.K_s: self.step, pygame.K_p: self.run_compare,
                    pygame.K_i: self.toggle_info, pygame.K_w: self.toggle_prob_mode,
                    pygame.K_a: self.toggle_ants, pygame.K_k: self.toggle_chain}
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            if event.key in keys:
                keys[event.key]()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            if event.pos[0] < BOARD_W:
                self.board_click(event)
            elif event.button == 1:
                if not any(b.handle(event.pos) for b in self.buttons):
                    if not any(s.handle_down(event.pos) for s in self.sliders):
                        self.table_click(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            for s in self.sliders:
                s.handle_motion(event.pos)
            if self.dragging is not None:
                x = min(max(event.pos[0], 10), BOARD_W - 10)
                y = min(max(event.pos[1], 10), HEIGHT - 10)
                self.points[self.dragging] = [float(x), float(y)]
                self.moved = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for s in self.sliders:
                s.handle_up()
            if self.dragging is not None:
                self.dragging = None
                if self.moved:
                    self.points_changed()
        return True

    def update(self):
        if self.running and self.colony and self.dragging is None:
            if self.animate_ants:
                self._update_ants()
            else:
                self._iterate(int(self.s_speed.value))

    # -- rysowanie --
    def draw(self):
        self.screen.fill(BG_BOARD, (0, 0, BOARD_W, HEIGHT))
        self._draw_pheromone()
        self._draw_overlay_or_best()
        self._draw_blocked()
        self._draw_prob_lines()
        self._draw_points()
        self._draw_ants()
        self._draw_board_info()
        self._draw_prob_table()
        self._draw_info()
        self._draw_panel()

    # -- tryb W: prawdopodobieństwa wyboru następnego punktu --
    def _prob_data(self):
        """Zwraca (punkt, odwiedzone, wektor p) albo None."""
        k = self.prob_point
        if not (self.prob_mode and self.colony and k is not None and k < len(self.points)):
            return None
        # Mrówka startuje w mrowisku, więc stojąc w innym punkcie ma je już odwiedzone.
        visited = [0] if k != 0 else []
        return k, visited, self.colony.probabilities(k, visited)

    def _chain_data(self):
        """Najbardziej prawdopodobna trasa mrówki z zaznaczonego punktu, krok po kroku.

        Na każdym kroku mrówka idzie do punktu o największym p_ij (wzór liczony
        z uwzględnieniem punktów już odwiedzonych). Zwraca listę kroków
        (skąd, dokąd, p, druga_opcja, p_drugiej) albo None.
        """
        data = self._prob_data()
        if not data:
            return None
        k, visited, _ = data
        n = len(self.points)
        seen = set(visited) | {k}
        cur, steps = k, []
        while len(seen) < n:
            p = self.colony.probabilities(cur, list(seen - {cur}))
            order = [int(j) for j in p.argsort()[::-1] if p[j] > 0]
            if not order:
                break
            j = order[0]
            alt = order[1] if len(order) > 1 else None
            steps.append((cur, j, float(p[j]), alt, float(p[alt]) if alt is not None else 0.0))
            seen.add(j)
            cur = j
        if steps and cur != 0:
            steps.append((cur, 0, 1.0, None, 0.0))  # powrót do mrowiska jest wymuszony
        return steps

    def _table_corner(self, w, h):
        """Róg planszy, w którym tabela zasłoni najmniej punktów."""
        corners = [(BOARD_W - w - 10, 10), (BOARD_W - w - 10, HEIGHT - h - 80),
                   (10, HEIGHT - h - 80), (10, 100)]

        def covered(corner):
            r = pygame.Rect(corner, (w, h)).inflate(30, 30)
            return sum(r.collidepoint(p) for p in self.points)

        return min(corners, key=covered)

    def _draw_chain_lines(self):
        steps = self._chain_data()
        if not steps:
            return
        layer = pygame.Surface((BOARD_W, HEIGHT), pygame.SRCALPHA)
        for a, b, p, _, _ in steps:
            pygame.draw.line(layer, (*PROB, int(90 + 165 * p)), self.points[a], self.points[b], 2 + round(6 * p))
        self.screen.blit(layer, (0, 0))
        for step, (a, b, p, _, _) in enumerate(steps, 1):
            (x1, y1), (x2, y2) = self.points[a], self.points[b]
            text = f"{step}. {p * 100:.0f}%"
            img = self.font_small.render(text, True, TEXT_DARK)
            box = img.get_rect(center=((x1 + x2) / 2, (y1 + y2) / 2)).inflate(8, 2)
            pygame.draw.rect(self.screen, (255, 255, 255), box, border_radius=4)
            pygame.draw.rect(self.screen, PROB, box, 1, border_radius=4)
            self.screen.blit(img, img.get_rect(center=box.center))
        x, y = self.points[self.prob_point]
        pygame.draw.circle(self.screen, PROB, (x, y), 22, 3)

    def _draw_chain_table(self):
        steps = self._chain_data()
        if not steps:
            return
        max_rows = 10
        shown = steps[:max_rows]
        w, row_h = 380, 20
        h = 58 + row_h * (len(shown) + 1) + (row_h if len(steps) > max_rows else 0) + 30
        x0, y0 = self._table_corner(w, h)
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((255, 255, 255, 235))
        self.screen.blit(box, (x0, y0))
        pygame.draw.rect(self.screen, PROB, (x0, y0, w, h), 2, border_radius=4)
        start = "z mrowiska" if self.prob_point == 0 else f"z punktu {self.prob_point}"
        self.screen.blit(self.font.render(f"Najbardziej prawdopodobna trasa {start}", True, TEXT_DARK),
                         (x0 + 10, y0 + 6))
        self.screen.blit(self.font_small.render("szansa liczona wśród jeszcze nieodwiedzonych punktów",
                                                True, MUTED), (x0 + 10, y0 + 30))
        name = lambda j: "mrowisko" if j == 0 else str(j)  # noqa: E731
        cols = [("krok", 0), ("ruch", 50), ("szansa", 170), ("2. opcja", 250)]
        y = y0 + 52
        for label, dx in cols:
            self.screen.blit(self.font_small.render(label, True, MUTED), (x0 + 10 + dx, y))
        for step, (a, b, p, alt, palt) in enumerate(shown, 1):
            y += row_h
            vals = [f"{step}.", f"{name(a)} → {name(b)}",
                    "wymuszony" if alt is None and b == 0 and p == 1.0 else f"{p * 100:.1f}%",
                    f"{name(alt)}: {palt * 100:.1f}%" if alt is not None else "–"]
            for (_, dx), v in zip(cols, vals):
                self.screen.blit(self.font_small.render(v, True, TEXT_DARK), (x0 + 10 + dx, y))
        if len(steps) > max_rows:
            y += row_h
            self.screen.blit(self.font_small.render(f"... i jeszcze {len(steps) - max_rows} kroków (na planszy)",
                                                    True, MUTED), (x0 + 10, y))
        total = 1.0
        for _, _, p, _, _ in steps:
            total *= p
        y += row_h + 6
        self.screen.blit(self.font_small.render(f"Szansa, że mrówka przejdzie dokładnie tę trasę: {total * 100:.3g}%",
                                                True, (150, 60, 20)), (x0 + 10, y))

    def _draw_prob_lines(self):
        if self.chain_mode:
            self._draw_chain_lines()
            return
        data = self._prob_data()
        if not data:
            return
        k, _, p = data
        top = p.max()
        if top <= 0:
            return
        best_j = int(p.argmax())
        layer = pygame.Surface((BOARD_W, HEIGHT), pygame.SRCALPHA)
        for j, pj in enumerate(p):
            if pj <= 0:
                continue
            rel = pj / top
            color = (*PROB, int(70 + 185 * rel))
            pygame.draw.line(layer, color, self.points[k], self.points[j], 1 + round(9 * rel))
        self.screen.blit(layer, (0, 0))
        for j, pj in enumerate(p):
            if pj < 0.01:
                continue
            (x1, y1), (x2, y2) = self.points[k], self.points[j]
            font = self.font if j == best_j else self.font_small
            img = font.render(f"{pj * 100:.0f}%", True, TEXT_DARK)
            # Etykieta bliżej punktu docelowego - przy krótkich odcinkach nie zachodzą na siebie.
            box = img.get_rect(center=(x1 + 0.65 * (x2 - x1), y1 + 0.65 * (y2 - y1))).inflate(8, 2)
            pygame.draw.rect(self.screen, (255, 255, 255), box, border_radius=4)
            pygame.draw.rect(self.screen, PROB, box, 2 if j == best_j else 1, border_radius=4)
            self.screen.blit(img, img.get_rect(center=box.center))
        x, y = self.points[k]
        pygame.draw.circle(self.screen, PROB, (x, y), 22, 3)

    def _draw_prob_table(self):
        """Rozpisanie wzoru p_ij dla najbardziej prawdopodobnych punktów."""
        if self.chain_mode:
            self._draw_chain_table()
            return
        data = self._prob_data()
        if not data:
            return
        k, visited, p = data
        c = self.colony
        order = [j for j in sorted(range(len(p)), key=lambda j: -p[j]) if p[j] > 0][:6]
        w, row_h = 380, 20
        h = 64 + row_h * (len(order) + 2)
        x0, y0 = self._table_corner(w, h)
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((255, 255, 255, 235))
        self.screen.blit(box, (x0, y0))
        pygame.draw.rect(self.screen, PROB, (x0, y0, w, h), 2, border_radius=4)
        name = "mrowisku" if k == 0 else f"punkcie {k}"
        lines = [(f"Mrówka stoi w {name} – dokąd pójdzie?", self.font),
                 (f"p(j) = τ^α·η^β / Σ τ^α·η^β     α={c.alpha:.1f}  β={c.beta:.1f}", self.font_small)]
        for i, (text, font) in enumerate(lines):
            self.screen.blit(font.render(text, True, TEXT_DARK), (x0 + 10, y0 + 6 + 22 * i))
        cols = [("punkt j", 0), ("odległość", 70), ("τ / τ₀", 160), ("τ^α·η^β *", 230), ("p(j)", 320)]
        y = y0 + 54
        for label, dx in cols:
            self.screen.blit(self.font_small.render(label, True, MUTED), (x0 + 10 + dx, y))
        weights = (c.tau[k] ** c.alpha) * (c.eta[k] ** c.beta)
        wmax = max(weights[j] for j in order) if order else 1.0
        for j in order:
            y += row_h
            d = c.dist[k, j]
            vals = ["mrowisko" if j == 0 else str(j),
                    "blokada" if d >= alg.BLOCKED_PENALTY else f"{d:.0f}",
                    f"{c.tau[k, j] / c.tau0:.2f}",
                    f"{weights[j] / wmax:.3g}",
                    f"{p[j] * 100:.1f}%"]
            for (_, dx), v in zip(cols, vals):
                self.screen.blit(self.font_small.render(v, True, TEXT_DARK), (x0 + 10 + dx, y))
        note = "* względem największej wartości;  τ₀ – feromon początkowy"
        self.screen.blit(self.font_small.render(note, True, MUTED), (x0 + 10, y + row_h + 2))

    # -- tryb A: animacja mrówek --
    def _draw_ants(self):
        if not (self.animate_ants and self.pending_tours is not None):
            return
        t = min(self.ant_t, 1.0)
        count = len(self.ant_paths)
        for idx, (pts, cum) in enumerate(self.ant_paths):
            target = t * cum[-1]
            seg = 0
            while seg < len(cum) - 2 and cum[seg + 1] < target:
                seg += 1
            (x1, y1), (x2, y2) = pts[seg], pts[seg + 1]
            seg_len = cum[seg + 1] - cum[seg] or 1.0
            f = (target - cum[seg]) / seg_len
            x, y = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            ux, uy = (x2 - x1) / seg_len, (y2 - y1) / seg_len
            # Mrówki idące tą samą ścieżką rozsuwamy lekko na boki, żeby się nie zlewały.
            side = (idx - (count - 1) / 2) * min(1.2, 14 / max(count, 1))
            x, y = x - uy * side, y + ux * side
            # mrówka: odwłok, tułów i głowa ułożone wzdłuż kierunku ruchu
            parts = [(-7, 5), (0, 3.5), (6, 4)]
            for off, r in parts:   # jasna obwódka - mrówka widoczna także na feromonie
                pygame.draw.circle(self.screen, BG_BOARD, (x + off * ux, y + off * uy), r + 1.5)
            for off, r in parts:
                pygame.draw.circle(self.screen, ANT, (x + off * ux, y + off * uy), r)

    # -- panel I: algorytm i wzory --
    def _draw_info(self):
        if not self.show_info:
            return
        c = self.colony
        params = (f"Bieżące parametry:  m = {int(self.s_ants.value)} mrówek,  α = {self.s_alpha.value:.1f},  "
                  f"β = {self.s_beta.value:.1f},  ρ = {self.s_rho.value:.2f},  "
                  f"Q = {c.q if c else 1:g},  e = {c.elite if c else 1:g}")
        blocks = [
            ("Grupa algorytmów", self.font_small, MUTED), (INFO_GROUP, self.font, TEXT_DARK), (None, 8, None),
            ("Użyty algorytm", self.font_small, MUTED), (INFO_VARIANT, self.font_title, TEXT_DARK), (None, 10, None),
            ("Reguła wyboru następnego punktu (ruletka)", self.font_small, MUTED),
        ]
        imgs = self.formula_imgs
        if imgs:
            blocks += [(imgs[0], None, None), (None, 6, None),
                       ("Aktualizacja feromonu po każdej iteracji", self.font_small, MUTED),
                       (imgs[1], None, None), (imgs[2], None, None)]
        else:
            blocks += [(INFO_FALLBACK[0], self.font, TEXT_DARK), (None, 6, None),
                       ("Aktualizacja feromonu po każdej iteracji", self.font_small, MUTED),
                       (INFO_FALLBACK[1], self.font, TEXT_DARK)]
        blocks += [(None, 8, None)] + [(s, self.font_small, TEXT_DARK) for s in INFO_SYMBOLS]
        blocks += [(None, 8, None), (params, self.font, (150, 60, 20)), (None, 4, None),
                   ("I – zamknij panel", self.font_small, MUTED)]

        def height(item):
            obj, font, _ = item
            if obj is None:
                return font
            if isinstance(obj, pygame.Surface):
                return obj.get_height() + 4
            return font.get_linesize() + 2

        w = min(BOARD_W - 40, 760)
        h = sum(height(b) for b in blocks) + 36
        x0, y0 = (BOARD_W - w) // 2, max(10, (HEIGHT - h) // 2 - 20)
        shade = pygame.Surface((BOARD_W, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 90))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, (255, 255, 255), (x0, y0, w, h), border_radius=10)
        pygame.draw.rect(self.screen, BTN_ACTIVE, (x0, y0, w, h), 3, border_radius=10)
        y = y0 + 18
        for item in blocks:
            obj, font, color = item
            if isinstance(obj, pygame.Surface):
                self.screen.blit(obj, (x0 + 28, y))
            elif obj is not None:
                self.screen.blit(font.render(obj, True, color), (x0 + 24, y))
            y += height(item)

    def _draw_pheromone(self):
        if not (self.show_pheromone and self.colony):
            return
        tau = self.colony.tau
        # Rysujemy względem najmniejszej wartości: na starcie feromon jest
        # wszędzie taki sam, więc żadna ścieżka nie jest jeszcze wyróżniona.
        low, top = tau.min(), tau.max()
        if top - low <= 1e-12:
            return
        layer = pygame.Surface((BOARD_W, HEIGHT), pygame.SRCALPHA)
        n = len(self.points)
        for i in range(n):
            for j in range(i + 1, n):
                level = (tau[i, j] - low) / (top - low)
                if level < 0.04:
                    continue
                color = (*PHEROMONE, int(40 + 200 * level))
                width = 1 + int(5 * level)
                pygame.draw.line(layer, color, self.points[i], self.points[j], width)
        self.screen.blit(layer, (0, 0))

    def _draw_tour(self, tour, color, width):
        if tour and len(tour) > 1:
            pts = [self.points[k] for k in tour]
            pygame.draw.lines(self.screen, color, True, pts, width)

    def _draw_overlay_or_best(self):
        if self.overlay and isinstance(self.compare.get(self.overlay), tuple):
            self._draw_tour(self.compare[self.overlay][0], COMPARE_COLORS[self.overlay], 4)
        elif self.colony and self.colony.best_tour and len(self.colony.best_tour) == len(self.points):
            self._draw_tour(self.colony.best_tour, BEST, 3)

    def _draw_blocked(self):
        for i, j in self.blocked:
            a, b = self.points[i], self.points[j]
            for k in range(10):  # linia przerywana
                t0, t1 = k / 10, (k + 0.5) / 10
                p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                pygame.draw.line(self.screen, BLOCKED, p0, p1, 3)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            pygame.draw.circle(self.screen, (255, 255, 255), (mx, my), 10)
            pygame.draw.circle(self.screen, BLOCKED, (mx, my), 10, 2)
            pygame.draw.line(self.screen, BLOCKED, (mx - 5, my - 5), (mx + 5, my + 5), 3)
            pygame.draw.line(self.screen, BLOCKED, (mx - 5, my + 5), (mx + 5, my - 5), 3)

    def _draw_points(self):
        for k, (x, y) in enumerate(self.points):
            if k == 0:
                # mrowisko: kopczyk z wejściem
                pygame.draw.circle(self.screen, ANTHILL, (x, y + 4), 18)
                pygame.draw.circle(self.screen, (150, 95, 50), (x, y), 14)
                pygame.draw.circle(self.screen, (40, 25, 10), (x, y + 2), 5)
            else:
                pygame.draw.circle(self.screen, FOOD, (x, y), 10)
                pygame.draw.circle(self.screen, (30, 80, 25), (x, y), 10, 2)
                label = self.font_small.render(str(k), True, TEXT_DARK)
                self.screen.blit(label, (x + 10, y - 22))

    def _draw_board_info(self):
        n_food = len(self.points) - 1
        lines = [f"Punkty pożywienia: {n_food}"]
        if self.colony:
            best = self.colony.best_length
            if best == math.inf:
                best_txt = "-"
            elif best < alg.BLOCKED_PENALTY:
                best_txt = f"{best:.1f}"
            else:
                best_txt = "przez blokadę!"
            lines.append(f"Iteracja: {self.colony.iteration}    Najlepsza trasa: {best_txt}")
            lines.append(f"Czas obliczeń ACO: {self.aco_time:.2f} s")
        box = pygame.Surface((420, 12 + 22 * len(lines)), pygame.SRCALPHA)
        box.fill((255, 255, 255, 170))
        self.screen.blit(box, (10, 10))
        for k, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, TEXT_DARK), (20, 16 + 22 * k))
        if self.message:
            img = self.font.render(self.message, True, TEXT_DARK)
            bg = pygame.Surface((img.get_width() + 20, 30), pygame.SRCALPHA)
            bg.fill((255, 255, 255, 190))
            self.screen.blit(bg, (10, HEIGHT - 70))
            self.screen.blit(img, (20, HEIGHT - 65))
        hint = ("LPM: dodaj/przesuń  PPM: usuń  Spacja: start  S: krok  I: wzory  W: wybór  K: kroki  "
                "A: mrówki  B: blokada  R: losuj  C: wyczyść  Esc")
        if self.block_mode:
            hint = "TRYB BLOKOWANIA - kliknij odcinek, aby go zablokować / odblokować (B - powrót)"
        elif self.prob_mode:
            hint = ("TRYB WYBORU - kliknij punkt, aby zobaczyć prawdopodobieństwa przejścia "
                    "(K - kroki 1, 2, 3...   W - powrót)")
        self.screen.blit(self.font_small.render(hint, True, TEXT_DARK), (12, HEIGHT - 28))

    def _draw_panel(self):
        self.screen.fill(BG_PANEL, (PANEL_X, 0, WIDTH - PANEL_X, HEIGHT))
        x0 = PANEL_X + 20
        self.screen.blit(self.font_title.render("Algorytm mrówkowy – TSP", True, TEXT), (x0, 14))
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(self.screen, self.font, mouse, self.font_small)
        for s in self.sliders:
            s.draw(self.screen, self.font)
        self._draw_chart()
        self._draw_table()

    def _draw_chart(self):
        r = self.chart_rect
        self.screen.blit(self.font_small.render("Długość najlepszej trasy w kolejnych iteracjach",
                                                True, MUTED), (r.x, r.y - 20))
        pygame.draw.rect(self.screen, (28, 31, 37), r, border_radius=4)
        hist = [h for h in (self.colony.history if self.colony else []) if h < alg.BLOCKED_PENALTY]
        if len(hist) < 2:
            return
        hist = hist[-300:]
        lo, hi = min(hist), max(hist)
        span = hi - lo or 1
        pts = [(r.x + 4 + (r.w - 8) * k / (len(hist) - 1),
                r.bottom - 6 - (r.h - 12) * (h - lo) / span) for k, h in enumerate(hist)]
        pygame.draw.lines(self.screen, BTN_ACTIVE, False, pts, 2)
        self.screen.blit(self.font_small.render(f"{hi:.0f}", True, MUTED), (r.right - 44, r.y + 2))
        self.screen.blit(self.font_small.render(f"{lo:.0f}", True, MUTED), (r.right - 44, r.bottom - 20))

    def _draw_table(self):
        x0, y = PANEL_X + 20, self.table_y
        self.table_rows = []
        if not self.compare:
            self.screen.blit(self.font_small.render("Porównanie: kliknij „Porównaj algorytmy” (P)",
                                                    True, MUTED), (x0, y))
            return
        head = self.font_small.render("Algorytm              długość     czas", True, MUTED)
        self.screen.blit(head, (x0, y))
        y += 20
        best = min(v[1] for v in self.compare.values() if isinstance(v, tuple))
        for name, val in self.compare.items():
            rect = pygame.Rect(x0 - 6, y - 1, WIDTH - x0 - 14, 21)
            if self.overlay == name:
                pygame.draw.rect(self.screen, BTN_HOVER, rect, border_radius=4)
            pygame.draw.circle(self.screen, COMPARE_COLORS[name], (x0 + 4, y + 10), 5)
            self.screen.blit(self.font_small.render(name, True, TEXT), (x0 + 14, y))
            if isinstance(val, tuple):
                _, length, t = val
                gap = (length / best - 1) * 100
                col = (130, 220, 130) if gap < 1e-6 else TEXT
                self.screen.blit(self.font_small.render(f"{length:.0f} (+{gap:.1f}%)", True, col), (x0 + 160, y))
                self.screen.blit(self.font_small.render(_fmt_time(t), True, TEXT), (x0 + 270, y))
                self.table_rows.append((rect, name))
            else:
                self.screen.blit(self.font_small.render(val, True, MUTED), (x0 + 160, y))
            y += 22

    def _draw_busy(self, text):
        img = self.font_title.render(text, True, TEXT)
        box = img.get_rect(center=(BOARD_W // 2, HEIGHT // 2)).inflate(40, 30)
        pygame.draw.rect(self.screen, BG_PANEL, box, border_radius=8)
        self.screen.blit(img, img.get_rect(center=box.center))
        pygame.display.flip()

    def loop(self):
        while True:
            for event in pygame.event.get():
                if not self.handle(event):
                    return
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)


def _fmt_time(seconds):
    if seconds < 1e-3:
        return f"{seconds * 1e6:.0f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.1f} ms"
    return f"{seconds:.2f} s"


def main():
    if sys.platform == "win32":
        try:  # ostry obraz przy skalowaniu ekranu w Windows
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    global WIDTH, BOARD_W, PANEL_X
    windowed = "--okno" in sys.argv
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")  # gładkie skalowanie
    pygame.init()
    flags = pygame.SCALED
    if windowed:
        flags |= pygame.RESIZABLE
    else:
        flags |= pygame.FULLSCREEN
        # Plansza wypełnia cały ekran: szerokość logiczna wg proporcji monitora.
        dw, dh = pygame.display.get_desktop_sizes()[0]
        WIDTH = max(1180, round(HEIGHT * dw / dh))
        BOARD_W = PANEL_X = WIDTH - PANEL_W
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Algorytm mrówkowy - problem komiwojażera")
    App(screen).loop()
    pygame.quit()


if __name__ == "__main__":
    main()
