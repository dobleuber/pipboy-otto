"""Demo 3: el brazo en el morral, sobre el hombro derecho, mientras la persona camina.

Uso:
  python demo_walk.py                     # mirar: sigue a la gente de la vereda (con y sin IMU)
  python demo_walk.py --video walk.mp4    # con video
  python demo_walk.py --hold              # sostener una caja mientras camina (pesos y voltajes)
  python demo_walk.py --hold --mass 0.2 --video hold_walk.mp4

Seguridad (siempre activa): la base no gira hacia la cabeza (PAN_MIN) y, si una parte del brazo
queda a menos de SAFE_DIST de la cabeza, el brazo se retira a la postura de reposo.
"""

import argparse

import mujoco
import numpy as np

import backpack as bp
import scene
from control import CONTROL_HZ, REST, Arm, TargetMotion, detect_face, look_velocity, ray_world, reach_velocity

DET_W, DET_H = 160, 120
PAN_MIN, PAN_MAX = -0.15, 1.9  # rad: negativo = hacia la cabeza (el brazo va en el hombro derecho)
SAFE_DIST = 0.10  # m, distancia mínima entre el brazo y la cabeza


class Safety:
    """Distancia del brazo a la cabeza del usuario (con las formas de choque del brazo)."""

    def __init__(self, m, d, wearer):
        self.m, self.d, self.wearer = m, d, wearer
        arm_bodies = {m.body(n).id for n in ("upper_arm", "lower_arm", "wrist", "gripper", "moving_jaw_so101_v1")}
        self.geoms = [g for g in range(m.ngeom) if m.geom_bodyid[g] in arm_bodies and m.geom_group[g] == 3
                      and m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH]
        self.head = m.geom("wearer_head").id
        self.events = 0

    def head_distance(self):
        """Distancia mínima (m) entre las formas de choque del brazo y la cabeza."""
        ft = np.zeros(6)
        return min(mujoco.mj_geomDistance(self.m, self.d, g, self.head, 1.0, ft) for g in self.geoms)

    def filter(self, arm, dq):
        """Devuelve la velocidad segura: si está muy cerca, se retira a REST."""
        if self.head_distance() < SAFE_DIST:
            self.events += 1
            return 2.0 * (REST - self.d.qpos[arm.qadr])
        return dq


def _walker(m, d, wearer, t0=0.0, fold_torque=bp.FOLD_TORQUE):
    """Mueve al usuario en cada paso de la física (si no, el soporte recibe tirones) y aplica los
    imanes de la bisagra."""

    def f():
        wearer.update(d.time - t0, m.opt.timestep)
        bp.magnets(m, d, fold_torque)

    return f


def base_omega(m, d):
    """Velocidad angular de la base (IMU del soporte), en el marco del mundo."""
    s = m.site("mount_imu").id
    return d.site_xmat[s].reshape(3, 3) @ d.sensor("mount_gyro").data


def mount_loads(m, d):
    """Fuerza (N) y momento (N·m) que el soporte hace sobre la base del brazo."""
    mujoco.mj_rnePostConstraint(m, d)
    b = m.body("base").id
    tau_c, f = d.cfrc_int[b][:3], d.cfrc_int[b][3:]
    c = d.subtree_com[m.body_rootid[b]]
    tau_p = tau_c + np.cross(c - d.xpos[b], f)
    return float(np.linalg.norm(f)), float(np.linalg.norm(tau_p))


