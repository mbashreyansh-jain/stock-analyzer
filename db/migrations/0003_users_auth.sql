-- People who can sign in, their sessions, invitations and an audit trail (decision D23).
-- Nobody can create an account without an invite from the admin.

CREATE TABLE users (
    id             bigserial PRIMARY KEY,
    email          text NOT NULL,
    name           text NOT NULL,
    password_hash  text NOT NULL,               -- Argon2id hash, never the password itself
    role           text NOT NULL CHECK (role IN ('admin', 'member')),
    is_active      boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    last_login_at  timestamptz
);
CREATE UNIQUE INDEX users_email_idx ON users (lower(email));

-- One row per signed-in browser. Only a SHA-256 hash of the cookie token is stored,
-- so a copy of the database cannot be used to sign in as anyone.
CREATE TABLE sessions (
    token_hash    text PRIMARY KEY,
    user_id       bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token    text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL,
    last_seen_at  timestamptz NOT NULL DEFAULT now(),
    user_agent    text,
    ip            text
);
CREATE INDEX sessions_user_idx ON sessions (user_id);

-- Invite links (kind 'invite') and password-reset links (kind 'reset') made by the admin.
-- Like sessions, only a hash of the link's token is stored.
CREATE TABLE invites (
    token_hash  text PRIMARY KEY,
    kind        text NOT NULL DEFAULT 'invite' CHECK (kind IN ('invite', 'reset')),
    email       text NOT NULL,
    role        text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    user_id     bigint REFERENCES users(id) ON DELETE CASCADE,   -- set for reset links
    created_by  bigint REFERENCES users(id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz,
    used_by     bigint REFERENCES users(id)
);

-- Failed sign-ins, used to slow down password guessing.
CREATE TABLE login_attempts (
    id     bigserial PRIMARY KEY,
    email  text NOT NULL,
    ip     text,
    at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_attempts_email_idx ON login_attempts (lower(email), at);
CREATE INDEX login_attempts_ip_idx ON login_attempts (ip, at);

-- Who did what: sign-ins, invites, blog publishing, account changes.
CREATE TABLE audit_log (
    id       bigserial PRIMARY KEY,
    user_id  bigint REFERENCES users(id) ON DELETE SET NULL,
    action   text NOT NULL,
    detail   jsonb NOT NULL DEFAULT '{}'::jsonb,
    at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_at_idx ON audit_log (at);
