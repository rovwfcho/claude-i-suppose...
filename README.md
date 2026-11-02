# Case for the Waveshare ESP32-S3-ePaper-3.97

A two-piece case with rounded edges for the Waveshare ESP32-S3 3.97" e-Paper board (SKU 33552, part number `ESP32-S3-ePaper-3.97`), with room inside for its 3.7 V 1500 mAh LiPo (Waveshare model 454261) and its speaker **side by side**. It measures 104.9 x 65.4 x 16.7 mm. It is designed for **rigid plastic**: nothing has to bend to assemble it or to press the buttons. This version is printed in **PLA**.

**Sized from your own parts.** The battery bay and the speaker pocket are made for the battery and speaker in your photos. Their sizes were read off the ruler in those photos (see [Where the numbers come from](#where-the-numbers-come-from)). The battery sits in a 62.5 x 42.5 mm bay with guides on all four sides. The speaker sits in its own pocket, sound side down over three slots. Neither can rattle, and both still go in easily.

![renders](preview/renders.png)

![explained](preview/explained.png)

## Files

| File | What it is |
|---|---|
| `stl/front_shell_battery.stl` + `stl/back_cover_battery.stl` | The two parts to print. |
| `docs/assembly_guide_en.pdf`, `docs/assembly_guide_bg.pdf` | Illustrated assembly guide in English and Bulgarian: what to buy, printing, and every step. |
| `dist/` | The zip to download: the two STL files, this README, the renders, the measurements and the assembly guides. `make_zips.py` rebuilds it. |
| `case.py` | Parametric generator. Every dimension is a named constant at the top. |
| `verify.py` | Quick fit check: collisions, insertion path, clamping, glass clearance. |
| `checks/` | The debugging rounds (see [DEBUG_LOG.md](DEBUG_LOG.md)). `checks/owner_photos/` holds crops of your photos for round 28. |
| `preview/` | Renders, cross-sections, the openings drawn onto Waveshare's photos, and `preview/owner_measurements.png`: your photos with every ruler tick, edge and landmark the measurements used. |
| `docs/guide-src/` | Everything the guides and `preview/renders.png` are built from (`docs/guide-src/build_all.sh` rebuilds them). |

## You also need

**4 × M2 screws, 5–6 mm long under the head, never longer than 7 mm** (the two bottom screws point at the battery: 8 mm or longer reaches it). Use M2 machine screws or thread-forming screws made for plastic, with a pan, cheese or button head no more than 4.0 mm across and 1.4 mm tall. Not countersunk, not washer-head. Two go in the bottom edge, one near the top-left corner and one in the right-hand end (see `preview/screw_locations.png`). They pass through the side wall and cut their own thread in the printed block behind it. Avoid 2.2 mm sheet-metal self-tappers (ST2.2): they jam in the wall hole and can split the blocks. If that's all you have, drill the wall holes out to 2.4–2.5 mm first (the pilots are already 1.8 mm).

**Double-sided PE foam mounting tape, 1.0–1.2 mm thick** (not thinner): four small pieces hold the board tight (see Assembly).

**Thin double-sided tape** (0.1–0.2 mm, the ordinary kind): one piece under the battery, and a frame of it round the speaker's membrane (see Assembly).

## Features

- **Display window:** 88.0 x 53.6 mm, placed from Waveshare's dimension drawing. The active area is 86.4 x 51.84 mm, so there is at least 0.7 mm of margin all round. The window edge has a 45° chamfer.
- **Why the left end of the frame is wider (11.1 mm vs about 6 mm elsewhere):** the display's picture area is not centred on the board. It starts 9.3 mm from the left PCB edge but ends 3.8 mm from the right one. The strip in between is inactive glass and the display's ribbon cable, so the window can't go further left without showing it (see `preview/explained.png`).
- **Board held tight, no load on the glass:** the lip sits about 0.5 mm above the screen. The PCB is pressed against pads along its top, bottom and right edges by four rings behind it (around the brass standoffs), each with a piece of foam tape stuck to both the ring and the board. The rings stop 0.6 mm short of the board, so the foam is always squeezed, even with print, layer-height and board-thickness tolerances. Because it's stuck on both sides it also holds the board sideways, so the board can't rattle. No plastic has to bend, and the left end has no pad because the glass edge is too close to the PCB edge there.
- **PWR and BOOT:** nothing covers them. The bottom wall is left out in front of both switches: an opening 22.0 mm wide, open from the front face up past the seam, with bevelled edges. A fingertip reaches the switches straight on or tilted 15° in any direction, and 30° from the front or back. Tilted 30° sideways toward an end of the opening, a fingertip stops about 3 mm short, so press those roughly straight on. The display lip stays continuous above the opening.
- **USB-C:** a 13 x 7 mm opening with 1.2 mm corner radius, so normal cable plugs seat fully.
- **microSD:** a slot with a finger scoop. The latched card sits about 4 mm inside the outer wall, so press it with a fingernail or a pen tip to eject it.
- **Dial (UP / DOWN / press):** the wheel rim is exposed through a slot with a thumb scoop. The back cover has a tab that closes the slot above the wheel.
- **Battery bay:** 62.5 x 42.5 mm and 5 mm deep, for your 61.1 x 40.7 x 4.3 mm cell. Guide bars 2 mm tall run along all four sides, so the cell can slide about 0.9 mm at most. The four corners are left open, so the wire can leave from whichever corner of the taped end yours comes out of. The tape under the cell holds it still.
- **Speaker pocket:** 11.2 x 15.3 mm, for your 14.2 x 10.2 x 4.5 mm speaker, turned lengthways. It's about 0.5 mm bigger than the speaker on every side. Four L-shaped corner brackets locate it. Their legs are short, so the middle of every side stays open for the speaker's white peg and its cable. The pocket is kept 7.9 mm from the ESP32's antenna so the speaker's magnet doesn't hurt Wi-Fi/Bluetooth range.
- **Speaker grille:** three 1.0 x 7.0 mm slots, all under the speaker's membrane (about 10 x 6 mm) and well inside its sealed face. Sound from the back of the speaker can't leak out round its edge and cancel the front. The slots are 0.8 mm apart, so the webs between them print.
- **Vents:** holes for the microphone (left side and back) and the temperature/humidity sensor (right side and back).
- **Closing the case:** 4 side screws hold the two halves firmly; they only come apart once the screws are out. Each screw's hole in the wall is set slightly toward the front, so the foam can push the cover back by at most about 0.2 mm (allowed for in the foam's squeeze), and the screw never has to cut a thread in the thin wall. Each pilot hole has a lead-in so the screw tip finds it. The pilots are 1.8 mm for PLA: forming the thread strains the thin block walls about a third less than with a 1.7 mm pilot, and each screw still holds about 70 N. The back cover's skirt only locates it, with 0.35 mm clearance. Nothing snaps or bends, so the case works in PLA or any other rigid plastic.
- **Optional extra screws:** small cone marks on the back show where to drill if you also want to screw into the board's brass standoffs. Their thread size is unknown (M2 or M2.5), and there is roughly 6 mm (an estimate) between a standoff and the back, so you'd need a spacer; a screw without one would pull the board off the front pads. The foam already holds the board, so this is rarely worth it.

## Printing

- **PLA** (this version), **0.2 mm layers or finer** (0.1–0.2 mm), 3 perimeters, 15–20 % infill. **No supports needed.** Don't use 0.3 mm layers: the slicer rounds the clamping faces too far for the foam to press the board reliably.
- **PLA softens at about 55 °C.** Keep the case out of direct sun, off sunny windowsills and out of a parked car. PLA is also more brittle than PETG: pre-cut the screw threads (Assembly, step 3) and don't over-tighten. **PETG** or **PCTG** would be tougher and take heat better, and need no other change.
- **ASA or ABS:** these shrink more as they cool (roughly 0.5–0.7 %, depending on the brand), enough to make the board too tight. Turn on your slicer's XY shrinkage compensation for that filament (PrusaSlicer and OrcaSlicer have it in the filament settings) or print in PLA/PETG. PLA and PETG (about 0.2–0.4 %) need nothing.
- **Front shell:** print display side down. The front edge uses an arc that ends in a 45° chamfer, so it prints cleanly against the bed.
- **Back cover:** the STL is already flipped. Print it outside face down.
- **Material:** about 26 g of PLA for both parts with these settings (PrusaSlicer's estimate). Its generic profile estimates about 3 hours; a fast printer takes much less.

## Assembly

1. Put the board face-down into the front shell. The dial drops into the notch on the top edge, and the PWR/BOOT switches sit in the opening in the bottom wall.
2. Hold the back cover with its inside facing you and the dial tab at the top, so the USB-C end is on your left (as in the guide's step 2 picture).
   - **Battery:** stick a piece of thin double-sided tape in its bay and press the cell in, **taped end (with the wire) toward the USB-C end** (left). If the wire comes out of the top corner of that end, turn the cell over so it comes out at the bottom corner. Plug it into **BAT**.
   - **Speaker:** it goes in its pocket next to the battery, **membrane side down** (the side with the white membrane in a black ring faces the slots), and **with its white peg pointing to the top edge**. Its cable then comes out on the side facing the battery. Stick it down with a frame of thin double-sided tape round the membrane: cut a window in the tape so the membrane stays uncovered, and the speaker seals against the cover. Plug it into **SPK**.
   - **Wires:** both run along the bottom edge of the board to the BAT and SPK connectors; the checked routes are about 38 mm and 30 mm long, with gentle bends (none tighter than 3 mm on the speaker's sleeved cable). The battery wire runs under the battery: tuck the spare length beside it. The speaker cable is much longer (about 10–11 cm). Lay the spare in one loop on the cover above the speaker, where there's room for about 8 cm, and hold it with a strip of tape. Keep it off the right-hand end, where the ESP32's antenna is, and away from the screw holes.
   - **Foam:** cut 4 pieces of the foam tape, about 1.5 × 3 mm, and stick one onto each of the 4 small curved rings in the back cover's corners. Peel the top liner off too, so the foam sticks to the board when the case is closed. The board will then come out with the back cover when you open the case; peel the foam off the board if you need to separate them. Foam tape usually tears when peeled, so use fresh pieces when you put it back together.
3. Pre-cut the threads: before closing, drive each screw about 4 mm into the hole in its block (from the side that will face the wall), then back it out. This way the screws turn easily later and you can feel when the heads seat. Then put the back cover on: seat its tab in the slot above the dial first and lower the cover straight down. Press it down until the seam closes (the foam gives a light springy resistance), hold it there and drive in the 4 screws until the heads just touch the bottom of their recesses, then stop. Tighten them top and bottom alternately. Over-tightening can strip the plastic thread or pull the cover sideways. When you reassemble, turn each screw backwards first until it drops into its old thread.

## Where the numbers come from

**Official (Waveshare outline drawing):**
- PCB 99.5 x 60 mm, corner radius 2 mm
- Active display area 86.40 x 51.84 mm

**Display window position:** from the dimension lines on the same drawing. Waveshare's photos agree within about 0.5 mm.

**Measured from your photos** (`checks/round28.py`, drawn in `preview/owner_measurements.png`). The scale comes from the ruler's tick marks, found automatically: 17–43 ticks per photo, with a straight line fitted through them. The edges were picked by eye and then refined to the strongest colour step. Expect about ±0.3 mm:
- **Battery:** 61.1 x 40.7 x 4.3 mm, including the taped end. Its wires leave that end at one corner (about 57 mm of wire). The bay leaves 0.7–0.9 mm on each side of it.
- **Speaker:** 14.2 x 10.2 x 4.5 mm. Its membrane is about 10.1 x 5.8 mm and centred to within 0.3 mm (found by a perspective transform of its frame in your top view). The white peg sticks out about 1.6 mm from one short side, 1 mm off its middle. The cable leaves a long side about 2.9 mm from the peg's end and is about 10–11 cm long. The pocket leaves about 0.5 mm on each side.
- **Your board:** the four standoff tops in your back photo were used as reference points. The USB-C, both buttons, the dial and the top edge land within 0.5 mm of the board model, so your board is the same revision the case was built for.

**Measured from Waveshare's 1600 x 1200 product photos** (about 10 px/mm, board outline as the scale). Expect about ±0.5 mm error:
- Standoff positions
- USB-C at mid-height of the left edge
- microSD at y ≈ 14 mm
- Dial centre x ≈ 79 mm; it sticks out 2.0 mm (drawing) to 2.6 mm (photos) past the top edge. The thumb scoop was checked for both
- BOOT at x ≈ 74 mm and PWR at x ≈ 84 mm, sticking out about 0.75 mm
- Mic and sensor positions

**Assumed or estimated** (not published by Waveshare):
- PCB thickness 1.6 mm. If you have calipers, measure it and set `PCB_T`: the foam takes up about ±0.16 mm, but a much thinner or thicker board needs the right value
- Panel stack about 1.2 mm
- Standoffs about 4.5 mm across and 3–4 mm tall
- Component heights on the back: 4 mm or less (you found the ESP32 module is the tallest part). Under the four screw blocks (see `SCREWS` in `case.py`; only flat pads and logo areas there in the photos), 2.7 mm or less. The block at x = 20 on the bottom edge sits over the SCL/SDA header holes, so nothing can be soldered into those pins with the case closed.
- **Removing the speaker does not make the case any thinner:** the speaker (4.5 mm) sits beside the battery in the same 5 mm layer.

The checks in `checks/` test the case against a model of the board built from these numbers. They are not a substitute for a test print. **Print the front shell first (about 9 cm³) and test-fit the board before printing the rest.**

### If something doesn't fit

Edit the matching constant in `case.py` and run `python3 case.py` (needs `pip install manifold3d numpy`; the checks also need `trimesh scipy shapely rtree networkx matplotlib pillow`):
- **Display window off-centre:** `WIN_CX`, `WIN_CY`
- **Whole board too tight or loose:** `CLR` (sideways); `PCB_T` (front to back: set it to your board's measured thickness)
- **Lip touching the glass:** `PANEL_T`
- **A port misaligned:** `USB_Y`, `SD_Y`, `WHEEL`, `BUTTONS` (the PWR/BOOT opening follows `BUTTONS`, 6 mm past each switch)
- **Battery too tight or too loose in its bay:** `BATTERY_BAY` (x0, x1, y0, y1 of the bay; the guides follow it)
- **Speaker too tight or too loose in its pocket:** `SPEAKER_BOX` (the pocket's width and length; the brackets follow it)
- **Tall standoffs or parts:** `STANDOFF_H` only describes the board for the checks: set it to what you measure and run `python3 verify.py`. If that reports a collision, raise `PARTS_SPACE` (or `BATTERY_SPACE` for a thicker battery), which do change the case

Then run `python3 verify.py` for the quick fit check, or `checks/run_all.sh` for every check from the debugging rounds (about 15 minutes). The photo checks download Waveshare's images on first use; where `www.waveshare.com` can't be reached they report SKIP, never a pass. Round 19 onwards slice the parts with PrusaSlicer if `prusa-slicer` is installed.
