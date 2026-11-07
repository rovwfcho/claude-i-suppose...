package com.eggerdetector;

import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.Style;
import net.minecraft.network.chat.TextColor;
import net.minecraft.util.StringDecomposer;
import net.minecraft.world.scores.PlayerTeam;
import org.jspecify.annotations.Nullable;

/** Reads the color a player's name has in the tab list (the player list on TAB). */
final class TabColors {
    private TabColors() {
    }

    /** Text with the color of every character, as the game draws it. */
    record Flat(String text, java.util.List<TextColor> colors) {
    }

    /**
     * Flatten a text the way the game's renderer does: styles merged with their parents, and
     * legacy "\u00A7" color codes inside plain text applied (and removed) - some plugins send
     * "\u00A76Orange's Egg" instead of a gold text.
     */
    static Flat flatten(Component text) {
        StringBuilder all = new StringBuilder();
        java.util.List<TextColor> colors = new java.util.ArrayList<>();
        StringDecomposer.iterateFormatted(text, Style.EMPTY, (int position, Style style, int codePoint) -> {
            int before = all.length();
            all.appendCodePoint(codePoint);
            for (int i = before; i < all.length(); i++) {
                colors.add(style.getColor());
            }
            return true;
        });
        return new Flat(all.toString(), colors);
    }

    /**
     * RGB of the player's name exactly as the tab list draws it, or null if it has no color.
     * The tab entry can be "[O] BigRemi1688": the color of the name itself is used, not of a prefix.
     */
    static @Nullable Integer nameColor(Minecraft mc, PlayerInfo info) {
        Component shown = mc.gui.getTabList().getNameForDisplay(info);
        String profileName = info.getProfile().name();
        Flat flat = flatten(shown);
        String text = flat.text();
        java.util.List<TextColor> colors = flat.colors();

        if (profileName != null && !profileName.isEmpty()) {
            int at = indexOfIgnoreCase(text, profileName);
            if (at >= 0) {
                TextColor c = colors.get(at);
                return c == null ? null : c.getValue() & 0xFFFFFF;
            }
        }
        // nickname instead of the real name: use the team color, then the color most letters have
        PlayerTeam team = info.getTeam();
        if (team != null && team.getColor() != ChatFormatting.RESET && team.getColor().getColor() != null) {
            return team.getColor().getColor() & 0xFFFFFF;
        }
        java.util.Map<Integer, Integer> counts = new java.util.HashMap<>();
        for (int i = 0; i < text.length(); i++) {
            TextColor c = colors.get(i);
            if (c != null && Character.isLetterOrDigit(text.charAt(i))) {
                counts.merge(c.getValue() & 0xFFFFFF, 1, Integer::sum);
            }
        }
        Integer best = null;
        int bestCount = 0;
        for (java.util.Map.Entry<Integer, Integer> e : counts.entrySet()) {
            if (e.getValue() > bestCount) {
                best = e.getKey();
                bestCount = e.getValue();
            }
        }
        return best;
    }

    /** Like indexOf, ignoring case, without changing the text's length (toLowerCase can). */
    private static int indexOfIgnoreCase(CharSequence text, String part) {
        String s = text.toString();
        for (int i = 0; i + part.length() <= s.length(); i++) {
            if (s.regionMatches(true, i, part, 0, part.length())) {
                return i;
            }
        }
        return -1;
    }
}
