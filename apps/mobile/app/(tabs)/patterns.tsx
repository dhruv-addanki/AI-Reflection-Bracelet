import { useQuery } from "@tanstack/react-query";
import { StyleSheet, Text, View } from "react-native";

import { EmptyState } from "../../src/components/EmptyState";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { TagChip } from "../../src/components/TagChip";
import { getWeeklyPatternHistory, getWeeklyPatterns } from "../../src/lib/api";
import { formatWeekOf, startOfWeekIso } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
import { theme } from "../../src/theme";

export default function PatternsScreen() {
  const { user } = useSession();
  const weekStart = startOfWeekIso();

  const currentQuery = useQuery({
    queryKey: ["weekly-patterns", user?.id, weekStart],
    enabled: Boolean(user),
    queryFn: () => getWeeklyPatterns(user!.id, weekStart)
  });
  const historyQuery = useQuery({
    queryKey: ["weekly-pattern-history", user?.id],
    enabled: Boolean(user),
    queryFn: () => getWeeklyPatternHistory(user!.id)
  });

  const current = currentQuery.data;
  const history = (historyQuery.data ?? []).filter((item) => item.weekStart !== weekStart);

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.title}>Weekly reflections</Text>
        <Text style={styles.subtitle}>Pattern recognition turns isolated voice notes into something more useful: what repeats, when it spikes, and what actually seems to help.</Text>
      </View>

      {!current ? (
        <EmptyState title="No weekly pattern yet" description="A few processed sessions across the week will surface recurring triggers, time windows, and a weekly reflection." />
      ) : (
        <>
          <SectionCard title="This week in patterns" subtitle={`Week of ${formatWeekOf(current.weekStart)}`}>
            <Text style={styles.reflection}>{current.weeklyReflection}</Text>
          </SectionCard>

          <SectionCard title="Recurring triggers">
            <WrapList items={current.topTriggers} tone="red" />
          </SectionCard>

          <SectionCard title="Hardest windows">
            <WrapList items={current.hardestTimeWindows} tone="warm" />
          </SectionCard>

          <SectionCard title="Repeated self-talk">
            <WrapList items={current.repeatedSelfTalkPatterns} />
          </SectionCard>

          <SectionCard title="Support that helps">
            <View style={styles.stack}>
              {current.supportStrategiesThatHelp.map((item) => (
                <Text key={item} style={styles.body}>
                  {item}
                </Text>
              ))}
            </View>
          </SectionCard>
        </>
      )}

      <SectionCard title="Past weekly reflections" subtitle="Earlier pattern snapshots, newest first.">
        {history.length ? (
          <View style={styles.historyList}>
            {history.map((item) => (
              <View key={item.id} style={styles.historyCard}>
                <Text style={styles.historyDate}>Week of {formatWeekOf(item.weekStart)}</Text>
                <Text style={styles.historyReflection}>{item.weeklyReflection}</Text>
                <WrapList items={item.topTriggers.slice(0, 3)} tone="red" />
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.body}>Past weekly reflections will collect here once the app has more than one week of pattern data.</Text>
        )}
      </SectionCard>
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
  hero: {
    gap: theme.spacing.xs
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  reflection: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 24
  },
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  },
  stack: {
    gap: theme.spacing.sm
  },
  historyList: {
    gap: theme.spacing.sm
  },
  historyCard: {
    backgroundColor: "#FCE9D5",
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: "#F0C9A5",
    padding: theme.spacing.md,
    gap: theme.spacing.sm
  },
  historyDate: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.6
  },
  historyReflection: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  body: {
    color: theme.colors.textMuted,
    lineHeight: 21
  }
});
