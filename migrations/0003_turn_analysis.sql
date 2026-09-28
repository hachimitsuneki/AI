PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS TURN_ANALYSIS (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    analyzer_version TEXT NOT NULL,
    attempt_no INTEGER NOT NULL DEFAULT 1,
    base_state_revision INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'pending', 'running', 'committed', 'rejected', 'stale', 'failed'
    )),
    input_snapshot_json TEXT NOT NULL,
    proposal_json TEXT,
    validation_json TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(turn_run_id, analyzer_version)
);
CREATE TABLE IF NOT EXISTS ANALYSIS_PROPOSAL (
    id TEXT PRIMARY KEY,
    turn_analysis_id TEXT NOT NULL REFERENCES TURN_ANALYSIS(id),
    proposal_type TEXT NOT NULL CHECK(proposal_type IN (
        'memory_candidate', 'self_observation', 'user_observation',
        'appraisal_candidate', 'emotion_candidate', 'relationship_signal'
    )),
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
    proposal_json TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reason_code TEXT,
    attempt_no INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ANALYSIS_COMMIT (
    id TEXT PRIMARY KEY,
    turn_analysis_id TEXT NOT NULL UNIQUE REFERENCES TURN_ANALYSIS(id),
    base_state_revision INTEGER NOT NULL,
    committed_state_revision INTEGER NOT NULL,
    mutation_summary_json TEXT NOT NULL,
    committed_at TEXT NOT NULL
);
