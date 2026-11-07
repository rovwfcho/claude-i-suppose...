package com.eggerdetector;

import com.eggerdetector.config.EggerConfig;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.network.chat.Component;

/** The one-line status in a top corner of the screen ("Egger: Orange's Egg | nobody within 50"). */
final class StatusHud implements HudElement {
    @Override
    public void extractRenderState(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker) {
        Minecraft mc = Minecraft.getInstance();
        EggerConfig cfg = EggerConfig.get();
        if (!cfg.showHud || mc.options.hideGui || mc.getDebugOverlay().showDebugScreen()) {
            return;
        }
        Component line = Detector.INSTANCE.hudLine(mc);
        if (line == null) {
            return;
        }
        int w = mc.font.width(line);
        int x = cfg.hudPosition == EggerConfig.HudPosition.TOP_RIGHT ? graphics.guiWidth() - w - 4 : 4;
        int y = 4;
        graphics.fill(x - 2, y - 2, x + w + 2, y + mc.font.lineHeight + 1, 0x80000000);
        graphics.text(mc.font, line, x, y, 0xFFFFFFFF, true);
    }
}
