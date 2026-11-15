"""Tworzy dwa kompletne raporty przykładowych eksperymentów bez interfejsu."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mrowisko.raporty import export_experiment  # noqa: E402
from mrowisko.symulacja import SimulationSession  # noqa: E402


def main():
    session = SimulationSession([(0, 0)])
    session.load_scenario('pulapka', width=1000, height=900)
    session.start_race()
    while not session.race.done:
        session.finish_iteration()
    directory = export_experiment(session.experiment_data(), ROOT / 'wyniki' / 'eksperymenty')
    print(f'Wyścig: {directory}')
    session.load_scenario('blokada', width=1000, height=900)
    session.iterate(50)
    session.block_best_route()
    session.iterate(50)
    directory = export_experiment(session.experiment_data(), ROOT / 'wyniki' / 'eksperymenty')
    print(f'Blokada: {directory}')
    print(f'Pierwsze obejście po {session.closure.found_after} iteracjach.')


if __name__ == '__main__':
    main()
