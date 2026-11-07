package com.eggerdetector;

import com.eggerdetector.config.EggerConfig;
import com.eggerdetector.gui.EggerConfigScreen;
import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.hud.VanillaHudElements;
import net.minecraft.ChatFormatting;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;

/** Entry point (client only). */
public final class EggerDetectorClient implements ClientModInitializer {
    public static final String MOD_ID = "eggerdetector";
    private static KeyMapping toggleKey;
    private static KeyMapping settingsKey;

    @Override
    public void onInitializeClient() {
        EggerConfig.load();
        KeyMapping.Category category = KeyMapping.Category.register(Identifier.fromNamespaceAndPath(MOD_ID, "keys"));
        // unbound by default: pick a key in Options > Controls if you want one
        toggleKey = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.eggerdetector.toggle", InputConstants.Type.KEYSYM, InputConstants.UNKNOWN.getValue(), category));
        settingsKey = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.eggerdetector.settings", InputConstants.Type.KEYSYM, InputConstants.UNKNOWN.getValue(), category));
        ClientTickEvents.END_CLIENT_TICK.register(mc -> {
            handleKeys(mc);
            Detector.INSTANCE.onEndTick(mc);
        });
        HudElementRegistry.attachElementBefore(VanillaHudElements.CHAT, Identifier.fromNamespaceAndPath(MOD_ID, "status"), new StatusHud());
    }

    private static void handleKeys(Minecraft mc) {
        while (toggleKey.consumeClick()) {
            EggerConfig c = EggerConfig.get().copy();
            c.enabled = !c.enabled;
            EggerConfig.apply(c);
            Detector.INSTANCE.onSettingsChanged();
            if (mc.level != null) {
                MessageSender.local(mc, Component.literal(c.enabled ? "switched ON" : "switched OFF")
                        .withStyle(c.enabled ? ChatFormatting.GREEN : ChatFormatting.RED));
            }
        }
        while (settingsKey.consumeClick()) {
            if (mc.screen == null) {
                mc.setScreen(EggerConfigScreen.create(null));
            }
        }
    }
}
