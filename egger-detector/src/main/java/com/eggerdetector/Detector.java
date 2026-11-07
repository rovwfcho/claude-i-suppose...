package com.eggerdetector;

import com.eggerdetector.config.EggerConfig;
import com.eggerdetector.config.RadiusRule;
import com.eggerdetector.core.ColorMatcher;
import com.eggerdetector.core.IntruderTracker;
import com.eggerdetector.core.LabelParser;
import com.eggerdetector.core.MessageFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextColor;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.InterpolationHandler;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The whole mod at run time, called at the end of every client tick (client thread only).
 *
 * <ol>
 *   <li>Read your name color in the tab list.</li>
 *   <li>Every half second, find the egg labels in sight ("Orange's Egg" text displays or
 *       name tags) and the dragon eggs under them.</li>
 *   <li>Lock on: when the egg closest to you carries your color name (or, with that rule
 *       off, any egg with your color name). Before the round starts names have no team
 *       color, so nothing locks in the glass boxes.</li>
 *   <li>After the start delay, measure every other player's horizontal distance to the
 *       egg each tick and let {@link IntruderTracker} decide what to send.</li>
 * </ol>
 */
public final class Detector {
    static final Logger LOG = LoggerFactory.getLogger("eggerdetector");
    public static final Detector INSTANCE = new Detector();
    private static final int SCAN_EVERY_TICKS = 10;
    /** The egg block must be missing this long before we believe it is gone (block updates arrive in pieces). */
    private static final int EGG_MISSING_TICKS = 40;
    /** How far the egg block may be from its label. */
    private static final int SEARCH_SIDE = 2, SEARCH_UP = 2, SEARCH_DOWN = 8;
    /** Your tab color must stay changed this long before guarding stops (1 second). */
    private static final int COLOR_CHANGE_TICKS = 20;
    /** Shortest group window (2 ticks), see watchPlayers. */
    private static final long MIN_GROUP_MS = 100;
    /** An egg without a block to check: its name must be missing for this many scans (2 s)... */
    private static final int LABEL_MISSING_SCANS = 4;
    /** ...while you are this close to it (further away the game may simply not show you the name). */
    private static final double LABEL_SURE_RANGE = 24;

    /** A label found this scan. */
    record Label(String text, String phrase, @Nullable Integer rgb, double x, double y, double z,
                 boolean hasEgg, double eggX, double eggZ, @Nullable BlockPos eggBlock) {
    }

    /** The egg we guard. */
    record Egg(String phrase, String colorName, String labelText, @Nullable Integer labelRgb, double x, double z, @Nullable BlockPos block) {
        Egg moveTo(Label l) {
            return new Egg(phrase, colorName, labelText, labelRgb, l.eggX(), l.eggZ(), l.eggBlock());
        }
    }

    private final IntruderTracker tracker = new IntruderTracker();
    private final MessageSender sender = new MessageSender();

    private @Nullable Object lastConnection;
    private @Nullable ClientLevel lastLevel;
    private long tick;
    private boolean failed;
    /** Connection the error happened on: joining another one starts the mod again. */
    private @Nullable Object failedConnection;
    /** Ticks your tab color has differed from the one we locked with. */
    private int colorMismatchTicks;
    /** Ticks your name has had no tab color while guarding with a typed color and "Ignore my team". */
    private int colorlessTicks;
    /**
     * Watching is paused this tick because your team color is missing or changing: warnings still
     * waiting for their group window can't be cleaned of teammates now.
     */
    private boolean watchPaused;
    /** Scans in a row the guarded egg's name was not seen (eggs without a block only). */
    private int labelMissingScans;

    // what the settings screen shows
    private @Nullable Integer myRgb;
    private List<String> myNames = List.of();
    private String waiting = "join a server";
    private List<Label> lastLabels = List.of();

    // lock
    private @Nullable Egg egg;
    private @Nullable Integer lockedRgb;
    private String lockedSettings = "";
    private long armedAtMs;
    /**
     * The egg we guarded this round, per tab color (same world, same egg settings). After guarding
     * stops in the middle of a round - your egg was broken, you toggled the mod - only an egg with
     * this name is taken again: an enemy egg whose name is another word for your color
     * (Lime / "Green's Egg") must never become "ours". Kept per color, so a short detour through
     * another color (a "respawning" team, a tab plugin redrawing names) can't wipe it.
     */
    private final java.util.Map<@Nullable Integer, RoundEgg> roundEggs = new java.util.HashMap<>();
    /** The egg settings the remembered round eggs were found with. */
    private String roundSettings = "";

