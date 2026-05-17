import type { Character } from "../../api";
import { PartyCompactGrid } from "./PartyCompactGrid";

export function PartyRosterPanel({
  characters,
  onRefresh,
  refreshingId,
}: {
  characters: Character[];
  onRefresh?: (character: Character) => void;
  refreshingId?: string | null;
}) {
  return (
    <PartyCompactGrid
      characters={characters}
      title="Party"
      onRefresh={onRefresh}
      refreshingId={refreshingId}
      className="max-h-[min(40dvh,calc(100dvh-14rem))]"
    />
  );
}
