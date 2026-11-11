// Doll accessory: hair-dye (tint) brush, 50 mm long
// Prints flat on the bed (flat underside), no supports needed.
//
// Axes: X runs along the brush (x = 0 at the handle tip, x = TOTAL_LENGTH at
// the bristle tips), Y is the width, Z is the thickness (z = 0 on the bed).

$fn = 48;

/* [Overall size] */
TOTAL_LENGTH   = 50;    // handle tip to bristle tips
BRISTLE_LENGTH = 6;
HEAD_LENGTH    = 13;    // triangular paddle between handle and bristles
HANDLE_LENGTH  = TOTAL_LENGTH - BRISTLE_LENGTH - HEAD_LENGTH;

/* [Handle and head] */
HEAD_WIDTH     = 12.4;  // width where the bristles come out
NECK_WIDTH     = 3.2;   // width where the handle meets the head
TIP_WIDTH      = 1.5;   // width at the handle tip (keep >= 1.2 to be printable)
HEAD_THICKNESS = 2.6;
TIP_THICKNESS  = 1.6;
EDGE_RADIUS    = 0.9;   // rounding of the top edges
HEAD_FULLNESS  = 0.8;   // < 1 widens the head sooner (fuller shoulders)
TIP_ROUNDING   = 1.0;   // length over which the handle tip is rounded off

/* [Thumb dimple] */
DIMPLE_LENGTH  = 6.4;   // along the brush
DIMPLE_WIDTH   = 5.2;
DIMPLE_DEPTH   = 0.6;
DIMPLE_POS     = 0.60;  // 0 = neck, 1 = bristle end of the head

/* [Bristles] */
TUFT_COUNT          = 7;
BRISTLE_THICKNESS   = 2.0;
BRISTLE_BASE_WIDTH  = HEAD_WIDTH - 0.6;  // slightly inset, like a ferrule lip
BRISTLE_TIP_WIDTH   = HEAD_WIDTH + 0.8;  // bristles fan out a little
GROOVE_WIDTH        = 0.6;   // gap between tufts (at the base)
GROOVE_DEPTH_TOP    = 0.8;   // groove cut into the top face
GROOVE_DEPTH_BOTTOM = 0.4;   // groove cut into the underside
NOTCH_LENGTH        = 1.2;   // at the tips the gaps go all the way through
TUFT_BEVEL          = 0.25;  // bevel on the top edges of each tuft

/* [Resolution] */
HANDLE_STEPS = 24;
HEAD_STEPS   = 32;
CORNER_STEPS = 6;

// ---------------------------------------------------------------- profiles

function lerp(a, b, t) = a + (b - a) * t;
function smoothstep(t) = t * t * (3 - 2 * t);

// Width of the straight handle taper, extrapolated past the neck
function handle_line(x) = lerp(TIP_WIDTH, NECK_WIDTH, x / HANDLE_LENGTH);

// Full width of the body at station x
function body_width(x) =
    x < TIP_ROUNDING
        // quarter-ellipse nose; starts blunt (not at zero width) at x = 0
        ? let(u = lerp(0.1, 1, x / TIP_ROUNDING))
          handle_line(x) * sqrt(1 - pow(1 - u, 2))
    : x <= HANDLE_LENGTH
        ? handle_line(x)
    : let(s = smoothstep(pow((x - HANDLE_LENGTH) / HEAD_LENGTH, HEAD_FULLNESS)))
        lerp(handle_line(x), HEAD_WIDTH, s);

// Thickness of the body at station x
function body_thickness(x) =
    lerp(TIP_THICKNESS, HEAD_THICKNESS, min(1, x / HANDLE_LENGTH));

// Stations along X: dense at the rounded tip, then handle, then head
function stations() = concat(
    [for (i = [0 : 5]) TIP_ROUNDING * (1 - cos(15 * i))],
    [for (i = [0 : HANDLE_STEPS])
        lerp(TIP_ROUNDING, HANDLE_LENGTH, i / HANDLE_STEPS)],
    [for (i = [1 : HEAD_STEPS])
        HANDLE_LENGTH + HEAD_LENGTH * i / HEAD_STEPS]
);