def run_look(imu=True, video=None, volts="12V", seconds=19.0, predict=True, fit="ajustado"):
    m = bp.build(volts, fit)
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    arm.set_pose(REST)
    arm.grip_cmd = 0.0
    wearer = bp.Wearer(m, d)
    safety = Safety(m, d, wearer)
    det = mujoco.Renderer(m, DET_H, DET_W)
    faces = [m.geom(f"{n}_face").id for n, _, _ in bp.BYSTANDERS]
    rec = Recorder(m, "Mirar caminando" + (" (con IMU)" if imu else " (sin IMU)")) if video else None

    walk = _walker(m, d, wearer)
    walk()
    mujoco.mj_forward(m, d)
    state, lost_for, nod_until = "buscar", 0.0, -1
    motion = TargetMotion(1 / CONTROL_HZ)
    st = dict(err=[], err_t=[], torque=[], head=[], force=[], moment=[], states=[], fold=[], shake=[])
    for k in range(int(seconds * CONTROL_HZ)):
        t = k / CONTROL_HZ
        det.update_scene(d, camera="wrist_cam")
        img = det.render()
        hit = detect_face(img)
        if hit:
            lost_for = 0.0
            if state == "buscar":
                state, nod_until = "saludar", t + 1.2
        else:
            lost_for += 1 / CONTROL_HZ
            if lost_for > 0.8:
                state = "buscar"
        w_base = base_omega(m, d) if imu else None
        w_target = motion.update(ray_world(arm, *hit[:2]) if hit else None) if predict else None
        if state == "buscar":
            target = REST.copy()
            target[0] = 0.75 + 0.9 * np.sin(2 * np.pi * t / 6)  # barre adelante y a la derecha
            dq = 2.0 * (target - d.qpos[arm.qadr])
        else:
            dq = look_velocity(arm, *(hit[:2] if hit else (0.0, 0.0)), base_omega=w_base, target_omega=w_target)
            if state == "saludar":
                dq[3] += 1.5 * np.cos(2 * np.pi * 1.6 * t)
                if t > nod_until:
                    state = "seguir"
        dq = safety.filter(arm, dq)
        arm.move(dq)
        arm.q_cmd[0] = np.clip(arm.q_cmd[0], PAN_MIN, PAN_MAX)
        arm.step(walk)

        cpos, Rc = arm.cam_frame()
        if state == "seguir" and hit:
            # Error contra la cara más cercana a la dirección de la mirada
            view = -Rc[:, 2]
            angs = [np.degrees(np.arccos(np.clip(view @ (d.geom_xpos[f] - cpos) / np.linalg.norm(d.geom_xpos[f] - cpos), -1, 1)))
                    for f in faces]
            st["err"].append(min(angs))
            st["err_t"].append((t, min(angs), int(np.argmin(angs))))
        st["torque"].append(np.abs(d.actuator_force[arm.act]).max())
        st["head"].append(safety.head_distance())
        f, mo = mount_loads(m, d)
        st["force"].append(f)
        st["moment"].append(mo)
        st["states"].append(state)
        st["fold"].append(-d.qpos[m.joint("fold").qposadr[0]])
        st["shake"].append(np.linalg.norm(base_omega(m, d)))
        if rec:
            rec.frame(d, img, state, hit, t, wearer)
    if rec:
        rec.save(video)
    err = np.array(st["err"]) if st["err"] else np.array([np.nan])
    states = st["states"]
    return {
        "err_median": float(np.median(err)), "err_p90": float(np.percentile(err, 90)),
        "greetings": sum(1 for i, s in enumerate(states) if s == "saludar" and (i == 0 or states[i - 1] != "saludar")),
        "max_torque": float(np.max(st["torque"])), "p99_torque": float(np.percentile(st["torque"], 99)),
        "min_head": float(np.min(st["head"])), "safety_events": safety.events,
        "max_force": float(np.max(st["force"])), "max_moment": float(np.max(st["moment"])),
        "max_fold_deg": float(np.degrees(np.max(st["fold"]))),
        "shake_rms": float(np.sqrt(np.mean(np.square(st["shake"])))),  # giro de la base (rad/s)
        "err_series": st["err_t"], "states": states,
    }


# Pinza respecto de la base: 28 cm adelante, 8 a la derecha y 12 arriba (a la altura del pecho y la
# cara, como sosteniendo un celular). Con 5 articulaciones la pinza tiene que apuntar hacia donde
# está (no puede correrse de lado apuntando recto adelante).
def _wearer_load(m, d, wearer, ext_body=None, ext_force=None):
    """Fuerza (N) y momento (N·m, respecto del centro de los hombros) que el usuario tiene que hacer
    para sostener todo lo que cuelga del morral: masa x aceleración - peso - fuerzas externas.
    (No incluye la inercia de giro de cada pieza, que es chica.)"""
    mujoco.mj_rnePostConstraint(m, d)
    W = d.mocap_pos[wearer.ids["wearer"]]
    g = m.opt.gravity
    F, M = np.zeros(3), np.zeros(3)
    acc = np.zeros(6)
    root = m.body("mount").id
    for b in range(m.nbody):
        if m.body_rootid[b] != root:
            continue
        mujoco.mj_objectAcceleration(m, d, mujoco.mjtObj.mjOBJ_BODY, b, acc, 0)
        f = m.body_mass[b] * (acc[3:] - g)
        F += f
        M += np.cross(d.xipos[b] - W, f)
    if ext_body is not None:
        F -= ext_force
        M -= np.cross(d.xipos[ext_body] - W, ext_force)
    return float(np.linalg.norm(F)), float(np.linalg.norm(M))


