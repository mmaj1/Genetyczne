import unittest

from mrowisko.symulacja import SimulationSession
from algorytmy import brute_force, nearest_neighbor, tour_length, distance_matrix


class PresentationBehaviourTests(unittest.TestCase):
    def test_loading_a_scenario_resets_the_show_and_repeats_the_same_choices(self):
        session = SimulationSession([(0, 0), (1, 0), (0, 1)])
        session.load_scenario('pierwsza')
        session.follow(0)
        first = session.ants
        session.play()
        session.update(100)
        session.toggle_block((0, 1))
        session.load_scenario('pierwsza')
        self.assertFalse(session.running)
        self.assertEqual(session.colony.iteration, 0)
        self.assertEqual(session.blocked, set())
        self.assertIsNone(session.followed)
        self.assertIsNone(session.improvement)
        session.follow(0)
        self.assertEqual(session.ants, first)

    def test_presentation_examples_demonstrate_their_named_effects(self):
        session = SimulationSession([(0, 0), (1, 0), (0, 1)])
        session.load_scenario('pulapka')
        dist = distance_matrix(session.points)
        self.assertGreater(tour_length(nearest_neighbor(dist), dist),
                           1.25 * tour_length(brute_force(dist), dist))
        session.load_scenario('bez_feromonu')
        session.colony.tau[0, 1] *= 1000
        before = session.colony.probabilities(0)
        session.colony.tau[0, 2] *= 1000
        self.assertEqual(session.colony.alpha, 0)
        self.assertEqual(tuple(before), tuple(session.colony.probabilities(0)))

    def test_road_closure_waits_for_a_route_and_then_preserves_learning(self):
        session = SimulationSession([(0, 0), (1, 0), (0, 1)])
        session.load_scenario('blokada')
        self.assertIsNone(session.block_best_route())
        session.iterate(20)
        learned = session.colony.tau.copy()
        edge = session.block_best_route()
        self.assertIn(edge, session.blocked)
        self.assertEqual(session.colony.iteration, 20)
        self.assertEqual(learned.tolist(), session.colony.tau.tolist())
        session.iterate(20)
        from algorytmy import uses_blocked
        self.assertFalse(uses_blocked(session.colony.best_tour, session.blocked))


if __name__ == '__main__':
    unittest.main()
