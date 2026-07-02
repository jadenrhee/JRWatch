#!/usr/bin/env python3
"""Close the documented open links, one verified batch per invocation.
Every coordinate here was checked against a full survey of local copper
(survey.py / zoneprobe.py) with 0.13 mm clearance and 0.5 mm hole-to-hole
margins computed by hand. Usage: close_links.py <batch>
"""
import sys
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"
NM = pcbnew.FromMM

def add_track(b, net, layer, pts, w):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(NM(x1), NM(y1)))
        t.SetEnd(pcbnew.VECTOR2I(NM(x2), NM(y2)))
        t.SetWidth(NM(w))
        t.SetLayer(layer)
        t.SetNet(net)
        b.Add(t)

def add_via(b, net, x, y, pad=0.4, drill=0.2):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(NM(x), NM(y)))
    v.SetDrill(NM(drill))
    v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, NM(pad))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    b.Add(v)

def batch1(b, nets):
    F, B, In1 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu
    vsys, vbat = nets["VSYS"], nets["VBAT"]

    # VSYS pin 4 (PVDD): stub east in the 0.6 mm lane between the locked
    # buck switch-node tracks, via past the PMIC_INT F diagonal, In1 lead-in
    # west into the VSYS pour (fill verified present at (94.0,103.82)).
    add_track(b, vsys, B, [(93.85, 103.95), (96.05, 103.95), (96.15, 104.05)], 0.25)
    add_via(b, vsys, 96.15, 104.05)
    add_track(b, vsys, In1, [(96.15, 104.05), (94.0, 103.82)], 0.35)

    # VBAT pin 19: west stub, via in the only clearance-positive spot of the
    # pocket (0.164 to the VBUS_USB F diagonal, 0.773 to the 0.3 mm via),
    # then In1 lane y=104.75 between the VBUS via ring and the VSYS corridor
    # into the VBAT pour (fill verified at (87.1,104.75)).
    add_track(b, vbat, B, [(88.55, 104.95), (88.15, 104.95), (87.8, 104.68), (87.8, 104.65)], 0.25)
    add_via(b, vbat, 87.8, 104.65)
    add_track(b, vbat, In1, [(87.8, 104.65), (87.8, 104.75), (87.1, 104.75)], 0.35)

    # VSYS pin 20: via seated in the pad itself (no room beside the pad row),
    # short In1 link to the existing VSYS corridor end at (88.85,105.269).
    add_via(b, vsys, 88.8, 104.45)
    add_track(b, vsys, In1, [(88.8, 104.45), (88.85, 105.269)], 0.3)

def _key(t):
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        return ("V", round(p.x / 1000), round(p.y / 1000))
    s, e = t.GetStart(), t.GetEnd()
    a = (round(s.x / 1000), round(s.y / 1000))
    c = (round(e.x / 1000), round(e.y / 1000))
    return ("T", t.GetLayer()) + tuple(sorted((a, c)))

def batch2(b, nets):
    """Pocket reshuffle: NTC re-routed out of the SW slot, VBAT via moved
    south onto the pour edge, VSYS pin20 gets a via-less B path to the
    existing VSYS via, pin4 via resized/relocated, In1 lane under the EP
    joins the VSYS corridor cluster to the pour. Removes batch-1 mistakes."""
    F, B, In1 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu
    vsys, vbat, ntc = nets["VSYS"], nets["VBAT"], nets["NTC"]

    def T(l, x1, y1, x2, y2):
        a = (round(NM(x1) / 1000), round(NM(y1) / 1000))
        c = (round(NM(x2) / 1000), round(NM(y2) / 1000))
        return ("T", l) + tuple(sorted((a, c)))

    def V(x, y):
        return ("V", round(NM(x) / 1000), round(NM(y) / 1000))

    doomed = {
        # old NTC SW diagonal + vertical
        T(B, 88.212, 105.45, 87.001, 106.661), T(B, 87.001, 106.661, 87.001, 108.359),
        T(B, 87.001, 108.359, 86.802, 108.558),
        # batch-1 VBAT attempt (wrong spot)
        T(B, 88.55, 104.95, 88.15, 104.95), T(B, 88.15, 104.95, 87.8, 104.68),
        T(B, 87.8, 104.68, 87.8, 104.65), V(87.8, 104.65),
        T(In1, 87.8, 104.65, 87.8, 104.75), T(In1, 87.8, 104.75, 87.1, 104.75),
        # batch-1 in-pad via (F-pad shorted VDD_DISP / I2C_SDA walls)
        V(88.8, 104.45), T(In1, 88.8, 104.45, 88.85, 105.269),
        # batch-1 pin4 via at 0.40 dia, relocating
        V(96.15, 104.05), T(In1, 96.15, 104.05, 94.0, 103.82),
        T(B, 96.05, 103.95, 96.15, 104.05),
    }
    tracks = list(b.GetTracks())
    to_remove = [t for t in tracks if _key(t) in doomed]
    assert len(to_remove) == len(doomed), \
        f"expected {len(doomed)} removals, matched {len(to_remove)}"

    # shrink the VBUS_USB cluster via so the new NTC vertical clears it
    for t in tracks:
        if t.GetClass() == "PCB_VIA" and _key(t) == V(87.752, 107.183):
            t.SetDrill(NM(0.2))
            t.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, NM(0.45))

    # --- adds ---
    # NTC re-route: hugs the pad row then steps around the shrunk via
    add_track(b, ntc, B, [(88.212, 105.45), (87.93, 105.73), (87.93, 106.55),
                          (88.24, 106.86), (88.24, 108.1), (86.9, 108.56),
                          (86.802, 108.558)], 0.15)
    # VBAT pin19: stub, slot descent, via at the pour edge, In1 lead-in
    add_track(b, vbat, B, [(88.55, 104.95), (87.9, 104.95)], 0.25)
    add_track(b, vbat, B, [(87.9, 104.95), (87.64, 105.3), (87.64, 106.1),
                           (87.4, 106.35), (87.2, 106.35)], 0.15)
    add_via(b, vbat, 87.2, 106.35, pad=0.45)
    add_track(b, vbat, In1, [(87.2, 106.35), (86.9, 106.35)], 0.35)
    # VSYS pin20: B-only path onto the existing VSYS via pad
    add_track(b, vsys, B, [(88.55, 104.45), (87.7, 104.45), (87.45, 104.9),
                           (87.076, 105.586)], 0.25)
    # VSYS pin4 via relocated at 0.45 dia + In1 lead-in to the pour
    add_track(b, vsys, B, [(96.05, 103.95), (96.11, 104.03)], 0.25)
    add_via(b, vsys, 96.11, 104.03, pad=0.45)
    add_track(b, vsys, In1, [(96.11, 104.03), (94.0, 103.82)], 0.35)
    # In1 lane under the EP: pour cluster <-> corridor cluster
    add_track(b, vsys, In1, [(94.0, 103.82), (93.6, 104.925), (89.2, 104.925),
                             (88.85, 105.269)], 0.35)

    for t in to_remove:
        b.Remove(t)

BATCHES = {"1": batch1, "2": batch2}

def main():
    b = pcbnew.LoadBoard(BOARD)
    nets = b.GetNetsByName()
    BATCHES[sys.argv[1]](b, {k: nets[k] for k in ("VSYS", "VBAT", "3V0", "SHPHLD",
                                                  "CC2", "DISP_SCK", "GND", "NTC")})
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print("batch", sys.argv[1], "applied + zones refilled")

if __name__ == "__main__":
    main()
