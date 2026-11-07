package com.eggerdetector.gui;

import com.eggerdetector.DetectorAccess;
import com.eggerdetector.config.EggerConfig;
import com.eggerdetector.config.RadiusRule;
import com.eggerdetector.core.LabelParser;
import com.eggerdetector.core.MessageFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import me.shedaniel.clothconfig2.api.AbstractConfigListEntry;
import me.shedaniel.clothconfig2.api.ConfigBuilder;
import me.shedaniel.clothconfig2.api.ConfigCategory;
import me.shedaniel.clothconfig2.api.ConfigEntryBuilder;
import me.shedaniel.clothconfig2.gui.entries.BooleanListEntry;
import me.shedaniel.clothconfig2.gui.entries.EnumListEntry;
import me.shedaniel.clothconfig2.gui.entries.IntegerListEntry;
import me.shedaniel.clothconfig2.gui.entries.MultiElementListEntry;
import me.shedaniel.clothconfig2.gui.entries.NestedListListEntry;
import me.shedaniel.clothconfig2.gui.entries.StringListEntry;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import org.jspecify.annotations.Nullable;

/**
 * The settings screen (Mod Menu's config button, or the "open settings" key), built with
 * Cloth Config: tabs, search, a Reset button on every option, tooltips.
 * Edits a copy of the settings; Save writes it, closing without saving throws it away.
 * Works at the title screen too: nothing here touches the world.
 */
public final class EggerConfigScreen {
    private static final String SAMPLE_1 = "Steve", SAMPLE_2 = "Alex";
    private static final int TIP_WIDTH = 46;

    private EggerConfigScreen() {
    }

