# Case for the Waveshare ESP32-S3-ePaper-3.97

A two-piece case with rounded edges for the Waveshare ESP32-S3 3.97" e-Paper board (SKU 33552, part number `ESP32-S3-ePaper-3.97`), with room inside for Waveshare's 3.7 V 1500 mAh LiPo (model 454261) and the speaker **side by side**. It measures 104.9 x 65.4 x 16.7 mm. It is designed for **rigid plastic**: nothing has to bend to assemble it or to press the buttons.

![renders](preview/renders.png)

![explained](preview/explained.png)

## Files

| File | What it is |
|---|---|
| `stl/front_shell_battery.stl` + `stl/back_cover_battery.stl` | The two parts to print. |
| `docs/assembly_guide_en.pdf`, `docs/assembly_guide_bg.pdf` | Illustrated assembly guide in English and Bulgarian: what to buy, printing, and every step. |
| `dist/` | The zip to download: the two STL files, this README, the renders and the assembly guides. `make_zips.py` rebuilds it. |
| `case.py` | Parametric generator. Every dimension is a named constant at the top. |
| `verify.py` | Quick fit check: collisions, insertion path, clamping, glass clearance. |
| `checks/` | The debugging rounds (see [DEBUG_LOG.md](DEBUG_LOG.md)). |
| `preview/` | Renders, cross-sections, and the openings drawn onto Waveshare's own photos. |

## You also need

**4 × M2 screws, 5–6 mm long under the head, never longer than 7 mm** (the two bottom screws point at the battery: 8 mm or longer reaches it). Use M2 machine screws or thread-forming screws made for plastic, with a pan, cheese or button head no more than 4.0 mm across and 1.4 mm tall. Not countersunk, not washer-head. Two go in the bottom edge, one near the top-left corner and one in the right-hand end (see `preview/screw_locations.png`). They pass through the side wall and cut their own thread in the printed block behind it. Avoid 2.2 mm sheet-metal self-tappers (ST2.2): they jam in the wall hole and can split the blocks. If that's all you have, drill the wall holes to 2.4–2.5 mm and the pilots to 1.8 mm first.

**Double-sided PE foam mounting tape, 1.0–1.2 mm thick** (not thinner): four small pieces hold the board tight (see Assembly).

## Features

- **Display window:** 88.0 x 53.6 mm, placed from Waveshare's dimension drawing. The active area is 86.4 x 51.84 mm, so there is at least 0.7 mm of margin all round. The window edge has a 45° chamfer.
- **Why the left end of the frame is wider (11.1 mm vs about 6 mm elsewhere):** the display's picture area is not centred on the board. It starts 9.3 mm from the left PCB edge but ends 3.8 mm from the right one. The strip in between is inactive glass and the display's ribbon cable, so the window can't go further left without showing it (see `preview/explained.png`).
- **Board held tight, no load on the glass:** the lip sits about 0.5 mm above the screen. The PCB is pressed against pads along its top, bottom and right edges by four rings behind it (around the brass standoffs), each with a piece of foam tape stuck to both the ring and the board. The rings stop 0.6 mm short of the board, so the foam is always squeezed, even with print, layer-height and board-thickness tolerances. Because it's stuck on both sides it also holds the board sideways, so the board can't rattle. No plastic has to bend, and the left end has no pad because the glass edge is too close to the PCB edge there.
- **PWR and BOOT:** nothing covers them. The bottom wall is left out in front of both switches: an opening 22.0 mm wide, open from the front face up past the seam, with bevelled edges. A fingertip reaches the switches straight on or tilted 15° in any direction, and 30° from the front or back. Tilted 30° sideways toward an end of the opening, a fingertip stops about 3 mm short, so press those roughly straight on. The display lip stays continuous above the opening.
- **USB-C:** a 13 x 7 mm opening with 1.2 mm corner radius, so normal cable plugs seat fully.
- **microSD:** a slot with a finger scoop. The latched card sits about 4 mm inside the outer wall, so press it with a fingernail or a pen tip to eject it.
- **Dial (UP / DOWN / press):** the wheel rim is exposed through a slot with a thumb scoop. The back cover has a tab that closes the slot above the wheel.
- **Vents and grille:** holes for the microphone (left side and back) and the temperature/humidity sensor (right side and back), plus a speaker grille on the back, under the speaker.
- **Battery bay:** 66 x 44 mm, with a short guide bar on each side. The corners are left open for the battery's wire. A cell of the 61 mm nominal length can slide about 2.5 mm each way between the guides (a longer cell less), so the tape is what holds it in place.
- **Closing the case:** 4 side screws hold the two halves firmly; they only come apart once the screws are out. Each screw's hole in the wall is set slightly toward the front, so the foam can push the cover back by at most about 0.2 mm (allowed for in the foam's squeeze), and the screw never has to cut a thread in the thin wall. Each pilot hole has a lead-in so the screw tip finds it. The back cover's skirt only locates it, with 0.35 mm clearance; nothing snaps or bends, so the case works in PLA or any other rigid plastic.
- **Optional extra screws:** small cone marks on the back show where to drill if you also want to screw into the board's brass standoffs. Their thread size is unknown (M2 or M2.5), and there is roughly 6 mm (an estimate) between a standoff and the back, so you'd need a spacer; a screw without one would pull the board off the front pads. The foam already holds the board, so this is rarely worth it.

