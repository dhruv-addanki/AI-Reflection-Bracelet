import type {
  ClipEvaluation,
  DailySummary,
  Device,
  RawSession,
  SessionDetail,
  SimulationPayload,
  TimelineBlock,
  UserProfile,
  WeeklyPatternSummary
} from "@bracelet/shared-types";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type ApiEnvelope<T> = {
  ok: boolean;
  data: T;
};

type SessionRecord = {
  session: Record<string, unknown>;
  evaluation?: Record<string, unknown> | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  const payload = (await response.json()) as ApiEnvelope<T> | { detail?: string };
  if (!response.ok || !("data" in payload)) {
    throw new Error(extractErrorDetail(payload));
  }
  return payload.data;
}

async function requestMultipart<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body
  });
  const payload = (await response.json()) as ApiEnvelope<T> | { detail?: string };
  if (!response.ok || !("data" in payload)) {
    throw new Error(extractErrorDetail(payload));
  }
  return payload.data;
}

function extractErrorDetail<T>(payload: ApiEnvelope<T> | { detail?: string }) {
  return "detail" in payload ? payload.detail ?? "Request failed" : "Request failed";
}

function mapUser(raw: Record<string, unknown>): UserProfile {
  return {
    id: String(raw.id),
    name: String(raw.name),
    schoolYear: String(raw.school_year),
    goals: (raw.goals as UserProfile["goals"]) ?? [],
    supportStyle: String(raw.support_style) as UserProfile["supportStyle"],
    topStressors: (raw.top_stressors as string[]) ?? [],
    createdAt: String(raw.created_at)
  };
}

function mapDevice(raw: Record<string, unknown>): Device {
  return {
    id: String(raw.id),
    userId: String(raw.user_id),
    nickname: String(raw.nickname),
    firmwareVersion: String(raw.firmware_version),
    linkedAt: String(raw.linked_at),
    status: String(raw.status) as Device["status"]
  };
}

function mapRawSession(raw: Record<string, unknown>): RawSession {
  return {
    id: String(raw.id),
    userId: String(raw.user_id),
    deviceId: String(raw.device_id),
    startedAt: String(raw.started_at),
    endedAt: String(raw.ended_at),
    audioUrl: raw.audio_url ? String(raw.audio_url) : null,
    transcriptOverride: raw.transcript_override ? String(raw.transcript_override) : null,
    avgHr: typeof raw.avg_hr === "number" ? raw.avg_hr : null,
    peakHr: typeof raw.peak_hr === "number" ? raw.peak_hr : null,
    baselineDelta: typeof raw.baseline_delta === "number" ? raw.baseline_delta : null,
    hrQuality: raw.hr_quality ? String(raw.hr_quality) : null,
    batteryStatus: typeof raw.battery_status === "number" ? raw.battery_status : null,
    uploadStatus: String(raw.upload_status) as RawSession["uploadStatus"],
    sourceType: String(raw.source_type) as RawSession["sourceType"]
  };
}

function mapClipEvaluation(raw?: Record<string, unknown> | null): ClipEvaluation | null {
  if (!raw) {
    return null;
  }
  return {
    id: String(raw.id),
    sessionId: String(raw.session_id),
    transcript: String(raw.transcript),
    toneLabels: (raw.tone_labels as string[]) ?? [],
    toneScores: (raw.tone_scores as { label: string; score: number }[]) ?? [],
    heartSummary: String(raw.heart_summary),
    triggerTags: (raw.trigger_tags as string[]) ?? [],
    mixedFeelings: (raw.mixed_feelings as string[]) ?? [],
    distressIntensity: Number(raw.distress_intensity ?? 1),
    oneLineSummary: String(raw.one_line_summary),
    supportSuggestion: String(raw.support_suggestion),
    primaryFeelings: (raw.primary_feelings as string[]) ?? [],
    selfTalkMarkers: (raw.self_talk_markers as string[]) ?? [],
    rawModelOutputsJson: (raw.raw_model_outputs_json as Record<string, unknown>) ?? {}
  };
}

function mapTimelineBlock(raw: Record<string, unknown>): TimelineBlock {
  return {
    label: String(raw.label),
    timeRange: String(raw.time_range),
    feeling: String(raw.feeling),
    intensity: Number(raw.intensity)
  };
}

function mapDailySummary(raw: Record<string, unknown> | null): DailySummary | null {
  if (!raw) {
    return null;
  }
  return {
    id: String(raw.id),
    userId: String(raw.user_id),
    date: String(raw.date),
    emotionalRecap: String(raw.emotional_recap),
    emotionDrivers: (raw.emotion_drivers as string[]) ?? [],
    hardestMoment: String(raw.hardest_moment),
    calmestMoment: String(raw.calmest_moment),
    repeatedFeeling: String(raw.repeated_feeling),
    oneThingToNotice: String(raw.one_thing_to_notice),
    moodTimeline: ((raw.mood_timeline_json as Record<string, unknown>[]) ?? []).map(mapTimelineBlock),
    recapParagraph: String(raw.recap_paragraph),
    reflectionPrompt: String(raw.reflection_prompt),
    reflectionResponse: raw.reflection_response ? String(raw.reflection_response) : null,
    mixedFeelingInsight: String(raw.mixed_feeling_insight ?? "")
  };
}