    public static Screen create(@Nullable Screen parent) {
        EggerConfig work = EggerConfig.get().copy();
        EggerConfig def = EggerConfig.defaults();
        ConfigBuilder builder = ConfigBuilder.create()
                .setParentScreen(parent)
                .setTitle(Component.literal("Egger Detector"))
                .setSavingRunnable(() -> {
                    EggerConfig.apply(work);
                    DetectorAccess.settingsChanged();
                });
        ConfigEntryBuilder eb = builder.entryBuilder();

        // ---------------------------------------------------------------- General
        ConfigCategory general = builder.getOrCreateCategory(Component.literal("General"));
        for (Component line : DetectorAccess.statusLines(Minecraft.getInstance())) {
            general.addEntry(eb.startTextDescription(line).build());
        }
        general.addEntry(eb.startBooleanToggle(Component.literal("Enabled"), work.enabled)
                .setDefaultValue(def.enabled)
                .setTooltip(tip("Switch the whole mod on or off. You can also bind a key for this in Options > Controls > Key Binds > Egger Detector."))
                .setSaveConsumer(v -> work.enabled = v)
                .build());
        general.addEntry(eb.startBooleanToggle(Component.literal("Sound"), work.sound)
                .setDefaultValue(def.sound)
                .setTooltip(tip("A ping only you hear when a warning goes out (higher for your smallest radius), and a low note if your egg disappears."))
                .setSaveConsumer(v -> work.sound = v)
                .build());

        // ---------------------------------------------------------------- Your egg
        ConfigCategory egg = builder.getOrCreateCategory(Component.literal("Your egg"));
        egg.addEntry(eb.startTextDescription(Component.literal("Your team color is read from your name in the tab list, again in every game, so a different color each round needs no change here.")
                .withStyle(ChatFormatting.GRAY)).build());
        egg.addEntry(eb.startBooleanToggle(Component.literal("Only start at the closest egg"), work.closestEggOnly)
                .setDefaultValue(def.closestEggOnly)
                .setTooltip(tip("Start guarding only when the egg closest to you is yours. With the color detected from the tab list (normal), your name must also have its team color, which keeps the mod quiet in the glass boxes before the round starts. Once started it keeps guarding that egg wherever you go."))
                .setSaveConsumer(v -> work.closestEggOnly = v)
                .build());
        egg.addEntry(eb.startDoubleField(Component.literal("Start delay (seconds)"), work.startDelaySeconds)
                .setDefaultValue(def.startDelaySeconds)
                .setMin(0).setMax(EggerConfig.MAX_START_DELAY)
                .setTooltip(tip("After it finds your egg, wait this long before warning anyone, so all your teammates have their team color first."))
                .setSaveConsumer(v -> work.startDelaySeconds = v)
                .build());
        egg.addEntry(eb.startBooleanToggle(Component.literal("Need a dragon egg under the name"), work.requireDragonEgg)
                .setDefaultValue(def.requireDragonEgg)
                .setTooltip(tip("Only count a name like \"Orange's Egg\" if a dragon egg sits under it (a placed egg block, or an egg shown by an item or block display)."))
                .setSaveConsumer(v -> work.requireDragonEgg = v)
                .build());
        egg.addEntry(eb.startStrField(Component.literal("Egg name format"), work.labelFormat)
                .setDefaultValue(def.labelFormat)
                .setTooltip(tip("How the name above the eggs is written; {color} stands for the color name. \"{color}'s Egg\" matches \"Orange's Egg\" (any capitals, straight or curly apostrophe)."))
                .setErrorSupplier(v -> v.toLowerCase(Locale.ROOT).contains(LabelParser.COLOR_PLACEHOLDER)
                        ? Optional.empty() : Optional.of(Component.literal("Must contain {color}")))
                .setSaveConsumer(v -> work.labelFormat = v)
                .build());
        egg.addEntry(eb.startStrField(Component.literal("Color name override"), work.colorOverride)
                .setDefaultValue(def.colorOverride)
                .setTooltip(tip("Leave EMPTY (normal): your color is detected from the tab list every game. Only type a name (e.g. Orange) if detection gets it wrong - it then stays fixed for every game until you clear it with Reset."))
                .setErrorSupplier(v -> v.length() > 32 ? Optional.of(Component.literal("Too long")) : Optional.empty())
                .setSaveConsumer(v -> work.colorOverride = v.strip())
                .build());

        // ---------------------------------------------------------------- Warnings
        ConfigCategory warn = builder.getOrCreateCategory(Component.literal("Warnings"));
        warn.addEntry(eb.startBooleanToggle(Component.literal("Ignore my team"), work.ignoreTeammates)
                .setDefaultValue(def.ignoreTeammates)
                .setTooltip(tip("Players whose name has the same color as yours in the tab list never trigger a warning."))
                .setSaveConsumer(v -> work.ignoreTeammates = v)
                .build());
        warn.addEntry(eb.startStrList(Component.literal("Ignore players"), new ArrayList<>(work.ignoredPlayers))
                .setDefaultValue(def.ignoredPlayers)
                .setExpanded(true)
                .setInsertInFront(false)
                .setAddButtonTooltip(Component.literal("Add a player name"))
                .setRemoveButtonTooltip(Component.literal("Remove"))
                .setTooltip(tip("These players never trigger a warning (not case sensitive). The round + button adds a name; click a name, then the round - button, to remove it."))
                .setSaveConsumer(v -> work.ignoredPlayers = new ArrayList<>(v))
                .build());
        warn.addEntry(eb.startDoubleField(Component.literal("Cooldown (seconds)"), work.cooldownSeconds)
                .setDefaultValue(def.cooldownSeconds)
                .setMin(0).setMax(EggerConfig.MAX_COOLDOWN)
                .setTooltip(tip("The same player can't trigger the same radius again for this long. Every radius has its own cooldown."))
                .setSaveConsumer(v -> work.cooldownSeconds = v)
                .build());
        warn.addEntry(eb.startDoubleField(Component.literal("Group players within (seconds)"), work.groupSeconds)
                .setDefaultValue(def.groupSeconds)
                .setMin(0).setMax(EggerConfig.MAX_GROUP)
                .setTooltip(tip("Players coming into the same radius this close together share one message ([players] lists them all). 0 = send at once."))
                .setSaveConsumer(v -> work.groupSeconds = v)
                .build());
        warn.addEntry(eb.startDoubleField(Component.literal("Gap between messages (seconds)"), work.messageGapSeconds)
                .setDefaultValue(def.messageGapSeconds)
                .setMin(EggerConfig.MIN_GAP).setMax(EggerConfig.MAX_GAP)
                .setTooltip(tip("At least this long between two chat messages from the mod (1 second minimum: vanilla kicks after about 10 quick messages and forgives one per second). Extra messages wait in line."))
                .setSaveConsumer(v -> work.messageGapSeconds = v)
                .build());

        // ---------------------------------------------------------------- Radii
        ConfigCategory radii = builder.getOrCreateCategory(Component.literal("Radii"));
        radii.addEntry(eb.startTextDescription(Component.literal("Distances are measured sideways only: height doesn't count. Only coming IN warns; leaving never does. "
                + "Placeholders: [players] all names, [player1] [player2] ... one name each, [count], [radius], [color]. A message starting with / runs as a command.")
                .withStyle(ChatFormatting.GRAY)).build());
        List<RadiusRule> rules = new ArrayList<>(work.radii);
        NestedListListEntry<RadiusRule, MultiElementListEntry<RadiusRule>> list = new NestedListListEntry<>(
                Component.literal("Warning radii"),
                rules,
                true,
                () -> Optional.of(tip("The round + button adds a radius. To remove one, click into it, then press the round - button. Each radius sends its own message when a player comes inside it.")),
                v -> work.radii = new ArrayList<>(v),
                () -> copyRules(def.radii),
                Component.literal("Reset"),
                true,
                false,
                (rule, owner) -> ruleCell(eb, rule == null ? new RadiusRule(30, RadiusRule.DEFAULT_MESSAGE, RadiusRule.Mode.CHAT, true) : rule));
        list.setErrorSupplier(() -> list.getValue().size() > EggerConfig.MAX_RULES
                ? Optional.of(Component.literal("At most " + EggerConfig.MAX_RULES + " radii")) : Optional.empty());
        radii.addEntry(list);
        radii.addEntry(eb.startTextDescription(Component.literal("Preview of your saved messages, if " + SAMPLE_1 + " and " + SAMPLE_2 + " came in:")
                .withStyle(ChatFormatting.YELLOW)).build());
        for (Component line : preview(EggerConfig.get())) {
            radii.addEntry(eb.startTextDescription(line).build());
        }
        return builder.build();
    }

