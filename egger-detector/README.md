# Egger Detector

A client-side Fabric mod for **Minecraft 26.1.2**. It finds **your team's dragon egg** from the
color of your name in the tab list ("Orange" name → the egg labelled **Orange's Egg**) and
**warns your team in chat** when other players come inside the radii you set around it.
Distances are measured **sideways only**: height doesn't count.

---

## Install

1. Fabric Loader **0.18.4 or newer** for Minecraft 26.1.2.
2. Put these in `.minecraft/mods`:
   - `eggerdetector-1.0.0.jar` (this mod; **Cloth Config is already inside it**)
   - **Fabric API** for 26.1.2 (tested with `0.155.3+26.1.2`): <https://modrinth.com/mod/fabric-api>
   - **Mod Menu** (recommended, for the settings button; tested with `18.0.2`): <https://modrinth.com/mod/modmenu>
3. Start the game. Settings: **Mods → Egger Detector → ⚙ (config button)**, or bind the key
   *"Open Egger Detector settings"* in Options → Controls → Key Binds → Egger Detector.

Client-only: the server needs nothing, and the mod works on any server.

`eggerdetector-1.0.0.jar` SHA-256:
`eef222f63d4bfc655405dce8baded76f6f1ef372a9c74026bb19eb68fa6d5fee`

---

## What it does, step by step

1. **Reads your team color** from your name in the tab list (the color of your name itself,
   not of a prefix like `[O]`). Example: `[O] BigRemi1688` drawn in gold `#FFAA00`.
   This is done **again in every game**, so a different color each round needs no change.
2. **Turns the color into the name written on the eggs.** The 16 Minecraft team colors have
   several possible names each (gold → *Orange* or *Gold*, aqua → *Light Blue* / *Aqua* /
   *Cyan*, light purple → *Pink* / *Magenta*, …). The mod looks at the egg labels it can see
   and picks the one that matches one of your color's names ("Orange's Egg"). If a label is
   drawn in exactly your color but has a name that is not a color (a team called "Dragon" →
   "Dragon's Egg"), that also counts.
3. **Finds the egg labels**: any text display or name tag that reads *"<color>'s Egg"*
   (any capitals, straight or curly apostrophe, decorations around it are fine), with a
   dragon egg under it (a placed dragon egg block, or a dragon egg shown by an item display or
   block display entity), up to 8 blocks below or 2 above the name and up to 2 blocks to the
   side. If the egg drops a block (dragon eggs fall when the block under them is dug out) it
   simply keeps guarding it.
4. **Starts guarding only when the egg closest to you is yours** (setting *Only start at the
   closest egg*). In the pre-game glass boxes your name has no team color yet, so nothing
   starts; when the round starts and names get their colors, it locks onto your egg. It never
   starts guarding while you are dead or spectating.
   You see *"Guarding Orange's Egg at x, z. Warnings start in 3s."* in chat (only you).
   If guarding stops in the middle of a round (your egg was broken, you switched the mod off
   and on), it only takes an egg **with the same name** again until you change world or egg
   settings – so an enemy egg whose name is another word for your color (you are Lime, they
   are "Green's Egg") never becomes "yours". This is remembered per team color: with a new
   color it starts fresh, and a short detour through another color (a "respawning" team)
   doesn't make it forget.
5. **Start delay** (default 3 s) after locking on, so every teammate has their team color
   before warnings begin.
6. Every tick it measures each other player's **horizontal** distance to the egg
   (`√(dx² + dz²)`, y ignored – an egg at y = 100 counts as if everyone were at y = 100).
7. **Warnings** (exactly the rules you asked for):
   - Only **coming in** warns. Leaving never does.
   - A player who **appears already inside** (teleported, logged in, came into view, or was
     there when guarding started) warns with the **smallest radius they are actually inside**,
     never a smaller one they haven't reached yet. Example: radii 50/30/15, a player appears
     at 25 blocks → the **30** message.
   - Crossing **several radii at once** (ender pearl, teleport) → **only the innermost** one
     they ended up in sends its message.
   - **Cooldown per player and per radius** (default 20 s): the same player can't trigger the
     same radius again within 20 s. Only the radius that made the warning gets the
     cooldown; the others are untouched. (The cooldown starts when the warning is made, even if
     it is later dropped as out of date – see Sending.)
   - Players who come into the same radius within **1 second** of each other share one message
     (`[players]` → `Steve, Alex`).
8. **Sending**: the message is typed into chat exactly as if you typed it (your server sends
   normal chat to your team chat). A message starting with `/` runs as a command. Each radius
   can instead be set to **Only me** (shown only to you). At most one chat message every 1.5 s
   (setting, minimum 1 s), so the server's spam protection doesn't kick you – extra messages wait
   in line (up to 10; beyond that the oldest is dropped and you get a note; a warning that waited
   more than 15 s is out of date and dropped with a note). The mod also keeps its own copy of
   the server's spam counter, **including the lines you type, the commands you click (counted
   when they really go out – after a confirmation screen only once you press Run) and what other
   mods send**, and waits a moment if you just sent a burst, always leaving room for 3 quick
   lines of your own. That copy only counts server ticks the server has confirmed (its time update,
   once a second), so it also holds back when the server lags or freezes, and nothing is sent
   while the connection stalls (checked in a simulation: lag down to 5 TPS, connection stalls up
   to 30 s, server freezes up to 15 s, your own typing in between).
