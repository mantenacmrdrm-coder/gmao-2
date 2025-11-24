#!/usr/bin/env python3
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from datetime import date, timedelta
import os
import sys
import re
import time

# ===========================================
# Configuration DB
# ===========================================
# Parse DATABASE_URL if available, otherwise use defaults
import urllib.parse

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gmao_user:gmao_password@localhost:5432/gmao_db")
parsed = urllib.parse.urlparse(DATABASE_URL)

DB_CONFIG = {
    "host": parsed.hostname or "localhost",
    "database": parsed.path.lstrip('/') if parsed.path else "gmao_db",
    "user": parsed.username or "gmao_user",
    "password": parsed.password or "gmao_password",
    "port": parsed.port or 5432
}
CSV_FOLDER = "./import"
FILES_FOLDER = os.path.join(CSV_FOLDER, "files")

# ===========================================
# Attendre PostgreSQL
# ===========================================
def wait_for_postgres():
    print("⏳ Attente de PostgreSQL...")
    for i in range(30):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            print("✅ PostgreSQL est prêt !")
            return True
        except:
            time.sleep(1)
    print("❌ PostgreSQL ne répond pas après 30s")
    sys.exit(1)

wait_for_postgres()

# ===========================================
# Connexion DB
# ===========================================
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("✅ Connecté à PostgreSQL")
except Exception as e:
    print(f"❌ Erreur de connexion: {e}")
    sys.exit(1)

PRIORITY_MAP = {'CH': 3, 'N': 2, 'C': 1}

def import_matrice():
    print("\n📦 Importation MATRICE.csv...")
    
    try:
        df = pd.read_csv(
            os.path.join(CSV_FOLDER, "MATRICE.csv"),
            encoding='cp1252',
            sep=';'
        )
    except FileNotFoundError:
        print("❌ MATRICE.csv non trouvé !")
        return
    
    for idx, row in df.iterrows():
        try:
            matricule = str(row['matricule']).strip()
            
            meta_json = Json({
                "marque": str(row.get('marque', '')),
                "annee": str(row.get('annee', '')),
                "pneumatique": str(row.get('pneumatique', '')),
                "qte_vidange": str(row.get('qte_vidange', ''))
            })
            
            cur.execute("""
                INSERT INTO assets (id, name, type, reg_number, km, running_h, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    km = EXCLUDED.km,
                    running_h = EXCLUDED.running_h,
                    meta = EXCLUDED.meta;
            """, (
                matricule,
                str(row['designation'])[:100],
                str(row['categorie']),
                str(row['matricule']),
                0, 0,
                meta_json
            ))
        except Exception as e:
            print(f"❌ Ligne {idx}: {e}")
            continue
    
    conn.commit()
    print(f"✅ {len(df)} engins importés")

