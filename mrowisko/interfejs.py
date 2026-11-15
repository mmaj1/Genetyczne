"""Kontroler Pygame: zdarzenia użytkownika przekłada na polecenia sesji."""

import math
from pathlib import Path
import random

import pygame

import algorytmy as alg
from mrowisko.kontrolki import Button, Slider
from mrowisko.motyw import (Layout, load_font, TEXT, MUTED, MARGIN, BG_BOARD,
                            COMPARE_COLORS, wrapped_text)
from mrowisko.objasnienia import ExplanationRenderer
from mrowisko.panel import PanelRenderer
from mrowisko.plansza import BoardRenderer
from mrowisko.scenariusze import SCENARIOS
from mrowisko.symulacja import SimulationSession
from mrowisko.widok_wyscigu import RaceRenderer


class App:
    def __init__(self, screen):
        self.screen = screen
        self.layout = Layout(*screen.get_size())
        self.font = load_font(16)
        self.font_small = load_font(13)
        self.font_title = load_font(24, bold=True)
        self.clock = pygame.time.Clock()
        self.session = SimulationSession([(0, 0)])
        self.block_mode = self.prob_mode = self.chain_mode = self.show_info = False
        self.show_pheromone = self.animate_ants = True
        self.prob_point = None
        self.dragging = None
        self.moved = False
        self.compare, self.overlay = {}, None
        self.message = ''
        self._completed_experiments = {}
        self.frame_seconds = 1 / 60
        self.formula_imgs = self._load_formulas()
        self._build_panel()
        self.board = BoardRenderer(screen, self.layout, self.font, self.font_small, self.font_title)
        self.explanations = ExplanationRenderer(self)
        self.panel = PanelRenderer(self)
        self.race_renderer = RaceRenderer(screen, self.layout, self.font, self.font_small, self.font_title)
        self.load_scenario('pierwsza')

    def _load_formulas(self):
        directory = Path(__file__).resolve().parent.parent / 'dokumentacja' / 'obrazy'
        images = []
        for name in ('wzor_p.png', 'wzor_tau.png', 'wzor_dtau.png'):
            try:
                image = pygame.image.load(str(directory / name)).convert()
                images.append(pygame.transform.smoothscale(image,
                              (round(image.get_width() * .42), round(image.get_height() * .42))))
            except (pygame.error, FileNotFoundError):
                return []
        return images

    def _build_panel(self):
        x, width = self.layout.panel_x + 22, self.layout.panel_w - 44
        self.buttons = []

        def row(y, items):
            w = (width - 8 * (len(items) - 1)) // len(items)
            for i, (label, action, active) in enumerate(items):
                self.buttons.append(Button((x + i * (w + 8), y, w, 32), label, action, active))

        presets = list(SCENARIOS.values())
        for start, y in ((0, 88), (2, 126)):
            row(y, [(s.title, lambda key=s.key: self.load_scenario(key),
                     lambda key=s.key: bool(self.session.scenario and self.session.scenario.key == key))
                    for s in presets[start:start + 2]])
        row(174, [(lambda: 'Pauza' if self.session.running else 'Start', self.toggle_run,
                    lambda: self.session.running),
                  (lambda: 'Nowy wyścig' if self.session.race_mode else 'Śledź mrówkę',
                   self.toggle_follow, lambda: self.session.followed is not None and not self.session.race_mode),
                  (lambda: 'Krok wyścigu' if self.session.race_mode else 'Następny ruch', self.next_move, None)])
        row(214, [('Iteracja (S)', self.step, None), ('Reset kolonii', self.reset_colony, None),
                  (lambda: 'Zablokuj drogę' if self._blocking_demo() else 'Blokowanie (B)',
                   self.block_action, lambda: self.block_mode or bool(self.session.blocked))])
        row(254, [('Losuj (R)', self.random_points, None), ('Wyczyść (C)', self.clear, None),
                  ('Feromon', self.toggle_pheromone, lambda: self.show_pheromone)])
        row(294, [(lambda: 'Plansza (V)' if self.session.race_mode else 'Wyścig (V)',
                   self.toggle_race, lambda: self.session.race_mode),
                  (lambda: 'Powrót (G)' if self.show_report else 'Wykresy (G)', self.toggle_report, lambda: self.show_report),
                  ('Porównaj (P)', self.run_compare, None)])
        row(334, [('Wzory (I)', self.toggle_info, lambda: self.show_info),
                  ('Wybór (W)', self.toggle_prob_mode, lambda: self.prob_mode),
                  ('Kroki (K)', self.toggle_chain, lambda: self.prob_mode and self.chain_mode),
                  ('Mrówki (A)', self.toggle_ants, lambda: self.animate_ants)])
        y, dy = 388, 39
        self.s_points = Slider(x, y, width, 'Losowane punkty pożywienia', 3, 60, 15, 1, '{:.0f}')
        self.s_ants = Slider(x, y + dy, width, 'Liczba mrówek', 5, 100, 20, 1, '{:.0f}',
                             lambda v: self._set_param('n_ants', int(v)))
        self.s_alpha = Slider(x, y + dy * 2, width, 'α  Wpływ feromonu', 0, 5, 1, .1, '{:.1f}',
                              lambda v: self._set_param('alpha', v))
        self.s_beta = Slider(x, y + dy * 3, width, 'β  Wpływ odległości', 0, 10, 3, .1, '{:.1f}',
                             lambda v: self._set_param('beta', v))
        self.s_rho = Slider(x, y + dy * 4, width, 'ρ  Parowanie feromonu', .01, .9, .3, .01, '{:.2f}',
                            lambda v: self._set_param('rho', v))
        self.s_speed = Slider(x, y + dy * 5, width, 'Prędkość odtwarzania', 1, 20, 1, 1, '{:.0f}')
        self.sliders = [self.s_points, self.s_ants, self.s_alpha, self.s_beta, self.s_rho, self.s_speed]
        self.chart_rect = pygame.Rect(x, 674, width, 72)
        self.table_y = 766
        self.table_rows = []

    def _parameters(self):
        return dict(n_ants=int(self.s_ants.value), alpha=self.s_alpha.value,
                    beta=self.s_beta.value, rho=self.s_rho.value)

    def _set_param(self, name, value):
        setattr(self.session.colony, name, value)
        if self.session.race_mode:
            self.message = 'Zmiany parametrów zadziałają po uruchomieniu nowego wyścigu.'
        elif self.session.scenario:
            self.message = 'Parametry zmienione — reset scenariusza przywróci ustawienia pokazu.'

    def _reset_view(self):
        self.compare, self.overlay = {}, None
        self.prob_point = self.dragging = None
        self.block_mode = self.prob_mode = self.chain_mode = self.show_info = False
        self.show_report = False
        self.report_image = self.report_directory = None
        self.report_data = None
        self._pending_report = self._announced_closure = None

    def start_race(self):
        if not self._ready():
            return
        self.session.pause()
        self.show_report = False
        self.message = 'Przygotowuję wspólną mapę i wynik odniesienia…'
        self.draw()
        pygame.display.flip()
        self.session.start_race()
        self._reset_view()
        self.message = 'Wyścig gotowy. Start: odtwarzaj, N lub S: jeden wspólny krok.'

    def toggle_race(self):
        if self.session.race_mode:
            self.session.leave_race()
            self.show_report = False
            self._pending_report = None
            self.message = 'Powrót do kolonii. Mapa i feromon kolonii są zachowane.'
        else:
            self.start_race()

    def toggle_report(self):
        if self.show_report:
            self.show_report = False
            return
        try:
            data = self.session.experiment_data()
        except ValueError as error:
            self.message = str(error)
            return
        self._pending_report = None
        self._export_and_show(data)

    def _export_and_show(self, data):
        self.session.pause()
        if self.report_data == data and self.report_image is not None:
            self.show_report = True
            return
        self.message = 'Tworzę wykresy i zapisuję wyniki eksperymentu…'
        self.draw()
        pygame.display.flip()
        try:
            from mrowisko.raporty import export_experiment
            root = Path(__file__).resolve().parent.parent / 'wyniki' / 'eksperymenty'
            directory = export_experiment(data, root)
            image = pygame.image.load(str(directory / 'podsumowanie.png')).convert()
            scale = min((self.layout.board_w - 48) / image.get_width(),
                        (self.layout.height - 245) / image.get_height())
            self.report_image = pygame.transform.smoothscale(
                image, (round(image.get_width() * scale), round(image.get_height() * scale)))
        except (OSError, ValueError, ImportError, pygame.error) as error:
            self.message = f'Nie udało się zapisać wykresów: {error}'
            return
        self.report_directory, self.report_data = directory, data
        self.show_report = True
        self.message = f'Zapisano PNG, CSV i JSON w wyniki/eksperymenty/{directory.name}'

    def _check_experiment_completion(self, seconds):
        key = None
        if self.session.race_mode and self.session.race.done:
            key = ('race', self.session.race)
        elif not self.session.race_mode and self.session.closure and self.session.closure.found_after is not None:
            key = ('closure', self.session.closure)
        if key is not None and self._completed_experiments.get(key[0]) is not key[1]:
            self._completed_experiments[key[0]] = key[1]
            self.session.pause()
            self._pending_report = [1.6, self.session.experiment_data()]
        if self._pending_report:
            self._pending_report[0] -= seconds
            if self._pending_report[0] <= 0:
                data = self._pending_report[1]
                self._pending_report = None
                self._export_and_show(data)

    def _draw_report(self):
        self.screen.fill(BG_BOARD, (0, 0, self.layout.board_w, self.layout.height))
        self.screen.blit(self.font_title.render('Podsumowanie eksperymentu', True, TEXT), (26, 22))
        self.screen.blit(self.font.render('G lub „Powrót”: wróć do planszy. Dane zapisano w wyniki/eksperymenty.',
                                          True, MUTED), (26, 68))
        if self.report_image is not None:
            rect = self.report_image.get_rect(center=(self.layout.board_w // 2, (self.layout.height - 10) // 2))
            self.screen.blit(self.report_image, rect)

    def load_scenario(self, key):
        self.session.load_scenario(key, width=self.layout.board_w, height=self.layout.height)
        self._reset_view()
        self.animate_ants = self.show_pheromone = True
        self.s_speed.value = 1
        scenario = self.session.scenario
        for slider, value in ((self.s_ants, scenario.n_ants), (self.s_alpha, scenario.alpha),
                              (self.s_beta, scenario.beta), (self.s_rho, scenario.rho)):
            slider.value = value
        self.message = 'Start: obserwuj kolonię. Śledź mrówkę: zobacz jej rzeczywiste wybory.'

    def reset_colony(self):
        if self.session.race_mode:
            self.start_race()
            return
        if self.session.scenario:
            self.load_scenario(self.session.scenario.key)
            return
        self.session.reset(self.session.points, blocked=self.session.blocked, **self._parameters())
        self._reset_view()
        self.message = 'Kolonia zaczyna od nowa.'

    def points_changed(self):
        self.session.reset(self.session.points, blocked=self.session.blocked, **self._parameters())
        self._reset_view()
        self.message = 'Mapa zmieniona. Uruchom nową kolonię.'

    def random_points(self):
        points = [[self.layout.board_w / 2, self.layout.height / 2]]
        while len(points) <= int(self.s_points.value):
            point = [random.uniform(MARGIN, self.layout.board_w - MARGIN),
                     random.uniform(180, self.layout.height - 180)]
            if all(math.dist(point, q) > 35 for q in points):
                points.append(point)
        self.session.reset(points, **self._parameters())
        self._reset_view()
        self.message = f'Wylosowano {len(points) - 1} punktów pożywienia.'

    def clear(self):
        self.session.reset([(self.layout.board_w / 2, self.layout.height / 2)], **self._parameters())
        self._reset_view()
        self.message = 'Kliknij planszę, aby dodać pożywienie.'

    def _ready(self):
        if len(self.session.points) >= 3:
            return True
        self.message = 'Dodaj co najmniej dwa punkty pożywienia.'
        return False

    def toggle_run(self):
        if self._ready():
            self.show_report = False
            self._pending_report = None
            if self.session.race_mode and self.session.race.done:
                self.message = 'Wyścig zakończony. Kliknij „Nowy wyścig”, aby go powtórzyć.'
                return
            self.session.pause() if self.session.running else self.session.play()

    def step(self):
        if self._ready():
            self._pending_report = None
            self.session.pause()
            self.session.finish_iteration()
            self._check_block_event()
            self.show_report = False
            self.message = (f'Wspólny krok wyścigu: {self.session.race.steps}.' if self.session.race_mode
                            else f'Iteracja {self.session.colony.iteration}: feromon zaktualizowany.')

    def next_move(self):
        self.show_report = False
        self._pending_report = None
        if self.session.race_mode:
            self.step()
            return
        if self._ready():
            self.animate_ants = True
            self.prob_mode = self.chain_mode = self.block_mode = False
            self.session.next_move()
            self._check_block_event()
            self.message = 'Pauza. Następny ruch prowadzi do kolejnego punktu śledzonej mrówki.'

    def toggle_follow(self):
        self.show_report = False
        self._pending_report = None
        if self.session.race_mode:
            self.start_race()
            return
        if self.session.followed is not None:
            self.session.followed = None
        elif self._ready():
            self.animate_ants = True
            self.prob_mode = self.chain_mode = self.block_mode = False
            self.session.follow(0)

    def toggle_block_mode(self):
        if self.session.race_mode:
            self.session.leave_race()
        self.show_report = False
        self._pending_report = None
        self.block_mode = not self.block_mode
        if self.block_mode:
            self.prob_mode = self.chain_mode = False
            self.session.followed = None
        self.message = 'Kliknij odcinek, aby zmienić blokadę.' if self.block_mode else 'Tryb edycji mapy.'

    def _blocking_demo(self):
        return bool(self.session.scenario and self.session.scenario.key == 'blokada')

    def block_action(self):
        self.show_report = False
        if self.session.race_mode:
            self.session.leave_race()
        if not self._blocking_demo():
            self.toggle_block_mode()
        elif not self.session.colony.best_tour:
            self.message = 'Najpierw uruchom kolonię, aby znalazła trasę.'
        else:
            self.toggle_block_mode()
            self.message = 'Kliknij odcinek złotej trasy, aby zamknąć drogę i uruchomić szukanie obejścia.'

    def toggle_block(self, edge):
        adding = tuple(sorted(edge)) not in self.session.blocked
        self.session.toggle_block(edge)
        self._block_changed(adding)
        if adding and self._blocking_demo():
            self.block_mode = False
            self.session.play()

    def _block_changed(self, adding):
        self.compare, self.overlay = {}, None
        self._pending_report = self._announced_closure = None
        self.message = 'Droga zamknięta. Kolonia zachowała feromon i szuka obejścia.' if adding else 'Droga otwarta.'
        self._check_block_event()

    def _check_block_event(self):
        closure = self.session.closure
        if closure and closure.found_after is not None and self._announced_closure is not closure:
            self._announced_closure = closure
            unit = 'iteracji' if closure.found_after == 1 else 'iteracjach'
            self.message = f'Znaleziono obejście po {closure.found_after} {unit}.'

    @property
    def block_event(self):
        closure = self.session.closure
        return dict(iteration=closure.iteration, found=closure.found_after,
                    seconds=closure.recovery_seconds) if closure else None

    def toggle_pheromone(self):
        self.show_pheromone = not self.show_pheromone

    def toggle_info(self):
        if self.session.race_mode:
            self.session.leave_race()
        self.show_report = False
        self._pending_report = None
        self.show_info = not self.show_info

    def toggle_prob_mode(self):
        if self.session.race_mode:
            self.session.leave_race()
        self.show_report = False
        self._pending_report = None
        self.prob_mode = not self.prob_mode
        self.chain_mode = False
        if self.prob_mode:
            self.block_mode = False
            self.session.followed = None
            self.prob_point = 0
        self.message = 'Kliknij punkt, aby zbadać jego szanse wyboru.' if self.prob_mode else 'Tryb edycji mapy.'

    def toggle_chain(self):
        if not self.prob_mode:
            self.toggle_prob_mode()
            self.chain_mode = True
        else:
            self.chain_mode = not self.chain_mode
        self.message = 'Podgląd zachłanny wybiera najwyższą szansę w każdym kroku.'

    def toggle_ants(self):
        if self.session.race_mode:
            self.message = 'Wyścig ma własne odtwarzanie. V: wróć do animacji mrówek.'
            return
        self.animate_ants = not self.animate_ants
        self.session.cancel_journeys()
        self.message = ('Animacja mrówek włączona.' if self.animate_ants else
                        'Szybkie obliczenia: animacja wyłączona.')

    def _iterate(self, count):
        for _ in range(count):
            self.session.iterate()
            self._check_block_event()

    def run_compare(self):
        if not self._ready():
            return
        self.session.leave_race()
        self.show_report = False
        self._pending_report = None
        self.message = 'Obliczam trasy porównawcze…'
        self.draw()
        pygame.display.flip()
        dist = alg.distance_matrix(self.session.points, self.session.blocked)
        solvers = {'Algorytm mrówkowy': lambda d: alg.aco(d, 100, seed=7, **self._parameters()),
                   'Najbliższy sąsiad': alg.nearest_neighbor, '2-opt': alg.two_opt}
        if len(self.session.points) - 1 <= alg.BRUTE_FORCE_LIMIT:
            solvers['Przegląd zupełny'] = alg.brute_force
        results = {}
        for name, solve in solvers.items():
            tour, seconds = alg.timed(solve, dist)
            results[name] = (tour, alg.tour_length(tour, dist), seconds) if tour else 'Nie znaleziono trasy'
        if 'Przegląd zupełny' not in results:
            results['Przegląd zupełny'] = f'Do {alg.BRUTE_FORCE_LIMIT} punktów'
        self.compare, self.overlay = results, None
        self.message = 'Kliknij wiersz tabeli, aby zobaczyć trasę. ACO: 100 iteracji.'

    def point_at(self, position, radius=15):
        return next((i for i in reversed(range(len(self.session.points)))
                     if math.dist(position, self.session.points[i]) <= radius), None)

    def edge_at(self, position):
        def distance(edge):
            a, b = (self.session.points[k] for k in edge)
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = min(1, max(0, ((position[0] - a[0]) * dx + (position[1] - a[1]) * dy) / (dx * dx + dy * dy or 1)))
            return math.dist(position, (a[0] + t * dx, a[1] + t * dy))
        preferred = set(self.session.blocked)
        if self.session.colony.best_tour:
            preferred |= alg.tour_edges(self.session.colony.best_tour)
        for edges, tolerance in ((preferred, 12),
                                 (((i, j) for i in range(len(self.session.points))
                                   for j in range(i + 1, len(self.session.points))), 8)):
            candidates = [(distance(edge), edge) for edge in edges]
            if candidates and min(candidates)[0] < tolerance:
                return min(candidates)[1]
        return None

    def board_click(self, event):
        if self.show_report or self.session.race_mode:
            return
        position = event.pos
        if not 180 <= position[1] <= self.layout.height - 100:
            return
        if self.show_info or (self.board.inspector_rect and self.board.inspector_rect.collidepoint(position)):
            return
        if event.button == 1 and self.block_mode:
            edge = self.edge_at(position)
            if edge:
                if (self._blocking_demo() and edge not in self.session.blocked
                        and edge not in alg.tour_edges(self.session.colony.best_tour or [])):
                    self.message = 'Wybierz odcinek aktualnej złotej trasy.'
                    return
                self.toggle_block(edge)
            return
        if event.button == 1 and self.prob_mode:
            point = self.point_at(position)
            if point is not None:
                self.prob_point = point
            return
        ant = self.board.pick_ant(position) if self.animate_ants else None
        if event.button == 1 and ant is not None:
            self.session.follow(ant)
            return
        index = self.point_at(position)
        if event.button == 1:
            if index is None:
                self.session.points.append(list(position))
                self.points_changed()
            else:
                self.session.pause()
                self.dragging, self.moved = index, False
                self.session.cancel_journeys()
        elif event.button == 3 and index is not None:
            if index == 0:
                self.message = 'Mrowisko można przesunąć, ale nie usunąć.'
                return
            self.session.points.pop(index)
            self.session.blocked = {(a - (a > index), b - (b > index))
                                    for a, b in self.session.blocked if index not in (a, b)}
            self.points_changed()

    def handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            actions = {pygame.K_SPACE: self.toggle_run, pygame.K_s: self.step,
                       pygame.K_n: self.next_move, pygame.K_f: self.toggle_follow,
                       pygame.K_b: self.toggle_block_mode, pygame.K_r: self.random_points,
                       pygame.K_c: self.clear, pygame.K_p: self.run_compare,
                       pygame.K_i: self.toggle_info, pygame.K_w: self.toggle_prob_mode,
                       pygame.K_k: self.toggle_chain, pygame.K_a: self.toggle_ants}
            actions.update({pygame.K_v: self.toggle_race, pygame.K_g: self.toggle_report})
            if event.key in actions:
                actions[event.key]()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            if event.pos[0] < self.layout.board_w:
                self.board_click(event)
            elif event.button == 1 and not any(b.handle(event.pos) for b in self.buttons):
                if not any(s.handle_down(event.pos) for s in self.sliders):
                    for rect, name in self.table_rows:
                        if rect.collidepoint(event.pos):
                            self.overlay = None if self.overlay == name else name
        elif event.type == pygame.MOUSEMOTION:
            for slider in self.sliders:
                slider.handle_motion(event.pos)
            if self.dragging is not None:
                x = min(max(event.pos[0], 15), self.layout.board_w - 15)
                y = min(max(event.pos[1], 180), self.layout.height - 100)
                self.session.points[self.dragging] = [x, y]
                self.moved = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for slider in self.sliders:
                slider.handle_up()
            if self.dragging is not None:
                self.dragging = None
                if self.moved:
                    self.points_changed()
        return True

    def update(self, seconds=1 / 60):
        self.frame_seconds = seconds
        if self.dragging is None:
            if self.show_report:
                pass
            elif self.animate_ants or self.session.race_mode:
                self.session.update(seconds, speed=240 * self.s_speed.value)
            elif self.session.running:
                self.session.improvement_age += seconds
                self._iterate(int(self.s_speed.value))
            else:
                self.session.improvement_age += seconds
        self._check_block_event()
        self._check_experiment_completion(seconds)

    def draw(self):
        overlay = None
        if self.overlay and isinstance(self.compare.get(self.overlay), tuple):
            overlay = self.compare[self.overlay][0], COMPARE_COLORS[self.overlay]
        if self.show_report:
            self._draw_report()
        elif self.session.race_mode:
            self.race_renderer.draw(self.session.race, self.session.running)
        else:
            self.board.draw(self.session, seconds=self.frame_seconds, show_pheromone=self.show_pheromone,
                            animate=self.animate_ants, overlay=overlay)
        self._draw_footer()
        if not self.session.race_mode and not self.show_report:
            self.explanations.draw()
        self.panel.draw()

    def _draw_footer(self):
        rect = pygame.Rect(24, self.layout.height - 76, self.layout.board_w - 48, 42)
        wrapped_text(self.screen, self.message, self.font_small, TEXT, rect)
        hint = 'Spacja: start/pauza   F: śledź   N: następny ruch   S: iteracja   B: blokady   Esc: wyjdź'
        if self.show_report:
            hint = 'G: powrót do planszy   V: wyścig algorytmów   Esc: wyjdź'
        elif self.session.race_mode:
            hint = 'Spacja: start/pauza   N / S: krok   G: wykresy   V: kolonia   Esc: wyjdź'
        self.screen.blit(self.font_small.render(hint, True, MUTED), (24, self.layout.height - 27))

    def loop(self):
        while True:
            seconds = min(.1, self.clock.tick(60) / 1000)
            for event in pygame.event.get():
                if not self.handle(event):
                    return
            self.update(seconds)
            self.draw()
            pygame.display.flip()
