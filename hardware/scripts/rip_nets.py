#!/usr/bin/env python3
"""Rip all unlocked tracks/vias of the named nets so Freerouting can re-route
them together with the still-open links in freed corridors. Locked (hand-routed)
copper is never touched."""
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"

RIP = {
    "DISP_MOSI", "DISP_CS", "DISP_ON", "EXTCOMIN",
    "I2C_SDA", "I2C_SCL", "N$2", "N$4",
    "CC1", "BTN2", "BTN2_PAD", "BTN1_PAD", "PMIC_INT",
}

b = pcbnew.LoadBoard(BOARD)
doomed = [t for t in list(b.GetTracks())
          if t.GetNetname() in RIP and not t.IsLocked()]
for t in doomed:
    b.Remove(t)
pcbnew.SaveBoard(BOARD, b)
print(f"ripped {len(doomed)} items across {len(RIP)} nets")
