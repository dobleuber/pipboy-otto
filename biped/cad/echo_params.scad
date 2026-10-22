// Imprime los parámetros que usa build_mjcf.py (una sola fuente de verdad: lib/params.scad).
include <lib/params.scad>
echo("S_DISC_Z", S_DISC_Z);
echo("S_CASE", S_CASE);
echo("S_W", S_W);
echo("S_SHORT", S_SHORT);
echo("S_LONG", S_LONG);
echo("D_YAW_ROLL", D_YAW_ROLL);
echo("D_ROLL_PITCH", D_ROLL_PITCH);
echo("D_THIGH", D_THIGH);
echo("D_SHIN", D_SHIN);
echo("D_ANKLE", D_ANKLE);
echo("D_SOLE", D_SOLE);
echo("FOOT_CLEAR", FOOT_CLEAR);
echo("PLATE_T", PLATE_T);
echo("SOLE_T", SOLE_T);
echo("HIP_Y", HIP_Y);
echo("FOOT_X0", FOOT_X0);
echo("FOOT_X1", FOOT_X1);
echo("FOOT_HW", FOOT_HW);
echo("SW_X0", SW_X[0]);
echo("SW_X1", SW_X[1]);
cube(1);
