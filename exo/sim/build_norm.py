"""Build normative gait curves (walk + run) from the public Fukuchi datasets.

Input  : raw files downloaded by fetch_data.py into <raw>/walk and <raw>/run
Output : exo/data/gait_norm.json  (101-point curves, right-leg convention)

Sagittal conventions used everywhere in this project
  angles  [deg]   hip +flexion, knee +flexion, ankle +dorsiflexion
  moments [Nm/kg] internal; hip +EXTENSOR, knee +EXTENSOR, ankle +PLANTARFLEXOR
  grf     [N/kg]  ap +forward (propulsion), v +up
"""
import csv, glob, json, os, sys
import numpy as np

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "gait_norm.json")
FS_FORCE = 300.0  # Hz, both datasets


def load(fn):
    with open(fn, encoding="latin1") as f:
        lines = f.read().strip().split("\n")
    head = lines[0].split("\t")
    def num(x):
        x = x.strip()
        try:
            return float(x)
        except ValueError:
            return np.nan
    arr = np.array([[num(x) for x in l.split("\t")] for l in lines[1:]])
    return head, arr


def stride_time(fy, steps_per_cycle):
    """Dominant period of a vertical-force signal via autocorrelation."""
    fy = fy[np.isfinite(fy)]
    fy = fy - fy.mean()
    n = len(fy)
    spec = np.fft.rfft(fy, 2 * n)
    ac = np.fft.irfft(spec * np.conj(spec))[:n]
    ac /= ac[0]
    # running: one plate sees both feet -> search the STEP period (0.25-0.48 s, 125-240 steps/min)
    # walking: one plate per belt -> search the STRIDE period (0.8-1.6 s)
    lo, hi = (int(0.25 * FS_FORCE), int(0.48 * FS_FORCE)) if steps_per_cycle == 2 else (int(0.8 * FS_FORCE), int(1.6 * FS_FORCE))
    k = lo + int(np.argmax(ac[lo:hi]))
    # parabolic refinement
    y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
    k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return steps_per_cycle * k / FS_FORCE


def lowpass_periodic(y, nharm):
    c = np.fft.rfft(y)
    c[nharm + 1:] = 0
    return np.fft.irfft(c, len(y))


LIMIT = dict(hip_ang=120, knee_ang=160, ankle_ang=70, pelvis_tilt=60, hip_mom=8, knee_mom=8, ankle_mom=8,
             grf_v=45, grf_ap=12)


def finish(curves, nh_ang=10, nh_mom=14, nh_grf=20):
    """Average across subjects, low-pass as a periodic signal (100 samples, 0..99 %)."""
    out = {}
    for k, stack in curves.items():
        a = np.array(stack)[:, :100]
        a = a[np.nanmax(np.abs(a), axis=1) < LIMIT[k]]      # reject sentinel / corrupt trials
        m = np.nanmean(a, axis=0)
        s = np.nanstd(a, axis=0)
        m = np.nan_to_num(m)
        nh = nh_ang if k.endswith("_ang") or k == "pelvis_tilt" else (nh_grf if k.startswith("grf") else nh_mom)
        m = lowpass_periodic(m, nh)
        if k == "grf_v":
            m = np.clip(m, 0, None)
        out[k] = {"mean": [round(float(x), 4) for x in m], "sd": [round(float(x), 4) for x in np.nan_to_num(s)]}
    return out


def build_walk():
    info = list(csv.DictReader(open(os.path.join(RAW, "walk", "WBDSinfo.csv"), encoding="latin1")))
    subj = {}
    for r in info:
        if r["FileName"].endswith("walkT05grf.txt") and r["AgeGroup"] == "Young":
            subj[int(r["Subject"])] = dict(mass=float(r["Mass"]), height=float(r["Height"]) / 100,
                                           leg=float(r["LegLength"]), speed=float(r["GaitSpeed(m/s)"]))
    curves = {k: [] for k in ["hip_ang", "knee_ang", "ankle_ang", "pelvis_tilt", "hip_mom", "knee_mom",
                              "ankle_mom", "grf_v", "grf_ap"]}
    T, used = [], []
    for s, meta in sorted(subj.items()):
        fa = os.path.join(RAW, "walk", f"WBDS{s:02d}walkT05ang.txt")
        fk = os.path.join(RAW, "walk", f"WBDS{s:02d}walkT05knt.txt")
        fg = os.path.join(RAW, "walk", f"WBDS{s:02d}walkT05grf.txt")
        if not (os.path.exists(fa) and os.path.exists(fk) and os.path.exists(fg)):
            continue
        ha, a = load(fa); hk, k = load(fk); hg, g = load(fg)
        col = lambda h, arr, n: arr[:, h.index(n)]
        for side in "RL":
            curves["hip_ang"].append(col(ha, a, f"{side}HipAngleZ"))
            curves["knee_ang"].append(col(ha, a, f"{side}KneeAngleZ"))
            curves["ankle_ang"].append(col(ha, a, f"{side}AnkleAngleZ"))
            curves["pelvis_tilt"].append(col(ha, a, f"{side}PelvisAngleZ"))
            curves["hip_mom"].append(-col(hk, k, f"{side}HipMomentZ"))     # dataset: flexor +
            curves["knee_mom"].append(col(hk, k, f"{side}KneeMomentZ"))    # extensor +
            curves["ankle_mom"].append(col(hk, k, f"{side}AnkleMomentZ"))  # plantarflexor +
            curves["grf_v"].append(col(hk, k, f"{side}GRFY"))
            curves["grf_ap"].append(col(hk, k, f"{side}GRFX"))
        T.append(stride_time(g[:, hg.index("Fy1")], 1))
        used.append(meta)
    return dict(
        label="walk", n_subjects=len(used),
        speed=round(float(np.mean([u["speed"] for u in used])), 3),
        stride_time=round(float(np.median(T)), 4), stride_time_sd=round(float(np.std(T)), 4),
        mass=round(float(np.mean([u["mass"] for u in used])), 2),
        height=round(float(np.mean([u["height"] for u in used])), 3),
        leg_length=round(float(np.mean([u["leg"] for u in used])), 3),
        curves=finish(curves))


