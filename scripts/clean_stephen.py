"""
Nettoyage de la table price.csv (prix d'achat fournisseur par article et par jour)
Responsable : Stephen MORLOT

Entrée  : data/raw/price.csv
Sortie  : data/clean/table_stephen.csv

Lancer depuis la racine du repo :
    python scripts/clean_stephen.py
"""

from pathlib import Path

import pandas as pd

RAW = Path("data/raw/price.csv")
CLEAN = Path("data/clean/table_stephen.csv")

# Un prix d'achat inférieur à 10 % du prix habituel de l'article est
# considéré comme une erreur de saisie (ex. 0,01 RMB/kg pour un article
# acheté 7 RMB/kg en temps normal) : un prix de gros ne chute pas de 90 % en un jour.
SEUIL_PRIX_ABERRANT = 0.10

# Fenêtre (en jours, de chaque côté) pour calculer le prix de remplacement
FENETRE_JOURS = 7


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Chargement
    # ------------------------------------------------------------------
    df = pd.read_csv(RAW)
    print(f"Lignes brutes : {len(df):,}")

    # ------------------------------------------------------------------
    # 2. Noms de colonnes : snake_case, sans espaces ni unités entre parenthèses
    #    -> même convention pour les 4 tables, jointures plus simples
    # ------------------------------------------------------------------
    df = df.rename(columns={
        "Date": "price_date",
        "Item Code": "item_code",
        "Wholesale Price (RMB/kg)": "wholesale_price_rmb_kg",
    })

    # ------------------------------------------------------------------
    # 3. Types
    #    - price_date : texte -> date
    #    - item_code  : entier -> texte. C'est un identifiant, pas un nombre :
    #      on ne le somme jamais, et Excel l'afficherait en notation
    #      scientifique (1,03E+14). Clé commune avec les 3 autres tables.
    #    - prix : décimal
    # ------------------------------------------------------------------
    df["price_date"] = pd.to_datetime(df["price_date"], format="%Y-%m-%d", errors="coerce")
    df["item_code"] = df["item_code"].astype(str).str.strip()
    df["wholesale_price_rmb_kg"] = pd.to_numeric(df["wholesale_price_rmb_kg"], errors="coerce")

    # ------------------------------------------------------------------
    # 4. Valeurs manquantes
    #    Aucune dans le fichier brut. On garde le contrôle : une ligne sans
    #    date, sans article ou sans prix est inutilisable, on la supprime.
    # ------------------------------------------------------------------
    nb_na = df.isna().any(axis=1).sum()
    df = df.dropna(subset=["price_date", "item_code", "wholesale_price_rmb_kg"])
    print(f"Lignes avec valeur manquante supprimées : {nb_na}")

    # ------------------------------------------------------------------
    # 5. Doublons
    #    Règle métier : un seul prix d'achat par article et par jour.
    #    (price_date, item_code) est la clé primaire de la table.
    # ------------------------------------------------------------------
    nb_doublons = df.duplicated(subset=["price_date", "item_code"]).sum()
    df = df.drop_duplicates(subset=["price_date", "item_code"], keep="last")
    print(f"Doublons (date, article) supprimés : {nb_doublons}")

    # ------------------------------------------------------------------
    # 6. Prix négatifs ou nuls : impossibles pour un prix d'achat
    # ------------------------------------------------------------------
    nb_neg = (df["wholesale_price_rmb_kg"] <= 0).sum()
    df.loc[df["wholesale_price_rmb_kg"] <= 0, "wholesale_price_rmb_kg"] = pd.NA
    print(f"Prix nuls ou négatifs : {nb_neg}")

    # ------------------------------------------------------------------
    # 7. Valeurs aberrantes
    #
    #    a) Erreurs de saisie -> CORRIGÉES
    #       Prix < 10 % du prix médian de l'article (ex. 0,01 RMB/kg).
    #       Remplacées par la médiane de l'article sur +/- 7 jours
    #       (le prix suit les saisons, une médiane sur 3 ans serait faussée).
    #
    #    b) Valeurs hors IQR -> SIGNALÉES, PAS SUPPRIMÉES
    #       L'IQR global n'a pas de sens : un champignon coûte 10x un chou.
    #       On le calcule donc PAR ARTICLE. Même ainsi, un prix haut peut être
    #       réel (pénurie, hors saison) : on ajoute une colonne is_outlier_iqr
    #       pour que l'analyse puisse les exclure si besoin.
    # ------------------------------------------------------------------
    df = df.sort_values(["item_code", "price_date"]).reset_index(drop=True)

    mediane_article = df.groupby("item_code")["wholesale_price_rmb_kg"].transform("median")
    df["is_price_corrected"] = (
        df["wholesale_price_rmb_kg"].isna()
        | (df["wholesale_price_rmb_kg"] < SEUIL_PRIX_ABERRANT * mediane_article)
    )
    print(f"Prix aberrants corrigés (< {SEUIL_PRIX_ABERRANT:.0%} de la médiane) : "
          f"{df['is_price_corrected'].sum()}")

    # Médiane glissante calculée sans les valeurs aberrantes
    prix_fiable = df["wholesale_price_rmb_kg"].where(~df["is_price_corrected"])
    mediane_glissante = (
        prix_fiable.groupby(df["item_code"])
        .transform(lambda s: s.rolling(2 * FENETRE_JOURS + 1, center=True, min_periods=1).median())
    )
    remplacement = mediane_glissante.fillna(mediane_article)
    df.loc[df["is_price_corrected"], "wholesale_price_rmb_kg"] = remplacement
    df["wholesale_price_rmb_kg"] = df["wholesale_price_rmb_kg"].astype(float).round(2)

    # IQR par article
    q1 = df.groupby("item_code")["wholesale_price_rmb_kg"].transform(lambda s: s.quantile(0.25))
    q3 = df.groupby("item_code")["wholesale_price_rmb_kg"].transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    df["is_outlier_iqr"] = (
        (df["wholesale_price_rmb_kg"] < q1 - 1.5 * iqr)
        | (df["wholesale_price_rmb_kg"] > q3 + 1.5 * iqr)
    )
    print(f"Prix hors IQR par article (signalés, conservés) : {df['is_outlier_iqr'].sum()}")

    # ------------------------------------------------------------------
    # 8. Export
    # ------------------------------------------------------------------
    df = df.sort_values(["price_date", "item_code"])
    df["price_date"] = df["price_date"].dt.strftime("%Y-%m-%d")
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN, index=False)
    print(f"Lignes nettoyées : {len(df):,} -> {CLEAN}")


if __name__ == "__main__":
    main()
