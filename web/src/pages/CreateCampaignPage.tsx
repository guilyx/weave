import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Character } from "../api";
import { PartyCompactGrid } from "../components/character/PartyCompactGrid";
import { DdbPartySetup } from "../components/character/DdbPartySetup";
import { Button } from "../components/ui/Button";
import { Card, CardTitle } from "../components/ui/Card";
import { Input, Label, Textarea } from "../components/ui/Input";

type Step = "details" | "party";

export default function CreateCampaignPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>("details");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [ddbCampaignId, setDdbCampaignId] = useState("");
  const [weaveCampaignId, setWeaveCampaignId] = useState<string | null>(null);
  const [party, setParty] = useState<Character[]>([]);
  const [partyDone, setPartyDone] = useState(false);

  const create = useMutation({
    mutationFn: () => api.createCampaign(name, description || undefined),
    onSuccess: (c) => {
      setWeaveCampaignId(c.id);
      setStep("party");
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });

  const canContinue =
    name.trim().length > 0 && ddbCampaignId.trim().length > 0 && /^\d+$/.test(ddbCampaignId.trim());

  return (
    <div className="mx-auto h-full max-w-3xl overflow-y-auto py-3">
      <Link
        to="/"
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted no-underline hover:text-gold"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to campaigns
      </Link>

      <h1 className="font-display text-3xl font-semibold text-parchment">New campaign</h1>
      <p className="mt-2 text-muted text-balance">
        Link your D&amp;D Beyond campaign, pick your character from the party, and Weave
        imports everyone for live sessions.
      </p>

      <ol className="my-8 flex gap-2">
        {(["details", "party"] as Step[]).map((s, i) => (
          <li
            key={s}
            className={`flex flex-1 items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
              step === s
                ? "border-gold bg-gold/10 text-gold"
                : weaveCampaignId && s === "details"
                  ? "border-moss/50 text-emerald-300"
                  : "border-border text-muted"
            }`}
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink text-xs font-bold">
              {weaveCampaignId && s === "details" ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                i + 1
              )}
            </span>
            {s === "details" ? "Campaign" : "Your character"}
          </li>
        ))}
      </ol>

      {step === "details" && (
        <Card>
          <CardTitle>Campaign &amp; D&amp;D Beyond</CardTitle>
          <div className="mt-4 space-y-4">
            <div>
              <Label htmlFor="name">Campaign name</Label>
              <Input
                id="name"
                placeholder="Curse of Strahd — Table 3"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="ddb-campaign-id">D&amp;D Beyond campaign ID</Label>
              <Input
                id="ddb-campaign-id"
                inputMode="numeric"
                placeholder="Numeric ID from dndbeyond.com/campaigns/…"
                value={ddbCampaignId}
                onChange={(e) => setDdbCampaignId(e.target.value.replace(/\D/g, ""))}
              />
              <p className="mt-1.5 text-xs text-muted">
                Open your campaign on D&amp;D Beyond — the number in the URL is the ID.
                Requires <code className="text-gold">DDB_COBALT_SESSION</code> on the server.
              </p>
            </div>
            <div>
              <Label htmlFor="desc">Description (optional)</Label>
              <Textarea
                id="desc"
                placeholder="Weekly game, level 5…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            {create.error && (
              <p className="text-sm text-red-400">{(create.error as Error).message}</p>
            )}
            <Button
              className="w-full sm:w-auto"
              disabled={!canContinue || create.isPending}
              onClick={() => create.mutate()}
            >
              Continue — choose your character
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      )}

      {step === "party" && weaveCampaignId && (
        <div className="flex max-h-[calc(100dvh-11rem)] flex-col gap-4 overflow-hidden">
          {!partyDone && (
            <DdbPartySetup
              campaignId={weaveCampaignId}
              initialDdbCampaignId={ddbCampaignId}
              autoLoad
              onComplete={(chars) => {
                setParty(chars);
                setPartyDone(true);
              }}
            />
          )}

          {partyDone && party.length > 0 && (
            <>
              <h2 className="shrink-0 font-display text-lg text-gold">Party imported</h2>
              <PartyCompactGrid
                characters={party}
                className="min-h-0 flex-1 max-h-full"
              />
              <Card className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted">Ready to run sessions.</p>
                <Button onClick={() => navigate(`/campaigns/${weaveCampaignId}`)}>
                  Open campaign
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
