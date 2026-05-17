from pydantic import BaseModel, Field


class AbilityScore(BaseModel):
    score: int = 10
    modifier: int = 0


class CharacterClass(BaseModel):
    name: str
    level: int = 1


class CharacterItem(BaseModel):
    name: str
    quantity: int = 1
    equipped: bool = False
    category: str | None = None


class CharacterFeature(BaseModel):
    name: str
    source: str | None = None


class CharacterSpell(BaseModel):
    name: str
    level: int | None = None
    prepared: bool | None = None


class CharacterSheet(BaseModel):
    ddb_character_id: int
    name: str
    race: str
    class_summary: str
    classes: list[CharacterClass]
    abilities: dict[str, AbilityScore]
    hit_points: int | None = None
    armor_class: int | None = None
    background: str | None = None
    speed: int | None = None
    alignment: str | None = None
    proficiency_bonus: int | None = None
    items: list[CharacterItem] = Field(default_factory=list)
    features: list[CharacterFeature] = Field(default_factory=list)
    spells: list[CharacterSpell] = Field(default_factory=list)
    avatar_url: str | None = None
    frame_avatar_url: str | None = None
    small_backdrop_avatar_url: str | None = None
    large_backdrop_avatar_url: str | None = None
    raw_source: str
