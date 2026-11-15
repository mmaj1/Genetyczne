"""Panele edukacyjne: podgląd wyboru, trasa zachłanna i wzory ACO."""

import pygame
import algorytmy as alg
from mrowisko.motyw import TEXT_DARK, MUTED, PROB, SURFACE, BEST, BTN_ACTIVE

INFO_GROUP = "Algorytmy inspirowane naturą  →  inteligencja roju  →  optymalizacja kolonią mrówek (ACO)"
INFO_VARIANT = "Ant System ze strategią elitarną (Elitist AS, Dorigo i in. 1996)"
INFO_SYMBOLS = [
    "τ – ilość feromonu na ścieżce,   η = 1/d – widoczność (bliżej = lepiej)",
    "α, β – wagi feromonu i odległości,   ρ – parowanie,   Q – ilość feromonu",
    "L_k – długość trasy mrówki k,   e – dodatkowa waga najlepszej dotąd trasy",
]
INFO_FALLBACK = [  # gdy brakuje obrazków wzorów
    "p_ij = τ_ij^α · η_ij^β / Σ_l τ_il^α · η_il^β",
    "τ_ij ← (1 − ρ) · τ_ij + Σ_k Q / L_k + e · Q / L_best",
]


class ExplanationRenderer:
    def __init__(self, app):
        self.app = app
        self.screen = app.screen
        self.layout = app.layout
        self.font = app.font
        self.font_small = app.font_small
        self.font_title = app.font_title

    def draw(self):
        self._draw_prob_lines()
        self._draw_prob_table()
        self._draw_info()

    def _prob_data(self):
        """Zwraca (punkt, odwiedzone, wektor p) albo None."""
        k = self.app.prob_point
        if not (self.app.prob_mode and self.app.session.colony and k is not None and k < len(self.app.session.points)):
            return None
        # Mrówka startuje w mrowisku, więc stojąc w innym punkcie ma je już odwiedzone.
        visited = [0] if k != 0 else []
        return k, visited, self.app.session.colony.probabilities(k, visited)

    def _chain_data(self):
        """Trasa zachłanna według szans mrówki z zaznaczonego punktu, krok po kroku.

        Na każdym kroku mrówka idzie do punktu o największym p_ij (wzór liczony
        z uwzględnieniem punktów już odwiedzonych). Zwraca listę kroków
        (skąd, dokąd, p, druga_opcja, p_drugiej) albo None.
        """
        data = self._prob_data()
        if not data:
            return None
        k, visited, _ = data
        n = len(self.app.session.points)
        seen = set(visited) | {k}
        cur, steps = k, []
        while len(seen) < n:
            p = self.app.session.colony.probabilities(cur, list(seen - {cur}))
            order = [int(j) for j in p.argsort()[::-1] if p[j] > 0]
            if not order:
                break
            j = order[0]
            alt = order[1] if len(order) > 1 else None
            steps.append((cur, j, float(p[j]), alt, float(p[alt]) if alt is not None else 0.0))
            seen.add(j)
            cur = j
        if steps and cur != 0:
            steps.append((cur, 0, 1.0, None, 0.0))  # powrót do mrowiska jest wymuszony
        return steps

    def _table_corner(self, w, h):
        """Róg planszy, w którym tabela zasłoni najmniej punktów."""
        corners = [(self.layout.board_w - w - 10, 10), (self.layout.board_w - w - 10, self.layout.height - h - 80),
                   (10, self.layout.height - h - 80), (10, 100)]

        def covered(corner):
            r = pygame.Rect(corner, (w, h)).inflate(30, 30)
            return sum(r.collidepoint(p) for p in self.app.session.points)

        return min(corners, key=covered)

    def _draw_chain_lines(self):
        steps = self._chain_data()
        if not steps:
            return
        layer = pygame.Surface((self.layout.board_w, self.layout.height), pygame.SRCALPHA)
        for a, b, p, _, _ in steps:
            pygame.draw.line(layer, (*PROB, int(90 + 165 * p)), self.app.session.points[a], self.app.session.points[b], 2 + round(6 * p))
        self.screen.blit(layer, (0, 0))
        for step, (a, b, p, _, _) in enumerate(steps, 1):
            (x1, y1), (x2, y2) = self.app.session.points[a], self.app.session.points[b]
            text = f"{step}. {p * 100:.0f}%"
            img = self.font_small.render(text, True, TEXT_DARK)
            box = img.get_rect(center=((x1 + x2) / 2, (y1 + y2) / 2)).inflate(8, 2)
            pygame.draw.rect(self.screen, SURFACE, box, border_radius=4)
            pygame.draw.rect(self.screen, PROB, box, 1, border_radius=4)
            self.screen.blit(img, img.get_rect(center=box.center))
        x, y = self.app.session.points[self.app.prob_point]
        pygame.draw.circle(self.screen, PROB, (x, y), 22, 3)

    def _draw_chain_table(self):
        steps = self._chain_data()
        if not steps:
            return
        max_rows = 10
        shown = steps[:max_rows]
        w, row_h = 380, 20
        h = 58 + row_h * (len(shown) + 1) + (row_h if len(steps) > max_rows else 0) + 30
        x0, y0 = self._table_corner(w, h)
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((*SURFACE, 245))
        self.screen.blit(box, (x0, y0))
        pygame.draw.rect(self.screen, PROB, (x0, y0, w, h), 2, border_radius=4)
        start = "z mrowiska" if self.app.prob_point == 0 else f"z punktu {self.app.prob_point}"
        self.screen.blit(self.font.render(f"Trasa zachłanna według szans {start}", True, TEXT_DARK),
                         (x0 + 10, y0 + 6))
        self.screen.blit(self.font_small.render("szansa liczona wśród jeszcze nieodwiedzonych punktów",
                                                True, MUTED), (x0 + 10, y0 + 30))
        name = lambda j: "mrowisko" if j == 0 else str(j)  # noqa: E731
        cols = [("krok", 0), ("ruch", 50), ("szansa", 170), ("2. opcja", 250)]
        y = y0 + 52
        for label, dx in cols:
            self.screen.blit(self.font_small.render(label, True, MUTED), (x0 + 10 + dx, y))
        for step, (a, b, p, alt, palt) in enumerate(shown, 1):
            y += row_h
            vals = [f"{step}.", f"{name(a)} → {name(b)}",
                    "wymuszony" if alt is None and b == 0 and p == 1.0 else f"{p * 100:.1f}%",
                    f"{name(alt)}: {palt * 100:.1f}%" if alt is not None else "–"]
            for (_, dx), v in zip(cols, vals):
                self.screen.blit(self.font_small.render(v, True, TEXT_DARK), (x0 + 10 + dx, y))
        if len(steps) > max_rows:
            y += row_h
            self.screen.blit(self.font_small.render(f"... i jeszcze {len(steps) - max_rows} kroków (na planszy)",
                                                    True, MUTED), (x0 + 10, y))
        total = 1.0
        for _, _, p, _, _ in steps:
            total *= p
        y += row_h + 6
        self.screen.blit(self.font_small.render(f"Szansa, że mrówka przejdzie dokładnie tę trasę: {total * 100:.3g}%",
                                                True, BEST), (x0 + 10, y))

    def _draw_prob_lines(self):
        if self.app.chain_mode:
            self._draw_chain_lines()
            return
        data = self._prob_data()
        if not data:
            return
        k, _, p = data
        top = p.max()
        if top <= 0:
            return
        best_j = int(p.argmax())
        layer = pygame.Surface((self.layout.board_w, self.layout.height), pygame.SRCALPHA)
        for j, pj in enumerate(p):
            if pj <= 0:
                continue
            rel = pj / top
            color = (*PROB, int(70 + 185 * rel))
            pygame.draw.line(layer, color, self.app.session.points[k], self.app.session.points[j], 1 + round(9 * rel))
        self.screen.blit(layer, (0, 0))
        for j, pj in enumerate(p):
            if pj < 0.01:
                continue
            (x1, y1), (x2, y2) = self.app.session.points[k], self.app.session.points[j]
            font = self.font if j == best_j else self.font_small
            img = font.render(f"{pj * 100:.0f}%", True, TEXT_DARK)
            # Etykieta bliżej punktu docelowego - przy krótkich odcinkach nie zachodzą na siebie.
            box = img.get_rect(center=(x1 + 0.65 * (x2 - x1), y1 + 0.65 * (y2 - y1))).inflate(8, 2)
            pygame.draw.rect(self.screen, SURFACE, box, border_radius=4)
            pygame.draw.rect(self.screen, PROB, box, 2 if j == best_j else 1, border_radius=4)
            self.screen.blit(img, img.get_rect(center=box.center))
        x, y = self.app.session.points[k]
        pygame.draw.circle(self.screen, PROB, (x, y), 22, 3)

    def _draw_prob_table(self):
        """Rozpisanie wzoru p_ij dla najbardziej prawdopodobnych punktów."""
        if self.app.chain_mode:
            self._draw_chain_table()
            return
        data = self._prob_data()
        if not data:
            return
        k, visited, p = data
        c = self.app.session.colony
        order = [j for j in sorted(range(len(p)), key=lambda j: -p[j]) if p[j] > 0][:6]
        w, row_h = 380, 20
        h = 64 + row_h * (len(order) + 2)
        x0, y0 = self._table_corner(w, h)
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((*SURFACE, 245))
        self.screen.blit(box, (x0, y0))
        pygame.draw.rect(self.screen, PROB, (x0, y0, w, h), 2, border_radius=4)
        name = "mrowisku" if k == 0 else f"punkcie {k}"
        lines = [(f"Mrówka stoi w {name} – dokąd pójdzie?", self.font),
                 (f"p(j) = τ^α·η^β / Σ τ^α·η^β     α={c.alpha:.1f}  β={c.beta:.1f}", self.font_small)]
        for i, (text, font) in enumerate(lines):
            self.screen.blit(font.render(text, True, TEXT_DARK), (x0 + 10, y0 + 6 + 22 * i))
        cols = [("punkt j", 0), ("odległość", 70), ("τ / τ₀", 160), ("τ^α·η^β *", 230), ("p(j)", 320)]
        y = y0 + 54
        for label, dx in cols:
            self.screen.blit(self.font_small.render(label, True, MUTED), (x0 + 10 + dx, y))
        weights = (c.tau[k] ** c.alpha) * (c.eta[k] ** c.beta)
        wmax = max(weights[j] for j in order) if order else 1.0
        for j in order:
            y += row_h
            d = c.dist[k, j]
            vals = ["mrowisko" if j == 0 else str(j),
                    "blokada" if d >= alg.BLOCKED_PENALTY else f"{d:.0f}",
                    f"{c.tau[k, j] / c.tau0:.2f}",
                    f"{weights[j] / wmax:.3g}",
                    f"{p[j] * 100:.1f}%"]
            for (_, dx), v in zip(cols, vals):
                self.screen.blit(self.font_small.render(v, True, TEXT_DARK), (x0 + 10 + dx, y))
        note = "* względem największej wartości;  τ₀ – feromon początkowy"
        self.screen.blit(self.font_small.render(note, True, MUTED), (x0 + 10, y + row_h + 2))

    def _draw_info(self):
        if not self.app.show_info:
            return
        c = self.app.session.colony
        params = (f"Bieżące parametry:  m = {int(self.app.s_ants.value)} mrówek,  α = {self.app.s_alpha.value:.1f},  "
                  f"β = {self.app.s_beta.value:.1f},  ρ = {self.app.s_rho.value:.2f},  "
                  f"Q = {c.q if c else 1:g},  e = {c.elite if c else 1:g}")
        blocks = [
            ("Grupa algorytmów", self.font_small, MUTED), (INFO_GROUP, self.font, TEXT_DARK), (None, 8, None),
            ("Użyty algorytm", self.font_small, MUTED), (INFO_VARIANT, self.font_title, TEXT_DARK), (None, 10, None),
            ("Reguła wyboru następnego punktu (ruletka)", self.font_small, MUTED),
        ]
        imgs = self.app.formula_imgs
        if imgs:
            blocks += [(imgs[0], None, None), (None, 6, None),
                       ("Aktualizacja feromonu po każdej iteracji", self.font_small, MUTED),
                       (imgs[1], None, None), (imgs[2], None, None)]
        else:
            blocks += [(INFO_FALLBACK[0], self.font, TEXT_DARK), (None, 6, None),
                       ("Aktualizacja feromonu po każdej iteracji", self.font_small, MUTED),
                       (INFO_FALLBACK[1], self.font, TEXT_DARK)]
        blocks += [(None, 8, None)] + [(s, self.font_small, TEXT_DARK) for s in INFO_SYMBOLS]
        blocks += [(None, 8, None), (params, self.font, BEST), (None, 4, None),
                   ("I – zamknij panel", self.font_small, MUTED)]

        def height(item):
            obj, font, _ = item
            if obj is None:
                return font
            if isinstance(obj, pygame.Surface):
                return obj.get_height() + 4
            return font.get_linesize() + 2

        w = min(self.layout.board_w - 40, 760)
        h = sum(height(b) for b in blocks) + 36
        x0, y0 = (self.layout.board_w - w) // 2, max(10, (self.layout.height - h) // 2 - 20)
        shade = pygame.Surface((self.layout.board_w, self.layout.height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 90))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, SURFACE, (x0, y0, w, h), border_radius=10)
        pygame.draw.rect(self.screen, BTN_ACTIVE, (x0, y0, w, h), 3, border_radius=10)
        y = y0 + 18
        for item in blocks:
            obj, font, color = item
            if isinstance(obj, pygame.Surface):
                self.screen.blit(obj, (x0 + 28, y))
            elif obj is not None:
                img = font.render(obj, True, color)
                if img.get_width() > w - 48:
                    img = pygame.transform.smoothscale(img, (w - 48, img.get_height()))
                self.screen.blit(img, (x0 + 24, y))
            y += height(item)

