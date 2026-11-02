# Debug log

**Stopping rule:** keep going until two rounds in a row find no mistakes in the case or its documentation. Each round adds checks that use different methods from the earlier rounds, and re-runs every earlier check on the current design. Check scripts are in `checks/`; `checks/run_all.sh` runs everything.

Each round below lists its new methods, then what it found. A "check bug" was a mistake in my own test, not in the case. Those were fixed and do not count toward the stopping rule either way.

## Round 1: STL files read back from disk
**New methods:**
- trimesh integrity checks
- spheres standing in for a fingertip
- a model USB plug and microSD card
- ray-cast wall thickness, confirmed by probing a point inside
- slicing to find islands that start in mid-air
- a model M2 screw

**Mistakes found and fixed:**
- Screw heads reached 0.15 mm into the back cover at the seam.
- The USB-C opening had round ends that rectangular plugs hit.
- Skirt slivers 0.05 mm thick were left at the corners.
- A 0.5 mm web sat between the window and the panel-tail relief.
- The tail relief cut into the wall corners.
- The skirt was not attached to the battery cover, which printed as 13 loose bodies.
- There were zero-area triangles.

**Check bugs:**
- The mirrored back cover was inverted twice.
- The dial test searched in the wrong direction.
- The size thresholds were naive.

## Round 2: different methods
**New methods:**
- KD-tree clearance from surface samples (no booleans)
- opening sizes measured off STL sections
- Monte Carlo over random board tolerances
- overhang angles
- the cover lowered onto the shell, and the screws driven in
- openings drawn onto Waveshare's photos

**Mistakes found and fixed:**
- Brass standoffs could hit the back pressure pads in 11 of 60 random boards. The pads were moved 0.5 mm further out.
- The battery cover had a 1.5 mm flat ledge printed in mid-air. It became a 45° slope.

**Check bugs:**
- An impossible board shift was allowed.
- Overhang rules were too strict for small round holes.
- The window search used closed holes only.
- The photo overlay drew the wrong radius.

## Round 3: different methods
**New methods:**
- my own binary-STL parser
- "calipers" (rays) checked against a hand calculation of the stack
- re-measuring from Waveshare's dimension drawing instead of the photos
- ±0.15 mm printer error
- fingers approaching at angles

**Mistakes found and fixed:**
- **The display window was 0.5 mm off in y and 0.4 mm in x** compared with the drawing's active area, so the bottom margin was about 0. It was re-centred with at least 0.7 mm margin.
- Skirt and tab clearances were too small for printer error, so they were raised to 0.35 mm.
- **The buttons could not be pressed at an angle.** The recessed pocket was replaced by an open, bevelled opening.

**Check bugs:**
- The drawing check picked up dimension lines.
- A caliper ray went through the window.
- Monte Carlo let standoffs hang off the PCB.

## Round 4: different methods
**New methods:**
- dial reach at the drawing's 2.0 mm protrusion
- worst-case tolerance corners
- seam flushness
- longest safe screw
- window-to-tail web
- README numbers checked against the STLs
- cross-section images reviewed by eye

**Mistakes found and fixed:**
- A large thumb rolling the dial at 30° stopped 0.77 mm short. The thumb scoop was made wider.

**Check bugs:**
- The seam outline comparison used the wrong polygon.
- A 0.10 mm result failed a ≤ 0.10 test through floating-point rounding.

## Round 5: different methods
**New methods:**
- 0.4 mm nozzle erosion of every layer
- line of sight to the switch tips
- hand strength formulas
- ports and standoffs re-measured by colour segmentation of the photos

**Mistakes found and fixed:**
- **The mic holes had 0.2–0.3 mm webs between them** (unprintable). They were spaced 2.0 mm apart.
- A 0.25 mm fin was left where the button opening cut the battery cover's skirt join.

**Check bugs:**
- The segmentation took the orange display cable for a standoff.

## Round 6: different methods
**New methods:**
- exact swept volumes of every motion
- packing the speaker and a LiPo
- plastic around each screw thread
- microSD ejection with a pin
- the dial pressed in

**Mistakes found and fixed:**
- **The README said a 60 x 35 mm LiPo fits, but it did not.** The top screw blocks were in the way, so the top screws were moved.

## Round 7: different methods
**New methods:**
- exact point-to-mesh distances
- an edge-gap map all round the PCB
- how much of the display is visible at 30° and 45°
- 3D renders reviewed by eye

