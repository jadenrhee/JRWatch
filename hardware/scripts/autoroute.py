#!/usr/bin/env python3
"""
Stage 3: autoroute the remaining low-speed nets with Freerouting.

  export DSN (planes + locked critical wiring included)
  -> java -jar freerouting -de ... -do ...
  -> import SES back into the board

Freerouting output is treated as a DRAFT (it over-vias on dense boards); the
finish stage adds the ground lattice, fills zones, and DRC gates everything.
"""
import os
import subprocess
import sys

import pcbnew

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')
DSN = os.path.join(HW, 'jrwatch.dsn')
SES = os.path.join(HW, 'jrwatch.ses')
JAR = os.path.join(HW, '..', 'tools', 'freerouting-1.5.0.jar')

STAGE = sys.argv[1] if len(sys.argv) > 1 else 'all'

if STAGE in ('export', 'all'):
    b = pcbnew.LoadBoard(BOARD_PATH)
    ok = pcbnew.ExportSpecctraDSN(b, DSN)
    # KiCad 10 exports locked tracks/vias with (type fix) natively — verified;
    # Freerouting honors them as fixed wiring.
    with open(DSN) as f:
        nfix = f.read().count('(type fix)')
    print(f'DSN export: {ok} {DSN} ({nfix} fixed items)')

if STAGE in ('route', 'all'):
    cmd = ['java', '-jar', JAR, '-de', DSN, '-do', SES, '-mp', '100',
           '-us', 'global', '-dct', '1']
    print('running:', ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print(r.stdout[-3000:])
    print(r.stderr[-2000:])
    print('ses exists:', os.path.exists(SES))

if STAGE in ('import', 'all'):
    b = pcbnew.LoadBoard(BOARD_PATH)
    ok = pcbnew.ImportSpecctraSES(b, SES)
    print('SES import:', ok)
    # remove any orphaned no-net copper the import may leave behind
    orphans = [t for t in b.GetTracks() if t.GetNetCode() <= 0]
    for t in orphans:
        b.Remove(t)
    print(f'removed {len(orphans)} no-net orphan tracks/vias')
    pcbnew.SaveBoard(BOARD_PATH, b)
    print('saved')
