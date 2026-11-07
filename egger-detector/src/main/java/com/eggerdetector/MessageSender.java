package com.eggerdetector;

import java.util.ArrayDeque;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Sends warnings as if you typed them in chat, with two safeties against the server's spam
 * protection (vanilla: TickThrottler(20, 200) - every chat line or command adds 20, one is
 * forgiven per server tick, kick at 200):
 * <ol>
 *   <li>a minimum gap between the mod's messages (setting, at least 1 s);</li>
 *   <li>a copy of the server's counter that also counts what you type yourself and forgives a
 *       quarter less than the server does - only for server ticks the server has confirmed with
 *       its time update (once a second), so a server that lags or freezes is followed too - and
 *       holds the queue while the count is high or the server's time is overdue (stalled
 *       connection, frozen server).</li>
 * </ol>
 * Client thread only.
 */
final class MessageSender {
    private static final Logger LOG = LoggerFactory.getLogger("eggerdetector");
    private static final int MAX_QUEUE = 10;
    /** A warning that waited this long is out of date: it is dropped instead of sent. */
    private static final long STALE_MS = 15_000;
    private static final int SPAM_STEP = 20;
    /** Never go above this ourselves: leaves room for 3 quick lines of your own (kick at 200). */
    private static final int SPAM_HOLD_AT = 120;
    /** The server forgives 1 per tick; we count 0.75 (15 per second on a healthy server). */
    private static final double SPAM_FORGIVEN_PER_TICK = 0.75;
    /**
     * Never more than 15 per second of real time, with at most 2 s saved up: after a stalled
     * connection the server's time updates arrive all at once, but the lines we sent during the
     * stall only reached the server at its end - the ticks before that forgave nothing of them.
     */
    private static final double MAX_FORGIVEN_PER_MS = 15.0 / 1000, MAX_FORGIVE_SAVED = 30;
    /**
     * The server's time is overdue when the client's own count of the game time runs this far
     * (1.5 s) past the last time the server sent: nothing is sent until it comes.
     */
    private static final long MAX_AHEAD = 30;

    private record Queued(String text, long atMs) {
    }

    private final ArrayDeque<Queued> queue = new ArrayDeque<>();
    private long lastSentMs = Long.MIN_VALUE / 2;
    private double spamCount;
    private double forgiveSaved;
    private long forgiveUpdatedMs = Long.MIN_VALUE / 2;
    /** The last game time the server sent, and for which world. */
    private @Nullable ClientLevel serverTimeLevel;
    private long serverTime;

    void enqueue(Minecraft mc, String message, long nowMs) {
        if (queue.size() >= MAX_QUEUE) {
            Queued dropped = queue.pollFirst();
            LOG.warn("Egger Detector: too many warnings waiting, dropped: {}", dropped.text());
            local(mc, Component.literal("Too many warnings at once, one was not sent: " + dropped.text()).withStyle(ChatFormatting.GRAY));
        }
        queue.addLast(new Queued(message, nowMs));
    }

    /** A chat line or command went to the server (yours, another mod's, or the mod's own). */
    void noteSent() {
        spamCount += SPAM_STEP;
    }

    /** Send the next waiting message if the gap has passed and the spam count allows it. */
    void tick(Minecraft mc, ClientPacketListener connection, long nowMs, long gapMs) {
        while (!queue.isEmpty() && nowMs - queue.peekFirst().atMs() > STALE_MS) {
            Queued old = queue.pollFirst();
            LOG.warn("Egger Detector: warning waited too long, not sent: {}", old.text());
            local(mc, Component.literal("Not sent, it waited too long: " + old.text()).withStyle(ChatFormatting.GRAY));
        }
        if (queue.isEmpty() || nowMs - lastSentMs < gapMs || spamCount + SPAM_STEP > SPAM_HOLD_AT || !serverTimeFresh(mc.level)) {
            return;
        }
        String message = queue.pollFirst().text();
        lastSentMs = nowMs;
        LOG.info("Egger Detector: sending \"{}\"", message);
        // exactly what the chat box does with a line you typed (counted by noteSent, like yours)
        if (message.startsWith("/")) {
            connection.sendCommand(message.substring(1));
        } else {
            connection.sendChat(message);
        }
    }

    /**
     * False while the server's time is overdue: the connection stalls (whatever we send would
     * reach the server all at once later) or the server is very slow between its time updates.
     */
    private boolean serverTimeFresh(@Nullable ClientLevel level) {
        return level != null && level == serverTimeLevel && level.getGameTime() <= serverTime + MAX_AHEAD;
    }

    /**
     * The server sent its game time (once a second, and on joining or changing world): forgive
     * what it forgave since its last update - one per tick it ran (we count 0.75). Runs whether
     * the mod is switched on or not, so what you type while it is off is forgiven too.
     */
    void noteServerTime(@Nullable ClientLevel level, long gameTime, long nowMs) {
        forgiveSaved = Math.min(MAX_FORGIVE_SAVED, forgiveSaved + Math.max(0, nowMs - forgiveUpdatedMs) * MAX_FORGIVEN_PER_MS);
        forgiveUpdatedMs = nowMs;
        if (level != null && level == serverTimeLevel && gameTime > serverTime) {
            double forgiven = Math.min((gameTime - serverTime) * SPAM_FORGIVEN_PER_TICK, forgiveSaved);
            forgiveSaved -= forgiven;
            spamCount = Math.max(0, spamCount - forgiven);
        }
        // (another world: its own clock - nothing to compare with until its next update)
        serverTimeLevel = level;
        serverTime = gameTime;
    }

    void clear() {
        queue.clear();
    }

    /** Left the server: drop the queue and let go of the old world. */
    void reset() {
        queue.clear();
        serverTimeLevel = null;
    }


    /** A line in your own chat only, never sent to the server. */
    static void local(Minecraft mc, Component message) {
        MutableComponent line = Component.literal("[Egger Detector] ").withStyle(ChatFormatting.GOLD).append(message);
        mc.gui.getChat().addClientSystemMessage(line);
    }
}
