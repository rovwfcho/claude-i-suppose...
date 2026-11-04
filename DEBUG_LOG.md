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

## Session 4: your own battery and speaker, printed in PLA

You measured your battery, speaker and board against a ruler and sent photos, and you're printing in PLA. The same stopping rule applies: rounds 28 onwards add new methods and re-run every earlier check on the current design, until two rounds in a row find no mistakes.

**What changed in the design:**
- **Battery bay:** 66 x 44 mm (sized for the largest cell Waveshare's photo allowed) → **62.5 x 42.5 mm** for your 61.1 x 40.7 x 4.3 mm cell. Your cell could slide 2.5 mm before; now it can slide about 0.9 mm. It has guide bars on all four sides, not one short bar per side. The bars skip the screw blocks and leave every corner open for the wire.
- **Speaker:** the old 14 x 19 x 4.5 mm space (from an 18 x 13 x 3.5 mm guess) → a **pocket for your 14.2 x 10.2 x 4.5 mm speaker** with four corner brackets. It is 7.9 mm from the antenna (was 6.5).
- **Grille:** 28 round holes in a 12 x 17 mm oval, larger than your speaker → **three slots, 7.0 mm long, under its membrane** (1.0 mm wide at first, 0.9 mm since round 33). 7 of the old holes would have been outside your speaker altogether, so the sound from the back of the cone would have leaked out round it and cancelled bass. 11 more would have sat under its frame and gasket instead of the membrane.
- **Screw pilots 1.7 → 1.8 mm** for PLA: forming the thread strains the block walls about a third less. Pull-out by round 22's model: about 73 N per screw.
- **Wire routes and a loop for the spare speaker cable** are now in `case.py`, so the checks and the guide's pictures use the same ones.

**Checks updated for the change** (they described the old parts, not mistakes in them):
- Round 6 and round 13 now read the pocket and bay sizes from `case.py`.
- Round 13: the grille test now asks that every opening sits under the membrane wherever the speaker sits in its pocket, and at least 1.5 mm inside the speaker's sealed face.
- Round 14's Monte Carlo now draws parts around your measured sizes instead of 60–65.5 mm cells and 15–18.5 mm speakers. Those would no longer fit this bay, by design.
- Round 15: Waveshare's battery photo is only shown for comparison now. Your cell was measured directly, and that is the one going in.
- Round 16 gives the bay and the pocket to 0.1 mm.
- Round 17's mutation test covers the two new constants the README names, `BATTERY_BAY` and `SPEAKER_BOX`.
- **Rounds 2, 3, 5 and 15 need Waveshare's photos and drawing, and `www.waveshare.com` and `docs.waveshare.com` are blocked where these rounds ran.** Those four sub-checks now print SKIP, never OK. They test the board-facing openings, which this session did not change, and they passed in sessions 1–3. Round 28 checks the USB-C, the buttons and the dial against photos of your own board instead.

**Check bugs found while redesigning:**
- **Round 1, islands:** with 1.8 mm pilots, the top of each pilot lies exactly on one of round 1's slicing planes (z = 6.5). trimesh's section there came out malformed and dropped a polygon, so the next layer looked like it started in mid-air. A second slicer (manifold3d) showed that layer fully supported (30.2 of 30.2 mm² on the layer below). The planes now sit 0.013 mm off the layer middles.
- **Round 1, screws:** the "tip buried" test had the old pilot's ring area typed in as a number. It now works it out from `SCREW_PILOT_R`.

## Round 28: your photos (new methods)
**New methods:**
- **Ruler scale read by the computer:** the dark tick marks along one row of each photo are found, and a straight line is fitted through tick number against position. That gives 17–43 ticks per photo (scatter 0.55–1.5 px), not two numbers read by eye.
- **Edges refined automatically:** from a position marked by eye, the outermost strong colour step, on 11–25 rows.
- **Perspective transforms:** the speaker's frame in your top view gives the membrane, peg and cable exit. The four brass standoff tops in your back photo give board coordinates.
- **A review image**, `preview/owner_measurements.png`, with every tick, edge and landmark drawn on.

**Results:**
- Battery 61.08 x 40.73 x 4.32 mm.
- Speaker 14.19 x 10.19 x 4.49 mm, membrane 10.08 x 5.77 mm. The cable leaves the speaker 2.88 mm from the peg's end.
- Your board: USB-C, buttons, dial and top edge all within 0.48 mm of the board model.

**Mistakes found and fixed:**
- **The speaker pocket was 11.5 x 15.5 mm**, leaving up to 0.75 mm on a side: looser than you asked for. It is now 11.2 x 15.3 mm, about 0.5 mm on every side.
- **The brackets' legs came within 0.08 mm of the speaker's cable** with the speaker pushed toward its peg end, because the cable leaves only 2.9 mm from that end. The legs along the long sides are now 1.2 mm (were 1.8) and along the short sides 2.0 mm (were 2.5). The cable now clears by 0.68 mm and the peg by 0.79 mm.

**Check bug:** the first edge finder took the strongest colour step. On the speaker, that is the inner side of its bright metal rim, so it read 0.2 mm small. It now takes the outermost strong step, which matches the outline.

## Round J: every check (rounds 1–28) on the session 4 design
**Result:** 314 checks passed. 4 were SKIPPED because Waveshare's site is blocked here: the photo overlay (round 2), the drawing (round 3), the photo segmentation (round 5) and the battery photo (round 15). **Not clean.**

**Mistake found and fixed (documentation):**
- The README named `build_all.sh` without its folder (found by round 12's link check). It now says `docs/guide-src/build_all.sh`.

**Check bugs:**
- **Round 17 still looked for "14.2"** (the old slim version's thickness) as a leftover. 14.2 mm is now your speaker's length. It now looks for the thickness wording instead.
- **Rounds 20 and 23 were killed for using 14 GB of memory.** Their through-hole finder cast all 650 000 rays in one batch. With 3 slots instead of 28 holes, the back face is cut into fewer, longer triangles whose boxes each cover many rays. It now casts 20 000 rays at a time; the result is the same.

## Round 29: different methods
**New methods:**
- **Tolerance stack-up, statistically:** 100 000 random cases combining measuring error, printing error and PLA shrinkage.
- **ID pictures:** each guide picture is rendered again in flat colours, one per part. Every numbered marker must be within 20 px of the part it names.
- **The same nine facts in three documents:** the README, the English guide and the Bulgarian guide.
- **Cable bends:** every corner of every wire route is rounded, and the radius each corner can take is worked out from the straight lengths beside it.
- **Calipers on the cover STL** for the bay and the pocket.
- **A heat estimate** for PLA.

**Mistakes found and fixed:**
- **The speaker cable's route needed a 2.45 mm bend.** It dropped straight down between two right-angle turns, and its sleeved part needs 3 mm or more. The route now slopes down under the battery: its bend under the battery can take 5.7 mm, and the thin leads at its two ends 2.35 and 3.1 mm.
- **The battery wire's route had two 0.95 mm bends** (it needs 1 mm). The short straight between them is now 2.4 mm.
- **The documents said the battery is 40.8 mm wide;** round 28 measures 40.73. `BATTERY_SIZE`, the README and both guides now say 40.7, and the play is about 0.9 mm (was 0.8).
- **One guide marker** (print picture, marker 1) sat in the middle of the display window, over empty space. It is now on the shell's rim.
- **The spare speaker cable didn't fit its loop.** Traced roughly in your photo, the cable is 100–105 mm (round 30's careful trace: 101 mm), so 70–75 mm is spare, but the loop held only 64 mm. The loop is now taller (reaching to within 4.9 mm of the top wall, clear of the dial tab and the antenna end) and holds 77 mm.

**Check bug:** the first version compared the battery plus tape plus ageing swelling with the nominal 5 mm room. Over the bay, the first thing the cell could reach is the wires under it, 5.6 mm away. It is now measured against that.

**Results:**
- The battery goes in, and has less than 1.2 mm of play per side, in 100 % of the random cases; so does the speaker.
- The speaker's cable clears its bracket legs in 100 % of cases and its peg in 99.9 %.
- The cell plus tape plus swelling never reaches what lies under it.
- 31 guide markers point at their parts.
- The case runs about 7 K above the room with 1 W inside; in full sun it can pass 55 °C, which the README warns about.

## Round 30: different methods
**New methods:**
- **Handedness of the speaker instruction:** the sign of (peg × cable) · (sound-face normal), from your top view of the speaker, carried into the case's real-space frame. With the sound face to the back and the peg up, the cable must point at the battery. That is what the README, the guides and the cable route say.
- **Cable lengths traced in your photo** and measured through a perspective transform from the four standoff tops, against the routes and the loop.
- **The slicer's lines over the thin new features:** at 0.1, 0.15 and 0.2 mm layers, PrusaSlicer's extrusion lines, at the widths it writes in the G-code, must cover at least 85 % of every guide bar and L bracket on each layer, up to within one layer of the top.
- **The documentation rebuilt from a clean clone** of the last commit: `preview/renders.png` must be pixel-identical, and both guides must have the same pages and text.

**Check bug found while writing it:** the first coverage test drew every extrusion line 0.45 mm wide with square ends, and measured each bracket as two separate boxes. It said the fine-layer bars were only 65–75 % covered. PrusaSlicer's own widths at 0.1 mm layers are 0.61–0.71 mm. With those, round ends and whole L shapes, the cover is 98–100 %.

**Result of round 30 (all scripts, rounds 1–30):** 340 checks passed, the same 4 SKIPPED (Waveshare's site), 0 problems in any script. **Not clean:** reading the README against round 30's results turned up two mistakes.

**Mistakes found and fixed (documentation):**
- The README said round 28 refines each edge to "the strongest colour step". Since round 28's own fix it takes the outermost strong step (the part's outline). The README now says that.
- The README gave about 57 mm of battery wire, and round 13's message about 106 mm of speaker cable. Both came from my first rough reading of the photo. Round 30 traces them through a perspective transform at 54 and 101 mm. The README, round 13 and round 29's entry now use those figures. Both cables still have plenty of length: 16 mm spare on the battery wire, and 71 mm on the speaker cable for a 77 mm loop.

## Round 31: different methods
**New methods:**
- **Cable routes found by a search instead of drawn:** the closed case becomes a 0.5 mm voxel map: sections of the shell, cover, board parts, the largest plausible battery and the speaker, filled layer by layer. A distance transform gives every voxel's room. Dijkstra's shortest path then runs through the voxels with room for each cable (2.8 mm speaker cable, 2.5 mm battery pair), from where each cable leaves its part to its plug.
- **Every number new in the README since session 3** is listed automatically, and each must be traced to `case.py`, a check's result or a measurement by a written rule.
- **The cover closing with its load:** the largest battery in each corner of its bay, the speaker in each corner of its pocket, and the spare-cable loop are swept straight down the last 20 mm with the cover (exact convex sweeps). They must miss the board and the shell.

**Result of round 31 (all scripts, rounds 1–31):** 344 checks passed, the same 4 SKIPPED, 0 problems in any script. **Not clean:** reading the README and both guides against the design turned up the following.

**Mistakes found and fixed (documentation):**
- **Nothing said which way to turn the back cover over with the wires plugged in.** The battery wire has only about 16 mm to spare (round 30). Turning the cover over its top edge would swing the battery's wire end about 115 mm away from the BAT plug and yank it. The README and both guides now say to turn it over like the page of a book along the bottom edge, where the wires run, then hold it over the shell with the tab above the dial slot and lower it straight down.
- **In both guides, pre-cutting the threads was in step 5,** after the case is closed in step 4. It said "before closing the case (step 4)", but a reader following the steps reaches it too late, and with PLA pre-cutting matters more. It is now the first thing in step 4; step 5 only drives the screws. The print section points to step 4.
- The README said "Neither can rattle", which is only true once the battery and speaker are taped in. It now says so.
- The fig3 legend said the tab goes in "first", which no longer matches the straight-down instruction.
- Two sentences in this log were wrong. It said the old grille would have left "about half" its holes outside your speaker; counted, it is 7 of 28 outside it and 11 more under its frame. It also said round 28 checks "the same openings" as Waveshare's photo checks; it checks the USB-C, the buttons and the dial. A comment in `case.py` named the wrong rounds for the cable routes (13 and 28; it is 13, 29 and 31).

## Round 32: different methods
**New methods:**
- **Calipers on the G-code:** the bay and the speaker pocket measured on what PrusaSlicer will print, at 0.1, 0.15 and 0.2 mm layers. Each inner face is where the slicer's lines end, their centre plus half the width it writes for them. These must be within 0.15 mm of the design, and leave your battery and speaker 0.3–1.2 mm on every side.
- **The order of the work:** the assembly steps of the README and of both guides are read in order. The plugs and the foam must come before the cover goes on, the threads must be pre-cut before it goes on, the cover must be turned over along the bottom edge before it is lowered, and the screws must be driven only after that.
- **Sound, a textbook estimate:** the grille's open area against the membrane, and the Helmholtz resonance of the air in front of the membrane, with the slots as its neck.

**Check bug found while writing it:** the first windows for the bay's inner faces were shorter than the guide bars. The slicer's lines run the bars' whole length, so no line fitted inside a window and the bay read as "nan". Each window now holds one whole bar.

**Results:**
- As sliced, the bay is 62.50 x 42.50 mm at all three layer heights. The pocket is 11.10–11.20 x 15.18–15.29 mm, leaving your speaker about 0.45–0.5 mm a side.
- The steps are in the right order in all three documents.
- The grille is 35 % open over the membrane, and the air in front of it resonates at about 15 kHz, above what this speaker plays.

**Result of round 32 (all scripts, rounds 1–32):** 346 checks passed, the same 4 SKIPPED. **Clean** for the case and its documentation: no mistake in either was found, by the scripts or by reading. One script problem was a check bug.

**Check bug:** round 31's README inventory had no rule for the "16 mm to spare" added in round 31's fixes. The number is right: round 30's 54 mm battery wire minus round 13's 38 mm route. The inventory now works it out from those two results.

## Round 33: different methods
**New methods:**
- **Can the new checks fail?** In a copy of the project, 5 deliberate mistakes are made in `case.py`, one at a time, and the STLs rebuilt there. The session-4 check meant to catch each one must then report a problem. The mistakes are: a bay 1.5 mm too short, a pocket 1 mm too narrow, slots 2 mm off the membrane, bracket legs 3 mm long, and the spare-cable loop moved next to the antenna.
- **The two guides side by side:** every field of the English and the Bulgarian text must have the same shape (rows, bullets, legends) and the same numbers in the same order.
- **Margins against small changes:** each new dimension (bay, pocket, bracket legs, slot pitch and length, cable exit) is moved 0.1 mm either way. Every session-4 margin must stay at or above its limit.

**Mistake found and fixed (design):**
- **The grille sat on the edge of two limits.** Its webs were exactly the 0.8 mm minimum, and with the speaker pushed fully to one side the outer slot came within 0.08 mm of the membrane's measured edge. Moving the slots 0.1 mm took both below zero. The slots are now 0.9 mm wide on the same 1.8 mm pitch: 0.9 mm webs, 0.13 mm of room at the membrane's edge (was 0.08), still 32 % open (Helmholtz resonance still about 15 kHz). The back cover STL changed.

**Check gap found by the deliberate mistakes:**
- **Nothing checked how close the cables come to the antenna.** Moving the spare-cable loop next to the antenna end, clear of everything else, got past every check. The README tells you to keep it away, but no check held the design to that. Round 14 now requires the cable routes and the loop to stay 5 mm (in plan) from the antenna end. The loop in the design is 5.1 mm away. With that, all 5 mistakes are caught.

**Check bug:** round 28 crashed in the copy because the copy had no `preview/` folder for its review image. The copy now gets one.

## Round 34: different methods
**New methods:**
- **Volume accounting against session 3:** session 3's back cover is read from git. With the screw blocks left out of both, its volume change must equal what this session's features add and remove, worked out by hand from their sizes: the new guide bars and brackets added, the slots cut out, the old guide bars removed and the 28 old grille holes filled in. Any change nobody intended would show up as a difference.
- **Pictures and the text that points at them:** in both guides every marker must be in its picture's legend and every legend entry must have a marker, and "marked 3 in the picture above" must point at the foam.
- **Is the measured battery a possible battery?** 1500 mAh at 3.7 V in the measured volume must give an energy density real LiPo pouch cells have (300–750 Wh/L).

**Result of round 34 (all scripts, rounds 1–34):** every script passed, the same 4 SKIPPED. **Not clean:** reading the log back found three of its own sentences wrong (round 28's edge rows are 11–25, not 10–20; round 29's loop reaches to within 4.9 mm of the top wall, not 5.5 mm from it; round 33's grille has 0.13 mm of room at the membrane's edge, not 0.13 mm more). They are corrected above.

## Session 5: the board screwed to the back, the lid on snap clips

You asked for the board to be held by four screws through its own corner standoffs, from the back, with the front lid then locked onto the back over the display, and answered my questions: snap clips, firm; thread size unknown (so M2 or M2.5); standoffs 3–4 mm (posts built for 4 mm, the screw 2 mm into the standoff); heads sunk flush; display window kept; no foam; same battery and speaker; back edges less round; M2.5 x 8 (or M2 x 8) screws. Rounds 35 onwards add new methods and re-run every earlier check that could have changed, until two rounds in a row find no mistakes. `checks/run_checks.py` now skips a round only when nothing it reads has changed since it passed (its scripts, `case.py` without comments, the STLs, the README, the guides, the log, the photos, the slicer).

**What changed in the design:**
- **Side screws, screw blocks and foam rings removed.** Each corner of the back cover has a **post** that stands on a standoff's top, where a 4 mm standoff ends. A 3.4 mm hole and a 6.2 x 2.4 mm recess take an M2.5 x 8 screw, which then goes 2.6 mm into the standoff with 3 or 4 mm standoffs (until round 46 the recess was 1.8 mm deep and the screw went 2 mm in) (with 3 mm ones the board sits 1 mm further back). The recess is printed face down, so its ceiling starts with two bridging layers (a slot across it, then a square) before the round hole.
- **Standoff positions re-measured.** Waveshare's photos had put them at x 2.2 / 96.7, y 2.85 / 57.4. Your back photo (round 35, corrected for the standoff tops being nearer the camera) puts the right-hand pair 0.3–0.7 mm further right. The case now uses the symmetric layout between the two (x 2.45 / 97.05, y 2.725 / 57.275); every estimate is within 0.45 mm of it, and the holes allow 0.4.
- **Snap clips:** four 28 mm stretches of the back cover's skirt along the long walls, freed from the cover by a 0.6 mm slot so each is a beam held at both ends, bending in the plane of the print layers. A hook on each (0.55 mm undercut, 45° catch) clicks into a groove inside the lid's wall; a 30° chamfer inside the lid's rim does the pushing. Closed, each beam stays bent 0.1 mm, so the lid can't rattle. About 17 N closes the lid and 29 N pulls it straight off; the beams bend at most 1.0 %. The existing notch in the right-hand end opens it.
- **The lid never touches the board or the glass:** the plate is 0.3 mm thinner over the glass (0.8 mm clear with 4 mm standoffs, 1.8 mm with 3 mm), and the pads stop 0.5 mm short of the PCB, holding it off the glass only while the case is being closed.
- **Back edge rounding 4.5 → 0.8 mm** (the front stays 4.5 mm), so the recesses keep about 1 mm of wall at the corners. You agreed to 2 mm; with the 6.2 mm recesses the holes need for the uncertain standoff positions, 2 mm left 0.3 mm.
- **USB-C and microSD openings 1 mm taller toward the back**, so plugs and cards fit with 3 or 4 mm standoffs.
- **Battery wire route** moved 0.4 mm away from the bottom-left post; the bottom guide bar is no longer broken by a screw block.

**Checks updated for the change** (they described the old closure, not mistakes in it): `verify.py` and rounds 1–11, 17, 22, 23, 31 and 34 now test the corner screws, the posts, the clips, the pad and glass gaps and both standoff heights instead of the side screws and the foam. Where a rigid-fit check compared the lid and the cover, the clip hooks are left out: they bend, and press the lid by their designed preload.

## Round 35: different methods (the new closure)
**New methods:**
- **Standoff positions measured in your back photo:** the board's left, right and top edges fitted as straight lines on clean stretches, the bottom edge from the 60 mm height; the brass rings fitted as circles; the ruler's 10 mm dots (it lies on the standoffs) give how much nearer the camera their tops are, and their image is pulled back by that much before it is mapped onto the board. With the point under the camera anywhere within 150 px of the photo's centre, every estimate (and Waveshare's) must be within 0.45 mm of `POSTS`, and for each one the board must have a place where all four screws pass their holes.
- **The clips read back from the STLs:** each slot open along its length, each beam anchored at both ends, each hook reaching `CLIP_UNDERCUT` past the lid's wall into a deeper groove, and the closed hooks pressing the lid by exactly the designed preload (worked out by hand: 4 x 0.1 x 0.55 x 6 mm³).
- **The clips and the screw recesses as sliced:** in PrusaSlicer's G-code, no plastic in the slot layers inside a beam, each beam and each recess ceiling starting as a bridge, and no plastic in any screw's path.

**Mistakes found and fixed (design), by the new methods and by every earlier round run on the new design:**
- **The screw recesses' ceilings printed over air.** Printed face down, each 6 mm recess has the post above it, with the 3.4 mm hole through it: a ring-shaped bridge with nothing to anchor its inner edge (round 2's overhang check). The first 0.2 mm over each recess is now a slot across it (two straight bridges ending on the recess wall), the next 0.2 mm a square, and only then the round hole. The slicer prints both as bridges (round 35).
- **The pads could touch the board.** At 0.15 mm layers the slicer rounds the lid's rim, the pad tops, the cover's rim and the post ends so that the board ends up 0.15 mm nearer the pads and the pads 0.05 mm taller: with a 0.16 mm thicker PCB and 0.1 mm taller standoffs they would press it by 0.16 mm (round 23). The pads now stop 0.5 mm short (was 0.3), and the plate is 0.3 mm thinner over the glass (was 0.2), so the glass is 0.8 mm clear and still 0.3 mm off the lid while the board rests on the pads.
- **The posts could touch the lid's inside corners.** With the lid printed 0.15 mm small and the cover 0.15 mm large, errors in x and y add up along the corners' diagonal to more than the 0.35 mm gap (round 3). The posts' outer corners are now rounded 3 mm (the lid's 2.3 mm), 0.8 mm off them along the diagonal.
- **The lid's rim above the USB-C opening was 1 mm thin** where the hooks' lead-in chamfer ran (round 8). The chamfer now runs only along the long walls.
- **The README overstated how well the standoff estimates agree** ("most within 0.3 mm"; they are within 0.43). It now gives the ranges round 35 measures and says the board can sit with no screw more than 0.3 mm off centre.

