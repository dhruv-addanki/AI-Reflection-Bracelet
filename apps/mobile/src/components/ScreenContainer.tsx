import type { ReactNode } from "react";
import { ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "../theme";

type Props = {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  scroll?: boolean;
};

export function ScreenContainer({ children, style, scroll = true }: Props) {
  const content = (
    <View style={styles.shell}>
      <View style={styles.glowTop} pointerEvents="none" />
      <View style={styles.glowBottom} pointerEvents="none" />
      <View style={[styles.content, style]}>{children}</View>
    </View>
  );
  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      {scroll ? <ScrollView contentContainerStyle={styles.scroll}>{content}</ScrollView> : content}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.background
  },
  scroll: {
    paddingBottom: theme.spacing.xxl
  },
  shell: {
    overflow: "hidden"
  },
  glowTop: {
    position: "absolute",
    top: -120,
    right: -60,
    width: 280,
    height: 280,
    borderRadius: 140,
    backgroundColor: "rgba(245, 128, 56, 0.10)"
  },
  glowBottom: {
    position: "absolute",
    bottom: 40,
    left: -70,
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: "rgba(232, 154, 99, 0.08)"
  },
  content: {
    paddingHorizontal: theme.spacing.md,
    paddingTop: theme.spacing.lg,
    gap: theme.spacing.md
  }
});
