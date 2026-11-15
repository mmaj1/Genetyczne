"""Uruchomienie laboratorium ACO: python aplikacja.py [--okno]."""

import os
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame  # noqa: E402

from mrowisko.interfejs import App  # noqa: E402
from mrowisko.motyw import WIDTH, HEIGHT, BOARD_W, PANEL_X, PANEL_W  # noqa: E402,F401


def main():
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
    os.environ.setdefault('SDL_RENDER_SCALE_QUALITY', '1')
    pygame.init()
    try:
        flags = pygame.SCALED
        width = WIDTH
        if '--okno' in sys.argv:
            flags |= pygame.RESIZABLE
        else:
            flags |= pygame.FULLSCREEN
            desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
            width = max(WIDTH, round(HEIGHT * desktop_w / desktop_h))
        screen = pygame.display.set_mode((width, HEIGHT), flags)
        pygame.display.set_caption('Życie kolonii — laboratorium ACO / TSP')
        App(screen).loop()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
