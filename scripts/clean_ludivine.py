import pandas as pd

# 1. Chargement (tout en texte pour garder les codes à 15 chiffres intacts)
df_avant = pd.read_csv("data/raw/product.csv", dtype=str)
df = df_avant.copy()

# 2. Noms de colonnes en snake_case
df.columns = df.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

# 3. Nettoyage du texte : espaces au début/fin et doubles espaces
for c in df.columns:
    df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)

# 4. Valeurs vides et doublons
df = df.replace("", pd.NA).dropna(subset=["item_code", "item_name"])
df = df.drop_duplicates().drop_duplicates(subset="item_code", keep="first")

# 5. Tri
df = df.sort_values(["category_code", "item_name"]).reset_index(drop=True)

# 6. Contrôle (non modifié) : noms présents dans plusieurs catégories
multi_cat = df.groupby("item_name")["category_code"].nunique()
print("Noms dans plusieurs catégories :", multi_cat[multi_cat > 1].index.tolist())

# 7. Affichage avant / après
print("AVANT :", df_avant.shape)
print(df_avant.head(10))
print("APRÈS :", df.shape)
print(df.head(10))
print("Espaces finaux avant :", (df_avant["Item Name"] != df_avant["Item Name"].str.strip()).sum())
print("Espaces finaux après :", (df["item_name"] != df["item_name"].str.strip()).sum())

# 8. Export
df.to_csv("data/clean/product_ludivine.csv", index=False, encoding="utf-8")
