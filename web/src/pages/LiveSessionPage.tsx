import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, liveWebSocket, type ChronicleEntry } from "../api";
import { audioChunkMs } from "../config";
import { characterSnapshot } from "../lib/character";
import { CharacterSheetPanel } from "../components/character/CharacterSheetPanel";
import { SessionMainArea } from "../components/layout/SessionMainArea";
import { WorkspaceLayout } from "../components/layout/WorkspaceLayout";
import { SessionActivityFeed } from "../components/session/SessionActivityFeed";
import { SessionChatPanel } from "../components/session/SessionChatPanel";
import {
  dedupeChronicleChapters,
  SessionTablePanel,
} from "../components/session/SessionTablePanel";
import type { SessionTab } from "../components/session/SessionCenterTabs";
import type { SessionViewpoint } from "../components/session/SessionPartyRail";
import { SessionWorkspaceSidebar } from "../components/session/SessionWorkspaceSidebar";
import { Card, CardTitle } from "../components/ui/Card";

export default function LiveSessionPage() {
  const { campaignId, sessionId } = useParams<{
    campaignId: string;
    sessionId: string;
  }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<SessionTab>("recap");
  const [recap, setRecap] = useState("");
  const [chronicleEntries, setChronicleEntries] = useState<ChronicleEntry[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [agentPending, setAgentPending] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [viewpoint, setViewpoint] = useState<SessionViewpoint>({ mode: "dm" });
  const [sheetCharacterId, setSheetCharacterId] = useState<string | null>(null);
  const [refreshingCharId, setRefreshingCharId] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const intervalRef = useRef<number | null>(null);

  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api.getSession(sessionId!),
    enabled: !!sessionId,
  });

  const recapQuery = useQuery({
    queryKey: ["recap", sessionId],
    queryFn: () => api.getRecap(sessionId!),
    enabled: !!sessionId,
  });

  const party = useQuery({
    queryKey: ["characters", campaignId],
    queryFn: () => api.listCharacters(campaignId!),
    enabled: !!campaignId,
  });

  useEffect(() => {
    if (recapQuery.data) {
      setRecap(recapQuery.data.recap);
      setChronicleEntries(dedupeChronicleChapters(recapQuery.data.entries ?? []));
    }
    if (recapQuery.data?.viewer_mode === "player" && recapQuery.data.viewer_character_id) {
      setViewpoint({
        mode: "player",
        characterId: recapQuery.data.viewer_character_id,
      });
    } else if (recapQuery.data?.viewer_mode === "dm") {
      setViewpoint({ mode: "dm" });
    }
  }, [recapQuery.data]);

  useEffect(() => {
    const s = session.data;
    if (!s) return;
    if (s.viewer_mode === "player" && s.viewer_character_id) {
      setViewpoint({ mode: "player", characterId: s.viewer_character_id });
    } else {
      setViewpoint({ mode: "dm" });
    }
  }, [session.data?.viewer_mode, session.data?.viewer_character_id]);

  useEffect(() => {
    if (!sessionId) return;
    const ws = liveWebSocket(sessionId);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as {
          type?: string;
          recap?: string;
          items?: string[];
          meta?: { entry?: ChronicleEntry };
        };
        if (data.type === "chronicle_append" && data.meta?.entry) {
          const entry = data.meta.entry;
          setChronicleEntries((prev) => {
            const idx = prev.findIndex((e) => e.id === entry.id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = entry;
              return next;
            }
            const ch = entry.chapter_index ?? 0;
            const withoutDupChapter = prev.filter(
              (e) => (e.chapter_index ?? 0) !== ch || ch === 0,
            );
            return [...withoutDupChapter, entry].sort(
              (a, b) => (a.chapter_index ?? 0) - (b.chapter_index ?? 0),
            );
          });
          if (data.recap) setRecap(data.recap);
          setAgentPending(false);
        }
        if (data.type === "recap_update" && data.recap) {
          setRecap(data.recap);
          void qc.invalidateQueries({ queryKey: ["recap", sessionId] });
          setAgentPending(false);
        }
        if (data.type === "suggestions" && data.items) {
          setSuggestions(data.items);
          setAgentPending(false);
        }
        if (data.type === "activity") {
          const d = data as { kind?: string };
          if (d.kind === "agent_queued") setAgentPending(true);
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [sessionId, qc]);

  const startSession = useMutation({
    mutationFn: () => api.startSession(sessionId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["session", sessionId] });
      qc.invalidateQueries({ queryKey: ["activity", sessionId] });
    },
  });

  const endSession = useMutation({
    mutationFn: () => api.endSession(sessionId!),
    onSuccess: () => {
      stopMic();
      qc.invalidateQueries({ queryKey: ["session", sessionId] });
      qc.invalidateQueries({ queryKey: ["activity", sessionId] });
    },
  });

  const uploadChunk = useCallback(
    async (blob: Blob) => {
      if (!sessionId) return;
      try {
        await api.uploadAudio(sessionId, blob);
        void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
      } catch (e) {
        console.error(e);
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.includes("404") || /not found/i.test(msg)) {
          stopMic();
          void qc.invalidateQueries({ queryKey: ["session", sessionId] });
        }
      }
    },
    [sessionId, qc],
  );

  const startMic = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    recorderRef.current = recorder;
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) uploadChunk(e.data);
    };
    recorder.start();
    intervalRef.current = window.setInterval(() => {
      if (recorder.state === "recording") {
        recorder.stop();
        recorder.start();
      }
    }, audioChunkMs);
    setMicOn(true);
  };

  const stopMic = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    recorderRef.current = null;
    setMicOn(false);
  };

  useEffect(() => {
    if (session.isError) stopMic();
  }, [session.isError]);

  const speakRecap = async () => {
    if (!recap.trim()) return;
    try {
      const data = await api.speakTts(recap);
      const audio = new Audio(
        `data:${data.content_type};base64,${data.audio_base64}`,
      );
      await audio.play();
    } catch {
      /* optional */
    }
  };

  const exportMd = useMutation({
    mutationFn: () => api.exportMarkdown(sessionId!),
    onSuccess: (data) => {
      const blob = new Blob([data.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `session-${sessionId}.md`;
      a.click();
    },
  });

  const triggerRecap = useMutation({
    mutationFn: () => api.triggerAgent(sessionId!),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
    },
  });

  const setViewpointMutation = useMutation({
    mutationFn: (v: SessionViewpoint) =>
      api.setViewpoint(sessionId!, {
        mode: v.mode,
        character_id: v.mode === "player" ? v.characterId : null,
      }),
    onSuccess: (data) => {
      setRecap(data.recap);
      setChronicleEntries(dedupeChronicleChapters(data.entries ?? []));
      setAgentPending(true);
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["recap", sessionId] });
    },
  });

  const handleViewpointChange = (v: SessionViewpoint) => {
    setViewpoint(v);
    setViewpointMutation.mutate(v);
  };

  if (!campaignId || !sessionId) return null;

  if (session.isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <Card className="max-w-md border-red-900/40 bg-red-950/20">
          <CardTitle>Session not found</CardTitle>
          <p className="mt-3 text-sm text-parchment/90">
            Stale link or database reset — create a new session from the campaign.
          </p>
          <Link
            to={`/campaigns/${campaignId}`}
            className="mt-4 inline-flex items-center gap-1 text-sm text-gold no-underline hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            Campaign
          </Link>
        </Card>
      </div>
    );
  }

  const isActive = session.data?.status === "active";
  const isEnded = session.data?.status === "ended";
  const partyList = party.data ?? [];
  const sheetChar = partyList.find((c) => c.id === sheetCharacterId) ?? null;
  const viewpointChar =
    viewpoint.mode === "player"
      ? partyList.find((c) => c.id === viewpoint.characterId)
      : null;
  const pcName = viewpointChar ? characterSnapshot(viewpointChar).name : null;
  const recapLabel =
    viewpoint.mode === "dm" ? "Table chronicle" : `${pcName ?? "Character"}'s story`;
  const recapHint =
    viewpoint.mode === "dm"
      ? "Append-only journal for the table — each mic pass adds a timestamped entry."
      : `Your character's journal — what ${pcName ?? "you"} saw and did. Tips are for you as a player.`;
  const tipsTitle = viewpoint.mode === "dm" ? "Scene & DM notes" : "Ideas for your character";

  return (
    <WorkspaceLayout
      sidebar={
        <SessionWorkspaceSidebar
          campaignId={campaignId}
          title={session.data?.title ?? "Live session"}
          status={session.data?.status ?? "…"}
          isActive={!!isActive}
          isEnded={!!isEnded}
          micOn={micOn}
          party={partyList}
          viewpoint={viewpoint}
          sheetCharacterId={sheetCharacterId}
          onViewpointChange={handleViewpointChange}
          onOpenSheet={setSheetCharacterId}
          onStart={() => startSession.mutate()}
          onEnd={() => endSession.mutate()}
          onMicToggle={() => (micOn ? stopMic() : startMic())}
          onRecap={() => triggerRecap.mutate()}
          onExport={() => exportMd.mutate()}
          onSpeak={speakRecap}
          recapPending={triggerRecap.isPending}
          hasRecap={chronicleEntries.length > 0 || !!recap.trim()}
        />
      }
      aside={
        <SessionActivityFeed
          sessionId={sessionId}
          isActive={!!isActive}
          onRecapUpdate={setRecap}
          onSuggestions={setSuggestions}
          className="h-full rounded-none border-0 bg-transparent shadow-none"
        />
      }
    >
      <SessionMainArea
        tab={tab}
        sheetOpen={!!sheetChar}
        onTabChange={(t) => {
          setSheetCharacterId(null);
          setTab(t);
        }}
      >
        {sheetChar ? (
          <CharacterSheetPanel
            snapshot={characterSnapshot(sheetChar)}
            ddbCharacterId={sheetChar.ddb_character_id}
            isPrimary={!!sheetChar.is_primary}
            variant="dense"
            onRefresh={async () => {
              setRefreshingCharId(sheetChar.id);
              try {
                await api.refreshCharacter(campaignId, sheetChar.id);
                qc.invalidateQueries({ queryKey: ["characters", campaignId] });
              } finally {
                setRefreshingCharId(null);
              }
            }}
            refreshing={refreshingCharId === sheetChar.id}
          />
        ) : tab === "recap" ? (
          <SessionTablePanel
            sessionId={sessionId}
            entries={chronicleEntries}
            suggestions={suggestions}
            isActive={!!isActive}
            agentPending={agentPending}
            viewpointLabel={recapLabel}
            viewpointHint={recapHint}
            tipsTitle={tipsTitle}
          />
        ) : (
          <SessionChatPanel sessionId={sessionId} className="h-full min-h-0 w-full flex-1" />
        )}
      </SessionMainArea>
    </WorkspaceLayout>
  );
}
