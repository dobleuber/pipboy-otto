// Mini16 - pierna izquierda (la derecha es su espejo: mirror([0,1,0])).
//
// Cadena: torso (servo yaw) -> yaw_link -> roll_link -> thigh -> shin -> ankle_cross -> foot (+ sole)
// Cada pieza está dibujada en el marco de su articulación de entrada, con la pierna recta:
//   x = adelante, y = izquierda (hacia afuera), z = arriba.
// Las piezas que giran sujetan el servo anterior por sus DOS discos (salida y pasivo), en "U";
// el STS3215 ya trae eje pasivo con rodamiento propio. Los cuerpos de los servos se atornillan
// (M2) a placas finas apoyadas en sus caras.
//
// Uso:
//   openscad -o thigh.stl -D 'PART="thigh"' leg.scad
//   PART = yaw_link | roll_link | thigh | shin | ankle_cross | foot | sole | assembly
//   Para el ensamble: -D 'Q=[yaw,roll,pitch,knee,ankle,ankle_roll]' (grados)

include <lib/params.scad>
use <lib/sts3215.scad>

PART = "assembly";
MIRROR = false;               // true: versión para la pierna derecha
Q = [0, 0, 43, -80, 37, 0];   // postura de pie (rodillas flexionadas)
SERVOS = true;
SERVO_INSET = 0;              // >0 encoge los servos (para revisar choques sin contar los apoyos)

PETG = [0.55, 0.82, 0.9];
TPU  = [0.18, 0.18, 0.2];

// ------------------------------------------------------------------ utilidades
module arm_y(y0, drop) {       // brazo plano en y, del disco (en el origen) hasta z = -drop
    hull() {
        translate([0, y0, 0]) rotate([-90, 0, 0]) cylinder(r = ARM_R, h = T);
        translate([-ARM_R, y0, -drop]) cube([2 * ARM_R, T, T]);
    }
}
module arm_x(x0, drop) {       // brazo plano en x
    hull() {
        translate([x0, 0, 0]) rotate([0, 90, 0]) cylinder(r = ARM_R, h = T);
        translate([x0, -ARM_R, -drop]) cube([T, 2 * ARM_R, T]);
    }
}
module disc_clear_y(z = 0) { translate([0, 0, z]) rotate([90, 0, 0]) cylinder(r = S_DISC_D / 2 + GAP, h = 2 * S_DISC_Z + 2, center = true); }
module disc_clear_x(z = 0) { translate([0, 0, z]) rotate([0, 90, 0]) cylinder(r = S_DISC_D / 2 + GAP, h = 2 * S_DISC_Z + 2, center = true); }
module horn_y() { rotate([90, 0, 0]) horn_holes(h = 2 * S_DISC_Z + 4 * T); }
module horn_x(z = 0) { translate([0, 0, z]) rotate([0, 90, 0]) horn_holes(h = 2 * S_DISC_Z + 4 * T); }
Y_ARM = [S_DISC_Z, -S_DISC_Z - T];    // posiciones de los brazos a ambos lados de un servo

// ------------------------------------------------------------------ piezas
// Cadera yaw: placa atornillada al disco del servo yaw (en el torso) + U sobre el servo roll.
module yaw_link() {
    difference() {
        union() {
            translate([-(S_DISC_Z + T), -ARM_R, -T]) cube([2 * (S_DISC_Z + T), 2 * ARM_R, T]);
            for (x0 = Y_ARM) hull() {
                translate([x0, -ARM_R, -T]) cube([T, 2 * ARM_R, T]);
                translate([x0, 0, -D_YAW_ROLL]) rotate([0, 90, 0]) cylinder(r = ARM_R, h = T);
            }
        }
        horn_holes(h = 4 * T);
        horn_x(-D_YAW_ROLL);
    }
}

// Cadera roll: sostiene el cuerpo del servo roll (arriba, acostado hacia afuera) y el del servo
// pitch (abajo, acostado hacia adelante).
module roll_link() {
    zp = -D_ROLL_PITCH;
    ftop = -S_W / 2 - 0.5;
    fbot = ftop - 2.5;
    difference() {
        union() {
            for (x0 = [S_CASE / 2, -S_CASE / 2 - TF])
                translate([x0, 3, fbot]) cube([TF, S_LONG + 2 - 3, S_W / 2 - fbot]);
            translate([-S_CASE / 2 - TF, -S_CASE / 2 - TF, fbot])
                cube([S_LONG + 2 + S_CASE / 2 + TF, S_LONG + 2 + S_CASE / 2 + TF, 2.5]);
            for (y0 = [S_CASE / 2, -S_CASE / 2 - TF])
                translate([3, y0, zp - S_W / 2]) cube([S_LONG + 2 - 3, TF, ftop - (zp - S_W / 2)]);
        }
        disc_clear_x(0);
        disc_clear_y(zp);
        servo_frame([0, 0, 0], [1, 0, 0], [0, 1, 0]) case_holes();
        servo_frame([0, 0, zp], [0, 1, 0], [1, 0, 0]) case_holes();
    }
}

