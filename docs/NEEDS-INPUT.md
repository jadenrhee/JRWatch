# NEEDS INPUT - items only you can resolve

Only items that are (a) irreversible **and** costly, or (b) require physical
measurement/equipment. Everything else was decided autonomously and logged in
`decision-log.md`. Nothing here blocks the design work - each item lists what was
assumed so the design could proceed.

| # | Item | What's needed from you | Assumption used meanwhile |
|---|---|---|---|
| 1 | JLCPCB fab + assembly order | Committing money to the fab order (review `docs/human-review-checklist.md` first) | - |
| 2 | Battery physical fit | Confirm the enclosure/strap concept and the LiPo's real dimensions before ordering cells | 150 mAh 502030-class pouch (30 × 20 × 5 mm) with built-in PCM, JST-SH pigtail |
| 3 | Measured sleep current | PPK2 / µCurrent measurement at bring-up to replace the *projected* numbers in README + verification report | Projections from datasheet typicals, itemized in `verification-report.md` |
| 4 | Enclosure | Test-fit one printed shell (bare board + USB cable) before ordering the set in final material | Printable two-piece case in `hardware/enclosure/`: 41.4 mm face, 13.6 mm stack incl. 5.4 mm battery bay, 22 mm strap lugs; display-aperture offset flagged for a check against the panel outline drawing |
