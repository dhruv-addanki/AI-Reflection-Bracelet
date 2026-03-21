export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function startOfWeekIso(date = new Date()): string {
  const target = new Date(date);
  const day = target.getDay();
  const delta = day === 0 ? -6 : 1 - day;
  target.setDate(target.getDate() + delta);
  return target.toISOString().slice(0, 10);
}

export function formatClock(isoString: string): string {
  return new Date(isoString).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit"
  });
}

export function formatFriendlyDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString([], {
    month: "short",
    day: "numeric"
  });
}