function mapWeeklySummary(raw: Record<string, unknown> | null): WeeklyPatternSummary | null {
  if (!raw) {
    return null;
  }
  return {
    id: String(raw.id),
    userId: String(raw.user_id),
    weekStart: String(raw.week_start),
    topTriggers: (raw.top_triggers as string[]) ?? [],
    hardestTimeWindows: (raw.hardest_time_windows as string[]) ?? [],
    repeatedSelfTalkPatterns: (raw.repeated_self_talk_patterns as string[]) ?? [],
    supportStrategiesThatHelp: (raw.support_strategies_that_help as string[]) ?? [],
    weeklyReflection: String(raw.weekly_reflection)
  };
}

export async function createUser(input: {
  name: string;
  schoolYear: string;
  goals: string[];
  supportStyle: string;
  topStressors: string[];
}): Promise<UserProfile> {
  const raw = await request<Record<string, unknown>>("/auth/onboarding", {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      school_year: input.schoolYear,
      goals: input.goals,
      support_style: input.supportStyle,
      top_stressors: input.topStressors
    })
  });
  return mapUser(raw);
}

export async function fetchProfile(userId: string): Promise<UserProfile> {
  const raw = await request<Record<string, unknown>>(`/auth/profile/${userId}`);
  return mapUser(raw);
}

export async function pairMockDevice(userId: string, nickname?: string): Promise<Device> {
  const raw = await request<Record<string, unknown>>("/devices/pair-mock", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      nickname
    })
  });
  return mapDevice(raw);
}

export async function listDevices(userId: string): Promise<Device[]> {
  const raw = await request<Record<string, unknown>[]>(`/devices?user_id=${userId}`);
  return raw.map(mapDevice);
}

export async function getTodaySessions(userId: string, date: string): Promise<{ session: RawSession; evaluation: ClipEvaluation | null }[]> {
  const raw = await request<SessionRecord[]>(`/sessions/today?user_id=${userId}&date=${date}`);
  return raw.map((item) => ({
    session: mapRawSession(item.session),
    evaluation: mapClipEvaluation(item.evaluation)
  }));
}

export async function getSession(id: string): Promise<SessionDetail> {
  const raw = await request<{ session: Record<string, unknown>; evaluation?: Record<string, unknown> | null }>(`/sessions/${id}`);
  return {
    session: mapRawSession(raw.session),
    evaluation: mapClipEvaluation(raw.evaluation)
  };
}

export async function getDailySummary(userId: string, date: string): Promise<DailySummary | null> {
  const raw = await request<Record<string, unknown> | null>(`/summaries/daily?user_id=${userId}&date=${date}`);
  return mapDailySummary(raw);
}

export async function getReflectionHistory(userId: string): Promise<DailySummary[]> {
  const raw = await request<Record<string, unknown>[]>(`/summaries/history?user_id=${userId}`);
  return raw.map((item) => mapDailySummary(item)).filter((item): item is DailySummary => Boolean(item));
}

export async function saveDailyReflection(userId: string, date: string, response: string): Promise<DailySummary> {
  const raw = await request<Record<string, unknown>>("/summaries/reflection", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      date,
      response
    })
  });
  return mapDailySummary(raw)!;
}

export async function getWeeklyPatterns(userId: string, weekStart: string): Promise<WeeklyPatternSummary | null> {
  const raw = await request<Record<string, unknown> | null>(`/patterns/weekly?user_id=${userId}&week_start=${weekStart}`);
  return mapWeeklySummary(raw);
}

export async function getWeeklyPatternHistory(userId: string): Promise<WeeklyPatternSummary[]> {
  const raw = await request<Record<string, unknown>[]>(`/patterns/history?user_id=${userId}`);
  return raw.map((item) => mapWeeklySummary(item)).filter((item): item is WeeklyPatternSummary => Boolean(item));
}

export async function simulateSession(payload: SimulationPayload): Promise<{ session: RawSession; evaluation: ClipEvaluation | null }> {
  const raw = await request<SessionRecord>("/simulate/session", {
    method: "POST",
    body: JSON.stringify({
      user_id: payload.userId,
      device_id: payload.deviceId,
      timestamp: payload.timestamp,
      transcript_override: payload.transcriptOverride,
      tone_preset: payload.tonePreset,
      tone_labels: payload.toneLabels,
      avg_hr: payload.avgHr,
      peak_hr: payload.peakHr,
      baseline_delta: payload.baselineDelta,
      battery_status: payload.batteryStatus,
      audio_file_url: payload.audioFileUrl
    })
  });
  return {
    session: mapRawSession(raw.session),
    evaluation: mapClipEvaluation(raw.evaluation)
  };
}

export async function uploadSessionWithAudio(formData: FormData): Promise<{ session: RawSession; evaluation: ClipEvaluation | null }> {
  const raw = await requestMultipart<SessionRecord>("/sessions/upload", formData);
  return {
    session: mapRawSession(raw.session),
    evaluation: mapClipEvaluation(raw.evaluation)
  };
}

export async function seedDemo(): Promise<{ user: UserProfile; device: Device; dailySummary: DailySummary | null; weeklySummary: WeeklyPatternSummary | null }> {
  const raw = await request<{
    user: Record<string, unknown>;
    device: Record<string, unknown>;
    daily_summary: Record<string, unknown> | null;
    weekly_summary: Record<string, unknown> | null;
  }>("/seed/demo", {
    method: "POST",
    body: JSON.stringify({ reset: true })
  });
  return {
    user: mapUser(raw.user),
    device: mapDevice(raw.device),
    dailySummary: mapDailySummary(raw.daily_summary),
    weeklySummary: mapWeeklySummary(raw.weekly_summary)
  };
}
