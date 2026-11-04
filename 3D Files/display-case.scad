// Coordinates match the supplied REAR view: buttons and USB on +X.
// Assembly Z runs from the front face toward the rear lid. Units: mm.
part = "layout"; // [layout,front,rear,assembly,exploded]
show_hardware = true;
$fn = 48;

pcb_w = 93.5;
pcb_h = 78.5;
pcb_t = 1.6;
panel_w = 91;
panel_h = 77;
panel_t = 1.2;
active_w = 84.8;
active_h = 63.6;
active_left = 3.1;
active_top = 3.1;
hole_edge_x = 4.75;
hole_edge_y = 4.25;
button_y = [16.03, 33.70];
standoff_height = 4;
standoff_tolerance = 0.2;

// Unmeasured stack-up and connector dimensions: verify before final printing.
panel_offset_x = (pcb_w - panel_w) / 2;
panel_offset_y = (pcb_h - panel_h) / 2;
panel_adhesive = 0.8;
gasket_t = 0.5;
standoff_d = 6.5; // Reference envelope only; height is user-supplied.
standoff_bore_d = 3; // Reference only; the original peg diameter is retained.
header_height = 8.5; // PCB rear to Pico underside, including seated headers.
pico_t = 1;
pico_component_height = 5;
electronics_height = 18; // Above the DISPLAY PCB rear, including the headers.
pico_w = 51;
pico_h = 21;
pico_right = pcb_w;
pico_center_y = 53.5;
usb_window_w = 16;
usb_window_bottom = 5;
usb_window_top = 18;
button_window_w = 8;
button_window_bottom = -0.5;
button_window_top = 6.5;

wall = 2;
face_t = 2;
back_t = 2;
side_clearance = 2.2;
rear_clearance = 3;
corner_r = 3;
window_margin = 0.4;
axial_play = 0.2; // Clearance above the TALLEST permissible standoff.
post_r = 2.7;
peg_d = 2.4; // Original design diameter, confirmed by the user.
peg_depth = 0.9; // Projection below the support shoulder, not insertion depth.
peg_tip_t = 0.15;
board_clearance = 0.35;
snap_width = 8;
snap_projection = 0.5;
snap_ramp = 0.5;
snap_flat = 0.25;
snap_z_clearance = 0.12;
snap_centers = [22, pcb_w - 22];
cap_clearance = 0.2;
cap_wall = 1.6;
cap_overlap = 5;
snap_groove_depth = 0.45;
port_rim_clearance = 0.8;
eps = 0.02;

pcb_front_z = face_t + gasket_t + panel_t + panel_adhesive;
pcb_back_z = pcb_front_z + pcb_t;
standoff_max = standoff_height + standoff_tolerance;
support_z = pcb_back_z + standoff_max + axial_play;
lid_z = max(
    pcb_back_z + max(electronics_height, standoff_max) + rear_clearance,
    pcb_back_z + max(usb_window_top, button_window_top) +
    cap_overlap + port_rim_clearance);
depth = lid_z + back_t;
outer_min = -side_clearance - wall;
outer_w = pcb_w + 2 * (side_clearance + wall);
outer_h = pcb_h + 2 * (side_clearance + wall);
print_min = outer_min;
print_w = pcb_w - 2*print_min;
print_h = pcb_h - 2*print_min;
cap_bottom_z = lid_z - cap_overlap;
snap_center_z = lid_z - cap_overlap/2;
snap_half_height = snap_ramp + snap_flat/2;
snap_crossing = cap_clearance / snap_projection * snap_ramp;
groove_half_height = snap_half_height - snap_crossing + snap_z_clearance;
body_inner_y = -side_clearance;
cap_outer_y = body_inner_y + cap_clearance;
active_x = panel_offset_x + active_left;
active_y = panel_offset_y + panel_h - active_top - active_h;

assert(electronics_height >= header_height + pico_t + pico_component_height,
       "Electronics envelope is too low for the Pico/header stack");
assert(standoff_height > standoff_tolerance && standoff_tolerance >= 0,
       "Invalid standoff height/tolerance");
assert(support_z < lid_z, "Insufficient room above the standoffs");
assert(peg_d > 0 && peg_d < 2*post_r && peg_tip_t < peg_depth,
       "Invalid peg dimensions");
assert(peg_depth > axial_play + 2*standoff_tolerance &&
       support_z - peg_depth > pcb_back_z,
       "Pegs must enter the shortest standoffs without reaching the PCB");
assert(snap_projection > cap_clearance && cap_clearance > 0 &&
       snap_groove_depth > snap_projection - cap_clearance,
       "Snap ridges need positive engagement and clearance inside the grooves");
