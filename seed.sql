-- ===========================================
-- Données initiales (à adapter avec tes CSV)
-- ===========================================

-- Types de maintenance
INSERT INTO maint_types (code, label) VALUES
('preventive', 'Préventif'),
('corrective', 'Curatif');

-- Exemple d'engins (remplace par tes données)
INSERT INTO assets (name, reg_number, purchase_dt, km, running_h, meta) VALUES
('Chariot élévateur Hyster H2.5', 'CH-H25-001', '2022-03-15', 12450, 850, '{"type": "chariot", "motorisation": "diesel"}'),
('Nacelle Genie Z-45', 'NA-G45-002', '2021-07-20', 9800, 620, '{"type": "nacelle", "motorisation": "electrique"}');

-- Programmes d'entretien
INSERT INTO maint_plans (asset_id, maint_type_id, every_hours, every_months, tolerance_days, checklist_json, next_due_dt) VALUES
(1, 1, 250, NULL, 30, '["Vérifier niveau huile", "Contrôler pression pneus", "Graisser points d''usure"]', CURRENT_DATE + INTERVAL '3 months'),
(2, 1, NULL, 6, 30, '["Vérifier batterie", "Tester fonctionnement sécurité", "Inspecter structure"]', CURRENT_DATE + INTERVAL '2 months');