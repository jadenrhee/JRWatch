// JRWatch enclosure - two-piece 3D-printable watch case
// ------------------------------------------------------
// Dimensions come from the actual board (hardware/jrwatch.kicad_pcb):
//   * board 36 x 36 mm, corner radius 6, thickness 0.8
//   * USB-C on the BOTTOM side, mouth at the south edge, x = 95..105 (board coords)
//   * side buttons SW1/SW2 on the east edge at y = 95 / 106 (board coords)
//   * display LS013B7DH03 on top: 26.6 x 30.3 x 0.74, active 23.04 sq,
//     FPC folds under its south edge into J2
//   * everything else on the bottom, tallest = USB-C shell (3.26)
// Case coordinates: origin at board center, +Y = board north, z=0 case bottom.
//
// Set PART before rendering:
//   "shell"    - bottom case            (print 1x)
//   "bezel"    - top ring               (print 1x)
//   "button"   - side pusher pin        (print 2x)
//   "assembly" - exploded preview       (not for printing)
//   "closed"   - assembled preview
//   "cutaway"  - assembled, sectioned through the USB slot

PART = "assembly";

/* ---------- board & stack ---------- */
board_w   = 36;      // square board edge
board_r   = 6;       // board corner radius
board_t   = 0.8;
clr       = 0.3;     // board-to-case clearance per side

floor_t   = 1.6;
bat_h     = 5.4;     // battery bay: 502030 pouch (5.0) + foam pad
comp_h    = 3.5;     // bottom-component headroom (USB-C shell is 3.26)
bezel_h   = 2.3;     // above board top

z_board   = floor_t + bat_h + comp_h;   // board underside = 10.5
z_part    = z_board + board_t;          // parting line at board top = 11.3
z_top     = z_part + bezel_h;           // 13.6 overall

/* ---------- case body ---------- */
wall      = 2.4;
cav_half  = board_w/2 + clr;            // 18.3
out_half  = cav_half + wall;            // 20.7
out_r     = 3.0;                        // outer corner radius (square-ish corners
                                        // leave meat for the screw bosses)
taper_h   = 3.0;                        // filleted/tapered lower body
taper_in  = 1.1;

/* ---------- screws (M2 x 12 self-tapping, from the back) ---------- */
screw_d    = 17.8;    // hole center at (+/-d, +/-d)
pilot_dia  = 1.7;
shank_dia  = 2.3;
head_dia   = 4.4;
head_h     = 1.4;

/* ---------- display ---------- */
disp_w    = 26.6;                 // x
disp_h    = 30.3;                 // y
disp_t    = 0.74;
disp_tape = 0.3;                  // mounting adhesive under the glass
disp_cy   = (100 - 97.65);        // panel center offset north (board y 82.5..112.8)
ap_size   = 25.2;                 // aperture over the 23.04 active area
ap_cy     = 3.2;                  // active-area center offset north (verify vs
                                  // datasheet fig 8-1 before ordering)

/* ---------- cutouts (from board footprints) ---------- */
usb_w     = 10.0;                 // slot width  (connector 8.94)
usb_zlo   = z_board - 3.6;        // slot bottom (connector hangs 3.26 below board)
usb_zhi   = z_board + 0.2;
btn_hole  = 3.2;                  // pusher pin bore
btn_y     = [ 5, -6 ];            // SW1 (board y=95), SW2 (board y=106)
btn_z     = z_board - 1.6;        // actuator center below the board

/* ---------- strap lugs (22 mm spring-bar strap) ---------- */
lug_gap   = 22.2;                 // between inner prong faces
lug_wide  = 3.0;                  // prong thickness (x)
lug_len   = 5.6;                  // protrusion from wall (y)
bar_hole  = 1.35;                 // spring-bar pin
bar_off   = 3.4;                  // hole center beyond the wall
bar_z     = 4.6;

$fn = 72;
eps = 0.01;

