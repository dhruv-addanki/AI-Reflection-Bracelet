import type { ClipEvaluation, RawSession } from "@bracelet/shared-types";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { EmptyState } from "../../src/components/EmptyState";
import { InsightRow } from "../../src/components/InsightRow";
import { ReflectionPromptCard } from "../../src/components/ReflectionPromptCard";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { TagChip } from "../../src/components/TagChip";
import { WarmButton } from "../../src/components/WarmButton";
import { getDailySummary, getTodaySessions } from "../../src/lib/api";
import { formatClock, formatLongDate, todayIsoDate } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
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
          description="Add your profile first so the recap language and reflection prompts feel personal."
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
          description="Pair the mock bracelet first so today’s homepage can fill with summaries, voice-note moments, and reflection prompts."
          actionLabel="Pair bracelet"
          onAction={() => router.push("/pair")}
        />
      </ScreenContainer>
    );
  }

  const summary = dailyQuery.data;
  const sessions = sessionsQuery.data ?? [];
  const emotionPoints = collectEmotionPoints(sessions);

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.date}>{formatLongDate(date)}</Text>
        <Text style={styles.title}>Good {getGreeting()}, {user.name.split(" ")[0]}.</Text>
        <Text style={styles.subtitle}>
          {summary?.emotionalRecap ?? "Your daily summary will appear here once a few voice notes have been processed."}
        </Text>
      </View>

      {!summary ? (
        <EmptyState
          title="No summary yet"
          description="Simulate or upload a few bracelet-style voice notes and the homepage will turn into a daily recap with emotions, causes, and a timeline of today’s recordings."
          actionLabel="Simulate session"
          onAction={() => router.push("/simulate")}
        />
      ) : (
        <>
          <SectionCard title="Daily summary" subtitle={summary.recapParagraph}>
            <View style={styles.summaryGroup}>
              <Text style={styles.groupLabel}>Emotion points</Text>
              <View style={styles.chipWrap}>
                {emotionPoints.length ? (
                  emotionPoints.map((point) => <TagChip key={point} label={point} tone={getEmotionTone(point)} />)
                ) : (
                  <TagChip label={summary.repeatedFeeling} tone={getEmotionTone(summary.repeatedFeeling)} />
                )}
              </View>
            </View>
            <View style={styles.summaryGroup}>
              <Text style={styles.groupLabel}>Likely causes</Text>
              <View style={styles.causeList}>
                {summary.emotionDrivers.map((item) => (
                  <Text key={item} style={styles.causeItem}>
                    {item}
                  </Text>
                ))}
              </View>
            </View>
          </SectionCard>

          <SectionCard title="Today’s voice notes" subtitle="A vertical timeline of how the day sounded and what seems to be driving it.">
            {sessions.length ? (
              <View style={styles.timeline}>
                <View style={styles.timelineRail} />
                {sessions.map((item, index) => (
                  <VoiceTimelineItem
                    key={item.session.id}
                    session={item.session}
                    evaluation={item.evaluation}
                    isLast={index === sessions.length - 1}
                    onPress={() => router.push(`/entry/${item.session.id}`)}
                  />
                ))}
              </View>
            ) : (
              <Text style={styles.body}>Today’s recordings will appear here as soon as your first processed voice note lands.</Text>
            )}
          </SectionCard>

          <SectionCard title="What stood out">
            <InsightRow label="Hardest moment" value={summary.hardestMoment} />
            <InsightRow label="Calmest moment" value={summary.calmestMoment} />
            <InsightRow label="Most repeated feeling" value={summary.repeatedFeeling} />
            <InsightRow label="One thing to notice" value={summary.oneThingToNotice} />
            <InsightRow label="Mixed feelings" value={summary.mixedFeelingInsight} />
          </SectionCard>

          <ReflectionPromptCard prompt={summary.reflectionPrompt} />

          <WarmButton label="Write today’s reflection" onPress={() => router.push("/entries")} />
        </>
      )}
    </ScreenContainer>
  );
}

function VoiceTimelineItem({
  session,
  evaluation,
  isLast,
  onPress
}: {
  session: RawSession;
  evaluation: ClipEvaluation | null;
  isLast: boolean;
  onPress: () => void;
}) {
  const cause = evaluation?.triggerTags[0] ?? evaluation?.selfTalkMarkers[0] ?? "general pressure";

  return (
    <Pressable style={[styles.timelineRow, isLast && styles.timelineRowLast]} onPress={onPress}>
      <View style={styles.nodeWrap}>
        <View style={styles.nodeOuter}>
          <View style={styles.nodeInner} />
        </View>
      </View>
      <View style={styles.timelineCard}>
        <Text style={styles.timelineTime}>{formatClock(session.startedAt)}</Text>
        <Text style={styles.timelineTitle}>{evaluation?.primaryFeelings[0] ?? "Reflective moment"}</Text>
        <Text style={styles.timelineSummary}>
          {evaluation?.oneLineSummary ?? "A processed insight will appear here once the note has been analyzed."}
        </Text>
        <Text style={styles.timelineCause}>Cause: {cause}</Text>
      </View>
    </Pressable>
  );
}

function collectEmotionPoints(sessions: { evaluation: ClipEvaluation | null }[]) {
  const counts = new Map<string, number>();

  sessions.forEach((item) => {
    item.evaluation?.primaryFeelings.forEach((feeling) => {
      counts.set(feeling, (counts.get(feeling) ?? 0) + 1);
    });
  });

  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 4)
    .map(([label]) => label);
}

function getEmotionTone(label: string) {
  const lowered = label.toLowerCase();
  return lowered.includes("anx") || lowered.includes("stress") || lowered.includes("over") || lowered.includes("frustr") ? "red" : "warm";
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
  date: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 32
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 24
  },
  summaryGroup: {
    gap: theme.spacing.xs
  },
  groupLabel: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.7
  },
  chipWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  },
  causeList: {
    gap: theme.spacing.xs
  },
  causeItem: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  timeline: {
    position: "relative",
    gap: theme.spacing.md,
    paddingLeft: 6
  },
  timelineRail: {
    position: "absolute",
    left: 11,
    top: 0,
    bottom: 0,
    width: 2,
    backgroundColor: theme.colors.border
  },
  timelineRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: theme.spacing.md
  },
  timelineRowLast: {
    paddingBottom: 0
  },
  nodeWrap: {
    width: 24,
    alignItems: "center",
    paddingTop: 24
  },
  nodeOuter: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: "#FFD8BE",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: theme.colors.accent
  },
  nodeInner: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.accent
  },
  timelineCard: {
    flex: 1,
    backgroundColor: "#FCEEDC",
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: "#F0C9A5",
    padding: theme.spacing.md,
    gap: theme.spacing.xs,
    shadowColor: "#B77A4C",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.12,
    shadowRadius: 18,
    elevation: 3
  },
  timelineTime: {
    color: theme.colors.accent,
    fontSize: theme.typography.label,
    textTransform: "uppercase",
    letterSpacing: 0.6
  },
  timelineTitle: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: theme.typography.heading
  },
  timelineSummary: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  },
  timelineCause: {
    color: theme.colors.text,
    fontSize: theme.typography.label
  },
  body: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  }
});
