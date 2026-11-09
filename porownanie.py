"""Eksperymenty porównujące algorytm mrówkowy z innymi metodami.

Uruchomienie:
    python porownanie.py            # pełny zestaw (ok. 1-3 min)
    python porownanie.py --szybko   # mniej powtórzeń, do sprawdzenia działania

Wyniki (tabele CSV i wykresy PNG) trafiają do katalogu wyniki/.

Eksperymenty:
    1. małe instancje (3-10 punktów)  - porównanie z trasą optymalną (przegląd zupełny),
    2. duże instancje (10-100 punktów) - porównanie ACO, najbliższego sąsiada i 2-opt,
    3. zbieżność ACO dla różnych parametrów,
    4. reakcja na zablokowanie ścieżki (rozszerzenie opcjonalne).
"""

import csv
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import algorytmy as alg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wyniki")
ACO_PARAMS = dict(n_ants=20, alpha=1.0, beta=3.0, rho=0.3)
ACO_ITERATIONS = 100

COLORS = {"ACO": "#d62728", "Najbliższy sąsiad": "#1f77b4", "2-opt": "#17a398",
          "Przegląd zupełny": "#ff9f00"}


def random_instance(n_food, rng):
    """Mrowisko + n_food punktów pożywienia w kwadracie 100 x 100."""
    return rng.random((n_food + 1, 2)) * 100


def solve_all(dist, with_brute, seed):
    algos = {
        "ACO": lambda d: alg.aco(d, ACO_ITERATIONS, seed=seed, **ACO_PARAMS),
        "Najbliższy sąsiad": alg.nearest_neighbor,
        "2-opt": alg.two_opt,
    }
    if with_brute:
        algos["Przegląd zupełny"] = alg.brute_force
    res = {}
    for name, f in algos.items():
        tour, t = alg.timed(f, dist)
        res[name] = (alg.tour_length(tour, dist), t)
    return res


def save_csv(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


def experiment_sizes(sizes, reps, with_brute, tag):
    """Średnia długość (względem najlepszej znanej) i czas dla kolejnych rozmiarów."""
    rng = np.random.default_rng(2024)
    names = ["ACO", "Najbliższy sąsiad", "2-opt"] + (["Przegląd zupełny"] if with_brute else [])
    gap = {k: [] for k in names}
    times = {k: [] for k in names}
    rows = []
    for n in sizes:
        g = {k: [] for k in names}
        t = {k: [] for k in names}
        for r in range(reps):
            d = alg.distance_matrix(random_instance(n, rng))
            res = solve_all(d, with_brute, seed=r)
            # punkt odniesienia: optimum (małe n) lub najlepszy wynik spośród metod
            ref = res["Przegląd zupełny"][0] if with_brute else min(v[0] for v in res.values())
            for k in names:
                g[k].append(max(0.0, (res[k][0] / ref - 1) * 100))
                t[k].append(res[k][1])
        for k in names:
            gap[k].append(np.mean(g[k]))
            times[k].append(np.mean(t[k]))
            rows.append([n, k, f"{np.mean(g[k]):.2f}", f"{np.mean(t[k]) * 1000:.3f}"])
        print(f"  n={n:3d} " + "  ".join(f"{k}: +{gap[k][-1]:.1f}% {times[k][-1] * 1000:.1f}ms" for k in names))
    save_csv(f"wyniki_{tag}.csv", ["punkty", "algorytm", "nadwyzka_dlugosci_%", "czas_ms"], rows)

    ref_name = "trasy optymalnej" if with_brute else "najlepszej znalezionej trasy"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for k in names:
        axes[0].plot(sizes, gap[k], "o-", color=COLORS[k], label=k)
        axes[1].plot(sizes, times[k], "o-", color=COLORS[k], label=k)
    axes[0].set_title(f"Długość trasy względem {ref_name}")
    axes[0].set_ylabel("nadwyżka długości [%]")
    axes[1].set_title("Czas wyznaczania trasy")
    axes[1].set_ylabel("czas [s] (skala logarytmiczna)")
    axes[1].set_yscale("log")
    for ax in axes:
        ax.set_xlabel("liczba punktów pożywienia")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"wykres_{tag}.png"), dpi=150)
    plt.close(fig)


