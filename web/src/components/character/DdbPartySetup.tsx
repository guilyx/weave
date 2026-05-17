import { useMutation } from "@tanstack/react-query";
import { Loader2, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Character, type DdbRosterEntry } from "../../api";
import { CharacterCarousel } from "./CharacterCarousel";
import { Button } from "../ui/Button";
import { Card, CardTitle } from "../ui/Card";
import { Input, Label } from "../ui/Input";

type Phase = "campaign-id" | "carousel" | "done";

export function DdbPartySetup({
  campaignId,
  initialDdbCampaignId = "",
  autoLoad = false,
  onComplete,
}: {
  campaignId: string;
  initialDdbCampaignId?: string;
  autoLoad?: boolean;
  onComplete?: (chars: Character[]) => void;
}) {
  const [phase, setPhase] = useState<Phase>(
    initialDdbCampaignId.trim() ? "carousel" : "campaign-id",
  );
  const [ddbCampaignId, setDdbCampaignId] = useState(initialDdbCampaignId);
  const [roster, setRoster] = useState<DdbRosterEntry[]>([]);
  const [primaryId, setPrimaryId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchRoster = useMutation({
    mutationFn: (id: number) => api.fetchDdbRoster(id),
    onSuccess: (entries) => {
      setRoster(entries);
      setPrimaryId(entries[0]?.ddb_character_id ?? null);
      setPhase("carousel");
      setError(null);
    },
    onError: (e) => setError((e as Error).message),
  });

  const importParty = useMutation({
    mutationFn: () =>
      api.importDdbParty(campaignId, {
        ddb_campaign_id: Number(ddbCampaignId.trim()),
        ddb_character_ids: roster.map((e) => e.ddb_character_id),
        primary_ddb_character_id: primaryId ?? undefined,
      }),
    onSuccess: (data) => {
      setPhase("done");
      if (data.failed?.length) {
        setError(
          `Imported ${data.count} character(s). Failed: ${data.failed
            .map((f) => `#${f.ddb_character_id} (${f.error})`)
            .join("; ")}`,
        );
      } else {
        setError(null);
      }
      if (data.linked.length > 0) {
        onComplete?.(data.linked);
      }
    },
    onError: (e) => setError((e as Error).message),
  });

  const loadRoster = () => {
    const id = Number(ddbCampaignId.trim());
    if (!Number.isFinite(id) || id <= 0) {
      setError("Enter a valid D&D Beyond campaign ID");
      return;
    }
    fetchRoster.mutate(id);
  };

  useEffect(() => {
    if (autoLoad && initialDdbCampaignId.trim() && phase === "carousel" && roster.length === 0) {
      loadRoster();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoLoad, initialDdbCampaignId, campaignId]);

  return (
    <Card className="border-gold/25 bg-gradient-to-br from-gold/5 to-transparent">
      <CardTitle className="flex items-center gap-2">
        <Users className="h-5 w-5 text-gold" />
        D&amp;D Beyond party
      </CardTitle>

      {phase === "campaign-id" && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-muted">
            Paste the <strong className="text-parchment">campaign ID</strong> from your
            D&amp;D Beyond URL (e.g.{" "}
            <code className="text-gold">dndbeyond.com/campaigns/12345</code> →{" "}
            <code className="text-gold">12345</code>). We&apos;ll load everyone in the
            campaign.
          </p>
          <div>
            <Label htmlFor={`ddb-cid-${campaignId}`}>D&amp;D Beyond campaign ID</Label>
            <Input
              id={`ddb-cid-${campaignId}`}
              placeholder="e.g. 12345678"
              value={ddbCampaignId}
              onChange={(e) => setDdbCampaignId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadRoster()}
            />
          </div>
          <Button
            className="w-full sm:w-auto"
            disabled={!ddbCampaignId.trim() || fetchRoster.isPending}
            onClick={loadRoster}
          >
            {fetchRoster.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading party…
              </>
            ) : (
              "Load characters"
            )}
          </Button>
        </div>
      )}

      {phase === "carousel" && fetchRoster.isPending && roster.length === 0 && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted">
          <Loader2 className="h-6 w-6 animate-spin text-gold" />
          Fetching party from D&amp;D Beyond…
        </div>
      )}

      {phase === "carousel" && roster.length > 0 && (
        <div className="mt-4">
          <CharacterCarousel
            entries={roster}
            primaryId={primaryId}
            onSelectPrimary={setPrimaryId}
          />
          <Button
            className="mt-8 w-full"
            disabled={primaryId == null || importParty.isPending}
            onClick={() => importParty.mutate()}
          >
            {importParty.isPending
              ? "Importing party…"
              : `Import ${roster.length} character${roster.length === 1 ? "" : "s"} & continue`}
          </Button>
        </div>
      )}

      {phase === "done" && (
        <p className="mt-4 text-sm text-emerald-300">
          Party imported. Your character is marked in the roster below.
        </p>
      )}

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </Card>
  );
}
