import { Dices, Loader2, ScrollText, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChronicleEntry } from "../../api";
import { formatActivityTime } from "../../lib/sessionActivity";
import { Card, CardTitle } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { IconBox } from "../ui/IconBox";

type ChapterView = "all" | number;

function chapterKey(entry: ChronicleEntry, index: number): number {
  return entry.chapter_index ?? index + 1;
}

/** One row per chapter_index (API should already enforce this). */
export function dedupeChronicleChapters(entries: ChronicleEntry[]): ChronicleEntry[] {
  const byChapter = new Map<number, ChronicleEntry>();
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i]!;
    const ch = chapterKey(entry, i);
    const existing = byChapter.get(ch);
    if (!existing) {
      byChapter.set(ch, entry);
      continue;
    }
    byChapter.set(ch, {
      ...existing,
      body: `${existing.body.trim()}\n\n${entry.body.trim()}`.trim(),
      stt_to: entry.stt_to ?? existing.stt_to,
    });
  }
  return [...byChapter.entries()]
    .sort(([a], [b]) => a - b)
    .map(([, e]) => e);
}

function ChapterNav({
  chapters,
  view,
  onView,
}: {
  chapters: ChronicleEntry[];
  view: ChapterView;
  onView: (v: ChapterView) => void;
}) {
  return (
    <nav
      className="flex max-h-28 shrink-0 flex-wrap gap-2 overflow-y-auto border-b border-border/60 pb-3"
      aria-label="Chronicle chapters"
    >
      <button
        type="button"
        onClick={() => onView("all")}
        className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
          view === "all"
            ? "border-gold/50 bg-gold/15 text-gold"
            : "border-border/60 bg-ink/40 text-muted hover:border-gold/30"
        }`}
      >
        Full scroll
      </button>
      {chapters.map((entry, index) => {
        const n = chapterKey(entry, index);
        const active = view === n;
        return (
          <button
            key={entry.id}
            type="button"
            onClick={() => onView(n)}
            title={
              entry.stt_from != null && entry.stt_to != null
                ? `Heard lines ${entry.stt_from}–${entry.stt_to}`
                : formatActivityTime(entry.created_at)
            }
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium tabular-nums transition ${
              active
                ? "border-gold/50 bg-gold/15 text-gold"
                : "border-border/60 bg-ink/40 text-muted hover:border-gold/30"
            }`}
          >
            Ch. {n}
          </button>
        );
      })}
    </nav>
  );
}

function ChronicleJournal({ entries }: { entries: ChronicleEntry[] }) {
  const [view, setView] = useState<ChapterView>("all");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (entries.length === 0) return;
    const last = entries[entries.length - 1]!;
    const lastN = chapterKey(last, entries.length - 1);
    setView((prev) => (prev === "all" ? prev : lastN));
  }, [entries]);

  useEffect(() => {
    if (view === "all") {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [entries.length, view]);

  const focused =
    view !== "all" ? entries.find((e, i) => chapterKey(e, i) === view) : null;
  const latestId = entries[entries.length - 1]?.id;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <ChapterNav chapters={entries} view={view} onView={setView} />

      {focused && view !== "all" ? (
        <article className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-gold/25 bg-ink/35 px-4 py-4">
          <ChapterHeader
            entry={focused}
            chapterNum={view}
            isLatest={focused.id === latestId}
          />
          <p className="prose-table mt-3 whitespace-pre-wrap text-parchment/95">{focused.body}</p>
        </article>
      ) : (
        <ol className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
          {entries.map((entry, index) => {
            const n = chapterKey(entry, index);
            return (
              <li
                key={entry.id}
                className="rounded-xl border border-border/70 bg-ink/35 px-4 py-3.5"
              >
                <ChapterHeader
                  entry={entry}
                  chapterNum={n}
                  isLatest={entry.id === latestId}
                />
                <p className="prose-table mt-2 whitespace-pre-wrap text-parchment/95">
                  {entry.body}
                </p>
              </li>
            );
          })}
          <div ref={endRef} aria-hidden className="h-1 shrink-0" />
        </ol>
      )}
    </div>
  );
}

