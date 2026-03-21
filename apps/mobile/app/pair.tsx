import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { pairMockDevice } from "../src/lib/api";
import { useSession } from "../src/lib/session";
import { ScreenContainer } from "../src/components/ScreenContainer";
import { SectionCard } from "../src/components/SectionCard";
import { WarmButton } from "../src/components/WarmButton";
import { theme } from "../src/theme";

type PairState = "idle" | "searching" | "found" | "connecting" | "connected";

export default function PairScreen() {
  const router = useRouter();
  const { user, setDevice, device } = useSession();
  const [state, setState] = useState<PairState>(device ? "connected" : "idle");
  const [nickname, setNickname] = useState("Campus Loop");

  useEffect(() => {
    if (state !== "searching") {
      return;
    }
    const timer = setTimeout(() => {
      setState("found");
    }, 1700);
    return () => clearTimeout(timer);
  }, [state]);

  const mutation = useMutation({
    mutationFn: () => pairMockDevice(user!.id, nickname),
    onMutate: () => setState("connecting"),
    onSuccess: async (nextDevice) => {
      await setDevice(nextDevice);
      setState("connected");
      setTimeout(() => router.replace("/"), 700);
    }
  });

  if (!user) {
    return (
      <ScreenContainer>
        <SectionCard title="Onboarding required">
          <Text style={styles.body}>Create a user profile first so the paired bracelet knows who it belongs to.</Text>
          <WarmButton label="Go to welcome" onPress={() => router.replace("/welcome")} />
        </SectionCard>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.title}>Pair your bracelet</Text>
        <Text style={styles.subtitle}>This is a fake pairing flow for now, but it creates the same device record the hardware will use later.</Text>
      </View>

      <SectionCard title="Connection status">
        <View style={styles.scanWrap}>
          <View style={[styles.orb, state !== "idle" && styles.orbActive]} />
          <Text style={styles.statusText}>{copyForState(state, nickname)}</Text>
        </View>
        <Pressable style={styles.nicknameBox} onPress={() => setNickname((current) => (current === "Campus Loop" ? "Studio Ember" : "Campus Loop"))}>
          <Text style={styles.nicknameLabel}>Tap to rename demo device</Text>
          <Text style={styles.nicknameValue}>{nickname}</Text>
        </Pressable>
      </SectionCard>

      {state === "idle" ? <WarmButton label="Search for bracelet" onPress={() => setState("searching")} /> : null}
      {state === "found" ? <WarmButton label="Connect to bracelet" onPress={() => mutation.mutate()} loading={mutation.isPending} /> : null}
      {state === "connected" ? <WarmButton label="Continue to app" onPress={() => router.replace("/")} /> : null}
    </ScreenContainer>
  );
}

function copyForState(state: PairState, nickname: string) {
  switch (state) {
    case "searching":
      return "Searching for bracelet nearby...";
    case "found":
      return `Bracelet found: ${nickname}`;
    case "connecting":
      return `Connecting to ${nickname}...`;
    case "connected":
      return `Connected to ${nickname}`;
    default:
      return "Ready to start a mock scan.";
  }
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
    lineHeight: 22
  },
  scanWrap: {
    alignItems: "center",
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.md
  },
  orb: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: theme.colors.cardMuted,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  orbActive: {
    backgroundColor: "rgba(240,138,60,0.16)",
    borderColor: theme.colors.accentSoft
  },
  statusText: {
    color: theme.colors.text,
    fontSize: theme.typography.body
  },
  nicknameBox: {
    backgroundColor: theme.colors.cardMuted,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    gap: theme.spacing.xs
  },
  nicknameLabel: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label
  },
  nicknameValue: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: "600"
  },
  body: {
    color: theme.colors.textMuted,
    lineHeight: 22
  }
});
