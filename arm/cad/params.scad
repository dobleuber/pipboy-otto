// Medidas del sistema de montaje del brazo SO-101 (mm). Única fuente: cambiar aquí y volver a
// exportar (./export.sh). La simulación lee las del morral con echo_params.scad.

$fn = 48;
CL = 0.4;            // holgura de ajuste (bajar a 0.3 si la impresora es precisa)
WALL = 4;            // paredes estructurales

// ---------------------------------------------------------------- base del SO-101 (medida del STL)
// Pestaña de la base: 87 x 111 mm, 16 mm de alto; la torre encima ocupa x -22.4..19.4, y ±22.4.
// Coordenadas respecto del origen del cuerpo "base" del modelo (eje x hacia adelante del brazo).
BASE_X0 = -22.4;  BASE_L = 87.0;  BASE_W = 111.0;  BASE_H = 16.0;
BASE_Z0 = -2.4;   // la cara de abajo de la base está 2.4 mm bajo su origen
TOWER_X1 = 19.4;  TOWER_HW = 22.4;

// ---------------------------------------------------------------- bandeja (abraza la pestaña)
FLOOR = 4;          // piso bajo la base
TRAY_WALL_H = 10;   // altura de las paredes laterales (la pestaña mide 16)
BAR_W = 20;  BAR_T = 8;  BAR_Y = 39;   // barras de apriete sobre las alas (y = ±39)
BAR_EAR = 10;       // las barras sobresalen y se atornillan fuera de la pestaña
PAD = 1.0;          // goma o TPU bajo las barras

// ---------------------------------------------------------------- riel cola de milano (tipo Arca, 38 mm)
// Perfil (de abajo hacia arriba): 38 mm de ancho los primeros RAIL_FLAT mm, luego se angosta a
// 45° hasta RAIL_W - 2*RAIL_BEVEL. Las mordazas del receptor montan sobre esos biseles y tiran el
// riel hacia abajo. Imprimir primero coupon.scad y probarlo con la pinza que se vaya a usar.
RAIL_W = 38;  RAIL_FLAT = 6;  RAIL_BEVEL = 3;  RAIL_L = 100;
RAIL_H = RAIL_FLAT + RAIL_BEVEL;
PIN_GROOVE_W = 6.2;  PIN_GROOVE_D = 2;   // ranura para el tornillo de seguridad M4

// ---------------------------------------------------------------- receptor (mesa y morral)
RX_L = 70;          // largo de agarre a lo largo del riel
RX_SIDE = 16;       // ancho de cada mordaza
RX_BASE = 8;        // espesor bajo el riel
JAW_TRAVEL = 4;     // recorrido de la mordaza móvil

// ---------------------------------------------------------------- tornillería
M3_INSERT = 4.0;  M5 = 5.4;  M5_HEAD = 9.5;  M5_NUT = 8.0 / cos(30) + 0.4;  M5_NUT_H = 4.2;
M6 = 6.4;  M6_NUT = 10.0 / cos(30) + 0.4;  M6_NUT_H = 5.2;  M4 = 4.4;  M8 = 8.4;

// ---------------------------------------------------------------- morral (marco: hombros del usuario)
// x adelante, y izquierda, z arriba; origen = centro de los hombros. El brazo va en el hombro derecho.
ARM_BASE = [-100, -260, 0];      // origen de la base del brazo (igual que MOUNT en sim/backpack.py)
SHEET = [3, 250, 380];           // placa de HDPE 3 mm (entra en el bolsillo de la laptop)
SHEET_X = -135;                  // cara delantera de la placa (hacia la espalda)
SHEET_TOP = -40;                 // borde de arriba de la placa
TUBE = 20;  TUBE_T = 1.5;        // tubo cuadrado de aluminio 20 x 20 x 1.5
FOOT_AT = [-154, -100, -60];     // donde nace el tubo (pie atornillado arriba a la derecha de la placa)
HEAD_AT = [-154, -225, -45];     // donde termina el tubo (cabeza con bisagra)
HINGE_BEHIND = 30;               // la bisagra está detrás del riel: el brazo se dobla hacia atrás
FOLD_TORQUE = 7;                 // N·m: con más que esto, los imanes ceden y el brazo se dobla
MAGNET_D = 10;  MAGNET_H = 5;    // imanes de neodimio 10 x 5 mm (4 pares)
BOX_IN = [45, 140, 95];          // caja de electrónica (adentro): Orange Pi 5 Pro + batería 3S + buck
BOX_Z = -330;                    // centro de la caja (abajo en la placa)
