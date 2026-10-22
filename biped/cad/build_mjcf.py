"""Genera model/mini16.xml a partir del CAD (lib/params.scad + STL de stl/).

Así la simulación usa las mismas distancias entre ejes, las mismas mallas y masas que las
piezas a imprimir. Correr después de ./export.sh:

  python build_mjcf.py
"""

import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / "model"

PETG_DENSITY, PETG_FILL = 1.27, 0.85  # g/cm3, fracción efectiva (4 perímetros + 35 % relleno)
TPU_DENSITY, TPU_FILL = 1.21, 0.55
SERVO_MASS = 0.055


def read_params():
    out = subprocess.run(["openscad", "-o", "/tmp/_p.echo", str(HERE / "echo_params.scad")],
                         capture_output=True, text=True)
    text = Path("/tmp/_p.echo").read_text() + out.stderr
    vals = dict(re.findall(r'ECHO: "(\w+)", ([-\d.e]+)', text))
    return {k: float(v) for k, v in vals.items()}


def part_mass(name):
    m = trimesh.load(HERE / "stl" / f"left_{name}.stl")
    d, f = (TPU_DENSITY, TPU_FILL) if name == "sole" else (PETG_DENSITY, PETG_FILL)
    return m.volume / 1000 * d * f / 1000  # kg


def servo_frame(Z, X, mirror=False):
    Z, X = np.array(Z, float), np.array(X, float)
    if mirror:
        Z[1], X[1] = -Z[1], -X[1]
    Y = np.cross(Z, X)
    return X, Y


def f(v):
    return " ".join(f"{x:.6g}" for x in v)


def servo_geom(name, origin_mm, Z, X, mirror):
    Xa, Ya = servo_frame(Z, X, mirror)
    o = np.array(origin_mm, float) / 1000
    if mirror:
        o[1] = -o[1]
    return (f'<geom name="{name}" type="mesh" mesh="servo" pos="{f(o)}" xyaxes="{f(Xa)} {f(Ya)}" '
            f'mass="{SERVO_MASS}" rgba="0.12 0.12 0.13 1"/>')


def knee_lo(P):   # límites sin choques medidos con check_leg.py
    return -1.74 if P["SHIN_UP"] else -1.45


def ankle_lo(P):
    return -1.4 if P["SHIN_UP"] else -0.19


def leg_xml(side, P, M):
    s = 1 if side == "left" else -1
    mir = side == "right"
    mm = lambda v: v / 1000  # noqa: E731
    z_yaw = mm(P["D_ROLL_PITCH"] + P["D_YAW_ROLL"])
    def part(n):
        return f'<geom name="{side}_{n}" type="mesh" mesh="{side}_{n}" mass="{M[n]:.4f}" class="petg"/>'
    sole_bottom = -mm(P["D_SOLE"])
    sw = [P["SW_X0"], P["SW_X1"]]
    return f"""
      <body name="{side}_hip_yaw_link" pos="0 {s * mm(P['HIP_Y']):.4f} {z_yaw:.5f}">
        <joint name="{side}_hip_yaw" axis="0 0 1" range="-0.35 0.35"/>
        {part('yaw_link')}
        <body name="{side}_hip_roll_link" pos="0 0 {-mm(P['D_YAW_ROLL']):.5f}">
          <joint name="{side}_hip_roll" axis="1 0 0" range="-0.5 0.5"/>
          {part('roll_link')}
          {servo_geom(f'{side}_hip_roll_servo', [0, 0, 0], [1, 0, 0], [0, 1, 0], mir)}
          {servo_geom(f'{side}_hip_pitch_servo', [0, 0, -P['D_ROLL_PITCH']], [0, 1, 0], [1, 0, 0], mir)}
          <body name="{side}_thigh" pos="0 0 {-mm(P['D_ROLL_PITCH']):.5f}">
            <joint name="{side}_hip_pitch" axis="0 1 0" range="-0.29 1.29"/>
            {part('thigh')}
            {servo_geom(f'{side}_knee_servo', [0, 0, -P['D_THIGH']], [0, 1, 0], [-1, 0, 0], mir)}
            <body name="{side}_shin" pos="0 0 {-mm(P['D_THIGH']):.5f}">
              <joint name="{side}_knee" axis="0 1 0" range="{knee_lo(P)} 0.1"/>
              {part('shin')}
              {servo_geom(f'{side}_ankle_servo', [0, 0, -P['D_SHIN']], [0, 1, 0], [0, 0, 1] if P['SHIN_UP'] else [1, 0, 0], mir)}
              <body name="{side}_ankle_link" pos="0 0 {-mm(P['D_SHIN']):.5f}">
                <joint name="{side}_ankle" axis="0 1 0" range="{ankle_lo(P)} 1.4"/>
                {part('ankle_cross')}
                {servo_geom(f'{side}_ankle_roll_servo', [0, 0, -P['D_ANKLE']], [1, 0, 0], [0, 1, 0], mir)}
                <body name="{side}_foot" pos="0 0 {-mm(P['D_ANKLE']):.5f}">
                  <joint name="{side}_ankle_roll" axis="1 0 0" range="-0.5 0.5"/>
                  <geom name="{side}_foot_plate" type="mesh" mesh="{side}_foot" mass="{M['foot']:.4f}" class="petg"/>
                  <!-- Suela de TPU: es la que toca el piso (forma real, con bordes curvos) -->
                  <geom name="{side}_sole" type="mesh" mesh="{side}_sole" mass="{M['sole']:.4f}" class="tpu"/>
                  <site name="{side}_toe_touch" type="box" pos="{mm(sw[0]):.4f} 0 {sole_bottom + 0.002:.4f}" size="0.012 0.022 0.004" rgba="0 0 0 0"/>
                  <site name="{side}_heel_touch" type="box" pos="{mm(sw[1]):.4f} 0 {sole_bottom + 0.002:.4f}" size="0.012 0.022 0.004" rgba="0 0 0 0"/>
                  <site name="{side}_sole_bottom" pos="0 0 {sole_bottom:.4f}" size="0.002"/>
                </body>
              </body>
            </body>
          </body>
        </body>
      </body>"""