def build_run(tag, speed):
    head, rows = None, {}
    with open(os.path.join(RAW, "run", "RBDSinfo.txt"), encoding="latin1") as f:
        for i, l in enumerate(f.read().split("\n")):
            c = l.split("\t")
            if i == 0:
                head = c
            elif len(c) > 5 and c[1].endswith("static.txt"):
                rows[int(c[0])] = dict(mass=float(c[head.index("Mass")]), height=float(c[head.index("Height")]) / 100)
    curves = {k: [] for k in ["hip_ang", "knee_ang", "ankle_ang", "hip_mom", "knee_mom", "ankle_mom", "grf_v", "grf_ap"]}
    T, used = [], []
    for fp in sorted(glob.glob(os.path.join(RAW, "run", "RBDS*processed.txt"))):
        s = int(os.path.basename(fp)[4:7])
        ff = os.path.join(RAW, "run", f"RBDS{s:03d}runT{tag}forces.txt")
        h, a = load(fp)
        if f"RhipAngZ{tag}" not in h or not os.path.exists(ff):
            continue
        col = lambda n: a[:, h.index(n)]
        if not np.isfinite(col(f"RkneeAngZ{tag}")).all():
            continue
        for side in "RL":
            curves["hip_ang"].append(col(f"{side}hipAngZ{tag}"))
            curves["knee_ang"].append(col(f"{side}kneeAngZ{tag}"))
            curves["ankle_ang"].append(col(f"{side}ankleAngZ{tag}"))
            curves["hip_mom"].append(-col(f"{side}hipMomZ{tag}"))
            curves["knee_mom"].append(col(f"{side}kneeMomZ{tag}"))
            curves["ankle_mom"].append(col(f"{side}ankleMomZ{tag}"))
            curves["grf_v"].append(np.nan_to_num(col(f"{side}grfY{tag}")))
            curves["grf_ap"].append(np.nan_to_num(col(f"{side}grfX{tag}")))
        hf, f_ = load(ff)
        T.append(stride_time(f_[:, hf.index("Fy")], 2))
        used.append(rows[s])
    return dict(
        label=f"run{tag}", n_subjects=len(used), speed=speed,
        stride_time=round(float(np.median(T)), 4), stride_time_sd=round(float(np.std(T)), 4),
        mass=round(float(np.mean([u["mass"] for u in used])), 2),
        height=round(float(np.mean([u["height"] for u in used])), 3),
        curves=finish(curves))


if __name__ == "__main__":
    data = {
        "source": {
            "walk": "Fukuchi CA, Fukuchi RK, Duarte M (2018) PeerJ 6:e4640, doi:10.7717/peerj.4640 — figshare 5722711 (CC BY 4.0). Treadmill, comfortable speed (T05), young adults.",
            "run": "Fukuchi RK, Fukuchi CA, Duarte M (2017) PeerJ 5:e3298, doi:10.7717/peerj.3298 — figshare 4543435 (CC BY 4.0). Treadmill 2.5 / 3.5 / 4.5 m/s.",
        },
        "conventions": __doc__.split("Sagittal conventions used everywhere in this project")[1].strip(),
        "gaits": {"walk": build_walk(), "run25": build_run("25", 2.5), "run35": build_run("35", 3.5),
                  "run45": build_run("45", 4.5)},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    for k, g in data["gaits"].items():
        c = g["curves"]
        pk = lambda n: (round(min(c[n]["mean"]), 2), round(max(c[n]["mean"]), 2))
        print(f"{k:6s} n={g['n_subjects']:2d} v={g['speed']} T={g['stride_time']}±{g['stride_time_sd']} m={g['mass']} h={g['height']}",
              "| hip", pk("hip_ang"), "knee", pk("knee_ang"), "ank", pk("ankle_ang"),
              "| Mhip", pk("hip_mom"), "Mknee", pk("knee_mom"), "Mank", pk("ankle_mom"), "| Fv", pk("grf_v"), "Fap", pk("grf_ap"))
