# 📊 DataPulse — Analyse de Ventes E-Commerce

Application web Flask pour l'analyse de fichiers Excel/CSV de ventes.

## 🚀 Installation rapide

```bash
# 1. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
python app.py
```

Ouvrez http://localhost:5000 dans votre navigateur.

## 📁 Structure du projet

```
analytics_app/
├── app.py              # Serveur Flask (routes & upload)
├── analytics.py        # Moteur Pandas (calculs & KPI)
├── requirements.txt    # Dépendances Python
├── templates/
│   ├── index.html      # Page d'upload (drag & drop)
│   └── dashboard.html  # Tableau de bord interactif
└── static/             # (pour CSS/JS additionnels)
```

## 📋 Format du fichier

Le fichier Excel/CSV doit contenir ces colonnes exactes :

| Colonne   | Type    | Exemple         |
|-----------|---------|-----------------|
| Date      | Date    | 15/01/2024      |
| Produit   | Texte   | Robe Fleurie    |
| Prix      | Nombre  | 250.00          |
| Quantité  | Nombre  | 2               |
| Ville     | Texte   | Casablanca      |
| Statut    | Texte   | Livré / Refusé  |

**Valeurs de Statut acceptées :** Livré, Refusé, Retourné, Annulé

Téléchargez un template exemple via le bouton sur la page d'accueil.

## 📊 KPIs calculés

- **Chiffre d'Affaires Global** — somme des ventes livrées
- **Volume de Commandes** — nombre total de transactions
- **Panier Moyen** — CA / nb commandes livrées
- **Taux de Livraison** — % commandes livrées / total

## 📈 Graphiques

- Évolution du CA (courbe temporelle)
- Top Villes (barres horizontales)
- Top 5 Produits (donut chart)
- Répartition des Statuts (pie chart)

## 🛠 Technologies

- **Backend** : Flask + Pandas + openpyxl
- **Frontend** : HTML/CSS/JS + Chart.js
- **Design** : Dark theme, Syne font, animations CSS
