import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { StyleSheet, Text } from "react-native";

import { getTodaySessions } from "../../src/lib/api";
import { todayIsoDate } from "../../src/lib/date";
import { useSession } from "../../src/lib/session";
import { EmptyState } from "../../src/components/EmptyState";
import { EntryCard } from "../../src/components/EntryCard";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { theme } from "../../src/theme";

export default function EntriesScreen() {
  const router = useRouter();
  const { user } = useSession();
  const date = todayIsoDate();

  const query = useQuery({
    queryKey: ["today-sessions", user?.id, date],
    enabled: Boolean(user),
    queryFn: () => getTodaySessions(user!.id, date)
  });

  return (
    <ScreenContainer>
      <Text style={styles.title}>Today&apos;s entries</Text>
      <Text style={styles.subtitle}>Each clip keeps the moment compact: summary, feelings, mixed tension, body signal, and a next support suggestion.</Text>

      {!query.data?.length ? (
        <EmptyState
          title="No sessions captured yet"
          description="Use the simulator to add a few bracelet-style uploads and they will show up here as entry cards."
          actionLabel="Simulate session"
          onAction={() => router.push("/simulate")}
        />
      ) : (
        query.data.map((item) => (
          <EntryCard key={item.session.id} session={item.session} evaluation={item.evaluation} onPress={() => router.push(`/entry/${item.session.id}`)} />
        ))
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  subtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body,
    lineHeight: 22
  }
});