    private record RoundEgg(String phrase, String text) {
    }
    private int eggMissingTicks;

    private Detector() {
    }

    static long nowMs() {
        return System.nanoTime() / 1_000_000L;
    }

    // ------------------------------------------------------------------ tick

    void onEndTick(Minecraft mc) {
        if (failed) {
            if (mc.getConnection() == failedConnection) {
                return;
            }
            failed = false; // joined again (or left to the title screen): try again
            failedConnection = null;
        }
        try {
            tick(mc);
        } catch (VirtualMachineError e) {
            throw e;
        } catch (Throwable t) {
            failed = true;
            failedConnection = mc.getConnection();
            LOG.error("Egger Detector hit an error and switched itself off (it starts again when you rejoin, or switch it off and on)", t);
            resetSession();
        }
    }

    /** A chat line or command went to the server (yours, another mod's or ours): it counts towards the spam limit. */
    void onChatSent() {
        sender.noteSent();
    }

    /** The server told us its game time (once a second). */
    void onServerTime(long gameTime) {
        sender.noteServerTime(Minecraft.getInstance().level, gameTime, nowMs());
    }

    /** Settings were saved: start again (also after an error). */
    public void onSettingsChanged() {
        failed = false;
        failedConnection = null;
    }

    private void tick(Minecraft mc) {
        ClientPacketListener conn = mc.getConnection();
        if (conn != lastConnection) {
            lastConnection = conn;
            resetSession();
        }
        if (conn == null || mc.level == null || mc.player == null) {
            waiting = "join a server";
            return;
        }
        if (mc.level != lastLevel) {
            // lobby -> map, server switch, dimension change: a new round, start over
            lastLevel = mc.level;
            unlock(mc, "you changed world");
            roundEggs.clear();
            lastLabels = List.of();
        }
        EggerConfig cfg = EggerConfig.get();
        long now = nowMs();
        if (!cfg.enabled) {
            if (egg != null) {
                unlock(mc, null);
            }
            sender.clear();
            waiting = "switched off";
            return;
        }
        tick++;

        PlayerInfo me = conn.getPlayerInfo(mc.player.getUUID());
        myRgb = me == null ? null : TabColors.nameColor(mc, me);
        myNames = myRgb == null ? List.of() : ColorMatcher.namesFor(myRgb, cfg.palette);

        String settingsKey = cfg.colorOverride.toLowerCase(Locale.ROOT) + "|" + cfg.labelFormat + "|" + cfg.requireDragonEgg + "|" + cfg.closestEggOnly;
        boolean colorSteady = true;
        if (egg == null || myRgb != null) {
            colorlessTicks = 0;
        }
        if (egg != null) {
            if (!settingsKey.equals(lockedSettings)) {
                unlock(mc, "the egg settings changed");
            } else if (java.util.Objects.equals(myRgb, lockedRgb) || !mc.player.isAlive() || mc.player.isSpectator()) {
                // same color - or you are dead or spectating, when servers often give you another
                // color for a while ("respawning" team): keep guarding with the color you had
                colorMismatchTicks = 0;
                colorlessTicks = 0;
            } else if (cfg.colorOverride.isBlank()) {
                // Servers sometimes drop and re-add a team for a moment: pause, and only stop
                // guarding when the change lasts.
                colorSteady = false;
                if (++colorMismatchTicks >= COLOR_CHANGE_TICKS) {
                    unlock(mc, myRgb == null ? "your name lost its team color" : "your team color changed");
                }
            } else if (myRgb == null) {
                // typed color name, but your name has no color: your teammates' names probably have
                // none either - with "Ignore my team" wait until it is back
                colorMismatchTicks = 0;
                if (cfg.ignoreTeammates) {
                    colorSteady = false;
                    // Warnings waiting for their group window stay until the color is back (a
                    // teammate whose color came back late is then taken out of them as usual);
                    // after 1 s they are dropped - they could name a teammate.
                    if (++colorlessTicks == COLOR_CHANGE_TICKS) {
                        tracker.clearPending();
                    }
                }
            } else if (++colorMismatchTicks < COLOR_CHANGE_TICKS) {
                colorSteady = false; // typed color: only "Ignore my team" needs the tab color
            } else {
                lockedRgb = myRgb; // your tab color really changed: teammates have the new one
                colorMismatchTicks = 0;
            }
        }

        watchPaused = !colorSteady;
        if (tick % SCAN_EVERY_TICKS == 0 || (egg == null && tick % 5 == 0)) {
            lastLabels = scan(mc, cfg);
            if (egg == null) {
                tryLock(mc, cfg, now, settingsKey);
            } else {
                follow(mc);
            }
        }
        if (egg != null) {
            checkEggStillThere(mc);
        }
        if (egg != null && colorSteady && now >= armedAtMs) {
            watchPlayers(mc, conn, cfg, now);
        }
        sender.tick(mc, conn, now, (long) (cfg.messageGapSeconds * 1000));
    }

