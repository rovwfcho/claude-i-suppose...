package com.eggerdetector.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Finds the team color name inside an egg label such as "Orange's Egg".
 *
 * <p>Pure Java (no game classes) so it can be unit tested. All matching is done on a
 * normalized copy of the text: lower case, curly apostrophes turned into ', runs of
 * white space turned into one space. {@link Normalized#sourceIndex} maps every
 * normalized character back to the original text so the caller can look up its color.
 */
public final class LabelParser {
    /** Placeholder for the color name in the label format setting. */
    public static final String COLOR_PLACEHOLDER = "{color}";
    public static final String DEFAULT_FORMAT = "{color}'s Egg";
    /** Longest color name, in words, that is looked for ("light blue" is 2, "dark light blue" would be 3). */
    private static final int MAX_WORDS = 3;

    private final String prefix;
    private final String suffix;

    /** One color name found in a label line. */
    public record Match(String phrase, int start) {
    }

    /** Normalized text plus, per character, the index of the character it came from. */
    public record Normalized(String text, int[] sourceIndex) {
    }

    public LabelParser(String format) {
        String f = format == null ? "" : format;
        int at = f.toLowerCase(java.util.Locale.ROOT).indexOf(COLOR_PLACEHOLDER);
        if (at < 0) {
            f = DEFAULT_FORMAT;
            at = 0;
        }
        String pre = normalize(f.substring(0, at)).text();
        String suf = normalize(f.substring(at + COLOR_PLACEHOLDER.length())).text();
        if (pre.isEmpty() && suf.isEmpty()) {
            // "{color}" alone would match every word of every name tag
            pre = "";
            suf = normalize(DEFAULT_FORMAT.substring(COLOR_PLACEHOLDER.length())).text();
        }
        this.prefix = pre;
        this.suffix = suf;
    }

    /** True when the format can't contain this text at all (cheap pre-filter, input already lower case). */
    public boolean mightMatch(String lowerCaseText) {
        String anchor = suffix.isEmpty() ? prefix : suffix;
        // compare on letters only, apostrophes vary
        String core = lettersOnly(anchor);
        return core.isEmpty() || lettersOnly(lowerCaseText).contains(core);
    }

    private static String lettersOnly(String s) {
        StringBuilder b = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isLetterOrDigit(c)) {
                b.append(Character.toLowerCase(c));
            }
        }
        return b.toString();
    }

    public static Normalized normalize(String s) {
        StringBuilder b = new StringBuilder(s.length());
        int[] map = new int[s.length()];
        boolean pendingSpace = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\u2019' || c == '\u2018' || c == '\u02BC' || c == '`' || c == '\u00B4' || c == '\u2032' || c == '\uFF07') {
                c = '\'';
            }
            if (Character.isWhitespace(c) || Character.isSpaceChar(c)) {
                pendingSpace = true;
                continue;
            }
            if (pendingSpace && b.length() > 0) {
                map[b.length()] = i - 1;
                b.append(' ');
            }
            pendingSpace = false;
            map[b.length()] = i;
            b.append(Character.toLowerCase(c));
        }
        int[] trimmed = new int[b.length()];
        System.arraycopy(map, 0, trimmed, 0, b.length());
        return new Normalized(b.toString(), trimmed);
    }

    /**
     * Every color name in one normalized line. {@code knownNames} (normalized) decides how many
     * words belong to the name: the longest known one wins ("dark blue" rather than "blue"),
     * otherwise the single word next to the format text.
     */
    public List<Match> find(String line, Set<String> knownNames) {
        List<Match> out = new ArrayList<>(1);
        if (!suffix.isEmpty()) {
            int from = 0;
            while (true) {
                int at = line.indexOf(suffix, from);
                if (at < 0) {
                    break;
                }
                from = at + 1;
                int after = at + suffix.length();
                if (after < line.length() && Character.isLetterOrDigit(line.charAt(after))
                        && Character.isLetterOrDigit(suffix.charAt(suffix.length() - 1))) {
                    continue; // "'s eggs" / "'s egghead" is not the label
                }
                int begin = 0;
                if (!prefix.isEmpty()) {
                    int p = line.lastIndexOf(prefix, at - 1);
                    if (p < 0) {
                        continue;
                    }
                    begin = p + prefix.length();
                }
                Match m = pick(line, begin, at, true, knownNames);
                if (m != null) {
                    out.add(m);
                }
            }
        } else {
            int from = 0;
            while (true) {
                int at = line.indexOf(prefix, from);
                if (at < 0) {
                    break;
                }
                from = at + 1;
                if (at > 0 && Character.isLetterOrDigit(line.charAt(at - 1)) && Character.isLetterOrDigit(prefix.charAt(0))) {
                    continue;
                }
                Match m = pick(line, at + prefix.length(), line.length(), false, knownNames);
                if (m != null) {
                    out.add(m);
                }
            }
        }
        return out;
    }

    /** Words in [begin, end); take them from the end (name before the suffix) or the start. */
    private static Match pick(String line, int begin, int end, boolean fromEnd, Set<String> knownNames) {
        List<int[]> words = new ArrayList<>();
        int i = begin;
        while (i < end) {
            while (i < end && !Character.isLetterOrDigit(line.charAt(i))) {
                i++;
            }
            int s = i;
            while (i < end && Character.isLetterOrDigit(line.charAt(i))) {
                i++;
            }
            if (i > s) {
                words.add(new int[] {s, i});
            }
        }
        if (words.isEmpty()) {
            return null;
        }
        if (fromEnd) {
            int[] last = words.getLast();
            if (last[1] != end && !onlySpaceOrApostrophe(line, last[1], end)) {
                return null; // something other than the name sits right before "'s Egg"
            }
        } else {
            int[] first = words.getFirst();
            if (first[0] != begin && !onlySpaceOrApostrophe(line, begin, first[0])) {
                return null;
            }
        }
        int n = words.size();
        Match best = null;
        for (int k = 1; k <= Math.min(MAX_WORDS, n); k++) {
            int from = fromEnd ? n - k : 0;
            int to = fromEnd ? n : k;
            String phrase = joinWords(line, words, from, to);
            // one word is the fallback; a longer phrase only if it is a known color name
            if (k == 1 || knownNames.contains(phrase)) {
                best = new Match(phrase, words.get(from)[0]);
            }
        }
        return best;
    }

    private static boolean onlySpaceOrApostrophe(String line, int from, int to) {
        for (int i = from; i < to; i++) {
            char c = line.charAt(i);
            if (c != ' ' && c != '\'') {
                return false;
            }
        }
        return true;
    }

    private static String joinWords(String line, List<int[]> words, int from, int to) {
        StringBuilder b = new StringBuilder();
        for (int w = from; w < to; w++) {
            if (b.length() > 0) {
                b.append(' ');
            }
            int[] r = words.get(w);
            b.append(line, r[0], r[1]);
        }
        return b.toString();
    }
}
