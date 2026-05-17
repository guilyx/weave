-- Chronicle chapters: one journal row per ~30 STT transcript lines (not per agent tick)
ALTER TABLE session_chronicle_entries
    ADD COLUMN IF NOT EXISTS chapter_index INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS stt_from INT,
    ADD COLUMN IF NOT EXISTS stt_to INT;

-- Legacy rows each had their own tick; give distinct chapter_index until new merge logic applies
WITH ordered AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY session_id, viewer_key
            ORDER BY created_at ASC
        ) AS rn
    FROM session_chronicle_entries
)
UPDATE session_chronicle_entries AS e
SET chapter_index = o.rn
FROM ordered AS o
WHERE e.id = o.id;

CREATE UNIQUE INDEX IF NOT EXISTS session_chronicle_session_viewer_chapter
    ON session_chronicle_entries (session_id, viewer_key, chapter_index);