    private void resetSession() {
        tracker.reset();
        sender.reset();
        egg = null;
        lockedRgb = null;
        lastLevel = null;
        lastLabels = List.of();
        roundEggs.clear();
        myRgb = null;
        myNames = List.of();
        eggMissingTicks = 0;
    }

    private void unlock(Minecraft mc, @Nullable String reason) {
        unlock(mc, reason, false);
    }

    /** @param keepQueue keep warnings that are still waiting to be sent (the egg vanished: they still matter) */
    private void unlock(Minecraft mc, @Nullable String reason, boolean keepQueue) {
        if (!keepQueue) {
            sender.clear(); // e.g. don't type "ALERT ... at our egg" in the lobby after the round
        } else if (egg != null && !watchPaused) {
            // the egg vanished: warnings still waiting for their group window go out now
            for (IntruderTracker.Alert a : tracker.flush(nowMs(), 0, true)) {
                send(mc, EggerConfig.get(), a);
            }
        }
        if (egg != null && reason != null) {
            LOG.info("Egger Detector: stopped guarding {}: {}", labelName(egg), reason);
        }
        egg = null;
        lockedRgb = null;
        waiting = "looking for your egg";
        eggMissingTicks = 0;
        colorMismatchTicks = 0;
        labelMissingScans = 0;
        tracker.forgetPositions();
        tracker.clearPending();
    }

    // ------------------------------------------------------------------ labels

    private List<Label> scan(Minecraft mc, EggerConfig cfg) {
        ClientLevel level = mc.level;
        LabelParser parser = new LabelParser(cfg.labelFormat);
        Set<String> known = ColorMatcher.knownNames(cfg.palette, cfg.colorOverride);
        List<Label> found = new ArrayList<>();
        List<double[]> eggEntities = new ArrayList<>();
        for (Entity e : level.entitiesForRendering()) {
            if (e instanceof Player) {
                continue;
            }
            if (e instanceof Display.BlockDisplay bd) {
                Display.BlockDisplay.BlockRenderState st = bd.blockRenderState();
                if (st != null && st.blockState().getBlock() == Blocks.DRAGON_EGG) {
                    eggEntities.add(new double[] {e.getX(), e.getY(), e.getZ()});
                }
            } else if (e instanceof Display.ItemDisplay id) {
                Display.ItemDisplay.ItemRenderState st = id.itemRenderState();
                if (st != null && st.itemStack().getItem() == Items.DRAGON_EGG) {
                    eggEntities.add(new double[] {e.getX(), e.getY(), e.getZ()});
                }
            }
            Component text = null;
            if (e instanceof Display.TextDisplay td) {
                Display.TextDisplay.TextRenderState st = td.textRenderState();
                if (st != null) {
                    text = st.text();
                }
            }
            if (text == null && e.hasCustomName()) {
                text = e.getCustomName();
            }
            if (text == null) {
                continue;
            }
            // decoded first: a legacy code anywhere (even inside "'s \u00A7lEgg") must not hide the label
            TabColors.Flat flat = TabColors.flatten(text);
            if (!parser.mightMatch(flat.text().toLowerCase(Locale.ROOT))) {
                continue;
            }
            readLabel(flat, parser, known, e, found);
        }
        // the dragon egg under (or next to) each label
        List<Label> out = new ArrayList<>(found.size());
        for (Label l : found) {
            BlockPos block = findEggBlock(level, l.x(), l.y(), l.z());
            double ex = l.x(), ez = l.z();
            boolean has = false;
            if (block != null) {
                has = true;
                ex = block.getX() + 0.5;
                ez = block.getZ() + 0.5;
            } else {
                for (double[] p : eggEntities) {
                    if (Math.abs(p[0] - l.x()) <= SEARCH_SIDE + 0.5 && Math.abs(p[2] - l.z()) <= SEARCH_SIDE + 0.5
                            && p[1] - l.y() <= SEARCH_UP && l.y() - p[1] <= SEARCH_DOWN) {
                        has = true;
                        ex = p[0];
                        ez = p[2];
                        break;
                    }
                }
            }
            out.add(new Label(l.text(), l.phrase(), l.rgb(), l.x(), l.y(), l.z(), has, ex, ez, block));
        }
        return out;
    }

