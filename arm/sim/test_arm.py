"""Pruebas de la simulación del brazo en la mesa. Correr con: MUJOCO_GL=osmesa python -m pytest -q

(La primera vez descarga el modelo del SO-101 de MuJoCo Menagerie.)
"""

import mujoco
import numpy as np
import pytest

import scene
from control import REST, Arm, detect_face


def test_scene_builds_with_arm_table_objects_person():
    m = scene.build()
    assert m.nu == 6  # 5 articulaciones + pinza
    for name in ("cube", "ball", "can", "person", "table"):
        assert mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, name) >= 0 or name == "table"
    assert abs(m.body_subtreemass[m.body("base").id] - 0.645) < 0.02  # brazo ~645 g


def test_rest_pose_camera_upright_and_sees_face():
    m = scene.build()
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    arm.set_pose(REST)
    _, Rc = arm.cam_frame()
    assert Rc[2, 1] > 0.8  # el "arriba" de la imagen apunta hacia arriba
    r = mujoco.Renderer(m, 120, 160)
    r.update_scene(d, camera="wrist_cam")
    hit = detect_face(r.render())
    assert hit is not None and abs(hit[0]) < 0.5


def test_tracks_person_and_greets_twice():
    import demo_track

    out = demo_track.run()
    states = out["states"]
    greetings = sum(1 for i, s in enumerate(states) if s == "saludar" and (i == 0 or states[i - 1] != "saludar"))
    assert greetings == 2  # al empezar y cuando la persona vuelve
    assert out["track_err_median_deg"] < 5
    assert out["max_torque"] < scene.STALL_TORQUE["7.4V"]  # alcanza con los servos de 7.4 V


@pytest.mark.parametrize("volts,mass", [("7.4V", 0.03), ("7.4V", 0.3), ("12V", 0.6)])
def test_grasps_holds_and_places_back(volts, mass):
    import demo_hold

    out = demo_hold.run("cube", mass, volts)
    assert out["held"] and out["placed_back"]
    assert np.all(out["hold_torque"] < scene.STALL_TORQUE[volts])


# ----------------------------------------------------------------------------- morral
def test_backpack_rest_pose_keeps_distance_from_head():
    import backpack as bp
    import demo_walk as dw

    m = bp.build()
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    arm.set_pose(REST)
    assert dw.Safety(m, d, bp.Wearer(m, d)).head_distance() > dw.SAFE_DIST


def test_looks_at_people_while_walking():
    import demo_walk as dw

    out = dw.run_look(imu=True, predict=True)
    assert out["greetings"] >= 2
    assert out["err_median"] < 5 and out["err_p90"] < 12
    assert out["min_head"] > dw.SAFE_DIST - 0.01  # nunca entra a la zona de la cabeza
    assert out["max_torque"] < scene.STALL_TORQUE["7.4V"]


@pytest.mark.parametrize("mass", [0.1, 0.3])
def test_holds_box_while_walking(mass):
    import demo_walk as dw

    out = dw.run_hold(mass, "12V")
    assert out["held"] and out["slip_mm"] < 15
    assert out["max_torque"] < scene.STALL_TORQUE["12V"]


def test_fold_hinge_protects_arm_from_branch():
    """Rama a 1.74 m: con la bisagra el brazo se dobla y recibe mucho menos golpe que rígido."""
    import demo_walk as dw

    hinge = dw.run_snag(rigid=False, height=1.74)
    rigid = dw.run_snag(rigid=True, height=1.74)
    assert hinge["max_fold_deg"] > 60  # se dobló hacia atrás
    assert hinge["max_crush"] < rigid["max_crush"] / 2
    assert hinge["min_head"] > 0.09  # al doblarse se aleja de la cabeza


def test_hinge_stays_closed_while_walking():
    import demo_walk as dw

    out = dw.run_look(imu=True, predict=True, seconds=12)
    assert out["max_fold_deg"] < 1.0


def test_cad_and_sim_agree():
    """Las medidas del soporte en la simulación son las de arm/cad/params.scad."""
    import re
    import shutil
    import subprocess
    from pathlib import Path

    import backpack as bp

    if shutil.which("openscad") is None:
        pytest.skip("OpenSCAD no instalado")
    cad = Path(__file__).resolve().parent.parent / "cad"
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        echo = Path(tmp) / "p.echo"
        subprocess.run(["openscad", "-o", str(echo), str(cad / "echo_params.scad")], capture_output=True, check=True)
        vals = dict(re.findall(r'"P:(\w+)=(.+?)"', echo.read_text()))
    vec = lambda k: np.array([float(x) for x in vals[k].strip("[]").split(",")]) / 1000  # noqa: E731
    arm_base = vec("ARM_BASE")
    np.testing.assert_allclose(arm_base, bp.MOUNT, atol=1e-6)
    np.testing.assert_allclose(vec("HINGE") - arm_base, bp.HINGE_REL, atol=1e-4)
    np.testing.assert_allclose(vec("FOOT_AT") - arm_base, bp.TUBE_FROM, atol=1e-4)
    np.testing.assert_allclose(vec("HEAD_AT") - arm_base, bp.TUBE_TO, atol=1e-4)
    assert float(vals["FOLD_TORQUE"]) == bp.FOLD_TORQUE
