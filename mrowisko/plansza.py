"""Rysowanie żywej planszy. Światło interpoluje stan; nie steruje algorytmem."""

import math

import numpy as np
import pygame

from mrowisko.motyw import (BG_BOARD, SURFACE, BORDER, TEXT, MUTED, ANTHILL, FOOD,
                            PHEROMONE, BEST, BLOCKED, ANT, PROB, MAX_DRAWN_ANTS,
                            point_name, wrapped_text)


class BoardRenderer:
    def __init__(self, screen, layout, font, small, title):
        self.screen, self.layout = screen, layout
        self.font, self.small, self.title = font, small, title
        self.colony = None
        self.visible_tau = None
        self.peak = 1.0
        self.ant_hits = []
        self.inspector_rect = None
        self.halos = {}
        self.background = pygame.Surface((layout.board_w, layout.height))
        self.background.fill(BG_BOARD)
        for x in range(24, layout.board_w, 32):
            for y in range(24, layout.height, 32):
                pygame.draw.circle(self.background, (22, 36, 49), (x, y), 1)

    def _halo(self, color, radius):
        key = color, radius
        if key not in self.halos:
            glow = pygame.Surface((2 * radius + 2, 2 * radius + 2), pygame.SRCALPHA)
            for r in range(radius, 0, -1):
                alpha = int(65 * (1 - r / radius) ** 2)
                pygame.draw.circle(glow, (*color, alpha), (radius + 1, radius + 1), r)
            self.halos[key] = glow
        return self.halos[key]

    def _glow(self, position, color, radius):
        glow = self._halo(color, radius)
        self.screen.blit(glow, glow.get_rect(center=position))

    def draw(self, session, *, seconds, show_pheromone=True, animate=True, overlay=None):
        self.screen.blit(self.background, (0, 0))
        self._pheromone(session, seconds, show_pheromone)
        tour, color = overlay if overlay else (session.colony.best_tour, BEST)
        if tour:
            age = session.improvement_age
            if session.closure and session.closure.found_after is not None:
                age = min(age, session.closure.recovered_age)
            self._tour(session.points, tour, color, age)
        self._blocked(session)
        self._points(session)
        ants = session.ants if animate else ()
        self._ants(session, ants)
        self._header(session)
        self._inspector(session, ants)
        self._improvement(session)
        self._closure_banner(session)

    def _pheromone(self, session, seconds, visible):
        colony = session.colony
        if self.colony is not colony:
            self.colony = colony
            self.visible_tau = colony.tau.copy()
            self.peak = max(float(colony.tau.max()), colony.tau0)
        blend = 1 - math.exp(-max(0, seconds) / .35)
        self.visible_tau += (colony.tau - self.visible_tau) * blend
        self.peak = max(self.peak, float(colony.tau.max()))
        if not visible or self.peak <= colony.tau0:
            return
        # Stały szczyt jasności: parowanie faktycznie wygasza ślady.
        denominator = math.log1p(self.peak / colony.tau0 - 1)
        levels = np.log1p(np.maximum(0, self.visible_tau / colony.tau0 - 1)) / denominator
        layer = pygame.Surface((self.layout.board_w, self.layout.height), pygame.SRCALPHA)
        for width, alpha in ((25, 18), (13, 36), (5, 70), (2, 210)):
            for i, a in enumerate(session.points):
                for j in range(i + 1, len(session.points)):
                    if (i, j) in session.blocked:
                        continue
                    level = float(levels[i, j]) ** 1.8
                    if level < .035:
                        continue
                    pygame.draw.line(layer, (*PHEROMONE, round(alpha * level)), a, session.points[j], width)
        self.screen.blit(layer, (0, 0))

    def _tour(self, points, tour, color, improvement_age):
        positions = [points[k] for k in tour]
        layer = pygame.Surface((self.layout.board_w, self.layout.height), pygame.SRCALPHA)
        pulse = max(0, 1 - improvement_age / 2.5)
        pygame.draw.lines(layer, (*color, int(18 + 28 * pulse)), True, positions, 14)
        pygame.draw.lines(layer, (*color, int(120 + 100 * pulse)), True, positions, 2)
        self.screen.blit(layer, (0, 0))

    def _blocked(self, session):
        for i, j in session.blocked:
            a, b = session.points[i], session.points[j]
            count = max(1, round(math.dist(a, b) / 16))
            for k in range(count):
                t, u = k / count, (k + .5) / count
                pygame.draw.line(self.screen, BLOCKED,
                                 (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t),
                                 (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u), 2)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            self._glow(mid, BLOCKED, 28)
            pygame.draw.circle(self.screen, BG_BOARD, mid, 12)
            pygame.draw.circle(self.screen, BLOCKED, mid, 12, 2)
            pygame.draw.line(self.screen, BLOCKED, (mid[0] - 4, mid[1] - 4), (mid[0] + 4, mid[1] + 4), 2)
            pygame.draw.line(self.screen, BLOCKED, (mid[0] - 4, mid[1] + 4), (mid[0] + 4, mid[1] - 4), 2)

    def _points(self, session):
        for index, point in enumerate(session.points):
            color = ANTHILL if index == 0 else FOOD
            self._glow(point, color, 45 if index == 0 else 29)
            if index == 0:
                pygame.draw.circle(self.screen, ANTHILL, point, 23, 1)
                pygame.draw.circle(self.screen, ANTHILL, point, 16, 2)
                pygame.draw.circle(self.screen, BG_BOARD, point, 9)
                pygame.draw.circle(self.screen, ANTHILL, point, 4)
                label = 'Mrowisko'
            else:
                pygame.draw.circle(self.screen, BG_BOARD, point, 10)
                pygame.draw.circle(self.screen, FOOD, point, 9, 2)
                pygame.draw.circle(self.screen, FOOD, point, 3)
                label = point_name(index)
            self.screen.blit(self.small.render(label, True, TEXT), (point[0] + 13, point[1] - 23))

    def _ants(self, session, ants):
        self.ant_hits = []
        drawn = list(ants[:MAX_DRAWN_ANTS])
        if session.followed is not None and session.followed >= MAX_DRAWN_ANTS:
            drawn.append(ants[session.followed])
        for ant in drawn:
            if ant.finished and ant.index != session.followed:
                continue
            ux, uy = math.cos(ant.heading), math.sin(ant.heading)
            side = ((ant.index % 7) - 3) * 1.5 if not ant.finished else 0
            x, y = ant.position[0] - uy * side, ant.position[1] + ux * side
            self.ant_hits.append((ant.index, (x, y)))
            selected = ant.index == session.followed
            if selected:
                self._glow((x, y), PROB, 34)
                pygame.draw.circle(self.screen, PROB, (x, y), 17, 1)
                self.screen.blit(self.small.render(f'Mrówka {ant.index + 1}', True, TEXT), (x + 20, y + 8))
            color = TEXT if selected else ANT
            # Odnóża i trzy części ciała podążają za kierunkiem ruchu.
            phase = session.distance * .13 + ant.index
            for offset in (-3, 1, 4):
                stride = math.sin(phase + offset) * 2
                for sign in (-1, 1):
                    start = (x + offset * ux, y + offset * uy)
                    end = (start[0] - uy * 7 * sign + ux * stride,
                           start[1] + ux * 7 * sign + uy * stride)
                    pygame.draw.line(self.screen, color, start, end, 1)
            for offset, radius in ((-6, 4), (0, 2.6), (5, 3)):
                center = (x + offset * ux, y + offset * uy)
                pygame.draw.circle(self.screen, BG_BOARD, center, radius + 1)
                pygame.draw.circle(self.screen, color, center, radius)

    def pick_ant(self, position):
        candidates = [(math.dist(position, p), index) for index, p in self.ant_hits]
        if candidates and min(candidates)[0] <= 13:
            return min(candidates)[1]
        return None

    def _header(self, session):
        self.screen.blit(self.title.render('Życie kolonii', True, TEXT), (26, 22))
        status = 'W ruchu' if session.running else 'Pauza'
        pygame.draw.circle(self.screen, PHEROMONE if session.running else MUTED, (31, 63), 3)
        self.screen.blit(self.small.render(f'{status}     Iteracja {session.colony.iteration}', True, MUTED), (43, 53))
        best = session.colony.best_length
        value = f'{best:.1f}' if math.isfinite(best) else '—'
        label = self.small.render('Najlepsza trasa', True, MUTED)
        number = self.title.render(value, True, BEST)
        self.screen.blit(label, (self.layout.board_w - 194, 23))
        self.screen.blit(number, (self.layout.board_w - 194, 45))
        if session.scenario:
            pygame.draw.line(self.screen, BORDER, (26, 88), (self.layout.board_w - 26, 88))
            self.screen.blit(self.font.render(session.scenario.title, True, PHEROMONE), (26, 100))
            wrapped_text(self.screen, session.scenario.description, self.small, MUTED,
                         pygame.Rect(26, 126, self.layout.board_w - 52, 48))

    def _inspector(self, session, ants):
        self.inspector_rect = None
        if session.followed is None or not ants:
            return
        ant = ants[session.followed]
        width, height = min(440, self.layout.board_w - 48), 237
        y = self.layout.height - height - (170 if session.closure else 90)
        positions = (24, self.layout.board_w - width - 24)
        x = min(positions, key=lambda x: sum(pygame.Rect(x, y, width, height).inflate(30, 30).collidepoint(p)
                                           for p in session.points))
        rect = self.inspector_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, SURFACE, rect, border_radius=10)
        pygame.draw.rect(self.screen, BORDER, rect, 1, border_radius=10)
        self.screen.blit(self.font.render(f'Śledzisz mrówkę {ant.index + 1}', True, TEXT), (x + 18, y + 14))
        if ant.finished:
            status = 'Brak dostępnego przejścia — mrówka utknęła.' if ant.trapped else 'Powrót do mrowiska zakończony.'
            wrapped_text(self.screen, status, self.font, BLOCKED if ant.trapped else FOOD,
                         pygame.Rect(x + 18, y + 50, width - 36, 60))
            wrapped_text(self.screen, 'Następny ruch kończy rundę pozostałych mrówek lub rozpoczyna kolejną.',
                         self.small, MUTED, pygame.Rect(x + 18, y + 124, width - 36, 90))
            return
        self.screen.blit(self.small.render(
            f'Ruch {ant.step + 1}: {point_name(ant.source)} → {point_name(ant.destination)}', True, PROB),
            (x + 18, y + 44))
        self.screen.blit(self.small.render('Szanse zapisane w chwili wyboru', True, MUTED), (x + 18, y + 70))
        options = sorted((j for j, p in enumerate(ant.probabilities) if p > 0),
                         key=lambda j: -ant.probabilities[j])
        shown = options[:5]
        if ant.destination not in shown:
            shown = shown[:4] + [ant.destination]
        for row, j in enumerate(shown):
            yy = y + 98 + row * 23
            p = ant.probabilities[j]
            chosen = j == ant.destination
            self.screen.blit(self.small.render(point_name(j), True, TEXT), (x + 18, yy))
            track = pygame.Rect(x + 57, yy + 5, width - 173, 7)
            pygame.draw.rect(self.screen, BORDER, track, border_radius=3)
            pygame.draw.rect(self.screen, BEST if chosen else PROB,
                             (track.x, track.y, max(1, round(track.w * p)), track.h), border_radius=3)
            self.screen.blit(self.small.render(f'{p * 100:.1f}%'.replace('.', ','), True, BEST if chosen else TEXT),
                             (x + width - 102, yy))
            if chosen:
                pygame.draw.circle(self.screen, BEST, (x + width - 23, yy + 9), 3)
        suffix = f'Pokazano {len(shown)} z {len(options)} opcji. ' if len(options) > len(shown) else ''
        self.screen.blit(self.small.render(suffix + 'Złoty punkt oznacza wylosowany ruch.', True, MUTED),
                         (x + 18, y + height - 25))
        # Połączenia szans dla śledzonej mrówki są rysowane z punktu decyzji.
        for j in shown:
            if ant.probabilities[j] >= .05:
                pygame.draw.circle(self.screen, BEST if j == ant.destination else PROB, session.points[j], 14, 1)

    def _improvement(self, session):
        if not session.improvement or session.improvement_age >= 3.5:
            return
        percent = f'{session.improvement.percent:.1f}'.replace('.', ',')
        text = self.font.render(f'Trasa krótsza o {percent}%', True, BEST)
        box = text.get_rect(midtop=(self.layout.board_w // 2, 22)).inflate(28, 16)
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        alpha = round(245 * min(1, 3.5 - session.improvement_age))
        pygame.draw.rect(layer, (*SURFACE, alpha), layer.get_rect(), border_radius=8)
        text.set_alpha(alpha)
        self.screen.blit(layer, box)
        self.screen.blit(text, text.get_rect(center=box.center))

    def _closure_banner(self, session):
        closure = session.closure
        if closure is None:
            return
        rect = pygame.Rect(24, self.layout.height - 158, self.layout.board_w - 48, 65)
        color = FOOD if closure.found_after is not None else BLOCKED
        pygame.draw.rect(self.screen, SURFACE, rect, border_radius=8)
        pygame.draw.rect(self.screen, color, rect, 1, border_radius=8)
        if closure.found_after is None:
            title = f'Droga zamknięta — szukamy obejścia. Iteracje od blokady: {closure.attempts}'
            subtitle = 'Feromon zachowany. Mrówki budują nowe trasy.'
        else:
            unit = 'iteracji' if closure.found_after == 1 else 'iteracjach'
            title = f'Obejście znalezione po {closure.found_after} {unit}'
            subtitle = f'Obliczenia do pierwszego obejścia: {closure.recovery_seconds * 1000:.2f} ms. G: wykres eksperymentu.'
        self.screen.blit(self.font.render(title, True, color), (rect.x + 16, rect.y + 10))
        self.screen.blit(self.small.render(subtitle, True, MUTED), (rect.x + 16, rect.y + 37))
