-- Per-session viewpoint: DM chronicle vs player-character POV recaps
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS viewer_mode TEXT NOT NULL DEFAULT 'dm',
    ADD COLUMN IF NOT EXISTS viewer_character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS recaps_by_viewer JSONB NOT NULL DEFAULT '{}';

ALTER TABLE sessions
    DROP CONSTRAINT IF EXISTS sessions_viewer_mode_check;

ALTER TABLE sessions
    ADD CONSTRAINT sessions_viewer_mode_check
    CHECK (viewer_mode IN ('dm', 'player'));