def run_snag(rigid=False, seconds=11.0, video=None, height=1.78):
    """Caminando, el brazo choca con una rama a `height` m del lado derecho (no toca la cabeza).

    rigid=True: soporte sin bisagra, para comparar.
    """
    m = bp.build(rigid=rigid, branch=height)
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    arm.set_pose(REST)
    wearer = bp.Wearer(m, d)
    safety = Safety(m, d, wearer)
    walk = _walker(m, d, wearer)
    walk()
    mujoco.mj_forward(m, d)
    fold_q = m.joint("fold").qposadr[0]
    branch = m.geom("branch").id
    rec = Recorder(m, f"Rama a {height:.2f} m: " + ("soporte rígido" if rigid else "con bisagra")) if video else None
    st = dict(fold=[], load=[], moment=[], torque=[], head=[], hit=[], crush=[])
    for k in range(int(seconds * CONTROL_HZ)):
        t = k / CONTROL_HZ
        arm.move(2.0 * (REST - d.qpos[arm.qadr]))
        arm.step(walk)
        f, mo = _wearer_load(m, d, wearer)
        touching, crush = False, 0.0
        cf = np.zeros(6)
        for i in range(d.ncon):
            c = d.contact[i]
            if branch in (c.geom1, c.geom2):
                touching = True
                mujoco.mj_contactForce(m, d, i, cf)
                crush += abs(cf[0])
        st["crush"].append(crush)
        st["fold"].append(-d.qpos[fold_q])
        st["load"].append(f)
        st["moment"].append(mo)
        st["torque"].append(np.abs(d.actuator_force[arm.act]).max())
        st["head"].append(safety.head_distance())
        st["hit"].append(touching)
        if rec:
            rec.frame(d, None, "reposo", None, t, wearer)
    if rec:
        rec.save(video)
    hit = np.array(st["hit"])
    idx = np.nonzero(hit)[0]
    win = slice(max(0, idx[0] - 5), idx[-1] + 15) if len(idx) else slice(0, 0)
    walking = slice(25, idx[0] - 10) if len(idx) else slice(25, None)
    return {
        "contact_s": float(hit.sum() / CONTROL_HZ),
        "max_crush": float(np.max(st["crush"])),  # N: fuerza de la rama contra el brazo
        "max_fold_deg": float(np.degrees(np.max(st["fold"]))),
        "fold_after_deg": float(np.degrees(st["fold"][-1])),
        "peak_moment": float(np.max(st["moment"][win])) if len(idx) else 0.0,
        "walking_moment": float(np.max(st["moment"][walking])),
        "peak_force": float(np.max(st["load"][win])) if len(idx) else 0.0,
        "walking_force": float(np.max(st["load"][walking])),
        "peak_servo_torque": float(np.max(st["torque"][win])) if len(idx) else 0.0,
        "min_head": float(np.min(st["head"])),
    }


HOLD_TARGET = np.array([0.28, -0.08, 0.12])
HOLD_APPROACH = np.array([HOLD_TARGET[0], HOLD_TARGET[1], 0.0]) / np.linalg.norm(HOLD_TARGET[:2])
HOLD_SEED = np.array([0.2, -0.8, 0.66, 0.14, -1.56])  # punto de partida de la cinemática inversa


# Caja agarrada: posición y orientación en el marco de la pinza, y ángulo de la mandíbula
GRASP_REL = np.array([0.00314, 0.01202, 0.00375])
GRASP_QUAT = np.array([0.49974, 0.49891, 0.50479, 0.49652])
GRASP_JAW = 0.311


