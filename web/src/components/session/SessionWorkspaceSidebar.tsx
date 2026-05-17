import {
  ArrowLeft,
  Download,
  Mic,
  MicOff,
  Play,
  Sparkles,
  Square,
  Swords,
  Volume2,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { Character } from "../../api";
import { audioChunkMs } from "../../config";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { SessionPartyRail, type SessionViewpoint } from "./SessionPartyRail";

export function SessionWorkspaceSidebar({
  campaignId,
  title,
  status,
  isActive,
  isEnded,
  micOn,
  party,
  viewpoint,
  sheetCharacterId,
  onViewpointChange,
  onOpenSheet,
  onStart,
  onEnd,
  onMicToggle,
  onRecap,
  onExport,
  onSpeak,
  recapPending,
  hasRecap,
}: {
  campaignId: string;
  title: string;
  status: string;
  isActive: boolean;
  isEnded: boolean;
  micOn: boolean;
  party: Character[];
  viewpoint: SessionViewpoint;
  sheetCharacterId: string | null;
  onViewpointChange: (v: SessionViewpoint) => void;
  onOpenSheet: (characterId: string | null) => void;
  onStart: () => void;
  onEnd: () => void;
  onMicToggle: () => void;
  onRecap: () => void;
  onExport: () => void;
  onSpeak: () => void;
  recapPending?: boolean;
  hasRecap?: boolean;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 space-y-3 border-b border-border p-3">
        <Link
          to={`/campaigns/${campaignId}`}
          className="inline-flex items-center gap-1.5 text-sm text-muted no-underline hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Campaign
        </Link>
        <h1 className="truncate font-display text-xl font-semibold leading-tight text-parchment">
          {title}
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={isActive ? "moss" : "muted"}>
            {isActive && <Swords className="h-3.5 w-3.5" aria-hidden />}
            {status}
          </Badge>
          {micOn && (
            <span className="live-pulse inline-flex items-center gap-1.5 rounded-full border border-emerald-700/50 bg-moss/20 px-2.5 py-0.5 text-xs font-medium text-emerald-200">
              <Mic className="h-3 w-3" aria-hidden />
              {audioChunkMs / 1000}s chunks
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Button className="w-full" disabled={isActive} onClick={onStart}>
            <Play className="h-4 w-4" />
            Start
          </Button>
          <Button className="w-full" variant="secondary" disabled={isEnded} onClick={onEnd}>
            <Square className="h-4 w-4" />
            End
          </Button>
        </div>

        <Button
          className="w-full"
          variant={micOn ? "danger" : "secondary"}
          disabled={!isActive && !micOn}
          onClick={onMicToggle}
        >
          {micOn ? (
            <>
              <MicOff className="h-5 w-5" />
              Mute table
            </>
          ) : (
            <>
              <Mic className="h-5 w-5" />
              Listen at table
            </>
          )}
        </Button>

        <div className="grid grid-cols-3 gap-2">
          <Button
            className="flex-col gap-1 px-2 py-2.5 text-xs"
            variant="ghost"
            disabled={recapPending}
            onClick={onRecap}
            title="Run AI recap now"
          >
            <Sparkles className="h-5 w-5" />
            Recap
          </Button>
          <Button className="flex-col gap-1 px-2 py-2.5 text-xs" variant="ghost" onClick={onExport} title="Export markdown">
            <Download className="h-5 w-5" />
            Export
          </Button>
          <Button
            className="flex-col gap-1 px-2 py-2.5 text-xs"
            variant="ghost"
            disabled={!hasRecap}
            onClick={onSpeak}
            title="Read recap aloud"
          >
            <Volume2 className="h-5 w-5" />
            Speak
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col border-b border-border">
        <SessionPartyRail
          characters={party}
          viewpoint={viewpoint}
          sheetCharacterId={sheetCharacterId}
          onViewpointChange={onViewpointChange}
          onOpenSheet={onOpenSheet}
        />
      </div>

    </div>
  );
}
