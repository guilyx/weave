import { Heart, Shield, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import type { Character } from "../../api";
import { characterSnapshot } from "../../lib/character";
import { CharacterPortrait } from "./CharacterPortrait";
import { CharacterSheetPanel } from "./CharacterSheetPanel";
import { Card } from "../ui/Card";

function PartyTile({
  character,
  selected,
  onSelect,
}: {
  character: Character;
  selected: boolean;
  onSelect: () => void;
}) {
  const snap = characterSnapshot(character);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex min-w-0 flex-col items-center rounded-lg border p-2 text-center transition ${
        selected
          ? "border-gold bg-gold/15 ring-1 ring-gold/40"
          : "border-border/70 bg-ink/40 hover:border-gold/35 hover:bg-gold/5"
      }`}
    >
      <CharacterPortrait
        snapshot={snap}
        ddbCharacterId={character.ddb_character_id}
        size="sm"
        className="h-10 w-10 rounded-lg text-xs"
      />
      <p className="mt-2 w-full truncate text-sm font-medium text-parchment">
        {snap.name}
        {character.is_primary && (
          <Sparkles className="ml-0.5 inline h-3 w-3 text-gold" aria-hidden />
        )}
      </p>
      <p className="w-full truncate text-xs leading-tight text-muted">
        {snap.class_summary || snap.race}
      </p>
      <div className="mt-1 flex flex-wrap justify-center gap-1">
        {snap.hit_points != null && (
          <span className="inline-flex items-center gap-0.5 rounded bg-crimson/20 px-1.5 py-0.5 text-xs text-red-200">
            <Heart className="h-3 w-3" />
            {snap.hit_points}
          </span>
        )}
        {snap.armor_class != null && (
          <span className="inline-flex items-center gap-0.5 rounded bg-white/5 px-1.5 py-0.5 text-xs text-parchment">
            <Shield className="h-3 w-3 text-gold" />
            {snap.armor_class}
          </span>
        )}
      </div>
    </button>
  );
}

export function PartyCompactGrid({
  characters,
  title = "Party",
  onRefresh,
  refreshingId,
  className = "",
}: {
  characters: Character[];
  title?: string;
  onRefresh?: (character: Character) => void;
  refreshingId?: string | null;
  className?: string;
}) {
  const defaultId =
    characters.find((c) => c.is_primary)?.id ?? characters[0]?.id ?? null;
  const [selectedId, setSelectedId] = useState<string | null>(defaultId);

  useEffect(() => {
    if (!characters.some((c) => c.id === selectedId)) {
      setSelectedId(defaultId);
    }
  }, [characters, selectedId, defaultId]);

  const selected = characters.find((c) => c.id === selectedId);

  if (characters.length === 0) return null;

  return (
    <Card
      className={`flex min-h-0 flex-col overflow-hidden p-0 ${className}`}
    >
      <div className="flex shrink-0 items-center justify-between border-b border-border px-3 py-2">
        <p className="text-sm font-medium text-parchment">
          {title}{" "}
          <span className="text-muted">({characters.length})</span>
        </p>
        <p className="text-[10px] text-muted">Tap a hero for full sheet</p>
      </div>

      <div className="min-h-0 shrink-0 overflow-y-auto p-2">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {characters.map((ch) => (
            <PartyTile
              key={ch.id}
              character={ch}
              selected={selectedId === ch.id}
              onSelect={() => setSelectedId(ch.id)}
            />
          ))}
        </div>
      </div>

      {selected && (
        <div className="min-h-0 flex-1 overflow-y-auto border-t border-border bg-ink/20">
          <CharacterSheetPanel
            snapshot={characterSnapshot(selected)}
            ddbCharacterId={selected.ddb_character_id}
            isPrimary={!!selected.is_primary}
            variant="dense"
            hideHeader
            onRefresh={onRefresh ? () => onRefresh(selected) : undefined}
            refreshing={refreshingId === selected.id}
          />
        </div>
      )}
    </Card>
  );
}
