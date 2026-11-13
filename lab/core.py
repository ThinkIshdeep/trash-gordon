from __future__ import annotations
import base64, heapq, io, json, math, threading
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'runtime'

def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and (not math.isfinite(value)):
        return None
    return value

def bounded(p, key, default, lo, hi, integer=False):
    v = float(p.get(key, default))
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f'{key} must be between {lo} and {hi}')
    return int(v) if integer else v

def decoded(p, key='data', limit=4000000):
    try:
        raw = base64.b64decode(p[key], validate=True)
    except (KeyError, ValueError) as e:
        raise ValueError('Upload must contain valid base64 data') from e
    if len(raw) > limit:
        raise ValueError('Upload exceeds the 4 MB application limit')
    return raw

def astar(start, goal, walls, n=18):
    start, goal = (tuple(start), tuple(goal))
    blocked = {tuple(x) for x in walls}
    if start in blocked or goal in blocked:
        return []
    q = [(0, 0, start)]
    prev = {start: None}
    cost = {start: 0}
    while q:
        _, g, u = heapq.heappop(q)
        if u == goal:
            out = []
            while u is not None:
                out.append(list(u))
                u = prev[u]
            return out[::-1]
        if g != cost[u]:
            continue
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            v = (u[0] + dx, u[1] + dy)
            if 0 <= v[0] < n and 0 <= v[1] < n and (v not in blocked) and (g + 1 < cost.get(v, 1000000000.0)):
                cost[v] = g + 1
                prev[v] = u
                heapq.heappush(q, (g + 1 + abs(v[0] - goal[0]) + abs(v[1] - goal[1]), g + 1, v))
    return []

class Base:
    actions = {'reset', 'evaluate'}

    def __init__(self):
        self.state = {}
        self.cancel_event = threading.Event()

    def snapshot(self):
        return clean(self.state)

    def check_cancel(self):
        if self.cancel_event.is_set():
            raise InterruptedError('Job cancelled')

    def dispatch(self, action, p):
        if action == 'state':
            return None
        if action not in self.actions:
            raise ValueError('Unknown project action')
        return getattr(self, action)(p)

    def restore(self, state):
        self.state = state

    def csv_records(self, text):
        import pandas as pd
        if len(text) > 4000000:
            raise ValueError('CSV too large')
        return pd.read_csv(io.StringIO(text))
