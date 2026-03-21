import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { simulateSession, uploadSessionWithAudio } from "../src/lib/api";
import { todayIsoDate } from "../src/lib/date";
import { useSession } from "../src/lib/session";
import { EmptyState } from "../src/components/EmptyState";
import { ScreenContainer } from "../src/components/ScreenContainer";
import { SectionCard } from "../src/components/SectionCard";
import { WarmButton } from "../src/components/WarmButton";
import { theme } from "../src/theme";

const TONES = ["overwhelmed", "calm but tired", "frustrated", "emotionally released", "anxious"] as const;

export default function SimulateScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, device } = useSession();
  const [transcript, setTranscript] = useState("I keep feeling behind and I needed to say it out loud before it snowballed again.");
  const [avgHr, setAvgHr] = useState("93");
  const [peakHr, setPeakHr] = useState("116");
  const [baselineDelta, setBaselineDelta] = useState("14");
  const [tonePreset, setTonePreset] = useState<typeof TONES[number]>("overwhelmed");
  const [audioAsset, setAudioAsset] = useState<DocumentPicker.DocumentPickerAsset | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const timestamp = new Date().toISOString();
      if (audioAsset) {
        const formData = new FormData();
        formData.append("user_id", user!.id);
        formData.append("device_id", device!.id);
        formData.append("timestamp", timestamp);
        formData.append("source_type", "mock");
        formData.append("battery_status", "76");
        formData.append("hr_quality", "simulated");
        formData.append("tone_preset", tonePreset);
        appendOptionalNumber(formData, "avg_hr", avgHr);
        appendOptionalNumber(formData, "peak_hr", peakHr);
        appendOptionalNumber(formData, "baseline_delta", baselineDelta);
        formData.append(
          "audio_file",
          {
            uri: audioAsset.uri,
            name: audioAsset.name ?? "session-audio.wav",
            type: audioAsset.mimeType ?? "audio/wav"
          } as unknown as Blob
        );
        return uploadSessionWithAudio(formData);
      }

      return simulateSession({
        userId: user!.id,
        deviceId: device!.id,
        timestamp,
        transcriptOverride: transcript || undefined,
        tonePreset,
        avgHr: parseNumber(avgHr),
        peakHr: parseNumber(peakHr),
        baselineDelta: parseNumber(baselineDelta),
        batteryStatus: 76
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["today-sessions", user?.id, todayIsoDate()] });
      await queryClient.invalidateQueries({ queryKey: ["daily-summary", user?.id, todayIsoDate()] });
      await queryClient.invalidateQueries({ queryKey: ["weekly-patterns"] });
      router.replace("/");
    }
  });

  if (!user || !device) {
    return (
      <ScreenContainer>
        <EmptyState
          title="Pair a bracelet first"
          description="The simulator sends bracelet-shaped payloads, so it needs a user and a paired device before it can create sessions."
          actionLabel="Go to pairing"
          onAction={() => router.replace("/pair")}
        />
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer>
      <Text style={styles.title}>Simulate bracelet session</Text>
      <Text style={styles.subtitle}>This feeds the same backend pipeline the real hardware upload path will use later.</Text>

      <SectionCard title="Transcript or local audio">
        <TextInput
          value={transcript}
          onChangeText={setTranscript}
          placeholder="Type what the student might say"
          placeholderTextColor={theme.colors.textMuted}
          multiline
          style={[styles.input, styles.multiline]}
        />
        <WarmButton
          label={audioAsset ? "Picked local audio" : "Select local audio file"}
          variant="ghost"
          onPress={async () => {
            const result = await DocumentPicker.getDocumentAsync({ type: "audio/*", copyToCacheDirectory: true });
            if (!result.canceled) {
              setAudioAsset(result.assets[0] ?? null);
            }
          }}
        />
        {audioAsset ? (
          <>
            <Text style={styles.meta}>Attached audio: {audioAsset.name}</Text>
            <Text style={styles.meta}>Attached audio will be transcribed and used instead of typed text.</Text>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Tone preset">
        <View style={styles.wrap}>
          {TONES.map((tone) => (
            <Pressable key={tone} style={[styles.chip, tonePreset === tone && styles.chipSelected]} onPress={() => setTonePreset(tone)}>
              <Text style={[styles.chipText, tonePreset === tone && styles.chipTextSelected]}>{tone}</Text>
            </Pressable>
          ))}
        </View>
      </SectionCard>

      <SectionCard title="Mock heart context">
        <TextInput value={avgHr} onChangeText={setAvgHr} keyboardType="numeric" style={styles.input} placeholder="Average HR" placeholderTextColor={theme.colors.textMuted} />
        <TextInput value={peakHr} onChangeText={setPeakHr} keyboardType="numeric" style={styles.input} placeholder="Peak HR" placeholderTextColor={theme.colors.textMuted} />
        <TextInput
          value={baselineDelta}
          onChangeText={setBaselineDelta}
          keyboardType="numeric"
          style={styles.input}
          placeholder="Baseline delta"
          placeholderTextColor={theme.colors.textMuted}
        />
      </SectionCard>

      <WarmButton label="Send mock upload" onPress={() => mutation.mutate()} loading={mutation.isPending} />
      {mutation.error ? <Text style={styles.error}>{mutation.error.message}</Text> : null}
    </ScreenContainer>
  );
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

const styles = StyleSheet.create({
  title: {
    color: theme.colors.text,
    fontFamily: theme.typefaces.heading,
    fontSize: 30
  },
  subtitle: {
    color: theme.colors.textMuted,
    lineHeight: 22
  },
  input: {
    backgroundColor: theme.colors.cardMuted,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    color: theme.colors.text,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 14
  },
  multiline: {
    minHeight: 140,
    textAlignVertical: "top"
  },
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  },
  chip: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.pill,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 10,
    backgroundColor: theme.colors.cardMuted
  },
  chipSelected: {
    backgroundColor: "rgba(240,138,60,0.14)",
    borderColor: theme.colors.accentSoft
  },
  chipText: {
    color: theme.colors.textMuted
  },
  chipTextSelected: {
    color: theme.colors.text
  },
  meta: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.label
  },
  error: {
    color: theme.colors.redMuted
  }
});
