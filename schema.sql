-- ===========================================
-- Mini-GMAO - Structure de base de données
-- ===========================================

-- Types de maintenance
CREATE TABLE IF NOT EXISTS maint_types (
    id   SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,      -- 'preventive' | 'corrective' | 'C' | 'N' | 'CH'
    label TEXT NOT NULL
);

-- Parc d'engins
CREATE TABLE IF NOT EXISTS assets (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT,               -- type d'engin (catégorie)
    reg_number  TEXT UNIQUE,
    purchase_dt DATE,
    km          INTEGER DEFAULT 0,
    running_h   INTEGER DEFAULT 0,
    meta        JSONB               -- données supplémentaires flexible
);

-- Programme d'entretien (le "quoi ?" et "quand ?")
CREATE TABLE IF NOT EXISTS maint_plans (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER REFERENCES assets(id),
    maint_type_id   INTEGER REFERENCES maint_types(id),
    every_km        INTEGER,           -- NULL si non applicable
    every_months    INTEGER,           -- NULL si non applicable
    every_hours     INTEGER,           -- NULL si applicable
    tolerance_days  INTEGER DEFAULT 30, -- ±1 mois par défaut
    checklist_json  JSONB,             -- ["vérifier l'huile", "vérifier les freins"]
    next_due_dt     DATE               -- prochaine échéance calculée
);

-- Interventions réalisées (le "fait")
CREATE TABLE IF NOT EXISTS maint_jobs (
    id            SERIAL PRIMARY KEY,
    plan_id       INTEGER REFERENCES maint_plans(id),
    due_dt        DATE NOT NULL,
    done_dt       DATE,               -- NULL tant que pas fait
    status        TEXT CHECK (status IN ('planned','done','overdue')),
    cost_labour   NUMERIC(8,2) DEFAULT 0,
    cost_parts    NUMERIC(8,2) DEFAULT 0,
    note          TEXT,
    pdf_report    TEXT                -- chemin vers le PDF signé
);

-- Table des alertes (historique des notifications)
CREATE TABLE IF NOT EXISTS alerts (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER REFERENCES maint_jobs(id),
    alert_dt    DATE NOT NULL,
    ack         BOOLEAN DEFAULT FALSE,
    sent_to     TEXT                 -- email ou notification id
);

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_jobs_status ON maint_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_due_dt ON maint_jobs(due_dt);
CREATE INDEX IF NOT EXISTS idx_plans_next_due ON maint_plans(next_due_dt);
