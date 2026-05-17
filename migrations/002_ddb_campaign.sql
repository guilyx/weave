ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS ddb_campaign_id BIGINT;

ALTER TABLE characters ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS characters_campaign_primary_idx
    ON characters (campaign_id) WHERE is_primary = TRUE;
