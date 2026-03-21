import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export function TimelineBlock({
  label,
  timeRange,
  feeling,
  intensity
}: {
  label: string;
  timeRange: string;
  feeling: string;
  intensity: number;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.meta}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.time}>{timeRange}</Text>
      </View>
      <View style={styles.barWrap}>
        <View style={[styles.bar, { width: `${Math.max(16, intensity * 10)}%` }]} />
      </View>
      <Text style={styles.feeling}>{feeling}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    gap: theme.spacing.sm
  },
  meta: {
    flexDirection: "row",
    justifyContent: "space-between"
  },
  label: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: "600"
  },
  time: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label
  },
  barWrap: {
    height: 10,
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.cardMuted,
    overflow: "hidden"
  },
  bar: {
    height: "100%",
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.accent
  },
  feeling: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label,
    textTransform: "capitalize"
  }
});
