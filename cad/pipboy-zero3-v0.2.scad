// Pip-Boy - wrist enclosure for Orange Pi Zero 3 + 5" HDMI display
// v0.2 - styled pass: screen hood, canister, control panel, wrap-around cuff.
// See docs/pipboy-zero3.md
//
// Parts (set PART, or pass -D 'PART="body"' on the command line):
//   assembly | exploded | body | bezel | cuff | knob
//
// Dimensions marked MEASURE are not confirmed against real parts: check them
// with calipers on your own display / board before printing.

PART = "assembly";
SHOW_GHOSTS = true;   // stand-ins for the electronics
SHOW_ARM = true;      // forearm stand-in in the assembly view
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
OPI_CENTER = [43, 53];

/* [Battery: 1x 21700 cell] */
BATT_D = 21.4;
BATT_L = 71;
BATT_X0 = 17;
BATT_Y = 14.5;

/* [Enclosure] */
WALL = 2.4;
FLOOR = 2;
R_OUT = 9;
BEZEL_T = 3;
BAY_H = 26;            // electronics bay under the display
MARGIN_L = 9;          // left of the display: screw bosses
GUTTER = 12;           // above the display: HDMI/USB ribbon cables
POD_W = 34;            // right of the display: controls + speaker
FOAM = 0.3;            // foam tape between bezel and LCD
CLR = 0.4;             // fit clearance around the display PCB

/* [Controls] */
BTN_D = 7.2;           // 7 mm panel-mount momentary buttons (PBS-110)
BTN_Y = [46, 60, 74];
LED_D = 5.1;
LED_Y = 86.5;
LABEL = "PIP-BOY";     // engraved on the bezel; "" for none
SPK_D = 28;            // round 28 mm speaker
SPK_Y = 20;
ENC_D = 7.2;           // EC11 rotary encoder bushing
ENC_Y = 60;
ENC_Z = 17;
TOGGLE_D = 6.2;        // mini toggle switch (MTS-102) as power switch
TOGGLE_Z = 16;
USBC_Z = 5.2;          // MEASURE: charge port centre above the floor

/* [Styling] */
HOOD_H = 5;            // height of the raised screen hood
HOOD_FRAME = 7;        // hood width around the window, at its base
HOOD_RUN = 4;          // how far the hood opening flares out (CRT look)
RIB_R = 1.4;           // vertical ribs on the long walls
FIN_OUT = 2.5;         // heat-sink fins on the left end

/* [Wrist cuff] */
R_ARM = 43;            // inner radius; pad with EVA foam for thinner arms
WRAP = 68;             // how far the wings reach down each side (degrees)
CUFF_MIN_T = 5.5;
STRAP_W = 40;          // slots for 38 mm velcro straps
STRAP_T = 4.5;
STRAP_DX = 42;         // strap centres, +/- from the middle
STRAP_A = 58;          // slot position on the wing (degrees from the top)
CUFF_RAKE = 0.55;      // how much the wing ends lean in (mm per mm of depth)

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
WING_T = OY / 2 - R_ARM;               // cuff sides end flush with the body
ARM_Z = -(CUFF_MIN_T + R_ARM);         // forearm axis, relative to the cuff top
CUFF_H = -(ARM_Z + R_ARM * cos(WRAP)); // how far the wings hang below the body
WIN_CX = DX0 + DISP_X / 2 + ACTIVE_OFF_X;
WIN_CY = DY0 + DISP_Y / 2 + ACTIVE_OFF_Y;
WIN_X = ACTIVE_X + 1;
WIN_Y = ACTIVE_Y + 1;
HOOD_TOP_Y = WIN_CY + WIN_Y / 2 + HOOD_FRAME;
CAN_Y = CAV_Y + WALL - 7.1;            // canister axis on the upper strip

BEZEL_SCREWS = [
    [3.5, 3.5], [3.5, CAV_Y - 3.5],
    [CAV_X - 3.5, 3.5], [CAV_X - 3.5, CAV_Y - 3.5],
    [DX0 + DISP_X * 0.58, CAV_Y - 3.5]
];
CUFF_SCREWS = [
    [4.2, 30], [4.2, 62],
    [CAV_X - 4.2, 30], [CAV_X - 4.2, 62]
];

