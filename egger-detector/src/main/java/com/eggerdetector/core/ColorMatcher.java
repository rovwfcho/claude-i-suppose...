package com.eggerdetector.core;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Turns the RGB color of your name in the tab list into the color name the server writes
 * on the eggs ("Orange's Egg"), and decides whether an egg label is yours.
 *
 * <p>Pure Java so it can be unit tested.
 */
public final class ColorMatcher {
    /** A palette color and the names a server may use for it, most likely first. */
    public record Entry(int rgb, List<String> names) {
        public Entry {
            names = List.copyOf(names);
        }
    }

    private ColorMatcher() {
    }

    /**
     * The 16 chat colors a scoreboard team can have, plus a few common hex colors.
     * Several names per color because servers call them differently (gold = "Orange",
     * aqua = "Light Blue", light purple = "Pink", ...).
     */
    public static List<Entry> defaultPalette() {
        List<Entry> p = new ArrayList<>();
        p.add(new Entry(0x000000, List.of("Black")));
        p.add(new Entry(0x0000AA, List.of("Dark Blue", "Navy", "Blue")));
        p.add(new Entry(0x00AA00, List.of("Dark Green", "Green")));
        p.add(new Entry(0x00AAAA, List.of("Dark Aqua", "Cyan", "Teal", "Aqua")));
        p.add(new Entry(0xAA0000, List.of("Dark Red", "Maroon", "Red")));
        p.add(new Entry(0xAA00AA, List.of("Purple", "Dark Purple", "Magenta")));
        p.add(new Entry(0xFFAA00, List.of("Orange", "Gold")));
        p.add(new Entry(0xAAAAAA, List.of("Gray", "Grey", "Light Gray", "Light Grey", "Silver")));
        p.add(new Entry(0x555555, List.of("Dark Gray", "Dark Grey", "Gray", "Grey")));
        p.add(new Entry(0x5555FF, List.of("Blue", "Light Blue")));
        p.add(new Entry(0x55FF55, List.of("Lime", "Green", "Light Green")));
        p.add(new Entry(0x55FFFF, List.of("Light Blue", "Aqua", "Cyan")));
        p.add(new Entry(0xFF5555, List.of("Red")));
        p.add(new Entry(0xFF55FF, List.of("Pink", "Magenta", "Light Purple")));
        p.add(new Entry(0xFFFF55, List.of("Yellow")));
        p.add(new Entry(0xFFFFFF, List.of("White")));
        // hex colors some servers use instead of the chat colors
        p.add(new Entry(0xFFA500, List.of("Orange")));
        p.add(new Entry(0xFFC0CB, List.of("Pink")));
        p.add(new Entry(0xFF69B4, List.of("Pink")));
        p.add(new Entry(0x800080, List.of("Purple")));
        p.add(new Entry(0x8B4513, List.of("Brown")));
        p.add(new Entry(0x00FFFF, List.of("Cyan", "Aqua", "Light Blue")));
        p.add(new Entry(0xFF00FF, List.of("Magenta", "Pink")));
        p.add(new Entry(0x00FF00, List.of("Lime", "Green")));
        p.add(new Entry(0xADD8E6, List.of("Light Blue")));
        return p;
    }

    /** Perceptual-ish RGB distance ("redmean"), good enough to pick the nearest palette color. */
    public static double distance(int a, int b) {
        int r1 = a >> 16 & 0xFF, g1 = a >> 8 & 0xFF, b1 = a & 0xFF;
        int r2 = b >> 16 & 0xFF, g2 = b >> 8 & 0xFF, b2 = b & 0xFF;
        double rm = (r1 + r2) / 2.0;
        int dr = r1 - r2, dg = g1 - g2, db = b1 - b2;
        return Math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db);
    }

    /** Names of the palette color nearest to {@code rgb}, in the palette's order. Empty if the palette is. */
    public static List<String> namesFor(int rgb, List<Entry> palette) {
        Entry best = null;
        double bestD = Double.MAX_VALUE;
        for (Entry e : palette) {
            double d = distance(rgb, e.rgb());
            if (d < bestD) {
                bestD = d;
                best = e;
            }
        }
        return best == null ? List.of() : best.names();
    }

    /** All palette names (normalized) plus the override: tells the label parser which multi-word names exist. */
    public static Set<String> knownNames(List<Entry> palette, String override) {
        Set<String> s = new HashSet<>();
        for (Entry e : palette) {
            for (String n : e.names()) {
                s.add(LabelParser.normalize(n).text());
            }
        }
        if (override != null && !override.isBlank()) {
            s.add(LabelParser.normalize(override).text());
        }
        return s;
    }

    /** How the color name was decided. */
    public enum Source {
        /** You typed your color name in the settings. */
        OVERRIDE,
        /** Your tab color's name matches the egg label. */
        NAME,
        /** The egg label is drawn in exactly your tab color. */
        LABEL_COLOR
    }

    /** Result of {@link #matches}: null when the label is not yours. */
    public record Verdict(Source source, String colorName) {
    }

    /**
     * Is a label with color name {@code phrase} (normalized), drawn in {@code labelRgb}
     * (null = no color), yours?
     *
     * @param override what you typed in the settings, blank for automatic
     * @param myRgb your name's color in the tab list, null if it has none
     */
    public static Verdict matches(String phrase, Integer labelRgb, String override, Integer myRgb, List<Entry> palette) {
        if (override != null && !override.isBlank()) {
            return LabelParser.normalize(override).text().equals(phrase) ? new Verdict(Source.OVERRIDE, override.strip()) : null;
        }
        if (myRgb == null) {
            return null; // no team color yet (lobby / glass boxes): never yours
        }
        for (String n : namesFor(myRgb, palette)) {
            if (LabelParser.normalize(n).text().equals(phrase)) {
                return new Verdict(Source.NAME, n);
            }
        }
        // A label drawn in exactly your color, for team names that aren't color names ("Dragons' Egg").
        // Not for a known color name that isn't yours, and not white-on-white (uncolored names are white).
        if (labelRgb != null && labelRgb.intValue() == myRgb.intValue() && myRgb != 0xFFFFFF && !isColorName(phrase, palette)) {
            return new Verdict(Source.LABEL_COLOR, titleCase(phrase));
        }
        return null;
    }

    private static boolean isColorName(String phrase, List<Entry> palette) {
        for (Entry e : palette) {
            for (String n : e.names()) {
                if (LabelParser.normalize(n).text().equals(phrase)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** "light blue" -> "Light Blue". */
    public static String titleCase(String s) {
        StringBuilder b = new StringBuilder(s.length());
        boolean up = true;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            b.append(up ? Character.toUpperCase(c) : c);
            up = c == ' ';
        }
        return b.toString();
    }

    /** "#FFAA00" style. */
    public static String hex(int rgb) {
        return String.format(Locale.ROOT, "#%06X", rgb & 0xFFFFFF);
    }
}