function ChapterHeader({
  entry,
  chapterNum,
  isLatest,
}: {
  entry: ChronicleEntry;
  chapterNum: number;
  isLatest: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
      <span className="rounded bg-gold/12 px-2 py-0.5 font-display text-sm font-semibold text-gold">
        Chapter {chapterNum}
      </span>
      {entry.stt_from != null && entry.stt_to != null && (
        <span className="rounded bg-surface-raised/80 px-1.5 py-0.5 tabular-nums text-muted">
          STT {entry.stt_from}–{entry.stt_to}
        </span>
      )}
      <time className="font-medium tabular-nums text-gold/90">
        {formatActivityTime(entry.created_at)}
      </time>
      <span
        className="rounded bg-surface-raised/80 px-1.5 py-0.5 font-mono text-[10px] text-muted"
        title={entry.id}
      >
        #{entry.id.slice(0, 8)}
      </span>
      {isLatest && (
        <span className="rounded-full bg-gold/15 px-2 py-0.5 text-gold">Current</span>
      )}
    </div>
  );
}

/**
 * Recap view — additive AI journal (never raw STT).
 */
export function SessionTablePanel({
  entries,
  suggestions,
  isActive,
  agentPending,
  viewpointLabel,
  viewpointHint,
  tipsTitle = "Quest hooks & tips",
}: {
  sessionId?: string;
  entries: ChronicleEntry[];
  suggestions: string[];
  isActive: boolean;
  agentPending?: boolean;
  viewpointLabel: string;
  viewpointHint: string;
  tipsTitle?: string;
}) {
  const chapters = dedupeChronicleChapters(entries);
  const hasEntries = chapters.length > 0;
  const hasTips = suggestions.length > 0;

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-5">
      <Card className="flex min-h-0 flex-1 flex-col border-gold/20">
        <div className="flex items-start gap-4">
          <IconBox icon={ScrollText} size="md" />
          <div className="min-w-0 flex-1">
            <CardTitle className="flex flex-wrap items-center gap-2 text-2xl">
              {viewpointLabel}
              {agentPending && (
                <span className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-3 py-1 text-sm font-normal text-gold">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Scribing…
                </span>
              )}
              {isActive && !agentPending && hasEntries && (
                <span
                  className="live-pulse inline-flex h-2.5 w-2.5 rounded-full bg-gold"
                  title="Live session"
                />
              )}
            </CardTitle>
            <p className="mt-1 text-sm text-muted">{viewpointHint}</p>
            {hasEntries && (
              <p className="mt-1 text-xs text-muted/80">
                {chapters.length} {chapters.length === 1 ? "chapter" : "chapters"} — one per ~30
                heard lines, grows until the next chapter
              </p>
            )}
          </div>
        </div>

        <div className="ornament-divider" aria-hidden />

        {!hasEntries && (
          <EmptyState icon={Sparkles} title="The chronicle awaits">
            {isActive
              ? "Speak at the table with the mic on. Weave adds to the current chapter until ~30 transcript lines, then starts the next."
              : "Start the session and enable the mic. Chapters appear here as Weave processes the night."}
          </EmptyState>
        )}

        {hasEntries && <ChronicleJournal entries={chapters} />}
      </Card>

      {hasTips && (
        <Card className="shrink-0 border-gold/25">
          <div className="mb-4 flex items-center gap-3">
            <IconBox icon={Wand2} size="sm" />
            <CardTitle className="mb-0 text-lg">{tipsTitle}</CardTitle>
          </div>
          <ol className="space-y-3">
            {suggestions.map((s, i) => (
              <li
                key={i}
                className="flex gap-4 rounded-xl border border-gold/25 bg-gradient-to-r from-gold/8 to-transparent px-4 py-3.5"
              >
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gold/40 bg-gold/15 font-display text-lg font-bold text-gold"
                  aria-hidden
                >
                  {i + 1}
                </span>
                <p className="pt-1 text-base leading-relaxed text-parchment/95">{s}</p>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {!hasEntries && !hasTips && !agentPending && (
        <p className="flex items-center justify-center gap-2 text-center text-sm text-muted">
          <Dices className="h-4 w-4 text-gold/60" aria-hidden />
          Journal entries are AI-written only
        </p>
      )}
    </div>
  );
}
