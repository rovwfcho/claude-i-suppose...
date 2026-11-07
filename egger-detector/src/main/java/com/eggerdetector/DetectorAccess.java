package com.eggerdetector;

import java.util.List;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

/** What the settings screen may ask the detector (keeps the detector's internals private). */
public final class DetectorAccess {
    private DetectorAccess() {
    }

    public static List<Component> statusLines(Minecraft mc) {
        return Detector.INSTANCE.statusLines(mc);
    }

    public static String previewColorName() {
        return Detector.INSTANCE.previewColorName();
    }

    /** A chat line or command is being sent to the server (anyone's: yours, another mod's, ours). */
    public static void chatSent() {
        Minecraft mc = Minecraft.getInstance();
        if (mc.isSameThread()) {
            Detector.INSTANCE.onChatSent();
        } else {
            mc.execute(Detector.INSTANCE::onChatSent);
        }
    }

    /** The server's game time arrived (ClientPacketListener.handleSetTime). */
    public static void serverTime(long gameTime) {
        Detector.INSTANCE.onServerTime(gameTime);
    }

    public static void settingsChanged() {
        Detector.INSTANCE.onSettingsChanged();
    }
}
