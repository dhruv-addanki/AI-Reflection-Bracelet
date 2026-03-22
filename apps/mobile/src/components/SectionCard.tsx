import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export function SectionCard({
  title,
  subtitle,
  children
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.card}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      <View style={styles.body}>{children}</View>
    </View>
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
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: theme.typography.heading
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label,
    lineHeight: 18
  },
  body: {
    gap: theme.spacing.sm
  }
});