HEAD = """
      <!-- ============================ CUELLO Y CABEZA ============================ -->
      <body name="neck" pos="0 0 {neck_z:.4f}" childclass="micro">
        <joint name="neck_pitch" axis="0 1 0" range="-0.8 0.8"/>
        <geom class="micro_servo"/>
        <geom name="neck" type="box" pos="0 0 0.004" size="0.009 0.012 0.004" mass="0.003" rgba="0.1 0.1 0.11 1"/>
        <body name="head_pitch_link" pos="0 0 0.008">
          <joint name="head_pitch" axis="0 1 0" range="-0.9 0.9"/>
          <geom class="micro_servo"/>
          <body name="head_yaw_link" pos="0 0 0.008">
            <joint name="head_yaw" axis="0 0 1" range="-1.3 1.3"/>
            <geom class="micro_servo" size="0.011 0.011 0.004"/>
            <body name="head" pos="0 0 0.008">
              <joint name="head_roll" axis="1 0 0" range="-0.5 0.5"/>
              <geom class="micro_servo" size="0.011 0.006 0.006"/>
              <geom name="head" type="box" pos="0.02 0 0.024" size="0.042 0.032 0.02" mass="0.04" rgba="0.55 0.82 0.9 1"/>
              <!-- Cámara USB compacta (placa 32 x 32 mm, ~6 g), ~70° de campo horizontal -->
              <geom name="camera_board" type="box" pos="0.0635 0 0.024" size="0.0015 0.016 0.016" mass="0.005"
                    contype="0" conaffinity="0" rgba="0.1 0.35 0.15 1"/>
              <geom name="camera_lens_mount" type="box" pos="0.0665 0 0.026" size="0.0015 0.0055 0.0055" mass="0.001"
                    contype="0" conaffinity="0" rgba="0.08 0.08 0.08 1"/>
              <geom name="camera_lens" type="cylinder" pos="0.069 0 0.026" zaxis="1 0 0" size="0.0038 0.001"
                    contype="0" conaffinity="0" density="0" rgba="0.15 0.2 0.5 1"/>
              <camera name="eye" pos="0.0705 0 0.026" xyaxes="0 -1 0 0 0 1" fovy="55"/>
              <site name="camera" pos="0.0705 0 0.026" size="0.003"/>
            </body>
          </body>
        </body>
      </body>"""


def stand_pose():
    """Postura de pie según la caminata de sim/ (rodillas flexionadas, pies planos)."""
    sys.path.insert(0, str(HERE.parent / "sim"))
    from gait import GaitParams, targets

    p = GaitParams(robot="mini16")
    return p.hip_height, targets(0.0, p, 0, 0)