def experiment_convergence(n=30, iterations=150):
    """Długość najlepszej trasy w kolejnych iteracjach dla różnych parametrów."""
    rng = np.random.default_rng(7)
    d = alg.distance_matrix(random_instance(n, rng))
    ref = alg.tour_length(alg.two_opt(d), d)
    variants = [
        ("α=1, β=3, ρ=0,3 (domyślne)", dict(alpha=1, beta=3, rho=0.3)),
        ("α=1, β=0 (bez odległości)", dict(alpha=1, beta=0, rho=0.3)),
        ("α=0, β=3 (bez feromonu)", dict(alpha=0, beta=3, rho=0.3)),
        ("α=1, β=3, ρ=0,05 (wolne parowanie)", dict(alpha=1, beta=3, rho=0.05)),
        ("α=1, β=3, ρ=0,8 (szybkie parowanie)", dict(alpha=1, beta=3, rho=0.8)),
    ]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rows = []
    for label, p in variants:
        runs = []
        for seed in range(3):
            c = alg.AntColony(d, n_ants=20, seed=seed, **p)
            c.run(iterations)
            runs.append(c.history)
        mean = np.mean(runs, axis=0)
        ax.plot(range(1, iterations + 1), mean, label=label)
        rows.append([label, f"{mean[-1]:.2f}", f"{(mean[-1] / ref - 1) * 100:.2f}"])
        print(f"  {label}: {mean[-1]:.1f}")
    ax.axhline(ref, color="gray", ls="--", label="wynik 2-opt")
    ax.set_title(f"Zbieżność algorytmu mrówkowego ({n} punktów, średnia z 3 uruchomień)")
    ax.set_xlabel("iteracja")
    ax.set_ylabel("długość najlepszej trasy")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "wykres_zbieznosc.png"), dpi=150)
    plt.close(fig)
    save_csv("wyniki_zbieznosc.csv", ["wariant", "dlugosc_koncowa", "nadwyzka_wzgl_2opt_%"], rows)


def experiment_blocking(reps, n=20, warmup=100, limit=300, tolerance=0.03):
    """Jak szybko kolonia znajduje dobrą trasę po zablokowaniu ścieżki.

    Po `warmup` iteracjach blokujemy losową krawędź najlepszej trasy i liczymy
    iteracje potrzebne do znalezienia trasy, która (a) omija blokadę i (b) jest
    co najwyżej o `tolerance` dłuższa niż wynik 2-opt na nowym grafie.
    Porównujemy kontynuację z zachowanym feromonem ze startem od zera.
    """
    rng = np.random.default_rng(11)
    keep, fresh, first_ok = [], [], []
    for r in range(reps):
        pts = random_instance(n, rng)
        d = alg.distance_matrix(pts)
        colony = alg.AntColony(d, seed=r, **ACO_PARAMS)
        colony.run(warmup)
        edges = sorted(alg.tour_edges(colony.best_tour))
        blocked = {edges[rng.integers(len(edges))]}
        d2 = alg.distance_matrix(pts, blocked)
        target = alg.tour_length(alg.two_opt(d2), d2) * (1 + tolerance)

        def iterations_to_target(c):
            first = None
            for k in range(1, limit + 1):
                c.iterate()
                if first is None and not alg.uses_blocked(c.best_tour, blocked):
                    first = k
                if c.best_length <= target:
                    return k, first
            return limit, first

        colony.set_distances(d2)               # feromon zachowany
        k_keep, k_first = iterations_to_target(colony)
        k_fresh, _ = iterations_to_target(alg.AntColony(d2, seed=r, **ACO_PARAMS))
        keep.append(k_keep)
        fresh.append(k_fresh)
        first_ok.append(k_first or limit)
    rows = [["pierwsza trasa omijajaca blokade (z feromonem)", f"{np.mean(first_ok):.1f}"],
            ["trasa dobrej jakosci - z zachowanym feromonem", f"{np.mean(keep):.1f}"],
            ["trasa dobrej jakosci - start od zera", f"{np.mean(fresh):.1f}"]]
    save_csv("wyniki_blokada.csv", ["miara", "srednia_liczba_iteracji"], rows)
    for r in rows:
        print("  " + ": ".join(r))

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["pierwsza trasa\nomijająca blokadę", "dobra trasa\n(zachowany feromon)", "dobra trasa\n(start od zera)"]
    vals = [np.mean(first_ok), np.mean(keep), np.mean(fresh)]
    bars = ax.bar(labels, vals, color=["#9467bd", "#d62728", "#7f7f7f"])
    ax.bar_label(bars, fmt="%.1f")
    ax.set_ylabel("średnia liczba iteracji")
    ax.set_title(f"Reakcja na zablokowanie ścieżki ({n} punktów, {reps} powtórzeń)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "wykres_blokada.png"), dpi=150)
    plt.close(fig)


def main():
    quick = "--szybko" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    reps = 2 if quick else 5
    print("1. Małe instancje (z trasą optymalną)")
    experiment_sizes([3, 4, 5, 6, 7, 8, 9, 10], reps, True, "male")
    print("2. Duże instancje")
    experiment_sizes([10, 20, 30, 50, 75, 100], 2 if quick else 3, False, "duze")
    print("3. Zbieżność ACO")
    experiment_convergence()
    print("4. Zablokowanie ścieżki")
    experiment_blocking(3 if quick else 10)
    print(f"Wyniki zapisano w {OUT}")


if __name__ == "__main__":
    main()
