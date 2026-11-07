package com.eggerdetector.config;

import com.eggerdetector.core.ColorMatcher;
import com.eggerdetector.core.LabelParser;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * All settings. Stored as {@code config/eggerdetector.json}. A file edited by hand is read
 * field by field: anything missing, of the wrong type or out of range falls back to the
 * default (or is clamped) instead of breaking the whole file.
 */
public final class EggerConfig {
    private static final Logger LOG = LoggerFactory.getLogger("eggerdetector");
    public static final int MAX_RULES = 20;
    public static final int MAX_MESSAGE_LENGTH = 256;
    // vanilla kicks at 10 quick chat messages and forgives one per second: never send faster than that
    public static final double MAX_COOLDOWN = 3600, MAX_GROUP = 10, MIN_GAP = 1, MAX_GAP = 10, MAX_START_DELAY = 60;

    /** Where the on-screen status line sits. */
    public enum HudPosition { TOP_LEFT, TOP_RIGHT }

    public boolean enabled = true;
    public boolean statusMessages = true;
    public boolean showHud = true;
    public HudPosition hudPosition = HudPosition.TOP_LEFT;
    public boolean sound = true;
    /** Your color name as written on your egg; blank = read it from your name color in the tab list. */
    public String colorOverride = "";
    public String labelFormat = LabelParser.DEFAULT_FORMAT;
    /** Only start guarding when the egg closest to you is yours (stops it firing in the pre-game glass boxes). */
    public boolean closestEggOnly = true;
    /** After locking on, wait this long before warning, so every teammate's name has its color. */
    public double startDelaySeconds = 3;
    public boolean requireDragonEgg = true;
    public boolean ignoreTeammates = true;
    public List<String> ignoredPlayers = new ArrayList<>();
    public double cooldownSeconds = 20;
    public double groupSeconds = 1;
    public double messageGapSeconds = 1.5;
    public List<RadiusRule> radii = new ArrayList<>();
    public List<ColorMatcher.Entry> palette = ColorMatcher.defaultPalette();

    private static EggerConfig current = defaults();
    private static String loadProblem;

    public static EggerConfig defaults() {
        EggerConfig c = new EggerConfig();
        c.radii.add(new RadiusRule(50, "Heads up: [players] within [radius] blocks of our egg!", RadiusRule.Mode.CHAT, true));
        c.radii.add(new RadiusRule(15, "ALERT: [players] at our egg ([radius] blocks)!", RadiusRule.Mode.CHAT, true));
        return c;
    }

    public static EggerConfig get() {
        return current;
    }

    /** Problem met while loading the file (shown once in chat), or null. */
    public static String takeLoadProblem() {
        String p = loadProblem;
        loadProblem = null;
        return p;
    }

    public EggerConfig copy() {
        EggerConfig c = new EggerConfig();
        c.enabled = enabled;
        c.statusMessages = statusMessages;
        c.showHud = showHud;
        c.hudPosition = hudPosition;
        c.sound = sound;
        c.colorOverride = colorOverride;
        c.labelFormat = labelFormat;
        c.closestEggOnly = closestEggOnly;
        c.startDelaySeconds = startDelaySeconds;
        c.requireDragonEgg = requireDragonEgg;
        c.ignoreTeammates = ignoreTeammates;
        c.ignoredPlayers = new ArrayList<>(ignoredPlayers);
        c.cooldownSeconds = cooldownSeconds;
        c.groupSeconds = groupSeconds;
        c.messageGapSeconds = messageGapSeconds;
        c.radii = new ArrayList<>();
        for (RadiusRule r : radii) {
            c.radii.add(r.copy());
        }
        c.palette = List.copyOf(palette);
        return c;
    }

