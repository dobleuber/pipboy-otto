"""Pruebas del modelo Mini17 y su caminata. Correr con: python -m pytest -q"""

import mujoco
import numpy as np
import pytest

import common
from common import load, simulate
from gait import GaitParams, leg_ik, targets

LEG_JOINTS = ["hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle", "ankle_roll"]
HEAD_JOINTS = ["neck_pitch", "head_pitch", "head_yaw", "head_roll", "jaw"]


def test_model_has_17_motors_in_expected_order():
    model, _ = load()
    names = [model.actuator(i).name for i in range(model.nu)]
    expected = [f"left_{j}" for j in LEG_JOINTS] + [f"right_{j}" for j in LEG_JOINTS] + HEAD_JOINTS
    assert names == expected


def test_size_and_mass():
    model, data = load()
    mass = model.body_subtreemass[model.body("torso").id]
    assert 0.9 < mass < 1.2  # ~1.07 kg
    head = model.geom("head").id
    head_top = data.geom_xpos[head][2] + model.geom_size[head][2]
    assert 0.21 < head_top < 0.26  # ~23 cm


def test_stands_still():
    model, data = load()
    for _ in range(int(3 / model.opt.timestep)):
        mujoco.mj_step(model, data)
    assert not common.fallen(data)
    assert common.torso_tilt(data) < np.radians(3)


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("target", [(0.0, 0.0, -0.065), (0.015, 0.008, -0.06), (-0.012, -0.006, -0.055)])
def test_leg_ik_matches_model(side, target):
    """Los ángulos de leg_ik() deben llevar el tobillo del modelo al punto pedido."""
    model, data = load()
    roll, pitch, knee, ankle = leg_ik(*target)
    joints = [("hip_yaw", 0), ("hip_roll", roll), ("hip_pitch", pitch), ("knee", knee), ("ankle", ankle), ("ankle_roll", -roll)]
    for name, q in joints:
        data.qpos[model.jnt_qposadr[model.joint(f"{side}_{name}").id]] = q
    data.qpos[:7] = [0, 0, 0.5, 1, 0, 0, 0]
    mujoco.mj_kinematics(model, data)
    hip_rest_y = model.body(f"{side}_hip_yaw_link").pos[1]
    # El punto de referencia es el eje de cadera pitch con roll = 0.
    ref = np.array([0, hip_rest_y, 0.5])
    ankle_pos = data.xanchor[model.joint(f"{side}_ankle").id]
    np.testing.assert_allclose(ankle_pos - ref, target, atol=1e-3)
    # Pie plano: paralelo al torso en pitch y en roll (tobillo roll = -cadera roll).
    foot_R = data.xmat[model.body(f"{side}_foot").id].reshape(3, 3)
    np.testing.assert_allclose(foot_R[2], [0, 0, 1], atol=1e-3)


def test_targets_within_servo_limits():
    model, _ = load()
    lo, hi = model.actuator_ctrlrange.T
    for p in [GaitParams(), GaitParams(turn=0.35), GaitParams(turn=-0.35)]:
        for t in np.linspace(0, 6, 300):
            q = targets(t, p)
            assert np.all(q >= lo - 1e-9) and np.all(q <= hi + 1e-9)


def test_walks_forward_within_servo_limits():
    out = simulate(GaitParams(), 10)
    assert out["fell_at"] is None
    assert out["x"] > 0.3  # > 3 cm/s
    assert abs(out["y"]) < 0.1
    assert abs(out["yaw_deg"]) < 10  # casi recto
    assert out["p99_leg_torque"] < 1.3  # < ~70 % del torque máximo del STS3215
    assert out["max_cmd_vel"] < 4.5  # STS3215 ~4.7 rad/s sin carga


def test_turns_both_ways_within_servo_limits():
    for turn, sign in [(0.3, 1), (-0.3, -1)]:
        out = simulate(GaitParams(turn=turn), 10)
        assert out["fell_at"] is None
        assert sign * out["yaw_deg"] > 60
        assert out["p99_leg_torque"] < 1.3
        assert out["max_cmd_vel"] < 4.5


@pytest.mark.parametrize("angle", [10, 15])
def test_climbs_ramps(angle):
    from terrain import load_with_ramp, ramp_progress

    out = simulate(GaitParams(), 20, load_fn=lambda: load_with_ramp(angle))
    assert out["fell_at"] is None
    assert ramp_progress(out) > 0.3
