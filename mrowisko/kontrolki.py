"""Kontrolki Pygame; nie znają modelu symulacji."""

import pygame
from mrowisko.motyw import BTN, BTN_HOVER, BTN_ACTIVE, TEXT


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