// Cross-section at x: flat bottom, rounded top edges
function ring(x) =
    let(w  = body_width(x) / 2,
        t  = body_thickness(x),
        rx = min(EDGE_RADIUS, w - 0.05),
        ry = min(EDGE_RADIUS, t * 0.6))
    concat(
        [[x, w, 0]],
        [for (k = [0 : CORNER_STEPS]) let(a = 90 * k / CORNER_STEPS)
            [x,  (w - rx + rx * cos(a)), t - ry + ry * sin(a)]],
        [for (k = [CORNER_STEPS : -1 : 0]) let(a = 90 * k / CORNER_STEPS)
            [x, -(w - rx + rx * cos(a)), t - ry + ry * sin(a)]],
        [[x, -w, 0]]
    );

// ------------------------------------------------------------------ parts

module body_blank() {
    xs = stations();
    n  = len(xs);
    p  = 2 * (CORNER_STEPS + 1) + 2;   // points per ring

    points = [for (x = xs) each ring(x)];
    sides  = [for (i = [0 : n - 2], j = [0 : p - 1])
        [i * p + j, (i + 1) * p + j, (i + 1) * p + (j + 1) % p, i * p + (j + 1) % p]];
    cap_tip  = [[for (j = [0 : p - 1]) j]];
    cap_head = [[for (j = [p - 1 : -1 : 0]) (n - 1) * p + j]];

    polyhedron(points, concat(sides, cap_tip, cap_head), convexity = 4);
}

module thumb_dimple() {
    // Spherical cap of in-plane radius r and depth d, stretched along X
    r = DIMPLE_WIDTH / 2;
    d = DIMPLE_DEPTH;
    R = (r * r + d * d) / (2 * d);
    translate([HANDLE_LENGTH + HEAD_LENGTH * DIMPLE_POS, 0, HEAD_THICKNESS + R - d])
        scale([DIMPLE_LENGTH / DIMPLE_WIDTH, 1, 1])
            sphere(r = R, $fn = 96);
}

module body() {
    difference() {
        body_blank();
        thumb_dimple();
    }
}

// 2D outline of the bristle block between x0 and x1 (local X, 0 = base)
function bristle_half_width(x) =
    lerp(BRISTLE_BASE_WIDTH, BRISTLE_TIP_WIDTH, x / BRISTLE_LENGTH) / 2;

module tuft(i) {
    pitch = BRISTLE_BASE_WIDTH / TUFT_COUNT;
    // y-range at the base; outer tufts keep their outside edge
    y0 = -BRISTLE_BASE_WIDTH / 2 + i * pitch + (i == 0 ? 0 : GROOVE_WIDTH / 2);
    y1 = -BRISTLE_BASE_WIDTH / 2 + (i + 1) * pitch
         - (i == TUFT_COUNT - 1 ? 0 : GROOVE_WIDTH / 2);
    fan = BRISTLE_TIP_WIDTH / BRISTLE_BASE_WIDTH;
    b   = TUFT_BEVEL;
    ov  = 0.3;   // overlap into the head so the union is solid

    hull() {
        // full footprint up to the start of the bevel
        linear_extrude(BRISTLE_THICKNESS - b)
            polygon([[-ov, y0], [-ov, y1],
                     [BRISTLE_LENGTH, y1 * fan], [BRISTLE_LENGTH, y0 * fan]]);
        // inset footprint at the top face
        translate([0, 0, BRISTLE_THICKNESS - 0.01])
            linear_extrude(0.01)
                polygon([[-ov, y0 + b], [-ov, y1 - b],
                         [BRISTLE_LENGTH - b, y1 * fan - b],
                         [BRISTLE_LENGTH - b, y0 * fan + b]]);
    }
}

module bristles() {
    ov = 0.3;
    translate([HANDLE_LENGTH + HEAD_LENGTH, 0, 0]) {
        for (i = [0 : TUFT_COUNT - 1]) tuft(i);

        // thin web that ties the tufts together (grooves stay visible above
        // and below it; near the tips the gaps are open, like a comb)
        w0 = BRISTLE_BASE_WIDTH / 2 - 0.3;
        w1 = bristle_half_width(BRISTLE_LENGTH - NOTCH_LENGTH) - 0.3;
        translate([0, 0, GROOVE_DEPTH_BOTTOM])
            linear_extrude(BRISTLE_THICKNESS - GROOVE_DEPTH_TOP - GROOVE_DEPTH_BOTTOM)
                polygon([[-ov, -w0], [-ov, w0],
                         [BRISTLE_LENGTH - NOTCH_LENGTH, w1],
                         [BRISTLE_LENGTH - NOTCH_LENGTH, -w1]]);
    }
}

module tint_brush() {
    color("#2b2b2b") body();
    color("#555555") bristles();
}

tint_brush();
