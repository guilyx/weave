import type { Character } from "../../api";
import { characterSnapshot } from "../../lib/character";
import { Card } from "../ui/Card";
import { CharacterSheetPanel } from "./CharacterSheetPanel";

export function CharacterCard({
  character,
  onRefresh,
  refreshing,
  variant = "full",
}: {
  character: Character;
  onRefresh?: () => void;
  refreshing?: boolean;
  variant?: "full" | "compact";
}) {
  const snap = characterSnapshot(character);

  return (
    <Card className="overflow-hidden p-0">
      <CharacterSheetPanel
        snapshot={snap}
        ddbCharacterId={character.ddb_character_id}
        isPrimary={!!character.is_primary}
        variant={variant}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />
    </Card>
  );
}