    /** Clamp every value into its allowed range (also used before saving from the settings screen). */
    public EggerConfig sanitize() {
        if (colorOverride == null) {
            colorOverride = "";
        }
        colorOverride = colorOverride.strip();
        if (labelFormat == null || !labelFormat.toLowerCase(Locale.ROOT).contains(LabelParser.COLOR_PLACEHOLDER)) {
            labelFormat = LabelParser.DEFAULT_FORMAT;
        }
        if (hudPosition == null) {
            hudPosition = HudPosition.TOP_LEFT;
        }
        startDelaySeconds = clamp(startDelaySeconds, 0, MAX_START_DELAY, 3);
        cooldownSeconds = clamp(cooldownSeconds, 0, MAX_COOLDOWN, 20);
        groupSeconds = clamp(groupSeconds, 0, MAX_GROUP, 1);
        messageGapSeconds = clamp(messageGapSeconds, MIN_GAP, MAX_GAP, 1.5);
        List<String> names = new ArrayList<>();
        if (ignoredPlayers != null) {
            for (String n : ignoredPlayers) {
                if (n != null && !n.isBlank() && !names.contains(n.strip())) {
                    names.add(n.strip());
                }
            }
        }
        ignoredPlayers = names;
        List<RadiusRule> rules = new ArrayList<>();
        if (radii != null) {
            for (RadiusRule r : radii) {
                if (r == null || rules.size() >= MAX_RULES) {
                    continue;
                }
                r.radius = Math.max(RadiusRule.MIN_RADIUS, Math.min(RadiusRule.MAX_RADIUS, r.radius));
                r.message = r.message == null ? "" : r.message;
                if (r.message.length() > MAX_MESSAGE_LENGTH) {
                    r.message = r.message.substring(0, MAX_MESSAGE_LENGTH);
                }
                if (r.mode == null) {
                    r.mode = RadiusRule.Mode.CHAT;
                }
                rules.add(r);
            }
        }
        radii = rules;
        if (palette == null || palette.isEmpty()) {
            palette = ColorMatcher.defaultPalette();
        }
        return this;
    }

    private static double clamp(double v, double lo, double hi, double fallback) {
        if (Double.isNaN(v) || Double.isInfinite(v)) {
            return fallback;
        }
        return Math.max(lo, Math.min(hi, v));
    }

    /** Is {@code playerName} on the ignore list (not case sensitive)? */
    public boolean isIgnored(String playerName) {
        for (String n : ignoredPlayers) {
            if (n.equalsIgnoreCase(playerName)) {
                return true;
            }
        }
        return false;
    }

    // ---------------------------------------------------------------- file

    public static Path path() {
        return net.fabricmc.loader.api.FabricLoader.getInstance().getConfigDir().resolve("eggerdetector.json");
    }

    public static void load() {
        Path p = path();
        if (!Files.exists(p)) {
            current = defaults();
            save(current);
            return;
        }
        try {
            String text = Files.readString(p, StandardCharsets.UTF_8);
            JsonElement root = JsonParser.parseString(text);
            if (!root.isJsonObject()) {
                throw new IllegalStateException("the file is not a JSON object");
            }
            current = fromJson(root.getAsJsonObject()).sanitize();
        } catch (Exception e) {
            LOG.error("Egger Detector: could not read {}, using the default settings", p, e);
            Path broken = p.resolveSibling("eggerdetector.json.broken");
            try {
                Files.move(p, broken, StandardCopyOption.REPLACE_EXISTING);
            } catch (IOException moveError) {
                LOG.error("Egger Detector: could not move the broken settings file aside", moveError);
            }
            loadProblem = "Your settings file could not be read (" + e.getMessage() + "), defaults are used. The old file was saved as eggerdetector.json.broken.";
            current = defaults();
            save(current);
        }
    }

    /** Make {@code c} the active settings and write it to disk. */
    public static void apply(EggerConfig c) {
        current = c.sanitize();
        save(current);
    }