    /** Split the label into lines, keep the color of every character, find the color names. */
    private static void readLabel(TabColors.Flat flat, LabelParser parser, Set<String> known, Entity e, List<Label> out) {
        List<TextColor> colors = flat.colors();
        int lineStart = 0;
        String s = flat.text();
        for (int i = 0; i <= s.length(); i++) {
            if (i == s.length() || s.charAt(i) == '\n') {
                String line = s.substring(lineStart, i);
                LabelParser.Normalized n = LabelParser.normalize(line);
                for (LabelParser.Match m : parser.find(n.text(), known)) {
                    TextColor c = colors.get(lineStart + n.sourceIndex()[m.start()]);
                    out.add(new Label(line.strip(), m.phrase(), c == null ? null : c.getValue() & 0xFFFFFF,
                            e.getX(), e.getY(), e.getZ(), false, e.getX(), e.getZ(), null));
                }
                lineStart = i + 1;
            }
        }
    }

    /** Nearest dragon egg block around the label, looking mostly below it. */
    private static @Nullable BlockPos findEggBlock(ClientLevel level, double x, double y, double z) {
        int bx = (int) Math.floor(x), by = (int) Math.floor(y), bz = (int) Math.floor(z);
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos();
        BlockPos best = null;
        int bestScore = Integer.MAX_VALUE;
        for (int dx = -SEARCH_SIDE; dx <= SEARCH_SIDE; dx++) {
            for (int dz = -SEARCH_SIDE; dz <= SEARCH_SIDE; dz++) {
                for (int dy = SEARCH_UP; dy >= -SEARCH_DOWN; dy--) {
                    p.set(bx + dx, by + dy, bz + dz);
                    if (!level.isLoaded(p) || level.getBlockState(p).getBlock() != Blocks.DRAGON_EGG) {
                        continue;
                    }
                    int score = (dx * dx + dz * dz) * 100 + Math.abs(dy);
                    if (score < bestScore) {
                        bestScore = score;
                        best = p.immutable();
                    }
                }
            }
        }
        return best;
    }

    /** Why the round's egg can't be taken again, or null when the round memory is not what stopped it. */
    private @Nullable String roundWaiting(EggerConfig cfg, Label closest) {
        RoundEgg round = roundEggs.get(myRgb);
        if (round == null || (cfg.closestEggOnly && round.phrase().equals(closest.phrase()))) {
            return null;
        }
        String roundText = round.text();
        Label seen = null;
        for (Label l : lastLabels) {
            if (round.phrase().equals(l.phrase())) {
                seen = l;
                if (usable(l, cfg)) {
                    break;
                }
            }
        }
        if (seen == null) {
            return roundText + " (your egg this round) is not in sight";
        }
        if (!usable(seen, cfg)) {
            return roundText + " (your egg this round) has no dragon egg under it";
        }
        return cfg.closestEggOnly ? roundText + " (your egg this round) is not the closest egg" : null;
    }

    /** Before the first lock of a round any egg can be ours; after it, only one with the same name. */
    private boolean sameRound(Label l) {
        RoundEgg round = roundEggs.get(myRgb);
        return round == null || round.phrase().equals(l.phrase());
    }

