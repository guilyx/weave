import { Crown, FileText, Heart, Shield, Sparkles, Users } from "lucide-react";
import type { Character } from "../../api";
import { characterSnapshot } from "../../lib/character";
import { CharacterPortrait } from "../character/CharacterPortrait";

export type SessionViewpoint =
  | { mode: "dm" }
  | { mode: "player"; characterId: string };

export function SessionPartyRail({
  characters,
  viewpoint,
  sheetCharacterId,
  onViewpointChange,
  onOpenSheet,
}: {
  characters: Character[];
  viewpoint: SessionViewpoint;
  sheetCharacterId: string | null;
  onViewpointChange: (v: SessionViewpoint) => void;
  onOpenSheet: (characterId: string | null) => void;
}) {
  const dmActive = viewpoint.mode === "dm";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted">
        <Users className="h-4 w-4 text-gold/80" aria-hidden />
        Perspective
      </div>

      <ul className="shrink-0 space-y-1.5 px-2 pb-2">
        <li>
          <button
            type="button"
            onClick={() => {
              onViewpointChange({ mode: "dm" });
              onOpenSheet(null);
            }}
            className={`flex w-full items-center gap-2.5 rounded-lg border px-2.5 py-2.5 text-left transition ${
              dmActive
                ? "border-gold/50 bg-gold/15 ring-1 ring-gold/30"
                : "border-border/60 bg-ink/30 hover:border-gold/30 hover:bg-gold/5"
            }`}
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-gold/35 bg-gold/12 text-gold">
              <Crown className="h-5 w-5" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-parchment">Dungeon Master</span>
              <span className="block text-xs text-muted">Table chronicle &amp; DM tools</span>
            </span>
          </button>
        </li>
      </ul>

      {characters.length === 0 ? (
        <p className="px-3 py-2 text-center text-sm text-muted">
          Import party on the campaign page.
        </p>
      ) : (
        <>
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted/80">
            Players
          </p>
          <ul className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-2 pb-2">
            {characters.map((ch) => {
              const snap = characterSnapshot(ch);
              const playerActive =
                viewpoint.mode === "player" && viewpoint.characterId === ch.id;
              const sheetOpen = sheetCharacterId === ch.id;
              return (
                <li key={ch.id} className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => {
                      onViewpointChange({ mode: "player", characterId: ch.id });
                      onOpenSheet(null);
                    }}
                    className={`flex min-w-0 flex-1 items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition ${
                      playerActive
                        ? "border-gold/50 bg-gold/15 ring-1 ring-gold/30"
                        : "border-border/60 bg-ink/30 hover:border-gold/30 hover:bg-gold/5"
                    }`}
                  >
                    <CharacterPortrait
                      snapshot={snap}
                      ddbCharacterId={ch.ddb_character_id}
                      size="sm"
                      className="h-11 w-11 shrink-0 rounded-lg text-xs"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1 truncate text-sm font-medium text-parchment">
                        {snap.name}
                        {ch.is_primary && (
                          <Sparkles
                            className="h-3.5 w-3.5 shrink-0 text-gold"
                            aria-label="Your character"
                          />
                        )}
                      </span>
                      <span className="block truncate text-xs text-muted">
                        {snap.class_summary || snap.race}
                      </span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        {snap.hit_points != null && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-crimson/20 px-1.5 py-0.5 text-[11px] text-red-200">
                            <Heart className="h-3 w-3" aria-hidden />
                            {snap.hit_points}
                          </span>
                        )}
                        {snap.armor_class != null && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-white/5 px-1.5 py-0.5 text-[11px] text-parchment">
                            <Shield className="h-3 w-3 text-gold" aria-hidden />
                            {snap.armor_class}
                          </span>
                        )}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    title="Character sheet"
                    aria-label={`Open sheet for ${snap.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenSheet(sheetOpen ? null : ch.id);
                    }}
                    className={`shrink-0 self-center rounded-lg border p-2 transition ${
                      sheetOpen
                        ? "border-gold/50 bg-gold/15 text-gold"
                        : "border-border/60 text-muted hover:border-gold/30 hover:text-parchment"
                    }`}
                  >
                    <FileText className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
