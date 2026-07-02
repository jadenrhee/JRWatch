// JRWatch enclosure — two-piece 3D-printable watch case
// ------------------------------------------------------
// Dimensions are taken from the actual board (hardware/jrwatch.kicad_pcb):
//   * board 36 x 36 mm, corner radius 6, thickness 0.8
//   * USB-C on the BOTTOM side, mouth at the south edge, x = 95..105 (board coords)
//   * side buttons SW1/SW2 on the east edge at y = 95 / 106 (board coords)
//   * display LS013B7DH03 on top: 26.6 x 30.3 x 0.74, active 23.04 sq,
//     FPC folds under its south edge into J2
//   * all other components on the bottom, tallest = USB-C shell (3.26)
// Case coordinates: origin at board center, +Y = board north, z=0 case bottom.
//
// Set PART before rendering:
//   "shell"    - bottom case (print 1x)
//   "bezel"    - top ring    (print 1x)
//   "button"   - side button pin (print 2x)
//   "assembly" - exploded preview, not for printing

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

/* ---------- screws (M2 x 12 self-tapping, from the bottom) ---------- */
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
btn_hole  = 3.2;                  // button pin bore
btn_y     = [ 5, -6 ];            // SW1 (board y=95), SW2 (board y=106)
btn_z     = z_board - 1.6;        // actuator center below the board

/* ---------- strap lugs (22 mm spring-bar strap) ---------- */
lug_gap   = 22.2;                 // between inner prong faces
lug_wide  = 3.0;                  // prong thickness (x)
lug_len   = 5.6;                  // protrusion from wall (y)
lug_h     = 8.5;
bar_hole  = 1.35;                 // spring-bar pin
bar_off   = 3.4;                  // hole center beyond the wall
bar_z     = 4.6;

$fn = 64;
eps = 0.01;

/* ================= helpers ================= */

module rsquare(half, r) {          // rounded square centered on origin
  offset(r = r) square(2*(half - r), center = true);
}

module cavity2d()  rsquare(cav_half, board_r + clr);
module outer2d()   rsquare(out_half, out_r);

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

// annular wedge that reaches under (or over) the board's corner arc — the
// board is clamped only here; corner zones are component-free on both sides
module corner_pads(h) {
  for (sx = [-1, 1], sy = [-1, 1])
    scale([sx, sy, 1])
      linear_extrude(h) intersection() {
        translate([12, 12]) difference() {
          circle(5.9);
          circle(4.6);
        }
        translate([12, 12]) rotate(45)
          polygon([[0,0], [10, 4.6], [10, -4.6]]);  // ~50 deg outward wedge
      }
}

module lugs() {
  for (sy = [-1, 1], sx = [-1, 1])
    scale([sx, sy, 1])
      translate([lug_gap/2 + lug_wide/2, out_half + lug_len/2 - eps, 0])
        difference() {
          intersection() {          // prong, top edge rounded
            translate([0, 0, lug_h/2]) cube([lug_wide, lug_len, lug_h], center=true);
            translate([0, -lug_len/2, 0]) scale([1, (lug_len + 2)/lug_h, 1])
              rotate([0, 90, 0]) cylinder(h = lug_wide, r = lug_h, center = true);
          }
          translate([0, out_half + bar_off - (out_half + lug_len/2 - eps), bar_z])
            rotate([0, 90, 0]) cylinder(h = lug_wide + 1, d = bar_hole, center = true);
        }
}

/* ================= bottom shell ================= */

module shell() {
  difference() {
    union() {
      // body
      linear_extrude(z_part) outer2d();
      lugs();
    }
    // main cavity
    translate([0, 0, floor_t]) linear_extrude(z_part) cavity2d();
    // screw shank + head pocket
    for (sx = [-1, 1], sy = [-1, 1]) {
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = z_part, d = shank_dia);
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = head_h + eps, d = head_dia);
    }
    // USB-C slot, south wall, with a plug-friendly outside chamfer
    translate([0, -out_half, (usb_zlo + usb_zhi)/2]) {
      cube([usb_w, 2*wall + 2, usb_zhi - usb_zlo], center = true);
      translate([0, -wall + 0.6, 0])
        cube([usb_w + 1.6, wall, usb_zhi - usb_zlo + 1.6], center = true);
    }
    // button bores + inner counterbores for the pin flanges, east wall
    for (y = btn_y) translate([cav_half - eps, y, btn_z]) rotate([0, 90, 0]) {
      cylinder(h = wall + 2, d = btn_hole);
      translate([0, 0, -1.2]) cylinder(h = 1.2 + eps, d = 4.9);
    }
  }
  // rebuild the posts (the cavity cut removed them), minus screw bores
  difference() {
    corner_posts(z_board);
    for (sx = [-1, 1], sy = [-1, 1])
      translate([sx*screw_d, sy*screw_d, -eps]) cylinder(h = z_board + 1, d = shank_dia);
  }
  // board rests on these
  translate([0, 0, z_board - 1.0]) corner_pads(1.0);
  // battery fence (502030 pouch + pad drops in here)
  translate([-1, 0, floor_t]) linear_extrude(0.8) difference() {
    rsquare(31.2/2 + 0.8, 2);
    rsquare(31.2/2, 1.6);
  }
}

/* ================= top bezel ================= */

module bezel() {
  translate([0, 0, -z_part]) union() {   // modeled in place, shifted for printing
    difference() {
      translate([0, 0, z_part]) linear_extrude(bezel_h) outer2d();
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
          translate([0, 0, bezel_h]) linear_extrude(eps) square(ap_size + 1.8, center=true);
        }
      }
      // screw pilots
      for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*screw_d, sy*screw_d, z_part - eps])
          cylinder(h = bezel_h - 0.4, d = pilot_dia);
    }
    // presses the board down onto the shell pads
    difference() {
      translate([0, 0, z_part - 0.05]) corner_pads(0.5);
      translate([0, disp_cy, z_part - 1]) linear_extrude(3)
        square([disp_w + 0.6, disp_h + 0.6], center = true);  // never touch the glass
    }
  }
}

/* ================= button pin (print 2) ================= */

module button_pin() {
  cylinder(h = 1.0, d = 4.5);            // flange (inside the wall)
  translate([0, 0, 1.0 - eps]) cylinder(h = 3.2, d = 2.9);
}

/* ================= preview ================= */

module board_mock() {
  color("SeaGreen") linear_extrude(board_t) rsquare(board_w/2, board_r);
  color("DimGray") translate([0, disp_cy, board_t + disp_tape])
    linear_extrude(disp_t) square([disp_w, disp_h], center = true);
}

if (PART == "shell")     shell();
if (PART == "bezel")     bezel();
if (PART == "button")    button_pin();
if (PART == "assembly") {
  shell();
  translate([0, 0, z_board + 6])  board_mock();
  color("SlateGray", 0.85) translate([0, 0, z_part + 14]) translate([0, 0, z_part]) bezel();
  for (y = btn_y)
    color("Orange") translate([cav_half + wall + 4, y, btn_z])
      rotate([0, -90, 0]) button_pin();
}