echo(str("Body (mm): ", OX, " x ", OY, " x ", FLOOR + RIM_Z + BEZEL_T + HOOD_H,
         " | cuff hangs ", CUFF_H, " below | wing thickness ", WING_T));

// ---------- helpers ----------
module rbox(size, r) {
    linear_extrude(size[2])
        translate([r, r]) offset(r) square([size[0] - 2 * r, size[1] - 2 * r]);
}

// centred 2D rounded rectangle
module rrect(w, h, r) {
    offset(r) square([w - 2 * r, h - 2 * r], center = true);
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
        cylinder(d = ENC_D, h = WALL + 4);
    // vents: upper wall next to the Orange Pi, and left end wall
    for (i = [0 : 6]) translate([18 + i * 8, CAV_Y - 1, 6]) cube([2.5, WALL + 2, 12]);
    for (i = [0 : 6]) translate([-WALL - 1, 16 + i * 8, 6]) cube([WALL + 2, 2.5, 12]);
}

module body_shell() {
    translate([-WALL, -WALL, -FLOOR]) rbox([OX, OY, FLOOR + RIM_Z], R_OUT);
}

// vertical rib with a rounded top, standing on the print bed
module rib(h) {
    hull() {
        cylinder(r = RIB_R, h = 0.01, $fn = 16);
        translate([0, 0, h]) sphere(r = RIB_R, $fn = 16);
    }
}

module body_styling() {
    // ribs on the lower wall, and on the upper wall beyond the vents
    for (x = [22 : 6 : 118]) translate([x, -WALL, -FLOOR]) rib(FLOOR + RIM_Z - 5);
    for (x = [82 : 6 : 124]) translate([x, CAV_Y + WALL, -FLOOR]) rib(FLOOR + RIM_Z - 5);
    // heat-sink fins between the vent slots on the left end
    for (i = [-1 : 6]) translate([-WALL - FIN_OUT, 16 + i * 8 + 3.75, -FLOOR]) hull() {
        cube([FIN_OUT + 0.1, 3, FLOOR + 20]);
        translate([FIN_OUT, 0, 0]) cube([0.1, 3, FLOOR + 20 + FIN_OUT]);
    }
    // collar around the encoder (45 degree cone: prints without supports)
    translate([CAV_X + WALL - 0.01, ENC_Y, ENC_Z]) rotate([0, 90, 0])
        cylinder(d1 = 28, d2 = 24, h = 2);
}

module body() {
    difference() {
        union() {
            difference() {
                body_shell();
                rbox([CAV_X, CAV_Y, RIM_Z + 1], R_OUT - WALL);
            }
            intersection() { body_internals(); body_shell(); }
            body_styling();
        }
        body_cutouts();
    }
}

// ---------- bezel ----------
// D-shaped tube lying on the bezel (prints face up without supports)
module dtube(x0, x1, r) {
    translate([x0, CAN_Y, BEZEL_T - 0.01]) intersection() {
        hull() {
            translate([0, -r, 0]) cube([x1 - x0, 2 * r, 0.01]);
            translate([0, 0, 1.5]) rotate([0, 90, 0]) cylinder(r = r, h = x1 - x0);
        }
        translate([0, -r, 0]) cube([x1 - x0, 2 * r, r + 2]);
    }
}

module canister(x0, x1) {
    dtube(x0, x1, 6);
    for (x = [x0, (x0 + x1) / 2 - 1.5, x1 - 3]) dtube(x, x + 3, 7);
    // thin rings between the collars
    for (x = [x0 + 9 : 5 : x1 - 9])
        if (abs(x - (x0 + x1) / 2) > 5) dtube(x, x + 1.2, 6.5);
}

module hood() {
    translate([WIN_CX, WIN_CY, 0]) hull() {
        translate([0, 0, BEZEL_T - 0.01]) linear_extrude(0.01)
            rrect(WIN_X + 2 * HOOD_FRAME, WIN_Y + 2 * HOOD_FRAME, 8);
        translate([0, 0, BEZEL_T + HOOD_H - 0.01]) linear_extrude(0.01)
            rrect(WIN_X + 2 * HOOD_FRAME - 2.4, WIN_Y + 2 * HOOD_FRAME - 2.4, 7);
    }
}