// Muslo: U sobre el servo de cadera pitch + cuna del servo de rodilla (acostado hacia atrás,
// como la placa del muslo del Microduck).
module thigh() {
    zk = -D_THIGH;
    cb = -R_CB - T;
    difference() {
        union() {
            for (y0 = Y_ARM) arm_y(y0, R_CB + T);
            translate([-(S_LONG + 2), -(S_DISC_Z + T), cb]) cube([S_LONG + 2 + ARM_R, 2 * (S_DISC_Z + T), T]);
            for (y0 = [S_CASE / 2, -S_CASE / 2 - TF])
                translate([-(S_LONG + 2), y0, zk - S_W / 2]) cube([S_LONG + 2 - 3, TF, cb - (zk - S_W / 2)]);
        }
        horn_y();
        disc_clear_y(zk);
        servo_frame([0, 0, zk], [0, 1, 0], [-1, 0, 0]) case_holes();
    }
}

// Canilla: U sobre el servo de rodilla + cuna del servo de tobillo pitch
// (SHIN_SERVO = "fwd": acostado hacia adelante; "up": parado a lo largo de la canilla).
module shin() {
    za = -D_SHIN;
    cb = -R_CB - T;
    difference() {
        union() {
            for (y0 = Y_ARM) arm_y(y0, R_CB + T);
            if (SHIN_SERVO == "up") {
                translate([-S_W / 2 - TF, -(S_DISC_Z + T), cb]) cube([S_W + 2 * TF, 2 * (S_DISC_Z + T), T]);
                for (y0 = [S_CASE / 2, -S_CASE / 2 - TF])
                    translate([-S_W / 2 - TF, y0, za + 3]) cube([S_W + 2 * TF, TF, cb - (za + 3)]);
            } else {
                translate([-ARM_R, -(S_DISC_Z + T), cb]) cube([S_LONG + 2 + ARM_R, 2 * (S_DISC_Z + T), T]);
                for (y0 = [S_CASE / 2, -S_CASE / 2 - TF])
                    translate([3, y0, za - S_W / 2]) cube([S_LONG + 2 - 3, TF, cb - (za - S_W / 2)]);
            }
        }
        horn_y();
        disc_clear_y(za);
        servo_frame([0, 0, za], [0, 1, 0], shin_servo_x()) case_holes();
    }
}
function shin_servo_x() = SHIN_SERVO == "up" ? [0, 0, 1] : [1, 0, 0];

// Tobillo: U sobre el servo de tobillo pitch + cuna del servo de tobillo roll (acostado hacia afuera).
module ankle_cross() {
    zr = -D_ANKLE;
    cb = -R_CB - T;
    difference() {
        union() {
            for (y0 = Y_ARM) arm_y(y0, R_CB + T);
            translate([-(S_CASE / 2 + TF), -(S_DISC_Z + T), cb])
                cube([S_CASE + 2 * TF, S_DISC_Z + T + S_LONG + 2, T]);
            for (x0 = [S_CASE / 2, -S_CASE / 2 - TF])
                translate([x0, 3, zr - S_W / 2]) cube([TF, S_LONG + 2 - 3, cb - (zr - S_W / 2)]);
        }
        horn_y();
        disc_clear_x(zr);
        servo_frame([0, 0, zr], [1, 0, 0], [0, 1, 0]) case_holes();
    }
}

// Pie (PETG): U sobre el servo de tobillo roll + plancha con alojamientos para los sensores
// de pisada (punta y talón) y 4 torres con insertos M3 para la suela.
SOLE_SCREWS = [[FOOT_X0 + 8, 14], [FOOT_X0 + 8, -14], [FOOT_X1 - 18, 14], [FOOT_X1 - 18, -14]];
module rounded_plate(x0, x1, hw, z0, h, r = 5) {
    hull() for (x = [x0 + r, x1 - r]) for (y = [-hw + r, hw - r]) translate([x, y, z0]) cylinder(r = r, h = h);
}
module foot() {
    pt = -FOOT_CLEAR;
    pb = pt - PLATE_T;
    difference() {
        union() {
            for (x0 = Y_ARM) hull() {
                translate([x0, 0, 0]) rotate([0, 90, 0]) cylinder(r = ARM_R, h = T);
                translate([x0, -ARM_R, pb]) cube([T, 2 * ARM_R, PLATE_T]);
            }
            rounded_plate(FOOT_X0, FOOT_X1, FOOT_HW, pb, PLATE_T);
            // carcasas de los interruptores
            for (x = SW_X) translate([x - SW_L / 2 - T, -SW_W / 2 - T, pt]) cube([SW_L + 2 * T, SW_W + 2 * T, SW_H]);
            // torres para insertos
            for (p = SOLE_SCREWS) translate([p[0], p[1], pt]) cylinder(d = INSERT_BOSS, h = INSERT_L + 1);
        }
        horn_x(0);
        for (x = SW_X) {
            translate([x - SW_L / 2 - CL / 2, -SW_W / 2 - CL / 2, pt]) cube([SW_L + CL, SW_W + CL, SW_H + 1]);
            translate([x - 2, -2, pb - 1]) cube([4, 4, PLATE_T + 2]);          // paso de la palanca
            for (dx = [-SW_PIN_DX / 2, SW_PIN_DX / 2])                             // pernos
                translate([x + dx, 0, pt + SW_H / 2]) rotate([90, 0, 0]) cylinder(d = SW_PIN + 0.2, h = SW_W + 4 * T, center = true, $fn = 16);
        }
        for (p = SOLE_SCREWS) translate([p[0], p[1], pb - 1]) cylinder(d = INSERT_D, h = PLATE_T + INSERT_L + 2, $fn = 24);
    }
}

