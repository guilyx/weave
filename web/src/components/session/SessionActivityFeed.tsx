import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Loader2, ScrollText, Sparkles, StickyNote, Wand2 } from "lucide-react";
import { IconBox } from "../ui/IconBox";
import { useEffect, useRef, useState } from "react";
import { api, liveWebSocket, type ActivityItem } from "../../api";
import {
  ACTIVITY_FILTERS,
  activityKindLabel,
  filterActivity,
  formatActivityTime,
  isAiOutputKind,
  mergeActivityItems,
  type ActivityFilter,
} from "../../lib/sessionActivity";
import { Button } from "../ui/Button";
import { Card, CardTitle } from "../ui/Card";
import { Textarea } from "../ui/Input";

interface LiveWsEvent {
  type: string;
  kind?: string;
  message?: string;
  text?: string;
  recap?: string;
  items?: string[];
  ts?: string;
  activity_id?: string;
}

function AiOutputCard({ item }: { item: ActivityItem }) {
  const isMemory = item.kind === "memory";
  const isTips = item.kind === "suggestion";
  const isChronicle = item.kind === "chronicle" || item.kind === "recap";
  return (
    <article
      className={`rounded-xl border px-4 py-3.5 ${
        isMemory
          ? "border-moss/40 bg-moss/10"
          : isTips
            ? "border-gold/30 bg-gold/8"
            : isChronicle
              ? "border-gold/30 bg-gold/10"
              : "border-gold/25 bg-gold/5"
      }`}
    >
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gold">
        {isMemory ? (
          <Sparkles className="h-4 w-4" />
        ) : isTips ? (
          <Wand2 className="h-4 w-4" />
        ) : isChronicle ? (
          <ScrollText className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
        {activityKindLabel(item.kind)}
        <time className="ml-auto font-normal normal-case tabular-nums text-muted">
          {formatActivityTime(item.ts)}
        </time>
      </div>
      {item.body && (
        <p className="mt-2.5 whitespace-pre-wrap text-base leading-relaxed text-parchment/95">
          {item.body}
        </p>
      )}
    </article>
  );
}

function activityFromWs(data: LiveWsEvent): ActivityItem | null {
  if (data.type !== "activity" || !data.kind || !data.message) return null;
  if (!isAiOutputKind(data.kind)) return null;
  const id =
    data.activity_id ??
    `live-${data.ts ?? Date.now()}-${data.kind}-${(data.text ?? "").slice(0, 24)}`;
  return {
    id,
    kind: data.kind,
    ts: data.ts ?? new Date().toISOString(),
    title: data.message,
    body: data.text ?? null,
    meta: {},
  };
}

export function SessionActivityFeed({
  sessionId,
  isActive,
  onRecapUpdate,
  onSuggestions,
  className = "",
}: {
  sessionId: string;
  isActive: boolean;
  onRecapUpdate?: (recap: string) => void;
  onSuggestions?: (items: string[]) => void;
  className?: string;
}) {
  const qc = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<ActivityFilter>("ai");
  const [liveItems, setLiveItems] = useState<ActivityItem[]>([]);
  const [note, setNote] = useState("");

  const activity = useQuery({
    queryKey: ["activity", sessionId, filter],
    queryFn: () => api.getActivity(sessionId, filter === "ai" ? "ai" : filter),
    enabled: !!sessionId,
    refetchInterval: isActive && filter === "ai" ? 6000 : false,
  });

  useEffect(() => {
    if (activity.isSuccess) setLiveItems([]);
  }, [activity.dataUpdatedAt, activity.isSuccess]);

  const merged = mergeActivityItems([...(activity.data ?? []), ...liveItems]);
  const visible = filterActivity(merged, filter);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visible.length, filter]);

  useEffect(() => {
    if (!sessionId) return;
    const ws = liveWebSocket(sessionId);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as LiveWsEvent;
        if (data.type === "activity") {
          const item = activityFromWs(data);
          if (item) {
            setLiveItems((prev) => mergeActivityItems([...prev, item]));
          }
        }
        if (data.type === "recap_update" && data.recap) {
          onRecapUpdate?.(data.recap);
          void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
        }
        if (data.type === "suggestions" && data.items) {
          onSuggestions?.(data.items);
          void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [sessionId, onRecapUpdate, onSuggestions, qc]);

  const saveNote = useMutation({
    mutationFn: () => api.addNote(sessionId, note),
    onSuccess: () => {
      setNote("");
      void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
    },
  });

  return (
    <Card
      className={`flex h-full min-h-0 flex-col overflow-hidden p-0 shadow-none ${className}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-4">
        <div className="flex items-center gap-3">
          <IconBox icon={ScrollText} size="sm" />
          <CardTitle className="mb-0 text-xl">AI journal</CardTitle>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {ACTIVITY_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                filter === f.id
                  ? "bg-gold/20 text-gold"
                  : "text-muted hover:bg-white/5 hover:text-parchment"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="min-h-[200px] flex-1 space-y-3 overflow-y-auto bg-ink/30 px-4 py-3"
      >
        {activity.isLoading && (
          <div className="flex items-center justify-center gap-2 py-12 text-base text-muted">
            <Loader2 className="h-4 w-4 animate-spin text-gold" />
            Loading…
          </div>
        )}
        {!activity.isLoading && visible.length === 0 && (
          <p className="py-10 text-center text-base leading-relaxed text-muted">
            {filter === "ai"
              ? "Weave condenses mic + notes into memory beats, recaps, and tips — usually every ~25s after speech."
              : filter === "notes"
                ? "Quick notes appear here (also fed to the agent)."
                : "Raw audio/STT pipeline (debug only)."}
          </p>
        )}
        {filter === "ai"
          ? visible.map((item) => <AiOutputCard key={item.id} item={item} />)
          : visible.map((item) => (
              <article
                key={item.id}
                className="rounded-lg border border-border/60 bg-surface-raised/30 px-3 py-2 text-sm text-parchment/80"
              >
                <span className="text-gold">{activityKindLabel(item.kind)}</span>
                {item.body && <p className="mt-1 whitespace-pre-wrap">{item.body}</p>}
              </article>
            ))}
      </div>

      <div className="border-t border-border bg-surface-raised/40 p-3">
        <label className="mb-2 block text-sm font-medium text-muted">
          Quick note <span className="text-muted/70">(triggers condense, not shown in AI tab)</span>
        </label>
        <div className="flex gap-2">
          <Textarea
            className="min-h-[2.25rem] flex-1 py-1.5 text-sm"
            rows={1}
            placeholder="Loot, rulings, NPC names…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && note.trim()) {
                e.preventDefault();
                saveNote.mutate();
              }
            }}
          />
          <Button
            variant="secondary"
            className="shrink-0 self-end px-3"
            disabled={!note.trim() || saveNote.isPending}
            onClick={() => saveNote.mutate()}
          >
            <StickyNote className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