**Checks updated:** round 2's Monte Carlo now lets the lid follow the board on its skirt (0.35 mm) when the screws put the board off centre; round 23 tells the USB-C from the microSD opening by height (they are now the same width at the height it looked at) and no longer counts the two left corner screw holes as microphone holes; round 31 counts the numbers new since session 4's README; rounds 3, 6 and 8 leave out a box just round each hook (subtracting the hooks themselves left float-rounding slivers that a projection turned into columns); round 8 sections each part on its own (the lid and the cover share points along the seam).

## Round 36: different methods
**New methods:**
- **The lid closing, step by step, on the meshes:** from 3 mm short of closed to closed in 0.05 mm steps, the least each hook must bend to clear the lid, found by bisection. It must stay within `CLIP_UNDERCUT`, never rise faster than 1 mm per mm of travel, and end at the designed preload.
- **The same with print errors:** the lid 0.15 mm small inside and the cover 0.15 mm large outside on each side, and the other way round.
- **The wires with 3 mm standoffs:** the board and the wires lying on it 1 mm further back, against the bottom of your battery.

**Mistake found and fixed (design):**
- **The clips could crack, or barely hold.** With the errors the way PLA usually errs (the lid's inside a little small, the cover's outside a little large), the 22 mm beams bent 0.75 mm while the lid closed: 2.2 % strain, about where printed PLA yields. The other way round, the hooks reached only 0.15 mm past the lid's wall. The beams were made longer (27 mm, and 28 mm since round 38) and the hooks 0.55 mm deep (their front is steeper, 55°, so they still fit on the beam; the lid's 30° rim chamfer does the leading). With 28 mm beams and those print errors the hooks bend it up to 1.56 % while closing, and the other way round they still reach 0.25 mm past the wall. About 17 N closes the lid, 29 N pulls it off.

