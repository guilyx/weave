const API_KEY = import.meta.env.VITE_WEAVE_API_KEY ?? "";

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) h["x-api-key"] = API_KEY;
  return h;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { ...headers(), ...init?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const body = err as { error?: string; detail?: string | { msg: string }[] };
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? body.detail.map((d) => d.msg).join(", ")
          : undefined;
    throw new Error(body.error ?? detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface Campaign {
  id: string;
  name: string;
  description: string | null;
  ai_brief: string | null;
  settings: unknown;
  created_at: string;
  updated_at: string;
}

export interface Character {
  id: string;
  campaign_id: string;
  ddb_character_id: number;
  snapshot: CharacterSnapshot;
  is_primary?: boolean;
  last_synced_at: string | null;
  created_at: string;
}

export interface DdbRosterEntry {
  ddb_character_id: number;
  name: string;
  level: number | null;
  class_summary: string | null;
  avatar_url?: string | null;
}

export interface ImportFailure {
  ddb_character_id: number;
  error: string;
}

export interface CharacterClass {
  name: string;
  level: number;
}

export interface CharacterItem {
  name: string;
  quantity: number;
  equipped: boolean;
  category?: string | null;
}

export interface CharacterFeature {
  name: string;
  source?: string | null;
}

export interface CharacterSpell {
  name: string;
  level?: number | null;
  prepared?: boolean | null;
}

export interface CharacterSnapshot {
  name: string;
  race: string;
  class_summary: string;
  classes?: CharacterClass[];
  abilities?: Record<string, { score: number; modifier: number }>;
  hit_points?: number | null;
  armor_class?: number | null;
  background?: string | null;
  speed?: number | null;
  alignment?: string | null;
  proficiency_bonus?: number | null;
  items?: CharacterItem[];
  features?: CharacterFeature[];
  spells?: CharacterSpell[];
  ddb_character_id?: number;
  avatar_url?: string | null;
  frame_avatar_url?: string | null;
  small_backdrop_avatar_url?: string | null;
  large_backdrop_avatar_url?: string | null;
  raw_source?: string;
}

export interface ChronicleEntry {
  id: string;
  session_id: string;
  viewer_key: string;
  body: string;
  source: string;
  created_at: string;
  chapter_index?: number;
  stt_from?: number;
  stt_to?: number;
}

export interface Session {
  id: string;
  campaign_id: string;
  status: string;
  title: string | null;
  started_at: string | null;
  ended_at: string | null;
  recap: string;
  viewer_mode?: "dm" | "player";
  viewer_character_id?: string | null;
  created_at: string;
}

export interface SessionEvent {
  id: string;
  session_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  ts: string;
}

export interface ActivityItem {
  id: string;
  kind: string;
  ts: string;
  title: string;
  body: string | null;
  meta?: Record<string, unknown>;
}

export interface SessionMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface LoreDoc {
  id: string;
  campaign_id: string;
  title: string;
  content: string;
  created_at: string;
}

export const api = {
  listCampaigns: () => request<Campaign[]>("/api/v1/campaigns"),
  createCampaign: (name: string, description?: string) =>
    request<Campaign>("/api/v1/campaigns", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  getCampaign: (id: string) => request<Campaign>(`/api/v1/campaigns/${id}`),
  updateCampaign: (
    id: string,
    body: { name?: string; description?: string; ai_brief?: string | null },
  ) =>
    request<Campaign>(`/api/v1/campaigns/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  fetchDdbRoster: (ddbCampaignId: number) =>
    request<DdbRosterEntry[]>(`/api/v1/ddb/campaigns/${ddbCampaignId}/roster`),
  fetchDdbCharacterSheet: (ddbCharacterId: number) =>
    request<CharacterSnapshot>(`/api/v1/ddb/characters/${ddbCharacterId}/sheet`),
  fetchDdbCharacterSheets: (ddbCharacterIds: number[]) =>
    request<CharacterSnapshot[]>("/api/v1/ddb/characters/sheets", {
      method: "POST",
      body: JSON.stringify({ ddb_character_ids: ddbCharacterIds }),
    }),
  importDdbParty: (
    campaignId: string,
    body: {
      ddb_campaign_id: number;
      ddb_character_ids: number[];
      primary_ddb_character_id?: number;
    },
  ) =>
    request<{ linked: Character[]; count: number; failed: ImportFailure[] }>(
      `/api/v1/campaigns/${campaignId}/import-ddb-party`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  listCharacters: (campaignId: string) =>
    request<Character[]>(`/api/v1/campaigns/${campaignId}/characters`),
  linkCharacter: (campaignId: string, ddb_character_id: number) =>
    request<Character>(`/api/v1/campaigns/${campaignId}/characters`, {
      method: "POST",
      body: JSON.stringify({ ddb_character_id }),
    }),
  refreshCharacter: (campaignId: string, characterId: string) =>
    request<Character>(
      `/api/v1/campaigns/${campaignId}/characters/${characterId}`,
      { method: "POST" },
    ),
  setPrimaryCharacter: (campaignId: string, characterId: string) =>
    request<Character>(
      `/api/v1/campaigns/${campaignId}/characters/${characterId}/set-primary`,
      { method: "POST" },
    ),

  listLore: (campaignId: string) =>
    request<LoreDoc[]>(`/api/v1/campaigns/${campaignId}/lore`),
  createLore: (campaignId: string, title: string, content: string) =>
    request<LoreDoc>(`/api/v1/campaigns/${campaignId}/lore`, {
      method: "POST",
      body: JSON.stringify({ title, content }),
    }),

  listSessions: (campaignId: string) =>
    request<Session[]>(`/api/v1/campaigns/${campaignId}/sessions`),
  createSession: (campaignId: string, title?: string) =>
    request<Session>(`/api/v1/campaigns/${campaignId}/sessions`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  getSession: (sessionId: string) =>
    request<Session>(`/api/v1/sessions/${sessionId}`),
  startSession: (sessionId: string) =>
    request<Session>(`/api/v1/sessions/${sessionId}/start`, { method: "POST" }),
  endSession: (sessionId: string) =>
    request<Session>(`/api/v1/sessions/${sessionId}/end`, { method: "POST" }),
  addNote: (sessionId: string, text: string) =>
    request<unknown>(`/api/v1/sessions/${sessionId}/notes`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  uploadAudio: async (sessionId: string, blob: Blob) => {
    const form = new FormData();
    form.append("audio", blob, "chunk.webm");
    const h: Record<string, string> = {};
    if (API_KEY) h["x-api-key"] = API_KEY;
    const res = await fetch(`/api/v1/sessions/${sessionId}/audio-chunks`, {
      method: "POST",
      headers: h,
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  getRecap: (sessionId: string) =>
    request<{
      recap: string;
      entries: ChronicleEntry[];
      viewer_mode?: "dm" | "player";
      viewer_character_id?: string | null;
      viewer_key?: string;
    }>(`/api/v1/sessions/${sessionId}/recap`),
  setViewpoint: (
    sessionId: string,
    body: { mode: "dm" | "player"; character_id?: string | null },
  ) =>
    request<{
      recap: string;
      entries: ChronicleEntry[];
      viewer_mode: "dm" | "player";
      viewer_character_id: string | null;
      agent_queued: boolean;
    }>(`/api/v1/sessions/${sessionId}/viewpoint`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  getTimeline: (sessionId: string) =>
    request<SessionEvent[]>(`/api/v1/sessions/${sessionId}/timeline`),
  getActivity: (sessionId: string, feed: "ai" | "notes" | "pipeline" | "full" | "chat" = "ai") =>
    request<ActivityItem[]>(
      `/api/v1/sessions/${sessionId}/activity?feed=${encodeURIComponent(feed)}`,
    ),
  listMessages: (sessionId: string) =>
    request<SessionMessage[]>(`/api/v1/sessions/${sessionId}/messages`),
  postMessage: (sessionId: string, content: string) =>
    request<{ reply: string }>(`/api/v1/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  triggerAgent: (sessionId: string) =>
    request<{ queued: boolean }>(`/api/v1/sessions/${sessionId}/agent-tick`, {
      method: "POST",
    }),
  exportMarkdown: (sessionId: string) =>
    request<{ markdown: string }>(`/api/v1/sessions/${sessionId}/export`),
  speakTts: (text: string) =>
    request<{ audio_base64: string; content_type: string }>("/api/v1/tts/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
};

export function liveWebSocket(sessionId: string): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return new WebSocket(`${proto}//${host}/api/v1/sessions/${sessionId}/live`);
}
