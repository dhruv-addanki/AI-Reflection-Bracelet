import { ActivityIndicator, Pressable, StyleSheet, Text, type StyleProp, type ViewStyle } from "react-native";

import { theme } from "../theme";

export function WarmButton({
  label,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
  style
}: {
  label: string;
  onPress: () => void;
  variant?: "primary" | "ghost";
  disabled?: boolean;
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <Pressable
      style={[
        styles.base,
        variant === "primary" ? styles.primary : styles.ghost,
        (disabled || loading) && styles.disabled,
        style
      ]}
      disabled={disabled || loading}
      onPress={onPress}
    >
      {loading ? (
        <ActivityIndicator color={theme.colors.text} />
      ) : (
        <Text style={[styles.label, variant === "ghost" && styles.ghostLabel]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    borderRadius: theme.radii.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: theme.spacing.md,
    borderWidth: 1
  },
  primary: {
    backgroundColor: theme.colors.accent,
    borderColor: theme.colors.accent
  },
  ghost: {
    backgroundColor: "transparent",
    borderColor: theme.colors.border
  },
  disabled: {
    opacity: 0.65
  },
  label: {
    color: theme.colors.background,
    fontWeight: "600",
    fontSize: theme.typography.body
  },
  ghostLabel: {
    color: theme.colors.text
  }
});