**Results:** the wires, with 3 mm standoffs, still clear your 4.3 mm battery by 0.30 mm (battery wire) and 0.45 mm (speaker cable); a swollen 4.8 mm cell would press them 0.20 and 0.05 mm.

## Round 37: different methods
**New methods:**
- **The log's own numbers, recomputed:** every figure this session's entries give for the new closure is found by its wording and recomputed from `case.py` or from the check that measures it.
- **Mistakes a person could make while assembling,** each answered in the README and both guides: 16 of them, from the battery in the wrong connector to screws of the wrong length and how to open the lid.
- **Markdown that renders:** bold and code marks in pairs, tables square, links with targets.

## Round 38: different methods
**New methods:**
- **Can the session-5 checks fail?** In a copy of the project, six deliberate mistakes are made in `case.py` one at a time: a post 0.8 mm off its standoff, the clip slots closed, hooks reaching only 0.1 mm, 1.0 mm deep recesses, pads touching the PCB, posts built for 6 mm standoffs. The check meant to catch each must report a problem.
- **Margins against small changes:** each new dimension moved 0.1 mm either way (hole and recess: their diameter); every session-5 margin must stay at or above its limit.

**Mistakes found and fixed (design):**
- **Three margins sat on their limit.** A 5 mm head 0.37 mm off centre had 0.025 mm to spare in the 6.0 mm recess, and a 0.1 mm deeper hook would have taken the clips over 1.8 % with print errors. The recesses are now 6.2 mm, the back edge is rounded 0.8 mm (so the corner wall stays 1.0 mm), and the beams are 28 mm (the figures above are for those).

