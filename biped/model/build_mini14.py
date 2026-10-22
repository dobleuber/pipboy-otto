"""Genera model/mini14.xml: bípedo de 14 servos XL330 diseñado con lo aprendido del Microduck.

Ideas de diseño (ver LECCIONES.md):
  - Servos chicos (Dynamixel XL330-M288-T, 18 g) alimentados directo con 2S (7.4 V).
  - 5 por pierna, sin tobillo roll. Piernas cortas: cadera a ~10 cm del piso.
  - Cabeza pesada y móvil (4 servos) con la batería adentro: sirve de contrapeso.
  - Servos modelados con los parámetros identificados por BAM para el XL330 (Rhoban/bam).

Correr:  python build_mini14.py   (escribe mini14.xml junto a este archivo)
Todas las medidas están en P: cambiar ahí y volver a correr.
"""

from pathlib import Path

import numpy as np

# ------------------------------------------------------------------------------------------
# Medidas (m, kg)
# ------------------------------------------------------------------------------------------
P = dict(
    # Servo XL330-M288-T: 20 x 34 x 26 mm (el eje atraviesa los 26 mm), 18 g.
    # El eje está a 10 mm de un extremo del lado de 34 mm.
    servo=(0.034, 0.020, 0.026),
    servo_axis_from_end=0.010,
    servo_mass=0.018,
    # Pierna (distancias entre ejes)
    hip_y=0.036,  # separación de cada pierna al centro
    yaw_to_roll=0.016,  # disco de cadera yaw -> eje roll
    roll_to_pitch=0.024,  # eje roll -> eje pitch
    thigh=0.045,  # cadera pitch -> rodilla
    shin=0.045,  # rodilla -> tobillo
    ankle_to_sole=0.022,  # tobillo -> suela
    foot=(0.080, 0.042),  # largo, ancho
    foot_x=0.008,  # la punta sobresale más que el talón
    # Altura de pie (cadera pitch sobre la suela)
    stand_hip=0.100,
    # Cuello y cabeza
    neck_pitch=(0.016, 0.075),  # (x, z) del eje de cuello pitch respecto del torso
    neck=0.030,  # cuello pitch -> cabeza pitch
    head=(0.070, 0.074, 0.044),  # caja de la cabeza (x, y, z)
    # Masas de componentes (kg)
    battery=0.104,  # 2x 18650 + soporte + BMS 2S, en la cabeza
    head_shell=0.030,
    head_sensors=0.008,  # cámara USB + ToF
    trunk_shell=0.045,
    trunk_electronics=0.070,  # Orange Pi Zero 3, interfaz de bus, UBEC 5 V, IMU, cables
    neck_link=0.008,
    yaw_link=0.006,
    roll_link=0.008,
    thigh_link=0.012,
    shin_link=0.010,
    foot_plate=0.014,
    sole=0.006,  # TPU
)

# XL330 a 7.4 V con parámetros BAM (params/xl330/m6.json, export a MuJoCo de bam.to_mujoco):
#   forcerange = vin*kt/R, damping = viscosa + kt^2/R, kp = 0.002877 * kp_fw * vin * kt / R
KP_FW = 400  # ganancia P del firmware (400 = valor de fábrica; el Microduck usa 200)
VIN, KT, R = 7.4, 0.346, 2.50
XL330 = dict(
    kp=0.002877 * KP_FW * VIN * KT / R,
    forcerange=VIN * KT / R,
    damping=0.0058 + KT**2 / R,
    frictionloss=0.012,
    armature=0.0016,
)


def f(*v):
    return " ".join(f"{x:.5g}" for x in v)


def servo_geom(name, center, axis, along, stator_body_note=""):
    """Caja de un servo. axis = eje de giro ('x','y','z'); along = eje del lado de 34 mm."""
    L, W, H = P["servo"]
    size = {"x": 0, "y": 0, "z": 0}
    size[axis] = H / 2
    size[along] = L / 2
    other = ({"x", "y", "z"} - {axis, along}).pop()
    size[other] = W / 2
    return (
        f'<geom name="{name}" class="servo" pos="{f(*center)}" '
        f'size="{f(size["x"], size["y"], size["z"])}"/>'
    )


