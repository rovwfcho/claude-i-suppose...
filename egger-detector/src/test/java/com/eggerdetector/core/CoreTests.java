package com.eggerdetector.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Plain-Java checks of the game-independent logic (no test library needed):
 * {@code java -cp <classes> com.eggerdetector.core.CoreTests}. Exits non-zero on a failure.
 */
public final class CoreTests {
    private static int passed;
    private static final List<String> failures = new ArrayList<>();

    private CoreTests() {
    }

    public static void main(String[] args) {
        labels();
        colors();
        tracker();
        formatter();
        System.out.println(passed + " checks passed, " + failures.size() + " failed");
        for (String f : failures) {
            System.out.println("FAIL " + f);
        }
        if (!failures.isEmpty()) {
            System.exit(1);
        }
    }

    private static void check(boolean ok, String what) {
        if (ok) {
            passed++;
        } else {
            failures.add(what);
        }
    }

    private static void eq(Object expected, Object actual, String what) {
        check(java.util.Objects.equals(expected, actual), what + ": expected <" + expected + "> got <" + actual + ">");
    }

    // ------------------------------------------------------------------ labels

    private static String phrase(LabelParser p, String text, Set<String> known) {
        List<LabelParser.Match> m = p.find(LabelParser.normalize(text).text(), known);
        return m.isEmpty() ? null : m.getFirst().phrase();
    }

    private static void labels() {
        Set<String> known = ColorMatcher.knownNames(ColorMatcher.defaultPalette(), "");
        LabelParser p = new LabelParser(LabelParser.DEFAULT_FORMAT);
        eq("orange", phrase(p, "Orange's Egg", known), "plain label");
        eq("orange", phrase(p, "Orange\u2019s Egg", known), "curly apostrophe");
        eq("orange", phrase(p, "ORANGE'S EGG", known), "upper case");
        eq("orange", phrase(p, "  Orange's   Egg ", known), "extra spaces");
        eq("light blue", phrase(p, "\u2726 Light Blue's Egg \u2726", known), "two-word name with decoration");
        eq("dark blue", phrase(p, "Dark Blue's Egg", known), "longest known name wins");
        eq("pink", phrase(p, "Team Pink's Egg", known), "unknown word before the color");
        eq("bob", phrase(p, "Bob's Egg", known), "unknown single word still parsed");
        eq(null, phrase(p, "Pink's Eggs", known), "plural is not a label");
        eq(null, phrase(p, "Bob's Egghead", known), "longer word is not a label");
        eq(null, phrase(p, "Pink Egg", known), "no apostrophe s");
        eq(null, phrase(p, "'s Egg", known), "no name");
        eq("orange", phrase(p, "Orange's Egg (3 lives)", known), "text after the label");
        LabelParser.Normalized n = LabelParser.normalize("Orange's  Egg");
        eq("orange's egg", n.text(), "normalize");
        eq(10, n.sourceIndex()[9], "source index after collapsed space");
        eq(9, n.sourceIndex()[8], "collapsed space maps to the last space");
        check(p.mightMatch("orange's egg"), "pre-filter accepts label");
        check(!p.mightMatch("steve"), "pre-filter rejects other names");
        LabelParser custom = new LabelParser("Egg of {color}");
        eq("red", phrase(custom, "Egg of Red", known), "custom format, name at the end");
        eq("light blue", phrase(custom, "Egg of Light Blue (3)", known), "custom format, two words");
        LabelParser broken = new LabelParser("no placeholder");
        eq("orange", phrase(broken, "Orange's Egg", known), "format without {color} falls back to default");
    }

    // ------------------------------------------------------------------ colors

