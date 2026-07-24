-- Home Offer Bridge — CRM schema (Postgres, local, next to n8n)
-- Matches backend/schema/lead.schema.json and workflow 01's Postgres nodes.
-- Run once as the homeofferbridge DB owner:  psql -U hob -d homeofferbridge -f 001_init_leads.sql

CREATE TABLE IF NOT EXISTS leads (
  lead_id                TEXT PRIMARY KEY,
  client_ref             TEXT UNIQUE,                 -- correlates lead + enrich events
  address                TEXT        NOT NULL,
  phone                  TEXT        NOT NULL,
  email                  TEXT,
  city                   TEXT        NOT NULL,
  state                  TEXT        NOT NULL,
  source                 TEXT        NOT NULL,         -- "state-slug/city-slug" attribution
  consent                BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  tier                   TEXT        NOT NULL DEFAULT 'NEW'
                           CHECK (tier IN ('NEW','HOT','WARM','COLD')),
  score                  INTEGER     CHECK (score BETWEEN 0 AND 100),
  status                 TEXT        NOT NULL DEFAULT 'new'
                           CHECK (status IN ('new','contacted','valuing','scheduled',
                                             'inspected','negotiating','under_contract',
                                             'closed','dead')),
  motivation             TEXT,
  timeline               TEXT,
  property_id            TEXT,
  offer_id               TEXT,
  deal_id                TEXT,
  audit                  JSONB       NOT NULL DEFAULT '[]'::jsonb,
  -- enrich event (condition + disclosures), upserted by client_ref
  self_rated_condition   TEXT        CHECK (self_rated_condition IN
                                     ('excellent','good','fair','poor','severe')),
  disclosed_issues       JSONB       NOT NULL DEFAULT '[]'::jsonb,
  disclosure_text        TEXT,
  disclosure_ack         BOOLEAN
);

-- Fast lookups the pipeline actually uses
CREATE INDEX IF NOT EXISTS idx_leads_client_ref ON leads (client_ref);
CREATE INDEX IF NOT EXISTS idx_leads_source     ON leads (source);
CREATE INDEX IF NOT EXISTS idx_leads_status     ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at DESC);

-- Optional: quick daily lead count view for eyeballing volume
CREATE OR REPLACE VIEW leads_by_day AS
  SELECT date_trunc('day', created_at) AS day,
         count(*)                       AS leads,
         count(*) FILTER (WHERE consent) AS consented
  FROM leads GROUP BY 1 ORDER BY 1 DESC;
