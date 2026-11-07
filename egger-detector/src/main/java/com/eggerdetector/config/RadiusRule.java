package com.eggerdetector.config;

/** One warning ring around the egg. Mutable: the settings screen edits a copy. */
public final class RadiusRule {
    public static final int MIN_RADIUS = 1;
    public static final int MAX_RADIUS = 1000;
    /** Message of a newly added radius (and of a hand-edited one without "message"). */
    public static final String DEFAULT_MESSAGE = "[players] within [radius] blocks of our egg!";

    /** Where the warning goes. */
    public enum Mode {
        /** Typed into chat like you would (a message starting with / runs as a command). */
        CHAT,
        /** Only shown to you. */
        ONLY_ME
    }

    public int radius;
    public String message;
    public Mode mode;
    public boolean enabled;

    public RadiusRule(int radius, String message, Mode mode, boolean enabled) {
        this.radius = radius;
        this.message = message;
        this.mode = mode;
        this.enabled = enabled;
    }

    public RadiusRule copy() {
        return new RadiusRule(radius, message, mode, enabled);
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof RadiusRule r && r.radius == radius && r.enabled == enabled && r.mode == mode
                && java.util.Objects.equals(r.message, message);
    }

    @Override
    public int hashCode() {
        return java.util.Objects.hash(radius, message, mode, enabled);
    }
}