def leg(side):
    s = 1 if side == "left" else -1
    p = P
    L = p["servo"][0]
    off = L / 2 - p["servo_axis_from_end"]  # del eje al centro del servo, a lo largo de los 34 mm
    yaw_z = p["roll_to_pitch"] + p["yaw_to_roll"]
    fl, fw = p["foot"]
    sole_t = 0.006
    return f"""
      <body name="{side}_hip_yaw_link" pos="0 {s * p['hip_y']:.4f} {yaw_z:.4f}">
        <joint name="{side}_hip_yaw" axis="0 0 1" range="-0.45 0.45"/>
        <geom name="{side}_yaw_bracket" type="box" pos="0 0 -0.005" size="0.012 0.012 0.002"
              mass="{p['yaw_link']}" class="plastic"/>
        {servo_geom(f"{side}_hip_roll_servo", (0, s * off, -p['yaw_to_roll']), "x", "y")}
        <body name="{side}_hip_roll_link" pos="0 0 {-p['yaw_to_roll']:.4f}">
          <joint name="{side}_hip_roll" axis="1 0 0" range="-0.4 0.4"/>
          <geom name="{side}_roll_bracket" type="box" pos="0 0 -0.012" size="0.013 0.015 0.002"
                mass="{p['roll_link']}" class="plastic"/>
          {servo_geom(f"{side}_hip_pitch_servo", (-off, 0, -p['roll_to_pitch']), "y", "x")}
          <body name="{side}_thigh" pos="0 0 {-p['roll_to_pitch']:.4f}">
            <joint name="{side}_hip_pitch" axis="0 1 0" range="-0.9 1.6"/>
            <geom class="hub"/>
            <geom name="{side}_thigh" type="box" pos="0 {s * 0.0145:.4f} {-p['thigh'] / 2:.4f}"
                  size="0.010 0.0015 {p['thigh'] / 2:.4f}" mass="{p['thigh_link']}" class="plastic"/>
            {servo_geom(f"{side}_knee_servo", (0, 0, -p['thigh'] + off), "y", "z")}
            <body name="{side}_shin" pos="0 0 {-p['thigh']:.4f}">
              <joint name="{side}_knee" axis="0 1 0" range="-2.3 0.1"/>
              <geom class="hub"/>
              <geom name="{side}_shin" type="box" pos="0 {s * 0.0145:.4f} {-p['shin'] / 2:.4f}"
                    size="0.010 0.0015 {p['shin'] / 2:.4f}" mass="{p['shin_link']}" class="plastic"/>
              {servo_geom(f"{side}_ankle_servo", (0, 0, -p['shin'] + off), "y", "z")}
              <body name="{side}_foot" pos="0 0 {-p['shin']:.4f}">
                <joint name="{side}_ankle" axis="0 1 0" range="-1.4 1.4"/>
                <geom class="hub"/>
                <geom name="{side}_foot_plate" type="box" pos="{p['foot_x']:.4f} 0 {-p['ankle_to_sole'] + sole_t + 0.002:.4f}"
                      size="{fl / 2 - 0.004:.4f} {fw / 2 - 0.002:.4f} 0.002" mass="{p['foot_plate']}" class="plastic"/>
                <geom name="{side}_sole" class="tpu" type="box"
                      pos="{p['foot_x']:.4f} 0 {-p['ankle_to_sole'] + sole_t / 2:.4f}"
                      size="{fl / 2:.4f} {fw / 2:.4f} {sole_t / 2:.4f}" mass="{p['sole']}"/>
                <site name="{side}_foot_touch" type="box" pos="{p['foot_x']:.4f} 0 {-p['ankle_to_sole']:.4f}"
                      size="{fl / 2 + 0.002:.4f} {fw / 2 + 0.002:.4f} 0.003" rgba="0 0 0 0"/>
                <site name="{side}_toe" type="box" pos="{p['foot_x'] + fl / 4:.4f} 0 {-p['ankle_to_sole']:.4f}"
                      size="{fl / 4 + 0.002:.4f} {fw / 2 + 0.002:.4f} 0.003" rgba="0 0 0 0"/>
                <site name="{side}_heel" type="box" pos="{p['foot_x'] - fl / 4:.4f} 0 {-p['ankle_to_sole']:.4f}"
                      size="{fl / 4 + 0.002:.4f} {fw / 2 + 0.002:.4f} 0.003" rgba="0 0 0 0"/>
              </body>
            </body>
          </body>
        </body>
      </body>"""


