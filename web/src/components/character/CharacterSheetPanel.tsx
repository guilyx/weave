import {
  Backpack,
  ExternalLink,
  Heart,
  RefreshCw,
  Scroll,
  Shield,
  Sparkles,
  Swords,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import type { CharacterSnapshot } from "../../api";
import {
  abilityRows,
  carriedItems,
  characterSubtitle,
  ddbCharacterUrl,
  equippedItems,
  formatModifier,
  spellsByLevel,
} from "../../lib/character";
import { CharacterPortrait } from "./CharacterPortrait";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

function ItemList({
  title,
  items,
  icon: Icon,
  dense,
}: {
  title: string;
  items: { name: string; quantity: number; category?: string | null }[];
  icon: typeof Swords;
  dense?: boolean;
}) {
  if (items.length === 0) return null;

  const list = (
    <ul className={dense ? "space-y-1" : "space-y-1.5"}>
      {items.map((item) => (
        <li
          key={`${title}-${item.name}`}
          className={`flex items-start justify-between gap-2 rounded-md border border-border/60 bg-ink/40 ${
            dense ? "px-2 py-1 text-xs" : "px-2.5 py-1.5 text-sm"
          }`}
        >
          <span className="text-parchment">{item.name}</span>
          <span className="shrink-0 text-[10px] text-muted sm:text-xs">
            {item.quantity > 1 ? `×${item.quantity}` : ""}
            {item.category ? ` · ${item.category}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );

  if (dense) {
    return (
      <details className="rounded border border-border/60 bg-ink/30">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2 py-1.5 font-display text-[10px] font-semibold uppercase tracking-wider text-gold [&::-webkit-details-marker]:hidden">
          <Icon className="h-3 w-3" />
          {title} ({items.length})
        </summary>
        <div className="px-2 pb-2">{list}</div>
      </details>
    );
  }

  return (
    <section>
      <h4 className="mb-2 flex items-center gap-1.5 font-display text-xs font-semibold uppercase tracking-wider text-gold">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </h4>
      {list}
    </section>
  );
}

function DenseFold({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Sparkles;
  children: ReactNode;
}) {
  return (
    <details className="rounded border border-border/60 bg-ink/30">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2 py-1.5 font-display text-[10px] font-semibold uppercase tracking-wider text-gold [&::-webkit-details-marker]:hidden">
        <Icon className="h-3 w-3" />
        {title}
      </summary>
      <div className="px-2 pb-2">{children}</div>
    </details>
  );
}

export function CharacterSheetPanel({
  snapshot,
  ddbCharacterId,
  isPrimary,
  variant = "full",
  hideHeader = false,
  onRefresh,
  refreshing,
}: {
  snapshot: CharacterSnapshot;
  ddbCharacterId?: number;
  isPrimary?: boolean;
  variant?: "full" | "compact" | "embed" | "dense";
  hideHeader?: boolean;
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  const abilities = abilityRows(snapshot);
  const equipped = equippedItems(snapshot);
  const carried = carriedItems(snapshot);
  const features = snapshot.features ?? [];
  const spellGroups = spellsByLevel(snapshot);
  const subtitle = characterSubtitle(snapshot);
  const dense = variant === "dense";
  const compact = variant === "compact" || dense;

  return (
    <div className="flex flex-col">
      {!hideHeader && (
      <div
        className={`border-b border-border bg-gradient-to-r from-gold/10 to-transparent ${
          compact ? "px-3 py-3" : "px-5 py-4"
        }`}
      >
        <div className="flex items-start gap-3">
          <CharacterPortrait
            snapshot={snapshot}
            ddbCharacterId={ddbCharacterId}
            size={compact ? "sm" : "md"}
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3
                className={`font-display font-semibold text-parchment ${
                  compact ? "text-lg" : "text-xl"
                }`}
              >
                {snapshot.name}
              </h3>
              {isPrimary && (
                <Badge tone="gold">
                  <Sparkles className="mr-0.5 inline h-3 w-3" />
                  Yours
                </Badge>
              )}
              {ddbCharacterId != null && (
                <Badge tone="muted">DDB #{ddbCharacterId}</Badge>
              )}
            </div>
            {subtitle && (
              <p className="mt-0.5 text-sm text-muted">{subtitle}</p>
            )}
            {snapshot.background && (
              <p className="mt-1 text-xs text-parchment/80">
                {snapshot.background}
                {snapshot.alignment ? ` · ${snapshot.alignment}` : ""}
              </p>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {snapshot.hit_points != null && (
            <span className="inline-flex items-center gap-1 rounded-md bg-crimson/20 px-2 py-1 text-red-200">
              <Heart className="h-3.5 w-3.5" />
              {snapshot.hit_points} HP
            </span>
          )}
          {snapshot.armor_class != null && (
            <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 text-parchment">
              <Shield className="h-3.5 w-3.5 text-gold" />
              AC {snapshot.armor_class}
            </span>
          )}
          {snapshot.speed != null && (
            <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 text-parchment">
              <Zap className="h-3.5 w-3.5 text-gold" />
              {snapshot.speed} ft
            </span>
          )}
          {snapshot.proficiency_bonus != null && (
            <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 text-parchment">
              Prof +{snapshot.proficiency_bonus}
            </span>
          )}
        </div>
      </div>
      )}

      <div
        className={`${dense ? "space-y-2 px-2 py-2" : compact ? "space-y-4 px-3 py-3" : "space-y-4 px-5 py-4"} ${
          variant === "embed" ? "max-h-[min(52vh,420px)] overflow-y-auto" : ""
        }`}
      >
        {hideHeader && dense && (
          <div className="flex flex-wrap gap-1.5 text-xs">
            {snapshot.hit_points != null && (
              <span className="inline-flex items-center gap-1 rounded bg-crimson/20 px-1.5 py-0.5 text-red-200">
                <Heart className="h-3 w-3" />
                {snapshot.hit_points} HP
              </span>
            )}
            {snapshot.armor_class != null && (
              <span className="inline-flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-parchment">
                <Shield className="h-3 w-3 text-gold" />
                AC {snapshot.armor_class}
              </span>
            )}
            {snapshot.speed != null && (
              <span className="inline-flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-parchment">
                <Zap className="h-3 w-3 text-gold" />
                {snapshot.speed} ft
              </span>
            )}
          </div>
        )}

        <div className={`grid grid-cols-6 ${dense ? "gap-1" : "gap-2"}`}>
          {abilities.map((a) => (
            <div
              key={a.key}
              className={`rounded-lg border border-border bg-ink/50 text-center ${
                dense ? "px-0.5 py-1" : "px-1 py-2"
              }`}
            >
              <div
                className={`font-bold uppercase tracking-wider text-muted ${
                  dense ? "text-[9px]" : "text-[10px]"
                }`}
              >
                {a.label}
              </div>
              <div
                className={`font-display font-semibold text-parchment ${
                  dense ? "text-sm" : compact ? "text-base" : "text-lg"
                }`}
              >
                {a.score}
              </div>
              <div className={dense ? "text-[10px] text-gold" : "text-xs text-gold"}>
                {formatModifier(a.modifier)}
              </div>
            </div>
          ))}
        </div>

        {!compact && snapshot.classes && snapshot.classes.length > 1 && (
          <section>
            <h4 className="mb-2 font-display text-xs font-semibold uppercase tracking-wider text-gold">
              Classes
            </h4>
            <div className="flex flex-wrap gap-2">
              {snapshot.classes.map((c) => (
                <Badge key={c.name} tone="muted">
                  {c.name} {c.level}
                </Badge>
              ))}
            </div>
          </section>
        )}

        <div className={dense ? "space-y-2" : compact ? "space-y-3" : "grid gap-4 sm:grid-cols-2"}>
          <ItemList title="Equipped" items={equipped} icon={Swords} dense={dense} />
          <ItemList title="Inventory" items={carried} icon={Backpack} dense={dense} />
        </div>

        {equipped.length === 0 && carried.length === 0 && !compact && (
          <p className="text-sm text-muted">
            No gear listed on the sheet — sync again after updating D&amp;D Beyond.
          </p>
        )}

        {features.length > 0 &&
          (dense ? (
            <DenseFold title={`Features (${features.length})`} icon={Sparkles}>
              <ul className="flex flex-wrap gap-1">
                {features.map((f) => (
                  <li
                    key={f.name}
                    className="rounded-full border border-border bg-ink/50 px-2 py-0.5 text-[10px] text-parchment"
                    title={f.source ?? undefined}
                  >
                    {f.name}
                  </li>
                ))}
              </ul>
            </DenseFold>
          ) : (
            <section>
              <h4 className="mb-2 flex items-center gap-1.5 font-display text-xs font-semibold uppercase tracking-wider text-gold">
                <Sparkles className="h-3.5 w-3.5" />
                Features &amp; feats
              </h4>
              <ul className="flex flex-wrap gap-2">
                {features.map((f) => (
                  <li
                    key={f.name}
                    className="rounded-full border border-border bg-ink/50 px-2.5 py-1 text-xs text-parchment"
                    title={f.source ?? undefined}
                  >
                    {f.name}
                  </li>
                ))}
              </ul>
            </section>
          ))}

        {spellGroups.length > 0 &&
          (dense ? (
            <DenseFold title={`Spells (${spellGroups.length} levels)`} icon={Scroll}>
              <div className="space-y-1">
                {spellGroups.map(([level, names]) => (
                  <div key={level}>
                    <p className="text-[9px] font-bold uppercase text-muted">
                      {level === 0 ? "Cantrips" : `L${level}`}
                    </p>
                    <p className="text-[11px] text-parchment/90">{names.join(", ")}</p>
                  </div>
                ))}
              </div>
            </DenseFold>
          ) : (
            <section>
              <h4 className="mb-2 flex items-center gap-1.5 font-display text-xs font-semibold uppercase tracking-wider text-gold">
                <Scroll className="h-3.5 w-3.5" />
                Spells
              </h4>
              <div className="space-y-2">
                {spellGroups.map(([level, names]) => (
                  <div key={level}>
                    <p className="text-[10px] font-bold uppercase text-muted">
                      {level === 0 ? "Cantrips" : `Level ${level}`}
                    </p>
                    <p className="text-sm text-parchment/90">{names.join(", ")}</p>
                  </div>
                ))}
              </div>
            </section>
          ))}

        {ddbCharacterId != null && (
          <div
            className={`flex flex-wrap items-center gap-2 border-t border-border ${
              dense ? "pt-2" : "pt-3"
            }`}
          >
            <a
              href={ddbCharacterUrl(ddbCharacterId)}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-1.5 text-gold hover:underline ${
                dense ? "text-xs" : "text-sm"
              }`}
            >
              Open on D&amp;D Beyond
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
            {onRefresh && (
              <Button
                variant="secondary"
                className="ml-auto py-1.5 text-xs"
                disabled={refreshing}
                onClick={onRefresh}
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
                />
                Sync sheet
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
