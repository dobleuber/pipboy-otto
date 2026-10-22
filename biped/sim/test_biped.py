"""Pruebas básicas del modelo y la caminata. Correr con: python -m pytest -q"""

import mujoco
import numpy as np

import common
from common import load, simulate
from gait import GaitParams, targets


def test_model_loads_with_6_servos():
    model, _ = load()
    assert model.nu == 6
    names = [model.actuator(i).name for i in range(model.nu)]
    assert names == [
        "left_hip_pitch",
        "left_ankle_pitch",
        "left_ankle_roll",
        "right_hip_pitch",
        "right_ankle_pitch",
        "right_ankle_roll",
    ]


def test_size_and_mass():
    model, data = load()
    mass = model.body_subtreemass[model.body("torso").id]
    assert 0.6 < mass < 1.0  # ~0.8 kg
    head_top = data.geom_xpos[model.geom("head").id][2] + model.geom_size[model.geom("head").id][0]
    assert 0.23 < head_top < 0.29  # ~26 cm


def test_stands_still():
    model, data = load()
    for _ in range(int(3 / model.opt.timestep)):
        mujoco.mj_step(model, data)
    assert not common.fallen(data)
    assert common.torso_tilt(data) < np.radians(3)


def test_targets_within_servo_limits():
    model, _ = load()
    lo, hi = model.actuator_ctrlrange.T
    p = GaitParams(turn=0.6)
    for t in np.linspace(0, 5, 200):
        q = targets(t, p)
        assert np.all(q >= lo) and np.all(q <= hi)


def test_walks_forward_without_falling():
    out = simulate(GaitParams(), 10)
    assert out["fell_at"] is None
    assert out["x"] > 0.5  # > 5 cm/s
    assert abs(out["y"]) < 0.15  # casi recto


def test_turns_both_ways():
    left = simulate(GaitParams(turn=0.4), 10)
    right = simulate(GaitParams(turn=-0.4), 10)
    assert left["fell_at"] is None and right["fell_at"] is None
    assert left["y"] > 0.15 and right["y"] < -0.15
