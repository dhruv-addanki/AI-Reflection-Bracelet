import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export function TagChip({ label, tone = "default" }: { label: string; tone?: "default" | "warm" | "red" }) {
  return (
    <View
      style={[
        styles.chip,
        tone === "warm" && styles.warm,
        tone === "red" && styles.red
      ]}
    >
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 6,
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.cardMuted,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  warm: {
    backgroundColor: "rgba(240,138,60,0.12)",
    borderColor: theme.colors.accentSoft
  },
  red: {
    backgroundColor: "rgba(184,90,78,0.12)",
    borderColor: theme.colors.redMuted
  },
  label: {
    color: theme.colors.text,
    fontSize: theme.typography.label
  }
});