**Result of round 38 (all scripts, rounds 1–38, on the final geometry):** 381 checks passed, the same 4 SKIPPED. **Not clean:** besides round 38's own find above, the README still gave the lid as about 9 cm³; with the plate thinner over the glass it is about 8 cm³ (round 16). Corrected.

**Check bugs:**
- Round 38's first mistake (a post 0.8 mm off) was sent to `verify.py`, which cannot see it: moving `POSTS` moves the modelled standoffs with the holes. Only the photo measurement can, so it now goes to round 35, which catches it.
- Round 31 had no rule for "27" once the clips stopped being 27 mm: it is now the PLA estimate, which round 19 checks against the slicer.
- Round 20: rounds 38–40 were not yet in `checks/run_all.sh`.

## Round 39: different methods
**New methods:**
- **The assembly in the guides' order, on the meshes,** with 4 mm and with 3 mm standoffs. The board is lowered face down into the lid until it rests on its pads; the glass must then be clear of the lid. With the cover clicked on, the posts must not reach the standoffs yet. Each screw, dropped through its hole onto its standoff, must catch at least one M2.5 thread (0.45 mm) before its head seats, then pull the board back off the pads until the standoff meets the post, ending 2 mm in.
- **The lid as sliced:** in PrusaSlicer's G-code, no plastic inside the grooves over the layers they span, the lip printed above each, and the plate over the glass at its designed thickness.

## Round 40: different methods
**New methods:**
- **The forces from the meshes:** round 36's bend curves (how far each hook is bent at each point of the lid's travel, found on the STLs) times the beams' stiffness, with the curve's slope as the angle the lid presses at. The peak push and the pull-off must match the README within 25 %.
- **The same word for the same part** in the README and both guides: no "front shell", foam or pilot left outside file names; "преден капак", "втулки", "стълбчета" and "щипки" in Bulgarian, with no second name for any of them.
- **Lying on its back:** the back face is the lowest plane, and a 1.8 mm head sits inside it.

## Round 41: different methods
**New methods:**
- **`case.py`'s own comments, recomputed:** every number the comments beside the new constants state (how far the glass floats, how far a screw goes in, the holes' and the recesses' room, the posts' clearance along the corners' diagonal, what the clip length and undercut leave with print errors) is recomputed from the code.
- **Heat and cold:** PLA grows about 68 µm per metre per degree, the board's glass-epoxy about 15. From 0 to 50 °C, the mismatch over the board's length must stay inside its 0.3 mm side clearance, each screw's shift inside its hole's play after round 35's worst offset, and the clips' preload must not vanish.

**Not clean:** reading the README back against the checks found two of its sentences wrong. It said 0.3 mm layers are too coarse because the slicer rounds the glass clearance faces too far; the real reason is the hooks, which are under 1 mm tall, so their 45° faces would print as three coarse steps. It also gave the full check run as about 15 minutes when it takes about 25. Both are corrected.

## Round 42: different methods
**New methods:**
- **Opening at the notch, as a tilt:** with the cover held, the lid is turned open about its left end at the seam in 0.25° steps up to 8°. Nothing rigid may run into the cover, and the hooks must let go one after another from the right-hand end.
- **The closing curve worked out by hand:** the bend each hook needs at each point of the lid's travel is written as a formula from the design's own numbers: the rim chamfer, the hook's faces and the preload. It must match round 36's mesh measurement to within 0.03 mm everywhere.

## Round 43: different methods
**New methods:**
- **Every new number in both guides accounted for:** each number in the English and Bulgarian texts that was not in session 4's is traced to `case.py`, a check or a measurement.
- **The zip as you will open it:** it is unpacked into an empty folder. Both STLs must load as single watertight parts of the right size, every picture must open, both PDFs must have all their pages and step headings, and the README's pictures must be found inside the zip.

## Round 44: your front photos (new methods)
You sent four photos of the board's front against the ruler. **New methods** (`checks/round44.py`, photo 14 cropped into `checks/owner_photos/front_long.jpg`):
- **A ruler that is not the same scale all along:** the camera was tilted, so the ruler reads 16.0 px/mm at the board's left end and 15.5 at the right. Positions are read on a smooth curve through its own cm and half-cm ticks (all within 0.28 mm of it; the 50 mm tick is left out, because the big circled 5 printed over it moves the found tick 0.5 mm).
- **The light field and the text:** along a clean line through the display the light field runs from 8.0 to 95.2 mm from the left end, and the text the firmware centres on the screen is centred at 51.3 mm.

**Mistake found and fixed (design):** Waveshare's drawing puts the picture at 9.3–95.7 mm (centre 52.5), and the window started at 8.4 mm. If the text is centred on the picture, the picture is at about 8.1–94.5 mm, and the window's left edge could have hidden up to 0.3 mm of it, more with the board's 0.3 mm of side play. The window now starts at 7.7 mm (88.7 mm wide, its right edge unchanged at 96.4 mm), and covers the drawing's picture area, the light field and the text-centred picture. The panel-tail relief under the plate now stops at 6.9 mm (6.8 since round 45), so 0.9 mm of plate stays between it and the window. The left frame is 10.4 mm wide (was 11.1). `preview/explained.png` is now built by `docs/guide-src/make_explained.py`, with a to-scale diagram instead of Waveshare's photo (their site is blocked here), and without the old side screws.