**Mistakes found and fixed:**
- **A screw counterbore ran into the dial's thumb scoop** (seen in the renders; a later round proved it merged). The fourth screw moved to the right-hand end.
- A 0.6 mm strip of shell was left above each counterbore. The screws were lowered so 1 mm remains.
- Pilot holes ended exactly at the screw tip, with no margin. They now go through the blocks.

## Round 8: different methods
**New methods:**
- wall-web scans at three depths
- build determinism
- half the circle resolution
- running the generator from another folder

**Mistakes found and fixed:**
- **Zero-area triangles** appeared where the pad edges sat exactly on circle vertices. Two independent checks agreed.
- Builds were not byte-identical. The STL writer now sorts the triangles.
- **The front skin was 0.33 mm thick at the top-left corner**, a pinhole seen in the renders and then measured. The panel-tail relief was moved off the corners.

## Round 9: different methods
**New methods:**
- dense thickness maps of the faces and walls
- a map of every opening compared with the intended list
- slim vs battery shells compared

**No mistakes in the case.**

**Check bugs:**
- Rays slipped through a mesh seam; a solid probe showed the wall was solid.
- One section passed exactly through vertices.

## Round 10: different methods
**New methods:**
- layer-by-layer support
- screw hole alignment recovered from the meshes
- display corners checked against the rounded window
- the whole README read against the code

**Mistakes found and fixed (documentation):**
- The README linked this file before it existed.
- It said the window position came from the photos.
- It gave only one dial protrusion value.
- It did not say the microSD card needs a nail or pen tip to eject.
- It listed only 3 of the check scripts.
- `preview/renders.png` still showed the old flexing buttons.
- The photo checks pointed at files on my machine; they now download Waveshare's images on first use.

**Check bugs found while running round 10:**
- Bridges over the USB-C and microSD openings were treated as unsupported.
- One layer passed exactly through the pilot-hole vertices.

## Round 11: different methods (clean)
**New methods:**
- point-in-solid grid clearance (a fourth independent engine)
- screwdriver access to every screw
- resting the case on each face and edge (no control may be pressed)
- smoothness of the outer skin
- the openings drawn on Waveshare's photos, reviewed by eye

**Result:** every check from rounds 1–11 found **0 problems**.

**Check bugs found while writing it:**
- The point grid was too slow.
- The smoothness test counted sliver faces along opening rims, and the hidden seam edge.

## Round 12: different methods (clean)
**New methods:**
- a capsule-shaped finger on the switches and dial
- rounded edges measured by fitting circles to sections: 7.00 mm plan corners and 4.50 mm edge rounding, exactly as designed
- the board pocket measured wall to wall: 100.10 x 60.60 mm, the PCB plus 0.3 mm each side
- every file and link named in the README exists
- cross-sections reviewed by eye

**Result:** every check from rounds 1–12 found **0 problems**.

**Check bugs found while writing it:**
- The circle fits mixed the inner and outer outlines.
- One section passed through the USB-C opening.

**Rounds 11 and 12 were two clean rounds in a row, so the session ended.**

## Session 2: the 454261 battery and the speaker

The battery version was rebuilt for Waveshare's 3.7 V 1500 mAh LiPo (454261) with the speaker beside it. The same stopping rule applies, with rounds 13 onwards adding new methods and re-running every earlier check on the new design.

**Found while redesigning, before the checks:**
- **The old battery version could not take a 454261 beside the speaker.** It was designed around a guessed 60 x 35 x 7 mm cell. Rebuilt for 61 x 42 x 4.5 mm, which also made it 2.0 mm thinner (16.7 mm instead of 18.7 mm).
- Removing the speaker saves no thickness: the speaker is thinner than the battery and sits beside it.

## Round 13: battery layout
**New methods:**
- the battery lowered into its bay (nominal, largest and bay-sized)
- how far the guides let it slide
- grille holes found by rays and checked against the speaker's face
- wire routes as 2.5 mm tubes through the closed case
- the stack-up sum for the new thickness

**Check bugs:**
- Round 3's hand calculation still expected the old 18.7 mm.
- The grille test ran before the geometry was rebuilt.
- The first wire routes started inside the battery.

## Round 14: different methods
**New methods:**
- distance from metal parts to the ESP32 antenna
- Monte Carlo over real battery and speaker sizes and positions
- the battery fitted the other way round

