// Pip-Boy - wrist enclosure for Orange Pi Zero 3 + 5" HDMI display
// v0.1 - first parametric pass. See docs/DESIGN-zero3.md
//
// Parts (set PART, or pass -D 'PART="body"' on the command line):
//   assembly | exploded | body | bezel | cuff | knob
//
// Dimensions marked MEASURE are not confirmed against real parts: check them
// with calipers on your own display / board before printing.

PART = "assembly";
SHOW_GHOSTS = true;   // translucent stand-ins for the electronics
$fn = 48;

/* [Display: 5" HDMI 800x480 module] */
DISP_X = 121;          // PCB long side
DISP_Y = 78;           // PCB short side
DISP_PCB_T = 1.6;
DISP_STACK_T = 7.2;    // MEASURE: back of PCB to front of LCD glass
ACTIVE_X = 108.0;      // visible area of a 5" 800x480 panel
ACTIVE_Y = 64.8;
ACTIVE_OFF_X = 0;      // MEASURE: visible-area centre relative to PCB centre
ACTIVE_OFF_Y = 0;

/* [Orange Pi Zero 3] */
OPI_X = 55;
OPI_Y = 50;
OPI_HOLE_DX = 50;      // MEASURE: mounting hole pattern (unconfirmed)
OPI_HOLE_DY = 45;      // MEASURE
OPI_STANDOFF_H = 4;    // clears the microSD slot on the underside
OPI_PILOT_D = 2.2;     // pilot for M2.5 self-tapping screws
OPI_ROT = 0;           // 0 or 90: turn the board so micro-HDMI faces free space
OPI_CENTER = [42, 53];

/* [Battery: 1x 21700 cell] */
BATT_D = 21.4;
BATT_L = 71;
BATT_X0 = 16;
BATT_Y = 14.5;

/* [Enclosure] */
WALL = 2.4;
FLOOR = 2;
R_OUT = 6;
BEZEL_T = 3;
BAY_H = 26;            // electronics bay under the display
MARGIN_L = 8;          // left of the display: screw bosses
GUTTER = 12;           // above the display: HDMI/USB ribbon cables
POD_W = 34;            // right of the display: controls + speaker
FOAM = 0.3;            // foam tape between bezel and LCD
CLR = 0.4;             // fit clearance around the display PCB

/* [Controls] */
BTN_D = 7.2;           // 7 mm panel-mount momentary buttons (PBS-110)
BTN_Y = [46, 60, 74];
LED_D = 5.1;
LED_Y = 85.5;
LABEL = "PIP-BOY";     // engraved on the bezel; "" for none
SPK_D = 28;            // round 28 mm speaker
SPK_Y = 20;
ENC_D = 7.2;           // EC11 rotary encoder bushing
ENC_Y = 60;
ENC_Z = 17;
TOGGLE_D = 6.2;        // mini toggle switch (MTS-102) as power switch
TOGGLE_Z = 16;
USBC_Z = 5.2;          // MEASURE: charge port centre above the floor

/* [Wrist cuff] */
R_ARM = 80;            // saddle radius (shallow; pad it with EVA foam)
CUFF_Y = 80;
CUFF_MIN_T = 5.5;
STRAP_W = 40;          // channel for 38 mm velcro straps
STRAP_T = 3;
STRAP_DX = 42;         // strap centres, +/- from the middle

// ---------- derived ----------
DX0 = MARGIN_L;                    // display PCB origin inside the cavity
DY0 = 0.5;
DX1 = DX0 + DISP_X;
DY1 = DY0 + DISP_Y;
CAV_X = DX1 + 0.5 + POD_W;
CAV_Y = DY1 + 0.5 + GUTTER;
OX = CAV_X + 2 * WALL;
OY = CAV_Y + 2 * WALL;
RIM_Z = BAY_H + DISP_STACK_T + FOAM;   // top of the body walls
FENCE_Z = BAY_H + 3;                   // locating fences around the PCB
POD_CX = (DX1 + CLR + 2 + CAV_X) / 2;
CX = CAV_X / 2;
CY = CAV_Y / 2;
CUFF_SAG = R_ARM - sqrt(R_ARM * R_ARM - CUFF_Y * CUFF_Y / 4);
CUFF_H = CUFF_MIN_T + CUFF_SAG;