    private static void colors() {
        List<ColorMatcher.Entry> pal = ColorMatcher.defaultPalette();
        // the server in the screenshots: [O] gold, [P] light purple, [LB] aqua, [GA] gray, [R] red, [Y] yellow
        eq("Orange", verdictName("orange", 0xFFAA00, "", 0xFFAA00), "orange team");
        eq("Pink", verdictName("pink", 0xFF55FF, "", 0xFF55FF), "pink team");
        eq("Light Blue", verdictName("light blue", 0x55FFFF, "", 0x55FFFF), "light blue team");
        eq("Gray", verdictName("gray", 0xAAAAAA, "", 0xAAAAAA), "gray team");
        eq("Red", verdictName("red", 0xFF5555, "", 0xFF5555), "red team");
        eq("Yellow", verdictName("yellow", 0xFFFF55, "", 0xFFFF55), "yellow team");
        eq("Orange", verdictName("orange", null, "", 0xFFA500), "hex orange name, uncolored label");
        eq(null, verdictName("pink", 0xFF55FF, "", 0xFFAA00), "orange player, pink egg");
        eq(null, verdictName("orange", 0xFFAA00, "", null), "no team color yet (glass boxes)");
        eq("Orange", verdictName("orange", null, "Orange", null), "typed color name");
        eq(null, verdictName("pink", null, "Orange", 0xFF55FF), "typed color name beats tab color");
        ColorMatcher.Verdict v = ColorMatcher.matches("crimson", 0x123456, "", 0x123456, pal);
        eq(ColorMatcher.Source.LABEL_COLOR, v == null ? null : v.source(), "label drawn in my exact color");
        eq(null, verdictName("pink", 0xFFFFFF, "", 0xFFFFFF), "white on white is not trusted");
        eq("White", verdictName("white", 0xFFFFFF, "", 0xFFFFFF), "white team by name");
        eq(null, verdictName("blue", 0x5555FF, "", 0x55FFFF), "light blue player is not on blue");
        eq(null, verdictName("blue", 0x55FFFF, "", 0x55FFFF), "label in my color but another team's color name");
        eq("Dragons", verdictName("dragons", 0x55FFFF, "", 0x55FFFF), "team name that is not a color, label in my color");
        eq("#FFAA00", ColorMatcher.hex(0xFFAA00), "hex");
        eq("Light Blue", ColorMatcher.titleCase("light blue"), "title case");
    }

    private static String verdictName(String phrase, Integer labelRgb, String override, Integer myRgb) {
        ColorMatcher.Verdict v = ColorMatcher.matches(phrase, labelRgb, override, myRgb, ColorMatcher.defaultPalette());
        return v == null ? null : v.colorName();
    }

    // ------------------------------------------------------------------ tracker

    private static final UUID A = new UUID(0, 1), B = new UUID(0, 2), C = new UUID(0, 3);
    private static final int[] RADII = {15, 50};
    private static final int[] RADII3 = {15, 30, 50};
    private static final long CD = 20_000;

    private static IntruderTracker.Observation o(UUID id, double d) {
        return new IntruderTracker.Observation(id, id == A ? "A" : id == B ? "B" : "C", d);
    }

    private static String run(IntruderTracker t, long now, int[] radii, long group, IntruderTracker.Observation... obs) {
        List<IntruderTracker.Alert> alerts = t.update(now, List.of(obs), radii, CD, group);
        StringBuilder b = new StringBuilder();
        for (IntruderTracker.Alert a : alerts) {
            if (b.length() > 0) {
                b.append(' ');
            }
            b.append(a.radius()).append(a.names());
        }
        return b.toString();
    }