**Mistakes found and fixed:**
- **The speaker space was 2 mm from the ESP32's antenna end** and could hurt Wi-Fi/Bluetooth range. It was turned lengthways and moved; it is now 6.5 mm away.

**Check bugs:**
- The Monte Carlo let the battery move further than the guides allow.

## Round 15: different methods
**New methods:**
- the battery's length-to-width ratio measured on Waveshare's photo of it
- the slim version's grille
- zip integrity

**Mistakes found and fixed:**
- **Waveshare's photo suggests the battery is up to about 64.6 mm long** including its taped end, longer than the 61 mm its name implies. The bay was enlarged from 63 x 43 to 66 x 44 mm, and the speaker space shrank from 15 x 20 to 14 x 19 mm to make room while keeping the antenna distance.

**Check bugs:**
- The photo measurement first counted the wires as part of the cell.

## Round C: every check (rounds 1–15) on the final design
**Result:** every script found 0 problems. Reading the README against the results by hand still turned up two mistakes, so this round is **not clean**.

**Mistakes found and fixed (documentation):**
- The wire routes were given as 38 and 26 mm; they are 37 and 28 mm.
- The README said a 61 mm cell has "a little play". It can slide 2.5 mm each way.

## Round 16 (full run D): different methods
**New methods:**
- my own edge-orientation and body count from the raw STL bytes
- a depth map of the free space over the battery bay and the speaker (a z-buffer)
- bed contact area and centre of mass of each printed part
- the zips unpacked and compared file by file
- the README's session-2 numbers recomputed

**Result:** every check from rounds 1–16 found **0 problems**, and the README read by hand was correct.

## The slim version is dropped
You asked for only the battery + speaker case, so the slim (14.2 mm) version was removed: its STLs, zip and previews were deleted, and so were the checks that only applied to it. The battery STLs came out byte-identical, so the case itself did not change. The README was rewritten for one version, and `preview/renders.png` and the new `preview/explained.png` were made from the final geometry. These are new files, so the stopping rule starts again.

## Round 17: different methods
**New methods:**
- mutation testing of the README's "If something doesn't fit" advice: each constant is edited in a copy of `case.py`, which is then rebuilt
- frame widths measured on the STL with rays and compared with the README and `explained.png`
- a search for anything left from the slim version

**Mistakes found and fixed:**
- **Editing `BUTTONS` did not move the PWR/BOOT opening**, which was a fixed 68–90 mm. The opening is now worked out from `BUTTONS` (6 mm past each switch), which gives the same 68–90 mm, so the STLs did not change.
- **The README implied `STANDOFF_H` changes the case.** It only describes the board for the checks; the README now says so and names the constants that do change the case.

## Round 18: different methods
**New methods:**
- a clean clone of the repository rebuilt from scratch (the STLs and zip must match byte for byte)
- the printed parts shrunk by typical plastic shrinkage, with the board checked against them

**Mistakes found and fixed:**
- **At 0.4 % shrinkage (normal for PLA/PETG) the display's flex cable would rub the left wall.** It sticks 0.1 mm past the PCB edge, so it only had 0.2 mm of room. The left wall now has 0.3 mm extra room beside the flex (`FLEX_RELIEF`); the wall there is still at least 1.05 mm thick (two perimeters; the relief now reaches down to the front skin). The board now fits up to 0.5 % shrinkage.
- **The README recommended ASA with no warning.** ASA shrinks about 0.5–0.7 %, so the board would not go in. The README now says to turn on the slicer's shrinkage compensation for ASA/ABS.

## Round E: every check (rounds 1–18) on the single-version design
**Mistakes found and fixed (documentation, by reading it against `case.py`):**
- The README and `explained.png` said the picture area starts 9.2 mm from the left PCB edge and ends 3.9 mm from the right one, with a 0.8 mm window margin. I had assumed it was centred on the window. Waveshare's drawing puts it at x 9.3–95.7, so it is **9.3 and 3.8 mm**, with margins of 0.9 and 0.7 mm.

**Check bugs:**
- Round 4 still read the case size from the old two-version table.
- Round 8 expected four STL files.
- Round 17 made the same centring assumption as the README.

## Round 19: different methods
**New methods:**
- a real slicer: PrusaSlicer 2.7 (installed for this) checks each STL, then slices it with supports off and the README's settings. Its stability warnings must stay silent, and every layer must print something. I first tested that it does warn, on a mushroom shape.
- material and time estimates from the slicer