assert(wall - snap_groove_depth >= 1.2 && cap_wall >= 1.2,
       "Blind body grooves must leave at least 1.2 mm of exterior skin");
assert(side_clearance - cap_clearance - cap_wall >
       snap_projection - cap_clearance + 0.05,
       "The internal rim needs inward flex clearance outside the PCB perimeter");
assert(snap_ramp >= snap_projection && snap_flat > 0,
       "Lid ridge ramps must be no steeper than a 45 degree overhang");
assert(groove_half_height >= snap_groove_depth &&
       groove_half_height < cap_overlap/2 - 0.5 &&
       snap_half_height < cap_overlap/2 - 0.5,
       "Grooves need 45 degree ramps and solid material above/below");
assert(snap_z_clearance > 0 &&
       snap_z_clearance < peg_depth - axial_play - 2*standoff_tolerance,
       "Snap seating play must not disengage the locating pegs");
assert(hole_edge_y - post_r > 0 &&
       hole_edge_y + post_r < pico_center_y - pico_h/2 &&
       pcb_h - hole_edge_y - post_r > pico_center_y + pico_h/2,
       "Corner supports must stay outside the Pico envelope");
assert(pcb_back_z + max(usb_window_top, button_window_top) <
       cap_bottom_z &&
       cap_bottom_z - pcb_back_z - max(usb_window_top, button_window_top) >=
       port_rim_clearance - eps,
       "Internal lid rim must not obscure connector/button openings");
assert(board_clearance > 0 && board_clearance < side_clearance,
       "Invalid board locator clearance");
assert(active_x - window_margin > panel_offset_x &&
       active_y - window_margin > panel_offset_y &&
       active_x + active_w + window_margin < panel_offset_x + panel_w &&
       active_y + active_h + window_margin < panel_offset_y + panel_h,
       "Window extends outside the panel");

echo(outer_dimensions_mm = [print_w, print_h, depth],
     pcb_back_z = pcb_back_z,
     standoff_max_mm = standoff_max,
     support_height_above_pcb_mm = support_z - pcb_back_z,
     peg_diameter_mm = peg_d,
     peg_insertion_range_mm =
         [peg_depth - axial_play - 2*standoff_tolerance,
          peg_depth - axial_play],
     snap_exterior_skin_mm = wall - snap_groove_depth,
     snap_engagement_mm = snap_projection - cap_clearance,
     cap_bottom_z = cap_bottom_z,
     lid_z = lid_z);

module rounded_rect(w, h, r) {
    translate([r, r])
        offset(r = r) square([w - 2*r, h - 2*r]);
}

module outline() {
    translate([outer_min, outer_min])
        rounded_rect(outer_w, outer_h, corner_r);
}

module standoff_positions() {
    for (x = [hole_edge_x, pcb_w - hole_edge_x])
        for (y = [hole_edge_y, pcb_h - hole_edge_y])
            translate([x, y, 0]) children();
}

module cavity() {
    translate([-side_clearance, -side_clearance])
        rounded_rect(pcb_w + 2*side_clearance,
                     pcb_h + 2*side_clearance, 1);
}

module port_cuts() {
    for (y = button_y)
        translate([pcb_w - 1, y - button_window_w/2,
                   pcb_back_z + button_window_bottom])
            cube([side_clearance + wall + 3, button_window_w,
                  button_window_top - button_window_bottom]);
    translate([pcb_w - 1, pico_center_y - usb_window_w/2,
               pcb_back_z + usb_window_bottom])
        cube([side_clearance + wall + 3, usb_window_w,
              usb_window_top - usb_window_bottom]);
}

module at_long_edges() {
    children();
    translate([0, pcb_h, 0]) mirror([0, 1, 0]) children();
}

module board_locators() {
    // Perimeter guides help align the board before the lid pegs are inserted.
    for (x = [-side_clearance, pcb_w + board_clearance])
        for (y = [1, pcb_h - 8])
            translate([x, y, face_t - eps])
                cube([side_clearance - board_clearance, 7,
                      pcb_back_z - face_t + eps]);
    at_long_edges()
        for (x = [1, pcb_w - 8])
            translate([x, -side_clearance, face_t - eps])
                cube([7, side_clearance - board_clearance,
                      pcb_back_z - face_t + eps]);
}

module edge_prism(profile, length) {
    // Extrude a Y/Z profile along X.
    rotate([90, 0, 90])
        linear_extrude(length) polygon(profile);
}