// Suela (TPU 95A): bordes redondeados en punta, talón y costados (suela "rocker").
module sole() {
    pb = -FOOT_CLEAR - PLATE_T;
    difference() {
        intersection() {
            hull() for (x = [FOOT_X0 + ROCKER_R, FOOT_X1 - ROCKER_R]) for (y = [-FOOT_HW + ROCKER_R, FOOT_HW - ROCKER_R])
                translate([x, y, pb - SOLE_T + ROCKER_R]) sphere(r = ROCKER_R);
            translate([FOOT_X0 - 1, -FOOT_HW - 1, pb - SOLE_T]) cube([FOOT_X1 - FOOT_X0 + 2, 2 * FOOT_HW + 2, SOLE_T]);
        }
        for (x = SW_X) translate([x - 2.5, -2.5, pb - SOLE_T - 1]) cube([5, 5, SOLE_T + 2]);
        for (p = SOLE_SCREWS) {
            translate([p[0], p[1], pb - SOLE_T - 1]) cylinder(d = M3_HOLE, h = SOLE_T + 2, $fn = 20);
            translate([p[0], p[1], pb - SOLE_T - 1]) cylinder(d = 6.5, h = 1 + 1.5, $fn = 24);   // cabeza
        }
    }
}

// ------------------------------------------------------------------ ensamble
module servo_vis(o, Z, X) {
    servo_frame(o, Z, X) if (SERVO_INSET > 0) shrunk_servo(); else sts3215();
}
module shrunk_servo() {
    s = SERVO_INSET;
    translate([-S_SHORT + s, -S_W / 2 + s, -S_CASE / 2 + s]) cube([S_SHORT + S_LONG - 2 * s, S_W - 2 * s, S_CASE - 2 * s]);
    for (z = [S_CASE / 2, -S_DISC_Z + s]) translate([0, 0, z]) cylinder(d = S_DISC_D - 2 * s, h = S_DISC_Z - S_CASE / 2 - s);
}

module leg(q = Q) {
    if (SERVOS) servo_vis([0, 0, S_DISC_Z], [0, 0, -1], [-1, 0, 0]);       // servo yaw (en el torso)
    rotate([0, 0, q[0]]) {
        color(PETG) yaw_link();
        translate([0, 0, -D_YAW_ROLL]) rotate([q[1], 0, 0]) {
            if (SERVOS) servo_vis([0, 0, 0], [1, 0, 0], [0, 1, 0]);
            color(PETG) roll_link();
            if (SERVOS) servo_vis([0, 0, -D_ROLL_PITCH], [0, 1, 0], [1, 0, 0]);
            translate([0, 0, -D_ROLL_PITCH]) rotate([0, q[2], 0]) {
                color(PETG) thigh();
                if (SERVOS) servo_vis([0, 0, -D_THIGH], [0, 1, 0], [-1, 0, 0]);
                translate([0, 0, -D_THIGH]) rotate([0, q[3], 0]) {
                    color(PETG) shin();
                    if (SERVOS) servo_vis([0, 0, -D_SHIN], [0, 1, 0], shin_servo_x());
                    translate([0, 0, -D_SHIN]) rotate([0, q[4], 0]) {
                        color(PETG) ankle_cross();
                        if (SERVOS) servo_vis([0, 0, -D_ANKLE], [1, 0, 0], [0, 1, 0]);
                        translate([0, 0, -D_ANKLE]) rotate([q[5], 0, 0]) {
                            color(PETG) foot();
                            color(TPU) sole();
                        }
                    }
                }
            }
        }
    }
}

module part(name) {
    if (name == "yaw_link") yaw_link();
    else if (name == "roll_link") roll_link();
    else if (name == "thigh") thigh();
    else if (name == "shin") shin();
    else if (name == "ankle_cross") ankle_cross();
    else if (name == "foot") foot();
    else if (name == "sole") sole();
}
if (MIRROR && PART != "assembly") mirror([0, 1, 0]) part(PART);
else if (PART == "yaw_link") yaw_link();
else if (PART == "roll_link") roll_link();
else if (PART == "thigh") thigh();
else if (PART == "shin") shin();
else if (PART == "ankle_cross") ankle_cross();
else if (PART == "foot") foot();
else if (PART == "sole") sole();
else if (PART == "servo") sts3215();
else if (PART == "servo_check") shrunk_servo();
else if (PART == "assembly") leg();
