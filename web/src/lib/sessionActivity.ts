import type { ActivityItem } from "../api";

export type ActivityFilter = "ai" | "notes" | "pipeline";

/** Default log: condensed AI outputs only. */
export const AI_OUTPUT_KINDS = new Set([
  "recap",
  "chronicle",
  "suggestion",
  "memory",
  "chat_assistant",
]);

export const ACTIVITY_FILTERS: { id: ActivityFilter; label: string }[] = [
  { id: "ai", label: "AI" },
  { id: "notes", label: "Notes" },
  { id: "pipeline", label: "Debug" },
];

const NOTE_KINDS = new Set(["note"]);
const PIPELINE_KINDS = new Set([
  "audio_chunk",
  "transcript",
  "agent_queued",
  "agent_done",
  "system",
  "chat_user",
]);

export function filterActivity(items: ActivityItem[], filter: ActivityFilter): ActivityItem[] {
  if (filter === "ai") return items.filter((i) => AI_OUTPUT_KINDS.has(i.kind));
  if (filter === "notes") return items.filter((i) => NOTE_KINDS.has(i.kind));
  if (filter === "pipeline") return items.filter((i) => PIPELINE_KINDS.has(i.kind));
  return items;
}

export function isAiOutputKind(kind: string): boolean {
  return AI_OUTPUT_KINDS.has(kind);
}

export function formatActivityTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

export function mergeActivityItems(items: ActivityItem[]): ActivityItem[] {
  const byId = new Map<string, ActivityItem>();
  for (const item of items) {
    byId.set(item.id, item);
  }
  return [...byId.values()].sort((a, b) => a.ts.localeCompare(b.ts));
}

export function activityKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    audio_chunk: "Audio",
    transcript: "STT",
    note: "Note",
    memory: "Memory",
    recap: "Recap",
    chronicle: "Chronicle",
    suggestion: "Tips",
    agent_queued: "Queued",
    agent_done: "Done",
    chat_user: "You",
    chat_assistant: "Weave",
    system: "System",
  };
  return labels[kind] ?? kind;
}