def _quat_mat(q):
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q / np.linalg.norm(q))
    return R.reshape(3, 3)


def _to_world(m, d, p_local, v_local=None):
    b = m.body("base").id
    R = d.xmat[b].reshape(3, 3)
    return d.xpos[b] + R @ p_local, (None if v_local is None else R @ v_local)


def _hold_pose(m, d, arm):
    """Postura para sostener (cinemática inversa sin física, con el usuario quieto)."""
    q = HOLD_SEED.copy()
    for _ in range(400):
        arm.set_pose(q)
        tgt, app = _to_world(m, d, HOLD_TARGET, HOLD_APPROACH)
        dq, err = reach_velocity(arm, tgt, app)
        q = np.clip(q + dq * 0.02, arm.lo + 0.02, arm.hi - 0.02)
    return q, err


def run_hold(mass=0.2, volts="12V", video=None, seconds=17.0):
    m = _add_box(volts, mass)
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    wearer = bp.Wearer(m, d)
    q_hold, ik_err = _hold_pose(m, d, arm)
    arm.set_pose(q_hold)
    # Empieza con la caja ya agarrada, en la posición donde queda tras cerrar la pinza (medida en
    # una simulación de agarre con 200 g). Cerrar la pinza en la simulación con cajas livianas es
    # frágil: el apretón las expulsa.
    box = m.body("box").id
    jq = m.jnt_qposadr[m.body_jntadr[box]]
    p, R = arm.site_pose()
    Rb = R @ _quat_mat(GRASP_QUAT)
    qb = np.zeros(4)
    mujoco.mju_mat2Quat(qb, Rb.flatten())
    d.qpos[jq : jq + 3] = p + R @ GRASP_REL
    d.qpos[jq + 3 : jq + 7] = qb
    d.qpos[arm.gq] = GRASP_JAW
    arm.grip_cmd = -0.17
    mujoco.mj_forward(m, d)
    for _ in range(int(0.5 * CONTROL_HZ)):  # se acomoda quieto antes de caminar
        arm.step()
    t0 = d.time
    walk = _walker(m, d, wearer, t0)
    rec = Recorder(m, f"Sosteniendo {mass * 1000:.0f} g caminando ({volts})") if video else None
    st = dict(torque=[], force=[], moment=[], acc=[])
    prev_v = None
    R0 = arm.site_pose()[1]
    rel0 = R0.T @ (d.xpos[box] - arm.site_pose()[0])  # posición de la caja en la pinza al empezar
    for k in range(int(seconds * CONTROL_HZ)):
        t = k / CONTROL_HZ
        arm.move(2.0 * (q_hold - arm.q_cmd))
        arm.step(walk)
        st["torque"].append(np.abs(d.actuator_force[arm.act]))
        f, mo = mount_loads(m, d)
        st["force"].append(f)
        st["moment"].append(mo)
        v = d.qvel[m.jnt_dofadr[m.body_jntadr[box]] : m.jnt_dofadr[m.body_jntadr[box]] + 3].copy()
        if prev_v is not None:
            st["acc"].append(np.linalg.norm(v - prev_v) * CONTROL_HZ)
        prev_v = v
        if rec:
            rec.frame(d, None, "sostener", None, t, wearer)
    if rec:
        rec.save(video)
    T = np.array(st["torque"])
    p, R = arm.site_pose()
    slip = float(np.linalg.norm(R.T @ (d.xpos[box] - p) - rel0))  # cuánto se deslizó en la pinza
    held = slip < 0.02 and d.xpos[box][2] > 1.0
    return {
        "mass_g": mass * 1000, "volts": volts, "held": bool(held), "slip_mm": slip * 1000, "ik_err_mm": ik_err * 1000,
        "p99_torque": float(np.percentile(T.max(1), 99)), "max_torque": float(T.max()),
        "max_force": float(np.max(st["force"])), "max_moment": float(np.max(st["moment"])),
        "p99_box_acc": float(np.percentile(st["acc"], 99)),
    }


