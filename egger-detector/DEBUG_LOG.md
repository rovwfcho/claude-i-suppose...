# Egger Detector - debugging log

## Before the passes (development testing)
- Run 1 (scripted scenario, real 26.1.2 server + client, Carpet fake players):
  - BUG: Bob teleported 40 -> 10 blocks (15 on cooldown) and the 30 message went out.
    Cause: other players are slid to their new position over 3 ticks (InterpolationHandler),
    so the mod saw intermediate positions inside 30. Fix: use the server position
    (getInterpolation().position()), and the innermost-only rule now also removes a player from
    bigger pending messages when the inner radius is on cooldown. New unit check added.
  - Test-script timing windows (4 false failures) fixed; spam step redesigned.
- Run 2: 21/22 - the remaining one was the script starting before the test player logged in
  (the mod correctly said "closest egg is Red's Egg"). Script now waits for the login.
- GUI (first, hand-made screen): clicks after "Preview"/"Remove" went to a stale copy because
  the layout object was reused across rebuilds. Screen replaced by Cloth Config (user request).
- Own review: team-color flicker could make teammates count as intruders for a tick -> compare
  with the locked color, pause watching during a mismatch, unlock after 20 ticks; error recovery
  message pointed to a disabled button -> restarts on rejoin/toggle; tab-name search used
  toLowerCase index (length can change) -> regionMatches.

## Pass 1
- Regression (in game): 22/22 expectations, spam step 16 messages, min gap 999 ms, no kick. Singleplayer
  (integrated server) locks onto Red's Egg, no errors. GUI: add (+), edit, Reset list, remove (click + -),
  Save writes the file, Cancel leaves it unchanged; title screen via Mod Menu OK.
- Own: tooltip/README said "X" removes a radius; Cloth removes the focused cell with the round minus -> fixed.
- Review GUI/config (accepted all 6): >20 radii silently dropped -> list error; MIN_GAP 0.5 s could reach
  vanilla's spam kick (TickThrottler 20/200) -> min 1 s, default 1.5 s; huge hand-edited radius wrapped
  to 1 -> clamp before int; unreadable radii -> defaults + note, missing message -> default text;
  per-field Reset used 30/template -> the rule's own values, cell title now live, RadiusRule.equals;
  two tooltips corrected.
- Review build/docs (accepted all): build.bat java check always failed (cmd /c strips the outer quotes
  of a for /f command that starts with a quote) -> version written to a temp file, findstr first;
  quoted JAVA_HOME; old jars copied -> clean build; settings.gradle comment; README: javac flags,
  world-change note (now also shown), clamping, 20 radii, queue of 10, 2 blocks above.
- Review detection (accepted all 7): egg falling one block (DragonEggBlock is a FallingBlock) unlocked after
  2 s -> follow() adopts the new block under the same name; unlisted NPC player entities were not filtered
  (getPlayerInfo also returns unlisted entries) -> must be in getListedOnlinePlayers(); typed color mode
  compared teammates with the locked color -> current tab color; MIN_GAP (see above) + client mirror of
  the server's spam counter; queued warnings survived world/team change -> cleared on unlock (kept when
  the egg vanished); eggs without a block never unlocked and a dropped egg item counted as an egg -> item
  entities no longer count, name gone for 4 scans within 24 blocks unlocks; failedConnection kept the old
  world in memory -> cleared.
- Scenario extended: egg falls one block / put back (must keep guarding + still warn), name-only egg whose
  name is removed (must stop).
- Pass 1 NOT clean (clean count 0).

## Pass 2
- Regression (in game, after the pass-1 fixes): 27/27 expectations incl. egg falling one block (kept
  guarding, still warned), egg put back, name-only egg unlocks when its name is removed; spam 16 msgs,
  min gap 999 ms (gap set to 1 s by the script), no kick.
