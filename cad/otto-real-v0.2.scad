// Otto Mobile - Real Body v0.2
// Functional design to hold actual hardware

$fn = 32;

// Real component dimensions
OP5P_LENGTH = 85;
OP5P_WIDTH = 56;
OP5P_HEIGHT = 20; // with some clearance

SCREEN_WIDTH = 121;
SCREEN_HEIGHT = 78;
SCREEN_DEPTH = 8;

SERVO_WIDTH = 12;
SERVO_LENGTH = 23;
SERVO_HEIGHT = 22;

CAMERA_WIDTH = 25;
CAMERA_HEIGHT = 25;

WALL_THICKNESS = 2;

module orange_pi_5_pro() {
    color("limegreen")
    cube([OP5P_LENGTH, OP5P_WIDTH, 15], center=true);
    
    // Ports visualization (one side)
    translate([0, OP5P_WIDTH/2 + 2, 0])
    color("silver")
    cube([30, 4, 8], center=true);
}

module display_5inch() {
    // PCB
    color("darkgreen")
    cube([SCREEN_WIDTH + 10, SCREEN_HEIGHT + 10, 2], center=true);
    
    // Visible screen
    color("black")
    translate([0, 0, 1.1])
    cube([SCREEN_WIDTH, SCREEN_HEIGHT, 0.5], center=true);
}

module servo_sg90() {
    union() {
        // Main body
        color("blue")
        cube([SERVO_LENGTH, SERVO_WIDTH, SERVO_HEIGHT - 6], center=true);
        
        // Top shaft
        translate([SERVO_LENGTH/4, 0, (SERVO_HEIGHT - 6)/2 + 2])
        color("white")
        cylinder(h=4, r=3);
        
        // Wire
        translate([-SERVO_LENGTH/2 - 5, 0, 0])
        color("red")
        cube([10, 2, 2], center=true);
    }
}

module arducam() {
    cube([CAMERA_WIDTH, CAMERA_WIDTH, 5], center=true);
    // Lens
    translate([0, 0, 2.5])
    cylinder(h=3, r=6);
}

// ============= BODY DESIGN =============

module body_base() {
    // Main compartment for Orange Pi
    inner_l = OP5P_LENGTH + 10;
    inner_w = OP5P_WIDTH + 15;
    inner_h = OP5P_HEIGHT + 5;
    
    difference() {
        // Outer shell
        cube([inner_l + WALL_THICKNESS*2, 
              inner_w + WALL_THICKNESS*2, 
              inner_h + WALL_THICKNESS], 
             center=true);
        
        // Inner cutout
        translate([0, 0, WALL_THICKNESS/2])
        cube([inner_l, inner_w, inner_h + 1], center=true);
        
        // Port access (back)
        translate([0, -inner_w/2 - 1, 0])
        cube([40, WALL_THICKNESS*2, 15], center=true);
        
        // Ventilation slots
        for (i = [-2:2]) {
            translate([i * 15, inner_w/2 + 1, 5])
            rotate([90, 0, 0])
            cylinder(h=WALL_THICKNESS*2, r=3);
        }
    }
    
    // Orange Pi (inside)
    translate([0, 0, -inner_h/2 + OP5P_HEIGHT/2 - 3])
    %orange_pi_5_pro();
}

module display_housing() {
    // Frame for 5" display (acts as Otto's "face")
    frame_w = SCREEN_WIDTH + 20;
    frame_h = SCREEN_HEIGHT + 20;
    
    difference() {
        // Frame
        cube([frame_w, frame_h, 15], center=true);
        
        // Screen cutout
        translate([0, 0, 5])
        cube([SCREEN_WIDTH + 2, SCREEN_HEIGHT + 2, 10], center=true);
        
        // Cable slot
        translate([0, -frame_h/2 + 5, -2])
        cube([20, 10, 8], center=true);
    }
    
    // Display (inside)
    translate([0, 0, 3])
    %display_5inch();
}

module pan_tilt_head() {
    // Pan servo base
    translate([0, 0, 0])
    rotate([0, 0, 90])
    servo_sg90();
    
    // Tilt mechanism
    translate([0, 0, SERVO_HEIGHT - 6])
    union() {
        // L-bracket (simplified)
        color("gray")
        difference() {
            union() {
                cube([30, 10, 3], center=true);
                translate([0, 10, 10])
                cube([30, 10, 3], center=true);
            }
            // Servo horn hole
            cylinder(h=10, r=4);
        }
        
        // Tilt servo
        translate([0, 20, 10])
        rotate([90, 0, 0])
        rotate([0, 0, 90])
        servo_sg90();
        
        // Camera mount
        translate([0, 20, 25])
        rotate([90, 0, 0]) {
            // Mount plate
            color("gray")
            difference() {
                cube([35, 30, 3], center=true);
                cylinder(h=10, r=4);
            }
            // Camera
            translate([0, 0, 5])
            %arducam();
        }
    }
}

module full_assembly() {
    // Body base (Orange Pi compartment)
    translate([0, 0, 0])
    body_base();
    
    // Display face (front, angled up)
    translate([50, 0, 25])
    rotate([0, -30, 0])
    display_housing();
    
    // Pan-tilt head (top)
    translate([0, 0, 35])
    pan_tilt_head();
    
    // Mounting tabs for morral/strap
    for (side = [-1, 1]) {
        translate([side * 55, 0, -10])
        color("orange")
        difference() {
            cube([10, 20, 5], center=true);
            translate([0, 0, -2])
            cylinder(h=10, r=2.5);
        }
    }
}

// Render
full_assembly();

// Exploded view (uncomment to see)
//translate([0, 80, 0]) body_base();
//translate([80, 0, 0]) display_housing();
//translate([160, 0, 0]) pan_tilt_head();
