"""Nettoyage de transaction.csv (Exercice 2, étape 3).

Usage : python src/clean_transaction.py <entrée.csv> <sortie.csv>
"""
import sys
import pandas as pd

COLS = {
    "Date": "date",
    "Time": "time",
    "Item Code": "item_code",
    "Quantity Sold (kilo)": "quantity_kg",
    "Unit Selling Price (RMB/kg)": "unit_price_rmb_kg",
    "Sale or Return": "sale_or_return",
    "Discount (Yes/No)": "discount",
}


def clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"Item Code": "string"}).rename(columns=COLS)
    n0 = len(df)

    # Types
    df["item_code"] = df["item_code"].str.strip()
    df["quantity_kg"] = pd.to_numeric(df["quantity_kg"], errors="coerce")
    df["unit_price_rmb_kg"] = pd.to_numeric(df["unit_price_rmb_kg"], errors="coerce")
    df["sale_or_return"] = df["sale_or_return"].str.strip().str.lower()
    df["discount"] = df["discount"].str.strip().str.lower().map({"yes": True, "no": False})

    # Date + heure (certaines heures n'ont pas de millisecondes -> format mixte)
    df["datetime"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str), format="mixed", errors="coerce"
    )
    df["date"] = df["datetime"].dt.date
    df = df.drop(columns="time")

    # Valeurs manquantes / invalides
    df = df.dropna(subset=["datetime", "item_code", "quantity_kg", "unit_price_rmb_kg", "discount"])
    df = df[df["unit_price_rmb_kg"] > 0]
    df = df.drop_duplicates()

    # Cohérence vente / retour : un retour a une quantité négative, une vente positive
    df = df[
        ((df["sale_or_return"] == "sale") & (df["quantity_kg"] > 0))
        | ((df["sale_or_return"] == "return") & (df["quantity_kg"] < 0))
    ]

    # Colonnes dérivées
    df["is_return"] = df["sale_or_return"] == "return"
    df["revenue_rmb"] = (df["quantity_kg"] * df["unit_price_rmb_kg"]).round(2)
    # Quantités extrêmes : signalées, pas supprimées
    df["is_outlier_qty"] = df["quantity_kg"].abs() > 20

    df = df.sort_values("datetime").reset_index(drop=True)
    print(f"{n0} lignes en entrée -> {len(df)} lignes propres")
    return df


if __name__ == "__main__":
    out = clean(sys.argv[1])
    out.to_csv(sys.argv[2], index=False)