    private static void save(EggerConfig c) {
        Path p = path();
        try {
            Files.createDirectories(p.getParent());
            Path tmp = p.resolveSibling("eggerdetector.json.tmp");
            Files.writeString(tmp, new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(c.toJson()), StandardCharsets.UTF_8);
            try {
                Files.move(tmp, p, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(tmp, p, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (IOException e) {
            LOG.error("Egger Detector: could not save {}", p, e);
        }
    }

    JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("configVersion", 1);
        o.addProperty("enabled", enabled);
        o.addProperty("statusMessages", statusMessages);
        o.addProperty("showHud", showHud);
        o.addProperty("hudPosition", hudPosition.name());
        o.addProperty("sound", sound);
        o.addProperty("colorOverride", colorOverride);
        o.addProperty("labelFormat", labelFormat);
        o.addProperty("closestEggOnly", closestEggOnly);
        o.addProperty("startDelaySeconds", startDelaySeconds);
        o.addProperty("requireDragonEgg", requireDragonEgg);
        o.addProperty("ignoreTeammates", ignoreTeammates);
        JsonArray ign = new JsonArray();
        ignoredPlayers.forEach(ign::add);
        o.add("ignoredPlayers", ign);
        o.addProperty("cooldownSeconds", cooldownSeconds);
        o.addProperty("groupSeconds", groupSeconds);
        o.addProperty("messageGapSeconds", messageGapSeconds);
        JsonArray rs = new JsonArray();
        for (RadiusRule r : radii) {
            JsonObject j = new JsonObject();
            j.addProperty("radius", r.radius);
            j.addProperty("message", r.message);
            j.addProperty("mode", r.mode.name());
            j.addProperty("enabled", r.enabled);
            rs.add(j);
        }
        o.add("radii", rs);
        JsonArray pal = new JsonArray();
        for (ColorMatcher.Entry e : palette) {
            JsonObject j = new JsonObject();
            j.addProperty("color", ColorMatcher.hex(e.rgb()));
            JsonArray n = new JsonArray();
            e.names().forEach(n::add);
            j.add("names", n);
            pal.add(j);
        }
        o.add("palette", pal);
        return o;
    }

    static EggerConfig fromJson(JsonObject o) {
        EggerConfig d = defaults();
        EggerConfig c = new EggerConfig();
        c.enabled = bool(o, "enabled", d.enabled);
        c.statusMessages = bool(o, "statusMessages", d.statusMessages);
        c.showHud = bool(o, "showHud", d.showHud);
        c.hudPosition = enumValue(o, "hudPosition", HudPosition.class, d.hudPosition);
        c.sound = bool(o, "sound", d.sound);
        c.colorOverride = string(o, "colorOverride", d.colorOverride);
        c.labelFormat = string(o, "labelFormat", d.labelFormat);
        c.closestEggOnly = bool(o, "closestEggOnly", d.closestEggOnly);
        c.startDelaySeconds = number(o, "startDelaySeconds", d.startDelaySeconds);
        c.requireDragonEgg = bool(o, "requireDragonEgg", d.requireDragonEgg);
        c.ignoreTeammates = bool(o, "ignoreTeammates", d.ignoreTeammates);
        c.ignoredPlayers = new ArrayList<>();
        JsonElement ign = o.get("ignoredPlayers");
        if (ign != null && ign.isJsonArray()) {
            for (JsonElement e : ign.getAsJsonArray()) {
                if (e.isJsonPrimitive() && e.getAsJsonPrimitive().isString()) {
                    c.ignoredPlayers.add(e.getAsString());
                }
            }
        } else if (ign != null && ign.isJsonPrimitive()) {
            c.ignoredPlayers.addAll(splitNames(ign.getAsString())); // "a, b, c" typed by hand
        }
        c.cooldownSeconds = number(o, "cooldownSeconds", d.cooldownSeconds);
        c.groupSeconds = number(o, "groupSeconds", d.groupSeconds);
        c.messageGapSeconds = number(o, "messageGapSeconds", d.messageGapSeconds);
        JsonElement rs = o.get("radii");
        if (rs != null && rs.isJsonArray()) {
            c.radii = new ArrayList<>();
            for (JsonElement e : rs.getAsJsonArray()) {
                if (!e.isJsonObject()) {
                    continue;
                }
                JsonObject j = e.getAsJsonObject();
                double radius = number(j, "radius", Double.NaN);
                if (Double.isNaN(radius)) {
                    continue;
                }
                // clamp before turning it into an int (a huge number would wrap around)
                radius = Math.max(RadiusRule.MIN_RADIUS, Math.min(RadiusRule.MAX_RADIUS, radius));
                c.radii.add(new RadiusRule((int) Math.round(radius), string(j, "message", RadiusRule.DEFAULT_MESSAGE),
                        enumValue(j, "mode", RadiusRule.Mode.class, RadiusRule.Mode.CHAT), bool(j, "enabled", true)));
            }
            if (c.radii.isEmpty() && !rs.getAsJsonArray().isEmpty()) {
                c.radii = d.radii; // nothing readable: better the defaults than silently no warnings
                loadProblem = "The radii in your settings file could not be read, the default radii are used.";
            }
        } else {
            c.radii = d.radii;
        }
        JsonElement pal = o.get("palette");
        if (pal != null && pal.isJsonArray()) {
            List<ColorMatcher.Entry> entries = new ArrayList<>();
            for (JsonElement e : pal.getAsJsonArray()) {
                if (!e.isJsonObject()) {
                    continue;
                }
                JsonObject j = e.getAsJsonObject();
                Integer rgb = parseColor(string(j, "color", ""));
                List<String> names = new ArrayList<>();
                JsonElement n = j.get("names");
                if (n != null && n.isJsonArray()) {
                    for (JsonElement x : n.getAsJsonArray()) {
                        if (x.isJsonPrimitive() && !x.getAsString().isBlank()) {
                            names.add(x.getAsString().strip());
                        }
                    }
                }
                if (rgb != null && !names.isEmpty()) {
                    entries.add(new ColorMatcher.Entry(rgb, names));
                }
            }
            c.palette = entries.isEmpty() ? d.palette : entries;
        }
        return c;
    }

    public static List<String> splitNames(String s) {
        List<String> out = new ArrayList<>();
        for (String part : s.split("[,;\\s]+")) {
            if (!part.isBlank()) {
                out.add(part.strip());
            }
        }
        return out;
    }

    /** "#FFAA00", "FFAA00" or "0xFFAA00" -> 0xFFAA00, else null. */
    public static Integer parseColor(String s) {
        String t = s.strip();
        if (t.startsWith("#")) {
            t = t.substring(1);
        } else if (t.startsWith("0x") || t.startsWith("0X")) {
            t = t.substring(2);
        }
        if (t.length() != 6) {
            return null;
        }
        try {
            return Integer.parseInt(t, 16);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static boolean bool(JsonObject o, String key, boolean def) {
        JsonElement e = o.get(key);
        if (e != null && e.isJsonPrimitive()) {
            JsonPrimitive p = e.getAsJsonPrimitive();
            if (p.isBoolean()) {
                return p.getAsBoolean();
            }
            if (p.isString()) {
                String s = p.getAsString().strip().toLowerCase(Locale.ROOT);
                if (s.equals("true") || s.equals("on") || s.equals("yes")) {
                    return true;
                }
                if (s.equals("false") || s.equals("off") || s.equals("no")) {
                    return false;
                }
            }
        }
        return def;
    }

    private static double number(JsonObject o, String key, double def) {
        JsonElement e = o.get(key);
        if (e != null && e.isJsonPrimitive()) {
            JsonPrimitive p = e.getAsJsonPrimitive();
            try {
                if (p.isNumber()) {
                    return p.getAsDouble();
                }
                if (p.isString()) {
                    return Double.parseDouble(p.getAsString().strip().replace(',', '.'));
                }
            } catch (NumberFormatException ignored) {
                // fall through to the default
            }
        }
        return def;
    }

    private static String string(JsonObject o, String key, String def) {
        JsonElement e = o.get(key);
        if (e != null && e.isJsonPrimitive()) {
            return e.getAsString();
        }
        return def;
    }

    private static <E extends Enum<E>> E enumValue(JsonObject o, String key, Class<E> type, E def) {
        JsonElement e = o.get(key);
        if (e != null && e.isJsonPrimitive()) {
            String s = e.getAsString().strip().toUpperCase(Locale.ROOT).replace(' ', '_');
            for (E v : type.getEnumConstants()) {
                if (v.name().equals(s)) {
                    return v;
                }
            }
        }
        return def;
    }
}
