# D-025: what is left, and why the routers cannot do it

Working notes for the interactive session that finishes the display
connector rework. Branch `d025-rework`. Board state at the time of
writing: 8 unconnected, 18 DRC errors.

Two engines were run to exhaustion against this: Freerouting 1.5.0
(global, 200 passes, twice, once with only the critical nets fixed and
once with the whole board fixed) and the repo's A* completer at three
clearances (0.225, 0.235, 0.335). Both report no path on the same set.
The reasons below are geometric, not a matter of trying harder.

## Still open

| Connection | Why it is blocked |
|---|---|
| 3V0, U2 pin 12 | see corridor note below |
| SHPHLD, U2 pin 15 -> R7.1 | same pin row, same corridor |
| CC2, U2 pin 24 -> J1.B5 | west pin column, no escape south |
| DISP_SCK, J2.10 -> U1.41 | south quadrant congestion |
| DISP_CS, remainder -> U1.39 | south quadrant congestion |
| GND zones, 3 links | one F.Cu island (C9.2, ~3.1 mm2) has no via_ok spot |

## The pin-escape problem

U2 is a QFN-32 on 0.5 mm pitch. Pad-to-pad gap is about 0.22 mm. A
0.15 mm track needs 0.15 + 2 x 0.13 = 0.41 mm to pass between two pads,
so **nothing can be routed between adjacent pins**. Every one of these
nets has to leave the pin row outward and then turn, which is why an
autorouter with a uniform clearance model gives up: it never finds a
legal first move.

## The 3V0 corridor, measured

Pin 12 sits at (91.25, 106.65). Its target is the In1 3V0 pour, and the
pour is not overhead: probing the filled polygons along y = 106.2-107.0
gives VSYS from x = 92 to 94, **bare copper from x = 95 to 99**, and 3V0
only from x = 100 east. A via dropped straight down from pin 12 lands on
the VSYS island and shorts. The tap has to reach x >= 100 first.

The only lane east runs between two hard edges:

- QFN south pad row, bottom edge ~ y = 106.775
- USB_DP / USB_DM tail vias at y = 107.50, pad edge ~ y = 107.20

That is a 0.425 mm lane. A 0.15 mm track centred at y = 106.99 leaves
0.14 mm to the pads and 0.135 mm to the vias, against a 0.13 mm rule.
It fits, with about 5 microns of margin either side. That is a live-DRC
job in the interactive router, not something to place open-loop.

**The alternative worth trying first:** move the USB_DP and USB_DM tail
vias south by ~0.3 mm. `fix_display.py` already anticipated this
("the USB_DP tail (via + last two segments) is deleted so the router can
re-place the via out of the pin-12 column"). Doing so widens the lane to
a comfortable 0.7 mm and very likely unblocks SHPHLD on pin 15 as well,
since it shares the corridor. Ripping those tails without re-placing
them is not enough on its own; that was tried and the pair was left
open.

## Things that are already correct

Do not re-derive these.

- J2 at (100, 107.75), pad k carrying panel terminal 11-k.
- J2 MP tabs re-cut to y 107.00-108.58. The stock footprint's tabs run
  to y = 110.25 and collide with J1's pad field at y = 108.83; both are
  GND so DRC never says a word about it.
- The GND stitch via that fell under the new pad row is gone.
- DISP_ON, EXTCOMIN, VDD_DISP, DISP_MOSI and part of DISP_CS are routed.

## Known non-routing DRC items

- 8 x hole_clearance inside SW1/SW2. This is the Alps SKRTLAE010's own
  pad-to-NPTH geometry in KiCad's stock footprint, and the part matches
  the BOM (C110293). Needs a scoped rule exception, not a fix.
- 4 x courtyard overlap between J2 and J1. Both are hand-soldered.
