-- Website Revamp tracking. One row per store being revamped, plus a per-page
-- per-element checklist. Read by the "Website Revamp" dashboard tab.

CREATE TABLE IF NOT EXISTS revamp_stores (
    id              SERIAL PRIMARY KEY,
    prefix          VARCHAR(40) UNIQUE NOT NULL,   -- matches config SHOPIFY_STORE_PREFIXES
    store_name      VARCHAR(120),
    domain          VARCHAR(120),
    live_theme_id   BIGINT,
    live_theme_name VARCHAR(200),
    draft_theme_id  BIGINT,
    draft_theme_name VARCHAR(200),
    preview_url     TEXT,                            -- ?preview_theme_id=... link
    editor_url      TEXT,                            -- admin theme editor link
    status          VARCHAR(40) DEFAULT 'pending',   -- pending|duplicated|audited|building|review|done
    current_activity TEXT,                           -- human-readable "what's happening now"
    current_page    VARCHAR(40),                     -- which page the work is on
    last_audited_at TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revamp_checklist (
    id              SERIAL PRIMARY KEY,
    store_prefix    VARCHAR(40) NOT NULL REFERENCES revamp_stores(prefix) ON DELETE CASCADE,
    page            VARCHAR(40) NOT NULL,            -- home|collection|product|cart
    element         VARCHAR(40) NOT NULL,            -- banner|category_cards|featured_carousel|vertical_grid
    status          VARCHAR(20) DEFAULT 'missing',   -- found|missing|planned|building|done
    evidence        TEXT,                            -- what the audit matched on
    template_key    VARCHAR(120),                    -- which template drives the page
    note            TEXT,                            -- agent's plan / notes for this element
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (store_prefix, page, element)
);

CREATE INDEX IF NOT EXISTS idx_revamp_checklist_store ON revamp_checklist(store_prefix);

-- Append-only activity log so the tab can show "what the agent did / is doing".
CREATE TABLE IF NOT EXISTS revamp_activity (
    id              SERIAL PRIMARY KEY,
    store_prefix    VARCHAR(40) NOT NULL,
    page            VARCHAR(40),
    message         TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revamp_activity_store ON revamp_activity(store_prefix, created_at DESC);
