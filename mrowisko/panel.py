"""Panel sterowania, wykres historii i tabela porównań."""

import math
import pygame

from mrowisko.motyw import (BG_PANEL, BORDER, SURFACE, TEXT, MUTED, BTN_HOVER,
                            PHEROMONE, FOOD, COMPARE_COLORS, format_time)


class PanelRenderer:
    def __init__(self, app):
        self.app = app

    def draw(self):
        app = self.app
        screen, layout = app.screen, app.layout
        x = layout.panel_x + 22
        screen.fill(BG_PANEL, (layout.panel_x, 0, layout.panel_w, layout.height))
        pygame.draw.line(screen, BORDER, (layout.panel_x, 0), (layout.panel_x, layout.height))
        screen.blit(app.font_title.render('Laboratorium ACO', True, TEXT), (x, 20))
        screen.blit(app.font_small.render('Gotowe eksperymenty', True, MUTED), (x, 62))
        mouse = pygame.mouse.get_pos()
        for button in app.buttons:
            button.draw(screen, app.font, mouse, app.font_small)
        for slider in app.sliders:
            slider.draw(screen, app.font_small)
        note = ('Parametry ustalone; zmiana dotyczy nowego wyścigu.' if app.session.race_mode
                else 'α, β i liczba mrówek: zmiana od następnej rundy.')
        screen.blit(app.font_small.render(note, True, MUTED), (x, 624))
        self._chart()
        self._table()
        seconds = (app.session.race.lanes['aco'].compute_seconds if app.session.race_mode
                   else app.session.compute_seconds)
        screen.blit(app.font_small.render(
            f'Obliczenia ACO: {format_time(seconds)}', True, MUTED),
            (x, layout.height - 23))

    def _chart(self):
        app = self.app
        r = app.chart_rect
        app.screen.blit(app.font_small.render('Długość najlepszej trasy', True, MUTED), (r.x, r.y - 24))
        pygame.draw.rect(app.screen, SURFACE, r, border_radius=6)
        colony = app.session.race.colony if app.session.race_mode else app.session.colony
        hist = colony.history[-300:]
        values = [v for v in hist if math.isfinite(v)]
        if len(values) < 2:
            app.screen.blit(app.font_small.render('Uruchom kolonię, aby zobaczyć postęp.', True, MUTED),
                            (r.x + 12, r.y + 25))
            return
        lo, hi = min(values), max(values)
        # Niewielki spadek nie powinien wyglądać jak ogromny skok jakości.
        if hi - lo < max(1, hi * .01):
            padding = max(.5, hi * .005)
            lo, hi = max(0, lo - padding), hi + padding
        span = hi - lo or 1
        # Zachowujemy luki dla iteracji, w których nie znaleziono pełnej trasy.
        segment = []
        for k, value in enumerate(hist):
            if math.isfinite(value):
                segment.append((r.x + 7 + (r.w - 14) * k / max(1, len(hist) - 1),
                                r.bottom - 10 - (r.h - 20) * (value - lo) / span))
            else:
                if len(segment) > 1:
                    pygame.draw.lines(app.screen, PHEROMONE, False, segment, 2)
                segment = []
        if len(segment) > 1:
            pygame.draw.lines(app.screen, PHEROMONE, False, segment, 2)
        app.screen.blit(app.font_small.render(f'{hi:.1f}', True, MUTED), (r.right - 54, r.y + 1))
        app.screen.blit(app.font_small.render(f'{lo:.1f}', True, MUTED), (r.right - 54, r.bottom - 20))

    def _table(self):
        app = self.app
        x, y = app.layout.panel_x + 22, app.table_y
        app.table_rows = []
        if app.session.race_mode:
            app.screen.blit(app.font_small.render('Wyścig: długość / czas obliczeń', True, MUTED), (x, y))
            for row, lane in enumerate(app.session.race.lanes.values(), 1):
                length = f'{lane.length:.1f}' if math.isfinite(lane.length) else '—'
                label = f'{lane.name}:  {length}  /  {format_time(lane.compute_seconds)}'
                app.screen.blit(app.font_small.render(label, True, TEXT), (x, y + row * 24))
            return
        if not app.compare:
            app.screen.blit(app.font_small.render('P: porównaj długość i czas obliczeń', True, MUTED), (x, y))
            return
        app.screen.blit(app.font_small.render('Algorytm                 długość       czas', True, MUTED), (x, y))
        y += 23
        lengths = [v[1] for v in app.compare.values() if isinstance(v, tuple)]
        best = min(lengths) if lengths else math.inf
        for name, value in app.compare.items():
            rect = pygame.Rect(x - 6, y, app.layout.panel_w - 32, 23)
            if app.overlay == name:
                pygame.draw.rect(app.screen, BTN_HOVER, rect, border_radius=4)
            pygame.draw.circle(app.screen, COMPARE_COLORS[name], (x + 3, y + 9), 4)
            label = 'ACO' if name == 'Algorytm mrówkowy' else name
            app.screen.blit(app.font_small.render(label, True, TEXT), (x + 14, y))
            if isinstance(value, tuple):
                _, length, seconds = value
                gap = (length / best - 1) * 100 if best > 0 else 0
                color = FOOD if gap < 1e-6 else TEXT
                app.screen.blit(app.font_small.render(f'{length:.0f} (+{gap:.1f}%)', True, color), (x + 168, y))
                app.screen.blit(app.font_small.render(format_time(seconds), True, TEXT), (x + 299, y))
                app.table_rows.append((rect, name))
            else:
                app.screen.blit(app.font_small.render(value, True, MUTED), (x + 168, y))
            y += 24
