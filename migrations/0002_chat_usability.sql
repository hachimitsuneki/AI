PRAGMA foreign_keys = ON;

ALTER TABLE MESSAGE
    ADD COLUMN reply_to_message_id TEXT REFERENCES MESSAGE(id);

CREATE INDEX IF NOT EXISTS IX_MESSAGE_REPLY_TO
    ON MESSAGE(reply_to_message_id);

UPDATE AI_IDENTITY
SET core_identity = '{"summary":"A curious, playful digital companion; clear, honest, and considerate."}',
    temperament = '{"curiosity":"somewhat high","playfulness":"somewhat high","assertiveness":"medium","mischievousness":"slight","humor":"occasional, situational"}',
    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
WHERE temperament = '{}'
  AND core_identity = '{"summary":"A text conversation partner. Reply clearly, honestly, and considerately."}';