BEZEL_SCREWS = [
    [3.5, 3.5], [3.5, CAV_Y - 3.5],
    [CAV_X - 3.5, 3.5], [CAV_X - 3.5, CAV_Y - 3.5],
    [DX0 + DISP_X * 0.58, CAV_Y - 3.5]
];
CUFF_SCREWS = [
    [4.2, 30], [4.2, 62],
    [CAV_X - 4.2, 30], [CAV_X - 4.2, 62]
];

echo(str("Outer size (mm): ", OX, " x ", OY, " x ",
         FLOOR + RIM_Z + BEZEL_T, " + cuff ", CUFF_H));

// ---------- helpers ----------
module rbox(size, r) {
    linear_extrude(size[2])
        translate([r, r]) offset(r) square([size[0] - 2 * r, size[1] - 2 * r]);
}

// axis-aligned block from [x0, y0] to [x1, y1], floor to ztop
module block(x0, y0, x1, y1, ztop) {
    translate([x0, y0, 0]) cube([x1 - x0, y1 - y0, ztop]);
}

module opi_place() {
    translate([OPI_CENTER[0], OPI_CENTER[1], 0]) rotate([0, 0, OPI_ROT]) children();
}

// ---------- body ----------
module display_supports() {
    // left side: shelf under the PCB edge + fence outside it
    block(0, 0, DX0 - CLR, 6, FENCE_Z);
    block(DX0 - CLR, 0, DX0 + 3, 6, BAY_H);
    block(0, DY1 - 5, DX0 - CLR, DY1 + CLR + 2, FENCE_Z);
    block(DX0 - CLR, DY1 - 5, DX0 + 3, DY1 + CLR, BAY_H);
    block(DX0 - CLR, DY1 + CLR, DX0 + 3, DY1 + CLR + 2, FENCE_Z);
    // right side: two pillars, open in the middle for cables to the pod
    block(DX1 - 3, 0, DX1 + CLR, 14, BAY_H);
    block(DX1 + CLR, 0, DX1 + CLR + 2, 14, FENCE_Z);
    block(DX1 - 3, DY1 - 12, DX1 + CLR, DY1 + CLR, BAY_H);
    block(DX1 + CLR, DY1 - 12, DX1 + CLR + 2, DY1 + CLR + 2, FENCE_Z);
    block(DX1 - 3, DY1 + CLR, DX1 + CLR, DY1 + CLR + 2, FENCE_Z);
    // mid support on the lower wall
    block(DX0 + DISP_X / 2 - 6, 0, DX0 + DISP_X / 2 + 6, 2.5, BAY_H);
}

module battery_cradle() {
    for (x = [BATT_X0 + 14, BATT_X0 + BATT_L - 17])
        difference() {
            translate([x, BATT_Y - 10, 0]) cube([3, 20, 7]);
            translate([x - 1, BATT_Y, BATT_D / 2 + 1])
                rotate([0, 90, 0]) cylinder(d = BATT_D + 0.6, h = 5);
        }
    // end stops
    for (x = [BATT_X0 - 3, BATT_X0 + BATT_L + 1])
        translate([x, BATT_Y - 6, 0]) cube([2, 12, 10]);
}

module body_internals() {
    display_supports();
    battery_cradle();
    // bezel screw bosses (M3 heat-set inserts in the top)
    for (p = BEZEL_SCREWS) translate([p[0], p[1], 0]) cylinder(r = 3.5, h = RIM_Z);
    // cuff screw bosses (inserts pressed in from below)
    for (p = CUFF_SCREWS) translate([p[0], p[1], 0]) cylinder(r = 3.5, h = 6);
    // Orange Pi standoffs
    opi_place()
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * OPI_HOLE_DX / 2, sy * OPI_HOLE_DY / 2, 0])
                cylinder(r = 3, h = OPI_STANDOFF_H);
    // rails for the charger/boost module in the pod
    for (dx = [-8, 6]) translate([POD_CX + dx, 0, 0]) cube([2, 28, 2]);
}