## Round 45: different methods
**New methods** (`checks/round45.py`):
- **Your two photos across the board** (photos 11 and 12, cropped into `checks/owner_photos/front_across_a.jpg` and `front_across_b.jpg`): round 44 measured the light field along the board; this measures it across. The board's own 60 mm is the scale, between the two long edges of the blue PCB. On each side the light field ends at a thin dark line, with about 0.9 mm of lighter glass border and the glass's bright edge beyond it. The text on the screen tells which way up the board lies (its tops point to the photo's left, so the top edge is on the left). The glass being nearer the camera than the PCB is left out, which makes the field look slightly larger, the safe way round.
- **The window's corners:** the corners of the drawing's picture area and of the light field from both directions must lie inside the window's rounded corners too, not just between its straight edges, which is all rounds 2 and 44 looked at.
- **How hard the screws may be tightened:** the plastic each screw clamps is measured on the back cover's STL. Under the head, the recess floor's first layer is two bridged segments with the 3.4 mm slot between them (round 35's bridging), so a head presses only outside the slot. At the post's end, the plastic presses on the ring of the standoff's top outside the hole, with the screw up to 0.29 mm off centre. Fingertip-tight (0.05 N m, about 100 N of pull) must stay under 30 MPa on the plastic. Printed PLA yields at about 50 MPa and creeps above about half that.
- **The window as sliced:** in PrusaSlicer's G-code for the lid (face down, mirrored for print), the opening's four edges on four layers, two in the 45° chamfer and two below it, must sit where `case.py` puts them, within 0.1 mm. They are within 0.01 mm, and the 10.4 mm frame is on the USB-C end.

**Mistakes found and fixed (design):**
- **The window could hide the bottom of the light field.** Across the board, the light field runs y 3.04–56.36 mm (photo 11) and 3.18–56.42 mm (photo 12), and the window started at y 3.4. The window now runs y 2.9–57.0 (88.7 x 54.1 mm), so the bottom frame is 5.6 mm, like the top's 5.7.
- **The window's 1 mm round corners clipped the light field's bottom-left corner by 0.11 mm** (inactive border, not pixels). The corners are now 0.5 mm round, and every corner of the light field is inside the window.
- **The plate between the panel-tail relief and the window was exactly at round 4's 0.8 mm limit** after round 44 widened the window, and float rounding made the check fail. The relief now stops at x 6.8, which leaves 0.9 mm.

- **The README and the guides offered screw heads that would squash the plastic.** They allowed pan, cheese or button heads up to 5.0 mm. A 5.0 mm pan head (or the 5 mm washer with M2 screws) presses on 4.1 mm² of plastic: 25 MPa fingertip-tight, and it starts to yield at about 0.10 N m. A 4.7 mm button head presses on 2.9 mm² (34 MPa) and a 4.5 mm cheese head on 2.2 mm² (45 MPa). Both are over the limit even fingertip-tight. The README and both guides now ask for ISO 7045 pan heads only, warn off cheese and button heads, and say to tighten with a small screwdriver turned by the fingertips until the head is snug. The posts' ends are fine: 16 MPa on a 4.5 mm round standoff and 22 MPa on a 4 mm hex one.

- **The display lip over the PWR/BOOT opening became too weak** when the window's lower edge moved 0.5 mm toward it (round 5: 30.5 MPa at 10 N, allow 30). Its section measured on the STL is weaker still, 31 MPa, because the front edge's rounding thins it. The lid's ledge pad at the bottom right (x 86–94) now runs along the whole opening (x 66–94), still 0.5 mm in front of the PCB: the lip's weakest section now takes 19.9 MPa.

- **Both guides overstated how well the standoff positions are known.** Their tip said "within about 0.3 mm", the same overstatement round 35 corrected in the README: the estimates differ by up to 0.7 mm, and 0.3 mm is how far off centre a screw can end up. They now say so (found by reading the rebuilt PDFs).

**Check bugs:**
- Round 5 took the lip as a 3.7 x 1.3 mm rectangle. It now measures the lip's real section on the STL every 0.5 mm along the opening. Its screw-head estimate now uses the 5.0 mm head the README asks for, instead of a 4.7 mm one.
- Round 2 measured the window's margins round an active area it assumed was centred in the window. The window has not been centred on the picture since round 44, so it now uses the drawing's active area (x 9.3–95.7, y 4.1–55.9).

**Independent review** (a separate agent read the whole project after round 45, as you asked). Each finding was checked before anything was changed:
- **The screw heads would have stood proud.** The recess was 1.8 mm deep, but M2.5 pan heads can be 2.0 mm tall (DIN 7985; ISO 7045's are a little lower). Worse, PrusaSlicer's default "thick bridges" prints the recess ceiling 0.2 mm lower, so as sliced the recess was 1.6 mm deep. The recess is now 2.4 mm deep (0.6 mm into the post): a 2.0 mm head sits 0.4 mm inside the back face, 0.2 mm with thick bridges. The README and the guides now ask for ISO 7045 or DIN 7985 pan heads up to 2.0 mm tall. An 8 mm screw now goes 2.6 mm into the standoff. With 3 mm standoffs its tip stops 0.4 mm short of the PCB, which is more than an 8 mm screw's length tolerance (±0.29 mm, ISO 4759-1). Round 4 and `verify.py` asked for 0.5 and 0.9 mm there, which the shallower recess happened to leave; they now ask for 0.3 mm.
- **The clip slots printed with less air than designed.** With thick bridges the beam's first strands hang 0.2 mm low, and the slot's floor lay on a layer boundary, so only 0.4 mm of the 0.6 mm slot was left as sliced. A beam fused to the cover at a few spots would not bend. Each slot now runs 0.3 mm into the cover's rim under its beam (inside the lid's wall, so it can't be seen), which leaves 0.8 mm of air as sliced.
- **The ESP32 module was in the wrong place in the board model.** It was modelled at x 81.5–99.5, y 14–40, with its antenna from x 93.5. In your back photo, mapped onto the board's plane as round 35 does (with the module's top 3.1 mm nearer the camera), the module runs x 73.2–99.1 including its pads and y 20.6–40.2 including the board's solder pads round it, and its shield can ends at x 92.9. The model now has the module at x 73.0–99.5, y 20.5–40.3, and the antenna from x 92.6. The speaker is 7.0 mm from the antenna (the README said 7.9). The spare-cable loop's right-hand side moved 1.1 mm left (the loop is 1 mm narrower and 1 mm taller), so it still keeps 5 mm from the antenna (5.3 mm) and is still about 77 mm long.
- **The assembly steps left two things to guesswork.** Step 2 didn't say where to put the lid before the cover is turned onto it like a page. It now says to lay the lid just in front of the cover, dial notch toward you, with the bottom edges together. Step 4 said "turn the case over", but after step 3 the back already faces you; it now says so. The guide's step 4 picture numbered the screws round the corners while the text said to tighten them in a cross pattern. The picture now numbers them in that order, and the text says to follow the numbers. Step 4 also says what to do if a screw spins without catching. With 3 mm standoffs the board lies 1.5 mm from the posts until the screws pull it up, and the screw's tip still reaches 1.1 mm into the standoff.
- **USB-C:** the README said cable plugs "seat fully". It now says which ones: moulded grips up to 13 mm wide and about 7 mm thick.
- **Clip forces:** the README's 17 N and 29 N are textbook figures for beams held rigidly at both ends. It now says that in three places the beams end on short stubs of skirt (2 mm, 2.3 mm and 2.4 mm), so those clips will hold somewhat less.
- **`preview/photo_overlay.png` was out of date.** It was drawn in an earlier session on Waveshare's product photos, which can't be downloaded here. It is removed; round 2 redraws it whenever it can download them.
- **The back cover's volume:** about 15 cm³ (15.4 in the STL), not 16.

**Check bugs:**
- Round 35's sliced check took each G-code line's middle point, so a long perimeter line through a short box (a clip slot, a screw hole) was missed. It now samples every line every 0.2 mm, and measures each line's nearest point to a screw's axis.
- Round 33 asked for 6 mm between the antenna and the speaker pocket's PLA brackets. Plastic that close doesn't matter: the back plate itself is PLA and lies right over the antenna. It now asks for 6 mm from the speaker, anywhere in its pocket.
- Rounds 29 and 31 still expected the README's screw wording and numbers from before round 45.

## Round 46: different methods
**New methods** (`checks/round46.py`):
- **Stiffness, not strength.** The display lip over the PWR/BOOT opening, as a bar clamped at both ends with its weakest section measured on the STL: 10 N on its middle bends it 0.075 mm, against the pads' 0.5 mm and the glass's 0.8 mm. The back plate, as a plate fixed along the walls (Roark, central load): 10 N in its middle bends it 0.16 mm, against 0.30 mm of room between your battery and its wire with 3 mm standoffs (it would touch at about 18 N, and only the battery would press on its own wire).
- **The lid's first layer on the bed:** cut from the STL just above the bed, it must be one closed ring round the window, at least 2 mm wide everywhere. It is 2.2 mm at its narrowest, 7.1 mm on the left.
- **Air under the bridges, as sliced,** with each extrusion's real height from the G-code: from the cover to the first strand over each clip slot (0.8 mm, want 0.5), and from the bed to the first strand where each screw head bears (2.2 mm, want 2.0, the tallest head allowed). This is the check that found the two thick-bridge problems above.
- **The clip beams' ends:** where the skirt is joined to the cover, along each long wall. The stubs each beam ends on are 2.0–7.0 mm, and the README must name the short ones.

**Not clean:** round 46's sliced check measured the two thick-bridge problems in the review's list (the recesses and the clip slots), and the full run after the fixes found four more things:
- **The screw tip's margin sat on its limit.** Round 38 moves every new dimension 0.1 mm either way. With the post printed 0.1 mm short, the tip came out 0.3 mm short of the PCB with 3 mm standoffs, exactly round 38's 0.3 mm limit. That limit counted the print error twice. It is now the physical one: the tip must stop short of the PCB by more than an 8 mm screw's length tolerance (±0.29 mm). In the worst case of all three at once (3 mm standoffs, a post 0.1 mm short and a screw 0.29 mm long) the tip still stops short, by 0.01 mm. With PrusaSlicer's default thick bridges, which seat the head 0.2 mm higher, it is 0.21 mm. This is what the deeper recess costs. A 2.2 mm recess would give 0.2 mm more here, but a 2.0 mm head would then sit exactly level with the back, with nothing to spare.
- Round 39 still expected the screw to end 2.0 mm into the standoff. It now expects the README's 2.6.
- Round 12 found the README still naming the removed `preview/photo_overlay.png`. It now just says that round 2 draws the overlay when it can download Waveshare's photos.
- Both guides said shorter screws "barely reach the thread". That is true for 6 mm, but a 7 mm screw now catches about 3 turns. They now say shorter screws catch too little of the thread.

## Round 47: different methods
**New methods** (`checks/round47.py`):
- **Steps 2 and 3 done to the STLs.** The lid's dial notch, the cover's tab and both parts' USB-C ends are found on the meshes, not taken from `case.py`. The parts are laid out as step 2 says (cover inside up, tab away from you; lid in front of it, notch toward you, bottom edges together), and the cover is turned like a page about the shared edge and lowered. It lands 0.0000 mm from its assembled place, overlapping the lid by exactly the hooks' 1.30 mm³ of preload. With the lid laid the other way round (notch away), the same turn puts the cover 104.9 mm off.
- **The wires with the case open.** Step 2 plugs both wires in with the board face down in the lid and the cover lying open in front of it. The shortest path for each wire over both parts' walls and the shared edge, unrolled flat: the battery wire needs 41 of its 54 mm, the speaker cable 41 of its 101 mm (want 5 mm to spare).
- **The connectors from your back photo,** mapped onto the board's plane as round 35 does, with each housing's edges refined on the image's brightness gradient.

**Not clean:** the photo showed the board model's connectors in the wrong place. They were modelled 2.2 mm nearer the bottom edge than they are (y 0.5–5 instead of 2.7–7.8), and the SPK header wasn't modelled at all; the plugs in BAT and SPK reach y 8.6. The board model now has all three headers from the photo, 0.1 mm or more larger all round, and the plugs in BAT and SPK. The wire routes now run just past the plugs' faces and end there: about 34 mm for the battery wire (was 38) and 27 mm for the speaker cable (was 30). The battery wire has about 20 mm to spare (was 16). The README and both guides now give these lengths. Nothing in the case had to change: the routes still clear every post, the battery and the speaker (round 13), the voxel search still finds them (round 31), and the spare-cable loop keeps 5 mm from the antenna (round 33).

## Round 48: different methods
**New methods** (`checks/round48.py`):
- **The two guides side by side.** Rounds 37 and 43 compared each guide with the README and the log. This compares the two guides with each other: all 39 texts exist in both languages, the 115 numbers in the English texts appear in the same order in their Bulgarian twins (decimal commas read as points), and each Bulgarian text has as many bold phrases as its English twin.
- **First-layer squish ("elephant's foot").** Unless the slicer compensates for it, the first layer on the bed often spreads 0.1–0.2 mm sideways. Each part's first layer was cut from its STL and every opening in it shrunk by 0.2 mm all round. All 12 openings in the back cover's first layer (the speaker slots, the microphone and sensor holes, the four recesses) and the lid's window are still open and at least 0.4 mm wide, and each recess still takes a 5.0 mm head with 0.3 mm to spare.
- **A read-through of the README and of both guides,** the Bulgarian text against the English line by line, and a search of all the English text for words used once that are one letter away from a word used more often (a cheap typo finder: it found none).

**Not clean:** the read-through found two wording problems in the Bulgarian guide.
- The buy list said not to use "цилиндрични или плоски глави" ("cheese or flat heads") where the English says cheese or button heads. "Flat head" usually means a countersunk screw, which is wrong too, but the button heads it should warn against weren't named. It now says "цилиндрични или полусферични (бутонни) глави". Round 45 looks for this warning and now looks for the new wording.
- The printing list called supports "поддръжки"; the buy list calls them "подпори". Both now say "подпори".

A method dropped: I first wrote a check of what the screw heads press on, measured on the STL. Round 45 already does that, so it isn't in round 48. Its numbers agreed with round 45's: a 5.0 mm head bears on 4.1 mm² of the recess's first layer, a 4.5 mm head on 2.2 mm².

## Round 49: different methods
**New methods** (`checks/round49.py`):
- **The window with the board anywhere it can sit.** Rounds 2, 44 and 45 put the board in the middle of the lid. But it lies loose in the lid until the screws hold it, and the lid's walls let it sit up to 0.3 mm off centre either way (the screw holes allow more, so the walls are the limit). The board was put in all nine positions (each wall, each corner, the middle), and the window must still clear the light field in your photos and the drawing's picture area by 0.1 mm on every side, and still hide the panel's tail strip.
- **The lid's first layer, its true width.** Round 46 measured the band of the lid's front face on the bed along lines from the window's centre. At the corners those lines cross the band at a slant and read it wider than it is. Here the width is the distance from each of 6000 points on the band's inner edge to the nearest point of its outer edge.
- **The download zip, file by file:** every file in it must be byte for byte the project's, and it must hold everything the README's Files table promises and every picture the README shows.
- **The pads and the glass with the board anywhere it can sit.** The pads in front of the PCB's rim reach deeper than the glass's front face, so with the board 0.3 mm toward each wall the glass must still keep clear of them, by more than the 0.3 mm its outline may be off in the photo it was measured on.
- **Every picture in the README and the guides, looked at** after rounds 47–49 changed the connectors and the window.

**Not clean:**
- **The window could hide the edge of the picture.** With the board pushed fully toward the bottom wall, the window's bottom edge would have covered up to 0.16 mm of the light field (about 1.5 rows of pixels), because the window cleared the field there by only 0.14 mm with the board in the middle. On the left the margin would have come down to 0.0. The window is now 0.3 mm deeper at the bottom (it runs from y 2.6) and 0.2 mm wider on the left (from x 7.5): 88.9 x 54.4 mm. Wherever the board sits, it clears the light field by at least 0.14 mm (0.14 bottom, 0.20 left, 0.28 top, 0.90 right). On those two edges the outside chamfer is narrower (0.5 and 0.6 mm instead of 0.8, so a little steeper than 45°). That leaves the frame's front face, and so its first layer on the bed, where it was. Simply moving the window edges would have narrowed the first layer to 1.88 mm at the bottom-right corner. The display lip over the PWR/BOOT opening is a little narrower: round 46's stiffness check is in the next full run. The left end of the frame is now 10.2 mm wide.
- **Round 46 overstated the first layer's narrowest width.** It is 2.04 mm, at the bottom-right corner of the window, not 2.2. The new window makes it 2.01 mm there (the chamfer's corner is pulled 0.3 mm down), still at least 2.0 everywhere; along the sides it is 2.24 mm or more.
- Round 43 found the guides' new battery wire length (34 mm) not traced to anything. It now traces both route lengths to `case.py`'s routes.
- **The right-hand pads could have touched the glass.** The glass ends only 1.0 mm in from the PCB's right edge, and the two pads on that edge reached 0.5 mm in from it. With the board 0.3 mm to the right they were 0.2 mm from the glass, less than the outline's possible measuring error, and the glass would then rest on a pad instead of the PCB. Round 2's random boards didn't find it, because they use the glass outline as measured. These two pads now reach 0.3 mm under the PCB: they keep 0.4 mm from the glass. When the board sits to the left they hardly touch the PCB, which is fine: the pads along the top and bottom edges hold the board on their own.
- **The board model still had the old SPK header.** Round 47's edit replaced the BAT and RTC boxes but left the old SPK box (x 52.5–61.5, y 0.5–5.0) beside the new one. It is removed. It was only in the board model: the case didn't change. Round 47's entry above is wrong to say SPK wasn't modelled at all: it was, in the wrong place.
- **The README said "the battery wire runs under the battery".** In step 2 the cover lies inside up, so "under" reads as beneath the cell, between it and the cover. There is no room there: a 2.5 mm wire under the cell would push it into the board. In the guide's step 2 picture the wire lies across the battery's bottom edge, on the board's side of it, which is where it goes. The README now says so.
- The first full run after round 47 also found no log entry for round 48. The entry was written while the run was going.

## Round 50: different methods
**New methods** (`checks/round50.py`):
- **Pressing on the display.** The window leaves the glass open, so a finger can press the board straight back. The board's bending under a firm 10 N press in the middle was estimated as a beam across the 94.6 mm between the standoffs (FR-4, 1.6 mm, half the board's width counted, and the glass bonded to it left out, which only stiffens it): about 0.96 mm. Behind the board the models leave 2.0 mm (4 mm standoffs) and 1.0 mm (3 mm standoffs) from the BAT and SPK plugs to the battery, so a board part reaches the battery only at about 21 N and 10 N. The battery wire, which lies on the microSD socket and across the battery's bottom edge, is squeezed against the battery sooner (from about 1 N with 3 mm standoffs), which a soft wire doesn't mind. Beyond that the battery, taped to the back, takes the load.
- **A read-through of the log from round 45 on, as a whole,** for figures a later round changed and no later entry corrects. Round 45's window (88.7 x 54.1 mm, from y 2.9), round 46's 2.2 mm first-layer band and round 47's "SPK wasn't modelled" are all corrected in round 49's entry.

