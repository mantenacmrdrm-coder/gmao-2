# Mini-GMAO - Gestion de Maintenance Assistée par Ordinateur

## Vue d'ensemble
Application complète de gestion de maintenance pour suivre le parc d'engins et planifier les interventions. Les entretiens sont programmés automatiquement pour 2026-2028 selon les règles définies dans Param.csv.

✨ **Fonctionnalité nouvelle** : Calendrier des entretiens programmés (42,676 entrées pour 227 engins × 3 ans)

## État actuel
✅ Application entièrement fonctionnelle
✅ Affichage des données CSV avec recherche par matricule
✅ Recherche globale dans tous les fichiers CSV simultanément
✅ **Calendrier des entretiens programmés pour 2026-2028**
✅ Backend API FastAPI opérationnel
✅ Frontend Streamlit sur port 5000
⚠️ Base de données PostgreSQL optionnelle pour les alertes

## Architecture

### Backend (FastAPI)
- **Port**: 8000 (localhost)
- **Fichier**: `main.py`
- **API Endpoints**:
  - GET /assets - Liste des engins
  - POST /assets - Ajouter un engin
  - GET /alerts - Alertes (nécessite PostgreSQL)
  - PUT /jobs/{id}/done - Marquer un job comme terminé

### Frontend (Streamlit)
- **Port**: 5000 (0.0.0.0)
- **Fichier**: `dashboard.py`
- **Pages**:
  - 🔎 Recherche globale - Chercher un matricule dans tous les CSV
  - 📊 Données CSV - Voir chaque fichier avec recherche
  - 📅 Entretiens programmés - **NOUVEAU** - Calendrier complet 2026-2028
  - 🔔 Alertes - Maintenance à venir (nécessite PostgreSQL)
  - ✅ Actions - Gestion des interventions

### Scheduler
- **Fichier**: `maintenance_scheduler.py`
- **Logique**:
  - Parse Param.csv pour extraire les règles d'entretien
  - Génère l'historique pour 2026-2028
  - Gère les priorités : Changement > Nettoyage > Contrôle

## Règles d'entretien (depuis Param.csv)
- **"C" - Contrôle**: Vérifications fréquentes (huile, pneus, batterie, etc.)
- **"N" - Nettoyage**: Maintenance intermédiaire (filtres, rotules, etc.)
- **"CH" - Changement**: Interventions complètes (vidange, remplacement, etc.)

### Priorités
Si plusieurs entretiens le même jour:
1. CH (Changement) prime sur N et C
2. N (Nettoyage) prime sur C
3. C (Contrôle) en dernier

## Fichiers CSV
- `import/MATRICE.csv` - Parc d'engins (227 véhicules)
- `import/VIDANGE.csv` - Historique des vidanges
- `import/SUIVI_CURATIF.csv` - Interventions curatives
- `import/Param.csv` - Règles d'entretien par intervalle

## Configuration requise

### 1. Application CSV (Fonctionnelle immédiatement)
L'application fonctionne complètement avec les fichiers CSV:
- Visualisation des données
- Recherche multi-fichier
- **Calendrier des entretiens programmés**

### 2. Base de données PostgreSQL (Optionnel)
Pour les alertes en temps réel:
1. Cliquer sur "Database" dans le panneau de gauche
2. Sélectionner "Create a database"
3. Les variables d'environnement seront configurées automatiquement
4. Initialiser les tables:
   ```bash
   psql $DATABASE_URL < schema.sql
   ```
5. Importer les données historiques:
   ```bash
   python import_csv.py
   ```

## Utilisation

### Démarrage automatique
```bash
# Backend API sur port 8000
uvicorn main:app --host localhost --port 8000

# Frontend Streamlit sur port 5000
streamlit run dashboard.py
```

### Accès
- Frontend: http://localhost:5000 (s'ouvre automatiquement)

### Exemples d'utilisation

**Recherche globale par matricule**:
1. Aller dans "🔎 Recherche globale"
2. Entrer un matricule (ex: "041-01")
3. Voir tous les résultats dans tous les fichiers

**Voir le calendrier d'entretiens**:
1. Aller dans "📅 Entretiens programmés"
2. Filtrer par année (2026, 2027, 2028)
3. Filtrer par type (Contrôle, Nettoyage, Changement)
4. Rechercher par matricule d'engin
5. Télécharger les résultats

## Dépendances Python
```
fastapi>=0.121.3
pandas>=2.3.3
psycopg2-binary>=2.9.11
requests>=2.32.5
sqlmodel>=0.0.27
streamlit>=1.51.0
uvicorn>=0.38.0
```

## Structure du projet
```
.
├── main.py                    # API FastAPI
├── dashboard.py               # Interface Streamlit
├── maintenance_scheduler.py   # Planification automatique
├── import_csv.py              # Import données PostgreSQL
├── schema.sql                 # Structure DB PostgreSQL
├── seed.sql                   # Données d'exemple
├── .streamlit/
│   └── config.toml            # Configuration Streamlit
├── import/
│   ├── MATRICE.csv            # Parc d'engins
│   ├── VIDANGE.csv            # Historique vidanges
│   ├── SUIVI_CURATIF.csv      # Interventions
│   └── Param.csv              # Règles d'entretien
└── .gitignore
```

## Fonctionnalités

### ✅ Implémentées
- Affichage des données CSV
- Recherche par matricule dans tous les fichiers
- Génération du calendrier d'entretiens (2026-2028)
- Filtrage par année, type, matricule
- Export des données en CSV
- API FastAPI complète

### 🔜 Futures (avec PostgreSQL)
- Suivi des alertes de maintenance
- Historique des interventions
- Gestion des statuts (planifié, en retard, fait)
- Rapports et statistiques

## Modifications (23 Nov 2025)
- ✅ Setup complet pour Replit
- ✅ Ajout de la recherche globale
- ✅ **Implémentation du calendrier d'entretiens programmés (2026-2028)**
- ✅ Support des variables d'environnement PostgreSQL
- ✅ Configuration des workflows automatiques
- ✅ Interface Streamlit multi-pages

## Notes techniques

### Parsing du Param.csv
Le fichier Param.csv utilise une structure complexe:
- Colonnes 7, 30, 90, 180, 360 = intervalles en jours
- "*" = entretien à cet intervalle
- "C", "N", "CH" = type d'entretien
- Colonnes "Contrôle", "Nettoyage.1", "Changement.1" = intervalles exacts

Exemple:
```
7;*;;;*;Frein;C;;CH;;7;;;;360
```
= Entretien "Frein" avec:
- Contrôle tous les 7 jours
- Changement tous les 360 jours