/* ================= 2D helpers ================= */

module rsquare(half, r) { offset(r = r) square(2*(half - r), center = true); }
module cavity2d()  rsquare(cav_half, board_r + clr);
module outer2d()   rsquare(out_half, out_r);

/* ================= shared 3D details ================= */

// crescent screw boss in each corner: post around the screw, clipped so it
// never intrudes on the board's corner arc
module corner_posts(h) {
  for (sx = [-1, 1], sy = [-1, 1])
    scale([sx, sy, 1])
      intersection() {
        linear_extrude(h) intersection() {
          translate([screw_d, screw_d]) circle(d = 5.6);
          cavity2d();
        }
        linear_extrude(h) difference() {
          square(2*out_half, center = true);
          translate([12, 12]) circle(board_r + clr + 0.05);
        }
      }
}

// annular wedge reaching under (or over) the board's corner arc - the board
// is clamped only here; the corner zones are component-free on both sides
module corner_pads(h) {
  for (sx = [-1, 1], sy = [-1, 1])
    scale([sx, sy, 1])
      linear_extrude(h) intersection() {
        translate([12, 12]) difference() { circle(5.9); circle(4.6); }
        translate([12, 12]) rotate(45)
          polygon([[0,0], [10, 4.6], [10, -4.6]]);   // ~50 deg outward wedge
      }
}

// curved watch-style lug horn, drilled for a spring bar
module lug_horn() {
  difference() {
    hull() {
      // root: blends into the case wall
      translate([0, -0.6, 4.6]) cube([lug_wide, 1.2, 8.6], center = true);
      // tip: round horn end
      translate([0, lug_len - 1.4, bar_z])
        rotate([0, 90, 0]) cylinder(h = lug_wide, r = 2.2, center = true);
    }
    translate([0, bar_off, bar_z])
      rotate([0, 90, 0]) cylinder(h = lug_wide + 1, d = bar_hole, center = true);
  }
}

module lugs()
  for (sy = [-1, 1], sx = [-1, 1])
    scale([sx, sy, 1])
      translate([lug_gap/2 + lug_wide/2, out_half - eps, 0]) lug_horn();

// raised pusher guard pods on the east wall
module button_pods()
  for (y = btn_y)
    translate([out_half - eps, y, btn_z]) rotate([0, 90, 0]) {
      cylinder(h = 1.3, d1 = 7.4, d2 = 6.2);
    }

// small alignment nubs on the shell rim (holes in the bezel underside)
nub_p = [[-(cav_half + wall/2), 0], [cav_half + wall/2, 0]];
module rim_nubs()  for (p = nub_p) translate([p[0], p[1], z_part - eps])
                     cylinder(h = 1.0 + eps, d1 = 1.9, d2 = 1.5);

/* ================= bottom shell ================= */

module shell_body() {
  // tapered, edge-filleted lower body flowing into straight walls
  hull() {
    translate([0, 0, 0])       linear_extrude(eps) rsquare(out_half - taper_in, out_r + 0.8);
    translate([0, 0, taper_h]) linear_extrude(eps) outer2d();
  }
  translate([0, 0, taper_h]) linear_extrude(z_part - taper_h) outer2d();
}

module back_engraving() {
  mirror([1, 0, 0]) {                       // reads correctly from outside
    translate([0, 2.6, -eps]) linear_extrude(0.45)
      text("JRWATCH", size = 3.4, font = "Helvetica:style=Bold",
           halign = "center", valign = "center", spacing = 1.15);
    translate([0, -2.6, -eps]) linear_extrude(0.45)
      text("r1  /  nRF52840  /  BLE", size = 1.7, font = "Helvetica",
           halign = "center", valign = "center", spacing = 1.1);
  }
  // decorative recessed rings
  for (r = [7.6, 12.4]) translate([0, 0, -eps]) linear_extrude(0.35)
    difference() { circle(r + 0.25); circle(r - 0.25); }
}