module body_cutouts() {
    // insert holes
    for (p = BEZEL_SCREWS) translate([p[0], p[1], RIM_Z - 6]) cylinder(d = 4.0, h = 7);
    for (p = CUFF_SCREWS) translate([p[0], p[1], -FLOOR - 1]) cylinder(d = 4.0, h = FLOOR + 5.5);
    opi_place()
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * OPI_HOLE_DX / 2, sy * OPI_HOLE_DY / 2, 0.6])
                cylinder(d = OPI_PILOT_D, h = OPI_STANDOFF_H);
    // USB-C charge port (lower wall, pod) with a recess for the plug
    translate([POD_CX, 1, USBC_Z]) rotate([90, 0, 0]) {
        hull() for (dx = [-2.9, 2.9]) translate([dx, 0, 0]) cylinder(d = 4.2, h = WALL + 2);
        translate([0, 0, 2]) hull()
            for (dx = [-3.2, 3.2]) translate([dx, 0, 0]) cylinder(d = 7.5, h = WALL);
    }
    // power toggle (upper wall, pod)
    translate([POD_CX, CAV_Y - 1, TOGGLE_Z]) rotate([-90, 0, 0])
        cylinder(d = TOGGLE_D, h = WALL + 2);
    // rotary encoder (right end wall)
    translate([CAV_X - 1, ENC_Y, ENC_Z]) rotate([0, 90, 0])
        cylinder(d = ENC_D, h = WALL + 2);
    // vents: upper wall next to the Orange Pi, and left end wall
    for (i = [0 : 6]) translate([18 + i * 8, CAV_Y - 1, 6]) cube([2.5, WALL + 2, 12]);
    for (i = [0 : 6]) translate([-WALL - 1, 16 + i * 8, 6]) cube([WALL + 2, 2.5, 12]);
}

module body() {
    difference() {
        union() {
            difference() {
                translate([-WALL, -WALL, -FLOOR]) rbox([OX, OY, FLOOR + RIM_Z], R_OUT);
                rbox([CAV_X, CAV_Y, RIM_Z + 1], R_OUT - WALL);
            }
            body_internals();
        }
        body_cutouts();
    }
}

// ---------- bezel ----------
module bezel() {
    wx = DX0 + DISP_X / 2 + ACTIVE_OFF_X;
    wy = DY0 + DISP_Y / 2 + ACTIVE_OFF_Y;
    difference() {
        union() {
            translate([-WALL, -WALL, 0]) rbox([OX, OY, BEZEL_T], R_OUT);
            // ring that centres the speaker under the grille
            translate([POD_CX, SPK_Y, -3]) difference() {
                cylinder(d = SPK_D + 3.6, h = 3.01);
                translate([0, 0, -1]) cylinder(d = SPK_D + 0.4, h = 5);
            }
        }
        // screen window, chamfered towards the front
        hull() {
            translate([wx, wy, -0.5]) cube([ACTIVE_X + 1, ACTIVE_Y + 1, 1], center = true);
            translate([wx, wy, BEZEL_T + 0.5])
                cube([ACTIVE_X + 1 + 2 * BEZEL_T, ACTIVE_Y + 1 + 2 * BEZEL_T, 1], center = true);
        }
        // countersunk M3 screws
        for (p = BEZEL_SCREWS) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = 3.4, h = BEZEL_T + 2);
            translate([0, 0, BEZEL_T - 1.7]) cylinder(d1 = 3.4, d2 = 6.8, h = 1.71);
        }
        // buttons and status LED
        for (y = BTN_Y) translate([POD_CX, y, -1]) cylinder(d = BTN_D, h = BEZEL_T + 2);
        translate([POD_CX, LED_Y, -1]) cylinder(d = LED_D, h = BEZEL_T + 2);
        // speaker grille
        translate([POD_CX, SPK_Y, -1]) {
            cylinder(d = 2.2, h = BEZEL_T + 2);
            for (ring = [[4, 6], [8, 12], [11.5, 18]], i = [0 : ring[1] - 1])
                rotate([0, 0, i * 360 / ring[1]]) translate([ring[0], 0, 0])
                    cylinder(d = 2.2, h = BEZEL_T + 2, $fn = 16);
        }
        // engraved label on the upper strip
        translate([DX0 + 30, DY1 + GUTTER / 2 + 1.5, BEZEL_T - 0.6])
            linear_extrude(1) text(LABEL, size = 6, halign = "center",
                                   valign = "center", font = "Liberation Sans:style=Bold");
    }
}

