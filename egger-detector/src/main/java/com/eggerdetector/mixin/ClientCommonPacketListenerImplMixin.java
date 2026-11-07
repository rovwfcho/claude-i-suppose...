package com.eggerdetector.mixin;

import com.eggerdetector.DetectorAccess;
import net.minecraft.client.multiplayer.ClientCommonPacketListenerImpl;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ServerboundChatCommandPacket;
import net.minecraft.network.protocol.game.ServerboundChatCommandSignedPacket;
import net.minecraft.network.protocol.game.ServerboundChatPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * For the copy of the server's spam counter: every chat line and command really sent to the
 * server - typed, clicked (chat links, books, dialogs; after a confirmation screen only once you
 * press Run), from another mod, or the mod's own warnings - goes through this one method.
 */
@Mixin(ClientCommonPacketListenerImpl.class)
abstract class ClientCommonPacketListenerImplMixin {
    @Inject(method = "send(Lnet/minecraft/network/protocol/Packet;)V", at = @At("HEAD"))
    private void eggerdetector$countChat(Packet<?> packet, CallbackInfo ci) {
        if (packet instanceof ServerboundChatPacket || packet instanceof ServerboundChatCommandPacket
                || packet instanceof ServerboundChatCommandSignedPacket) {
            DetectorAccess.chatSent();
        }
    }
}
