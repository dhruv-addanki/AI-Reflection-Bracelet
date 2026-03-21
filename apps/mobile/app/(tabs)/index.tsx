import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { getDailySummary, getTodaySessions } from "../../src/lib/api";
import { todayIsoDate } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
import { EmptyState } from "../../src/components/EmptyState";
import { EntryCard } from "../../src/components/EntryCard";
import { InsightRow } from "../../src/components/InsightRow";
import { ReflectionPromptCard } from "../../src/components/ReflectionPromptCard";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { TimelineBlock } from "../../src/components/TimelineBlock";
import { WarmButton } from "../../src/components/WarmButton";
import { theme } from "../../src/theme";

export default function HomeScreen() {
  const router = useRouter();
  const { user, device } = useSession();
  const date = todayIsoDate();

  const dailyQuery = useQuery({
    queryKey: ["daily-summary", user?.id, date],
    enabled: Boolean(user),
    queryFn: () => getDailySummary(user!.id, date)
  });
  const sessionsQuery = useQuery({
    queryKey: ["today-sessions", user?.id, date],
    enabled: Boolean(user),
    queryFn: () => getTodaySessions(user!.id, date)
  });

  if (!user) {
    return (
      <ScreenContainer>
        <EmptyState
          title="Start with onboarding"
          description="Add your profile first so the recap language has the right tone."
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
          title="No bracelet paired yet"
          description="Use the fake pairing flow to create a believable device connection before you start simulating sessions."
          actionLabel="Pair bracelet"
          onAction={() => router.push("/pair")}
        />
      </ScreenContainer>
    );
  }

  const summary = dailyQuery.data;
  const sessions = sessionsQuery.data ?? [];

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.eyebrow}>Today&apos;s reflection</Text>
        <Text style={styles.title}>Good {getGreeting()}, {user.name.split(" ")[0]}.</Text>
        <Text style={styles.subtitle}>
          {summary?.emotionalRecap ?? "Simulate a few sessions and the bracelet will start stitching the day together here."}
        </Text>
      </View>

      {summary ? (
        <>
          <SectionCard title="Emotional recap">
            <InsightRow label="Hardest moment" value={summary.hardestMoment} />
            <InsightRow label="Calmest moment" value={summary.calmestMoment} />
            <InsightRow label="Most repeated feeling" value={summary.repeatedFeeling} />
            <InsightRow label="One thing to notice" value={summary.oneThingToNotice} />
          </SectionCard>

          <SectionCard title="Mood timeline">
            {summary.moodTimeline.map((block) => (
              <TimelineBlock key={`${block.label}-${block.timeRange}`} {...block} />
            ))}
          </SectionCard>

          <SectionCard title="Mixed feelings">
            <Text style={styles.body}>{summary.mixedFeelingInsight}</Text>
          </SectionCard>

          <SectionCard title="End-of-day reflection">
            <Text style={styles.body}>{summary.recapParagraph}</Text>
          </SectionCard>

          <ReflectionPromptCard prompt={summary.reflectionPrompt} />
        </>
      ) : (
        <EmptyState
          title="No recap yet"
          description="Create a few mock bracelet sessions and the daily summary will populate with emotional recap, timeline blocks, and reflection prompts."
          actionLabel="Simulate a session"
          onAction={() => router.push("/simulate")}
        />
      )}

      <SectionCard title="Quick actions">
        <View style={styles.actions}>
          <WarmButton label="Talk more" onPress={() => router.push("/simulate")} style={styles.actionButton} />
          <WarmButton label="View entries" onPress={() => router.push("/entries")} variant="ghost" style={styles.actionButton} />
          <WarmButton label="See patterns" onPress={() => router.push("/patterns")} variant="ghost" style={styles.actionButton} />
        </View>
      </SectionCard>

      <SectionCard title="Latest entries">
        {sessions.length ? (
          sessions.slice(0, 3).map((item) => (
            <EntryCard key={item.session.id} session={item.session} evaluation={item.evaluation} onPress={() => router.push(`/entry/${item.session.id}`)} />
          ))
        ) : (
          <Text style={styles.body}>Today&apos;s entries will appear here once you simulate or upload bracelet-style sessions.</Text>
        )}
      </SectionCard>
    </ScreenContainer>
  );
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) {
    return "morning";
  }
  if (hour < 18) {
    return "afternoon";
  }
  return "evening";
}

const styles = StyleSheet.create({
  hero: {
    gap: theme.spacing.xs,
    paddingTop: theme.spacing.sm
  },
  eyebrow: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.8
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
  body: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  actions: {
    gap: theme.spacing.sm
  },
  actionButton: {
    width: "100%"
  }
});
