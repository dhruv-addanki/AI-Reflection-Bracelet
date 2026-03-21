export type GoalOption =
  | "reduce stress"
  | "understand feelings better"
  | "vent more safely"
  | "stop spiraling"
  | "reflect consistently";

export type SupportStyle = "gentle friend" | "calm coach" | "reflective guide";

export type TonePreset =
  | "overwhelmed"
  | "calm but tired"
  | "frustrated"
  | "emotionally released"
  | "anxious";

export type SourceType = "mock" | "bracelet";

export type DeviceStatus = "connected" | "idle" | "needs-charge";

export type UploadStatus = "pending" | "processed" | "failed";

export interface UserProfile {
  id: string;
  name: string;
  schoolYear: string;
  goals: GoalOption[];
  supportStyle: SupportStyle;
  topStressors: string[];
  createdAt: string;
}

export interface Device {
  id: string;
  userId: string;
  nickname: string;
  firmwareVersion: string;
  linkedAt: string;
  status: DeviceStatus;
}

export interface RawSession {
  id: string;
  userId: string;
  deviceId: string;
  startedAt: string;
  endedAt: string;
  audioUrl?: string | null;
  transcriptOverride?: string | null;
  avgHr?: number | null;
  peakHr?: number | null;
  baselineDelta?: number | null;
  hrQuality?: string | null;
  batteryStatus?: number | null;
  uploadStatus: UploadStatus;
  sourceType: SourceType;
}

export interface ToneLabelScore {
  label: string;
  score: number;
}

export interface ClipEvaluation {
  id: string;
  sessionId: string;
  transcript: string;
  toneLabels: string[];
  toneScores: ToneLabelScore[];
  heartSummary: string;
  triggerTags: string[];
  mixedFeelings: string[];
  distressIntensity: number;
  oneLineSummary: string;
  supportSuggestion: string;
  primaryFeelings: string[];
  selfTalkMarkers: string[];
  rawModelOutputsJson: Record<string, unknown>;
}

export interface TimelineBlock {
  label: string;
  timeRange: string;
  feeling: string;
  intensity: number;
}

export interface DailySummary {
  id: string;
  userId: string;
  date: string;
  emotionalRecap: string;
  hardestMoment: string;
  calmestMoment: string;
  repeatedFeeling: string;
  oneThingToNotice: string;
  moodTimeline: TimelineBlock[];
  recapParagraph: string;
  reflectionPrompt: string;
  mixedFeelingInsight: string;
}

export interface WeeklyPatternSummary {
  id: string;
  userId: string;
  weekStart: string;
  topTriggers: string[];
  hardestTimeWindows: string[];
  repeatedSelfTalkPatterns: string[];
  supportStrategiesThatHelp: string[];
  weeklyReflection: string;
}

export interface SessionDetail {
  session: RawSession;
  evaluation?: ClipEvaluation | null;
}

export interface SimulationPayload {
  userId: string;
  deviceId?: string;
  timestamp?: string;
  transcriptOverride?: string;
  tonePreset?: TonePreset;
  toneLabels?: string[];
  avgHr?: number;
  peakHr?: number;
  baselineDelta?: number;
  batteryStatus?: number;
  audioFileUrl?: string;
}
