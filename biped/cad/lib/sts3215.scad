// Feetech STS3215 y utilidades de montaje.
// Marco del servo: origen en el eje, sobre el plano medio de la carcasa.
//   Z = eje (disco de salida en +Z, disco pasivo en -Z)
//   X = a lo largo del cuerpo (extremo corto en -X, largo en +X)
//   Y = ancho
include <params.scad>

module sts3215() {
    color([0.12, 0.12, 0.13])
        translate([-S_SHORT, -S_W / 2, -S_CASE / 2]) cube([S_SHORT + S_LONG, S_W, S_CASE]);
    color([0.78, 0.78, 0.8]) {
        translate([0, 0, S_CASE / 2]) cylinder(d = S_DISC_D, h = S_DISC_Z - S_CASE / 2);
        translate([0, 0, -S_DISC_Z]) cylinder(d = S_DISC_D, h = S_DISC_Z - S_CASE / 2);
    }
    // conector del bus (lado largo)
    color([0.9, 0.9, 0.9]) translate([S_LONG - 9, -6, S_CASE / 2]) cube([8, 12, 1.5]);
}

// Agujeros del disco (4x M2 + central), a lo largo de Z, centrados en el origen.
module horn_holes(h = 20) {
    for (a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([S_HORN_R, 0, 0])
        cylinder(d = M2_HOLE, h = h, center = true, $fn = 16);
    cylinder(d = HORN_CENTER, h = h, center = true, $fn = 24);
}

// Agujeros M2 de la carcasa en el plano XY del servo (perforan a lo largo de Z).
module case_holes(h = 60) {
    for (x = S_CASE_HOLES_X) for (y = [-S_CASE_HOLE_Y, S_CASE_HOLE_Y])
        translate([x, y, 0]) cylinder(d = M2_HOLE, h = h, center = true, $fn = 16);
}

// Coloca los hijos en el marco de un servo dado su eje Z y su dirección X (en el marco padre).
function _cross(a, b) = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
module servo_frame(origin, Z, X) {
    Y = _cross(Z, X);
    translate(origin)
        multmatrix([[X[0], Y[0], Z[0], 0], [X[1], Y[1], Z[1], 0], [X[2], Y[2], Z[2], 0], [0, 0, 0, 1]])
            children();
}
