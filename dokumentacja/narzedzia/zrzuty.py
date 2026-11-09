"""Zrzuty ekranu aplikacji do dokumentacji i prezentacji.

Użycie (z katalogu projektu):  python dokumentacja/narzedzia/zrzuty.py .
Obrazy trafiają do dokumentacji/obrazy/. Na końcu krótki test obsługi zdarzeń.
"""
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
proj = sys.argv[1]
sys.path.insert(0, proj)
import numpy as np  # noqa: E402
import pygame  # noqa: E402

import aplikacja as ap  # noqa: E402
import algorytmy as alg  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((ap.WIDTH, ap.HEIGHT))
random.seed(7)
np.random.seed(7)
app = ap.App(screen)
app.colony.rng = np.random.default_rng(7)
out = os.path.join(proj, "dokumentacja", "obrazy")


def shot(name, message=None):
    if message is not None:
        app.message = message
    app.draw()
    pygame.image.save(screen, os.path.join(out, name))


shot("gui_start.png")

# Tryb W przed pierwszą iteracją: feromon wszędzie równy, decyduje tylko odległość.
app.toggle_prob_mode()
app.prob_point = 0
shot("gui_wybor_start.png", "Iteracja 0: feromon wszędzie równy – o wyborze decyduje tylko odległość.")
app.toggle_prob_mode()

app._iterate(3)
shot("gui_iter3.png", "Iteracja 3 - feromon jest jeszcze rozproszony.")

# Animacja mrówek w trakcie iteracji 4.
app.toggle_ants()
app.running = True
for _ in range(150):
    app.update()
shot("gui_mrowki.png", "Animacja: mrówki przechodzą swoje trasy w iteracji 4.")
for _ in range(400):
    app.update()
app.running = False
app.toggle_ants()

# Tryb W po kilku iteracjach: feromon zaczyna przeważać nad samą odległością.
app._iterate(4)
app.toggle_prob_mode()
app.prob_point = 0
shot("gui_wybor.png", "Iteracja 8: feromon zmienia prawdopodobieństwa wyboru.")
app.toggle_chain()
shot("gui_kroki.png", "Kroki: najbardziej prawdopodobna trasa mrówki i szansa każdego kroku.")
app.toggle_chain()
app.toggle_prob_mode()

app._iterate(92)
shot("gui_iter100.png", "Iteracja 100 - kolonia skupiła się na krótkiej trasie.")

app.show_info = True
shot("gui_wzory.png", "")
app.show_info = False

# Blokada odcinka najlepszej trasy.
e = sorted(alg.tour_edges(app.colony.best_tour))[3]
app.block_mode = True
app.toggle_block(e)
for _ in range(200):
    app._iterate(1)
    if app.block_event["found"] is not None:
        break
print("blokada:", app.block_event)
app._iterate(30)
shot("gui_blokada.png")
app.block_mode = False

app.run_compare()
app.overlay = "2-opt"
shot("gui_porownanie.png")
print({k: (v[1], v[2]) if isinstance(v, tuple) else v for k, v in app.compare.items()})

# Test zdarzeń myszy: dodawanie, usuwanie, przyciski, suwak.
n = len(app.points)
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 100), button=1))
assert len(app.points) == n + 1
app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(100, 100), button=1))
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 100), button=3))
assert len(app.points) == n
for key in (pygame.K_i, pygame.K_w, pygame.K_a, pygame.K_i, pygame.K_w, pygame.K_a):
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
for b in app.buttons:
    b.action()
    app.update()
    app.draw()
app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(ap.PANEL_X + 200, app.s_alpha.track.centery),
                              button=1))
print("alpha", app.s_alpha.value)
app.clear()
app.draw()
app.run_compare()
app.toggle_run()
print("ok", app.message)
