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

    def draw(self, surf, font, mouse):
        if self.active and self.active():
            color = BTN_ACTIVE
        else:
            color = BTN_HOVER if self.rect.collidepoint(mouse) else BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        label = self.label() if callable(self.label) else self.label
        img = font.render(label, True, TEXT)
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

        self._build_panel()
        self.random_points()

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
        ]
        actives = {
            "Start": lambda: self.running,
            "Blokowanie": lambda: self.block_mode,
            "Feromon": lambda: self.show_pheromone,
        }
        labels = {"Start": lambda: "Pauza" if self.running else "Start"}
        self.buttons = []
        for row in rows:
            for k, (label, action) in enumerate(row):
                rect = (x0 + k * (half + 10), y, half, 32)
                self.buttons.append(Button(rect, labels.get(label, label), action, actives.get(label)))
            y += 40

        y += 6
        self.s_points = Slider(x0, y, w, "Losowane punkty pożywienia", 3, 60, 15, 1, "{:.0f}")
        self.s_ants = Slider(x0, y + 44, w, "Liczba mrówek", 5, 100, 20, 1, "{:.0f}",
                             lambda v: self._set_param("n_ants", int(v)))
        self.s_alpha = Slider(x0, y + 88, w, "α (waga feromonu)", 0, 5, 1.0, 0.1, "{:.1f}",
                              lambda v: self._set_param("alpha", v))
        self.s_beta = Slider(x0, y + 132, w, "β (waga odległości)", 0, 10, 3.0, 0.1, "{:.1f}",
                             lambda v: self._set_param("beta", v))
        self.s_rho = Slider(x0, y + 176, w, "ρ (parowanie feromonu)", 0.01, 0.9, 0.3, 0.01, "{:.2f}",
                            lambda v: self._set_param("rho", v))
        self.s_speed = Slider(x0, y + 220, w, "Prędkość (iteracje na klatkę)", 1, 20, 1, 1, "{:.0f}")
        self.sliders = [self.s_points, self.s_ants, self.s_alpha, self.s_beta, self.s_rho, self.s_speed]
        self.chart_rect = pygame.Rect(x0, y + 286, w, 100)
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
        if len(self.points) >= 3:
            self.colony = alg.AntColony(
                self.dist(), n_ants=int(self.s_ants.value), alpha=self.s_alpha.value,
                beta=self.s_beta.value, rho=self.s_rho.value)

    def points_changed(self):
        self.compare, self.overlay = {}, None
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
        if self.colony:
            self._iterate(1)

    def toggle_block_mode(self):
        self.block_mode = not self.block_mode
        self.message = ("Tryb blokowania: kliknij odcinek, aby go zablokować lub odblokować."
                        if self.block_mode else "Tryb edycji punktów.")

    def toggle_pheromone(self):
        self.show_pheromone = not self.show_pheromone

    def _iterate(self, count):
        for _ in range(count):
            start = time.perf_counter()
            self.colony.iterate()
            self.aco_time += time.perf_counter() - start
            self._check_block_event()

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
                    pygame.K_s: self.step, pygame.K_p: self.run_compare}
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
            self._iterate(int(self.s_speed.value))

    # -- rysowanie --
    def draw(self):
        self.screen.fill(BG_BOARD, (0, 0, BOARD_W, HEIGHT))
        self._draw_pheromone()
        self._draw_overlay_or_best()
        self._draw_blocked()
        self._draw_points()
        self._draw_board_info()
        self._draw_panel()

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
        hint = ("LPM: dodaj / przesuń punkt   PPM: usuń   Spacja: start/pauza   "
                "B: blokowanie   R: losuj   C: wyczyść   F11: pełny ekran   Esc: wyjście")
        if self.block_mode:
            hint = "TRYB BLOKOWANIA - kliknij odcinek, aby go zablokować / odblokować (B - powrót)"
        self.screen.blit(self.font_small.render(hint, True, TEXT_DARK), (12, HEIGHT - 28))

    def _draw_panel(self):
        self.screen.fill(BG_PANEL, (PANEL_X, 0, WIDTH - PANEL_X, HEIGHT))
        x0 = PANEL_X + 20
        self.screen.blit(self.font_title.render("Algorytm mrówkowy – TSP", True, TEXT), (x0, 14))
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(self.screen, self.font, mouse)
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
