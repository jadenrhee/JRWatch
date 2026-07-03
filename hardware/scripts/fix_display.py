#!/usr/bin/env python3
"""Display-connector correction (see decision log D-025):
- J2 moves to the tail-centered position (Sharp fig 8-1: tail center = panel
  center); pads land at y=112.8 in the strip south of the glass.
- J2 pad nets are mirrored (pad k mates panel terminal 11-k after the fold).
- The old west-side display fan and the south-quadrant signal nets are ripped
  for re-routing; the USB_DP tail (via + last two segments) is deleted so the
  router can re-place the via out of the pin-12 column.
"""
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"
NM = pcbnew.FromMM
mm = lambda v: v / 1e6

b = pcbnew.LoadBoard(BOARD)
nets = b.GetNetsByName()

# --- 1. move J2 -----------------------------------------------------------
j2 = b.FindFootprintByReference("J2")
j2.SetPosition(pcbnew.VECTOR2I(NM(100.0), NM(114.65)))
p1 = [p for p in j2.Pads() if p.GetNumber() == "1"][0]
print(f"J2 moved: pad1 now at ({mm(p1.GetPosition().x):.2f},{mm(p1.GetPosition().y):.2f})")

# --- 2. mirror the pad nets ----------------------------------------------
new_nets = {"1": "GND", "2": "GND", "3": "VDD_DISP", "4": "VDD_DISP",
            "5": "VDD_DISP", "6": "DISP_ON", "7": "EXTCOMIN",
            "8": "DISP_CS", "9": "DISP_MOSI", "10": "DISP_SCK",
            "MP": "GND"}
for p in j2.Pads():
    p.SetNet(nets[new_nets[p.GetNumber()]])
print("J2 pads renetted (mirrored)")

# --- 3. rip for re-route ---------------------------------------------------
RIP_ALL = {"DISP_MOSI", "DISP_CS", "DISP_ON", "EXTCOMIN", "DISP_SCK",
           "I2C_SDA", "I2C_SCL", "CC1", "CC2", "SHPHLD", "PMIC_INT",
           "N$2", "N$4", "BTN2", "BTN2_PAD", "BTN1_PAD"}
tracks = list(b.GetTracks())
doomed = [t for t in tracks if t.GetNetname() in RIP_ALL and not t.IsLocked()]

# VDD_DISP: rip everything except the pin-29 pocket escape (y <= 101.9)
for t in tracks:
    if t.GetNetname() != "VDD_DISP":
        continue
    if t.GetClass() == "PCB_VIA":
        ymax = mm(t.GetPosition().y)
    else:
        ymax = max(mm(t.GetStart().y), mm(t.GetEnd().y))
    if ymax > 101.9:
        doomed.append(t)

# USB_DP tail: via at (91.25,107.5), B vert into U4.4, F diag to (91.9,106.85)
def near(v, x, y):
    return abs(mm(v.x) - x) < 0.05 and abs(mm(v.y) - y) < 0.05
for t in tracks:
    if t.GetNetname() != "USB_DP":
        continue
    if t.GetClass() == "PCB_VIA" and near(t.GetPosition(), 91.25, 107.5):
        doomed.append(t)
    elif t.GetClass() != "PCB_VIA":
        s, e = t.GetStart(), t.GetEnd()
        if (near(s, 91.25, 107.5) or near(e, 91.25, 107.5)) or \
           (min(mm(s.y), mm(e.y)) >= 107.4 and max(mm(s.x), mm(e.x)) <= 91.35):
            doomed.append(t)

doomed = list({id(t): t for t in doomed}.values())
for t in doomed:
    b.Remove(t)
print(f"ripped {len(doomed)} items")

pcbnew.SaveBoard(BOARD, b)
print("saved")
