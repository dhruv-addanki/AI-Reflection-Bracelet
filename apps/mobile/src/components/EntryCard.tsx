import type { ClipEvaluation, RawSession } from "@bracelet/shared-types";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { formatClock } from "../lib/date";
import { theme } from "../theme";
import { TagChip } from "./TagChip";
import { TonePill } from "./TonePill";

export function EntryCard({
  session,
  evaluation,
  onPress
}: {
  session: RawSession;
  evaluation: ClipEvaluation | null;
  onPress?: () => void;
}) {
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.header}>
        <Text style={styles.time}>{formatClock(session.startedAt)}</Text>
        <Text style={styles.meta}>{session.sourceType === "bracelet" ? "bracelet sync" : "note sync"}</Text>
      </View>
      <Text style={styles.summary}>
        {evaluation?.oneLineSummary ?? "A processed entry will appear here once the session is analyzed."}
      </Text>
      <View style={styles.row}>
        {(evaluation?.primaryFeelings ?? []).slice(0, 2).map((label) => (
          <TonePill key={label} label={label} />
        ))}
      </View>
      {evaluation?.mixedFeelings?.[0] ? <Text style={styles.mixed}>{evaluation.mixedFeelings[0]}</Text> : null}
      {evaluation?.heartSummary ? <Text style={styles.note}>{evaluation.heartSummary}</Text> : null}
      {evaluation?.supportSuggestion ? (
        <View style={styles.footer}>
          <TagChip label="Support suggestion" tone="warm" />
          <Text style={styles.note}>{evaluation.supportSuggestion}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    gap: theme.spacing.sm,
    shadowColor: "#B77A4C",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.12,
    shadowRadius: 18,
    elevation: 3
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between"
  },
  time: {
    color: theme.colors.text,
    fontWeight: "600"
  },
  meta: {
    color: theme.colors.textMuted,
    textTransform: "capitalize"
  },
  summary: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  row: {
    flexDirection: "row",
    gap: theme.spacing.sm,
    flexWrap: "wrap"
  },
  mixed: {
    color: theme.colors.gold,
    fontSize: theme.typography.label,
    fontStyle: "italic"
  },
  note: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label,
    lineHeight: 18
  },
  footer: {
    gap: theme.spacing.sm
  }
});