module nameplate(x0, x1) {
    w = x1 - x0;
    translate([(x0 + x1) / 2, CAN_Y, BEZEL_T - 0.01]) {
        linear_extrude(0.8) rrect(w, 10.5, 2);
        linear_extrude(1.6) difference() { rrect(w, 10.5, 2); rrect(w - 2, 8.5, 1.2); }
        if (LABEL != "")
            linear_extrude(1.6) text(LABEL, size = 5.2, halign = "center", valign = "center",
                                     font = "Liberation Sans:style=Bold");
    }
}

module control_panel() {
    translate([POD_CX, 0, BEZEL_T - 0.01]) {
        // speaker surround
        translate([0, SPK_Y, 0]) difference() {
            cylinder(d1 = 34, d2 = 31.5, h = 2.5);
            translate([0, 0, -1]) cylinder(d = 27, h = 5);
        }
        // rail around the three buttons
        difference() {
            hull() for (y = [BTN_Y[0], BTN_Y[2]]) translate([0, y, 0])
                cylinder(d1 = 17, d2 = 15.5, h = 2);
            hull() for (y = [BTN_Y[0], BTN_Y[2]]) translate([0, y, -1])
                cylinder(d = 12.6, h = 5);
        }
        // LED bezel
        translate([0, LED_Y, 0]) cylinder(d1 = 10, d2 = 8, h = 2.5);
    }
}

module bezel() {
    top = BEZEL_T + HOOD_H;
    difference() {
        union() {
            translate([-WALL, -WALL, 0]) rbox([OX, OY, BEZEL_T], R_OUT);
            hood();
            canister(DX0 + 5, DX0 + DISP_X * 0.58 - 8);
            nameplate(DX0 + DISP_X * 0.58 + 8, DX1 - 1);
            control_panel();
        }
        // screen window: flares out towards the front, like a CRT surround
        translate([WIN_CX, WIN_CY, 0]) hull() {
            translate([0, 0, -0.5]) linear_extrude(0.01) rrect(WIN_X, WIN_Y, 1.5);
            translate([0, 0, top + 0.5]) linear_extrude(0.01)
                rrect(WIN_X + 2 * HOOD_RUN, WIN_Y + 2 * HOOD_RUN, 5);
        }
        // countersunk M3 screws
        for (p = BEZEL_SCREWS) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = 3.4, h = BEZEL_T + 2);
            translate([0, 0, BEZEL_T - 1.7]) cylinder(d1 = 3.4, d2 = 6.8, h = 1.71);
            translate([0, 0, BEZEL_T]) cylinder(d = 6.8, h = top);
        }
        // buttons and status LED
        for (y = BTN_Y) translate([POD_CX, y, -1]) cylinder(d = BTN_D, h = top + 2);
        translate([POD_CX, LED_Y, -1]) cylinder(d = LED_D, h = top + 2);
        // speaker grille
        translate([POD_CX, SPK_Y, -1]) {
            cylinder(d = 2.2, h = BEZEL_T + 2);
            for (ring = [[4, 6], [8, 12], [11.5, 18]], i = [0 : ring[1] - 1])
                rotate([0, 0, i * 360 / ring[1]]) translate([ring[0], 0, 0])
                    cylinder(d = 2.2, h = BEZEL_T + 2, $fn = 16);
        }
    }
}

// ---------- cuff ----------
// cross-section in (y, z): flat top under the body, wings wrapping the forearm
module cuff_profile() {
    big = 4 * R_ARM;
    difference() {
        intersection() {
            hull() {
                translate([-OY / 2, -CUFF_MIN_T]) square([OY, CUFF_MIN_T]);
                translate([0, ARM_Z]) circle(r = R_ARM + WING_T, $fn = 200);
            }
            translate([0, ARM_Z]) polygon([
                [0, 0], [-big * sin(WRAP), big * cos(WRAP)],
                [-big, big], [big, big], [big * sin(WRAP), big * cos(WRAP)]
            ]);
        }
        translate([0, ARM_Z]) circle(r = R_ARM, $fn = 200);
    }
}