    private static boolean usable(Label l, EggerConfig cfg) {
        return l.hasEgg() || !cfg.requireDragonEgg;
    }

    private void tryLock(Minecraft mc, EggerConfig cfg, long now, String settingsKey) {
        boolean manual = !cfg.colorOverride.isBlank();
        if (!mc.player.isAlive() || mc.player.isSpectator()) {
            // while you wait to respawn (or watch) the server may give you another color for a moment
            waiting = "you are dead or spectating";
            return;
        }
        if (myRgb == null && (!manual || cfg.ignoreTeammates)) {
            // (with a typed color name too: "Ignore my team" can't tell teammates apart without it)
            waiting = "your name has no team color yet";
            return;
        }
        if (!settingsKey.equals(roundSettings)) {
            roundEggs.clear(); // new egg settings: a new start
            roundSettings = settingsKey;
        }
        double px = mc.player.getX(), pz = mc.player.getZ();
        Label pick = null;
        ColorMatcher.Verdict verdict = null;
        double best = Double.MAX_VALUE;
        Label closest = null;
        double closestD = Double.MAX_VALUE;
        for (Label l : lastLabels) {
            if (!usable(l, cfg)) {
                continue;
            }
            double d = Math.hypot(l.eggX() - px, l.eggZ() - pz);
            if (d < closestD) {
                closestD = d;
                closest = l;
            }
            if (!cfg.closestEggOnly && sameRound(l)) {
                ColorMatcher.Verdict v = ColorMatcher.matches(l.phrase(), l.rgb(), cfg.colorOverride, myRgb, cfg.palette);
                if (v != null && d < best) {
                    best = d;
                    pick = l;
                    verdict = v;
                }
            }
        }
        if (cfg.closestEggOnly && closest != null && sameRound(closest)) {
            verdict = ColorMatcher.matches(closest.phrase(), closest.rgb(), cfg.colorOverride, myRgb, cfg.palette);
            if (verdict != null) {
                pick = closest;
            }
        }
        if (pick == null) {
            if (closest == null) {
                boolean labelsWithoutEgg = !lastLabels.isEmpty();
                waiting = labelsWithoutEgg ? "egg labels in sight, but no dragon egg under them" : "no egg label in sight";
            } else {
                String why = roundWaiting(cfg, closest);
                waiting = why != null ? why
                        : cfg.closestEggOnly ? "closest egg is " + closest.text() + ", not yours" : "none of the eggs in sight is yours";
            }
            return;
        }
        egg = new Egg(pick.phrase(), verdict.colorName(), pick.text(), pick.rgb(), pick.eggX(), pick.eggZ(), pick.eggBlock());
        lockedRgb = myRgb;
        lockedSettings = settingsKey;
        roundEggs.put(myRgb, new RoundEgg(pick.phrase(), pick.text()));
        eggMissingTicks = 0;
        colorMismatchTicks = 0;
        labelMissingScans = 0;
        armedAtMs = now + (long) (cfg.startDelaySeconds * 1000);
        tracker.forgetPositions();
        tracker.clearPending();
        waiting = "";
        LOG.info("Egger Detector: guarding {} at {}, {} (color {} via {})", pick.text(), fmt(egg.x()), fmt(egg.z()),
                myRgb == null ? "none" : ColorMatcher.hex(myRgb), verdict.source());
    }