- Own: README key-bind path (Options > Controls > Key Binds), bad "Dragons' Egg" example, closest-egg
  row with a typed color -> fixed. Pass 2 NOT clean (clean count 0).
- Review GUI/build/docs (pass 2, accepted all): build.bat lost "!" in paths under delayed expansion (also
  inside gradlew.bat) -> DisableDelayedExpansion, %JMAJOR% default 99; list Reset stayed grey after edits
  (cell value read the rule object, only written on Save) -> cell getValue() from the live fields;
  wrong-JAVA_HOME message; "Radius: 0" title for invalid text -> "?"; README file-tolerance wording.
- Review detection (pass 2, accepted all 4): players who stopped counting inside the group window were
  still named -> tracker.dropPending() for filtered players (unit check); follow() could leave an intact
  egg for a same-named label elsewhere -> never while the egg block is there, moving keeps pending
  messages; spam mirror could never hold (gap >= 1 s) and ignored your own typing -> counts your chat
  and commands (Fabric ClientSendMessageEvents, own sends skipped), assumes 15 forgiven per second;
  egg vanished -> pending group-window messages sent instead of dropped, queued warnings older than
  15 s dropped with a note.
- Scenario extended: decoy Orange egg while ours is intact (no switch), 7 typed lines then a warning
  (must wait >= 0.8 s, no kick).
- Pass 2 NOT clean (clean count 0).

## Pass 3
- Regression (in game): 30/30 after correcting one test expectation (the inserted steps made Bob's
  30-block cooldown expire, so "R30: Bob" was right). New checks pass: decoy Orange egg -> no switch;
  7 typed lines -> next warning waited 1.38 s, no kick; egg fall; name-only egg unlock. Spam step 16
  messages, min gap 981 ms at the server (client sends on 50 ms ticks), no kick.
- Own review: MessageSender start values/overflow, unlock(keepQueue) send path (egg still set) - nothing.
- Review GUI/build/docs (pass 3): settings screen clean (getValue() override verified against Cloth
  bytecode). build.bat accepted 5: "&" in path breaks gradlew.bat -> wrapper jar started directly;
  quoted JAVA_HOME with ")" crashed the error echo -> messages moved out of blocks (labels); UNC path ->
  pushd + self-check; JAVA_TOOL_OPTIONS "version" line -> findstr " version "; name-gone stop now plays
  the low note like the README says.
- build.bat RUN under Wine 9 cmd with a stand-in java.exe: path "C:\Mods & Tools!\egger (1)", JAVA_HOME
  with "&"/quotes/wrong+parentheses/unset, Java 8/21/25/26-ea, Gradle failing, half-extracted zip,
  JAVA_TOOL_OPTIONS with "version" -> all correct messages / jar copied. Wine showed two more problems
  (fixed): "|| goto" after pushd unreliable -> explicit check; findstr /i + && in the copy loop ->
  plain string test.
- Review detection (pass 3, accepted 2 low): clicked commands (sendUnattendedCommand) not counted ->
  small mixin; hold point 140 left room for 2 own lines -> 120 (3 lines).
- Pass 3 NOT clean (clean count 0).

## Pass 4
- Regression (in game): 30/30. 4 typed lines + 3 clicked commands -> next warning waited 2.71 s
  (predicted 2.7 s: mirror 140 -> 100 at 15/s), so the mixin applies; no mixin errors in the log;
  spam step 16 messages, min gap 999 ms, no kick.
