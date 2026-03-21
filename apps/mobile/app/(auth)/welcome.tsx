import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { WarmButton } from "../../src/components/WarmButton";
import { theme } from "../../src/theme";

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.kicker}>Voice-first reflection</Text>
        <Text style={styles.title}>Talk through your day and get a calmer read on what it held.</Text>
        <Text style={styles.body}>
          Short voice notes become daily reflection, entry-level insight, and longer patterns without needing the hardware to be built yet.
        </Text>
      </View>

      <SectionCard title="What the bracelet is for">
        <Text style={styles.body}>It listens to brief check-ins, adds heart-rate context, and turns those moments into supportive summaries.</Text>
        <Text style={styles.body}>For now, you can pair a mock bracelet and simulate uploads to demo the full product flow.</Text>
      </SectionCard>

      <WarmButton label="Start onboarding" onPress={() => router.push("/onboarding")} />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: {
    paddingTop: theme.spacing.xl,
    gap: theme.spacing.sm
  },
  kicker: {
    color: theme.colors.accent,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    fontSize: theme.typography.label
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 34,
    lineHeight: 40
  },
  body: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  }
});
