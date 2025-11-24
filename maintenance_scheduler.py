# maintenance_scheduler.py → VERSION FINALE AVEC EXCLUSIONS PAR CATÉGORIE
import pandas as pd
from datetime import datetime, timedelta


class MaintenanceScheduler:
    # === Liste officielle des 22 opérations (ordre respecté) ===
    ALL_OPERATIONS = [
        "Niveau d'huile du carter", "Etanchéité de tous les circuits", "Frein",
        "courroie", "Filtre à huile", "Vidanger le carter moteur",
        "Filtre à air", "Filtre carburant", "chaine", "soupape",
        "Graissage général", "moyeu de roue", "pneu", "boite de vitesse",
        "cardan", "embrayage", "circuit hydraulique", "pompe hydraulique",
        "Filtre hydraulique", "Réservoir hydraulique", "alternateur",
        "batterie", "Faisceaux électriques"
    ]

    # === Dictionnaire d'exclusions (exactement comme ton VBA, mais en Python) ===
    EXCLUSIONS = {
        "geg": [
            "frein", "chaine", "pneu", "moyeu de roue", "graissage général",
            "boite de vitesse", "cardan", "embrayage", "circuit hydraulique",
            "pompe hydraulique", "filtre hydraulique", "réservoir hydraulique",
            "faisceaux électriques"
        ],
        "air comprime": [
            "frein", "chaine", "pneu", "moyeu de roue", "graissage général",
            "boite de vitesse", "cardan", "embrayage", "circuit hydraulique",
            "pompe hydraulique", "faisceaux électriques"
        ],
        "leger": [
            "graissage général", "circuit hydraulique", "pompe hydraulique",
            "filtre hydraulique", "réservoir hydraulique",
            "faisceaux électriques"
        ],
        "trans/marchandise 1": [
            "niveau d'huile du carter", "etanchéité des circuits", "courroie",
            "filtre à huile", "vidanger le carter moteur", "filtre à air",
            "filtre carburant", "chaine", "soupape", "boite de vitesse",
            "cardan", "embrayage", "circuit hydraulique", "pompe hydraulique",
            "filtre hydraulique", "réservoir hydraulique", "alternateur",
            "batterie", "faisceaux électriques"
        ],
        "trans et v, speciaux 1": [
            "niveau d'huile du carter", "etanchéité des circuits", "courroie",
            "filtre à huile", "vidanger le carter moteur", "filtre à air",
            "filtre carburant", "chaine", "soupape", "boite de vitesse",
            "cardan", "embrayage", "circuit hydraulique", "pompe hydraulique",
            "filtre hydraulique", "réservoir hydraulique", "alternateur",
            "batterie", "faisceaux électriques"
        ],
        "trans/personnel": [
            "niveau d'huile du carter", "circuit hydraulique",
            "pompe hydraulique", "filtre hydraulique", "réservoir hydraulique",
            "faisceaux électriques"
        ],
        "trans/benne.r": [
            "embrayage", "chaine", "boite de vitesse", "alternateur",
            "faisceaux électriques"
        ]
    }

    TYPE_MAP = {'C': 'Contrôle', 'N': 'Nettoyage', 'CH': 'Changement'}
    PRIORITY = {'CH': 3, 'N': 2, 'C': 1}

    def __init__(self, param_csv="import/Param.csv"):
        self.param_df = pd.read_csv(param_csv,
                                    encoding='cp1252',
                                    sep=';',
                                    dtype=str).fillna('')
        self.rules = self._extract_rules()

    def _extract_rules(self):
        rules = []
        for _, row in self.param_df.iterrows():
            operation_raw = str(row.get('Opération « poste intervention »',
                                        '')).strip()
            if not operation_raw:
                continue

            operation_clean = operation_raw.split(' (')[0].strip().lower()

            # Trouver l'opération officielle correspondante
            matched_op = next(
                (op
                 for op in self.ALL_OPERATIONS if op.lower() in operation_clean
                 or operation_clean in op.lower()), None)
            if not matched_op:
                continue

            # Détection des intervalles avec *
            for col in ['7', '30', '90', '180', '360']:
                if str(row.get(col, '')).strip() == '*':
                    interval_days = int(col)

                    # Recherche du type C/N/CH
                    maint_type = None
                    for tcol in [
                            'Contrôler', 'Nettoyage', 'Nettoyage.1',
                            'Changement', 'Changement.1'
                    ]:
                        val = str(row.get(tcol, '')).strip()
                        if val in ['C', 'N', 'CH']:
                            maint_type = val
                            break

                    if maint_type:
                        rules.append({
                            'operation': matched_op,
                            'type': maint_type,
                            'type_name': self.TYPE_MAP[maint_type],
                            'interval_days': interval_days,
                            'priority': self.PRIORITY[maint_type]
                        })
        return rules

    def _is_excluded(self, operation, categorie):
        """Retourne True si l'opération est exclue pour cette catégorie"""
        if not categorie:
            return False
        cat_lower = categorie.strip().lower()

        for key, excluded_ops in self.EXCLUSIONS.items():
            if key in cat_lower:
                if any(ex.lower() in operation.lower() for ex in excluded_ops):
                    return True
        return False

    def generate_schedule_for_asset(self,
                                    asset_row,
                                    start_year=2026,
                                    end_year=2028):
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        results = []
        categorie = str(asset_row.get('categorie', '')).strip()

        for rule in self.rules:
            operation = rule['operation']

            # EXCLUSION PAR CATÉGORIE
            if self._is_excluded(operation, categorie):
                continue  # On saute cette opération pour cet engin

            current = start_date
            delta = timedelta(days=rule['interval_days'])

            while current <= end_date:
                results.append({
                    'matricule':
                    str(asset_row.get('matricule', '')).strip(),
                    'engin':
                    str(asset_row.get('designation', '')).strip(),
                    'catégorie':
                    categorie,
                    'date':
                    current.date(),
                    'année':
                    current.year,
                    'opération':
                    operation,
                    'type':
                    rule['type'],
                    'type_nom':
                    rule['type_name'],
                    'intervalle_jours':
                    rule['interval_days']
                })
                current += delta

        return results


def create_complete_maintenance_schedule(matrice_csv="import/MATRICE.csv",
                                         param_csv="import/Param.csv",
                                         start_year=2026,
                                         end_year=2028):
    matrice_df = pd.read_csv(matrice_csv, encoding='cp1252', sep=';')
    scheduler = MaintenanceScheduler(param_csv)

    print(f"{len(scheduler.rules)} règles de base détectées")
    all_results = []

    for _, asset in matrice_df.iterrows():
        all_results.extend(
            scheduler.generate_schedule_for_asset(asset, start_year, end_year))

    df = pd.DataFrame(all_results)
    print(
        f"Calendrier final généré : {len(df):,} entretiens programmés (exclusions appliquées)"
    )
    return df


# Test rapide
if __name__ == "__main__":
    df = create_complete_maintenance_schedule()
    print("\nExemple pour un engin GEG :")
    print(df[df['catégorie'].str.contains("GEG", case=False,
                                          na=False)]['opération'].unique())
    print("\nTotal opérations uniques :", df['opération'].nunique())
