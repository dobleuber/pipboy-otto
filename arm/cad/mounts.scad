// Sistema de montaje del brazo SO-101: la misma unión (riel cola de milano) sirve en la mesa y en
// el morral. Elegir la pieza con PART (ver export.sh), o ver el conjunto con PART="mesa" / "morral".
//
// Piezas para imprimir (PETG, 6 perímetros, 40 % de relleno):
//   bandeja, barra (x2), receptor, mordaza, perilla, base_mesa, pie_mastil, cabeza_fija,
//   cabeza_movil, caja, tapa, probeta_riel, probeta_receptor
// Se compra: tubo de aluminio 20x20x1.5, placa de HDPE 3 mm (se corta con placa_espalda.dxf),
//   tornillos M4/M5/M8, tuercas, 8 imanes de neodimio 10x5 mm, prensas en C para la mesa.

include <params.scad>

PART = "morral";

XC = BASE_X0 + BASE_L / 2;                     // centro de la pestaña de la base
FLOOR_Z = BASE_Z0 - FLOOR;                     // cara de abajo de la bandeja
RAIL_Z = FLOOR_Z - RAIL_H;                     // cara de abajo del riel
BOLT_X = [BASE_X0 - BAR_EAR / 2 - 3, BASE_X0 + BASE_L + BAR_EAR / 2 + 3];

module along_x(L) { rotate([90, 0, 90]) linear_extrude(L) children(); }   // 2D (y, z) -> extruido en x

module rail_2d(grow = 0) {
    w = RAIL_W / 2 + grow;  n = RAIL_W / 2 - RAIL_BEVEL + grow;
    polygon([[-w, -grow], [w, -grow], [w, RAIL_FLAT], [n, RAIL_H + grow], [-n, RAIL_H + grow], [-w, RAIL_FLAT]]);
}

// ------------------------------------------------------------------------------------ bandeja
module cradle() {
    ix = BASE_L + 2 * CL;  iy = BASE_W + 2 * CL;
    x0 = BOLT_X[0] - BAR_EAR;  x1 = BOLT_X[1] + BAR_EAR;
    difference() {
        union() {
            // piso + paredes
            translate([x0, -iy / 2 - WALL, FLOOR_Z]) cube([x1 - x0, iy + 2 * WALL, FLOOR]);
            difference() {
                translate([BASE_X0 - CL - WALL, -iy / 2 - WALL, FLOOR_Z])
                    cube([ix + 2 * WALL, iy + 2 * WALL, FLOOR + TRAY_WALL_H]);
                translate([BASE_X0 - CL, -iy / 2, BASE_Z0]) cube([ix, iy, 50]);
            }
            // postes donde se atornillan las barras (a la altura de la pestaña)
            for (bx = BOLT_X, s = [-1, 1])
                translate([bx - BAR_EAR / 2 - 2, s * BAR_Y - BAR_W / 2, FLOOR_Z])
                    cube([BAR_EAR + 4, BAR_W, FLOOR + BASE_H - PAD]);
            // riel por debajo
            translate([XC - RAIL_L / 2, 0, RAIL_Z]) along_x(RAIL_L) rail_2d();
        }
        // tornillos M5 de las barras, con tuerca atrapada desde abajo
        for (bx = BOLT_X, s = [-1, 1]) translate([bx, s * BAR_Y, FLOOR_Z - 1]) {
            cylinder(d = M5, h = 40);
            cylinder(d = M5_NUT, h = M5_NUT_H + 1, $fn = 6);
        }
        // ranura del tornillo de seguridad (en el centro del riel)
        translate([XC - PIN_GROOVE_W / 2, -RAIL_W, RAIL_Z - 1]) cube([PIN_GROOVE_W, 2 * RAIL_W, PIN_GROOVE_D + 1]);
        // alivianado del piso bajo la torre (ahorra plástico)
        translate([XC, 0, FLOOR_Z + FLOOR / 2]) cube([40, 60, FLOOR + 0.1], center = true);
    }
}

module clamp_bar() {   // barra que aprieta un ala de la pestaña (con goma de PAD mm debajo)
    len = BOLT_X[1] - BOLT_X[0] + BAR_EAR + 4;
    difference() {
        translate([BOLT_X[0] - BAR_EAR / 2 - 2, -BAR_W / 2, 0]) cube([len, BAR_W, BAR_T]);
        for (bx = BOLT_X) translate([bx, 0, -1]) { cylinder(d = M5, h = 20); translate([0, 0, BAR_T - 3]) cylinder(d = M5_HEAD + 0.6, h = 5); }
    }
}

