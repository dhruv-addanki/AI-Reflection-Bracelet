import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { createUser } from "../../src/lib/api";
import { useSession } from "../../src/lib/session";
import { ScreenContainer } from "../../src/components/ScreenContainer";
import { SectionCard } from "../../src/components/SectionCard";
import { WarmButton } from "../../src/components/WarmButton";
import { theme } from "../../src/theme";

const GOALS = [
  "reduce stress",
  "understand feelings better",
  "vent more safely",
  "stop spiraling",
  "reflect consistently"
] as const;

const SUPPORT_STYLES = ["gentle friend", "calm coach", "reflective guide"] as const;

export default function OnboardingScreen() {
  const router = useRouter();
  const { setUser } = useSession();
  const [name, setName] = useState("");
  const [schoolYear, setSchoolYear] = useState("Junior");
  const [goals, setGoals] = useState<string[]>(["reduce stress", "reflect consistently"]);
  const [supportStyle, setSupportStyle] = useState("calm coach");
  const [stressors, setStressors] = useState("deadlines, exams, feeling behind");

  const ready = name.trim().length > 1 && stressors.trim().length > 0;

  const mutation = useMutation({
    mutationFn: () =>
      createUser({
        name: name.trim(),
        schoolYear,
        goals,
        supportStyle,
        topStressors: stressors.split(",").map((item) => item.trim()).filter(Boolean)
      }),
    onSuccess: async (user) => {
      await setUser(user);
      router.replace("/pair");
    }
  });

  function toggleGoal(goal: string) {
    setGoals((current) => (current.includes(goal) ? current.filter((item) => item !== goal) : [...current, goal]));
  }

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.title}>Set the reflection tone.</Text>
        <Text style={styles.subtitle}>A little context makes the recap feel more like yours.</Text>
      </View>

      <SectionCard title="Basic profile">
        <TextInput value={name} onChangeText={setName} placeholder="Name" placeholderTextColor={theme.colors.textMuted} style={styles.input} />
        <TextInput
          value={schoolYear}
          onChangeText={setSchoolYear}
          placeholder="School year"
          placeholderTextColor={theme.colors.textMuted}
          style={styles.input}
        />
      </SectionCard>

      <SectionCard title="Goals">
        <View style={styles.wrap}>
          {GOALS.map((goal) => (
            <OptionChip key={goal} label={goal} selected={goals.includes(goal)} onPress={() => toggleGoal(goal)} />
          ))}
        </View>
      </SectionCard>

      <SectionCard title="Support style">
        <View style={styles.wrap}>
          {SUPPORT_STYLES.map((style) => (
            <OptionChip key={style} label={style} selected={supportStyle === style} onPress={() => setSupportStyle(style)} />
          ))}
        </View>
      </SectionCard>

      <SectionCard title="Top stressors" subtitle="Comma-separated is enough for the demo.">
        <TextInput
          value={stressors}
          onChangeText={setStressors}
          placeholder="deadlines, roommate tension, internships"
          placeholderTextColor={theme.colors.textMuted}
          style={[styles.input, styles.inputMultiline]}
          multiline
        />
      </SectionCard>

      {mutation.error ? <Text style={styles.error}>{mutation.error.message}</Text> : null}
      <WarmButton label="Continue to pairing" onPress={() => mutation.mutate()} loading={mutation.isPending} disabled={!ready} />
    </ScreenContainer>
  );
}

function OptionChip({
  label,
  selected,
  onPress
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={[styles.chip, selected && styles.chipSelected]}>
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
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
    lineHeight: 21
  },
  input: {
    backgroundColor: theme.colors.cardMuted,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    color: theme.colors.text,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 14
  },
  inputMultiline: {
    minHeight: 110,
    textAlignVertical: "top"
  },
  wrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: theme.spacing.sm
  },
  chip: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 10,
    borderRadius: theme.radii.pill,
    borderWidth: 1,
    borderColor: theme.colors.border,
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
  error: {
    color: theme.colors.redMuted
  }
});
