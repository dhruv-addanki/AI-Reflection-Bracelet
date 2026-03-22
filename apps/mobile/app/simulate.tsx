import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { EmptyState } from "../src/components/EmptyState";
import { ScreenContainer } from "../src/components/ScreenContainer";
import { SectionCard } from "../src/components/SectionCard";
import { WarmButton } from "../src/components/WarmButton";
import { uploadSessionWithAudio } from "../src/lib/api";
import { todayIsoDate } from "../src/lib/date";
import { useSession } from "../src/lib/session";
import { theme } from "../src/theme";

const SYNC_DURATION_MS = 10_000;

type SyncStage = "idle" | "syncing" | "done";

export default function SyncNotesScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, device } = useSession();
  const [avgHr] = useState("93");
  const [peakHr] = useState("116");
  const [baselineDelta] = useState("14");
  const [tonePreset] = useState("overwhelmed");
  const [audioAsset, setAudioAsset] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [syncStage, setSyncStage] = useState<SyncStage>("idle");
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!audioAsset) {
        throw new Error("Choose a fallback audio file before syncing notes.");
      }

      const timestamp = new Date().toISOString();
      const formData = new FormData();
      formData.append("user_id", user!.id);
      formData.append("device_id", device!.id);
      formData.append("timestamp", timestamp);
      formData.append("source_type", "bracelet");
      formData.append("battery_status", "76");
      formData.append("hr_quality", "wifi-sync fallback");
      formData.append("tone_preset", tonePreset);
      appendOptionalNumber(formData, "avg_hr", avgHr);
      appendOptionalNumber(formData, "peak_hr", peakHr);
      appendOptionalNumber(formData, "baseline_delta", baselineDelta);
      formData.append(
        "audio_file",
        {
          uri: audioAsset.uri,
          name: audioAsset.name ?? "bracelet-note.wav",
          type: audioAsset.mimeType ?? "audio/wav"
        } as unknown as Blob
      );

      const [result] = await Promise.all([uploadSessionWithAudio(formData), waitForSyncAnimation()]);
      return result;
    },
    onMutate: () => {
      setSyncStage("syncing");
      setProgress(0.04);
    },
    onSuccess: async () => {
      stopProgressAnimation();
      setProgress(1);
      setSyncStage("done");
      await queryClient.invalidateQueries({ queryKey: ["today-sessions", user?.id, todayIsoDate()] });
      await queryClient.invalidateQueries({ queryKey: ["daily-summary", user?.id, todayIsoDate()] });
      await queryClient.invalidateQueries({ queryKey: ["reflection-history", user?.id] });
      await queryClient.invalidateQueries({ queryKey: ["weekly-patterns"] });
      await queryClient.invalidateQueries({ queryKey: ["weekly-pattern-history", user?.id] });
      setTimeout(() => router.replace("/"), 500);
    },
    onError: () => {
      stopProgressAnimation();
      setSyncStage("idle");
      setProgress(0);
    }
  });

  useEffect(() => {
    if (syncStage !== "syncing") {
      stopProgressAnimation();
      return;
    }

    const startedAt = Date.now();
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const next = Math.min(0.94, 0.04 + elapsed / SYNC_DURATION_MS);
      setProgress(next);
    }, 120);

    return stopProgressAnimation;
  }, [syncStage]);

  const syncSteps = useMemo(
    () => [
      { label: "Secure Wi-Fi handshake", threshold: 0.18 },
      { label: "Pulling bracelet note", threshold: 0.42 },
      { label: "Aligning voice and heart data", threshold: 0.7 },
      { label: "Building reflection outputs", threshold: 0.92 }
    ],
    []
  );

  if (!user || !device) {
    return (
      <ScreenContainer>
        <EmptyState
          title="Pair a bracelet first"
          description="A paired bracelet and user profile are required before notes can sync into the app."
          actionLabel="Go to pairing"
          onAction={() => router.replace("/pair")}
        />
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer>
      <WarmButton label="Back" onPress={() => router.back()} variant="ghost" style={styles.backButton} />

      {syncStage === "syncing" || syncStage === "done" ? (
        <View style={styles.syncWrap}>
          <View style={styles.syncOrb}>
            <View style={[styles.syncInner, syncStage === "done" && styles.syncInnerDone]} />
          </View>
          <Text style={styles.title}>{syncStage === "done" ? "Notes synced" : "Syncing bracelet notes"}</Text>
          <Text style={styles.subtitle}>
            {syncStage === "done"
              ? "Your bracelet note has been processed. Preparing your updated reflections now."
              : "Pulling the latest bracelet note, aligning fallback audio, and updating your reflections."}
          </Text>

          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${Math.round(progress * 100)}%` }]} />
          </View>
          <Text style={styles.progressText}>{Math.round(progress * 100)}%</Text>

          <View style={styles.stepList}>
            {syncSteps.map((step) => {
              const complete = progress >= step.threshold;
              return (
                <View key={step.label} style={styles.stepRow}>
                  <View style={[styles.stepDot, complete && styles.stepDotActive]} />
                  <Text style={[styles.stepLabel, complete && styles.stepLabelActive]}>{step.label}</Text>
                </View>
              );
            })}
          </View>
        </View>
      ) : (
        <>
          <View style={styles.hero}>
            <Text style={styles.title}>Sync notes</Text>
            <Text style={styles.subtitle}>Import the latest bracelet note and refresh today’s emotional timeline and reflections.</Text>
          </View>

          <SectionCard title="Fallback audio" subtitle="Upload an audio file only if the bracelet note needs a fallback source during sync.">
            <WarmButton
              label={audioAsset ? "Fallback audio attached" : "Choose fallback audio"}
              variant="ghost"
              onPress={async () => {
                const result = await DocumentPicker.getDocumentAsync({ type: "audio/*", copyToCacheDirectory: true });
                if (!result.canceled) {
                  setAudioAsset(result.assets[0] ?? null);
                }
              }}
            />
            <Text style={styles.meta}>Just for fallback. If attached, the uploaded audio will be used to complete the sync pipeline.</Text>
            {audioAsset ? (
              <View style={styles.fileBox}>
                <Text style={styles.fileName}>{audioAsset.name}</Text>
                <Text style={styles.fileMeta}>Ready to sync through bracelet Wi-Fi flow</Text>
              </View>
            ) : null}
          </SectionCard>

          <SectionCard title="Bracelet status">
            <View style={styles.statusRow}>
              <Text style={styles.statusLabel}>Device</Text>
              <Text style={styles.statusValue}>{device.nickname}</Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.statusLabel}>Connection</Text>
              <Text style={styles.statusValue}>Wi-Fi available</Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.statusLabel}>Battery</Text>
              <Text style={styles.statusValue}>76%</Text>
            </View>
          </SectionCard>

          <WarmButton label="Sync notes" onPress={() => mutation.mutate()} disabled={!audioAsset} loading={mutation.isPending} />
          {mutation.error ? <Text style={styles.error}>{mutation.error.message}</Text> : null}
        </>
      )}
    </ScreenContainer>
  );

  function stopProgressAnimation() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }
}

function parseNumber(value: string): number | undefined {
  const next = Number(value);
  return Number.isFinite(next) ? next : undefined;
}

function appendOptionalNumber(formData: FormData, key: string, value: string) {
  const parsed = parseNumber(value);
  if (parsed !== undefined) {
    formData.append(key, String(parsed));
  }
}

function waitForSyncAnimation() {
  return new Promise((resolve) => {
    setTimeout(resolve, SYNC_DURATION_MS);
  });
}

const styles = StyleSheet.create({
  backButton: {
    alignSelf: "flex-start"
  },
  hero: {
    gap: theme.spacing.xs
  },
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30,
    textAlign: "center"
  },
  subtitle: {
    color: theme.colors.textMuted,
    lineHeight: 22,
    textAlign: "center"
  },
  meta: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label,
    lineHeight: 18
  },
  fileBox: {
    backgroundColor: "#FCE9D5",
    borderWidth: 1,
    borderColor: "#F0C9A5",
    borderRadius: theme.radii.md,
    padding: theme.spacing.md,
    gap: theme.spacing.xs
  },
  fileName: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: "600"
  },
  fileMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label
  },
  statusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center"
  },
  statusLabel: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body
  },
  statusValue: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: "600"
  },
  syncWrap: {
    minHeight: 540,
    alignItems: "center",
    justifyContent: "center",
    gap: theme.spacing.md,
    paddingHorizontal: theme.spacing.md
  },
  syncOrb: {
    width: 124,
    height: 124,
    borderRadius: 62,
    backgroundColor: "#FCE9D5",
    borderWidth: 1,
    borderColor: "#F0C9A5",
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#C7844E",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.16,
    shadowRadius: 20,
    elevation: 4
  },
  syncInner: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: theme.colors.accent,
    opacity: 0.9
  },
  syncInnerDone: {
    backgroundColor: theme.colors.success
  },
  progressTrack: {
    width: "100%",
    height: 12,
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.cardMuted,
    overflow: "hidden",
    marginTop: theme.spacing.sm
  },
  progressFill: {
    height: "100%",
    borderRadius: theme.radii.pill,
    backgroundColor: theme.colors.accent
  },
  progressText: {
    color: theme.colors.text,
    fontSize: theme.typography.label
  },
  stepList: {
    width: "100%",
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.sm
  },
  stepDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.border
  },
  stepDotActive: {
    backgroundColor: theme.colors.accent
  },
  stepLabel: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.body
  },
  stepLabelActive: {
    color: theme.colors.text
  },
  error: {
    color: theme.colors.redMuted
  }
});
