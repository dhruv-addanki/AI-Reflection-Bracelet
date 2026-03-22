import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export function ReflectionPromptCard({ prompt }: { prompt: string }) {
  return (
    <View style={styles.card}>
      <Text style={styles.eyebrow}>Reflection prompt</Text>
      <Text style={styles.prompt}>{prompt}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FCE9D5",
    borderColor: theme.colors.accentSoft,
    borderWidth: 1,
    borderRadius: theme.radii.lg,
    padding: theme.spacing.md,
    gap: theme.spacing.xs,
    shadowColor: "#C7844E",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 2
  },
  eyebrow: {
    color: theme.colors.accent,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    fontSize: theme.typography.label
  },
  prompt: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 22
  }
});