// ------------------------------------------------------------------------------------ receptor
// Coordenadas: x a lo largo del riel (entra desde x = 0 hasta el tope en x = RX_L), z = 0 cara
// de abajo del riel. El lado -y es fijo; el +y es una mordaza que empuja un tornillo M5.
RX_W = RAIL_W + 2 * RX_SIDE;
POCKET_Y0 = RAIL_W / 2 - RAIL_BEVEL - 1;        // donde empieza el bolsillo de la mordaza
POCKET_Y1 = RX_W / 2 - 4;                        // pared exterior de 4 mm (lleva la tuerca)
STOP = 5;                                         // tope al fondo

module receiver_body() {
    difference() {
        translate([0, -RX_W / 2, -RX_BASE]) cube([RX_L + STOP, RX_W, RX_BASE + RAIL_H]);
        translate([-1, 0, 0]) along_x(RX_L + 1) rail_2d(CL);
        translate([-1, -(RAIL_W / 2 - RAIL_BEVEL + CL), RAIL_FLAT]) cube([RX_L + 1, RAIL_W - 2 * RAIL_BEVEL + 2 * CL, 20]);
        // bolsillo de la mordaza móvil
        translate([-1, POCKET_Y0, 0]) cube([RX_L + 1, POCKET_Y1 - POCKET_Y0, RAIL_H + 1]);
        // tornillo de la perilla (M5 con tuerca atrapada en la pared exterior)
        translate([RX_L / 2, RX_W / 2 + 1, RAIL_H / 2]) rotate([90, 0, 0]) {
            cylinder(d = M5, h = 10);
            translate([0, 0, 1.2]) rotate([0, 0, 30]) cylinder(d = M5_NUT, h = M5_NUT_H, $fn = 6);
        }
        // tornillo de seguridad M4 desde abajo (entra en la ranura del riel)
        translate([RX_L / 2, 0, -RX_BASE - 1]) cylinder(d = M4 - 0.6, h = RX_BASE + 2);   // rosca en el plástico o inserto
        // agujeros M5 para fijar el receptor (a la base de mesa o a la cabeza del mástil)
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([x, s * (RX_W / 2 - 6), -RX_BASE - 1]) {
            cylinder(d = M5, h = 30);
            translate([0, 0, RX_BASE - 2]) cylinder(d = M5_HEAD + 0.6, h = 30);
        }
    }
}

module jaw() {   // mordaza móvil: su cara interior es el bisel espejo del riel
    difference() {
        translate([0, POCKET_Y0 + CL, CL]) cube([RX_L - 2 * CL, POCKET_Y1 - POCKET_Y0 - 2 * CL - JAW_TRAVEL, RAIL_H - 2 * CL]);
        translate([-1, 0, 0]) along_x(RX_L + 2) rail_2d(CL);
    }
}

module knob() {   // perilla para la cabeza de un tornillo M5 x 30
    difference() {
        union() {
            cylinder(d = 26, h = 10);
            for (a = [0:60:359]) rotate([0, 0, a]) translate([13, 0, 0]) cylinder(d = 6, h = 10);
        }
        translate([0, 0, -1]) cylinder(d = M5, h = 20);
        translate([0, 0, 5]) cylinder(d = M5_HEAD / cos(30) * 0.95, h = 10, $fn = 6);
    }
}

// ------------------------------------------------------------------------------------ mesa
module table_mount() {   // receptor + alas para dos prensas en C (como el SO-101 original)
    W = 150;  D = 90;  T = 8;
    difference() {
        union() {
            translate([-(W - RX_L - STOP) / 2, -D / 2, -RX_BASE - T]) cube([W, D, T]);
            for (s = [-1, 1]) hull() {   // nervios
                translate([-(W - RX_L - STOP) / 2, s * (D / 2 - 3) - 3, -RX_BASE - T]) cube([W, 6, T]);
                translate([0, s * (RX_W / 2) - 3, -RX_BASE - T]) cube([RX_L + STOP, 6, T + 6]);
            }
        }
        // ranuras para las prensas y agujeros para tornillos de madera
        for (x = [-(W - RX_L - STOP) / 2 + 15, (W + RX_L + STOP) / 2 - 15]) {
            translate([x - 10, -D / 2 + 15, -50]) cube([20, D - 30, 100]);
        }
        for (x = [-(W - RX_L - STOP) / 2 + 6, (W + RX_L + STOP) / 2 - 6], s = [-1, 1])
            translate([x, s * (D / 2 - 8), -50]) cylinder(d = 4.5, h = 100);
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([x, s * (RX_W / 2 - 6), -50]) cylinder(d = M5, h = 100);
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([x, s * (RX_W / 2 - 6), -RX_BASE - T - 1]) cylinder(d = M5_NUT, h = M5_NUT_H + 1, $fn = 6);
        translate([RX_L / 2, 0, -50]) cylinder(d = 10, h = 100);   // acceso al tornillo de seguridad
    }
}

