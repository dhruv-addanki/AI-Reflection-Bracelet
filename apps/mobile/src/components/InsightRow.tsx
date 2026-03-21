import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export function InsightRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    gap: 6
  },
  label: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.6
  },
  value: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 21
  }
});
