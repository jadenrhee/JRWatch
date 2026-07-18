#!/usr/bin/env python3
"""
Generate JRWatch.pretty custom footprints.

Only one custom footprint is needed - the Murata DFE201612E 2016-metric power
inductor. Murata's official land pattern was not retrievable programmatically,
so the land is derived per IPC-7351B nominal density from the body drawing
(L 2.0 +/-0.2, W 1.6 +/-0.2, bottom terminals ~0.5 mm):

    pads 0.95 x 1.70 mm at x = +/-0.85  (toe ~0.35, generous heel, gap 0.75)

Cross-check against the Murata land pattern before ordering assembly, since
this was derived per IPC-7351B rather than taken from Murata's own published
pattern, which was not retrievable. Oversize is safe here - the
part has no fine-pitch neighbors and both nets are power.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'footprints', 'JRWatch.pretty')
os.makedirs(OUT, exist_ok=True)

INDUCTOR = """(footprint "L_Murata_DFE201612E_2016"
  (version 20221018)
  (generator jrwatch_gen_footprints)
  (layer "F.Cu")
  (descr "Murata DFE201612E molded power inductor 2.0x1.6x1.2mm (0806/2016). Land derived per IPC-7351B nominal; see gen_footprints.py")
  (tags "inductor power 2016 0806 DFE201612E")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.7) (layer "F.SilkS")
    (effects (font (size 0.7 0.7) (thickness 0.11))))
  (fp_text value "L_Murata_DFE201612E_2016" (at 0 1.8) (layer "F.Fab")
    (effects (font (size 0.5 0.5) (thickness 0.08))))
  (fp_line (start -1.0 -0.8) (end 1.0 -0.8) (layer "F.Fab") (stroke (width 0.1) (type solid)))
  (fp_line (start -1.0 0.8) (end 1.0 0.8) (layer "F.Fab") (stroke (width 0.1) (type solid)))
  (fp_line (start -1.0 -0.8) (end -1.0 0.8) (layer "F.Fab") (stroke (width 0.1) (type solid)))
  (fp_line (start 1.0 -0.8) (end 1.0 0.8) (layer "F.Fab") (stroke (width 0.1) (type solid)))
  (fp_line (start -0.35 -1.0) (end 0.35 -1.0) (layer "F.SilkS") (stroke (width 0.12) (type solid)))
  (fp_line (start -0.35 1.0) (end 0.35 1.0) (layer "F.SilkS") (stroke (width 0.12) (type solid)))
  (fp_rect (start -1.58 -1.1) (end 1.58 1.1) (layer "F.CrtYd") (stroke (width 0.05) (type solid)) (fill none))
  (pad "1" smd roundrect (at -0.85 0) (size 0.95 1.7) (layers "F.Cu" "F.Paste" "F.Mask")
    (roundrect_rratio 0.15))
  (pad "2" smd roundrect (at 0.85 0) (size 0.95 1.7) (layers "F.Cu" "F.Paste" "F.Mask")
    (roundrect_rratio 0.15))
)
"""

with open(os.path.join(OUT, 'L_Murata_DFE201612E_2016.kicad_mod'), 'w') as f:
    f.write(INDUCTOR)
print('wrote', OUT)
