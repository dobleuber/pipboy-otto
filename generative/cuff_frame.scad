// The v0.2 cuff in the frame the generative pipeline uses. Export the baseline with:
//   openscad -o generative/baselines/cuff.stl generative/cuff_frame.scad
// x across the arm, y up towards the body (0 = face that bolts to the body), z along the forearm.
use <../cad/pipboy-zero3-v0.2.scad>
CY = 45.5;    // CAV_Y / 2 in the CAD file
WALL = 2.4;
multmatrix([[0, 1, 0, -CY], [0, 0, 1, 0], [1, 0, 0, WALL], [0, 0, 0, 1]]) cuff();