9. **Stops guarding** (and tells you why, except when you leave the server or a proxy moves you
   to another server) when you change
   world/server (lobby ↔ map), your name loses or changes its team color for more than 1 second
   (not while you are dead or spectating – servers often give you a "respawning" color then;
   with a typed *Color name override* it keeps guarding and uses your new color for teammates),
   the egg block disappears (2 s check; for an egg with no block, its name is gone for 2 s while
   you are within 24 blocks), or you change the egg settings. Warnings still waiting to be sent
   are dropped then (except when the egg disappeared: then they are all sent – apart from ones still
   in their group window while warnings were paused because your team color was missing or
   changing, as they could name a teammate). Then it starts
   again by the same rules. While guarding, a second egg with your color name elsewhere never
   pulls it away from your egg as long as your egg block is still there (or too far away for
   the game to show it).

Players who **never** trigger a warning: you, players with your tab color (*Ignore my team*),
names on the *Ignore players* list, spectators, and players not shown in the tab list (NPCs).

---

## Settings (Mod Menu → Egger Detector)

Every option has a **Reset** button and a tooltip; there is a search bar at the top.

### General
| Setting | Default | What it does |
|---|---|---|
| (status) | – | Your detected tab color and the egg being guarded (read when the screen opens). |
| Enabled | Yes | On/off switch for the whole mod (also bindable to a key). |
| Chat notes | Yes | Notes only you see: egg found, guarding stopped and why, egg moved. |
| Status line | Yes | One line in a top corner: guarded egg, players within your largest radius, nearest distance (or "no radius is on"). |
| Status line position | Top left | Top left / Top right. |
| Sound | Yes | A ping only you hear when a warning goes out (higher pitch for your smallest radius); a low note if your egg disappears. |

### Your egg
| Setting | Default | What it does |
|---|---|---|
| Only start at the closest egg | Yes | Start only when the closest egg is yours; with the color detected automatically your name must also have its team color (quiet in the glass boxes). |
| Start delay (seconds) | 3 | Wait after locking on before warning (0–60). |
| Need a dragon egg under the name | Yes | Ignore labels that have no dragon egg (block, or item/block display) under them. |
| Egg name format | `{color}'s Egg` | How the egg labels are written; `{color}` = the color name. |
| Color name override | (empty) | **Leave empty** – the color is detected every game. Only fill in if detection is wrong; it then stays fixed until you Reset it. With *Ignore my team* on it still waits until your name has a team color (that is how teammates are told apart); if your name loses its color while guarding, warnings pause, and ones still waiting for the group window are dropped after 1 s (they could name a teammate). |

