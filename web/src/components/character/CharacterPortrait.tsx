import { useState } from "react";
import type { CharacterSnapshot } from "../../api";
import { characterPortraitSrc, initials } from "../../lib/character";

export function CharacterPortrait({
  snapshot,
  ddbCharacterId,
  size = "md",
  className = "",
}: {
  snapshot: CharacterSnapshot;
  ddbCharacterId?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = characterPortraitSrc(snapshot, ddbCharacterId);
  const showImage = src && !failed;

  const sizeClass =
    size === "sm"
      ? "h-11 w-11 text-sm"
      : size === "lg"
        ? "h-20 w-20 text-2xl"
        : "h-14 w-14 text-lg";

  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-gold/30 bg-ink font-display font-bold text-gold ${sizeClass} ${className}`}
    >
      {showImage ? (
        <img
          src={src}
          alt=""
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        initials(snapshot.name)
      )}
    </div>
  );
}
