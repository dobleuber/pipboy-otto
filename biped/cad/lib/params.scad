// Parámetros comunes de Mini16 (mm). Todo el diseño depende de estos valores.

// ---------- Impresión ----------
CL   = 0.4;   // holgura de ajuste entre piezas (0.3-0.4 según la impresora)
GAP  = 1.0;   // separación mínima entre piezas que se mueven entre sí
T    = 3.0;   // brazos y placas estructurales (PETG, 4 perímetros con boquilla 0.4 = 1.6 mm + relleno)
TF   = 2.0;   // placas fijas apoyadas en la cara del servo: deben ser más finas que lo que
              // sobresale el disco (2.6 mm) para no rozar el brazo que gira encima

// ---------- Servo Feetech STS3215 (plano oficial Waveshare/Feetech "SCS215") ----------
S_SHORT  = 10.11;  // del eje al extremo corto
S_LONG   = 35.11;  // del eje al extremo largo (45.22 total)
S_W      = 24.72;  // ancho
S_CASE   = 32.0;   // espesor de la carcasa (entre las caras con discos)
S_DISC_D = 19.2;   // diámetro de los discos (salida y pasivo)
S_DISC_Z = 37.25 / 2;  // cara exterior de cada disco desde el plano medio
S_HORN_R = 7.0;    // radio del círculo de 4 agujeros M2 del disco
M2_HOLE  = 2.4;    // paso para tornillo M2
HORN_CENTER = 6.5; // paso para la cabeza del tornillo central M3 del disco
// Agujeros M2 de la carcasa (en ambas caras), medidos desde el eje a lo largo del cuerpo.
// Cara de salida: 8.3 y 32.75; cara pasiva: 8.3 y 29.0. Se perforan los tres en ambas caras
// para que las piezas sirvan en la pierna izquierda y en la derecha (espejo).
S_CASE_HOLES_X = [8.3, 29.0, 32.75];
S_CASE_HOLE_Y  = 10.25;
S_CORNER_R = sqrt(S_SHORT * S_SHORT + (S_W / 2) * (S_W / 2));  // 16.0: esquina del lado corto

// ---------- Pierna: distancias entre ejes (se pasan al modelo de simulación) ----------
R_CB    = S_CORNER_R + GAP;          // radio interior del travesaño de cada "U"
ARM_R   = 11.0;                      // radio del extremo redondeado de los brazos (cubre el disco)
D_YAW_ROLL   = T + R_CB + 5;         // cara del disco del servo yaw -> eje roll
                                     // (+5 mm: el servo roll, acostado hacia afuera, puede inclinarse ±29°)
D_ROLL_PITCH = S_W / 2 + 3.5 + S_W / 2;   // eje roll -> eje pitch (servo roll sobre servo pitch)
D_THIGH = R_CB + T + GAP + S_W / 2;  // eje cadera pitch -> eje rodilla
// Servo del tobillo pitch en la canilla:
//   "fwd": acostado hacia adelante -> canilla corta (33 mm); la rodilla llega a ~83°
//   "up":  parado a lo largo de la canilla -> canilla de 56 mm; la rodilla llega a ~100°
SHIN_SERVO = "fwd";
D_SHIN  = SHIN_SERVO == "up" ? R_CB + T + GAP + S_LONG : R_CB + T + GAP + S_W / 2;
D_ANKLE = D_THIGH;                   // eje tobillo pitch -> eje tobillo roll
FOOT_CLEAR = 27.5;                   // eje tobillo roll -> cara superior de la plancha del pie
                                     // (deja inclinar el pie ±29° sin tocar el servo, que sobresale hacia afuera)
PLATE_T = 3.0;                       // plancha del pie (PETG)
SOLE_T  = 4.0;                       // suela (TPU 95A)
D_SOLE  = FOOT_CLEAR + PLATE_T + SOLE_T;   // eje tobillo roll -> suela

HIP_Y   = 30.0;                      // separación lateral de cada pierna desde el centro
FOOT_X0 = -38;  FOOT_X1 = 48;        // largo del pie (8.6 cm), x hacia adelante
FOOT_HW = 22;                        // medio ancho del pie (4.4 cm)
ROCKER_R = 6;                        // radio de la suela curva en punta, talón y costados

// ---------- Sensores de pisada (microinterruptor tipo SS-10: MEDIR el comprado) ----------
SW_L = 13.0; SW_W = 6.0; SW_H = 6.5;   // cuerpo
SW_PIN = 2.0;                          // pernos de montaje (separación SW_PIN_DX)
SW_PIN_DX = 6.5;
SW_X = [FOOT_X1 - 11, FOOT_X0 + 11];   // punta y talón

// ---------- Insertos M3 de latón ----------
INSERT_D = 4.0;   // agujero para inserto M3 (revisar con el fabricante del inserto)
INSERT_L = 5.0;
INSERT_BOSS = 7.5;
M3_HOLE = 3.4;

$fn = 48;
