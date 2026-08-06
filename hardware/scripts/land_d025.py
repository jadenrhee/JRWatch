#!/usr/bin/env python3
"""
D-025 landing: move the display FPC connector to the position the panel's
tail can actually reach, and correct the pin order for the fold.

Sharp's tail exits the centre of the panel and folds 180 degrees back
underneath, so the connector has to sit inside the ~9 mm window the folded
tail reaches (D-025 derives x = 95.3-104.7) and the fold inverts the contact
face, which reverses the order the connector sees. J2 therefore moves to
(100, 107.75) and pad k takes panel terminal 11-k.

The five display signal nets are ripped here; complete_routes.py re-routes
them to the new pad row. VDD_DISP and GND keep their existing copper (the
cap bank and the pours), and only need the new pads tied in.

Run under KiCad's bundled python:
  /Applications/KiCad/KiCad.app/Contents/MacOS/../Frameworks/Python.framework/\
Versions/3.9/bin/python3 land_d025.py
"""
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')

J2_POS = (100.0, 107.75)

# pad -> net, per hardware/netlist/jrwatch-netlist.json (post-fold order)
PAD_NETS = {
    '1': 'GND',      '2': 'GND',
    '3': 'VDD_DISP', '4': 'VDD_DISP', '5': 'VDD_DISP',
    '6': 'DISP_ON',  '7': 'EXTCOMIN', '8': 'DISP_CS',
    '9': 'DISP_MOSI', '10': 'DISP_SCK',
}

# ripped wholesale: every one of these ran to the old west-side pad row
RIP_NETS = ('DISP_SCK', 'DISP_MOSI', 'DISP_CS', 'EXTCOMIN', 'DISP_ON')


def main():
    b = pcbnew.LoadBoard(BOARD_PATH)
    nets = b.GetNetsByName()

    j2 = b.FindFootprintByReference('J2')
    if j2 is None:
        sys.exit('J2 not found')
    old = (ToMM(j2.GetPosition().x), ToMM(j2.GetPosition().y))
    j2.SetPosition(VECTOR2I(FromMM(J2_POS[0]), FromMM(J2_POS[1])))
    print(f'J2 {old} -> {J2_POS}')

    for p in j2.Pads():
        num = p.GetNumber()
        want = 'GND' if num == 'MP' else PAD_NETS.get(num)
        if want is None:
            continue
        if p.GetNetname() != want:
            p.SetNet(nets[want])
    print('pad nets set to the folded order')
    for p in sorted(j2.Pads(), key=lambda q: q.GetNumber()):
        pp = p.GetPosition()
        print(f'   pad {p.GetNumber():>2s} {p.GetNetname():10s} '
              f'({ToMM(pp.x):.3f},{ToMM(pp.y):.3f})')

    removed = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() in RIP_NETS:
            b.Remove(t)
            removed += 1
    print(f'ripped {removed} track/via items on {", ".join(RIP_NETS)}')

    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(BOARD_PATH)
    print('saved', BOARD_PATH)


if __name__ == '__main__':
    main()
