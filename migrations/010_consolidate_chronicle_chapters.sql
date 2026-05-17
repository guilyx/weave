-- Merge legacy one-row-per-agent-tick chronicle rows into ~30-STT chapters.
-- Migration 009 assigned chapter_index = row_number (101 ticks → 101 "chapters").

BEGIN;

CREATE TEMP TABLE _chronicle_merged ON COMMIT DROP AS
WITH entry_stats AS (
    SELECT
        e.id,
        e.session_id,
        e.viewer_key,
        e.body,
        e.source,
        e.created_at,
        COALESCE(e.stt_to, 0) AS row_stt_to,
        ROW_NUMBER() OVER (
            PARTITION BY e.session_id, e.viewer_key
            ORDER BY e.created_at ASC
        ) AS rn,
        COUNT(*) OVER (PARTITION BY e.session_id, e.viewer_key) AS entry_cnt,
        (
            SELECT COUNT(*)::int
            FROM session_events ev
            WHERE ev.session_id = e.session_id
              AND ev.event_type = 'transcript'
        ) AS stt_total
    FROM session_chronicle_entries e
),
with_chapter AS (
    SELECT
        es.*,
        GREATEST(
            1,
            CASE
                WHEN es.row_stt_to > 0 THEN ((es.row_stt_to - 1) / 30) + 1
                ELSE (
                    (es.rn - 1) / GREATEST(
                        1,
                        (
                            es.entry_cnt
                            + GREATEST(1, (es.stt_total + 29) / 30)
                            - 1
                        ) / GREATEST(1, (es.stt_total + 29) / 30)
                    )
                ) + 1
            END
        )::int AS new_chapter
    FROM entry_stats es
)
SELECT
    session_id,
    viewer_key,
    new_chapter AS chapter_index,
    ((new_chapter - 1) * 30 + 1) AS stt_from,
    LEAST(new_chapter * 30, GREATEST(1, MAX(stt_total))) AS stt_to,
    STRING_AGG(body, E'\n\n' ORDER BY created_at) AS body,
    'agent' AS source,
    MIN(created_at) AS created_at
FROM with_chapter wc
GROUP BY session_id, viewer_key, new_chapter;

DELETE FROM session_chronicle_entries;

INSERT INTO session_chronicle_entries (
    session_id, viewer_key, chapter_index, stt_from, stt_to, body, source, created_at
)
SELECT
    session_id,
    viewer_key,
    chapter_index,
    stt_from,
    stt_to,
    body,
    source,
    created_at
FROM _chronicle_merged;

COMMIT;