def import_param():
    print("\n⚙️  Importation Param.csv...")
    
    try:
        df = pd.read_csv(
            os.path.join(CSV_FOLDER, "Param.csv"),
            encoding='cp1252',
            sep=';'
        )
    except FileNotFoundError:
        print("❌ Param.csv non trouvé !")
        return
    
    for op_code in ['C', 'N', 'CH']:
        cur.execute("""
            INSERT INTO maint_types (code, label) VALUES (%s, %s)
            ON CONFLICT (code) DO NOTHING;
        """, (op_code, {'C': 'Contrôle', 'N': 'Nettoyage', 'CH': 'Changement'}[op_code]))
    conn.commit()
    
    interval_cols = [col for col in df.columns if col.isdigit()]
    operation_cols = [col for col in df.columns if col in ['Contrôler', 'Nettoyage', 'Changement']]
    
    for idx, row in df.iterrows():
        operation_label = str(row.get('Opération « poste intervention »', '')).strip()
        if not operation_label or operation_label == 'nan':
            continue
        
        for interval_col in interval_cols:
            cell_value = str(row.get(interval_col, '')).strip()
            
            if cell_value in ['*', 'C', 'N', 'CH']:
                op_type = None
                for op_col in operation_cols:
                    op_code = str(row.get(op_col, '')).strip()
                    if op_code in ['C', 'N', 'CH']:
                        op_type = op_code
                        break
                
                if not op_type and cell_value in ['C', 'N', 'CH']:
                    op_type = cell_value
                
                if not op_type:
                    continue
                
                cur.execute("""
                    SELECT id FROM maint_plans
                    WHERE maint_type_id = (SELECT id FROM maint_types WHERE code = %s)
                    AND every_months = %s;
                """, (op_type, int(interval_col) // 30))
                
                if cur.fetchone():
                    continue
                
                checklist_json = Json([{"item": operation_label, "type": op_type}])
                
                cur.execute("""
                    INSERT INTO maint_plans (maint_type_id, every_months, tolerance_days, checklist_json)
                    VALUES (
                        (SELECT id FROM maint_types WHERE code = %s),
                        %s,
                        30,
                        %s
                    );
                """, (
                    op_type,
                    int(interval_col) // 30,
                    checklist_json
                ))
    
    conn.commit()
    print(f"✅ Logique Param.csv importée")

def import_vidange():
    print("\n🔧 Importation VIDANGE.csv...")
    
    try:
        df = pd.read_csv(
            os.path.join(CSV_FOLDER, "VIDANGE.csv"),
            encoding='cp1252',
            sep=';',
            parse_dates=['date_entretien'],
            dayfirst=True
        )
    except FileNotFoundError:
        print("❌ VIDANGE.csv non trouvé !")
        return
    
    for idx, row in df.iterrows():
        try:
            matricule = str(row['matricule']).strip()
            
            cur.execute("SELECT id, type FROM assets WHERE id = %s", (matricule,))
            asset = cur.fetchone()
            if not asset:
                print(f"⚠️ Asset inconnu: {matricule}")
                continue
            
            compteur = str(row['compteur_km_h']).replace(',', '').strip()
            km_realise = None
            heures_realisees = None
            try:
                valeur = int(float(compteur))
                if valeur < 50000 and 'engin' in str(asset[1]).lower():
                    heures_realisees = valeur
                else:
                    km_realise = valeur
            except:
                pass
            
            entretien = str(row.get('entretien', row.get('obs', 'VIDANGE'))).strip()
            
            cur.execute("""
                SELECT id FROM maint_plans 
                WHERE maint_type_id IN (SELECT id FROM maint_types WHERE code IN ('C','N','CH'))
                AND checklist_json::text ILIKE %s
            """, (f"%{entretien}%",))
            
            plan = cur.fetchone()
            if not plan:
                cur.execute("""
                    INSERT INTO maint_plans (asset_id, maint_type_id, every_months, tolerance_days, checklist_json)
                    VALUES (%s, (SELECT id FROM maint_types WHERE code='C'), 6, 30, %s)
                    RETURNING id;
                """, (matricule, Json([{"item": entretien, "type": "C"}])))
                plan = cur.fetchone()
            
            plan_id = plan[0] if plan else None
            
            cur.execute("""
                INSERT INTO maint_jobs (plan_id, due_dt, done_dt, status, note)
                VALUES (%s, %s, %s, 'done', %s);
            """, (
                plan_id,
                row['date_entretien'].strftime('%Y-%m-%d'),
                row['date_entretien'].strftime('%Y-%m-%d'),
                f"{entretien} | Compteur: {compteur} | Obs: {row.get('obs', '')}"
            ))
            
            if km_realise:
                cur.execute("UPDATE assets SET km = %s WHERE id = %s", (km_realise, matricule))
            elif heures_realisees:
                cur.execute("UPDATE assets SET running_h = %s WHERE id = %s", (heures_realisees, matricule))
            
        except Exception as e:
            print(f"❌ Ligne {idx}: {e}")
            continue
    
    conn.commit()
    print(f"✅ {len(df)} vidanges importées")

def import_curatif():
    print("\n🔨 Importation SUIVI_CURATIF.csv...")
    
    # 🔥 Debug : afficher les colonnes réelles
    try:
        df_preview = pd.read_csv(
            os.path.join(CSV_FOLDER, "SUIVI_CURATIF.csv"),
            encoding='cp1252',
            sep=';',
            nrows=3
        )
        print(f"Colonnes détectées: {list(df_preview.columns)}")
    except:
        pass
    
    try:
        df = pd.read_csv(
            os.path.join(CSV_FOLDER, "SUIVI_CURATIF.csv"),
            encoding='cp1252',
            sep=';',
            parse_dates=['date_entree', 'date_sortie'],
            dayfirst=True
        )
    except FileNotFoundError:
        print("❌ SUIVI_CURATIF.csv non trouvé !")
        return
    
    # Crée ou récupère le plan curatif
    plan_label = "Intervention curative"
    
    cur.execute("""
        SELECT id FROM maint_plans
        WHERE checklist_json->>0 ILIKE %s;
    """, (f"%{plan_label}%",))
    
    plan_existing = cur.fetchone()
    
    if plan_existing:
        plan_id = plan_existing[0]
        print(f"✅ Plan curatif existant ID: {plan_id}")
    else:
        cur.execute("""
            INSERT INTO maint_plans (maint_type_id, every_months, tolerance_days, checklist_json)
            VALUES ((SELECT id FROM maint_types WHERE code='CH'), NULL, 30, %s)
            RETURNING id;
        """, (Json([{"item": plan_label, "type": "CH"}]),))
        plan_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Plan curatif créé ID: {plan_id}")
    
    success = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            date_effectuee = row.get('date_sortie')
            if pd.isna(date_effectuee):
                date_effectuee = row.get('date_entree')
            
            if pd.isna(date_effectuee):
                print(f"⚠️ Ligne {idx}: date manquante")
                errors += 1
                continue
            
            cout = row.get('cout_total', 0)
            if pd.isna(cout):
                cout = 0
            
            cur.execute("""
                INSERT INTO maint_jobs (plan_id, due_dt, done_dt, status, cost_parts, note)
                VALUES (%s, %s, %s, 'done', %s, %s);
            """, (
                plan_id,
                date_effectuee.strftime('%Y-%m-%d'),
                date_effectuee.strftime('%Y-%m-%d'),
                cout,
                f"Panne: {row.get('panne_declatee','')}\nIntervenant: {row.get('intervenant','')}\nPieces: {row.get('pieces','')}"
            ))
            conn.commit()
            success += 1
            
        except Exception as e:
            print(f"❌ Ligne {idx}: {e}")
            conn.rollback()
            errors += 1
            continue
    
    print(f"✅ {success} lignes importées, {errors} erreurs")

# ==================== MAIN ====================
if __name__ == "__main__":
    os.makedirs(FILES_FOLDER, exist_ok=True)
    
    try:
        import_matrice()
        import_param()
        import_vidange()
        import_curatif()
        
        print("\n📅 Recalcul des prochaines échéances...")
        cur.execute("""
            UPDATE maint_plans p
            SET next_due_dt = (
                SELECT MAX(j.done_dt) + INTERVAL '1 day' * (p.every_months * 30)
                FROM maint_jobs j
                WHERE j.plan_id = p.id AND j.done_dt IS NOT NULL
            )
            WHERE p.every_months IS NOT NULL;
        """)
        conn.commit()
        
        print("\n✅✅✅ IMPORT TOTAL TERMINÉ AVEC SUCCÈS !")
        
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cur.close()
        conn.close()