### Warnings
| Setting | Default | What it does |
|---|---|---|
| Ignore my team | Yes | Players with your tab color never warn. |
| Ignore players | (empty) | Names that never warn (⊕ adds a name; click a name, then ⊖, to remove it). |
| Cooldown (seconds) | 20 | Per player, per radius (0–3600). |
| Group players within (seconds) | 1 | Players entering the same radius this close together share one message. 0 = at once (0.1 s, so a teammate whose color shows up a tick late is never named) (0–10). |
| Gap between messages (seconds) | 1.5 | Minimum time between two chat messages from the mod (1–10; vanilla kicks after about 10 quick messages and forgives one per second). |

### Radii
A list (up to 20): **⊕** adds a radius; to remove one, click into it, then press **⊖**. Each radius has:
**Radius (blocks)** (1–1000), **Message**, **Send to** (Chat / Only me), **On**.
A radius with an empty message counts as switched off.
Defaults: **50** → `Heads up: [players] within [radius] blocks of our egg!` and
**15** → `ALERT: [players] at our egg ([radius] blocks)!`.
At the bottom: a preview of your saved messages.

**Placeholders** (not case sensitive):
`[players]` all names (`Steve, Alex`), `[player1]`, `[player2]`, … one name each (also
`[player 1]`; empty if there is no such player), `[count]`, `[radius]`, `[color]` (your
color name, e.g. Orange). Messages are cut to 256 characters (the chat limit); a very long
`[players]` list becomes `A, B, C +5 more`.

Settings file: `.minecraft/config/eggerdetector.json` (edited by hand is fine: wrong or
missing values fall back to defaults, out-of-range numbers are clamped into range, messages
are cut to 256 characters, radius entries without a readable `radius` are skipped and at most 20
are kept; a file that can't be read is kept as `eggerdetector.json.broken`). Advanced, file only: `palette` – the color → name table.

---

## Limits (read this)

- **The mod only sees what the game shows you.** Players and egg labels are only known to your
  client within the server's *entity tracking range* (often 48–128 blocks, set by the
  server). A radius bigger than that, or an egg far away from you, can't be watched. The
  status line shows *nobody within …* / the nearest distance so you can see it working.
- Once guarding started, it keeps guarding that egg wherever you go – but it can only warn
  about players your game can see.
- If your chat is set to **Hidden** in Options, the server refuses chat messages; warnings
  sent as commands (starting with `/`) still work.
- A server plugin with stricter spam rules than vanilla may need a bigger
  *Gap between messages*.
- The spam safety follows the server's own clock, which the server sends once a second (vanilla
  does; servers built on it normally do too). On a server that never sends it, chat warnings are
  never sent: each one is dropped after 15 s with a *Not sent, it waited too long* note
  (*Only me* warnings still show). That is the safe way round: it never risks a kick.
- On an extremely bad connection (2.5 s or more round trip) together with a server freeze of
  5–15 s and you typing 8 lines around it, the simulation could still reach the kick (8 of 2772
  cases). At up to 2 s round trip: never.

---

## How it was tested

- **In a real game**: a Minecraft 26.1.2 server (Fabric, Carpet fake players as the other teams)
  and a real 26.1.2 client running this mod, headless. A script plays a whole round – glass box
  without colors, wrong closest egg, lock-on, teammates getting their color late, players walking
  in and out of radii, appearing inside, several radii at once, cooldowns, grouping, dying and
  spectating, a renamed/legacy-colored label, your egg broken mid-round, an egg with another name
  for your color nearby, typed color override, your color vanishing for a moment, a burst of 16
  warnings, you typing and clicking commands at the same time, the server lagging at 10 TPS, the
  mod switched off and on. **What the server actually received** is checked against what should
  have been sent: the last runs met all 53 checks, never a kick. The settings screen was
  checked on screenshots.