    private static void tracker() {
        IntruderTracker t = new IntruderTracker();
        eq("", run(t, 0, RADII, 0, o(A, 100)), "outside");
        eq("", run(t, 50, RADII, 0, o(A, 60)), "still outside");
        eq("50[A]", run(t, 100, RADII, 0, o(A, 49)), "walks into 50");
        eq("", run(t, 150, RADII, 0, o(A, 30)), "inside 50, no repeat");
        eq("15[A]", run(t, 200, RADII, 0, o(A, 14)), "walks into 15");
        eq("", run(t, 250, RADII, 0, o(A, 20)), "leaving 15 says nothing");
        eq("", run(t, 300, RADII, 0, o(A, 14)), "back into 15 inside the cooldown");
        eq("", run(t, 350, RADII, 0, o(A, 100)), "leaving everything says nothing");
        eq("", run(t, 400, RADII, 0, o(A, 49)), "back into 50 inside its cooldown");
        eq("", run(t, 20_150, RADII, 0, o(A, 60)), "out again");
        eq("50[A]", run(t, 20_200, RADII, 0, o(A, 49)), "50 again after its 20 s");
        eq("", run(t, 20_250, RADII, 0, o(A, 20)), "between");
        eq("15[A]", run(t, 20_300, RADII, 0, o(A, 14)), "15 again after its 20 s");

        // exactly on the line counts as inside
        t = new IntruderTracker();
        run(t, 0, RADII, 0, o(A, 60));
        eq("50[A]", run(t, 50, RADII, 0, o(A, 50.0)), "distance equal to the radius");

        // appearing already inside: the radius they are in, not the next one in front of them
        t = new IntruderTracker();
        eq("30[A]", run(t, 0, RADII3, 0, o(A, 25)), "appears at 25 -> radius 30, not 15");
        t = new IntruderTracker();
        eq("50[A]", run(t, 0, RADII3, 0, o(A, 40)), "appears at 40 -> 50");
        t = new IntruderTracker();
        eq("", run(t, 0, RADII3, 0, o(A, 80)), "appears outside");

        // teleport across several radii: only the innermost, and only it gets the cooldown
        t = new IntruderTracker();
        run(t, 0, RADII3, 0, o(A, 100));
        eq("15[A]", run(t, 50, RADII3, 0, o(A, 5)), "teleport 100 -> 5: only 15");
        eq("", run(t, 100, RADII3, 0, o(A, 100)), "back out");
        eq("50[A]", run(t, 150, RADII3, 0, o(A, 45)), "50 has no cooldown, it never spoke");
        eq("30[A]", run(t, 200, RADII3, 0, o(A, 29)), "30 has no cooldown either");
        eq("", run(t, 250, RADII3, 0, o(A, 14)), "15 is on cooldown");

        // out of sight and back: counts as appearing again (cooldown still applies)
        t = new IntruderTracker();
        eq("50[A]", run(t, 0, RADII, 0, o(A, 40)), "appears in 50");
        eq("", run(t, 50, RADII, 0), "gone from view");
        eq("", run(t, 100, RADII, 0, o(A, 40)), "back in view, 50 on cooldown");
        eq("", run(t, 150, RADII, 0), "gone again");
        eq("50[A]", run(t, 20_100, RADII, 0, o(A, 40)), "back in view after the cooldown");

        // grouping: same radius within the window -> one message
        t = new IntruderTracker();
        run(t, 0, RADII, 1000, o(A, 100), o(B, 100), o(C, 100));
        eq("", run(t, 100, RADII, 1000, o(A, 45), o(B, 100), o(C, 100)), "A in, waiting for others");
        eq("", run(t, 600, RADII, 1000, o(A, 44), o(B, 45), o(C, 100)), "B joins the same message");
        eq("50[A, B]", run(t, 1100, RADII, 1000, o(A, 44), o(B, 44), o(C, 100)), "window closes");
        eq("", run(t, 1500, RADII, 1000, o(A, 44), o(B, 44), o(C, 45)), "C later");
        eq("50[C]", run(t, 2500, RADII, 1000, o(A, 44), o(B, 44), o(C, 44)), "C alone");

        // going deeper while the bigger radius still waits: only the innermost speaks
        t = new IntruderTracker();
        run(t, 0, RADII, 1000, o(A, 100), o(B, 100));
        run(t, 100, RADII, 1000, o(A, 45), o(B, 45));
        run(t, 300, RADII, 1000, o(A, 10), o(B, 45));
        eq("50[B]", run(t, 1100, RADII, 1000, o(A, 10), o(B, 45)), "B stays in the 50 message");
        eq("15[A]", run(t, 1300, RADII, 1000, o(A, 10), o(B, 45)), "A only in the 15 message");
        run(t, 1400, RADII, 1000, o(A, 100), o(B, 45));
        run(t, 1500, RADII, 1000, o(A, 45), o(B, 45));
        eq("50[A]", run(t, 2500, RADII, 1000, o(A, 45), o(B, 45)), "50 never spoke for A, so no cooldown");

        // going deeper within the window into a radius that is on cooldown: nothing at all
        t = new IntruderTracker();
        run(t, 0, RADII, 1000, o(A, 100));
        run(t, 100, RADII, 1000, o(A, 10));
        eq("15[A]", run(t, 1100, RADII, 1000, o(A, 10)), "first visit to 15");
        run(t, 1200, RADII, 1000, o(A, 100));
        run(t, 1300, RADII, 1000, o(A, 45));
        run(t, 1400, RADII, 1000, o(A, 10));
        eq("", run(t, 2400, RADII, 1000, o(A, 10)), "50 dropped because A went on into 15 (on cooldown)");

        // a player who stops counting inside the group window is left out of the message
        t = new IntruderTracker();
        run(t, 0, RADII, 1000, o(A, 100), o(B, 100));
        run(t, 100, RADII, 1000, o(A, 40), o(B, 40));
        t.dropPending(List.of(A));
        eq("50[B]", run(t, 1100, RADII, 1000, o(B, 40)), "A dropped from the waiting message");
        run(t, 1200, RADII, 1000, o(A, 100));
        run(t, 1300, RADII, 1000, o(A, 40));
        t.dropPending(List.of(A));
        eq("", run(t, 2300, RADII, 1000), "message with only A is gone");

        // per-player cooldown: another player is not blocked
        t = new IntruderTracker();
        run(t, 0, RADII, 0, o(A, 100), o(B, 100));
        eq("50[A]", run(t, 50, RADII, 0, o(A, 40), o(B, 100)), "A");
        eq("50[B]", run(t, 100, RADII, 0, o(A, 40), o(B, 40)), "B right after A");

        // HUD helpers and forgetting positions
        eq(2, t.countInside(50), "count inside");
        check(Math.abs(t.nearestDistance() - 40) < 1e-9, "nearest distance");
        t.forgetPositions();
        eq("", run(t, 150, RADII, 0, o(A, 40), o(B, 40)), "forgotten, but still on cooldown");
        t.reset();
        eq("50[A, B]", run(t, 200, RADII, 0, o(A, 40), o(B, 40)), "reset clears cooldowns");

        // radius list changes while someone is inside: a new outer radius they are already in says nothing
        t = new IntruderTracker();
        run(t, 0, new int[] {15}, 0, o(A, 30));
        eq("", run(t, 50, new int[] {15, 50}, 0, o(A, 30)), "new radius around a player already seen");
        // NaN distance is treated as not seen
        eq("", run(t, 100, RADII, 0, o(A, Double.NaN)), "NaN");
        eq("15[A]", run(t, 150, RADII, 0, o(A, 10)), "after NaN they count as appearing");
    }