// ------------------------------------------------------------------------------------ probetas
module coupon_rail() { along_x(20) rail_2d(); }
module coupon_receiver() { intersection() { receiver_body(); translate([RX_L / 2 - 10, -50, -50]) cube([20, 100, 100]); } }

// ------------------------------------------------------------------------------------ morral
function v_sub(a, b) = [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
TUBE_DIR = v_sub(HEAD_AT, FOOT_AT);
TUBE_LEN = norm(TUBE_DIR);
// Ángulos para orientar el tubo (eje +z local) de FOOT_AT a HEAD_AT
T_YAW = atan2(TUBE_DIR[1], TUBE_DIR[0]);
T_PITCH = acos(TUBE_DIR[2] / TUBE_LEN);
module tube_frame() { translate(FOOT_AT) rotate([0, 0, T_YAW]) rotate([0, T_PITCH, 0]) children(); }

module tube() { tube_frame() difference() { translate([-TUBE / 2, -TUBE / 2, 0]) cube([TUBE, TUBE, TUBE_LEN]);
    translate([-TUBE / 2 + TUBE_T, -TUBE / 2 + TUBE_T, -1]) cube([TUBE - 2 * TUBE_T, TUBE - 2 * TUBE_T, TUBE_LEN + 2]); } }

SOCKET = 45;   // largo del tubo dentro de cada pieza
module socket_outer() { translate([-TUBE / 2 - 5, -TUBE / 2 - 5, 0]) cube([TUBE + 10, TUBE + 10, SOCKET]); }
module socket_cut() {
    translate([-TUBE / 2 - CL, -TUBE / 2 - CL, -1]) cube([TUBE + 2 * CL, TUBE + 2 * CL, SOCKET + 2]);
    for (z = [12, SOCKET - 12]) translate([-30, 0, z]) rotate([0, 90, 0]) cylinder(d = M5, h = 60);   // pasadores M5
}

module mast_foot() {   // atornillado (4 x M5) a la cara de atrás de la placa, arriba a la derecha
    difference() {
        hull() {
            translate([SHEET_X - SHEET[0] - 6, FOOT_AT[1] - 35, FOOT_AT[2] - 35]) cube([6, 70, 70]);
            tube_frame() translate([0, 0, -8]) socket_outer();
        }
        tube_frame() translate([0, 0, -8]) socket_cut();
        for (dy = [-25, 25], dz = [-25, 25]) translate([SHEET_X - 40, FOOT_AT[1] + dy, FOOT_AT[2] + dz])
            rotate([0, 90, 0]) cylinder(d = M5, h = 60);
    }
}

// Cabeza: la parte fija toma el extremo del tubo y lleva la bisagra (pasador M8) y el tope; la
// móvil lleva el receptor. Cerrada, 4 pares de imanes la sostienen; si el brazo se engancha
// (más de FOLD_TORQUE), se dobla hacia atrás, nunca hacia la cabeza.
RX_TOP = ARM_BASE[2] + FLOOR_Z;                  // cara de arriba del receptor (debajo de la bandeja)
RX_ORIGIN = [ARM_BASE[0] + XC - RX_L / 2 - STOP, ARM_BASE[1], RX_TOP - RAIL_H];
PLATE_T = 8;
PLATE_Z = RX_ORIGIN[2] - RX_BASE - PLATE_T;       // cara de abajo de la placa móvil (= apoyo)
HINGE = [RX_ORIGIN[0] - HINGE_BEHIND, ARM_BASE[1], PLATE_Z];
KNUCKLE = 14;  KR = 11;                           // ancho de cada nudillo móvil y radio
SUPPORT_X0 = HINGE[0] + KR + 3;                   // el apoyo empieza después de la bisagra
MAG_X = [RX_ORIGIN[0] + 25, RX_ORIGIN[0] + 55];
MAG_Y = RX_W / 2 - 9;

module head_moving() {
    difference() {
        union() {
            translate(RX_ORIGIN) receiver_body();
            translate([HINGE[0], ARM_BASE[1] - RX_W / 2, PLATE_Z]) cube([RX_ORIGIN[0] + RX_L + STOP - HINGE[0], RX_W, PLATE_T]);
            for (s = [-1, 1]) translate([HINGE[0], ARM_BASE[1] + s * (RX_W - KNUCKLE) / 2, HINGE[2]])
                rotate([90, 0, 0]) cylinder(r = KR, h = KNUCKLE, center = true);
        }
        translate(HINGE) rotate([90, 0, 0]) cylinder(d = M8, h = 200, center = true);
        // hueco para el nudillo central (fijo), con lugar para girar
        lug = RX_W - 2 * KNUCKLE;
        translate(HINGE) rotate([90, 0, 0]) cylinder(r = KR + 1, h = lug, center = true);
        translate([HINGE[0], ARM_BASE[1] - lug / 2, PLATE_Z - 1]) cube([KR + 1, lug, PLATE_T + 2]);
        for (x = MAG_X, s = [-1, 1]) translate([x, ARM_BASE[1] + s * MAG_Y, PLATE_Z - 0.01])
            cylinder(d = MAGNET_D + 0.3, h = MAGNET_H + 0.2);   // imanes (se pegan con epoxi)
        // pasadas de los tornillos del receptor
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([RX_ORIGIN[0] + x, ARM_BASE[1] + s * (RX_W / 2 - 6), PLATE_Z - 1])
            cylinder(d = M5, h = 30);
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([RX_ORIGIN[0] + x, ARM_BASE[1] + s * (RX_W / 2 - 6), PLATE_Z - 1])
            cylinder(d = M5_NUT, h = M5_NUT_H + 1, $fn = 6);
    }
}

module head_fixed() {
    lug = RX_W - 2 * KNUCKLE - 2 * CL;
    difference() {
        union() {
            // nudillo central + unión con el tubo
            hull() {
                translate(HINGE) rotate([90, 0, 0]) cylinder(r = KR, h = lug, center = true);
                tube_frame() translate([0, 0, TUBE_LEN - SOCKET + 8]) socket_outer();
            }
            // apoyo bajo la placa móvil (lleva los otros imanes); el tope que impide doblarse hacia adelante
            hull() {
                translate([SUPPORT_X0, ARM_BASE[1] - RX_W / 2, PLATE_Z - 10]) cube([RX_ORIGIN[0] + RX_L + STOP - SUPPORT_X0, RX_W, 10]);
                translate([HINGE[0], ARM_BASE[1] - lug / 2, PLATE_Z - KR]) cube([1, lug, 2]);
            }
        }
        tube_frame() translate([0, 0, TUBE_LEN - SOCKET + 8]) socket_cut();
        translate(HINGE) rotate([90, 0, 0]) cylinder(d = M8, h = 200, center = true);
        for (x = MAG_X, s = [-1, 1]) translate([x, ARM_BASE[1] + s * MAG_Y, PLATE_Z - MAGNET_H - 0.19])
            cylinder(d = MAGNET_D + 0.3, h = MAGNET_H + 0.2);
        // espacio para que giren los nudillos móviles
        for (s = [-1, 1]) translate([HINGE[0], ARM_BASE[1] + s * (RX_W - KNUCKLE) / 2, HINGE[2]])
            rotate([90, 0, 0]) cylinder(r = KR + 1, h = KNUCKLE + 2 * CL, center = true);
        // las cabezas de los tornillos del receptor quedan en la placa móvil: rebaje en el apoyo
        for (x = [10, RX_L - 5], s = [-1, 1]) translate([RX_ORIGIN[0] + x, ARM_BASE[1] + s * (RX_W / 2 - 6), PLATE_Z - 4])
            cylinder(d = M5_NUT + 2, h = 5);
    }
}

// ------------------------------------------------------------------------------------ electrónica
module box() {   // caja abajo en la placa: Orange Pi 5 Pro, batería 3S (3 x 18650), buck 5 V, relé de parada
    w = 2.5;
    difference() {
        translate([-BOX_IN[0] / 2 - w, -BOX_IN[1] / 2 - w, -BOX_IN[2] / 2 - w]) cube([BOX_IN[0] + 2 * w, BOX_IN[1] + 2 * w, BOX_IN[2] + w]);
        translate([-BOX_IN[0] / 2, -BOX_IN[1] / 2, -BOX_IN[2] / 2]) cube([BOX_IN[0], BOX_IN[1], BOX_IN[2] + 1]);
        for (dy = [-50, 50], dz = [-30, 30]) translate([BOX_IN[0] / 2 - 1, dy, dz]) rotate([0, 90, 0]) cylinder(d = M5, h = 10);
        for (dy = [-40, 0, 40]) translate([0, dy, -BOX_IN[2] / 2 - 5]) cylinder(d = 12, h = 10);   // pasacables
    }
}
module lid() { translate([-BOX_IN[0] / 2 - 2.5, -BOX_IN[1] / 2 - 2.5, 0]) cube([BOX_IN[0] + 5, BOX_IN[1] + 5, 2.5]); }

module sheet_2d() {   // placa de la espalda (HDPE 3 mm), vista de frente: (y, z)
    difference() {
        offset(r = 20) offset(delta = -20) translate([-SHEET[1] / 2, SHEET_TOP - SHEET[2]]) square([SHEET[1], SHEET[2]]);
        for (dy = [-25, 25], dz = [-25, 25]) translate([FOOT_AT[1] + dy, FOOT_AT[2] + dz]) circle(d = M5);
        for (dy = [-50, 50], dz = [-30, 30]) translate([dy, BOX_Z + dz]) circle(d = M5);
        for (s = [-1, 1], z = [SHEET_TOP - 30, SHEET_TOP - SHEET[2] + 30]) translate([s * (SHEET[1] / 2 - 15) - 2.5, z - 13]) square([5, 26]);   // correas
        // ventanas para alivianar (~150 g en vez de ~270 g), lejos de los tornillos
        for (s = [-1, 1]) translate([s * 55, SHEET_TOP - 210]) offset(r = 15) offset(delta = -15) square([80, 170], center = true);
    }
}
module sheet() { translate([SHEET_X - SHEET[0], 0, 0]) rotate([90, 0, 90]) linear_extrude(SHEET[0]) sheet_2d(); }

// ------------------------------------------------------------------------------------ conjuntos
module arm_ghost() { color([1, 0.82, 0.12, 0.5]) translate([0, 0, BASE_Z0]) {
    translate([BASE_X0, -BASE_W / 2, 0]) cube([BASE_L, BASE_W, BASE_H]);
    translate([BASE_X0, -TOWER_HW, BASE_H]) cube([TOWER_X1 - BASE_X0, 2 * TOWER_HW, 60]); } }

module mounted_arm() {
    color("gainsboro") cradle();
    color("dimgray") for (s = [-1, 1]) translate([0, s * BAR_Y, BASE_Z0 + BASE_H]) clamp_bar();
    arm_ghost();
}

if (PART == "bandeja") cradle();
if (PART == "barra") clamp_bar();
if (PART == "receptor") receiver_body();
if (PART == "mordaza") jaw();
if (PART == "perilla") knob();
if (PART == "base_mesa") union() { table_mount(); }
if (PART == "pie_mastil") mast_foot();
if (PART == "cabeza_fija") head_fixed();
if (PART == "cabeza_movil") head_moving();
if (PART == "caja") box();
if (PART == "tapa") lid();
if (PART == "probeta_riel") coupon_rail();
if (PART == "probeta_receptor") coupon_receiver();
if (PART == "placa_espalda") sheet_2d();
if (PART == "mesa") {
    color("lightsteelblue") table_mount();
    color("gainsboro") receiver_body();
    color("dimgray") jaw();
    translate([RX_L + STOP - (XC + RAIL_L / 2) + 0, 0, -RAIL_Z]) mounted_arm();
}
if (PART == "morral") {
    color([0.9, 0.9, 0.9, 0.8]) sheet();
    color("silver") tube();
    color("slategray") mast_foot();
    color("slategray") head_fixed();
    color("lightsteelblue") head_moving();
    translate(ARM_BASE) mounted_arm();
    color("darkolivegreen") translate([SHEET_X - SHEET[0] - BOX_IN[0] / 2 - 2.5, 0, BOX_Z]) box();
}
