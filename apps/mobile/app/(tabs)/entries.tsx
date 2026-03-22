import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { StyleSheet, Text, TextInput, View } from "react-native";

import { EmptyState } from "../../src/components/EmptyState";
import { ReflectionPromptCard } from "../../src/components/ReflectionPromptCard";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { WarmButton } from "../../src/components/WarmButton";
import { getDailySummary, getReflectionHistory, saveDailyReflection } from "../../src/lib/api";
import { formatFriendlyDate, todayIsoDate } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
import { theme } from "../../src/theme";

export default function ReflectionsScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, device } = useSession();
  const date = todayIsoDate();
  const [draft, setDraft] = useState("");

  const todayQuery = useQuery({
    queryKey: ["daily-summary", user?.id, date],
    enabled: Boolean(user),
    queryFn: () => getDailySummary(user!.id, date)
  });
  const historyQuery = useQuery({
    queryKey: ["reflection-history", user?.id],
    enabled: Boolean(user),
    queryFn: () => getReflectionHistory(user!.id)
  });

  useEffect(() => {
    setDraft(todayQuery.data?.reflectionResponse ?? "");
  }, [todayQuery.data?.id, todayQuery.data?.reflectionResponse]);

  const saveMutation = useMutation({
    mutationFn: async () => saveDailyReflection(user!.id, date, draft.trim()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["daily-summary", user?.id, date] });
      await queryClient.invalidateQueries({ queryKey: ["reflection-history", user?.id] });
    }
  });

  if (!user) {
    return (
      <ScreenContainer>
        <EmptyState
          title="Start with onboarding"
          description="Create your profile first so the reflection questions feel tailored to you."
          actionLabel="Go to welcome"
          onAction={() => router.replace("/welcome")}
        />
      </ScreenContainer>
    );
  }

  if (!device) {
    return (
      <ScreenContainer>
        <EmptyState
          title="Pair the bracelet first"
          description="The reflection journal unlocks after the bracelet has a user and device context."
          actionLabel="Pair bracelet"
          onAction={() => router.push("/pair")}
        />
      </ScreenContainer>
    );
  }

  const todaySummary = todayQuery.data;
  const history = (historyQuery.data ?? []).filter((item) => item.reflectionResponse);
  const pastReflections = history.filter((item) => item.date !== date);

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.title}>Reflections</Text>
        <Text style={styles.subtitle}>Each day gets one thoughtful question from the AI. Answer it here, then look back on how your responses evolve over time.</Text>
      </View>

      {!todaySummary ? (
        <EmptyState
          title="No reflection prompt yet"
          description="Today’s question appears after at least one synced voice note gives the model enough context to ask something useful."
          actionLabel="Sync notes"
          onAction={() => router.push("/simulate")}
        />
      ) : (
        <SectionCard title="Today’s reflection" subtitle={formatFriendlyDate(todaySummary.date)}>
          <ReflectionPromptCard prompt={todaySummary.reflectionPrompt} />
          <TextInput
            multiline
            value={draft}
            onChangeText={setDraft}
            placeholder="Write a short reflection about what the question brings up for you."
            placeholderTextColor={theme.colors.textMuted}
            style={styles.input}
            textAlignVertical="top"
          />
          <WarmButton
            label={todaySummary.reflectionResponse ? "Update reflection" : "Save reflection"}
            onPress={() => saveMutation.mutate()}
            loading={saveMutation.isPending}
            disabled={!draft.trim()}
          />
        </SectionCard>
      )}

      <SectionCard title="Past reflections" subtitle="Your previous daily answers, newest first.">
        {pastReflections.length ? (
          <View style={styles.historyList}>
            {pastReflections.map((item) => (
              <View key={item.id} style={styles.historyCard}>
                <Text style={styles.historyDate}>{formatFriendlyDate(item.date)}</Text>
                <Text style={styles.historyPrompt}>{item.reflectionPrompt}</Text>
                <Text style={styles.historyResponse}>{item.reflectionResponse}</Text>
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.body}>Your saved daily reflections will build up here after you answer a few prompts.</Text>
        )}
      </SectionCard>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: {
    gap: theme.spacing.xs
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  input: {
    minHeight: 140,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.backgroundElevated,
    padding: theme.spacing.md,
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  historyList: {
    gap: theme.spacing.sm
  },
  historyCard: {
    backgroundColor: "#FCE9D5",
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: "#F0C9A5",
    padding: theme.spacing.md,
    gap: theme.spacing.xs
  },
  historyDate: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.6
  },
  historyPrompt: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: theme.typography.heading
  },
  historyResponse: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  body: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  }
});