def head():
    p = P
    nx, nz = p["neck_pitch"]
    hx, hy, hz = p["head"]
    L = p["servo"][0]
    off = L / 2 - p["servo_axis_from_end"]
    # Ejes: cuello pitch (torso) -> cabeza pitch (cuello) -> cabeza yaw -> cabeza roll (en la cabeza).
    return f"""
      {servo_geom("neck_pitch_servo", (nx - off, 0, nz), "y", "x")}
      <body name="neck" pos="{nx:.4f} 0 {nz:.4f}">
        <joint name="neck_pitch" axis="0 1 0" range="-0.9 1.0"/>
        <geom class="hub" size="0.009 0.0145"/>
        <geom name="neck" type="box" pos="0 0 {p['neck'] / 2:.4f}" size="0.010 0.0145 {p['neck'] / 2:.4f}"
              mass="{p['neck_link']}" class="plastic"/>
        {servo_geom("head_pitch_servo", (0, 0, p['neck'] - off), "y", "z")}
        <body name="head_pitch_link" pos="0 0 {p['neck']:.4f}">
          <joint name="head_pitch" axis="0 1 0" range="-1.2 1.2"/>
          <geom class="hub" size="0.009 0.0145"/>
          {servo_geom("head_yaw_servo", (0, 0, 0.012 + 0.013), "z", "x")}
          <body name="head_yaw_link" pos="0 0 0.012">
            <joint name="head_yaw" axis="0 0 1" range="-1.5 1.5"/>
            {servo_geom("head_roll_servo", (0, 0, 0.030), "x", "y")}
            <body name="head" pos="0 0 0.030">
              <joint name="head_roll" axis="1 0 0" range="-0.45 0.45"/>
              <geom name="head" type="box" pos="0.012 0 {hz / 2 - 0.012:.4f}" size="{hx / 2:.4f} {hy / 2:.4f} {hz / 2:.4f}"
                    mass="{p['head_shell']}" class="shell"/>
              <!-- Batería 2x18650 acostada a lo ancho, atrás en la cabeza -->
              <geom name="battery" type="box" pos="-0.006 0 {hz / 2 - 0.012:.4f}" size="0.019 0.034 0.0095"
                    mass="{p['battery']}" rgba="0.2 0.3 0.6 1" contype="0" conaffinity="0"/>
              <geom name="sensors" type="box" pos="{0.012 + hx / 2 - 0.004:.4f} 0 {hz / 2 - 0.012:.4f}"
                    size="0.004 0.014 0.012" mass="{p['head_sensors']}" rgba="0.1 0.1 0.1 1"
                    contype="0" conaffinity="0"/>
              <geom type="cylinder" pos="{0.012 + hx / 2:.4f} 0 {hz / 2 - 0.006:.4f}" zaxis="1 0 0" size="0.011 0.0015"
                    contype="0" conaffinity="0" density="0" rgba="0.98 0.6 0.15 1"/>
              <geom type="cylinder" pos="{0.012 + hx / 2 + 0.0015:.4f} 0 {hz / 2 - 0.006:.4f}" zaxis="1 0 0" size="0.006 0.0015"
                    contype="0" conaffinity="0" density="0" rgba="0.05 0.05 0.05 1"/>
              <camera name="eye" pos="{0.012 + hx / 2 + 0.004:.4f} 0 {hz / 2 - 0.006:.4f}" xyaxes="0 -1 0 0 0 1" fovy="70"/>
              <site name="camera" pos="{0.012 + hx / 2 + 0.004:.4f} 0 {hz / 2 - 0.006:.4f}" size="0.003"/>
              <!-- ToF 8x8 bajo la cámara, mirando 45° al piso -->
              <site name="tof" pos="{0.012 + hx / 2 + 0.002:.4f} 0 {hz / 2 - 0.026:.4f}" size="0.003"
                    zaxis="0.7071 0 -0.7071"/>
            </body>
          </body>
        </body>
      </body>"""


def stand_pose():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
    from gait import leg_ik  # noqa: E402
    import robots  # noqa: E402

    rb = robots.get("mini14")
    roll, pitch, knee, ankle = leg_ik(0.0, 0.0, -(P["stand_hip"] - P["ankle_to_sole"]), rb)
    return [0.0, roll, pitch, knee, ankle]


