PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS APP_META (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO APP_META(key, value) VALUES
    ('state_revision', '0'),
    ('schema_version', 'text-v01-p0-1');

CREATE TABLE IF NOT EXISTS AI_IDENTITY (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    role TEXT NOT NULL,
    core_identity TEXT NOT NULL,
    temperament TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS AI_STATE (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL UNIQUE REFERENCES AI_IDENTITY(id),
    curiosity REAL,
    social_interest REAL,
    engagement REAL,
    fatigue_like REAL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS MOOD_STATE (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL UNIQUE REFERENCES AI_IDENTITY(id),
    valence REAL,
    activation REAL,
    control REAL,
    last_updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS USER_PROFILE (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    stable_attributes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS CONVERSATION (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    user_profile_id TEXT NOT NULL REFERENCES USER_PROFILE(id),
    started_at TEXT NOT NULL,
    ended_at TEXT
);
CREATE INDEX IF NOT EXISTS IX_CONVERSATION_PARTICIPANTS
    ON CONVERSATION(ai_identity_id, user_profile_id, started_at);
CREATE TABLE IF NOT EXISTS MESSAGE (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES CONVERSATION(id),
    speaker TEXT NOT NULL CHECK(speaker IN ('user', 'assistant')),
    content TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('committed', 'delivering', 'delivery_partial', 'delivered', 'failed')),
    delivery_offset INTEGER NOT NULL DEFAULT 0 CHECK(delivery_offset >= 0),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK(speaker = 'user' OR status <> 'committed'),
    CHECK(speaker <> 'user' OR delivery_offset = 0)
);
CREATE INDEX IF NOT EXISTS IX_MESSAGE_CANONICAL
    ON MESSAGE(conversation_id, created_at, id);
CREATE TRIGGER IF NOT EXISTS TR_MESSAGE_APPEND_DELIVERY_ONLY
BEFORE UPDATE OF content, delivery_offset ON MESSAGE
WHEN OLD.speaker = 'assistant' AND (
    NEW.delivery_offset < OLD.delivery_offset
    OR substr(NEW.content, 1, length(OLD.content)) <> OLD.content
    OR NEW.delivery_offset <> length(NEW.content)
)
BEGIN
    SELECT RAISE(ABORT, 'assistant delivery content must be append-only and match its offset');
END;

CREATE TABLE IF NOT EXISTS RESPONSE_TRACE (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE REFERENCES MESSAGE(id),
    state_snapshot TEXT NOT NULL,
    model_config TEXT NOT NULL,
    prompt_context_summary TEXT NOT NULL,
    latency_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS MEMORY_CANDIDATE (
    id TEXT PRIMARY KEY,
    source_message_id TEXT NOT NULL REFERENCES MESSAGE(id),
    candidate_type TEXT NOT NULL,
    proposed_content TEXT NOT NULL,
    proposed_importance REAL,
    decision TEXT NOT NULL,
    decision_reason TEXT,
    evaluated_at TEXT
);
CREATE TABLE IF NOT EXISTS MEMORY_ITEM (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    memory_kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    importance REAL,
    status TEXT NOT NULL CHECK(status IN ('active', 'archived', 'superseded', 'soft_deleted')),
    retention_class TEXT,
    happened_at TEXT,
    created_at TEXT NOT NULL,
    last_recalled_at TEXT,
    last_mentioned_at TEXT,
    recall_count INTEGER NOT NULL DEFAULT 0 CHECK(recall_count >= 0),
    mention_count INTEGER NOT NULL DEFAULT 0 CHECK(mention_count >= 0)
);
CREATE INDEX IF NOT EXISTS IX_MEMORY_VISIBLE
    ON MEMORY_ITEM(ai_identity_id, status, importance, created_at);
CREATE TRIGGER IF NOT EXISTS TR_MEMORY_NO_SOFT_DELETE_RESURRECTION
BEFORE UPDATE OF status ON MEMORY_ITEM
WHEN OLD.status = 'soft_deleted' AND NEW.status <> 'soft_deleted'
BEGIN
    SELECT RAISE(ABORT, 'soft-deleted memory cannot be reactivated');
END;
CREATE TABLE IF NOT EXISTS MEMORY_EPISODE (
    memory_item_id TEXT PRIMARY KEY REFERENCES MEMORY_ITEM(id),
    event_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS MEMORY_CLAIM (
    memory_item_id TEXT PRIMARY KEY REFERENCES MEMORY_ITEM(id),
    subject_type TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_value TEXT NOT NULL,
    confidence REAL,
    claim_status TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT
);
CREATE TRIGGER IF NOT EXISTS TR_MEMORY_SUBTYPE_EXCLUSIVE_EPISODE
BEFORE INSERT ON MEMORY_EPISODE
WHEN EXISTS (SELECT 1 FROM MEMORY_CLAIM WHERE memory_item_id = NEW.memory_item_id)
BEGIN
    SELECT RAISE(ABORT, 'memory item may have only one v0.1 subtype');
END;
CREATE TRIGGER IF NOT EXISTS TR_MEMORY_SUBTYPE_EXCLUSIVE_CLAIM
BEFORE INSERT ON MEMORY_CLAIM
WHEN EXISTS (SELECT 1 FROM MEMORY_EPISODE WHERE memory_item_id = NEW.memory_item_id)
BEGIN
    SELECT RAISE(ABORT, 'memory item may have only one v0.1 subtype');
END;
CREATE TABLE IF NOT EXISTS MEMORY_EVIDENCE (
    id TEXT PRIMARY KEY,
    memory_item_id TEXT NOT NULL REFERENCES MEMORY_ITEM(id),
    message_id TEXT NOT NULL REFERENCES MESSAGE(id),
    evidence_type TEXT NOT NULL,
    support_weight REAL
);
CREATE TRIGGER IF NOT EXISTS TR_MEMORY_EVIDENCE_VISIBLE_SOURCE
BEFORE INSERT ON MEMORY_EVIDENCE
WHEN NOT EXISTS (
    SELECT 1 FROM MEMORY_ITEM mi
    WHERE mi.id = NEW.memory_item_id AND mi.status <> 'soft_deleted'
) OR NOT EXISTS (
    SELECT 1 FROM MESSAGE m
    WHERE m.id = NEW.message_id
      AND (m.speaker = 'user' AND m.status = 'committed'
           OR m.speaker = 'assistant' AND m.status IN ('delivery_partial', 'delivered'))
)
BEGIN
    SELECT RAISE(ABORT, 'evidence must reference a visible memory and canonical message');
END;
CREATE TABLE IF NOT EXISTS MEMORY_REVISION (
    id TEXT PRIMARY KEY,
    memory_item_id TEXT NOT NULL REFERENCES MEMORY_ITEM(id),
    revision_type TEXT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    reason TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS MEMORY_LIFECYCLE_EVENT (
    id TEXT PRIMARY KEY,
    memory_item_id TEXT NOT NULL REFERENCES MEMORY_ITEM(id),
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    reason_type TEXT,
    reason TEXT,
    confidence REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS SELF_OBSERVATION (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    source_message_id TEXT NOT NULL REFERENCES MESSAGE(id),
    observation_type TEXT NOT NULL,
    subject TEXT,
    description TEXT NOT NULL,
    spontaneity REAL,
    user_influence REAL,
    context_key TEXT,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS SELF_HYPOTHESIS (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    statement TEXT NOT NULL,
    confidence REAL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS HYPOTHESIS_EVIDENCE (
    id TEXT PRIMARY KEY,
    self_hypothesis_id TEXT NOT NULL REFERENCES SELF_HYPOTHESIS(id),
    self_observation_id TEXT NOT NULL REFERENCES SELF_OBSERVATION(id),
    polarity TEXT NOT NULL,
    evidence_weight REAL,
    independence_weight REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS SELF_HYPOTHESIS_REVISION (
    id TEXT PRIMARY KEY,
    self_hypothesis_id TEXT NOT NULL REFERENCES SELF_HYPOTHESIS(id),
    previous_confidence REAL,
    new_confidence REAL,
    previous_status TEXT,
    new_status TEXT,
    reason TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS SELF_MODEL_ITEM (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    source_hypothesis_id TEXT UNIQUE REFERENCES SELF_HYPOTHESIS(id),
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL,
    stability REAL,
    origin TEXT NOT NULL,
    status TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT
);
CREATE TABLE IF NOT EXISTS SELF_MODEL_EVIDENCE (
    id TEXT PRIMARY KEY,
    self_model_item_id TEXT NOT NULL REFERENCES SELF_MODEL_ITEM(id),
    self_observation_id TEXT NOT NULL REFERENCES SELF_OBSERVATION(id),
    support_weight REAL
);
CREATE TABLE IF NOT EXISTS USER_MODEL_ITEM (
    id TEXT PRIMARY KEY,
    user_profile_id TEXT NOT NULL REFERENCES USER_PROFILE(id),
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL,
    temporal_scope TEXT,
    status TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS USER_MODEL_EVIDENCE (
    id TEXT PRIMARY KEY,
    user_model_item_id TEXT NOT NULL REFERENCES USER_MODEL_ITEM(id),
    memory_claim_id TEXT NOT NULL REFERENCES MEMORY_CLAIM(memory_item_id),
    support_weight REAL
);
CREATE TABLE IF NOT EXISTS USER_HYPOTHESIS (
    id TEXT PRIMARY KEY,
    user_profile_id TEXT NOT NULL REFERENCES USER_PROFILE(id),
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    statement TEXT NOT NULL,
    confidence REAL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS USER_HYPOTHESIS_EVIDENCE (
    id TEXT PRIMARY KEY,
    user_hypothesis_id TEXT NOT NULL REFERENCES USER_HYPOTHESIS(id),
    memory_item_id TEXT NOT NULL REFERENCES MEMORY_ITEM(id),
    polarity TEXT NOT NULL,
    evidence_weight REAL
);

CREATE TABLE IF NOT EXISTS RELATIONSHIP (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    user_profile_id TEXT NOT NULL REFERENCES USER_PROFILE(id),
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(ai_identity_id, user_profile_id)
);
CREATE TABLE IF NOT EXISTS RELATIONSHIP_DIMENSION (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL REFERENCES RELATIONSHIP(id),
    dimension_type TEXT NOT NULL,
    value REAL NOT NULL,
    confidence REAL,
    stability REAL,
    updated_at TEXT NOT NULL,
    UNIQUE(relationship_id, dimension_type)
);
CREATE TABLE IF NOT EXISTS RELATIONSHIP_SIGNAL (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL REFERENCES RELATIONSHIP(id),
    source_episode_id TEXT REFERENCES MEMORY_EPISODE(memory_item_id),
    signal_type TEXT NOT NULL,
    strength REAL NOT NULL,
    reason TEXT,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS RELATIONSHIP_DIMENSION_EVIDENCE (
    id TEXT PRIMARY KEY,
    relationship_dimension_id TEXT NOT NULL REFERENCES RELATIONSHIP_DIMENSION(id),
    relationship_signal_id TEXT NOT NULL REFERENCES RELATIONSHIP_SIGNAL(id),
    support_weight REAL
);
CREATE TABLE IF NOT EXISTS APPRAISAL_EVENT (
    id TEXT PRIMARY KEY,
    source_message_id TEXT REFERENCES MESSAGE(id),
    source_memory_episode_id TEXT REFERENCES MEMORY_EPISODE(memory_item_id),
    pleasantness REAL,
    novelty REAL,
    relevance REAL,
    goal_alignment REAL,
    controllability REAL,
    cause_type TEXT,
    target_type TEXT,
    target_ref TEXT,
    created_at TEXT NOT NULL,
    CHECK(source_message_id IS NOT NULL OR source_memory_episode_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS EMOTION_EPISODE (
    id TEXT PRIMARY KEY,
    ai_identity_id TEXT NOT NULL REFERENCES AI_IDENTITY(id),
    appraisal_event_id TEXT NOT NULL REFERENCES APPRAISAL_EVENT(id),
    primary_type TEXT NOT NULL,
    optional_label TEXT,
    intensity REAL,
    target_type TEXT,
    target_ref TEXT,
    action_tendency TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    ended_at TEXT
);
CREATE TABLE IF NOT EXISTS AFFECT_STATE_EFFECT (
    id TEXT PRIMARY KEY,
    emotion_episode_id TEXT NOT NULL REFERENCES EMOTION_EPISODE(id),
    ai_state_id TEXT NOT NULL REFERENCES AI_STATE(id),
    state_dimension TEXT NOT NULL,
    delta REAL NOT NULL,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS MOOD_INFLUENCE (
    id TEXT PRIMARY KEY,
    emotion_episode_id TEXT NOT NULL REFERENCES EMOTION_EPISODE(id),
    mood_state_id TEXT NOT NULL REFERENCES MOOD_STATE(id),
    valence_delta REAL,
    activation_delta REAL,
    control_delta REAL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS TURN_RUN (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES CONVERSATION(id),
    user_message_id TEXT NOT NULL UNIQUE REFERENCES MESSAGE(id),
    assistant_message_id TEXT UNIQUE REFERENCES MESSAGE(id),
    turn_sequence INTEGER NOT NULL CHECK(turn_sequence > 0),
    status TEXT NOT NULL CHECK(status IN (
        'preparing', 'generating', 'streaming', 'completed',
        'completed_partial', 'failed_before_delivery', 'cancelled'
    )),
    state_revision INTEGER NOT NULL,
    transcript_revision INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    first_token_at TEXT,
    completed_at TEXT,
    terminal_reason TEXT,
    UNIQUE(conversation_id, turn_sequence)
);
CREATE INDEX IF NOT EXISTS IX_TURN_RUN_ACTIVE ON TURN_RUN(conversation_id, status);
CREATE TABLE IF NOT EXISTS TURN_EVENT_TRACE (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    truth_state TEXT NOT NULL,
    persistence_class TEXT NOT NULL,
    causation_event_id TEXT REFERENCES TURN_EVENT_TRACE(id),
    observed_at_mono_ns INTEGER NOT NULL,
    emitted_at_wall TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE(turn_run_id, sequence)
);
CREATE TABLE IF NOT EXISTS CANCELLATION_SCOPE (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL UNIQUE REFERENCES TURN_RUN(id),
    status TEXT NOT NULL CHECK(status IN ('active', 'cancelled', 'closed')),
    cancel_reason TEXT,
    cancelled_at TEXT
);
CREATE TABLE IF NOT EXISTS COMPONENT_ATTEMPT (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    cancellation_scope_id TEXT NOT NULL REFERENCES CANCELLATION_SCOPE(id),
    component TEXT NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running', 'succeeded', 'failed', 'cancelled', 'deferred')),
    failure_code TEXT,
    retryable INTEGER NOT NULL DEFAULT 0 CHECK(retryable IN (0, 1)),
    attempt_no INTEGER NOT NULL CHECK(attempt_no > 0),
    started_mono_ns INTEGER NOT NULL,
    ended_mono_ns INTEGER,
    deadline_mono_ns INTEGER,
    UNIQUE(turn_run_id, component, operation, attempt_no)
);
CREATE TABLE IF NOT EXISTS RETRIEVAL_RUN (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    conversation_id TEXT NOT NULL REFERENCES CONVERSATION(id),
    query_text TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    request_state_revision INTEGER NOT NULL,
    completion_state_revision INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ok', 'degraded', 'unavailable')),
    degraded_reasons TEXT NOT NULL,
    elapsed_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS RETRIEVAL_RESULT (
    id TEXT PRIMARY KEY,
    retrieval_run_id TEXT NOT NULL REFERENCES RETRIEVAL_RUN(id),
    source_kind TEXT NOT NULL CHECK(source_kind IN ('memory_item', 'raw_message')),
    source_ref TEXT NOT NULL,
    memory_item_id TEXT REFERENCES MEMORY_ITEM(id),
    message_id TEXT REFERENCES MESSAGE(id),
    source_class TEXT NOT NULL,
    source_time TEXT NOT NULL,
    temporal_role TEXT NOT NULL,
    source_status TEXT NOT NULL,
    content_for_context TEXT NOT NULL,
    evidence_refs TEXT NOT NULL,
    signals TEXT NOT NULL,
    final_rank INTEGER NOT NULL CHECK(final_rank > 0),
    privacy_class TEXT NOT NULL,
    CHECK((source_kind = 'memory_item' AND memory_item_id IS NOT NULL AND message_id IS NULL)
       OR (source_kind = 'raw_message' AND message_id IS NOT NULL AND memory_item_id IS NULL))
);
CREATE INDEX IF NOT EXISTS IX_RETRIEVAL_RESULT_RUN_RANK
    ON RETRIEVAL_RESULT(retrieval_run_id, final_rank);
CREATE TABLE IF NOT EXISTS CONTEXT_SNAPSHOT (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    retrieval_run_id TEXT REFERENCES RETRIEVAL_RUN(id),
    schema_version TEXT NOT NULL,
    state_revision INTEGER NOT NULL,
    transcript_revision INTEGER NOT NULL,
    input_truth TEXT NOT NULL,
    identity_version TEXT NOT NULL,
    persona_version TEXT NOT NULL,
    privacy_filter_version TEXT NOT NULL,
    token_budget_total INTEGER NOT NULL,
    estimated_tokens INTEGER NOT NULL,
    sections_json TEXT NOT NULL,
    selected_refs_json TEXT NOT NULL,
    omissions_json TEXT NOT NULL,
    context_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS MODEL_INVOCATION (
    id TEXT PRIMARY KEY,
    turn_run_id TEXT NOT NULL REFERENCES TURN_RUN(id),
    context_snapshot_id TEXT NOT NULL REFERENCES CONTEXT_SNAPSHOT(id),
    component_attempt_id TEXT NOT NULL UNIQUE REFERENCES COMPONENT_ATTEMPT(id),
    role TEXT NOT NULL,
    backend TEXT NOT NULL,
    model_id TEXT NOT NULL,
    blocking INTEGER NOT NULL CHECK(blocking IN (0, 1)),
    schema_version TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    ttft_ms INTEGER,
    duration_ms INTEGER,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    failure_code TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS DELIVERY_SPAN (
    id TEXT PRIMARY KEY,
    model_invocation_id TEXT NOT NULL REFERENCES MODEL_INVOCATION(id),
    assistant_message_id TEXT NOT NULL REFERENCES MESSAGE(id),
    char_start INTEGER NOT NULL CHECK(char_start >= 0),
    char_end INTEGER NOT NULL CHECK(char_end > char_start),
    delivery_basis TEXT NOT NULL,
    confidence_class TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE(assistant_message_id, char_start, char_end)
);
CREATE TABLE IF NOT EXISTS RETRIEVAL_EMBEDDING_CACHE (
    source_kind TEXT NOT NULL CHECK(source_kind IN ('memory_item', 'raw_message')),
    source_ref TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    model_id TEXT NOT NULL,
    embedding_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(source_kind, source_ref, text_hash, model_id)
);