- Own review: mixin over-counts commands that open a confirmation screen (safe direction) - nothing.
- Review whole mod (pass 4, accepted 2): legacy "§" codes inside plain-text labels/tab names were not
  applied (the game's renderer applies them via StringDecomposer) -> shared TabColors.flatten() uses
  StringDecomposer.iterateFormatted for labels and tab names; a radius with an empty message swallowed
  the outer radii -> skipped like a switched-off radius.
- Scenario extended: Pink label sent as plain "§dPink's Egg" (server confirmed the text), empty-message
  15 radius with a jump to 10 blocks -> 50 message.
- Pass 4 NOT clean (clean count 0).

## Pass 5
- Regression run 5a: 31/32 - the miss was my scenario (Dave is pink, Tester had just joined pink, so Dave
  was correctly ignored as a teammate). Step switched to Bob (red). Run 5b: 32/32 PASS: plain-text
  "§dPink's Egg" label recognised (locked onto Pink's Egg), empty-message 15 radius -> "R50: Bob (1)",
  spam step 16 messages, min gap 1000 ms, no kick.
- Own review: flatten() index alignment with LabelParser.sourceIndex, per-part code reset - nothing.
- Review whole mod (pass 5, accepted 1): the quick pre-check ran on the raw text, so a code between
  "'s" and "Egg" ("§6Orange's §lEgg") hid the label -> flatten first, pre-check the decoded text.
  (Also noted: build/libs jar was stale - packaging rebuilds clean.)
- Scenario: legacy label now "§dPink's §lEgg".
- Pass 5 NOT clean (clean count 0).

## Pass 6
- Regression (in game): 32/32 PASS, incl. "§dPink's §lEgg" recognised; spam 16 msgs, min gap 999 ms, no kick.
- Own review: cost of decoding every named entity per scan - negligible. Nothing.
- Review whole mod (pass 6, accepted 2 low): a switched-on radius with an empty message still counted
  for the "smallest radius" ping pitch and the HUD "within N" -> shared warns() filter (also treats a
  message that is only "§" codes as empty); README: no stop note when a proxy moves you to another
  server (connection replaced) -> wording.
- Test driver now logs sounds (mixin on SoundManager.play) and has a "hud" command; scenario step
  added: empty 100 + empty 5 radius -> HUD "within 50", jump to 3 blocks -> R15 + ping pitch 2.0.
- Pass 6 NOT clean (clean count 0).

## Pass 7
- Regression run 7a: 33/35 - both misses were my new step's windows (counted from the step start, the
  teleport came 3 s later; the mod sent R15 + pitch 2.0 1.1 s after the teleport). Step split.
  Run 7b: 35/35 PASS: HUD "within 50" with an empty 100 radius, R15 + ping 2.0 with an empty 5 radius;
  spam 16 msgs, min gap 999 ms, no kick; client log errors only offline/no-audio ones (same as before).
- Own review: HUD "nobody within 0" when no radius warns (cosmetic) - also found by the reviewer.
- Review whole mod (pass 7, accepted 5): after guarding stopped mid-round (egg broken, toggle), the
  closest egg whose name is an alias of your color (Lime -> "Green's Egg") could become "yours" ->
  round memory: same world + color + egg settings only re-locks onto the same egg name; cooldown/stale
  mismatch with gap > 15 s -> MAX_GAP 10 s + README wording (cooldown starts when the warning is made);
  "nobody within 0" -> "no radius is on"; build.bat folder check by fixed name -> %~nx0; a same-named
  egg in sight could pull guarding away while ours was in an unloaded chunk -> no move then.
- Scenario extended: pink egg broken mid-round next to a "Magenta's Egg" -> no lock, HUD names the
  round's egg; pink egg back -> guarding Pink again.
- Pass 7 NOT clean (clean count 0).

## Pass 8
- Regression run 8a: 38/39 - step 21 (egg block removed) now showed "Orange's Egg (your egg this
  round) is not in sight" although its name was in sight (only the egg block was gone): my new
  waiting text was wrong -> roundWaiting(): not in sight / has no dragon egg under it / is not the
  closest egg. Locking itself was right in every step (no Magenta lock, Pink re-locked). Bug in my
  pass-8 change -> pass 8 NOT clean.
- build.bat under Wine: normal name and renamed "build (1).bat" in "C:\Mods & Tools!\egger (1)" with
  JAVA_HOME "C:\jdk & 25" -> both build and copy the jar.
