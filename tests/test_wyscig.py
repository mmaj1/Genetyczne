import unittest
import json

from mrowisko.symulacja import SimulationSession


SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]


class RaceBehaviourTests(unittest.TestCase):
    def test_a_map_without_a_cycle_never_reports_a_solution_or_zero_gap(self):
        session = SimulationSession([(0, 0), (1, 0), (0, 1)], n_ants=5, seed=7)
        session.toggle_block((0, 1))
        session.toggle_block((0, 2))
        session.start_race(iterations=3)
        for _ in range(10):
            session.finish_iteration()
        data = session.experiment_data()
        self.assertTrue(data['complete'])
        self.assertTrue(data['optimum_known'])
        self.assertIsNone(data['optimum'])
        for result in data['results']:
            self.assertIsNone(result['tour'])
            self.assertIsNone(result['length'])
            self.assertIsNone(result['gap'])
        json.dumps(data, allow_nan=False)

    def test_experiment_snapshot_contains_real_results_and_is_json_safe(self):
        session = SimulationSession(SQUARE, seed=7, n_ants=5)
        session.start_race(iterations=8)
        for _ in range(12):
            session.finish_iteration()
        data = session.experiment_data()
        self.assertEqual(data['kind'], 'race')
        self.assertTrue(data['complete'])
        self.assertEqual(data['optimum'], 400)
        self.assertEqual(data['aco_iterations'], 8)
        self.assertEqual({r['key'] for r in data['results']}, {'aco', 'nn', '2opt'})
        self.assertTrue(all(r['length'] == 400 for r in data['results']))
        json.dumps(data, allow_nan=False)
        session.leave_race()
        session.block_best_route()
        self.assertEqual(data['blocked'], [])

    def test_race_uses_shared_time_and_pause_without_changing_the_live_colony(self):
        session = SimulationSession(SQUARE, seed=7, n_ants=5)
        session.start_race(iterations=8)
        session.play()
        session.update(.12)
        self.assertEqual(session.race.steps, 1)
        self.assertEqual(session.colony.iteration, 0)
        session.pause()
        session.update(10)
        self.assertEqual(session.race.steps, 1)
        session.toggle_block((0, 1))
        self.assertFalse(session.race_mode)
        self.assertIsNone(session.race)

    def test_three_algorithms_finish_on_one_map_with_a_known_optimum(self):
        session = SimulationSession(SQUARE, seed=7, n_ants=5)
        session.start_race(iterations=8)
        for _ in range(20):
            session.finish_iteration()
        race = session.race
        self.assertEqual(race.points, tuple(SQUARE))
        self.assertEqual(race.optimum, 400)
        self.assertTrue(race.done)
        self.assertFalse(session.running)
        self.assertEqual(race.lanes['nn'].length, 400)
        self.assertEqual(race.lanes['2opt'].length, 400)
        for lane in race.lanes.values():
            self.assertEqual(set(lane.tour), {0, 1, 2, 3})
            self.assertGreaterEqual(lane.compute_seconds, 0)
            self.assertAlmostEqual(race.gap(lane), 0)


if __name__ == '__main__':
    unittest.main()
