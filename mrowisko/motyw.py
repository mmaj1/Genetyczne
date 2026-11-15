"""Geometria i wspólny język wizualny interfejsu."""

from dataclasses import dataclass
import pygame

WIDTH, HEIGHT = 1440, 900
PANEL_W = 440
BOARD_W = PANEL_X = WIDTH - PANEL_W
MARGIN = 50
MAX_DRAWN_ANTS = 30

BG_BOARD = (10, 19, 32)
BG_PANEL = (19, 31, 45)
SURFACE = (25, 41, 56)
BORDER = (47, 67, 84)
TEXT = (231, 239, 243)
TEXT_DARK = TEXT
MUTED = (156, 177, 192)
BTN = (34, 52, 69)
BTN_HOVER = (48, 72, 88)
BTN_ACTIVE = (31, 108, 108)
ANTHILL = (210, 143, 86)
FOOD = (155, 206, 178)
BEST = (255, 216, 144)
PHEROMONE = (65, 213, 210)
BLOCKED = (255, 112, 115)
PROB = (158, 191, 255)
ANT = (245, 180, 120)
COMPARE_COLORS = {
    'Algorytm mrówkowy': BEST,
    'Najbliższy sąsiad': (129, 174, 255),
    '2-opt': (98, 215, 178),
    'Przegląd zupełny': (213, 166, 255),
}


@dataclass(frozen=True)
class Layout:
    width: int = WIDTH
    height: int = HEIGHT
    panel_w: int = PANEL_W

    @property
    def board_w(self):
        return self.width - self.panel_w

    @property
    def panel_x(self):
        return self.board_w


def load_font(size, bold=False):
    # Kolekcje TTC na macOS potrafią wybrać ciężką odmianę również dla regular.
    return pygame.font.SysFont('arial,dejavusans,segoeui', size, bold=bold)


def point_name(index):
    return 'M' if index == 0 else str(index)


def format_time(seconds):
    if seconds < 1e-3:
        return f'{seconds * 1e6:.0f} µs'
    if seconds < 1:
        return f'{seconds * 1e3:.1f} ms'
    return f'{seconds:.2f} s'


def wrapped_text(surface, text, font, color, rect, *, gap=3):
    """Rysuje zawijany tekst w przydzielonym prostokącie, bez wychodzenia poza niego."""
    line, y = '', rect.y
    for word in text.split():
        candidate = f'{line} {word}'.strip()
        if line and font.size(candidate)[0] > rect.w:
            if y + font.get_linesize() > rect.bottom:
                return y
            surface.blit(font.render(line, True, color), (rect.x, y))
            y += font.get_linesize() + gap
            line = word
        else:
            line = candidate
    if line and y + font.get_linesize() <= rect.bottom:
        surface.blit(font.render(line, True, color), (rect.x, y))
    return y + font.get_linesize() + gap