    // ------------------------------------------------------------------ messages

    private static void formatter() {
        eq("A, B near our egg", MessageFormatter.format("[players] near our egg", List.of("A", "B"), 50, "Orange"), "[players]");
        eq("A and B !", MessageFormatter.format("[player1] and [player 2] [player3]!", List.of("A", "B"), 50, "Orange"), "[playerN], missing one is empty");
        eq("2 at 15 near Orange", MessageFormatter.format("[count] at [RADIUS] near [Color]", List.of("A", "B"), 15, "Orange"), "count radius color, any case");
        eq("hi there", MessageFormatter.format("hi\u00A7c\nthere", List.of(), 1, ""), "section sign and newline removed");
        eq("/teammsg A is here", MessageFormatter.format("/teammsg [players] is here", List.of("A"), 1, ""), "command kept");
        eq("[nope] A", MessageFormatter.format("[nope] [players]", List.of("A"), 1, ""), "unknown placeholder kept");
        eq("$1 A", MessageFormatter.format("$1 [players]", List.of("A"), 1, ""), "dollar sign is literal");
        List<String> many = new ArrayList<>();
        for (int i = 0; i < 40; i++) {
            many.add("Player_" + String.format("%09d", i));
        }
        String s = MessageFormatter.format("Alert: [players] at the egg!", many, 15, "");
        check(s.length() <= MessageFormatter.MAX_CHAT_LENGTH, "long list fits 256 (" + s.length() + ")");
        check(s.contains(" more") && s.endsWith("at the egg!"), "long list shortened with +N more: " + s);
        String longText = "x".repeat(300);
        eq(256, MessageFormatter.format(longText, List.of(), 1, "").length(), "long message cut at 256");
    }
}
