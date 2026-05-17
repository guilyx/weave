import type { Character, CharacterSnapshot } from "../api";

const ABILITY_ORDER = ["str", "dex", "con", "int", "wis", "cha"] as const;
const ABILITY_LABELS: Record<string, string> = {
  str: "STR",
  dex: "DEX",
  con: "CON",
  int: "INT",
  wis: "WIS",
  cha: "CHA",
};

export function parseSnapshot(raw: unknown): CharacterSnapshot {
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as CharacterSnapshot;
    } catch {
      return { name: "Unknown", race: "", class_summary: "" };
    }
  }
  return raw as CharacterSnapshot;
}

export function characterSnapshot(ch: Character): CharacterSnapshot {
  return parseSnapshot(ch.snapshot);
}

export function formatModifier(mod: number): string {
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

export function ddbCharacterUrl(ddbId: number): string {
  return `https://www.dndbeyond.com/characters/${ddbId}`;
}

/** Proxied through Weave so private portraits work with DDB_COBALT_SESSION. */
export function characterPortraitSrc(
  snapshot: CharacterSnapshot,
  ddbCharacterId?: number,
): string | undefined {
  if (!snapshot.avatar_url || !ddbCharacterId) return undefined;
  return `/api/v1/ddb/characters/${ddbCharacterId}/avatar`;
}

export function rosterPortraitSrc(ddbCharacterId: number, avatarUrl?: string | null): string | undefined {
  if (avatarUrl && ddbCharacterId) {
    return `/api/v1/ddb/characters/${ddbCharacterId}/avatar`;
  }
  return undefined;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function abilityRows(snapshot: CharacterSnapshot) {
  const abilities = snapshot.abilities ?? {};
  return ABILITY_ORDER.map((key) => ({
    key,
    label: ABILITY_LABELS[key],
    score: abilities[key]?.score ?? 10,
    modifier: abilities[key]?.modifier ?? 0,
  }));
}

export function characterSubtitle(snapshot: CharacterSnapshot): string {
  return [snapshot.race, snapshot.class_summary].filter(Boolean).join(" · ");
}

export function equippedItems(snapshot: CharacterSnapshot) {
  return (snapshot.items ?? []).filter((i) => i.equipped);
}

export function carriedItems(snapshot: CharacterSnapshot) {
  return (snapshot.items ?? []).filter((i) => !i.equipped);
}

export function spellsByLevel(snapshot: CharacterSnapshot) {
  const groups = new Map<number, string[]>();
  for (const spell of snapshot.spells ?? []) {
    const lvl = spell.level ?? 0;
    const list = groups.get(lvl) ?? [];
    list.push(spell.name);
    groups.set(lvl, list);
  }
  return [...groups.entries()].sort(([a], [b]) => a - b);
}

export function characterRecapLines(snapshot: CharacterSnapshot): string[] {
  const lines: string[] = [];
  const subtitle = characterSubtitle(snapshot);
  if (subtitle) lines.push(subtitle);
  if (snapshot.background) lines.push(`Background: ${snapshot.background}`);
  if (snapshot.alignment) lines.push(`Alignment: ${snapshot.alignment}`);
  if (snapshot.hit_points != null) lines.push(`Hit points: ${snapshot.hit_points}`);
  if (snapshot.armor_class != null) lines.push(`Armor class: ${snapshot.armor_class}`);
  if (snapshot.speed != null) lines.push(`Speed: ${snapshot.speed} ft`);
  if (snapshot.proficiency_bonus != null) {
    lines.push(`Proficiency: +${snapshot.proficiency_bonus}`);
  }
  if (snapshot.classes?.length) {
    lines.push(
      snapshot.classes.map((c) => `${c.name} ${c.level}`).join(" · "),
    );
  }
  return lines;
}
