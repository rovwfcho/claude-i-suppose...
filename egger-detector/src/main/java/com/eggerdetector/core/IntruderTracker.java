package com.eggerdetector.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;

/**
 * Decides when a player has come inside one of the warning radii around the egg.
 *
 * <ul>
 *   <li>Only coming in counts, going out never does.</li>
 *   <li>A player crossing several radii at once (teleport, appearing already inside) only
 *       triggers the innermost radius they are now inside of.</li>
 *   <li>A player not seen in the previous update (just came into view, logged in,
 *       teleported in) counts as coming in from outside.</li>
 *   <li>Cooldown per player <em>and</em> per radius: only the radius that actually sent a
 *       message is blocked for that player.</li>
 *   <li>Players coming into the same radius within the group window share one message.</li>
 * </ul>
 *
 * <p>Pure Java, no game classes; distances are computed by the caller. Not thread safe:
 * use it from one thread (the client thread).
 */
public final class IntruderTracker {
    /** A player seen this update and their horizontal distance to the egg. */
    public record Observation(UUID id, String name, double distance) {
    }

    /** A message to send: these players came inside {@code radius}. */
    public record Alert(int radius, List<String> names) {
    }

    private static final class State {
        double lastDistance = Double.POSITIVE_INFINITY;
        boolean present;
        boolean seen;
    }

    private static final class Batch {
        final long startMs;
        final LinkedHashMap<UUID, String> members = new LinkedHashMap<>();

        Batch(long startMs) {
            this.startMs = startMs;
        }
    }

    private final Map<UUID, State> states = new HashMap<>();
    /** player -> radius -> time the radius last sent a message for them. */
    private final Map<UUID, Map<Integer, Long>> lastSent = new HashMap<>();
    /** radius -> players waiting for the group window to close. */
    private final TreeMap<Integer, Batch> pending = new TreeMap<>();

    /**
     * Feed one update.
     *
     * @param radii enabled radii, ascending, no duplicates
     * @return alerts whose group window closed now (may be empty)
     */
    public List<Alert> update(long nowMs, List<Observation> seen, int[] radii, long cooldownMs, long groupMs) {
        for (State s : states.values()) {
            s.seen = false;
        }
        for (Observation o : seen) {
            State s = states.computeIfAbsent(o.id(), k -> new State());
            if (s.seen) {
                continue; // same player twice in one update: keep the first
            }
            s.seen = true;
            double prev = s.present ? s.lastDistance : Double.POSITIVE_INFINITY;
            double d = o.distance();
            if (Double.isNaN(d)) {
                s.present = false;
                continue;
            }
            s.present = true;
            s.lastDistance = d;
            // innermost radius they are inside now; it is "newly entered" only if they were outside it before
            for (int r : radii) {
                if (d <= r) {
                    if (!(prev <= r)) {
                        enter(o, r, nowMs, cooldownMs);
                    }
                    break;
                }
            }
        }
        states.values().removeIf(s -> !s.seen); // out of sight: next time they count as appearing
        pruneCooldowns(nowMs, cooldownMs);
        return flush(nowMs, groupMs, false);
    }

    private void enter(Observation o, int radius, long nowMs, long cooldownMs) {
        // Went deeper while a bigger radius was still waiting for its group window: only the
        // innermost one speaks - even if it is on cooldown and therefore says nothing.
        Iterator<Map.Entry<Integer, Batch>> it = pending.tailMap(radius, false).entrySet().iterator();
        while (it.hasNext()) {
            Batch bigger = it.next().getValue();
            bigger.members.remove(o.id());
            if (bigger.members.isEmpty()) {
                it.remove();
            }
        }
        Map<Integer, Long> sent = lastSent.get(o.id());
        Long last = sent == null ? null : sent.get(radius);
        if (last != null && nowMs - last < cooldownMs) {
            return;
        }
        Batch b = pending.get(radius);
        if (b != null && b.members.containsKey(o.id())) {
            return;
        }
        if (b == null) {
            b = new Batch(nowMs);
            pending.put(radius, b);
        }
        b.members.put(o.id(), o.name());
    }

    /** Alerts whose group window has closed (or all of them when {@code all}). Starts their cooldowns. */
    public List<Alert> flush(long nowMs, long groupMs, boolean all) {
        List<Alert> out = new ArrayList<>(0);
        Iterator<Map.Entry<Integer, Batch>> it = pending.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<Integer, Batch> e = it.next();
            Batch b = e.getValue();
            if (all || nowMs - b.startMs >= groupMs) {
                for (UUID id : b.members.keySet()) {
                    lastSent.computeIfAbsent(id, k -> new HashMap<>()).put(e.getKey(), nowMs);
                }
                out.add(new Alert(e.getKey(), List.copyOf(b.members.values())));
                it.remove();
            }
        }
        return out;
    }

    private void pruneCooldowns(long nowMs, long cooldownMs) {
        Iterator<Map<Integer, Long>> it = lastSent.values().iterator();
        while (it.hasNext()) {
            Map<Integer, Long> m = it.next();
            m.values().removeIf(t -> nowMs - t >= cooldownMs);
            if (m.isEmpty()) {
                it.remove();
            }
        }
    }

    /** Forget where everyone was: the next update treats every player as just appearing. Cooldowns stay. */
    public void forgetPositions() {
        states.clear();
    }

    /**
     * These players stopped counting (became a teammate, ignored, spectator, hidden NPC): take them
     * out of messages still waiting for their group window.
     */
    public void dropPending(java.util.Collection<UUID> ids) {
        if (ids.isEmpty() || pending.isEmpty()) {
            return;
        }
        Iterator<Batch> it = pending.values().iterator();
        while (it.hasNext()) {
            Batch b = it.next();
            b.members.keySet().removeAll(ids);
            if (b.members.isEmpty()) {
                it.remove();
            }
        }
    }

    /** Drop messages that are still waiting for their group window. */
    public void clearPending() {
        pending.clear();
    }

    /** Everything: positions, waiting messages and cooldowns. */
    public void reset() {
        states.clear();
        pending.clear();
        lastSent.clear();
    }

    /** Players currently inside {@code radius} according to the last update (for the HUD). */
    public int countInside(double radius) {
        int n = 0;
        for (State s : states.values()) {
            if (s.present && s.lastDistance <= radius) {
                n++;
            }
        }
        return n;
    }

    /** Nearest tracked player's distance, or +infinity. */
    public double nearestDistance() {
        double best = Double.POSITIVE_INFINITY;
        for (State s : states.values()) {
            if (s.present && s.lastDistance < best) {
                best = s.lastDistance;
            }
        }
        return best;
    }

    public boolean hasPending() {
        return !pending.isEmpty();
    }
}
