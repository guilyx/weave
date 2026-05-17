from typing import Any

from weave.ddb.extract import (
    extract_alignment,
    extract_features,
    extract_items,
    extract_proficiency_bonus,
    extract_spells,
    extract_speed,
)
from weave.ddb.portraits import extract_portraits
from weave.ddb.models import AbilityScore, CharacterClass, CharacterSheet

ABILITY_MAP = {1: "str", 2: "dex", 3: "con", 4: "int", 5: "wis", 6: "cha"}


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def _safe_int(value: Any, default: int = 10) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def race_name(raw: Any) -> str:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        return str(
            raw.get("fullName") or raw.get("name") or raw.get("definition", {}).get("name") or "Unknown"
        )
    return "Unknown"


def background_name(raw: Any) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        definition = raw.get("definition")
        if isinstance(definition, dict) and definition.get("name"):
            return str(definition["name"])
        if raw.get("name"):
            return str(raw["name"])
    return None


def abilities_from_stats(stats: list[Any]) -> dict[str, AbilityScore]:
    data: dict[str, AbilityScore] = {
        k: AbilityScore() for k in ("str", "dex", "con", "int", "wis", "cha")
    }
    for stat in stats:
        if not isinstance(stat, dict):
            continue
        sid = stat.get("id")
        value = stat.get("value", stat.get("score", 10))
        if sid is None:
            continue
        key = ABILITY_MAP.get(_safe_int(sid, -1))
        if key:
            score = _safe_int(value, 10)
            data[key] = AbilityScore(score=score, modifier=ability_modifier(score))
    return data


def classes_from_json(classes: list[Any]) -> list[CharacterClass]:
    out: list[CharacterClass] = []
    for c in classes:
        if not isinstance(c, dict):
            continue
        definition = c.get("definition") or {}
        name = definition.get("name") or c.get("name")
        if not name:
            continue
        level = _safe_int(c.get("level", 1), 1)
        out.append(CharacterClass(name=str(name), level=max(level, 1)))
    return out


def class_summary(classes: list[CharacterClass]) -> str:
    return " | ".join(f"{c.name} {c.level}" for c in classes)


def normalize_v5(character_id: int, data: dict[str, Any]) -> CharacterSheet:
    root = data.get("data", data)
    if not isinstance(root, dict):
        root = data
    race = race_name(root.get("race")) if root.get("race") else str(root.get("race_full_name") or "Unknown")
    classes = classes_from_json(root.get("classes") or [])
    stats = root.get("stats") or []
    background = background_name(root.get("background")) or root.get("background_name")
    portraits = extract_portraits(root)
    return CharacterSheet(
        ddb_character_id=character_id,
        name=str(root.get("name", "Unknown")),
        race=str(race),
        class_summary=class_summary(classes),
        classes=classes,
        abilities=abilities_from_stats(stats),
        hit_points=root.get("baseHitPoints") or root.get("base_hit_points"),
        armor_class=root.get("armorClass"),
        background=str(background) if background else None,
        speed=extract_speed(root),
        alignment=extract_alignment(root),
        proficiency_bonus=extract_proficiency_bonus(root),
        items=extract_items(root),
        features=extract_features(root),
        spells=extract_spells(root),
        avatar_url=portraits.avatar_url,
        frame_avatar_url=portraits.frame_avatar_url,
        small_backdrop_avatar_url=portraits.small_backdrop_avatar_url,
        large_backdrop_avatar_url=portraits.large_backdrop_avatar_url,
        raw_source="v5",
    )


def normalize_legacy(character_id: int, data: dict[str, Any]) -> CharacterSheet:
    race = race_name(data.get("race"))
    classes = classes_from_json(data.get("classes") or [])
    stats = data.get("stats") or []
    background = background_name(data.get("background")) or data.get("backgroundName")
    portraits = extract_portraits(data)
    return CharacterSheet(
        ddb_character_id=character_id,
        name=str(data.get("name", "Unknown")),
        race=str(race),
        class_summary=class_summary(classes),
        classes=classes,
        abilities=abilities_from_stats(stats),
        hit_points=data.get("baseHitPoints") or data.get("base_hit_points"),
        armor_class=data.get("armorClass"),
        background=str(background) if background else None,
        speed=extract_speed(data),
        alignment=extract_alignment(data),
        proficiency_bonus=extract_proficiency_bonus(data),
        items=extract_items(data),
        features=extract_features(data),
        spells=extract_spells(data),
        avatar_url=portraits.avatar_url,
        frame_avatar_url=portraits.frame_avatar_url,
        small_backdrop_avatar_url=portraits.small_backdrop_avatar_url,
        large_backdrop_avatar_url=portraits.large_backdrop_avatar_url,
        raw_source="legacy",
    )