def build():
    hip_height, q0 = stand_pose()
    P = read_params()
    M = {n: part_mass(n) for n in ["yaw_link", "roll_link", "thigh", "shin", "ankle_cross", "foot", "sole"]}
    mm = lambda v: v / 1000  # noqa: E731
    z_yaw = mm(P["D_ROLL_PITCH"] + P["D_YAW_ROLL"])
    disc = mm(P["S_DISC_Z"] - P["S_CASE"] / 2)          # lo que sobresale el disco
    # Torso: servos yaw abajo (dentro), batería encima, Orange Pi arriba.
    t_bot = z_yaw + disc - 0.002
    s1_top = z_yaw + disc + mm(P["S_CASE"]) + disc
    bat_z0 = s1_top + 0.001
    board_z0 = bat_z0 + 0.019 + 0.001
    t_top = board_z0 + 0.012 + 0.004
    tz, thz = (t_bot + t_top) / 2, (t_top - t_bot) / 2
    tx0, tx1 = -mm(P["S_LONG"]) - 0.004, 0.034
    tcx, thx = (tx0 + tx1) / 2, (tx1 - tx0) / 2
    thy = mm(P["HIP_Y"] + P["S_W"] / 2) + 0.003
    s1 = []
    for side, sgn in (("left", 1), ("right", -1)):
        X, Y = servo_frame([0, 0, -1], [-1, 0, 0], sgn < 0)
        o = [0, sgn * mm(P["HIP_Y"]), z_yaw + mm(P["S_DISC_Z"])]
        s1.append(f'<geom name="{side}_hip_yaw_servo" type="mesh" mesh="servo" pos="{f(o)}" '
                  f'xyaxes="{f(X)} {f(Y)}" mass="{SERVO_MASS}" rgba="0.12 0.12 0.13 1" contype="0" conaffinity="0"/>')

    assets = "\n".join(
        f'    <mesh name="{side}_{n}" file="../cad/stl/{side}_{n}.stl" scale="0.001 0.001 0.001"/>'
        for side in ("left", "right") for n in M)
    xml = f"""<!--
  Mini16 (GENERADO por cad/build_mjcf.py a partir del CAD: no editar a mano).

  Bípedo de 16 motores: 12 Feetech STS3215 en las piernas (cadera yaw/roll/pitch, rodilla,
  tobillo pitch y roll) y 4 Feetech SCS0009 en cuello/cabeza. Distancias entre ejes, mallas y
  masas salen de cad/lib/params.scad y de las piezas exportadas (PETG/TPU).

  Componentes: Orange Pi Zero 3, cámara USB, 2x 18650 + BMS 2S, IMU BNO055,
  ToF VL53L5CX/VL53L8CX, 4x SS-10 (pisada en punta y talón).

  Ejes: x = adelante, y = izquierda, z = arriba. Unidades: m, kg, rad.
  Origen del torso = punto medio entre los ejes de cadera pitch.
-->
<mujoco model="mini16">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" integrator="implicitfast"/>

  <asset>
{assets}
    <mesh name="servo" file="../cad/stl/servo.stl" scale="0.001 0.001 0.001"/>
  </asset>

  <default>
    <geom contype="2" conaffinity="1" friction="0.9 0.02 0.01" condim="3"/>
    <joint damping="0.08" armature="0.01" frictionloss="0.03"/>
    <!-- STS3215 7.4 V: ~1.9 N·m máx. Ganancias estimadas (identificar con servo real). -->
    <position kp="10" kv="0.15" forcerange="-1.9 1.9"/>
    <default class="micro">
      <!-- Feetech SCS0009: ~0.23 N·m a 6 V. Valores estimados. -->
      <joint damping="0.01" armature="0.001" frictionloss="0.005"/>
      <position kp="1.5" kv="0.02" forcerange="-0.22 0.22"/>
    </default>
    <default class="micro_servo">
      <geom type="box" size="0.012 0.011 0.006" mass="0.012" rgba="0.1 0.1 0.11 1"/>
    </default>
    <default class="petg">
      <geom rgba="0.55 0.82 0.9 1"/>
    </default>
    <default class="tpu">
      <geom rgba="0.2 0.2 0.22 1" friction="1.0 0.02 0.01" solref="0.015 1"/>
    </default>
  </default>

  <worldbody>
    <body name="torso" pos="0 0 {hip_height:.4f}">
      <freejoint name="root"/>
      <!-- IMU BNO055 nivelada entre los servos de cadera -->
      <site name="imu" pos="0 0 {z_yaw + 0.02:.4f}" size="0.005"/>
      <geom name="imu_board" type="box" pos="0 0 {z_yaw + 0.018:.4f}" size="0.0105 0.013 0.001" mass="0.003" contype="0" conaffinity="0" rgba="0.1 0.3 0.6 1"/>
      <!-- Torso (PETG): servos yaw abajo, batería 2x18650 encima, Orange Pi Zero 3 arriba;
           atrás: adaptadores de bus, UBEC 5 V, regulador 6 V, BMS 2S y condensador. -->
      <geom name="torso" type="box" pos="{tcx:.4f} 0 {tz:.4f}" size="{thx:.4f} {thy:.4f} {thz:.4f}" mass="0.07" rgba="0.55 0.82 0.9 0.35"/>
      <geom name="battery" type="box" pos="{tcx:.4f} 0 {bat_z0 + 0.0095:.4f}" size="0.0325 0.0185 0.0095" mass="0.098" contype="0" conaffinity="0" rgba="0.2 0.3 0.6 1"/>
      <geom name="orange_pi" type="box" pos="{tcx:.4f} 0 {board_z0 + 0.006:.4f}" size="0.0275 0.025 0.006" mass="0.025" contype="0" conaffinity="0" rgba="0.95 0.5 0.1 1"/>
      <geom name="power_and_bus" type="box" pos="{tx0 + 0.006:.4f} 0 {bat_z0 + 0.012:.4f}" size="0.004 0.035 0.012" mass="0.05" contype="0" conaffinity="0" rgba="0.1 0.5 0.2 1"/>
      <!-- Sensor ToF 8x8 (VL53L5CX / VL53L8CX) al frente, mirando 45° hacia el piso -->
      <geom name="tof_sensor" type="box" pos="{tx1 + 0.001:.4f} 0 {t_bot + 0.012:.4f}" size="0.001 0.0065 0.01" mass="0.002" contype="0" conaffinity="0" rgba="0.1 0.1 0.1 1"/>
      <site name="tof" pos="{tx1 + 0.003:.4f} 0 {t_bot + 0.012:.4f}" zaxis="0.7 0 -0.7" size="0.003"/>
      {s1[0]}
      {s1[1]}
{leg_xml('left', P, M)}
{leg_xml('right', P, M)}
{HEAD.format(neck_z=t_top)}
    </body>
  </worldbody>

  <actuator>
""" + "\n".join(
        f'    <position name="{side}_{j}" joint="{side}_{j}" ctrlrange="{lo} {hi}"/>'
        for side in ("left", "right")
        for j, lo, hi in [("hip_yaw", -0.35, 0.35), ("hip_roll", -0.5, 0.5), ("hip_pitch", -0.29, 1.29),
                          ("knee", knee_lo(P), 0.1), ("ankle", ankle_lo(P), 1.4), ("ankle_roll", -0.5, 0.5)]) + f"""
    <position name="neck_pitch" joint="neck_pitch" class="micro" ctrlrange="-0.8 0.8"/>
    <position name="head_pitch" joint="head_pitch" class="micro" ctrlrange="-0.9 0.9"/>
    <position name="head_yaw" joint="head_yaw" class="micro" ctrlrange="-1.3 1.3"/>
    <position name="head_roll" joint="head_roll" class="micro" ctrlrange="-0.5 0.5"/>
  </actuator>

  <sensor>
    <framequat name="imu_quat" objtype="site" objname="imu"/>
    <gyro name="imu_gyro" site="imu"/>
    <accelerometer name="imu_accel" site="imu"/>
    <touch name="left_toe_touch" site="left_toe_touch"/>
    <touch name="left_heel_touch" site="left_heel_touch"/>
    <touch name="right_toe_touch" site="right_toe_touch"/>
    <touch name="right_heel_touch" site="right_heel_touch"/>
    <rangefinder name="tof" site="tof"/>
  </sensor>

  <keyframe>
    <!-- De pie, rodillas flexionadas (calculado con la cinemática inversa de sim/gait.py) -->
    <key name="home" qpos="0 0 {hip_height + 0.001:.4f} 1 0 0 0 {f(q0)}" ctrl="{f(q0)}"/>
  </keyframe>
</mujoco>
"""
    (MODEL / "mini16.xml").write_text(xml)
    return P, M


if __name__ == "__main__":
    P, M = build()
    print("Distancias (mm):", {k: round(P[k], 2) for k in ["D_YAW_ROLL", "D_ROLL_PITCH", "D_THIGH", "D_SHIN", "D_ANKLE", "D_SOLE", "HIP_Y"]})
    print("Masas plástico por pierna (g):", {k: round(v * 1000, 1) for k, v in M.items()})
