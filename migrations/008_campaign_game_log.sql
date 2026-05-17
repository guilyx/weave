-- D&D Beyond campaign game log (rolls, etc.) synced via game-log-rest-live API
ALTER TABLE campaigns
    ADD COLUMN IF NOT EXISTS ddb_user_id BIGINT,
    ADD COLUMN IF NOT EXISTS game_log_synced_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS campaign_game_log_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    ddb_message_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, ddb_message_id)
);

CREATE INDEX IF NOT EXISTS campaign_game_log_campaign_ts
    ON campaign_game_log_entries (campaign_id, occurred_at DESC NULLS LAST);
