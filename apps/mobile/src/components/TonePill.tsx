import { TagChip } from "./TagChip";

export function TonePill({ label }: { label: string }) {
  const tone = label.includes("over") || label.includes("anx") || label.includes("frustr") ? "red" : "warm";
  return <TagChip label={label} tone={tone} />;
}
