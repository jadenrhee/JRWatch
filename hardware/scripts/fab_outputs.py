#!/usr/bin/env python3
"""
BOM (JLCPCB CSV) + CPL (pick-and-place) from the live board and netlist JSON.

BOM: Comment,Designator,Footprint,LCSC  - grouped by (value, footprint, LCSC),
DNP/hand-place lines flagged in Comment. CPL: Designator,Val,Package,
Mid X,Mid Y,Rotation,Layer (JLC convention; rotations may need the usual
per-part tweak in JLC's viewer - noted in fab/README).
"""
import csv
import json
import os

import pcbnew
from pcbnew import ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.abspath(os.path.join(HW, '..'))
FAB = os.path.join(ROOT, 'fab')

nl = json.load(open(os.path.join(HW, 'netlist', 'jrwatch-netlist.json')))
parts = {p['ref']: p for p in nl['parts']}

b = pcbnew.LoadBoard(os.path.join(HW, 'jrwatch.kicad_pcb'))

# ------------------------------------------------------------------- BOM
groups = {}
for ref, p in parts.items():
    f = p.get('fields', {})
    lcsc = f.get('LCSC', '')
    if ref == 'J4':                      # Tag-Connect: footprint only
        continue
    key = (p['value'], p['footprint'].split(':', 1)[-1], lcsc)
    groups.setdefault(key, []).append(ref)

bom_path = os.path.join(FAB, 'bom-jlcpcb.csv')
with open(bom_path, 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC'])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        srcs = {parts[r].get('fields', {}).get('Sourcing', '') for r in refs}
        note = val
        if 'hand/DigiKey' in srcs:
            note += ' [HAND-PLACE: DigiKey, LCSC OOS at design time]'
        elif 'hand' in srcs:
            note += ' [HAND-PLACE]'
        w.writerow([note, ','.join(sorted(refs)), fp, lcsc])
print('wrote', bom_path)

# ------------------------------------------------------------------- CPL
cpl_path = os.path.join(FAB, 'cpl-jlcpcb.csv')
with open(cpl_path, 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['Designator', 'Val', 'Package', 'Mid X', 'Mid Y',
                'Rotation', 'Layer'])
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        if ref == 'J4':
            continue
        pos = fp.GetPosition()
        w.writerow([ref, fp.GetValue(),
                    parts.get(ref, {}).get('footprint', ':').split(':', 1)[-1],
                    f'{ToMM(pos.x):.4f}', f'{-ToMM(pos.y):.4f}',   # y-up for JLC
                    f'{fp.GetOrientationDegrees():.1f}',
                    'Bottom' if fp.IsFlipped() else 'Top'])
print('wrote', cpl_path)
