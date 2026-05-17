-- Running session narrative built from STT + agent (full context for AI).
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS story TEXT NOT NULL DEFAULT '';
