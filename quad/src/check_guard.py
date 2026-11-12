"""Check gait.legs_clear against the CAD: it must never call a pose clear that the parts' solids collide in.

    cad run src/robot.py        # prints the model's id
    python3 src/check_guard.py <id>

40 random poses, biased towards both legs of a side reaching inward (where they can meet), each judged by
`cad model interference` on the exact solids and by the guard.
"""
import json
import os
import random
import subprocess
import sys

from gait import legs_clear

random.seed(7)
poses = []
while len(poses) < 40:
    q = {}
    for n, sx in (("f", 1), ("r", -1)):
        for side in "lr":
            q[f"hip_{n}{side}"] = round(sx * random.uniform(-10, 45), 1)
            q[f"knee_{n}{side}"] = round(random.uniform(-45, 45), 1)
    poses.append(q)

cmd = [os.path.expanduser("~/.local/bin/cad"), "model", "interference", sys.argv[1], "--json"]
for q in poses:
    cmd += ["--pose", json.dumps(q)]
result = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
norm = lambda q: tuple(sorted(q.items()))
collide = {norm(json.loads(pose)) for row in result["measurements"]["overlaps"] for pose in row["poses"]}
assert not result["measurements"].get("unmeasured"), "a pair could not be measured: no verdict"

table = {}
for q in poses:
    key = (legs_clear(q), norm(q) in collide)
    table[key] = table.get(key, 0) + 1
print(f"CAD collides in {len(collide)} of {len(poses)} poses")
print(f"guard clear, CAD clear: {table.get((True, False), 0)}")
print(f"guard refuses, CAD collides: {table.get((False, True), 0)}")
print(f"guard refuses, CAD clear (conservative): {table.get((False, False), 0)}")
print(f"guard clear, CAD COLLIDES: {table.get((True, True), 0)}")
assert collide, "no pose collided: the check shows nothing"
assert table.get((True, True), 0) == 0, "the guard called a colliding pose clear"
