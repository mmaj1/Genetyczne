"""Powtarzalne mapy i parametry gotowych eksperymentów."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    description: str
    points: tuple[tuple[float, float], ...]
    seed: int = 7
    alpha: float = 1.0
    beta: float = 3.0
    rho: float = 0.3
    n_ants: int = 20

    @property
    def parameters(self):
        return dict(alpha=self.alpha, beta=self.beta, rho=self.rho, n_ants=self.n_ants)

    def board_points(self, width, height):
        # Jednakowa skala obu osi zachowuje proporcje i własności mapy.
        scale = min(width - 150, height - 360)
        left = (width - scale) / 2
        return [(left + x * scale, 170 + y * scale) for x, y in self.points]


SCENARIOS = {
    'pierwsza': Scenario(
        'pierwsza', 'Pierwsza kolonia',
        'Uruchom kolonię. Ślady dobrych tras rozświetlają się. Kliknij mrówkę, aby poznać jej wybory.',
        ((.48, .5), (.1, .18), (.4, .08), (.85, .17), (.95, .62), (.68, .92), (.18, .85), (.13, .5))),
}

SCENARIOS['pulapka'] = Scenario(
    'pulapka', 'Pułapka najbliższego sąsiada',
    'Najbliższy punkt kusi, lecz cały objazd jest dłuższy. Porównaj algorytmy i wybierz trasę w tabeli.',
    ((.39, .76), (.77, .02), (.25, .94), (.56, .13), (.34, .60), (0, .41), (.25, .32)),
    seed=12)
SCENARIOS['bez_feromonu'] = Scenario(
    'bez_feromonu', 'Bez feromonu',
    'α = 0: mrówki kierują się odległością. Feromon jest widoczny, ale nie wpływa na ich wybory.',
    SCENARIOS['pierwsza'].points, alpha=0)
SCENARIOS['blokada'] = Scenario(
    'blokada', 'Zablokowana droga',
    'Znajdź trasę, potem kliknij „Zablokuj drogę”. Kolonia zachowa feromon i poszuka obejścia.',
    ((.12, .5), (.25, .12), (.6, .04), (.92, .28), (.88, .72), (.58, .94), (.28, .87), (.5, .48)),
    seed=11)
