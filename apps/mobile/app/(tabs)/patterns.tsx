import { useQuery } from "@tanstack/react-query";
import { StyleSheet, Text, View } from "react-native";

import { getWeeklyPatterns } from "../../src/lib/api";
import { startOfWeekIso } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
import { EmptyState } from "../../src/components/EmptyState";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { TagChip } from "../../src/components/TagChip";
import { theme } from "../../src/theme";

export default function PatternsScreen() {
  const { user } = useSession();
  const weekStart = startOfWeekIso();
  const query = useQuery({
    queryKey: ["weekly-patterns", user?.id, weekStart],
    enabled: Boolean(user),
    queryFn: () => getWeeklyPatterns(user!.id, weekStart)
  });

  const patterns = query.data;

  return (
    <ScreenContainer>
      <Text style={styles.title}>Weekly patterns</Text>
      <Text style={styles.subtitle}>Recurring themes help the product move beyond isolated entries and into pattern recognition.</Text>

      {!patterns ? (
        <EmptyState title="No weekly patterns yet" description="A few processed sessions across the week will surface time windows, triggers, and the support strategies that tend to help." />
      ) : (
        <>
          <SectionCard title="Recurring triggers">
            <WrapList items={patterns.topTriggers} tone="red" />
          </SectionCard>
          <SectionCard title="Hardest time windows">
            <WrapList items={patterns.hardestTimeWindows} tone="warm" />
          </SectionCard>
          <SectionCard title="Repeated self-talk">
            <WrapList items={patterns.repeatedSelfTalkPatterns} />
          </SectionCard>
          <SectionCard title="What helps most">
            <View style={styles.stack}>
              {patterns.supportStrategiesThatHelp.map((item) => (
                <Text key={item} style={styles.body}>
                  {item}
                </Text>
              ))}
            </View>
          </SectionCard>
          <SectionCard title="Weekly reflection">
            <Text style={styles.body}>{patterns.weeklyReflection}</Text>
          </SectionCard>
        </>
      )}
    </ScreenContainer>
  );
}

function WrapList({ items, tone = "default" }: { items: string[]; tone?: "default" | "warm" | "red" }) {
  return (
    <View style={styles.wrap}>
      {items.map((item) => (
        <TagChip key={item} label={item} tone={tone} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  subtitle: {
    color: theme.colors.textMuted,
    lineHeight: 22
  },
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  },
  stack: {
    gap: theme.spacing.sm
  },
  body: {
    color: theme.colors.textMuted,
    lineHeight: 21
  }
});
