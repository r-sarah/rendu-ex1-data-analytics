"""Nettoyage de la table loss_rate.csv (taux de perte par article)."""
from pathlib import Path

import pandas as pd

# Chemins relatifs à la racine du repo (fonctionne quel que soit le dossier d'exécution)
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "loss_rate.csv"
CLEAN = ROOT / "data" / "clean" / "table_sarah.csv"

# 1. Lecture : utf-8-sig retire le caractère invisible (BOM) en début de fichier
df = pd.read_csv(RAW, encoding="utf-8-sig", dtype={"Item Code": str})
print(f"Lignes au départ : {len(df)}")

# 2. Noms de colonnes plus simples à manipuler
df = df.rename(columns={
    "Item Code": "item_code",
    "Item Name": "item_name",
    "Loss Rate (%)": "loss_rate_pct",
})

# 3. Texte : espaces en début/fin et doubles espaces
df["item_name"] = (
    df["item_name"]
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)
df["item_code"] = df["item_code"].str.strip()

# 4. Types : le taux doit être numérique
df["loss_rate_pct"] = pd.to_numeric(df["loss_rate_pct"], errors="coerce")

# 5. Doublons : sur le code article uniquement
#    (deux articles peuvent avoir le même nom avec des codes différents, c'est normal)
nb_doublons = df.duplicated(subset="item_code").sum()
df = df.drop_duplicates(subset="item_code", keep="first")
print(f"Doublons de code supprimés : {nb_doublons}")

# 6. Valeurs manquantes ou impossibles (un taux de perte est entre 0 et 100)
print("Valeurs manquantes :\n", df.isna().sum())
hors_bornes = ~df["loss_rate_pct"].between(0, 100)
print(f"Taux hors de [0, 100] : {hors_bornes.sum()}")
df = df[~hors_bornes]

# 7. Colonne utile : nom sans le suffixe "(1)", "(2)"...
df["item_name_base"] = df["item_name"].str.replace(r"\s*\(\d+\)$", "", regex=True)

# 8. Taux à 0.00 : ils correspondent à une absence de donnée (et non à une vraie
#    perte nulle), donc on les supprime pour ne pas fausser les statistiques
zeros = df["loss_rate_pct"] == 0
print(f"Lignes à 0.00 supprimées (absence de donnée) : {zeros.sum()}")
df = df[~zeros]

# 9. Export
CLEAN.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEAN, index=False, encoding="utf-8")
print(f"Lignes après nettoyage : {len(df)}")
print(f"Fichier écrit : {CLEAN}")
