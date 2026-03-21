import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { seedDemo } from "../../src/lib/api";
import { useSession } from "../../src/lib/session";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { WarmButton } from "../../src/components/WarmButton";
import { theme } from "../../src/theme";

export default function ProfileScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, device, applySeededDemo, clear } = useSession();

  const seedMutation = useMutation({
    mutationFn: seedDemo,
    onSuccess: async (payload) => {
      await applySeededDemo(payload.user, payload.device);
      await queryClient.invalidateQueries();
    }
  });

  return (
    <ScreenContainer>
      <Text style={styles.title}>Profile</Text>

      <SectionCard title="User context">
        {user ? (
          <>
            <Text style={styles.primary}>{user.name}</Text>
            <Text style={styles.body}>{user.schoolYear}</Text>
            <Text style={styles.body}>Goals: {user.goals.join(", ")}</Text>
            <Text style={styles.body}>Support style: {user.supportStyle}</Text>
            <Text style={styles.body}>Stressors: {user.topStressors.join(", ")}</Text>
          </>
        ) : (
          <Text style={styles.body}>No user profile saved on this device yet.</Text>
        )}
      </SectionCard>

      <SectionCard title="Bracelet link">
        {device ? (
          <>
            <Text style={styles.primary}>{device.nickname}</Text>
            <Text style={styles.body}>Firmware {device.firmwareVersion}</Text>
            <Text style={styles.body}>Status: {device.status}</Text>
          </>
        ) : (
          <Text style={styles.body}>No bracelet paired locally.</Text>
        )}
      </SectionCard>

      <SectionCard title="Demo controls">
        <View style={styles.actions}>
          <WarmButton label="Pair bracelet" onPress={() => router.push("/pair")} />
          <WarmButton label="Simulate session" onPress={() => router.push("/simulate")} variant="ghost" />
          <WarmButton label="Generate demo data" onPress={() => seedMutation.mutate()} loading={seedMutation.isPending} variant="ghost" />
          <WarmButton
            label="Clear local session"
            onPress={async () => {
              await clear();
              queryClient.clear();
              router.replace("/welcome");
            }}
            variant="ghost"
          />
        </View>
      </SectionCard>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  primary: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: "600"
  },
  body: {
    color: theme.colors.textMuted,
    lineHeight: 22
  },
  actions: {
    gap: theme.spacing.sm
  }
});