    private static MultiElementListEntry<RadiusRule> ruleCell(ConfigEntryBuilder eb, RadiusRule rule) {
        RadiusRule start = rule.copy(); // what each field's Reset goes back to
        List<AbstractConfigListEntry<?>> fields = new ArrayList<>();
        IntegerListEntry radiusField = eb.startIntField(Component.literal("Radius (blocks)"), rule.radius)
                .setDefaultValue(start.radius)
                .setMin(RadiusRule.MIN_RADIUS).setMax(RadiusRule.MAX_RADIUS)
                .setTooltip(tip("Blocks around the egg, measured sideways only. A player warns when they come inside it."))
                .setSaveConsumer(v -> rule.radius = v)
                .build();
        fields.add(radiusField);
        StringListEntry messageField = eb.startStrField(Component.literal("Message"), rule.message)
                .setDefaultValue(start.message)
                .setTooltip(tip("What is sent. [players] all names, [player1] [player2] one each, [count], [radius], [color]. Start with / to run a command."))
                .setErrorSupplier(v -> v.length() > EggerConfig.MAX_MESSAGE_LENGTH
                        ? Optional.of(Component.literal("Longer than " + EggerConfig.MAX_MESSAGE_LENGTH + " characters")) : Optional.empty())
                .setSaveConsumer(v -> rule.message = v)
                .build();
        fields.add(messageField);
        EnumListEntry<RadiusRule.Mode> modeField = eb.startEnumSelector(Component.literal("Send to"), RadiusRule.Mode.class, rule.mode)
                .setDefaultValue(start.mode)
                .setEnumNameProvider(m -> Component.literal(m == RadiusRule.Mode.CHAT ? "Chat" : "Only me"))
                .setTooltip(tip("Chat: typed into chat like you would (your server sends it to your team chat). Only me: shown only to you, nothing is sent."))
                .setSaveConsumer(v -> rule.mode = v)
                .build();
        fields.add(modeField);
        BooleanListEntry onField = eb.startBooleanToggle(Component.literal("On"), rule.enabled)
                .setDefaultValue(start.enabled)
                .setTooltip(tip("Switch just this radius off without deleting it."))
                .setSaveConsumer(v -> rule.enabled = v)
                .build();
        fields.add(onField);
        return new MultiElementListEntry<>(Component.literal("Radius"), rule, fields, true) {
            @Override
            public Component getFieldName() {
                // follows the number while you type it
                return Component.literal("Radius: " + (radiusField.getError().isPresent() ? "?" : radiusField.getValue()) + " blocks");
            }

            @Override
            public RadiusRule getValue() {
                // what the fields show right now, so the list's Reset button and "edited" state are right
                return new RadiusRule(radiusField.getValue(), messageField.getValue(), modeField.getValue(), onField.getValue());
            }
        };
    }

    private static List<RadiusRule> copyRules(List<RadiusRule> rules) {
        List<RadiusRule> out = new ArrayList<>();
        for (RadiusRule r : rules) {
            out.add(r.copy());
        }
        return out;
    }

    private static List<Component> preview(EggerConfig cfg) {
        List<Component> out = new ArrayList<>();
        String colorName = DetectorAccess.previewColorName();
        List<RadiusRule> sorted = new ArrayList<>(cfg.radii);
        sorted.sort((a, b) -> Integer.compare(b.radius, a.radius));
        for (RadiusRule r : sorted) {
            if (!r.enabled) {
                continue;
            }
            String text = MessageFormatter.format(r.message, List.of(SAMPLE_1, SAMPLE_2), r.radius, colorName);
            String where = r.mode == RadiusRule.Mode.CHAT ? (text.startsWith("/") ? "command" : "chat") : "only you";
            out.add(Component.literal(r.radius + " blocks (" + where + "): ").withStyle(ChatFormatting.GRAY)
                    .append(Component.literal(text.isBlank() ? "(empty - nothing is sent)" : text).withStyle(ChatFormatting.WHITE)));
        }
        if (out.isEmpty()) {
            out.add(Component.literal("No radius is switched on.").withStyle(ChatFormatting.GRAY));
        }
        return out;
    }

    /** Tooltip text wrapped into short lines. */
    static Component[] tip(String text) {
        List<Component> lines = new ArrayList<>();
        StringBuilder line = new StringBuilder();
        for (String word : text.split(" ")) {
            if (line.length() > 0 && line.length() + 1 + word.length() > TIP_WIDTH) {
                lines.add(Component.literal(line.toString()));
                line.setLength(0);
            }
            if (line.length() > 0) {
                line.append(' ');
            }
            line.append(word);
        }
        if (line.length() > 0) {
            lines.add(Component.literal(line.toString()));
        }
        return lines.toArray(new Component[0]);
    }
}