- **Spam safety**: besides the in-game burst and lag tests, a simulation of the server's spam
  counter (lag down to 5 TPS, connection stalls up to 30 s, server freezes up to 15 s, 150–2000 ms
  round trip, your own typing in between): no kick caused by the mod.
- **Unit tests** for the game-independent logic: 98 checks, run on every build.
- **Debugging passes**: each pass = the full in-game run + an independent review of the whole
  code. Bugs found were fixed and the next pass started over; passes 15 and 16 found nothing
  (two clean passes in a row). The jar here is the Gradle build: its classes are byte-identical
  to the ones tested, and it passed the full in-game run itself too.
- `build.bat` was tested with Wine (paths with spaces, `&`, `!` and parentheses).
- **Not tested**: a real Windows double-click of `build.bat`, your actual server and its plugins,
  and signed chat on an online-mode server (the test server ran offline).

---

## How it was built

- Minecraft **26.1.2** is not obfuscated: no mappings, no remapping.
- **Gradle 9.8.2** (wrapper included, checksum-pinned) + **Fabric Loom 1.19.3**
  (`net.fabricmc.fabric-loom`), Java **25** toolchain.
- Dependencies: Fabric Loader 0.20.1, Fabric API 0.155.3+26.1.2, Mod Menu 18.0.2 (compile only),
  Cloth Config 26.1.154 (bundled with Loom's `include`; LGPL-3.0, unmodified).
- All game classes used were read from the decompiled 26.1.2 client (Vineflower), method
  signatures checked with `javap`.
- The game-independent logic (radii, cooldowns, grouping, label parsing, color matching,
  message placeholders) is in `src/main/java/com/eggerdetector/core` and is checked by
  `src/test/java/.../CoreTests.java` on every `gradlew build`.
- A second build with plain `javac` and the same flags as `build.gradle`
  (`-Xlint:all -Xlint:-classfile -Xlint:-processing -g`) gives **zero warnings** and
  byte-identical classes.

### Rebuild it yourself
Windows: double-click **`build.bat`** (needs Java 25: e.g. Eclipse Temurin 25). The jar is
copied to `OUTPUT\`. Linux/macOS: `./build.sh`. Or run `gradlew build` and take
`build/libs/eggerdetector-1.0.0.jar`.

---

## Files

| Path | What |
|---|---|
| `src/main/java/com/eggerdetector/Detector.java` | The run-time logic: color, labels, lock-on, players, sending. |
| `src/main/java/com/eggerdetector/core/IntruderTracker.java` | Radius crossing rules, cooldowns, grouping. |
| `src/main/java/com/eggerdetector/core/LabelParser.java` | Reads "Orange's Egg" style labels. |
| `src/main/java/com/eggerdetector/core/ColorMatcher.java` | Tab color → color names, "is this label mine?". |
| `src/main/java/com/eggerdetector/core/MessageFormatter.java` | Placeholders, chat-safe text, 256 limit. |
| `src/main/java/com/eggerdetector/TabColors.java` | Reads a name's color from the tab list. |
| `src/main/java/com/eggerdetector/MessageSender.java` | Sends chat/commands with the gap between messages. |
| `src/main/java/com/eggerdetector/StatusHud.java` | The status line. |
| `src/main/java/com/eggerdetector/gui/EggerConfigScreen.java` | The settings screen (Cloth Config). |
| `src/main/java/com/eggerdetector/config/` | Settings and the JSON file. |
| `src/main/java/com/eggerdetector/mixin/` | Two small hooks: counts every chat line/command that goes to the server, and reads the server's clock. |

License: MIT (this mod). Cloth Config 26.1.154: LGPL-3.0 (© shedaniel), bundled unmodified;
its source is at <https://github.com/shedaniel/ClothConfig> and its license text is inside the
bundled jar (`LICENSE.md`).