// ---------- cuff ----------
module cuff() {
    difference() {
        translate([-WALL, CY - CUFF_Y / 2, -CUFF_H]) rbox([OX, CUFF_Y, CUFF_H], R_OUT);
        // forearm saddle
        translate([CX, CY, -CUFF_MIN_T - R_ARM]) rotate([0, 90, 0])
            cylinder(r = R_ARM, h = OX + 2, center = true, $fn = 200);
        // strap channels between the cuff and the body floor
        for (s = [-1, 1])
            translate([CX + s * STRAP_DX - STRAP_W / 2, CY - CUFF_Y / 2 - 1, -STRAP_T])
                cube([STRAP_W, CUFF_Y + 2, STRAP_T + 1]);
        // M3 screws from the arm side, heads recessed
        for (p = CUFF_SCREWS) translate([p[0], p[1], 0]) {
            translate([0, 0, -CUFF_H - 1]) cylinder(d = 3.4, h = CUFF_H + 2);
            translate([0, 0, -CUFF_H - 1]) cylinder(d = 6.5, h = CUFF_H + 1 - 3);
        }
    }
}

// ---------- encoder knob ----------
module knob() {
    difference() {
        cylinder(d = 20, h = 12);
        for (i = [0 : 23]) rotate([0, 0, i * 15]) translate([10.3, 0, -1])
            cylinder(d = 1.6, h = 14, $fn = 12);
        // 6 mm D-shaft
        translate([0, 0, -1]) intersection() {
            cylinder(d = 6.2, h = 11);
            translate([-3.1, -3.1, 0]) cube([6.2, 4.7 + 0.1, 11]);
        }
    }
}

// ---------- ghosts ----------
module ghosts() {
    // display: PCB + LCD
    color("darkgreen") translate([DX0, DY0, BAY_H]) cube([DISP_X, DISP_Y, DISP_PCB_T]);
    color("black") translate([DX0 + 2, DY0 + 2, BAY_H + DISP_PCB_T])
        cube([DISP_X - 4, DISP_Y - 4, DISP_STACK_T - DISP_PCB_T]);
    // Orange Pi Zero 3 (board + tallest connector)
    opi_place() {
        color("orange") translate([-OPI_X / 2, -OPI_Y / 2, OPI_STANDOFF_H])
            cube([OPI_X, OPI_Y, 1.6]);
        color("silver") translate([-OPI_X / 2, -OPI_Y / 2 + 4, OPI_STANDOFF_H + 1.6])
            cube([21, 16, 13.5]);
    }
    // battery
    color("steelblue") translate([BATT_X0, BATT_Y, BATT_D / 2 + 1])
        rotate([0, 90, 0]) cylinder(d = BATT_D, h = BATT_L);
    // speaker
    color("dimgray") translate([POD_CX, SPK_Y, RIM_Z - 6]) cylinder(d = SPK_D, h = 6);
}

// ---------- output ----------
if (PART == "body") {
    body();
} else if (PART == "bezel") {
    // printed face down
    translate([0, 0, BEZEL_T]) mirror([0, 0, 1]) bezel();
} else if (PART == "cuff") {
    // printed with the flat side on the bed
    mirror([0, 0, 1]) cuff();
} else if (PART == "knob") {
    knob();
} else {
    gap = PART == "exploded" ? 30 : 0;
    color("darkolivegreen") body();
    color("olivedrab") translate([0, 0, RIM_Z + gap]) bezel();
    color("dimgray") translate([0, 0, -FLOOR - gap]) cuff();
    color("goldenrod") translate([CAV_X + WALL + 2 + gap, ENC_Y, ENC_Z])
        rotate([0, 90, 0]) knob();
    if (SHOW_GHOSTS) translate([0, 0, gap / 3]) ghosts();
}