module lid_ridges() {
    at_long_edges()
        for (x = snap_centers)
            translate([x - snap_width/2, 0, snap_center_z])
                edge_prism([
                    [cap_outer_y + eps,
                     -snap_half_height - eps*snap_ramp/snap_projection],
                    [cap_outer_y - snap_projection, -snap_flat/2],
                    [cap_outer_y - snap_projection, snap_flat/2],
                    [cap_outer_y + eps,
                     snap_half_height + eps*snap_ramp/snap_projection]
                ], snap_width);
}

module body_grooves() {
    at_long_edges()
        for (x = snap_centers)
            translate([x - snap_width/2 - 0.4, 0, snap_center_z])
                edge_prism([
                    [body_inner_y + eps, -groove_half_height - eps],
                    [body_inner_y - snap_groove_depth,
                     -groove_half_height + snap_groove_depth],
                    [body_inner_y - snap_groove_depth,
                     groove_half_height - snap_groove_depth],
                    [body_inner_y + eps, groove_half_height + eps]
                ], snap_width + 0.8);
}

module front() {
    difference() {
        union() {
            difference() {
                linear_extrude(lid_z) outline();
                translate([0, 0, face_t])
                    linear_extrude(depth) cavity();
                translate([active_x - window_margin,
                           active_y - window_margin, -eps])
                    cube([active_w + 2*window_margin,
                          active_h + 2*window_margin, face_t + 2*eps]);
            }
            board_locators();
        }
        port_cuts();
        body_grooves();
    }
}

module rear() {
    union() {
        translate([0, 0, lid_z]) linear_extrude(back_t) outline();
        difference() {
            translate([0, 0, cap_bottom_z])
                linear_extrude(cap_overlap + eps)
                    offset(delta = -cap_clearance) cavity();
            translate([0, 0, cap_bottom_z - eps])
                linear_extrude(cap_overlap + 2*eps)
                    offset(delta = -cap_clearance - cap_wall) cavity();
        }
        lid_ridges();
        standoff_positions() {
            translate([0, 0, support_z])
                cylinder(h = lid_z - support_z + eps, r = post_r);
            translate([0, 0, support_z - peg_depth + peg_tip_t])
                cylinder(h = peg_depth - peg_tip_t + eps, d = peg_d);
            translate([0, 0, support_z - peg_depth])
                cylinder(h = peg_tip_t + eps,
                         d1 = peg_d - 0.4, d2 = peg_d);
        }
    }
}

module hardware() {
    color([0.05, 0.25, 0.65])
        translate([0, 0, pcb_front_z]) cube([pcb_w, pcb_h, pcb_t]);
    color([0.8, 0.8, 0.75])
        translate([panel_offset_x, panel_offset_y, face_t + gasket_t])
            cube([panel_w, panel_h, panel_t]);
    color("silver")
        standoff_positions()
            translate([0, 0, pcb_back_z])
                difference() {
                    cylinder(d = standoff_d, h = standoff_max);
                    translate([0, 0, -eps])
                        cylinder(d = standoff_bore_d, h = standoff_max + 2*eps);
                }
    color([0.15, 0.15, 0.15])
        for (y = [pico_center_y - 8.89, pico_center_y + 8.89])
            translate([pico_right - pico_w, y - 1.25, pcb_back_z])
                cube([pico_w, 2.5, header_height]);
    color([0.1, 0.5, 0.25])
        translate([pico_right - pico_w, pico_center_y - pico_h/2,
                   pcb_back_z + header_height])
            cube([pico_w, pico_h, pico_t]);
    color("silver")
        translate([pico_right - 4.5, pico_center_y - 4,
                   pcb_back_z + header_height + pico_t])
            cube([6, 8, 3]);
    color("silver")
        for (y = button_y)
            translate([pcb_w - 3, y - 2, pcb_back_z])
                cube([4, 4, 3]);
}

// Lid exterior is down; its four supports print vertically upward.
if (part == "front")
    translate([-print_min, -print_min, 0]) front();
else if (part == "rear")
    translate([-print_min, pcb_h - print_min, depth])
        rotate([180, 0, 0]) rear();
else if (part == "layout") {
    translate([-print_min, -print_min, 0]) front();
    translate([print_w + 10 - print_min, pcb_h - print_min, depth])
        rotate([180, 0, 0]) rear();
} else if (part == "assembly" || part == "exploded") {
    color([0.75, 0.75, 0.8, 0.65]) front();
    translate([0, 0, part == "exploded" ? 25 : 0])
        color([0.35, 0.4, 0.5, 0.65]) rear();
    if (show_hardware) hardware();
} else
    assert(false, "Unknown part selection");