**Result:** both parts are manifold, one piece each, and slice with no warnings and no empty layers. The README now gives the estimate: about 26 g of PLA.

## Round F: every check (rounds 1–19)
**Result:** every check found **0 problems**, and the README and the explanation image read correctly by hand. **Clean.**

## Round 20: different methods
**New methods:**
- holes checked in the slicer's own G-code: every opening through the back plate (33: grille, mic, sensor) and the display window must keep a clear gap of at least 0.5 mm in the extrusion paths. The narrowest is 1.07 mm.
- bookkeeping: every check script is in `run_all.sh` and has an entry in this log

**Mistakes found and fixed (documentation):**
- Round 16's methods were filed under the heading "Round D", so no entry for round 16 could be found. The heading now names both.

## Round 21: different methods
**New methods:**
- as-sliced vs as-designed: on every second layer, PrusaSlicer's G-code is compared with a section of the STL at the same height. Nothing may be extruded outside the model, so no side opening (USB-C, microSD, PWR/BOOT, dial, vents, screw holes) gets bridged or filled, and the outer ring of every wall must actually be printed. To prove the test can fail, I offset the G-code by 1 mm; both parts of the test caught it.

**Check bugs found while writing it:**
- A section plane lying exactly on a flat face (the PCB pad tops at 3.3 mm) dropped those faces. The test now uses sections just above and below each layer's middle.

## Round H: every check (rounds 1–21)
**Result:** no problems in the case or its documentation: 289 checks passed, and rounds 1–19 and 21 reported 0 problems. **Clean**, with one caveat: round 20's bookkeeping test failed once, because I created `round22.py` while this round was running and it wasn't registered yet. That was my process slip (files should not change during a round), not a defect, so it does not count against the case. Round 22 was registered before round I.

