import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Mic,
  ScrollText,
  Sparkles,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { PartyCompactGrid } from "../components/character/PartyCompactGrid";
import { CampaignAiBrief } from "../components/campaign/CampaignAiBrief";
import { DdbPartySetup } from "../components/character/DdbPartySetup";
import { SidebarTabs } from "../components/layout/SidebarTabs";
import { WorkspaceLayout } from "../components/layout/WorkspaceLayout";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardTitle } from "../components/ui/Card";
import { Input, Label, Textarea } from "../components/ui/Input";

type Tab = "party" | "sessions" | "lore" | "brief";

export default function CampaignDetailPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("party");
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [loreTitle, setLoreTitle] = useState("");
  const [loreContent, setLoreContent] = useState("");
  const [sessionTitle, setSessionTitle] = useState("");
  const [showDdbImport, setShowDdbImport] = useState(false);

  const campaign = useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => api.getCampaign(campaignId!),
    enabled: !!campaignId,
  });

  const characters = useQuery({
    queryKey: ["characters", campaignId],
    queryFn: () => api.listCharacters(campaignId!),
    enabled: !!campaignId,
  });

  const sessions = useQuery({
    queryKey: ["sessions", campaignId],
    queryFn: () => api.listSessions(campaignId!),
    enabled: !!campaignId,
  });

  const lore = useQuery({
    queryKey: ["lore", campaignId],
    queryFn: () => api.listLore(campaignId!),
    enabled: !!campaignId,
  });

  const addLore = useMutation({
    mutationFn: () => api.createLore(campaignId!, loreTitle, loreContent),
    onSuccess: () => {
      setLoreTitle("");
      setLoreContent("");
      qc.invalidateQueries({ queryKey: ["lore", campaignId] });
    },
  });

  const newSession = useMutation({
    mutationFn: () =>
      api.createSession(campaignId!, sessionTitle || undefined),
    onSuccess: () => {
      setSessionTitle("");
      qc.invalidateQueries({ queryKey: ["sessions", campaignId] });
    },
  });

  if (!campaignId) return null;

  const party = characters.data ?? [];
  const sessionList = sessions.data ?? [];
  const needsParty = party.length === 0;

  return (
    <div className="h-full min-h-0 py-3">
      <WorkspaceLayout
        sidebar={
          <div className="flex h-full min-h-0 flex-col">
            <div className="shrink-0 space-y-2 border-b border-border p-2">
              <Link
                to="/"
                className="inline-flex items-center gap-1 text-xs text-muted no-underline hover:text-gold"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Campaigns
              </Link>
              <h1 className="truncate font-display text-base font-semibold text-parchment">
                {campaign.data?.name ?? "…"}
              </h1>
              {campaign.data?.description && (
                <p className="line-clamp-3 text-xs text-muted">
                  {campaign.data.description}
                </p>
              )}
            </div>
            <SidebarTabs<Tab>
              tabs={[
                {
                  id: "party",
                  label: "Party",
                  icon: <Users className="h-4 w-4 shrink-0" />,
                  count: party.length,
                },
                {
                  id: "sessions",
                  label: "Sessions",
                  icon: <Mic className="h-4 w-4 shrink-0" />,
                  count: sessionList.length,
                },
                {
                  id: "lore",
                  label: "Lore",
                  icon: <BookOpen className="h-4 w-4 shrink-0" />,
                  count: lore.data?.length,
                },
                {
                  id: "brief",
                  label: "AI brief",
                  icon: <Sparkles className="h-4 w-4 shrink-0" />,
                },
              ]}
              active={tab}
              onChange={setTab}
            />
          </div>
        }
      >
        <div className="h-full min-h-0 overflow-y-auto p-4">
          {tab === "party" && (
            <div className="flex h-full min-h-0 w-full flex-col gap-4">
              {needsParty ? (
                <DdbPartySetup
                  campaignId={campaignId}
                  onComplete={() => {
                    qc.invalidateQueries({ queryKey: ["characters", campaignId] });
                  }}
                />
              ) : (
                <>
                  <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-muted">
                      {party.length} character{party.length === 1 ? "" : "s"} from DDB
                    </p>
                    <Button variant="secondary" onClick={() => setShowDdbImport((v) => !v)}>
                      {showDdbImport ? "Cancel" : "Re-import"}
                    </Button>
                  </div>
                  {showDdbImport && (
                    <DdbPartySetup
                      campaignId={campaignId}
                      onComplete={() => {
                        setShowDdbImport(false);
                        qc.invalidateQueries({ queryKey: ["characters", campaignId] });
                      }}
                    />
                  )}
                  <PartyCompactGrid
                    characters={party}
                    className="min-h-0 flex-1"
                    refreshingId={refreshingId}
                    onRefresh={async (ch) => {
                      setRefreshingId(ch.id);
                      try {
                        await api.refreshCharacter(campaignId!, ch.id);
                        qc.invalidateQueries({
                          queryKey: ["characters", campaignId],
                        });
                      } finally {
                        setRefreshingId(null);
                      }
                    }}
                  />
                </>
              )}
            </div>
          )}

          {tab === "sessions" && (
            <div className="mx-auto max-w-2xl space-y-4">
              <Card>
                <CardTitle className="flex items-center gap-2">
                  <ScrollText className="h-4 w-4" />
                  Start session
                </CardTitle>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                  <Input
                    placeholder="Session title (optional)"
                    value={sessionTitle}
                    onChange={(e) => setSessionTitle(e.target.value)}
                  />
                  <Button
                    className="shrink-0"
                    disabled={newSession.isPending || needsParty}
                    onClick={() => newSession.mutate()}
                  >
                    <Mic className="h-4 w-4" />
                    New session
                  </Button>
                </div>
                {needsParty && (
                  <p className="mt-2 text-sm text-muted">Import party first.</p>
                )}
              </Card>
              <div className="space-y-2">
                {sessionList.map((s) => (
                  <Link
                    key={s.id}
                    to={`/campaigns/${campaignId}/sessions/${s.id}`}
                    className="flex items-center justify-between rounded-xl border border-border bg-surface-raised/60 px-4 py-3 no-underline transition hover:border-gold/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-parchment">
                        {s.title ?? "Session"}
                      </span>
                      <Badge tone={s.status === "active" ? "moss" : "muted"}>
                        {s.status}
                      </Badge>
                    </div>
                    <span className="text-sm text-gold">
                      {s.status === "active" ? "Live →" : "Open →"}
                    </span>
                  </Link>
                ))}
                {sessionList.length === 0 && (
                  <p className="text-center text-sm text-muted">No sessions yet.</p>
                )}
              </div>
            </div>
          )}

          {tab === "brief" && campaign.data && (
            <div className="mx-auto max-w-3xl">
              <CampaignAiBrief campaignId={campaignId} campaign={campaign.data} />
            </div>
          )}

          {tab === "lore" && (
            <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-2">
              <Card>
                <CardTitle>Add lore</CardTitle>
                <div className="mt-4 space-y-3">
                  <div>
                    <Label>Title</Label>
                    <Input
                      value={loreTitle}
                      onChange={(e) => setLoreTitle(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Content</Label>
                    <Textarea
                      placeholder="NPCs, locations, factions…"
                      value={loreContent}
                      onChange={(e) => setLoreContent(e.target.value)}
                    />
                  </div>
                  <Button
                    disabled={
                      !loreTitle.trim() || !loreContent.trim() || addLore.isPending
                    }
                    onClick={() => addLore.mutate()}
                  >
                    Save lore
                  </Button>
                </div>
              </Card>
              <div className="space-y-3">
                {lore.data?.map((doc) => (
                  <Card key={doc.id}>
                    <h3 className="font-display text-gold">{doc.title}</h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-parchment/90">
                      {doc.content}
                    </p>
                  </Card>
                ))}
                {lore.data?.length === 0 && (
                  <p className="text-sm text-muted">No lore documents yet.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </WorkspaceLayout>
    </div>
  );
}
