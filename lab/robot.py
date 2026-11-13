import math, re
from .core import Base, astar, bounded

class Engine(Base):
    actions = Base.actions | {'command', 'step', 'mechanism', 'target', 'obstacle'}

    def __init__(self):
        super().__init__()
        self.reset({})

    def reset(self, p):
        walls = [[x, y] for x in range(6, 10) for y in range(6, 9)] + [[x, y] for x in range(12, 15) for y in range(3, 7)] + [[x, y] for x in range(2, 6) for y in range(12, 14)]
        self.state = {'n': 18, 'position': [2, 2], 'speaker': [14, 14], 'heading': 0.0, 'dock': [2, 2], 'battery': 100.0, 'fill': 25.0, 'mission': 'ready', 'lid': 'closed', 'bag': 'ready', 'bag_timer': 0, 'cartridges': 4, 'path': [], 'target': None, 'walls': walls, 'landmarks': {'sofa': [4, 11], 'table': [7, 10], 'kitchen': [13, 8], 'door': [16, 15], 'dock': [2, 2]}, 'log': [], 'tick': 0, 'last_result': None, 'collision_count': 0}

    def log(self, text):
        self.state['log'] = [{'tick': self.state['tick'], 'text': text}] + self.state['log'][:59]

    def target(self, p):
        x = bounded(p, 'x', 14, 0, 17, True)
        y = bounded(p, 'y', 14, 0, 17, True)
        if [x, y] in self.state['walls']:
            raise ValueError('Speaker marker must be in free space')
        self.state['speaker'] = [x, y]
        self.log(f'Speaker location set to ({x}, {y}).')

    def route(self, goal):
        s = self.state
        if s['bag'] != 'ready' or s['lid'] != 'closed':
            raise ValueError('Close lid and finish bag service before movement')
        path = astar(s['position'], goal, s['walls'], 18)
        s['target'] = goal
        s['path'] = path[1:]
        s['mission'] = 'navigating' if path else 'blocked'
        self.log('Destination grounded at ' + str(goal) + ('. Route planned.' if path else '. Route unavailable.'))

    def command(self, p):
        text = str(p.get('text', '')).strip().lower()
        if not text:
            raise ValueError('Enter a command')
        if re.search('\\b(stop|cancel|halt)\\b', text):
            self.state.update(path=[], mission='ready')
            self.log('Motion stopped.')
            return
        if 'open' in text:
            return self.mechanism({'kind': 'open'})
        if 'close' in text:
            return self.mechanism({'kind': 'close'})
        if 'seal' in text:
            return self.mechanism({'kind': 'seal'})
        if 'inflate' in text or 'new bag' in text:
            return self.mechanism({'kind': 'inflate'})
        goal = None
        for name, cell in self.state['landmarks'].items():
            if name in text:
                goal = cell[:]
                break
        if goal is None and re.search('\\b(here|me)\\b', text):
            goal = self.state['speaker'][:]
        if goal is None:
            raise ValueError('Destination unclear. Use here, sofa, table, kitchen, door, or dock.')
        self.route(goal)
        return {'transcript': text, 'grounded_target': goal, 'location_source': 'explicit room marker or named landmark'}

    def mechanism(self, p):
        s = self.state
        k = p.get('kind')
        if k == 'deposit':
            if s['lid'] != 'open':
                raise ValueError('Open the lid first')
            s['fill'] = min(100, s['fill'] + 15)
            self.log('Simulated waste deposited.')
            return
        if k == 'open':
            if s['mission'] in ['navigating', 'docking'] or s['bag'] != 'ready':
                raise ValueError('Robot must be stationary with bag ready')
            s['lid'] = 'open'
        elif k == 'close':
            s['lid'] = 'closed'
        elif k == 'seal':
            if s['mission'] not in ['ready', 'charging'] or s['lid'] != 'closed' or s['bag'] != 'ready':
                raise ValueError('Stationary robot and closed lid required')
            s.update(bag='sealing', bag_timer=0, mission='bag service', path=[])
        elif k == 'remove':
            if s['bag'] != 'sealed':
                raise ValueError('Seal the bag before removal')
            s.update(bag='empty', fill=0.0, mission='bag service')
        elif k == 'inflate':
            if s['bag'] != 'empty' or s['cartridges'] <= 0:
                raise ValueError('Remove old bag and ensure a spare cartridge is available')
            s.update(bag='inflating', bag_timer=0, mission='bag service')
            s['cartridges'] -= 1
        else:
            raise ValueError('Unknown mechanism operation')
        self.log('Mechanism: ' + str(k) + '.')

    def obstacle(self, p):
        cell = [bounded(p, 'x', 10, 0, 17, True), bounded(p, 'y', 10, 0, 17, True)]
        if cell in [self.state['position'], self.state['dock'], self.state['speaker']]:
            raise ValueError('Cannot place obstacle on robot, dock, or speaker')
        if cell in self.state['walls']:
            self.state['walls'].remove(cell)
        else:
            self.state['walls'].append(cell)
        self.log('Obstacle map updated.')

    def step(self, p):
        s = self.state
        s['tick'] += 1
        if s['bag'] in ['sealing', 'inflating']:
            s['bag_timer'] += 1
            if s['bag_timer'] >= 12:
                s['bag'] = 'sealed' if s['bag'] == 'sealing' else 'ready'
                s['mission'] = 'bag service' if s['bag'] == 'sealed' else 'ready'
                self.log('Bag sequence complete: ' + s['bag'])
        elif s['mission'] in ['navigating', 'docking', 'blocked'] and s['target']:
            if not s['path'] or s['path'][0] in s['walls']:
                s['path'] = astar(s['position'], s['target'], s['walls'], 18)[1:]
                s['mission'] = 'navigating' if s['path'] else 'ready' if s['position'] == s['target'] else 'blocked'
            if s['path']:
                nxt = s['path'].pop(0)
                assert nxt not in s['walls']
                dx = nxt[0] - s['position'][0]
                dy = nxt[1] - s['position'][1]
                s['heading'] = math.atan2(dx, dy)
                s['position'] = nxt
                s['battery'] = max(0, s['battery'] - 0.06)
                if not s['path']:
                    s['mission'] = 'charging' if s['position'] == s['dock'] else 'ready'
                    self.log('Destination reached.')
        elif s['mission'] == 'charging':
            s['battery'] = min(100, s['battery'] + 0.2)
        if s['battery'] < 12 and s['bag'] == 'ready' and (s['lid'] == 'closed') and (s['target'] != s['dock']):
            self.route(s['dock'][:])
            self.log('Low battery: returning to dock.')

    def evaluate(self, p):
        import numpy as np
        success = 0
        collisions = 0
        for seed in range(20):
            self.check_cancel()
            e = Engine()
            r = np.random.default_rng(900 + seed)
            free = [[x, y] for x in range(18) for y in range(18) if [x, y] not in e.state['walls']]
            goal = free[int(r.integers(len(free)))]
            path = astar(e.state['position'], goal, e.state['walls'], 18)
            if not path:
                continue
            e.route(goal)
            for _ in range(80):
                e.step({})
            success += e.state['position'] == goal
            collisions += e.state['collision_count']
        e = Engine()
        e.mechanism({'kind': 'seal'})
        interlock = False
        try:
            e.route([5, 5])
        except ValueError:
            interlock = True
        out = {'navigation_tasks': 20, 'successes': success, 'collisions': collisions, 'bag_motion_interlock': interlock, 'note': 'Twenty seeded goal checks in the authored room; physical sensors, SLAM, sealing and inflation are not validated.'}
        self.state['last_result'] = out
        return out
