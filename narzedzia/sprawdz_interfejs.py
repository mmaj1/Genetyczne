"""Próba przepływów Pygame i zrzuty nowego interfejsu bez otwierania okna."""

import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
from aplikacja import App, WIDTH, HEIGHT  # noqa: E402
from mrowisko.scenariusze import SCENARIOS  # noqa: E402


def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        app = App(screen)
        output = ROOT / 'wyniki' / 'podglad'
        output.mkdir(parents=True, exist_ok=True)

        def click(position, button=1):
            app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=button))
            app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=button))

        def key(value):
            app.handle(pygame.event.Event(pygame.KEYDOWN, key=value))

        def shot(name):
            app.draw()
            pygame.image.save(screen, str(output / name))

        shot('start.png')
        app.session.iterate(4)
        app.toggle_run()
        for _ in range(75):
            app.update(1 / 60)
        app.draw()
        candidates = [(i, p) for i, p in app.board.ant_hits
                      if app.point_at(p, 22) is None and p[1] > 180]
        assert candidates, 'Brak mrówki do kliknięcia'
        index, position = candidates[0]
        click(position)
        assert app.session.followed == index
        key(pygame.K_SPACE)
        assert not app.session.running
        previous = app.session.ants[index]
        key(pygame.K_n)
        assert app.session.ants[index].step > previous.step
        assert not app.session.running
        shot('sledzenie.png')
        # Wzory i obydwa istniejące podglądy działają po przeniesieniu do modułu.
        key(pygame.K_i)
        shot('wzory.png')
        key(pygame.K_i)
        key(pygame.K_w)
        shot('wybor.png')
        key(pygame.K_k)
        shot('kroki.png')
        key(pygame.K_w)

        for scenario in SCENARIOS.values():
            button = next(b for b in app.buttons if b.label == scenario.title)
            click(button.rect.center)
            assert app.session.scenario.key == scenario.key
            assert app.session.colony.iteration == 0
            assert not app.session.running
            app.step()
            app.draw()
        app.run_compare()
        app.draw()
        if app.table_rows:
            rect, name = app.table_rows[0]
            click(rect.center)
            assert app.overlay == name
        app.block_action()
        assert app.block_mode
        edges = sorted(__import__('algorytmy').tour_edges(app.session.colony.best_tour))
        for edge in edges:
            a, b = [app.session.points[j] for j in edge]
            position = (a[0] + .37 * (b[0] - a[0]), a[1] + .37 * (b[1] - a[1]))
            if app.edge_at(position) == edge:
                break
        click(position)
        assert app.session.closure.edge == edge
        shot('blokada_szukamy.png')
        assert app.session.blocked
        assert not app.session.ants
        app.session.iterate(15)
        app.update()
        assert app.block_event['found'] is not None
        shot('blokada.png')
        key(pygame.K_g)
        assert app.show_report
        assert (app.report_directory / 'wyniki.csv').exists()
        shot('wykres_blokady.png')
        key(pygame.K_g)

        app.load_scenario('pulapka')
        key(pygame.K_v)
        assert app.session.race_mode
        key(pygame.K_SPACE)
        for _ in range(5):
            app.update(.12)
        key(pygame.K_SPACE)
        assert app.session.race.steps == 5
        app.update(.5)
        assert app.session.race.steps == 5
        key(pygame.K_SPACE)
        while not app.session.race.done:
            app.update(.12)
        shot('wyscig.png')
        app.update(2)
        assert app.show_report
        assert app.report_data['kind'] == 'race'
        assert len(app.report_data['results']) == 3
        assert (app.report_directory / 'postep_aco.csv').exists()
        shot('wykres_wyscigu.png')
        key(pygame.K_g)
        key(pygame.K_v)
        assert not app.session.race_mode

        app.clear()
        click((150, 250))
        click((350, 280))
        assert len(app.session.points) == 3
        click((150, 250), 3)
        assert len(app.session.points) == 2
        app.draw()
        app.toggle_run()
        assert not app.session.running
        print(f'OK: kliknięcie mrówki, pauza, ruch, scenariusze, blokada, podglądy, porównanie i edycja. Zrzuty: {output}')
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
