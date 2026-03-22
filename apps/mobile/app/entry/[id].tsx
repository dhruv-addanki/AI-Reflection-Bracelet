import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { WarmButton } from "../../src/components/WarmButton";
import { getSession } from "../../src/lib/api";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { TagChip } from "../../src/components/TagChip";
import { TonePill } from "../../src/components/TonePill";
import { theme } from "../../src/theme";

export default function EntryDetailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const sessionId = params.id;
  const query = useQuery({
    queryKey: ["session-detail", sessionId],
    enabled: Boolean(sessionId),
    queryFn: () => getSession(sessionId!)
  });

  const detail = query.data;
  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }

    router.replace("/entries");
  };

  return (
    <ScreenContainer>
      <WarmButton label="Back to entries" onPress={handleBack} variant="ghost" style={styles.backButton} />
      <Text style={styles.title}>Entry detail</Text>
      {!detail ? (
        <Text style={styles.body}>Loading session...</Text>
      ) : (
        <>
          <SectionCard title="Transcript">
            <Text style={styles.body}>{detail.evaluation?.transcript ?? detail.session.transcriptOverride ?? "No transcript available."}</Text>
          </SectionCard>
          <SectionCard title="Tone labels">
            <View style={styles.wrap}>
              {(detail.evaluation?.toneLabels ?? []).map((label) => (
                <TonePill key={label} label={label} />
              ))}
            </View>
          </SectionCard>
          <SectionCard title="Trigger tags">
            <View style={styles.wrap}>
              {(detail.evaluation?.triggerTags ?? []).map((label) => (
                <TagChip key={label} label={label} tone="warm" />
              ))}
            </View>
          </SectionCard>
          <SectionCard title="Distress intensity">
            <Text style={styles.body}>{detail.evaluation?.distressIntensity ?? 0} / 10</Text>
          </SectionCard>
          <SectionCard title="Synthesis summary">
            <Text style={styles.body}>{detail.evaluation?.oneLineSummary ?? "Summary not available."}</Text>
            <Text style={styles.body}>{detail.evaluation?.heartSummary}</Text>
            <Text style={styles.body}>{detail.evaluation?.supportSuggestion}</Text>
          </SectionCard>
        </>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  backButton: {
    alignSelf: "flex-start"
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  body: {
    color: theme.colors.textMuted,
    lineHeight: 22
  },
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  }
});