## Round 22: different methods (estimates from textbook mechanics)
**New methods:**
- **Back-plate bending** (Navier series for a simply supported plate, checked against Timoshenko's square-plate value 0.0116). A thumb press of 20 N anywhere over the battery bends the 1.8 mm back about 0.6 mm in PLA and 1.05 mm in PETG. That leaves at least 1.7 mm between the largest allowed battery (4.8 mm) and the modelled board parts, and still 0.15 mm (PETG) to 0.6 mm (PLA) even if a 4 mm part sat anywhere under the bay. A hard 50 N squeeze is only reported: with PETG it could touch a 4 mm part if one sat mid-bay, and the board model has none there.
- **Screw pull-out:** 4.65 mm of thread in each block, about 146 N per screw (10 MPa layer-bond shear, 50 % thread fill).

**Result:** 0 problems.

## Round I: every check (rounds 1–22)
**Result:** every check found **0 problems** (297 checks passed).

**Rounds H and I were two clean rounds in a row on the final design, so session 2 ended.**

## Session 3: holding the board tight

You asked for the board to be held tight so it can't wobble, without screwing it down. Until now it was held at exactly zero gap between the front pads and the back rings, so print tolerance could leave it about 0.1–0.2 mm loose.

**First change (replaced in round 24):** each of the 4 back rings got a crush dot that pressed 0.2 mm into the board's place, and the ring faces sat 0.2 mm back. The first closing squashes the dots just enough. The board model leaves out a small zone around each dot (`crush_allowance()`), so every fit check treats that squeeze as intended. `verify.py` checks that the dots bite exactly as designed (0.402 mm³) and nothing else touches the PCB.

## Round 23: different methods
**New methods:**
- **Handedness in real space:** features are found on the printed STLs (the port end with USB-C above microSD, the wide frame band, the mic holes and the sensor slots) and compared with the real board in Waveshare's photos, using the sign of (left × up) · display normal. No numbers are taken from `case.py`.
- **Crush dots in the G-code:** PrusaSlicer must extrude every dot up to its tip.
- **Crush vs screw slack:** the dots must press further (0.2 mm) than the screws let the cover move back (0.15 mm).
- **Squash force:** a rough estimate from the dots' area.

**Mistakes found and fixed:**
- **The front shell STL was a mirror image of the part you need, in every version since session 1.** The design frame (x right and y up seen from the front, z into the device) is a mirror of real space. The back cover's print flip is a mirroring, which happened to correct it; the front shell was exported without one. All earlier checks compared the parts with a board model in the same mirrored frame, and the render script flips z, so nothing could see it. The front shell is now exported mirrored left to right (`front_for_print`), and the checks undo that. Run on the old files, the new test reports the front shell as a mirror image and the back cover as correct; on the new files, both are correct.
- **The first crush dots (0.6 mm) were dropped by the slicer.** The G-code ended at the ring faces. A test print of dot sizes showed 0.8 mm and up are printed, so the dots are now 0.8 mm.

**Checks updated for the change:**
- Round 3's calipers now expect the ring face 0.2 mm behind the PCB, and the dot tip 0.2 mm into it.
- Round 17 reads the front shell through the loader that undoes the print mirroring.

## Round 24: independent review by a second agent
A separate agent reviewed the whole project cold, with methods the checks didn't use:
- slicing at 0.12, 0.15 and 0.3 mm layers and reading the clamp heights from the G-code
- pixel profiles of the board edge in Waveshare's front photo
- the rings, dots and screw blocks overlaid on the back photo
- probing material along each screw axis
- post buckling and the mechanics of plastic crush

It confirmed the mirroring fix and found:
- **The crush dots only clamped at exactly 0.2 mm layers** (two rounding errors happened to cancel). At 0.15 mm the dots had to squash 0.4 mm and the case couldn't be closed by hand; at 0.3 mm the board was loose.
- **Squashed plastic stores almost no spring.** The side screws let the cover back off about 0.15–0.2 mm, so the grip mostly disappeared after the first closing. Round 23's "crush > screw slack" test compared the wrong things (a plastic squash with an elastic slack).
- **The first-closing force was underestimated about 2×** (16–29 kg). The dots' contact area grows as they squash.
- **The screw blocks stood 0.35 mm off the wall**, so tightening pulled the cover sideways across the skirt clearance.
- **The left front pads sat almost on the display glass's edge.** The photo shows the glass 0.75 mm from the PCB edge, not 1.0 as modelled. Round 2 never tested the full 0.3 mm left shift, because of a comment left over from before `FLEX_RELIEF`.
- Smaller items: `PCB_T` tolerance eats the clamp budget; the screw block at x = 20 sits over the SCL/SDA pins; the drill-mark screws would need spacers; stale comments in `case.py`; two PCB notches missing from the board model (no clash).

**Fixes:**
- **Foam replaces the crush dots** (your choice). The ring faces stay 0.6 mm behind the PCB, and a piece of 1 mm foam tape on each ring keeps the board pressed. It's elastic, so it absorbs layer height, board thickness and screw slack.
- **Screws (replaced again in round 25, see there).** My first fix, a boss on each block reaching to 0.1 mm from the wall, failed round 3's printer-error test: with the shell 0.15 mm small and the cover 0.15 mm large, the bosses scraped the wall (3.2 mm³ overlap). My second fix threaded the screws into the wall too (see round 25).
- **The left pads are removed**, and the board model's glass edges now come from the photo profile (x 0.75–98.5).
- **The flex relief** now reaches down to the front skin, for any panel thickness.
- **Round 2** shifts the board the full 0.3 mm in every direction.
- **Round 23** now slices both parts at 0.1, 0.15, 0.2 and 0.3 mm layers and works out the foam squeeze as printed. After round 25's stricter test, 1.0–1.2 mm foam stays squeezed 14–72 % at 0.1–0.2 mm layers (PCB ±0.16, 0.1 mm back-off). At 0.3 mm layers it can go loose, so the README asks for 0.2 mm or finer.
- The README notes were added and the stale comments fixed.
- The PCB notches were left out of the model: they make nothing collide, and the pad that would have lost its support is gone.

## Round 25: second independent review
The same agent reviewed the changes. It confirmed that the foam absorbs layer-height and board-thickness tolerance, and found:
- **The 1 mm thread in the wall would strip as soon as the screw head seated** (about 31 N by round 22's own model, reached at a torque below what it takes to drive the screw). After that, the head pulls the block sideways again.
- **Foam pressing on the narrow ring faces gives only about 1–2.5 N**, so friction alone barely holds the board sideways (estimate). The README didn't name a foam type or say what to do with the liner.
- **Round 23's foam test was too lenient.** It used 1.0 mm foam only, a 5 % floor, and zero slack.
- No lead-in on the pilots.
- The PCB-thickness advice was still missing.
- The flex relief leaves 1.05 mm of wall, not the "1.3 mm" this log said.
- The suggested foam piece size overhangs the smallest ring.

**Fixes:**
- **The wall hole is a clearance hole again, set 0.15 mm toward the front** (a drawbore). With the case shut, the screw shank rests on the hole's back edge, so the foam can't push the cover back, and no thin wall thread carries load. Rounds 1, 9 and 10 now check the offset hole. Round 10's hole finder was itself wrong for an off-centre hole (it averaged ray hits); it now fits a circle.
- **Each pilot has a 0.35 mm 45° lead-in.**
- **Foam:** PE foam mounting tape, 1.0–1.2 mm, about 1.5 × 3 mm pieces, stuck to both the ring and the board, so adhesion holds the board sideways and squeeze is only needed for contact.
- **Round 23** now requires 10–75 % squeeze for both 1.0 and 1.2 mm foam, over PCB ±0.16 and 0.1 mm of back-off.
- **README:** says to stop when the head touches, how to reassemble, and to measure the PCB (`PCB_T`).

## Round 26: third independent review
The reviewer found nothing significant in the drawbore or the foam stuck on both sides. One real but minor finding, confirmed in G-code: at 0.2 mm layers two roundings add up (the hole top prints at 10.2 instead of 10.3, and the cover rim at 4.4 instead of 4.3). With the 0.15 mm draw, the M2 shank would cut about 0.17 mm into the top of the wall hole, partly bringing back the wall-thread stripping risk.

**Fixes:**
- **`SCREW_DRAW` is 0.05.** The hole top (10.4) now sits on both the 0.1 and 0.2 mm layer grids.
- **Round 23 measures the screw position instead of assuming a 0.1 mm back-off.** It reads the printed hole top and pilot axis from the G-code and requires the shank to cut no more than 0.05 mm, with the foam still squeezed over the measured back-off.
  - Results: back-off 0.13 / 0.23 / 0.03 mm at 0.1 / 0.15 / 0.2 mm layers, no cutting, foam squeezed 11–72 %.
  - At 0.3 mm layers the shank would cut 0.4 mm, so they stay not recommended.
  - Check bug found while writing it: the pilot search window first reached past the top of the block and counted empty layers as hole.
- **README:** use fresh foam after opening; seat the dial tab first and lower the cover straight.

## Final full run: every check (rounds 1–23) on the delivered design
**Result:** 0 problems; 304 checks passed. The last independent review (round 26) found nothing significant, and its one minor finding is fixed. Round 23 now measures exactly what that finding was about, and its numbers match the reviewer's own G-code measurements.

## Round 27: fourth independent review (final design, material, screws, screwless option)
**Findings and fixes:**
- **Screws of 8 mm or more in the two bottom holes reach the battery,** and nothing gave a maximum length (the owner will use found screws). README and both guides now say 5–6 mm, never more than 7 mm. Round 22 sweeps screw lengths against the largest allowed cell at the bay's edge: 8 mm reaches it in the bottom holes, 12 mm in the top hole.
- **The plastic around each pilot is thin:** 1.2 mm at the sides and 0.9 mm at the free end, printed as two strips joined across layers. The estimated strain from thread-forming was about 2–2.8 % for M2. The pilot is now 1.7 mm (r 0.85): estimated strain about 1.5–2.1 %, thread engagement still 4.4 mm, pull-out about 110 N per screw.
- **Docs:**
  - Screw heads: 4.0 mm or less across, 1.4 mm or less tall, not countersunk or washer-head.
  - Avoid ST2.2 sheet-metal screws, or drill the holes out first.
  - Pre-cut the threads before closing, and tighten top and bottom alternately.
  - PETG (or PCTG) is recommended; PLA only indoors.
- **Not changed:** widening the screw blocks needs the photo check of the parts under them redone. The block at x 64 can't grow, because it is 0.5 mm from a connector.
- **Material verdict:** a stiff, tough plastic, not a flexible one. Black PETG, or PCTG if available. No TPU or PP for the body.
- **Screwless (snap-fit) option:** feasible, with rigid hooks along the top edge and two latch arms along the bottom. But it holds about 10–30× less than the screws, the arms are printed across the layers, and the worst-case hook engagement is only about 0.3 mm. Not built; the owner decides.

## What the checks cannot prove
Every check compares the case with a model of the board. That model is built from Waveshare's drawing, which covers only the outline and display area, and from my measurements of their photos (about ±0.5 mm). The board thickness, the panel stack and the component heights are estimates; see README. A test print of the front shell is still the real proof.
