import unittest

import numpy as np

from mrowisko.symulacja import SimulationSession


POINTS = [(0, 0), (100, 0), (100, 100), (0, 100)]


class SimulationBehaviourTests(unittest.TestCase):
    def test_closure_report_distinguishes_an_unavailable_route_from_recovery(self):
        session = SimulationSession(POINTS, seed=7, n_ants=20)
        session.iterate(5)
        session.block_best_route()
        pending = session.experiment_data()
        self.assertEqual(pending['kind'], 'closure')
        self.assertFalse(pending['complete'])
        self.assertIsNone(pending['after'][0][1])
        session.iterate(2)
        report = session.experiment_data()
        self.assertTrue(report['complete'])
        self.assertEqual(report['found_after'], 1)
        self.assertEqual(report['iteration_closed'], 5)
        self.assertIsNone(pending['after'][0][1])
        __import__('json').dumps(report, allow_nan=False)

    def test_closure_counts_the_first_recovery_even_when_running_a_batch(self):
        session = SimulationSession(POINTS, seed=7, n_ants=20)
        session.iterate(5)
        old_tour = tuple(session.colony.best_tour)
        session.block_best_route()
        self.assertEqual(session.closure.old_tour, old_tour)
        self.assertIsNone(session.closure.found_after)
        session.iterate(10)
        self.assertEqual(session.closure.found_after, 1)
        self.assertEqual(session.closure.attempts, 10)
        self.assertEqual(session.closure.before[-1], (5, 400))
        self.assertEqual(session.closure.after[0], (5, None))
        self.assertEqual(session.closure.after[1][0], 6)

    def test_pause_freezes_positions_and_next_move_advances_to_a_vertex(self):
        session = SimulationSession(POINTS, seed=7, n_ants=3)
        session.follow(0)
        session.play()
        session.update(0.1, speed=100)
        before = session.ants[0]
        session.pause()
        session.update(10, speed=100)
        self.assertEqual(session.ants[0], before)
        session.next_move()
        after = session.ants[0]
        self.assertEqual(after.position, POINTS[before.destination])
        self.assertFalse(session.running)
        self.assertGreater(after.step, before.step)

    def test_pheromone_changes_once_after_the_last_ant_returns(self):
        session = SimulationSession(POINTS, seed=7, n_ants=3)
        session.follow(0)
        initial = session.colony.tau.copy()
        session.play()
        session.update(0.1, speed=100)
        np.testing.assert_array_equal(session.colony.tau, initial)
        session.update(100, speed=100)
        self.assertEqual(session.colony.iteration, 1)
        self.assertTrue(all(ant.finished for ant in session.ants))
        self.assertFalse(np.array_equal(session.colony.tau, initial))
        session.pause()
        session.update(100)
        self.assertEqual(session.colony.iteration, 1)

    def test_blocking_cancels_pending_journeys_but_preserves_pheromone(self):
        session = SimulationSession(POINTS, seed=7, n_ants=5)
        session.play()
        session.update(100)
        saved = session.colony.tau.copy()
        session.update(0.1)
        session.follow(0)
        session.toggle_block((0, 1))
        self.assertEqual(session.ants, ())
        self.assertIsNone(session.followed)
        np.testing.assert_array_equal(session.colony.tau, saved)
        self.assertEqual(session.colony.probabilities(0)[1], 0)
        session.update(100)
        self.assertEqual(session.colony.iteration, 2)
        self.assertNotIn((0, 1), __import__('algorytmy').tour_edges(session.colony.best_tour))

    def test_shorter_route_emits_a_percentage_improvement(self):
        session = SimulationSession(POINTS, n_ants=1, beta=0, seed=0)
        session.iterate(1)
        self.assertIsNone(session.improvement)
        session.iterate(8)
        self.assertAlmostEqual(session.improvement.previous, 482.842712474619)
        self.assertAlmostEqual(session.improvement.current, 400)
        self.assertAlmostEqual(session.improvement.percent, 17.157287525381)

    def test_finishing_an_iteration_keeps_the_already_drawn_journeys(self):
        session = SimulationSession(POINTS, seed=3, n_ants=3)
        session.follow(0)
        drawn = session.journeys
        session.finish_iteration()
        self.assertEqual(session.colony.iteration, 1)
        self.assertIs(session.journeys, drawn)
        self.assertTrue(all(ant.finished for ant in session.ants))

    def test_changing_ant_count_applies_next_round_without_losing_the_followed_ant(self):
        session = SimulationSession(POINTS, seed=3, n_ants=3)
        session.follow(2)
        session.colony.n_ants = 1
        session.follow(2)
        self.assertEqual(len(session.ants), 3)
        session.finish_iteration()
        session.play()
        session.update(.1)
        self.assertEqual(len(session.ants), 1)
        self.assertEqual(session.followed, 0)


if __name__ == '__main__':
    unittest.main()