def _add_box(volts, mass):
    """La escena del morral con una caja de 4 x 4 x 6 cm para sostener."""
    spec = bp.build_spec(volts)
    b = spec.worldbody.add_body()
    b.name, b.pos = "box", [0, 0, 3]
    b.add_freejoint()
    scene._geom(b, "box", scene.B, (0.02, 0.02, 0.03), rgba=(0.1, 0.75, 0.2, 1), mass=mass, condim=4,
                friction=[1.0, 0.03, 0.003], solref=[0.01, 1])
    return spec.compile()


class Recorder:
    LABEL = {"buscar": "buscando...", "saludar": "¡hola!", "seguir": "siguiendo", "sostener": "sosteniendo",
             "reposo": "en reposo"}

    def __init__(self, m, title):
        from PIL import ImageFont

        self.r = mujoco.Renderer(m, 480, 640)
        self.cam_r = mujoco.Renderer(m, 168, 224)
        self.frames, self.title = [], title
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)

    def frame(self, d, cam_img, state, hit, t, wearer):
        from PIL import Image, ImageDraw

        self.r.update_scene(d, camera="follow")
        big = Image.fromarray(self.r.render())
        if cam_img is None:
            self.cam_r.update_scene(d, camera="wrist_cam")
            cam_img = self.cam_r.render()
        small = Image.fromarray(cam_img).resize((224, 168))
        if hit:
            dr = ImageDraw.Draw(small)
            u, v, size = hit
            cx, cy = (u + 1) / 2 * 224, (v + 1) / 2 * 168
            rad = max(6, 120 * np.sqrt(size))
            dr.rectangle([cx - rad, cy - rad, cx + rad, cy + rad], outline=(60, 230, 90), width=3)
        big.paste(small, (8, 8))
        dr = ImageDraw.Draw(big)
        dr.rectangle([8, 8, 232, 176], outline=(255, 255, 255), width=2)
        dr.text((12, 180), "cámara del brazo", fill=(255, 255, 255), font=self.font)
        dr.text((250, 10), self.title, fill=(255, 255, 255), font=self.font)
        speed = wearer.walk.speed(t)
        dr.text((250, 36), f"{self.LABEL[state]}   {t:4.1f} s   caminando {speed * 3.6:.1f} km/h"
                if speed > 0.05 else f"{self.LABEL[state]}   {t:4.1f} s   parado", fill=(255, 230, 90), font=self.font)
        self.frames.append(np.array(big))

    def save(self, path):
        import imageio.v2 as iio

        iio.mimsave(path, self.frames, fps=CONTROL_HZ, macro_block_size=1)
        print("Video guardado en", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", action="store_true", help="sostener una caja mientras camina")
    ap.add_argument("--mass", type=float, help="kg (con --hold)")
    ap.add_argument("--volts", default="12V", choices=list(scene.STALL_TORQUE))
    ap.add_argument("--video")
    args = ap.parse_args()
    if args.hold:
        cases = ([(args.mass, args.volts)] if args.mass else
                 [(mm, v) for v in ("7.4V", "12V") for mm in (0.1, 0.2, 0.3)])
        for mass, volts in cases:
            o = run_hold(mass, volts, args.video if args.mass else None)
            print(f"{o['volts']:5s} {o['mass_g']:4.0f} g  sostiene={'sí' if o['held'] else 'NO'} (se deslizó {o['slip_mm']:.0f} mm)  "
                  f"torque p99 {o['p99_torque']:.2f} / máx {o['max_torque']:.2f} N·m (límite {scene.STALL_TORQUE[volts]})  "
                  f"soporte: {o['max_force']:.0f} N, {o['max_moment']:.2f} N·m  sacudida de la caja p99 {o['p99_box_acc']:.1f} m/s²")
        return
    for imu in (True, False):
        o = run_look(imu, args.video if imu else None, args.volts)
        o.pop("err_series"), o.pop("states")
        print(f"{'Con IMU' if imu else 'Sin IMU'}: error de mirada mediana {o['err_median']:.1f}°, p90 {o['err_p90']:.1f}° | "
              f"saludos {o['greetings']} | torque máx {o['max_torque']:.2f} N·m | "
              f"distancia mínima a la cabeza {o['min_head'] * 100:.0f} cm (retiros: {o['safety_events']}) | "
              f"soporte: {o['max_force']:.0f} N, {o['max_moment']:.2f} N·m")


if __name__ == "__main__":
    main()