## Printing

- **PETG** (recommended; **PCTG** is even tougher), or PLA for indoor use out of the sun (PLA softens around 55 °C and is more likely to crack at the screws). **0.2 mm layers or finer** (0.1–0.2 mm), 3 perimeters, 15–20 % infill. **No supports needed.** Don't use 0.3 mm layers: the slicer rounds the clamping faces too far for the foam to press the board reliably.
- **ASA or ABS:** these shrink more as they cool (roughly 0.5–0.7 %, depending on the brand), enough to make the board too tight. Turn on your slicer's XY shrinkage compensation for that filament (PrusaSlicer and OrcaSlicer have it in the filament settings) or print in PLA/PETG. PLA and PETG (about 0.2–0.4 %) need nothing.
- **Front shell:** print display side down. The front edge uses an arc that ends in a 45° chamfer, so it prints cleanly against the bed.
- **Back cover:** the STL is already flipped. Print it outside face down.
- **Material:** about 26 g of PLA for both parts with these settings (PrusaSlicer's estimate). Its generic profile estimates about 3 hours; a fast printer takes much less.

## Assembly

1. Put the board face-down into the front shell. The dial drops into the notch on the top edge, and the PWR/BOOT switches sit in the opening in the bottom wall.
2. Plug in the speaker and the battery. Stick them to the back cover with thin double-sided tape. Cut 4 pieces of the foam tape, about 1.5 × 3 mm, and stick one onto each of the 4 small curved rings in the back cover's corners. Peel the top liner off too, so the foam sticks to the board when the case is closed. The board will then come out with the back cover when you open the case; peel the foam off the board if you need to separate them. Foam tape usually tears when peeled, so use fresh pieces when you put it back together. When closing, seat the dial tab first and lower the cover straight down.
   - The battery goes in its bay, with its wire end toward the USB-C side of the case. The speaker sits over the grille next to the bay, turned lengthways and kept 6.5 mm from the ESP32's antenna end so it doesn't hurt Wi-Fi/Bluetooth range.
   - **Wires:** both run along the bottom edge of the board to the BAT and SPK headers; checked routes are about 37 mm and 28 mm long.
3. Pre-cut the threads: before closing, drive each screw about 4 mm into the hole in its block (from the side that will face the wall), then back it out. This way the screws turn easily later and you can feel when the heads seat. Then put the back cover on; its tab drops into the slot above the dial. Press it down until the seam closes (the foam gives a light springy resistance), hold it there and drive in the 4 screws until the heads just touch the bottom of their recesses, then stop. Tighten them top and bottom alternately. Over-tightening can strip the plastic thread or pull the cover sideways. When you reassemble, turn each screw backwards first until it drops into its old thread.

## Where the numbers come from

**Official (Waveshare outline drawing):**
- PCB 99.5 x 60 mm, corner radius 2 mm
- Active display area 86.40 x 51.84 mm

**Display window position:** from the dimension lines on the same drawing. Waveshare's photos agree within about 0.5 mm.

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
- Component heights on the back: 4 mm or less. Under the four screw blocks (see `SCREWS` in `case.py`; only flat pads and logo areas there in the photos), 2.7 mm or less. The block at x = 20 on the bottom edge sits over the SCL/SDA header holes, so nothing can be soldered into those pins with the case closed.
- **Battery:** Waveshare's 3.7 V 1500 mAh LiPo, model 454261. By the usual LiPo naming convention that is 4.5 x 42 x 61 mm, but Waveshare's photo of it looks up to about 64.6 mm long including the taped end. The bay takes up to about 65.5 x 43.5 x 5 mm.
- **Speaker:** about 18 x 13 x 3.5 mm, estimated from Waveshare's photo next to the board (its size is not published). A 14 x 19 x 4.5 mm space is kept for it, turned lengthways.
- **Removing the speaker does not make the case any thinner:** the speaker is thinner than the battery and sits beside it.

The checks in `checks/` test the case against a model of the board built from these numbers. They are not a substitute for a test print. **Print the front shell first (about 9 cm³) and test-fit the board before printing the rest.**

### If something doesn't fit

Edit the matching constant in `case.py` and run `python3 case.py` (needs `pip install manifold3d numpy`; the checks also need `trimesh scipy shapely rtree networkx matplotlib pillow`):
- **Display window off-centre:** `WIN_CX`, `WIN_CY`
- **Whole board too tight or loose:** `CLR` (sideways); `PCB_T` (front to back: set it to your board's measured thickness)
- **Lip touching the glass:** `PANEL_T`
- **A port misaligned:** `USB_Y`, `SD_Y`, `WHEEL`, `BUTTONS` (the PWR/BOOT opening follows `BUTTONS`, 6 mm past each switch)
- **Tall standoffs or parts:** `STANDOFF_H` only describes the board for the checks: set it to what you measure and run `python3 verify.py`. If that reports a collision, raise `PARTS_SPACE` (or `BATTERY_SPACE` for a thicker battery), which do change the case

Then run `python3 verify.py` for the quick fit check, or `checks/run_all.sh` for every check from the debugging rounds (about 10 minutes; the photo checks download Waveshare's images on first use, and round 19 slices the parts with PrusaSlicer if `prusa-slicer` is installed).
