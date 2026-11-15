"""Trzy zsynchronizowane plansze z jedną wspólną geometrią mapy."""

import math
import pygame

from mrowisko.motyw import (BG_BOARD, SURFACE, BORDER, TEXT, MUTED, BEST, FOOD,
                            BLOCKED, PHEROMONE, format_time, point_name, wrapped_text)


class RaceRenderer:
    def __init__(self, screen, layout, font, small, title):
        self.screen, self.layout = screen, layout
        self.font, self.small, self.title = font, small, title

    def draw(self, race, running):
        screen, layout = self.screen, self.layout
        screen.fill(BG_BOARD, (0, 0, layout.board_w, layout.height))
        screen.blit(self.title.render('Wyścig algorytmów', True, TEXT), (26, 22))
        state = 'Zakończony' if race.done else 'W ruchu' if running else 'Pauza'
        screen.blit(self.small.render(f'{state}  •  wspólny krok prezentacji: {race.steps}', True, PHEROMONE), (26, 60))
        reference = (f'Optimum: {race.optimum:.1f}' if race.optimum is not None and math.isfinite(race.optimum)
                     else 'Przegląd zupełny: brak dopuszczalnej trasy' if race.optimum is not None
                     else 'Optimum nieznane — za duża mapa na przegląd zupełny')
        screen.blit(self.small.render(reference, True, MUTED), (26, 88))
        wrapped_text(screen, 'Wszystkie metody rozwiązują tę samą mapę. 2-opt zaczyna od trasy najbliższego sąsiada. '
                     'Krok prezentacji służy animacji; czas obliczeń mierzymy osobno.', self.small, MUTED,
                     pygame.Rect(26, 113, layout.board_w - 52, 40))
        gap, margin = 12, 24
        width = (layout.board_w - 2 * margin - 2 * gap) // 3
        for index, (key, lane) in enumerate(race.lanes.items()):
            color = (BEST, (129, 174, 255), FOOD)[index]
            card = pygame.Rect(margin + index * (width + gap), 172, width, layout.height - 292)
            pygame.draw.rect(screen, SURFACE, card, border_radius=10)
            pygame.draw.rect(screen, BORDER, card, 1, border_radius=10)
            pygame.draw.circle(screen, color, (card.x + 19, card.y + 25), 4)
            screen.blit(self.font.render(lane.name, True, TEXT), (card.x + 31, card.y + 14))
            if key == 'aco':
                status = f'Iteracja {race.colony.iteration} / {race.iterations}'
            elif lane.done:
                status = 'Gotowe' if lane.tour else 'Nie znaleziono trasy'
            elif len(lane.path) < len(race.points):
                status = f'Buduje trasę: {len(lane.path)}/{len(race.points)}'
            else:
                status = 'Poprawia połączenia'
            screen.blit(self.small.render(status, True, MUTED), (card.x + 18, card.y + 46))
            map_rect = pygame.Rect(card.x + 18, card.y + 86, width - 36, card.h - 308)
            self._map(race, lane, map_rect, color)
            y = card.bottom - 185
            pygame.draw.line(screen, BORDER, (card.x + 18, y - 12), (card.right - 18, y - 12))
            screen.blit(self.small.render('Długość trasy', True, MUTED), (card.x + 18, y))
            value = f'{lane.length:.1f}' if math.isfinite(lane.length) else '—'
            screen.blit(self.title.render(value, True, color), (card.x + 18, y + 22))
            screen.blit(self.small.render('Czas obliczeń', True, MUTED), (card.x + 18, y + 65))
            screen.blit(self.font.render(format_time(lane.compute_seconds), True, TEXT), (card.x + 18, y + 87))
            percent = race.gap(lane)
            note = f'+{percent:.2f}% od optimum' if percent is not None else 'Odchylenie od optimum: —'
            screen.blit(self.small.render(note, True, MUTED), (card.x + 18, y + 122))
            if lane.done:
                screen.blit(self.small.render('Zakończono obliczenia', True, FOOD), (card.x + 18, y + 151))
        label = ('Wyniki gotowe. Za chwilę pojawią się wykresy. G: wykresy, V: powrót do kolonii.' if race.done
                 else 'Spacja: start/pauza   N lub S: jeden wspólny krok   V: powrót do edycji mapy')
        wrapped_text(screen, label, self.small, MUTED,
                     pygame.Rect(26, layout.height - 108, layout.board_w - 52, 30))

    def _map(self, race, lane, rect, color):
        xs, ys = zip(*race.points)
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        scale = min((rect.w - 18) / max(1, span_x), (rect.h - 18) / max(1, span_y))
        center_x, center_y = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        points = [(rect.centerx + (x - center_x) * scale, rect.centery + (y - center_y) * scale)
                  for x, y in race.points]
        for a, b in race.blocked:
            pygame.draw.line(self.screen, BLOCKED, points[a], points[b], 1)
        path = list(lane.path)
        pairs = list(zip(path, path[1:]))
        if len(path) == len(points):
            pairs.append((path[-1], path[0]))
        layer = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        for a, b in pairs:
            if tuple(sorted((a, b))) not in race.blocked:
                pygame.draw.line(layer, (*color, 35), points[a], points[b], 8)
                pygame.draw.line(layer, (*color, 230), points[a], points[b], 2)
        self.screen.blit(layer, (0, 0))
        for index, point in enumerate(points):
            pygame.draw.circle(self.screen, BG_BOARD, point, 6)
            pygame.draw.circle(self.screen, BEST if index == 0 else TEXT, point, 5, 1)
            if len(points) <= 20 or index == 0:
                self.screen.blit(self.small.render(point_name(index), True, TEXT), (point[0] + 5, point[1] - 18))
