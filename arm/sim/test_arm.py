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
