-- Additive session chronicle (journal entries per viewpoint)
CREATE TABLE IF NOT EXISTS session_chronicle_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    viewer_key TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS session_chronicle_session_viewer_ts
    ON session_chronicle_entries(session_id, viewer_key, created_at);
