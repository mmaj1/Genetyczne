"""Eksport wyników do PNG/CSV/JSON; wykresy korzystają wyłącznie z zapisu sesji."""

import csv
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile


COLORS = ('#b77d1b', '#3974c4', '#208e79')


def _series(ax, samples, **kwargs):
    if samples:
        ax.plot([s[0] for s in samples], [s[1] for s in samples], **kwargs)


def _race_figure(fig, data):
    grid = fig.add_gridspec(2, 2, height_ratios=(1, 1.2))
    length_ax, time_ax = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])
    history_ax = fig.add_subplot(grid[1, :])
    names = [r['name'] for r in data['results']]
    lengths = [r['length'] or 0 for r in data['results']]
    bars = length_ax.bar(names, lengths, color=COLORS, width=.55)
    for bar, result in zip(bars, data['results']):
        gap = f" (+{result['gap']:.1f}%)" if result['gap'] is not None else ''
        label = f"{result['length']:.1f}{gap}" if result['length'] is not None else 'Brak trasy'
        length_ax.annotate(label, (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                           xytext=(0, 5), textcoords='offset points', ha='center', fontsize=10)
    if data['optimum'] is not None:
        length_ax.axhline(data['optimum'], color='#354759', ls='--', lw=1.2, label='Optimum')
        length_ax.legend(fontsize=9)
    length_ax.set(title='Długość znalezionej trasy', ylabel='Odległość [jednostki planszy]')
    length_ax.margins(y=.22)
    milliseconds = [r['seconds'] * 1000 for r in data['results']]
    bars = time_ax.bar(names, milliseconds, color=COLORS, width=.55)
    if min(milliseconds) > 0 and max(milliseconds) / min(milliseconds) > 20:
        time_ax.set_yscale('log')
    for bar, value in zip(bars, milliseconds):
        time_ax.annotate(f'{value:.3f}', (bar.get_x() + bar.get_width() / 2, value),
                         xytext=(0, 5), textcoords='offset points', ha='center', fontsize=10)
    time_ax.set(title='Rzeczywisty czas obliczeń', ylabel='Czas [ms]')
    time_ax.margins(y=.3)
    _series(history_ax, data['aco_history'], color=COLORS[0], lw=2, label='ACO')
    for result, color in zip(data['results'][1:], COLORS[1:]):
        if result['length'] is not None:
            qualifier = 'wynik końcowy' if result['done'] else 'wynik bieżący'
            history_ax.axhline(result['length'], color=color, ls=':',
                               label=f"{result['name']} — {qualifier}")
    if data['optimum'] is not None:
        history_ax.axhline(data['optimum'], color='#354759', ls='--', label='Optimum')
    history_ax.set(title='Postęp ACO i wyniki metod odniesienia', xlabel='Iteracja ACO',
                   ylabel='Długość najlepszej trasy')
    history_ax.legend(fontsize=9)
    for ax in (length_ax, time_ax, history_ax):
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    state = 'zakończony' if data['complete'] else 'w trakcie'
    fig.suptitle(f"Wyścig algorytmów — {state} • {len(data['points']) - 1} punktów pożywienia", fontsize=16)
    reference = (f"Optimum obliczono osobno w {data['reference_seconds'] * 1000:.2f} ms."
                 if data['optimum_known'] else 'Optimum nie jest znane dla tej mapy.')
    fig.text(.5, .018, f"ACO: {data['aco_iterations']} iter. Czasy: obliczenia, bez animacji i wykresów. " + reference,
             ha='center', fontsize=9, color='#4b5c6a')


def _closure_figure(fig, data):
    grid = fig.add_gridspec(2, 2, height_ratios=(1.2, 1))
    history_ax = fig.add_subplot(grid[0, :])
    _series(history_ax, data['before'], color='#b77d1b', lw=2, marker='o', ms=3, label='Przed blokadą')
    _series(history_ax, data['after'], color='#208e79', lw=2, marker='o', ms=3, label='Po blokadzie')
    closed = data['iteration_closed']
    history_ax.axvline(closed, color='#cc4f55', ls='--', label='Zamknięcie drogi')
    found = data['found_after']
    if found is not None:
        history_ax.axvline(closed + found, color='#208e79', ls=':', label=f'Pierwsze obejście: +{found} iter.')
    history_ax.set(xlabel='Iteracja kolonii', ylabel='Długość dopuszczalnej trasy', title='Przebieg reakcji na zamknięcie drogi')
    history_ax.grid(alpha=.2)
    history_ax.legend(fontsize=9, loc='best')
    stats_ax, map_ax = fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])
    stats_ax.axis('off')
    stats_ax.set_title('Wynik eksperymentu', loc='left')
    recovery = f'{found} iter.' if found is not None else f"Jeszcze nie znaleziono ({data['attempts']} iter.)"
    cpu = f"{data['recovery_seconds'] * 1000:.3f} ms" if data['recovery_seconds'] is not None else '—'
    old = f"{data['old_length']:.1f}" if data['old_length'] is not None else '—'
    new = f"{data['length']:.1f}" if data['length'] is not None else '—'
    lines = [f"Zamknięty odcinek: {data['edge'][0]}–{data['edge'][1]}",
             f'Pierwsze dopuszczalne obejście: {recovery}', f'Obliczenia do obejścia: {cpu}',
             f'Długość przed blokadą: {old}', f'Bieżąca długość po blokadzie: {new}',
             'Feromon zachowano; czas animacji pominięto.']
    for i, line in enumerate(lines):
        stats_ax.text(0, .9 - i * .14, line, transform=stats_ax.transAxes, fontsize=10)
    points = data['points']
    for tour, color, style, label in ((data['old_tour'], '#cc4f55', '--', 'Stara trasa'),
                                       (data['tour'], '#208e79', '-', 'Nowa trasa')):
        if tour:
            path = [points[j] for j in [*tour, tour[0]]]
            map_ax.plot([p[0] for p in path], [p[1] for p in path], style, color=color, alpha=.8, label=label)
    map_ax.scatter([p[0] for p in points], [p[1] for p in points], s=18, c='#354759', zorder=3)
    a, b = [points[j] for j in data['edge']]
    map_ax.plot([a[0], b[0]], [a[1], b[1]], color='#cc4f55', lw=3)
    map_ax.scatter([(a[0] + b[0]) / 2], [(a[1] + b[1]) / 2], marker='x', c='#cc4f55', s=80, zorder=5)
    map_ax.set_aspect('equal', adjustable='datalim')
    map_ax.invert_yaxis()
    map_ax.set_title('Ta sama mapa przed i po zamknięciu')
    map_ax.legend(fontsize=8, loc='best')
    map_ax.set_xticks([])
    map_ax.set_yticks([])
    fig.suptitle('Droga została zamknięta — reakcja kolonii', fontsize=16)
    fig.text(.5, .018, 'Stara trasa może być po blokadzie niedopuszczalna. Luki oznaczają brak znalezionej trasy.',
             ha='center', fontsize=9, color='#4b5c6a')


