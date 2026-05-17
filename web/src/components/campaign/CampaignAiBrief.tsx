import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Brain, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Campaign } from "../../api";
import { Button } from "../ui/Button";
import { Card, CardTitle } from "../ui/Card";
import { Label, Textarea } from "../ui/Input";

export function CampaignAiBrief({
  campaignId,
  campaign,
}: {
  campaignId: string;
  campaign: Campaign;
}) {
  const qc = useQueryClient();
  const [brief, setBrief] = useState(campaign.ai_brief ?? "");

  useEffect(() => {
    setBrief(campaign.ai_brief ?? "");
  }, [campaign.ai_brief]);

  const save = useMutation({
    mutationFn: () =>
      api.updateCampaign(campaignId, { ai_brief: brief.trim() || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
    },
  });

  const dirty = brief !== (campaign.ai_brief ?? "");

  return (
    <Card className="border-gold/20">
      <CardTitle className="flex items-center gap-2">
        <Brain className="h-5 w-5 text-gold" />
        Campaign brief for the AI
      </CardTitle>
      <p className="mt-2 text-sm text-muted">
        This text is included in every live-session prompt: recaps, suggestions, and
        session chat. Summarize where the story is, major NPCs, open threads, and
        anything the assistant should always remember.
      </p>
      <div className="mt-4">
        <Label htmlFor="ai-brief">Standing campaign summary</Label>
        <Textarea
          id="ai-brief"
          className="mt-1.5 min-h-[200px] font-mono text-sm leading-relaxed"
          placeholder={`Example:\n- Level 5 party in Vallaki (Curse of Strahd)\n- Ally: Ireena (escort quest active)\n- Villain: Strahd has appeared twice; party wary of dreams\n- House rule: flanking grants +2`}
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
        />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          <Save className="h-4 w-4" />
          {save.isPending ? "Saving…" : "Save brief"}
        </Button>
        {save.isSuccess && !dirty && (
          <span className="text-sm text-emerald-300">Saved.</span>
        )}
        {save.error && (
          <span className="text-sm text-red-400">{(save.error as Error).message}</span>
        )}
      </div>
      <ul className="mt-6 space-y-2 border-t border-border pt-4 text-sm text-muted">
        <li>
          <strong className="text-parchment">Lore tab</strong> — reference docs (NPCs,
          locations) are injected as separate sections.
        </li>
        <li>
          <strong className="text-parchment">Session recap</strong> — builds during play
          for the current session; ended sessions&apos; recaps are included automatically.
        </li>
        <li>
          <strong className="text-parchment">Party</strong> — full character sheets from
          D&amp;D Beyond are sent with each agent call.
        </li>
      </ul>
    </Card>
  );
}