module shell() {
  difference() {
    union() { shell_body(); lugs(); button_pods(); }
    // main cavity
    translate([0, 0, floor_t]) linear_extrude(z_part) cavity2d();
    // screw shank + head pocket
    for (sx = [-1, 1], sy = [-1, 1]) {
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = z_part, d = shank_dia);
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = head_h + eps, d = head_dia);
    }
    // USB-C slot with a port-recess and plug chamfer, south wall
    translate([0, -out_half, (usb_zlo + usb_zhi)/2]) {
      cube([usb_w, 2*wall + 2, usb_zhi - usb_zlo], center = true);
      translate([0, -wall + 0.55, 0]) hull() {
        cube([usb_w + 0.4, wall, usb_zhi - usb_zlo + 0.4], center = true);
        translate([0, -0.9, 0])
          cube([usb_w + 2.4, 0.2, usb_zhi - usb_zlo + 2.2], center = true);
      }
    }
    // stepped pusher bores, east wall (pin inserts from the inside):
    // flange counterbore -> narrow retention bore -> wide channel for the cap
    for (y = btn_y) translate([cav_half - eps, y, btn_z]) rotate([0, 90, 0]) {
      translate([0, 0, -1.2]) cylinder(h = 1.2 + eps, d = 4.9);   // flange seat
      cylinder(h = 1.0 + eps, d = btn_hole);                      // retention bore
      translate([0, 0, 1.0]) cylinder(h = wall + 3, d = 4.4);     // cap channel
    }
    back_engraving();
  }
  // rebuild the corner posts (the cavity cut removed them), minus screw bores
  difference() {
    corner_posts(z_board);
    for (sx = [-1, 1], sy = [-1, 1])
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = z_board + 1, d = shank_dia);
  }
  translate([0, 0, z_board - 1.0]) corner_pads(1.0);   // board rests on these
  rim_nubs();
  // battery fence (502030 pouch + foam pad drop in here)
  translate([-1, 0, floor_t]) linear_extrude(0.8) difference() {
    rsquare(31.2/2 + 0.8, 2);
    rsquare(31.2/2, 1.6);
  }
}

/* ================= top bezel ================= */

module bezel_body() {
  // straight band, then a crowned top edge
  translate([0, 0, z_part]) linear_extrude(bezel_h - 1.0) outer2d();
  hull() {
    translate([0, 0, z_part + bezel_h - 1.0]) linear_extrude(eps) outer2d();
    translate([0, 0, z_top - eps]) linear_extrude(eps) rsquare(out_half - 0.9, out_r + 0.5);
  }
}

module bezel() {
  translate([0, 0, -z_part]) union() {    // modeled in place, shifted for printing
    difference() {
      bezel_body();
      // display pocket (panel + tape live here)
      translate([0, disp_cy, z_part - eps])
        linear_extrude(disp_tape + disp_t + 0.25 + eps)
          square([disp_w + 0.6, disp_h + 0.6], center = true);
      // FPC fold + connector relief, south-west
      translate([-10.7, -13.5, z_part - eps])
        linear_extrude(1.5 + eps) square([12.0, 8.4], center = true);
      // aperture with a 45-degree outward chamfer
      translate([0, ap_cy, z_part - eps]) {
        linear_extrude(bezel_h + 2*eps) square(ap_size, center = true);
        hull() {
          translate([0, 0, bezel_h - 0.9]) linear_extrude(eps) square(ap_size, center=true);
          translate([0, 0, bezel_h]) linear_extrude(eps) square(ap_size + 1.9, center=true);
        }
      }
      // engraved 12 o'clock index triangle on the north flat
      translate([0, ap_cy + ap_size/2 + 2.4, z_top - 0.4]) linear_extrude(0.5)
        polygon([[-1.5, 0.9], [1.5, 0.9], [0, -1.1]]);
      // engraved wordmark on the south flat
      translate([0, -(out_half - 3.3), z_top - 0.4]) linear_extrude(0.5)
        text("JRWATCH", size = 1.9, font = "Helvetica:style=Bold",
             halign = "center", valign = "center", spacing = 1.3);
      // screw pilots
      for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*screw_d, sy*screw_d, z_part - eps])
          cylinder(h = bezel_h - 0.4, d = pilot_dia);
      // alignment nub holes
      for (p = nub_p) translate([p[0], p[1], z_part - eps])
        cylinder(h = 1.25, d = 2.15);
    }
    // presses the board down onto the shell pads
    difference() {
      translate([0, 0, z_part - 0.05]) corner_pads(0.5);
      translate([0, disp_cy, z_part - 1]) linear_extrude(3)
        square([disp_w + 0.6, disp_h + 0.6], center = true);  // never touch the glass
    }
  }
}

