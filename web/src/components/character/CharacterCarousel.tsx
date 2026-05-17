import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type CharacterSnapshot, type DdbRosterEntry } from "../../api";
import { initials, rosterPortraitSrc } from "../../lib/character";
import { CharacterPortrait } from "./CharacterPortrait";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { CharacterSheetPanel } from "./CharacterSheetPanel";

export function CharacterCarousel({
  entries,
  primaryId,
  onSelectPrimary,
}: {
  entries: DdbRosterEntry[];
  primaryId: number | null;
  onSelectPrimary: (ddbCharacterId: number) => void;
}) {
  const [index, setIndex] = useState(0);

  const ids = entries.map((e) => e.ddb_character_id);

  const sheetsQuery = useQuery({
    queryKey: ["ddb-sheets", ids.join(",")],
    queryFn: () => api.fetchDdbCharacterSheets(ids),
    enabled: ids.length > 0,
    staleTime: 60_000,
  });

  const sheetById = new Map<number, CharacterSnapshot>();
  for (const sheet of sheetsQuery.data ?? []) {
    if (sheet.ddb_character_id != null) {
      sheetById.set(sheet.ddb_character_id, sheet);
    }
  }

  useEffect(() => {
    if (index >= entries.length) setIndex(0);
  }, [entries.length, index]);

  if (entries.length === 0) return null;

  const current = entries[index];
  const isPrimary = primaryId === current.ddb_character_id;
  const currentSheet = sheetById.get(current.ddb_character_id);
  const loadingSheet = sheetsQuery.isLoading || sheetsQuery.isFetching;

  const prev = () => setIndex((i) => (i - 1 + entries.length) % entries.length);
  const next = () => setIndex((i) => (i + 1) % entries.length);

  return (
    <div className="relative">
      <p className="mb-4 text-center text-sm text-muted">
        Swipe through your party, review each sheet, and choose{" "}
        <strong className="text-gold">your character</strong>.
      </p>

      <div className="flex items-stretch gap-2">
        <button
          type="button"
          onClick={prev}
          className="flex h-10 w-10 shrink-0 self-center items-center justify-center rounded-full border border-border bg-surface-raised text-gold transition hover:border-gold/50"
          aria-label="Previous character"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <div className="min-h-[320px] flex-1 overflow-hidden rounded-2xl border border-border bg-surface-raised shadow-inner">
          {loadingSheet && !currentSheet ? (
            <div className="flex h-full min-h-[320px] flex-col items-center justify-center gap-2 text-muted">
              <Loader2 className="h-8 w-8 animate-spin text-gold" />
              Loading {current.name}&apos;s sheet…
            </div>
          ) : currentSheet ? (
            <CharacterSheetPanel
              snapshot={currentSheet}
              ddbCharacterId={current.ddb_character_id}
              isPrimary={isPrimary}
              variant="embed"
            />
          ) : rosterPortraitSrc(current.ddb_character_id, current.avatar_url) ? (
            <div className="flex h-full min-h-[280px] flex-col items-center justify-center px-6">
              <CharacterPortrait
                snapshot={{ name: current.name, race: "", class_summary: "", avatar_url: current.avatar_url ?? undefined }}
                ddbCharacterId={current.ddb_character_id}
                size="lg"
              />
              <h3 className="mt-4 font-display text-2xl font-semibold text-parchment">
                {current.name}
              </h3>
              {current.class_summary && (
                <p className="mt-1 text-muted">
                  {current.class_summary}
                  {current.level != null ? ` · Level ${current.level}` : ""}
                </p>
              )}
              <p className="mt-3 text-sm text-muted">Loading full sheet…</p>
            </div>
          ) : (
            <div className="flex h-full min-h-[280px] flex-col items-center justify-center px-6 text-center">
              <div
                className={`flex h-20 w-20 items-center justify-center rounded-2xl border-2 font-display text-2xl font-bold ${
                  isPrimary
                    ? "border-gold bg-gold/20 text-gold"
                    : "border-border bg-ink text-parchment"
                }`}
              >
                {initials(current.name)}
              </div>
              <h3 className="mt-4 font-display text-2xl font-semibold text-parchment">
                {current.name}
              </h3>
              {current.class_summary && (
                <p className="mt-1 text-muted">
                  {current.class_summary}
                  {current.level != null ? ` · Level ${current.level}` : ""}
                </p>
              )}
              <p className="mt-3 text-sm text-red-300">
                Could not load full sheet — you can still import this character.
              </p>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={next}
          className="flex h-10 w-10 shrink-0 self-center items-center justify-center rounded-full border border-border bg-surface-raised text-gold transition hover:border-gold/50"
          aria-label="Next character"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      <div className="mt-4 flex justify-center gap-1.5">
        {entries.map((e, i) => (
          <button
            key={e.ddb_character_id}
            type="button"
            onClick={() => setIndex(i)}
            className={`h-2 rounded-full transition-all ${
              i === index
                ? "w-6 bg-gold"
                : primaryId === e.ddb_character_id
                  ? "w-2 bg-gold/50"
                  : "w-2 bg-border"
            }`}
            aria-label={`Show ${e.name}`}
          />
        ))}
      </div>

      <div className="mt-6 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
        <Button
          variant={isPrimary ? "primary" : "secondary"}
          onClick={() => onSelectPrimary(current.ddb_character_id)}
        >
          {isPrimary ? (
            <>
              <Sparkles className="h-4 w-4" />
              Selected as mine
            </>
          ) : (
            "This is my character"
          )}
        </Button>
      </div>
    </div>
  );
}