    /** While locked: if our egg's label shows up somewhere else, the egg was moved. */
    private void follow(Minecraft mc) {
        EggerConfig cfg = EggerConfig.get();
        Label same = null;
        double best = Double.MAX_VALUE;
        for (Label l : lastLabels) {
            if (!l.phrase().equals(egg.phrase()) || !usable(l, cfg)) {
                continue;
            }
            double d = Math.hypot(l.eggX() - egg.x(), l.eggZ() - egg.z());
            if (d < best) {
                best = d;
                same = l;
            }
        }
        boolean seenHere = same != null && best <= 1.5;
        if (egg.block() == null) {
            // no block to check: the name itself tells us the egg is still there
            double me = Math.hypot(mc.player.getX() - egg.x(), mc.player.getZ() - egg.z());
            if (seenHere) {
                labelMissingScans = 0;
            } else if (me <= LABEL_SURE_RANGE && ++labelMissingScans >= LABEL_MISSING_SCANS) {
                if (cfg.sound) {
                    mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.NOTE_BLOCK_BASS, 0.6f));
                }
                unlock(mc, "the name above your egg is gone", true);
                return;
            }
        }
        if (same == null) {
            return;
        }
        if (!seenHere && egg.block() != null && (!mc.level.isLoaded(egg.block())
                || mc.level.getBlockState(egg.block()).getBlock() == Blocks.DRAGON_EGG)) {
            // our egg is still there (or too far away to check): a same-named label elsewhere is
            // another egg (or a display)
            return;
        }
        if (seenHere) {
            // same egg; it may have dropped a block (dragon eggs fall) or shifted a little:
            // keep checking the block where it is now
            if (same.eggBlock() != null && !same.eggBlock().equals(egg.block())) {
                egg = egg.moveTo(same);
                eggMissingTicks = 0;
            }
            return;
        }
        egg = egg.moveTo(same);
        labelMissingScans = 0;
        eggMissingTicks = 0;
        tracker.forgetPositions();
        LOG.info("Egger Detector: egg moved to {}, {}", fmt(egg.x()), fmt(egg.z()));
    }

    private void checkEggStillThere(Minecraft mc) {
        BlockPos b = egg.block();
        if (b == null || !mc.level.isLoaded(b)) {
            eggMissingTicks = 0;
            return;
        }
        if (mc.level.getBlockState(b).getBlock() == Blocks.DRAGON_EGG) {
            eggMissingTicks = 0;
            return;
        }
        if (++eggMissingTicks >= EGG_MISSING_TICKS) {
            String where = b.getX() + ", " + b.getZ();
            if (EggerConfig.get().sound) {
                mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.NOTE_BLOCK_BASS, 0.6f));
            }
            unlock(mc, "the dragon egg is no longer at " + where, true);
        }
    }

    // ------------------------------------------------------------------ players

    private void watchPlayers(Minecraft mc, ClientPacketListener conn, EggerConfig cfg, long now) {
        List<IntruderTracker.Observation> seen = new ArrayList<>();
        List<UUID> notCounted = new ArrayList<>(0);
        UUID self = mc.player.getUUID();
        // your team's color: the one you had when guarding started (with a typed color name, the
        // tab color you changed to); while it differs for a moment, watching is paused
        Integer teamRgb = lockedRgb;
        if (cfg.ignoreTeammates && teamRgb == null) {
            return; // "Ignore my team" switched on after guarding started without a tab color
        }
        for (AbstractClientPlayer p : mc.level.players()) {
            if (p == mc.player || self.equals(p.getUUID())) {
                continue;
            }
            PlayerInfo info = conn.getPlayerInfo(p.getUUID());
            boolean counts = p.isAlive() && !p.isSpectator()
                    // not shown in the tab list: an NPC, not a player
                    && info != null && info.getGameMode() != GameType.SPECTATOR && conn.getListedOnlinePlayers().contains(info)
                    && !cfg.isIgnored(info.getProfile().name())
                    // (watching is paused while your color differs from the locked one for a moment)
                    && !(cfg.ignoreTeammates && teamRgb != null && teamRgb.equals(TabColors.nameColor(mc, info)));
            if (!counts) {
                notCounted.add(p.getUUID()); // e.g. their team color arrived a tick late: no message about them
                continue;
            }
            String name = info.getProfile().name();
            // where the server says they are: the game slides other players there over 3 ticks,
            // which would make a teleport look like a walk through every radius on the way
            InterpolationHandler lerp = p.getInterpolation();
            Vec3 at = lerp != null ? lerp.position() : p.position();
            seen.add(new IntruderTracker.Observation(p.getUUID(), name, Math.hypot(at.x - egg.x(), at.z - egg.z())));
        }
        TreeSet<Integer> radii = new TreeSet<>();
        for (RadiusRule r : cfg.radii) {
            if (warns(r)) {
                radii.add(r.radius);
            }
        }
        int[] sorted = radii.stream().mapToInt(Integer::intValue).toArray();
        tracker.dropPending(notCounted);
        List<IntruderTracker.Alert> alerts = tracker.update(now, seen, sorted,
                // at least 2 ticks, even with "0": a teammate whose team color arrives a tick late
                // is dropped (dropPending above) before anything is sent
                (long) (cfg.cooldownSeconds * 1000), Math.max(MIN_GROUP_MS, (long) (cfg.groupSeconds * 1000)));
        for (IntruderTracker.Alert a : alerts) {
            send(mc, cfg, a);
        }
    }

    private void send(Minecraft mc, EggerConfig cfg, IntruderTracker.Alert a) {
        LOG.info("Egger Detector: {} came inside {} blocks", a.names(), a.radius());
        boolean any = false;
        for (RadiusRule r : cfg.radii) {
            if (!r.enabled || r.radius != a.radius()) {
                continue;
            }
            String text = MessageFormatter.format(r.message, a.names(), r.radius, egg.colorName());
            if (text.isBlank()) {
                continue;
            }
            any = true;
            if (r.mode == RadiusRule.Mode.CHAT) {
                sender.enqueue(mc, text, nowMs());
            } else {
                MessageSender.local(mc, Component.literal(text).withStyle(ChatFormatting.RED));
            }
        }
        if (any && cfg.sound) {
            mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.NOTE_BLOCK_PLING, a.radius() <= smallestRadius(cfg) ? 2.0f : 1.4f));
        }
    }

    /** A radius that can warn: switched on and with a message (one with no message would only swallow the others). */
    private static boolean warns(RadiusRule r) {
        return r.enabled && !MessageFormatter.clean(r.message).isBlank();
    }

    private static int smallestRadius(EggerConfig cfg) {
        int s = Integer.MAX_VALUE;
        for (RadiusRule r : cfg.radii) {
            if (warns(r)) {
                s = Math.min(s, r.radius);
            }
        }
        return s;
    }

    // ------------------------------------------------------------------ for the settings screen

    /** Lines for the top of the settings screen. */
    List<Component> statusLines(Minecraft mc) {
        List<Component> lines = new ArrayList<>();
        EggerConfig cfg = EggerConfig.get();
        if (mc.level == null || mc.player == null) {
            lines.add(Component.literal("Join a server to see what is detected.").withStyle(ChatFormatting.GRAY));
            return lines;
        }
        if (failed) {
            lines.add(Component.literal("Stopped because of an error - it starts again when you rejoin.").withStyle(ChatFormatting.RED));
        }
        if (!cfg.colorOverride.isBlank()) {
            lines.add(Component.literal("Your color: " + cfg.colorOverride.strip() + " (typed in below)").withStyle(ChatFormatting.WHITE));
        } else if (myRgb == null) {
            lines.add(Component.literal("Your name has no team color in the tab list yet.").withStyle(ChatFormatting.GRAY));
        } else {
            lines.add(Component.literal("Your tab color: ").withStyle(ChatFormatting.WHITE)
                    .append(Component.literal(ColorMatcher.hex(myRgb) + " " + String.join(" / ", myNames)).withStyle(s -> s.withColor(myRgb))));
        }
        if (egg != null) {
            double d = Math.hypot(mc.player.getX() - egg.x(), mc.player.getZ() - egg.z());
            lines.add(Component.literal("Guarding " + labelName(egg) + " at " + fmt(egg.x()) + ", " + fmt(egg.z()) + " (" + (int) d + " blocks from you)")
                    .withStyle(ChatFormatting.GREEN));
        } else {
            lines.add(Component.literal("Not guarding: " + (cfg.enabled ? waiting : "switched off")).withStyle(ChatFormatting.YELLOW));
        }
        return lines;
    }

    /** Your color name as the placeholder [color] would say it, for the message preview. */
    String previewColorName() {
        if (egg != null) {
            return egg.colorName();
        }
        EggerConfig cfg = EggerConfig.get();
        if (!cfg.colorOverride.isBlank()) {
            return cfg.colorOverride.strip();
        }
        return myNames.isEmpty() ? "Orange" : myNames.getFirst();
    }

    boolean isFailed() {
        return failed;
    }

    private static String labelName(Egg e) {
        return e.labelText();
    }

    private static String fmt(double v) {
        return Integer.toString((int) Math.floor(v));
    }
}