/* ================= pusher pin (print 2) ================= */

module button_pin() {
  cylinder(h = 1.0, d = 4.5);                       // flange (inside the wall)
  translate([0, 0, 1.0 - eps]) cylinder(h = 1.0, d = 2.9);   // retention stem
  // knurled cap, rides in the wide channel and sits proud of the pod
  translate([0, 0, 2.0 - eps]) difference() {
    cylinder(h = 2.7, d = 4.0, $fn = 12);           // 12 flats = knurl look
    for (a = [0:30:330]) rotate(a) translate([2.1, 0, 0.5])
      cylinder(h = 2.4, d = 0.45, $fn = 12);
  }
}

/* ================= previews ================= */

module board_mock() {
  color("SeaGreen") linear_extrude(board_t) rsquare(board_w/2, board_r);
  // display glass + active area
  color([0.15, 0.15, 0.17]) translate([0, disp_cy, board_t + disp_tape])
    linear_extrude(disp_t) square([disp_w, disp_h], center = true);
  color([0.05, 0.05, 0.06]) translate([0, ap_cy, board_t + disp_tape + disp_t])
    linear_extrude(0.02) square(23.04, center = true);
  // bottom-side landmarks: radio module (north), USB-C shell (south)
  color("Silver") translate([0, 12.8, -2.0]) linear_extrude(2.0)
    square([12.4, 7.5], center = true);
  color("Silver") translate([0, -16.2, -3.2]) linear_extrude(3.2)
    square([8.9, 7.3], center = true);
}

module battery_mock()
  color([0.55, 0.58, 0.62]) translate([-1, 0, floor_t + 0.5])
    linear_extrude(5.0) rsquare(15, 2.5);

module buttons_in_place()
  for (y = btn_y)
    color([0.9, 0.45, 0.1]) translate([cav_half - 1.2, y, btn_z])
      rotate([0, 90, 0]) button_pin();

module closed_assembly(with_mocks = true) {
  color([0.23, 0.25, 0.28]) shell();
  if (with_mocks) { battery_mock(); translate([0, 0, z_board]) board_mock(); }
  color([0.45, 0.48, 0.52]) translate([0, 0, z_part]) bezel();
  if (with_mocks) buttons_in_place();
}

if (PART == "shell")   shell();
if (PART == "bezel")   bezel();
if (PART == "button")  button_pin();
if (PART == "closed")  closed_assembly();
if (PART == "cutaway")
  difference() {
    closed_assembly();
    translate([0, -60, -1]) cube([70, 120, 40]);    // keep -X half: section
  }                                                 // passes through USB + bays
if (PART == "assembly") {
  color([0.23, 0.25, 0.28]) shell();
  battery_mock();
  translate([0, 0, z_board + 7])  board_mock();
  color([0.45, 0.48, 0.52]) translate([0, 0, z_part + 16]) translate([0, 0, z_part]) bezel();
  for (i = [0, 1])
    color([0.9, 0.45, 0.1]) translate([cav_half + wall + 5, btn_y[i], btn_z])
      rotate([0, -90, 0]) button_pin();
}
