package com.eggerdetector.mixin;

import com.eggerdetector.DetectorAccess;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundSetTimePacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** For the copy of the server's spam counter: the server's game time tells how many ticks the server really ran. */
@Mixin(ClientPacketListener.class)
abstract class ClientPacketListenerMixin {
    // TAIL: on the client thread only (on the network thread the method hands over and returns early)
    @Inject(method = "handleSetTime", at = @At("TAIL"))
    private void eggerdetector$serverTime(ClientboundSetTimePacket packet, CallbackInfo ci) {
        DetectorAccess.serverTime(packet.gameTime());
    }
}
