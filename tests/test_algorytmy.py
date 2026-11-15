import unittest

import numpy as np

from algorytmy import (AntColony, distance_matrix, tour_edges, tour_length,
                       brute_force, nearest_neighbor, two_opt)


class ColonyBehaviourTests(unittest.TestCase):
    def test_blocked_edge_is_impossible_even_without_distance_weight(self):
        colony = AntColony(distance_matrix([(0, 0), (1, 0), (0, 1), (1, 1)], {(0, 1)}),
                           alpha=0, beta=0, seed=4)
        self.assertEqual(colony.probabilities(0)[1], 0)
        colony.run(12)
        self.assertIsNotNone(colony.best_tour)
        self.assertNotIn((0, 1), tour_edges(colony.best_tour))

    def test_journey_records_the_actual_draw_and_its_original_probabilities(self):
        colony = AntColony(distance_matrix([(0, 0), (1, 0), (2, 0)]),
                           n_ants=1, beta=1, seed=0)
        journey = colony.construct_journeys()[0]
        decision = journey.decisions[0]
        self.assertEqual(decision.source, 0)
        self.assertAlmostEqual(decision.probabilities[1], 2 / 3)
        self.assertAlmostEqual(decision.probabilities[2], 1 / 3)
        self.assertEqual(decision.destination, journey.tour[1])
        colony.beta = 0
        self.assertAlmostEqual(decision.probabilities[1], 2 / 3)
        self.assertEqual(journey.decisions[-1].destination, 0)
        self.assertTrue(journey.complete)

    def test_comparison_never_reports_a_blocked_route_as_a_solution(self):
        dist = distance_matrix([(0, 0), (1, 0), (1, 1), (0, 1)], {(0, 1)})
        self.assertEqual(tour_length([0, 1, 2, 3], dist), float('inf'))
        for solve in (brute_force, nearest_neighbor, two_opt):
            tour = solve(dist)
            if tour is not None:
                self.assertEqual(set(tour), {0, 1, 2, 3})
                self.assertNotIn((0, 1), tour_edges(tour))
        isolated = distance_matrix([(0, 0), (1, 0), (0, 1)], {(0, 1), (0, 2)})
        for solve in (brute_force, nearest_neighbor, two_opt):
            self.assertIsNone(solve(isolated))


if __name__ == '__main__':
    unittest.main()