module cuff() {
    slot_r = R_ARM + WING_T / 2;
    difference() {
        intersection() {
            translate([-WALL, CY, 0]) rotate([90, 0, 90]) linear_extrude(OX) cuff_profile();
            translate([-WALL, -WALL, -200]) rbox([OX, OY, 200], R_OUT);
            // raked ends: the wings are shorter than the top
            translate([0, CY + 100, 0]) rotate([90, 0, 0]) linear_extrude(200) polygon([
                [-WALL, 0], [-WALL, -CUFF_MIN_T],
                [-WALL + CUFF_RAKE * (CUFF_H + 1 - CUFF_MIN_T), -CUFF_H - 1],
                [OX - WALL - CUFF_RAKE * (CUFF_H + 1 - CUFF_MIN_T), -CUFF_H - 1],
                [OX - WALL, -CUFF_MIN_T], [OX - WALL, 0]
            ]);
        }
        // strap slots through the wings
        for (s = [-1, 1], side = [-1, 1])
            translate([CX + s * STRAP_DX - STRAP_W / 2,
                       CY + side * slot_r * sin(STRAP_A) - 15,
                       ARM_Z + slot_r * cos(STRAP_A) - STRAP_T / 2])
                cube([STRAP_W, 30, STRAP_T]);
        // armour-plate grooves along the sides
        for (side = [-1, 1], z = [-9, -17])
            translate([-WALL - 1, CY + side * (OY / 2 - 0.4) - 0.5, z])
                cube([OX + 2, 1, 1.2]);
        // M3 screws from the arm side, heads recessed
        for (p = CUFF_SCREWS) translate([p[0], p[1], 0]) {
            translate([0, 0, -30]) cylinder(d = 3.4, h = 31);
            translate([0, 0, -30]) cylinder(d = 6.5, h = 27);
        }
    }
}

// ---------- encoder knob ----------
module knob() {
    difference() {
        union() {
            cylinder(d = 27, h = 4);
            translate([0, 0, 4]) cylinder(d1 = 27, d2 = 22, h = 9);
            // pointer
            translate([3, -1, 12.99]) cube([8, 2, 1]);
        }
        for (i = [0 : 9]) rotate([0, 0, i * 36 + 18]) translate([15, 0, -1])
            cylinder(d = 6, h = 16, $fn = 24);
        // 6 mm D-shaft
        translate([0, 0, -1]) intersection() {
            cylinder(d = 6.2, h = 11);
            translate([-3.1, -3.1, 0]) cube([6.2, 4.8, 11]);
        }
    }
}

// ---------- ghosts ----------
module ghosts() {
    // display: PCB + LCD
    color("darkgreen") translate([DX0, DY0, BAY_H]) cube([DISP_X, DISP_Y, DISP_PCB_T]);
    color([0.05, 0.25, 0.08]) translate([DX0 + 2, DY0 + 2, BAY_H + DISP_PCB_T])
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

module arm_ghost() {
    color([0.85, 0.68, 0.55]) translate([CX, CY, -FLOOR + ARM_Z]) rotate([0, 90, 0])
        cylinder(r = R_ARM - 1.5, h = OX + 110, center = true, $fn = 96);
}

// ---------- output ----------
if (PART == "body") {
    body();
} else if (PART == "bezel") {
    // printed face up, flat underside on the bed
    bezel();
} else if (PART == "cuff") {
    // printed with the flat side on the bed, wings pointing up
    mirror([0, 0, 1]) cuff();
} else if (PART == "knob") {
    knob();
} else {
    gap = PART == "exploded" ? 34 : 0;
    color([0.33, 0.38, 0.22]) body();
    color([0.16, 0.17, 0.15]) translate([0, 0, RIM_Z + gap]) bezel();
    color([0.33, 0.38, 0.22]) translate([0, 0, -FLOOR - gap]) cuff();
    color("goldenrod") translate([CAV_X + WALL + 3 + gap, ENC_Y, ENC_Z])
        rotate([0, 90, 0]) knob();
    if (SHOW_GHOSTS) translate([0, 0, gap / 3]) ghosts();
    if (SHOW_ARM && PART != "exploded") arm_ghost();
}