**Not clean:** the full run found four things.
- **Round 49's wider window thinned a web.** Round 4 wants the strip of plate between the panel-tail relief and the window to be at least 0.8 mm wide (two extrusion lines). After round 49 moved the window's left edge to x 7.5 it was 0.70 mm (0.9 before). The window now starts at x 7.6 (88.8 x 54.4 mm), and the relief ends 0.05 mm sooner, at x 6.75, so the web is 0.85 mm. With the board pushed 0.3 mm to the left, the window clears the light field by 0.10 mm there, so the README now says "at least 0.1 mm", not round 49's 0.14 (bottom 0.14, top 0.28, right 0.90 as before). The left end of the frame is 10.3 mm wide. The display lip over the PWR/BOOT opening now bends 0.077 mm under 10 N (0.075 before round 49).
- Round 17's mutation test of the README's advice still looked for the old window constants. It now edits the new ones.
- Round 20 found rounds 49 and 50 missing from `checks/run_all.sh`. They are in it now, with round 51.
- Round 31 found the README's new "0.14 mm" not traced to anything. The README now gives 0.1 mm, which is.

## Round 51: different methods
**New methods** (`checks/round51.py`):
- **Where the clip beams go while the lid closes.** Round 36 found how far each hook must bend inward to pass the lid's rim, not what the bending beam could hit. Each beam bends like a beam fixed at both ends with a load in the middle, up to 1.2 mm at the hook with print errors the worst way round. The space its inner face sweeps was cut into 0.5 mm slices and compared with every part inside: the board's parts (4 mm and 3 mm standoffs), both wires, the spare-cable loop, the battery and the speaker. The nearest is 0.5 mm away (the BAT and SPK plugs, with 3 mm standoffs; want 0.3).
- **The buy list, item by item:** each of the 7 rows in the guide's buy table, with its quantity and every number in it, must also be in the README. They all are.
- **A read-through of the README passages rounds 49 and 50 changed** (the window, the battery wire).
- **The case as it will be used** (by me, not a script): lying on its back on a desk, lying face down, standing on each edge, held in a hand, with the USB-C cable in. What each does to the speaker, the vents, the buttons, the dial and the display.

