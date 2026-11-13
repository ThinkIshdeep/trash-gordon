import base64, io, json, math, unittest
import numpy as np
from lab.core import astar, clean
from lab import robot

class CoreTests(unittest.TestCase):

    def test_astar_routes_around_wall(self):
        path = astar([0, 0], [4, 4], [[2, y] for y in range(4)], 5)
        self.assertEqual(path[-1], [4, 4])
        self.assertTrue(all((p[0] != 2 or p[1] == 4 for p in path)))

    def test_astar_impossible(self):
        self.assertEqual(astar([0, 0], [2, 2], [[1, y] for y in range(3)], 3), [])

    def test_json_serialization(self):
        self.assertEqual(clean({'a': np.int64(2), 'b': float('nan')}), {'a': 2, 'b': None})

class RobotTests(unittest.TestCase):

    def test_here_grounding(self):
        e = robot.Engine()
        e.target({'x': 15, 'y': 15})
        e.command({'text': 'dustbin come here'})
        self.assertEqual(e.state['target'], [15, 15])

    def test_motion_interlock(self):
        e = robot.Engine()
        e.mechanism({'kind': 'open'})
        with self.assertRaises(ValueError):
            e.command({'text': 'go to sofa'})

    def test_complete_bag_sequence(self):
        e = robot.Engine()
        e.mechanism({'kind': 'seal'})
        for _ in range(12):
            e.step({})
        self.assertEqual(e.state['bag'], 'sealed')
        e.mechanism({'kind': 'remove'})
        e.mechanism({'kind': 'inflate'})
        for _ in range(12):
            e.step({})
        self.assertEqual(e.state['bag'], 'ready')
        self.assertEqual(e.state['cartridges'], 3)

    def test_dynamic_replan(self):
        e = robot.Engine()
        e.command({'text': 'go to door'})
        blocked = e.state['path'][0]
        e.obstacle({'x': blocked[0], 'y': blocked[1]})
        e.step({})
        self.assertNotEqual(e.state['position'], blocked)

    def test_stop_clears_path(self):
        e = robot.Engine()
        e.command({'text': 'go to kitchen'})
        e.command({'text': 'stop'})
        self.assertFalse(e.state['path'])
