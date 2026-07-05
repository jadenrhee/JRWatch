# Enclosure

Two-piece 3D-printable watch case, written as parametric OpenSCAD
(`jrwatch_case.scad`), same code-first approach as the rest of the project.
Every cutout is measured from the actual board file: the USB-C slot, the two
side-button bores, and the display aperture. The board has no mounting
holes, so the case clamps it at the four corner arcs, which I verified are
component-free on both sides.

| Exploded | Assembled |
|---|---|
| ![exploded](enclosure-preview.png) | ![closed](enclosure-closed.png) |
| **Section through the USB slot** | **Case back** |
| ![cutaway](enclosure-cutaway.png) | ![back](enclosure-back.png) |

Design details: tapered, edge-filleted body; curved lug horns drilled for
22 mm spring bars; raised pusher-guard pods with knurled sliding pushers
(retained by an internal flange in a stepped bore); crowned bezel with a
chamfered aperture, engraved 12-o'clock index and wordmark; engraved case
back; alignment nubs between the halves; recessed USB-C port with a plug
chamfer.

## Printed parts (`stl/`)

| File | Qty | What it is |
|---|---|---|
| `case-shell.stl` | 1 | Bottom shell: battery bay, component headroom, USB port, pusher pods, lug horns, engraved back |
| `case-bezel.stl` | 1 | Top ring: display pocket, FPC relief, chamfered aperture, index + wordmark |
| `case-button.stl` | 2 | Knurled sliding pushers (drop into the east-wall bores from the inside) |

Overall 41.4 × 41.4 × 13.6 mm plus lugs. Fits a 22 mm spring-bar strap.

No metal-plated or metal-filled materials: the BLE antenna sits at the north
edge and the case must stay RF-transparent there.

## Other hardware

| Item | Spec | Note |
|---|---|---|
| Screws ×4 | M2 × 12 mm self-tapping, pan head | enter from the back, bite into the bezel |
| Spring bars ×2 | 22 mm, Ø1.3-1.5 tips | standard watch part |
| Strap | any 22 mm | |
| Display adhesive | 0.3 mm double-sided tape (3M 9448A or VHB) | frame the glass edges, keep the active area clear |
| Battery pad | 1-2 mm foam tape in the battery bay | |


## Regenerating

```
openscad -D 'PART="shell"'  -o stl/case-shell.stl  jrwatch_case.scad
openscad -D 'PART="bezel"'  -o stl/case-bezel.stl  jrwatch_case.scad
openscad -D 'PART="button"' -o stl/case-button.stl jrwatch_case.scad
```

All key dimensions (stack heights, clearances, lug size) are parameters at
the top of the file.
