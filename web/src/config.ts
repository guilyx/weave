/** Client-side mic chunk length (ms). Override with VITE_AUDIO_CHUNK_MS in .env */
const raw = Number(import.meta.env.VITE_AUDIO_CHUNK_MS ?? "4000");
export const audioChunkMs = Number.isFinite(raw) && raw >= 1000 && raw <= 60000 ? raw : 4000;