def export_experiment(data, root):
    # Import dopiero przy eksporcie: start aplikacji nie ładuje biblioteki wykresów.
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'aco-matplotlib-cache'))
    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    directory = Path(root) / f"{data['kind']}_{datetime.now():%Y%m%d_%H%M%S_%f}"
    directory.mkdir(parents=True, exist_ok=False)
    with matplotlib.rc_context({'font.family': 'DejaVu Sans', 'font.size': 11}):
        fig = Figure(figsize=(12, 7.6), facecolor='white')
        FigureCanvasAgg(fig)
        if data['kind'] == 'race':
            _race_figure(fig, data)
        elif data['kind'] == 'closure':
            _closure_figure(fig, data)
        else:
            ax = fig.add_subplot(111)
            _series(ax, data['history'], color=COLORS[0], lw=2, marker='o', ms=2)
            ax.set(xlabel='Iteracja ACO', ylabel='Długość najlepszej trasy', title='Postęp kolonii')
            ax.grid(alpha=.2)
        fig.tight_layout(rect=(0, .045, 1, .94))
        fig.savefig(directory / 'podsumowanie.png', dpi=140)
        fig.clear()
    (directory / 'dane.json').write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    with (directory / 'wyniki.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.writer(handle, delimiter=';')
        if data['kind'] == 'race':
            writer.writerow(['algorytm', 'dlugosc', 'czas_obliczen_ms', 'nadwyzka_wzgledem_optimum_%'])
            for r in data['results']:
                writer.writerow([r['name'], r['length'], r['seconds'] * 1000, r['gap']])
        else:
            writer.writerow(['etap', 'iteracja', 'dlugosc'])
            series = [('przed_blokada', data['before']), ('po_blokadzie', data['after'])] if data['kind'] == 'closure' else [('ACO', data['history'])]
            for stage, values in series:
                writer.writerows((stage, i, length) for i, length in values)
    if data['kind'] == 'race':
        with (directory / 'postep_aco.csv').open('w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.writer(handle, delimiter=';')
            writer.writerow(['iteracja_ACO', 'najlepsza_dlugosc'])
            writer.writerows(data['aco_history'])
    return directory
