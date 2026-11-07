package com.eggerdetector.core;

import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Fills in the placeholders of a warning message and makes the result safe to send as chat.
 *
 * <ul>
 *   <li>{@code [players]} all names, comma separated</li>
 *   <li>{@code [player1]}, {@code [player2]}, ... (also {@code [player 1]}) one name each, empty if there is no such player</li>
 *   <li>{@code [count]} number of players</li>
 *   <li>{@code [radius]} the radius in blocks</li>
 *   <li>{@code [color]} your team color name</li>
 * </ul>
 * Placeholders are not case sensitive. Pure Java so it can be unit tested.
 */
public final class MessageFormatter {
    /** What the vanilla chat box allows. */
    public static final int MAX_CHAT_LENGTH = 256;
    private static final Pattern PLACEHOLDER = Pattern.compile("\\[\\s*(players|count|radius|color|colour|player\\s*(\\d{1,3}))\\s*]", Pattern.CASE_INSENSITIVE);

    private MessageFormatter() {
    }

    public static String format(String template, List<String> names, int radius, String colorName) {
        String full = fill(template, names, names.size(), radius, colorName);
        if (full.length() <= MAX_CHAT_LENGTH || names.size() <= 1) {
            return cut(full);
        }
        // too long: list fewer names in [players] and say how many were left out
        for (int shown = names.size() - 1; shown >= 1; shown--) {
            String s = fill(template, names, shown, radius, colorName);
            if (s.length() <= MAX_CHAT_LENGTH) {
                return s;
            }
        }
        return cut(fill(template, names, 1, radius, colorName));
    }

    private static String fill(String template, List<String> names, int shown, int radius, String colorName) {
        Matcher m = PLACEHOLDER.matcher(template == null ? "" : template);
        StringBuilder b = new StringBuilder();
        while (m.find()) {
            String key = m.group(1).toLowerCase(Locale.ROOT);
            String value;
            if (m.group(2) != null) {
                int i = Integer.parseInt(m.group(2));
                value = i >= 1 && i <= names.size() ? names.get(i - 1) : "";
            } else {
                value = switch (key) {
                    case "players" -> list(names, shown);
                    case "count" -> Integer.toString(names.size());
                    case "radius" -> Integer.toString(radius);
                    default -> colorName == null ? "" : colorName; // color / colour
                };
            }
            m.appendReplacement(b, Matcher.quoteReplacement(value));
        }
        m.appendTail(b);
        return clean(b.toString());
    }

    private static String list(List<String> names, int shown) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < Math.min(shown, names.size()); i++) {
            if (i > 0) {
                b.append(", ");
            }
            b.append(names.get(i));
        }
        if (shown < names.size()) {
            b.append(" +").append(names.size() - shown).append(" more");
        }
        return b.toString();
    }

    /**
     * Remove what the server refuses (it kicks for the section sign and control characters)
     * and collapse spaces the way the chat box does.
     */
    public static String clean(String s) {
        StringBuilder b = new StringBuilder(s.length());
        boolean space = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            boolean ws = c == ' ' || c == '\t' || c == '\n' || c == '\r' || Character.isWhitespace(c);
            if (ws) {
                space = true;
                continue;
            }
            if (c == '\u00A7') {
                i++; // a formatting code like \u00A7c: drop the code letter too
                continue;
            }
            if (c < 32 || c == 127) {
                continue;
            }
            if (space && b.length() > 0) {
                b.append(' ');
            }
            space = false;
            b.append(c);
        }
        return b.toString();
    }

    private static String cut(String s) {
        if (s.length() <= MAX_CHAT_LENGTH) {
            return s;
        }
        int end = MAX_CHAT_LENGTH;
        if (Character.isHighSurrogate(s.charAt(end - 1))) {
            end--; // don't split an emoji in half
        }
        return s.substring(0, end).strip();
    }
}