The full run (48 rounds) found no problems.

**Not clean:** the in-use look found one thing the README didn't say. The speaker's only way out is the slots in the back, so with the case lying on its back on a table they face the table and it sounds muffled. The README's speaker paragraph and both guides' tips now say so: stand it up, or lay it face down, to hear it. The rest is fine: face down, the glass sits about 2.1 mm back from the front face, so it doesn't touch the table; standing on its bottom edge, the buttons are 1.95 mm inside the wall, so its weight doesn't press them; the microphone and the sensor breathe through the side vents, which stay open in every position; the USB-C plug comes out of the middle of the left end, so with the cable in the case can lie on its back or face or stand on its bottom edge, just not on that end.

## Round 52: different methods
**New methods** (`checks/round52.py`):
- **The window, statistically.** Round 49 put the board in its nine worst positions, with everything else at its measured value. Here 200 000 builds were drawn at random. Each one has the board anywhere in its play, the lid shrinking 0.2–0.4 % as it cools (that pulls the walls in, so the board has less play, but it pulls the window's edges in too), each edge of the light field off by its measuring error (0.1 mm standard deviation: your two photos across the board agree within 0.14 mm), and each window edge off by the printer's error (0.05 mm). In 0.39 % of builds the frame hides a whole row or column of pixels (0.108 mm) on some side (left 0.27 %, bottom 0.11 %, never right or top; want under 1 %). In 3.8 % it covers any sliver at all.
- **The README's window numbers recomputed from the lid's STL,** not from `case.py`: a cut through the lid behind the chamfer gives a window from x 7.60 to 96.40 and y 2.60 to 57.00 (88.8 x 54.4 mm) and a 10.3 mm left frame, as the README says.
- **Every text of the guides reaches the PDF.** Round 43 looked for the headings. Here all 123 texts of each guide (every sentence, table cell, legend line and tip, round 51's new tip among them) must be in the PDF's text. They all are. (The check reads the PDF in its own order, `pdftotext -raw`: in reading order, the buy table's columns interleave. It ignores hyphens, because pdftotext joins a word broken after one.)
- **The guide pages as Chromium lays them out for print** (A4 less the guides' margins): no line of text may stick out of its box (a table cell, a note, a legend line) or the page, every picture must load, and no two numbered markers on a picture may touch.

**Not clean:** in step 2's picture, marker 6 (where the battery wire leaves the cell) touched marker 3 on the bottom-left post: their centres were 22.8 px apart and the circles are 23.4 px across. Both numbers could still be read, but the two looked like one blob. Marker 6 now sits 5 mm along the wire, on the wire's red run beside the cell's taped end, clear of marker 3. Round 29 still finds it on the battery wire. Everything else passed: all 301 (EN) and 328 (BG) lines inside their boxes, all 8 pictures loaded, the other markers apart.

The full run with round 52 (run 7: 35 rounds run, 14 unchanged since they passed) found no problems.

## Round 53: different methods
**New methods** (`checks/round53.py`):
- **Standing it up.** Round 51 told you to stand the case up to hear the speaker. Here the closed case was put on a table on each of its six faces. The centre of mass comes from the parts: both printed parts from their STLs (PLA), the board's parts from the board model, the battery (a pouch cell, tried from 1.8 to 2.4 g/cm³) and the speaker. The whole device is about 97 g, and its centre of mass is 8.7 mm behind the front face (8.5–8.8 with the battery's weight anywhere in that range). On its bottom edge it tips over only past 8.3° forward and 13.0° back (a phone on its edge tips at about 2°), and the nearest board part, the buttons, stays 1.95 mm in from the table. Lying on its back, the screw heads are 0.4 mm in; lying face down, the nearest board part is 2.1 mm in. The two short ends tip at about 5°.
- **The window from 0 to 50 °C.** Round 41 checked the clearances in heat and cold, round 49 the window with the board anywhere in its play at room temperature. Once screwed in, the board stays where it was put, while the window, in PLA, grows and shrinks about the lid's middle more than the board does. With the board in each of round 49's nine positions, the window still hides nothing of the light field: at 0 °C the narrowest margin is 0.05 mm (left), at 50 °C 0.17 mm. With round 52's random builds, a whole row or column of pixels is hidden in 0.60 % of builds at 10 °C and 0.98 % at 0 °C (0.39 % at 20 °C; want under 1 % at 10 °C).
- **The guides on paper:** every picture in the two PDFs has at least 155 pixels per inch at its printed size (the step 2 picture; want 150).

**Not clean:** on its top edge the case would rest on the dial. The wheel's rim is only 0.09 mm in from the top face, and the board can sit up to 0.3 mm nearer that edge. Round 51's advice just said "stand it up". The README and both guides now say to stand it on its bottom edge, not its top edge, where the dial is. The README also gives the angles it tips over at. Round 11's table test had found the dial 0.09 mm off the table and passed it, with the board in the middle of its play. It now allows for the play on every edge, and for the top edge it asks the README to warn.

The full run with round 53 (run 8: 36 rounds run, 14 unchanged since they passed) found no problems.

## Round 54: different methods
**New methods** (`checks/round54.py`):
- **Can the newest checks fail?** Rounds 33 and 38 made deliberate mistakes to see that the checks of their time catch them. The checks added in rounds 44–53 had not been tried that way. In a copy of the project, 16 mistakes were made one at a time, and the check that should catch each was run on the copy. First, as a control, all 15 of those checks were run on the unchanged copy, where they must pass.
  - In `case.py`: the window's left edge 0.06 mm further in (caught by rounds 49 and 53) and 0.15 mm further in (round 52's random builds: 5.2 % of builds then hide a pixel column); the right-hand pads back to 0.5 mm under the PCB (round 49); the bottom chamfer back to 0.8 mm (round 49's first-layer band, 1.77 mm); the buttons standing 2.5 mm out of the board (rounds 11 and 53); 2.4 mm standoffs as the shortest (round 50); the headers 1 mm taller (round 51's clip beams).
  - In the README: the speaker advice back to "stand it up" (round 53); the top-edge warning gone (round 11); the window 88.9 mm wide (round 52); ISO 7046 for 7045 (round 51); the README changed after the zip was made (round 49).
  - In the guides: a text the PDF lacks (round 52); two markers on top of each other, and an unbreakable word in a table cell (round 52's layout check); the pictures at 100 ppi (round 53).

  All 16 are caught. Five catches are also checked for their reason: the FAIL line must name the right thing.
- **Page breaks in the guides:** in both PDFs no heading may end a page, and every picture's legend must be whole and on the picture's page. None ends a page, and all 7 legends are on their picture's page. The check catches a heading added at the foot of a page and the step 2 picture moved to the next page.

While writing round 54 I found a fault in the round itself, not in the case. The copies were run with Python's compiled-file cache on. A mistake and the restore that follows it can leave `case.py` the same size and with the same second's timestamp, so Python reused the previous mistake's compiled `case.py`. The "headers 1 mm taller" run was then really caught by the 2.4 mm standoffs before it. The copies now run without the cache, and that catch must name the connectors with 3 mm standoffs, which it does. Round 38 makes the same kind of edits, but each of its checks runs for many seconds, so its timestamps always differ.

The full run with round 54 (run 9: 11 rounds run, 40 unchanged since they passed) found no problems: round 54 is clean.

## Round 55: different methods
**New methods** (`checks/round55.py`):
- **Put together the wrong way round.** Round 37 checked that the documents answer the mistakes a person could make. Here the parts themselves were tried. Each wrong way overlaps the lid by far more than 1 mm³, so none can sit flat or close without you noticing:
  - the board turned round in its plane, display still down and the dial at the bottom: 43 mm³, mostly the dial against the bottom wall;
  - the board turned over about either axis: 275 and 352 mm³;
  - the back cover turned round, tab at the bottom: 94 mm³.

  As a control, the right way round overlaps nothing.
- **The guides' finished pages, looked at** (by me, not a script): all 7 pages of each PDF, as they print. The steps, pictures, markers and legends line up; the new speaker tip is on page 7 in both; the Cyrillic text, its "ѝ" included, renders in the guide's font. Pages 3, 5 and 6 end with white space, because each step is kept whole on one page, as intended.
- **A read-through of the log's entries for rounds 51–54 as a whole,** for figures a later round changed and no later entry corrects.

**Not clean:** the read-through found one such figure. Round 52's entry says the Bulgarian guide has 328 lines of text. Round 53's longer speaker tip made it 329, and round 53's entry doesn't say so. It is corrected here: the English guide has 301 lines and the Bulgarian 329, all inside their boxes. Nothing else in those entries was changed later without a correction.

The full run with round 55 (run 10: 11 rounds run, 41 unchanged since they passed) found no problems.

## Round 56: different methods
**New methods** (`checks/round56.py`):
- **The project with its history, as you will get it.** The last commit was packed the way the delivery zip is, as a `git archive` of the commit and a `git bundle` of the whole history (49 MB). It was unpacked into an empty folder, and the bundle was cloned into another one, as the zip's HOW-TO-USE.txt says. The clone checks out this branch at this commit, with all 40 commits. Its 98 files are byte for byte the archive's, and `verify.py` passes in it.
- **No dead constants:** each of the 94 named constants at the top of `case.py` is used, 85 by its own code and the other 9 by the checks or the guide scripts, so none would mislead whoever edits them.
- **The README's Files table, the other way round:** round 12 checks that every file it names exists. Here every file and folder in the project is named in it, apart from the README itself and the tools' own settings (`.claude/`, `.gitignore`). While writing this check, it first flagged the README itself, which a Files table needn't list: that was a fault in the check, fixed before it ran.

Round 56 found nothing.

The full run with round 56 (run 11: 12 rounds run, 41 unchanged since they passed) found no problems: round 56 is clean.

## Round 57: different methods
**New methods** (`checks/round57.py`):
- **Spelling, by a spell checker** (pyspellchecker's English word list): every word of the README, of the English guide and of the log's session-5 entries that the list doesn't know must be one of a short list of exceptions (British spellings such as centre and colour, units, names). One spelling must hold throughout: no word in both its British and its American form.
- **The checks give the same answer twice:** rounds 52, 53 and 55 (random numbers, Chromium's layout, the meshes' booleans) are each run twice, and their output must be the same word for word.
- **Enough random builds:** rounds 52 and 53 count rare events in 200 000 random builds. Each count must lie at least 5 standard errors under its 1 % limit, and five other random seeds must all stay under it too.

Its first run flagged "booleans", "pyspellchecker's" and "txt" (from HOW-TO-USE.txt), all in the entries for rounds 56 and 57 written just before. All are spelled right: the check now leaves out file names and knows the two words. The Bulgarian guide isn't spell-checked: the checker has no Bulgarian word list (round 48 read it through).

The full run with round 57 (run 12: 40 rounds run, 14 unchanged since they passed) found no problems: round 57 is clean. **Rounds 56 and 57 are two clean rounds in a row, so the debugging ends here.** One check could not run in this environment: round 5's colour segmentation of Waveshare's back photo, because `www.waveshare.com` can't be reached from here. It reports SKIP, not a pass; rounds 35 and 47 measured the same parts in your own back photo instead.

## Round 58: an independent review
After round 57 a separate reviewer (another agent, which had not built the case, given only the project and your photos) went through all of it. It rebuilt the parts from `case.py` (byte for byte the committed STLs), sliced them, measured the STLs, and read the README and both guides, the Bulgarian one included. It found nothing that stops the case being printed or put together. I checked each of its findings myself before changing anything. So rounds 56 and 57 were not the end: the count of clean rounds starts again after this one.

**Not clean.** Five small mistakes:
- **The two screw pictures numbered the screws differently.** `preview/screw_locations.png` numbered them in the order of the corner posts in `case.py`. The guide's step 4 picture numbers them in a cross, and the README's step 4 says to follow the guide's numbers. Both pictures now take one order from `case.py` (`SCREW_ORDER`): seen from the back, 1 bottom-right, 2 top-left, 3 bottom-left, 4 top-right.
- **The README promised too large a USB-C plug,** "up to 13 mm wide and about 7 mm thick". Pushed into the case, a 13 x 7 grip touches the opening with 3 mm standoffs, or with the board 0.3 mm off centre. Even the 12.4 x 6.6 grip that rounds 1 and 2 try (with the board centred) just touches the opening's side with 3 mm standoffs and the board 0.3 mm along the edge. The README now says 12.3 x 6.5 mm, which fits with either standoff height wherever the board sits.
- **The window came within 0.08 mm of the light field at one corner,** not the 0.1 mm the README promised. The cavity is the PCB outline grown by 0.3 mm, so the board can move anywhere in a 0.3 mm circle. Pushed into the bottom-left corner it moves diagonally, and the window's corners, then 0.5 mm round, came within 0.08 mm of the light field's corner. Round 49 pushed the board toward each wall and into the corners of a square, and round 45 tried the corners with the board centred, so neither saw it. The window's corners are now 0.4 mm round, which leaves at least 0.1 mm everywhere, and round 49 now moves the board round the circle (on the old corners it fails, at 0.08 mm).
- **"The clip beams print as short bridges":** each is a 28 mm bridge (in the G-code, three strands held only at the beam's ends, with 0.8 mm of air under them). The README and the guides now say so, and say to press each beam's middle after printing, to check that it moves and that its slot is open.
- **One stub was 2.5 mm, not 2.4:** the stretch of skirt between the top right-hand beam and the dial notch. Round 46 sampled the wall every 0.05 mm and allowed 0.1 mm, so it read 2.45 and passed. It now samples every 0.01 mm and allows 0.06.

Three gaps in the instructions:
- **Wires on the rim.** Laid open as step 2 says, both wires cross the lid's bottom rim and the cover's bottom wall, over the bottom clips and next to the PWR/BOOT opening, and nothing said to move them before closing. Step 3 now says to push both wires inside the lid's rim before lowering the cover, and to check afterwards that no wire shows in the seam or the PWR/BOOT opening.
- **The display's protective film.** Your front photo along the board shows a red pull tab at one corner of the display's left end, which ends up under the frame. Step 1 now says to peel the film off first.
- **"The notch in the right-hand end"** is only on the right with the display facing you, and after step 4 the back faces you. It is now "the end opposite the USB-C port".

Smaller wording, all fixed: the README said the battery wire "lies across" the battery's bottom edge (it runs along it, just inside it); comments in `case.py` said the wires run "under the battery" (they run between the board and the cell); the guides left out the README's advice to tuck the spare battery wire beside the cell's taped end; and the README said `preview/owner_measurements.png` shows every landmark the measurements used (it shows round 28's photos; the front photos and the headers are measured by rounds 44, 45 and 47). In the guides the beam check went into the "Print the back cover first" box, so that the English guide's printing list stays on one page.

**New methods** (`checks/round58.py`): the review itself, and three checks made from its findings, each of which would have caught one:
- **the screw pictures:** both must be drawn from the same four points in the same order, and the order must be a cross;
- **the README's USB-C grip,** pushed in with 4 and 3 mm standoffs and the board at 36 points round its play circle, must not touch the case (as a control, a 13 x 7 grip with the board 0.3 mm along the edge overlaps 4.6 mm³);
- **the window cut out of the lid's STL** (not worked out from `case.py`'s numbers), against the light field moved to 360 points round the play circle: it must stay at least 0.1 mm inside everywhere, and the corner radius measured from the section must be the README's 0.4 mm.

Round 37 now also looks for the four new steps (the film, the wires on the rim, the beams after printing, the spare battery wire) in all three documents: 20 slips in all.

The full run after these fixes (run 13) got to round 37 before you asked me to stop: rounds 1–37 found no problems apart from two in the checks' own bookkeeping, both fixed (round 31's list of where each new README number comes from needed the new USB-C grip size, and round 20 ran while round 59's file was being written).

## Round 59: different methods
**New methods** (`checks/round59.py`), run on their own and passing:
- **Every numbered marker in the guide's pictures** (36 in 7 pictures) sits on the part its legend names, found from the rendered meshes, and in the right place on the case. As a control, two swapped legend items fail.
- **The words for directions** (75 in the README's steps and both guides), each read in the view its step sets up: all right, and no "left" or "right" where the back faces you.
- **The round 58 reviewer's own scripts** (kept in `checks/review58/`), run again on the fixed case: the README's USB-C grip fits, and the window keeps 0.1 mm.

## Round 60: stopped
Round 60 (every README number traced to the checks' output, and a second independent review) was started, then stopped at your request: you will print the case and report anything wrong. **The debugging stops here, after round 59, without the second clean round in a row.**