def build():
    p = P
    L = p["servo"][0]
    off = L / 2 - p["servo_axis_from_end"]
    yaw_z = p["roll_to_pitch"] + p["yaw_to_roll"]
    leg_q = stand_pose()
    head_q = [0.0, 0.0, 0.0, 0.0]
    q = leg_q + leg_q + head_q
    z0 = p["stand_hip"]
    joints = [f"{s}_{j}" for s in ("left", "right") for j in ("hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle")]
    joints += ["neck_pitch", "head_pitch", "head_yaw", "head_roll"]

    xml = f"""<!--
  Mini14: GENERADO por build_mini14.py (no editar a mano).

  14 servos Dynamixel XL330-M288-T a 7.4 V (2S):
    Cada pierna (5): cadera yaw, cadera roll, cadera pitch, rodilla, tobillo pitch
    Cuello/cabeza (4): cuello pitch, cabeza pitch, cabeza yaw, cabeza roll
  La batería (2x18650) va en la cabeza: es el contrapeso, como la cabeza del Microduck.

  Ejes: x = adelante, y = izquierda, z = arriba. Origen del torso = altura de cadera pitch.
  Servos: parámetros BAM del XL330 (kp de firmware {KP_FW}).
-->
<mujoco model="mini14">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" integrator="implicitfast"/>

  <default>
    <geom contype="2" conaffinity="1" friction="0.9 0.02 0.01" condim="3"/>
    <joint damping="{XL330['damping']:.4f}" armature="{XL330['armature']}" frictionloss="{XL330['frictionloss']}"/>
    <position kp="{XL330['kp']:.4f}" kv="0" forcerange="-{XL330['forcerange']:.3f} {XL330['forcerange']:.3f}"/>
    <default class="servo">
      <geom type="box" mass="{p['servo_mass']}" rgba="0.1 0.1 0.11 1" contype="0" conaffinity="0"/>
    </default>
    <default class="hub">
      <geom type="cylinder" size="0.008 0.0135" zaxis="0 1 0" contype="0" conaffinity="0" density="0"
            rgba="0.75 0.75 0.78 1"/>
    </default>
    <default class="plastic">
      <geom contype="0" conaffinity="0" rgba="0.95 0.95 0.92 1"/>
    </default>
    <default class="shell">
      <geom type="box" rgba="0.95 0.95 0.92 1"/>
    </default>
    <default class="tpu">
      <geom rgba="0.2 0.2 0.22 1" friction="1.0 0.02 0.01" solref="0.015 1"/>
    </default>
  </default>

  <worldbody>
    <body name="torso" pos="0 0 {z0:.4f}">
      <freejoint name="root"/>
      <site name="imu" pos="0 0 {yaw_z + 0.03:.4f}" size="0.005"/>
      <geom name="torso" class="shell" pos="-0.002 0 {yaw_z + 0.032:.4f}" size="0.036 0.046 0.036"
            mass="{p['trunk_shell']}"/>
      <!-- Orange Pi Zero 3 vertical contra la espalda; UBEC, interfaz de bus e IMU -->
      <geom name="electronics" type="box" pos="-0.028 0 {yaw_z + 0.035:.4f}" size="0.006 0.027 0.025"
            mass="{p['trunk_electronics']}" rgba="0.1 0.5 0.2 1" contype="0" conaffinity="0"/>
      {servo_geom("left_hip_yaw_servo", (-off, p['hip_y'], yaw_z + 0.013), "z", "x")}
      {servo_geom("right_hip_yaw_servo", (-off, -p['hip_y'], yaw_z + 0.013), "z", "x")}
{leg("left")}
{leg("right")}
{head()}
    </body>
  </worldbody>

  <actuator>
{chr(10).join(f'    <position name="{j}" joint="{j}" ctrlrange="-2.3 1.6"/>' for j in joints)}
  </actuator>

  <sensor>
    <framequat name="imu_quat" objtype="site" objname="imu"/>
    <gyro name="imu_gyro" site="imu"/>
    <accelerometer name="imu_accel" site="imu"/>
    <touch name="left_foot_touch" site="left_foot_touch"/>
    <touch name="right_foot_touch" site="right_foot_touch"/>
    <touch name="left_toe" site="left_toe"/>
    <touch name="left_heel" site="left_heel"/>
    <touch name="right_toe" site="right_toe"/>
    <touch name="right_heel" site="right_heel"/>
    <rangefinder name="tof" site="tof"/>
  </sensor>

  <keyframe>
    <key name="home" qpos="0 0 {z0:.4f} 1 0 0 0 {f(*q)}" ctrl="{f(*q)}"/>
  </keyframe>
</mujoco>
"""
    out = Path(__file__).resolve().parent / "mini14.xml"
    out.write_text(xml)
    scene = (Path(__file__).resolve().parent / "scene_mini13.xml").read_text()
    (out.parent / "scene_mini14.xml").write_text(scene.replace("mini13", "mini14"))
    print(f"Escrito {out}")


if __name__ == "__main__":
    build()