- Regression run 8b (with roundWaiting): 39/39 PASS; step 21 HUD "Orange's Egg (your egg this round)
  has no dragon egg under it", Magenta step: no lock, HUD names Pink's Egg, Pink re-locked.
- Review whole mod (pass 8, accepted 1): the round memory was wiped the first tick your tab name
  showed another color (gray "respawning" team, tab plugin redraw) -> back to Lime, the Green egg
  could be taken after all -> round egg remembered per tab color (map), cleared on world change,
  new connection and egg-settings change only. README updated.
- Scenario extended: 2 s detour through a gray team while standing at the Magenta egg -> still no lock.
- Pass 8 NOT clean (clean count 0).

## Pass 9
- Regression (in game): 39/39 PASS. Gray detour visible in the HUD (2.2 s "closest egg is Magenta's
  Egg, not yours", back to pink at 4.2 s "Pink's Egg (your egg this round) has no dragon egg under it"),
  no Magenta lock, Pink re-locked; spam 16 msgs, min gap 999 ms, no kick.
- Review whole mod (pass 9, accepted 4 + packaging note): spam mirror forgave 15/s of wall time, so a
  server below ~13 TPS could kick during a long fight -> forgive 0.75 per server tick read from the
  game time (client predicts +1/tick, the server corrects it every second; backward corrections undo
  what was forgiven too early, up to 20 s). Simulated vs TickThrottler(20,200) with the queue never
  empty and 3 own lines every 20 s: never kicked from 20 down to 5 TPS (gap 1/1.5/3 s); at 2-3 TPS the
  user's own typing alone gets kicked. A new lock while dead/spectating (a gray "respawning" team) ->
  no new lock then. Typed-color mode named teammates while the server dropped your team -> same 1 s
  pause, then teammates compared with the last tab color. Group 0 could name a teammate whose color
  came a tick late -> group window at least 0.1 s. Blank "waiting - " after unlock -> "looking for
  your egg". Gradle jar stale -> rebuilt when packaging.
- Scenario extended: spectator + settings change -> no lock, HUD "you are dead or spectating";
  survival again -> guarding again.
- Pass 9 NOT clean (clean count 0).

## Pass 10
- Regression (in game): 43/43 PASS. Game-time spam mirror: 4 typed lines + 3 clicked commands -> next
  warning after 2.75 s (predicted 2.67 s: 140 -> 100 at 0.75/tick); spam step 16 msgs, min gap 1000 ms,
  no kick. Spectator: stop on settings change, no new lock, HUD "you are dead or spectating"; survival
  -> guarding again.
- Review whole mod (pass 10, accepted 4): typed-color mode adopted a gray "respawning" color while you
  were dead (teammates then warned) and could lock with no colors in the glass box -> a color change
  while dead/spectating never counts (both modes: keep guarding with the color you had), typed mode
  with "Ignore my team" needs a tab color to lock and waits while your name has none, teammates are
  always compared with the locked color; a network stall let the mirror forgive the client's own
  guessed ticks -> server time recorded (mixin at TAIL of handleSetTime), the guess trusted at most
  30 ticks past it, and nothing is sent while the server's time is overdue; a world change could
  forgive 30 too much -> forward jumps > 40 forgive nothing, no forgiveness before the new world's
  time arrives; the old world stayed referenced after leaving -> sender.reset().
  Simulation (sim/spam5.py) vs TickThrottler(20,200): 20/13/10/5 TPS x gap 1/1.5/3 s x stall
  0/10/20/30 s x with/without 3 own lines every 20 s: never kicked, peak 142.
- Scenario extended: typed color, Tester dies into a gray team -> pink teammate not warned, red Bob
  warned; /tick rate 10 with Bob in and out for 25 s (cooldown 0) -> no kick.
- Pass 10 NOT clean (clean count 0).

## Pass 11
- Regression (in game): 44/44 PASS. 10 TPS (/tick rate 10), cooldown 0, Bob in/out for 25 s: 20 messages,
  9 at 1.0 s gaps, then every 2.6-2.7 s (predicted 20 / 7.5 per s = 2.67 s), old ones dropped as out
  of date, no kick. Typed color + death into a gray team: only red Bob warned, pink Dave not. Spam step
  16 msgs, min gap 999 ms; 4 typed + 3 clicked -> waits as before.
- Review whole mod (pass 11, accepted 3): the copy still forgave up to 30 ticks of the client's own
  time guess while the server was frozen (kick possible with 8 own lines) and forgave nothing while
  the mod was off (typed lines then held warnings up to 20 s) -> forgiveness only from the server's
  time updates (0.75 x confirmed ticks, applied when the update arrives - also while the mod is off),
  at most 15 per second of real time with 2 s saved (late updates arriving together after a stall);
  nothing sent while the server's time is overdue. Simulation sim/spam7.py: 2772 cases (20/13/10/5
  TPS x gap 1/1.5/3 s x none/stall 10-30 s/freeze 2-15 s x own typing patterns): 0 kicks caused by
  the mod, highest server count 180; same message rate as before at 20 TPS. (Without the 15/s cap:
  56 kicks after 20-30 s stalls.) Typed color + no tab color: waiting warnings were sent after an
  open-ended pause -> sent at once when the pause starts.
