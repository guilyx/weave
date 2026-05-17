import { Sparkles } from "lucide-react";
import type { Character } from "../../api";
import { characterSnapshot } from "../../lib/character";
import { CharacterPortrait } from "../character/CharacterPortrait";

export function SessionPartyStrip({ characters }: { characters: Character[] }) {
  if (characters.length === 0) return null;

  return (
    <div className="flex items-center gap-2 overflow-x-auto rounded-lg border border-border/70 bg-ink/40 px-2 py-2">
      {characters.map((ch) => {
        const snap = characterSnapshot(ch);
        return (
          <div
            key={ch.id}
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-border/60 bg-surface-raised/50 px-2 py-1"
            title={[snap.name, snap.class_summary].filter(Boolean).join(" · ")}
          >
            <CharacterPortrait
              snapshot={snap}
              ddbCharacterId={ch.ddb_character_id}
              size="sm"
              className="h-8 w-8 rounded-md text-[10px]"
            />
            <span className="max-w-[5.5rem] truncate text-xs font-medium text-parchment">
              {snap.name}
            </span>
            {ch.is_primary && (
              <Sparkles className="h-3 w-3 shrink-0 text-gold" aria-label="Your character" />
            )}
          </div>
        );
      })}
    </div>
  );
}
