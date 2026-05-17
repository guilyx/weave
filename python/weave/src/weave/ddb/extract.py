"""Extract inventory, features, and spells from D&D Beyond JSON shapes."""

from typing import Any

from weave.ddb.models import CharacterFeature, CharacterItem, CharacterSpell


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _item_name(raw: dict[str, Any]) -> str | None:
    definition = raw.get("definition") or raw.get("itemDefinition") or {}
    if not isinstance(definition, dict):
        definition = {}
    name = definition.get("name") or raw.get("name") or raw.get("displayName")
    if name:
        return str(name).strip()
    return None


def _item_category(raw: dict[str, Any]) -> str | None:
    definition = raw.get("definition") or raw.get("itemDefinition") or {}
    if not isinstance(definition, dict):
        definition = {}
    for key in ("type", "filterType", "category"):
        val = definition.get(key) or raw.get(key)
        if val:
            return str(val)
    return None


def _is_equipped(raw: dict[str, Any]) -> bool:
    if raw.get("equipped") is True or raw.get("isEquipped") is True:
        return True
    if raw.get("equipped") is False or raw.get("isEquipped") is False:
        return False
    state = raw.get("equippedState") or raw.get("equippedType")
    if isinstance(state, str):
        lowered = state.lower()
        return lowered in ("equipped", "worn", "active")
    return False


def _parse_item(raw: Any) -> CharacterItem | None:
    if not isinstance(raw, dict):
        return None
    name = _item_name(raw)
    if not name:
        return None
    qty = _as_int(raw.get("quantity") or raw.get("qty")) or 1
    return CharacterItem(
        name=name,
        quantity=max(qty, 1),
        equipped=_is_equipped(raw),
        category=_item_category(raw),
    )


def _append_items(raw: Any, out: list[CharacterItem], seen: set[str]) -> None:
    if isinstance(raw, list):
        for entry in raw:
            item = _parse_item(entry)
            if item and item.name not in seen:
                seen.add(item.name)
                out.append(item)
    elif isinstance(raw, dict):
        for key in ("equipped", "equippedItems", "inventory", "backpack", "carriedGear", "items"):
            if key in raw:
                _append_items(raw[key], out, seen)
        if "containers" in raw:
            for container in raw.get("containers") or []:
                if isinstance(container, dict):
                    _append_items(container.get("items") or container.get("inventory"), out, seen)


def extract_items(root: dict[str, Any]) -> list[CharacterItem]:
    items: list[CharacterItem] = []
    seen: set[str] = set()
    _append_items(root.get("inventory"), items, seen)
    _append_items(root.get("customItems"), items, seen)
    _append_items(root.get("equipment"), items, seen)
    modifiers = root.get("modifiers")
    if isinstance(modifiers, dict):
        _append_items(modifiers.get("item"), items, seen)
    elif isinstance(modifiers, list):
        for mod in modifiers:
            if isinstance(mod, dict) and mod.get("type") in ("item", "equipment"):
                item = _parse_item(mod)
                if item and item.name not in seen:
                    seen.add(item.name)
                    items.append(item)
    return items


def _feature_name(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    definition = raw.get("definition") or {}
    if not isinstance(definition, dict):
        definition = {}
    name = definition.get("name") or raw.get("name") or raw.get("displayName")
    return str(name).strip() if name else None


def _feature_source(raw: dict[str, Any]) -> str | None:
    for key in ("source", "sourceType", "type"):
        val = raw.get(key)
        if val:
            return str(val)
    definition = raw.get("definition")
    if isinstance(definition, dict) and definition.get("source"):
        return str(definition["source"])
    return None


def _append_features(raw: Any, out: list[CharacterFeature], seen: set[str]) -> None:
    if not isinstance(raw, list):
        return
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = _feature_name(entry)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(CharacterFeature(name=name, source=_feature_source(entry)))


def extract_features(root: dict[str, Any]) -> list[CharacterFeature]:
    features: list[CharacterFeature] = []
    seen: set[str] = set()
    for key in (
        "traits",
        "racialTraits",
        "feats",
        "classFeatures",
        "features",
        "options",
    ):
        _append_features(root.get(key), features, seen)
    modifiers = root.get("modifiers")
    if isinstance(modifiers, dict):
        for mod_type in ("race", "class", "feat", "background", "item"):
            _append_features(modifiers.get(mod_type), features, seen)
    return features


def _parse_spell(raw: Any) -> CharacterSpell | None:
    if not isinstance(raw, dict):
        return None
    definition = raw.get("definition") or raw.get("spellDefinition") or {}
    if not isinstance(definition, dict):
        definition = {}
    name = definition.get("name") or raw.get("name")
    if not name:
        return None
    level = _as_int(definition.get("level") or raw.get("level"))
    prepared = raw.get("prepared")
    if prepared is None:
        prepared = raw.get("alwaysPrepared")
    return CharacterSpell(
        name=str(name),
        level=level,
        prepared=bool(prepared) if prepared is not None else None,
    )


def extract_spells(root: dict[str, Any]) -> list[CharacterSpell]:
    spells: list[CharacterSpell] = []
    seen: set[str] = set()
    spell_root = root.get("spells") or root.get("classSpells") or []
    if isinstance(spell_root, list):
        for group in spell_root:
            if isinstance(group, dict):
                group_spells = group.get("spells") or group.get("spellList") or []
                for raw in group_spells:
                    spell = _parse_spell(raw)
                    if spell and spell.name not in seen:
                        seen.add(spell.name)
                        spells.append(spell)
            else:
                spell = _parse_spell(group)
                if spell and spell.name not in seen:
                    seen.add(spell.name)
                    spells.append(spell)
    spells.sort(key=lambda s: (s.level if s.level is not None else 99, s.name))
    return spells


def extract_speed(root: dict[str, Any]) -> int | None:
    speed = root.get("speed")
    if isinstance(speed, (int, float)):
        return int(speed)
    if isinstance(speed, dict):
        for key in ("walk", "Walk", "speed", "value"):
            val = _as_int(speed.get(key))
            if val is not None:
                return val
    return _as_int(root.get("walkingSpeed") or root.get("walking_speed"))


def extract_alignment(root: dict[str, Any]) -> str | None:
    alignment = root.get("alignment")
    if isinstance(alignment, dict):
        alignment = alignment.get("name") or alignment.get("shortName")
    if alignment:
        return str(alignment)
    details = root.get("details")
    if isinstance(details, dict) and details.get("alignment"):
        return str(details["alignment"])
    return None


def extract_proficiency_bonus(root: dict[str, Any]) -> int | None:
    for key in ("proficiencyBonus", "proficiency_bonus", "bonusProficiency"):
        val = _as_int(root.get(key))
        if val is not None:
            return val
    return None