- Scenario extended: mod off, 8 lines typed 3 s apart, mod on -> next warning not held.
- Pass 11 NOT clean (clean count 0).

## Pass 12
- Regression run 12a: 45/46 - the miss was my new step's window (the 24 s of typing came before the
  switch-on; the mod re-locked 0.25 s after it and Bob's warning went out 1.1 s after he came). Step
  split. Run 12b: 46/46 PASS. Server-confirmed forgiveness in game: 4 typed + 3 clicked -> next warning
  2.6 s later; 10 TPS lag step 21 msgs, gaps 1.0 s then 2/2/4 s (15 forgiven per 2 s time update =
  7.5/s), no kick; mod-off typing then on -> warning not held; spam step 16 msgs, min gap 999 ms.
- Review whole mod (pass 12, accepted 2, declined 1): (1) the pass 11 change (typed color, no tab
  color: send waiting warnings at once) could name a teammate whose color vanished a tick before
  yours -> waiting warnings now stay until the color is back (teammates are then taken out as usual)
  and are dropped after 1 s without it. (2) Clicked commands were counted at sendUnattendedCommand
  HEAD, i.e. also when a confirmation screen opened and nothing was sent (Cancel) -> every chat line
  and command is now counted where it really goes out: ClientCommonPacketListenerImpl.send HEAD for
  ServerboundChatPacket / ServerboundChatCommandPacket / ServerboundChatCommandSignedPacket (the only
  client class creating them is ClientPacketListener, all via this.send). Fabric's send events, the
  sendUnattendedCommand hook and the sender's own +20 were removed (the hook counts its line too).
  Declined: eggs as items on armor stands (the user's server uses a block egg; "Need a dragon egg"
  can be switched off).
- Pass 12 NOT clean (clean count 0).

## Pass 13
- Unit tests 98/98. Regression run pass13: 50/50 PASS (new steps: typed color, group 3 s - Bob comes in,
  Tester colorless 0.3 s -> "P50: Bob" at +3.12 s; Eve comes in, Tester colorless 2.5 s -> no warning).
  4 typed + 3 clicked (counted at the packet send now) -> next warning 2.27 s later; spam step 16 msgs,
  min gap 999 ms; 10 TPS lag step 20 msgs, gaps 1.0 s then 2/2/4 s, no kick.
