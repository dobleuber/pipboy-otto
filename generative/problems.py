"""Generative-design trial for the wrist cuff of cad/pipboy-zero3-v0.2.scad.

Frame (mm, N): x across the forearm, y up towards the body (y = 0 is the flat face that bolts to the body
floor), z along the forearm from the left end of the enclosure. The forearm axis is the line x = 0, y = ARM_Y.
The frame is turned so the forearm runs along z, because the pipeline's cylinders are along z only. The M3
screws then run along y, so their holes and head pockets are square (boxes): an M3 passes a 3.4 mm square and
its head a 6.5 mm one.

Loads are assumptions, nothing was measured:
  - the enclosure with its electronics is taken as 0.5 kg, times 3 for knocks: 15 N;
  - a snug velcro strap is taken as 25 N of tension on each of its two bars.
Dimensions are those of the CAD file (R_ARM, strap slots, cuff screws); change them there and here together.
"""
from genpart import Problem, RemoteLoad, box, zcyl

R_ARM = 43.0
ARM_Y = -48.5                      # -(CUFF_MIN_T + R_ARM)
LINER = 2.0                        # crisp skin against the arm, under each strap
HALF_W = 48.0
DEPTH = -32.5
LENGTH = 169.25

SCREWS = [(-15.5, 6.6), (16.5, 6.6), (-15.5, 162.7), (16.5, 162.7)]     # (x, z)
STRAPS = [(22.65, 62.65), (106.65, 146.65)]                              # slot extent along z
SLOT_Y = (-26.75, -22.25)
WEIGHT = 15.0
STRAP_TENSION = 25.0


def cuff():
    bands = [(z0 - 3, z1 + 3) for z0, z1 in STRAPS]
    liners = [zcyl(0, ARM_Y, R_ARM + LINER, z0, z1) for z0, z1 in bands]
    bosses = [box(x - 5.5, x + 5.5, -10, 0, z - 5, z + 5) for x, z in SCREWS]
    # the bar each strap wraps around, below its slot, on both wings
    bars = {(side, i): box(side * 36, side * HALF_W, DEPTH, SLOT_Y[0], z0, z1)
            for i, (z0, z1) in enumerate(bands) for side in (-1, 1)}
    # patches of the liner: where the arm rests, and where it leans on a wing
    top = [box(-14, 14, -8, -3.5, z0, z1) for z0, z1 in bands]
    wing = {(side, i): box(side * 36, side * 46, -31, -14, z0, z1)
            for i, (z0, z1) in enumerate(bands) for side in (-1, 1)}

    def centre(prim):
        return ((prim[1] + prim[2]) / 2, (prim[3] + prim[4]) / 2, (prim[5] + prim[6]) / 2)

    def on(prim, force):
        return RemoteLoad([prim], centre(prim), force)

    pull = STRAP_TENSION
    return Problem(
        name="cuff",
        bounds=(-HALF_W, HALF_W, DEPTH, 0, 0, LENGTH),
        keepout=[zcyl(0, ARM_Y, R_ARM, -20, LENGTH + 20)]                          # the forearm (99 is too short here)
        + [box(side * 23, side * 99, SLOT_Y[0], SLOT_Y[1], z0, z1)                  # strap slots
           for z0, z1 in STRAPS for side in (-1, 1)]
        + [box(x - 3.25, x + 3.25, -99, -3, z - 3.25, z + 3.25) for x, z in SCREWS],   # screw heads, driver
        preserve=liners + bosses + list(bars.values()),
        holes=[box(x - 1.7, x + 1.7, -99, 99, z - 1.7, z + 1.7) for x, z in SCREWS],
        support=[box(x - 5.5, x + 5.5, -2, 1, z - 5, z + 5) for x, z in SCREWS],    # bolted to the body
        cases={
            # the enclosure rests on the arm
            "rests on arm": [on(t, (0, WEIGHT / 2, 0)) for t in top],
            # straps pulled tight: bars pulled down and slightly in, the arm pushes back on the saddle
            "straps tight": [on(bars[side, i], (-side * 0.2 * pull, -0.98 * pull, 0))
                             for i in range(2) for side in (-1, 1)]
            + [on(t, (0, 2 * 0.98 * pull, 0)) for t in top],
            # arm turned on its side: the enclosure hangs sideways and the arm leans on one wing
            "hangs left": [on(wing[-1, i], (-WEIGHT / 2, 0, 0)) for i in range(2)],
            "hangs right": [on(wing[1, i], (WEIGHT / 2, 0, 0)) for i in range(2)],
            # arm pointing down: the weight acts along the forearm
            "slides along arm": [on(t, (0, 0, WEIGHT / 2)) for t in top],
            # the enclosure rocks end to end
            "rocks": [on(top[0], (0, WEIGHT, 0)), on(top[1], (0, -WEIGHT, 0))],
        },
        round=3.0, round_top=False,
        voxel=2.0, volfrac=0.30, rmin=2.5, min_wall=1.6,
        baseline="baselines/cuff.stl",
        youngs=2100.0, poisson=0.35, density=1.27e-3,                               # PETG
        extra={"blender": {"voxel": 0.6}},
    )


PROBLEMS = {"cuff": cuff}