- Review whole mod (pass 13, accepted 1): both pass-13 changes verified correct (mixin target exists,
  no override, only ClientPacketListener builds chat packets, all via this.send; off-thread -> execute).
  Found: when the egg vanishes during a color pause (typed color colorless, or the automatic mode's
  up-to-19-tick mismatch pause), unlock(keepQueue) still sent all waiting warnings uncleaned of
  teammates -> new watchPaused flag (set each tick before follow/checkEggStillThere); while paused,
  unlock drops waiting warnings instead. README stop rule updated. (Also noted: build/libs jar is
  stale - packaging does a clean Gradle build.)
- Scenario extended: Carl comes in, egg broken, Tester colorless 2 s later -> egg loss noticed inside
  the pause -> no Carl warning; egg back -> guarding again.
- Pass 13 NOT clean (clean count 0).

## Pass 14
- Unit tests 98/98. Regression run pass14: 53/53 PASS. New step: Tester colorless from +2.0 s, egg loss
  noticed at +2.59 s (inside the pause, before the 1 s drop) -> Carl not warned; guarding again at
  +6.29 s after the egg was put back. Spam step 16 msgs, min gap 1000 ms; lag step 21 msgs, no kick.
- Review whole mod (pass 14): no code bugs (watchPaused verified: never stale when read; mixins,
  server chat counting, config, GUI, build scripts re-checked). Accepted 1 (doc): the README's stop
  rule said all warnings are dropped when the egg vanishes during a color pause; only those still in
  their group window are (queued ones were cleaned of teammates before the pause and are sent) ->
  reworded. Declined: egg-missing check finishing on exactly the tick a teammate's color arrives
  (needs both on the same tick; negligible).
- Pass 14 NOT clean (clean count 0) - README wording only.

## Pass 15
- Regression run pass15: 53/53 PASS (egg loss noticed at +2.55 s inside the color pause -> Carl not
  warned). Spam step 16 msgs, min gap 999 ms; lag step 20 msgs, no kick.
- Review whole mod (pass 15, fresh eyes on GUI/config/parsers/README/build): no real bugs found
  (300k-case fuzz of the parsers/formatter, config round trip and bad input, Cloth save path,
  metadata, wrapper manifest, every README claim). Considered and rejected by the reviewer: a rank
  prefix containing your own name case-insensitively ("[MAX] Max"), egg without a block pulled away
  when its label is out of view (README only promises this for a placed egg block).
- Pass 15 CLEAN (clean count 1).

## Pass 16
- Code unchanged since pass 15. Regression run pass16: 53/53 PASS (egg loss noticed at +2.57 s inside
  the color pause -> Carl not warned). Spam step 16 msgs, min gap 999 ms; lag step 20 msgs, no kick.
- Review whole mod (pass 16, session-lifecycle focus): no real bugs found (tick order across lock /
  arm / watch / follow / unlock / relock, respawn keeps ClientLevel, reconnect and error recovery,
  tracker across radius edits, HUD states, thread safety of both mixins; spam simulation re-run with
  150/500/1000/2000 ms round trip: 0 mod-caused kicks in 4 x 2772 cases, 400 random-typing trials
  at 50-1500 ms: 0 kicks, peak 185). Limits noted (not bugs, fail safe): a server that never sends
  its time update -> chat warnings wait and are dropped after 15 s with a note; round trip >= 2.5 s
  with a 5-15 s freeze and 8 own lines around it kicked in 8/2772 simulated cases. Both go in the
  README's limits.
- Pass 16 CLEAN (clean count 2) -> two clean passes in a row: package and deliver.

## Packaging
- Gradle 9.8.2 offline clean build: BUILD SUCCESSFUL, CoreTests 98/98; all 33 classes byte-identical to
  the javac build tested in passes 15/16 (Gradle jar adds LICENSE_eggerdetector + MANIFEST; fabric.mod.json
  same content). Full in-game run on the Gradle jar itself: 53/53 PASS, no kick; Cloth loads jar-in-jar.
