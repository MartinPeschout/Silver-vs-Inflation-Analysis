import pandas as pd
import openpyxl
import matplotlib.pyplot as plt
import matplotlib

# --- 1. Načtení a úprava dat o stříbru (USD ceny) ---
silver_df = pd.read_csv("Silver Futures Historical Data.csv")
silver_df["Date"] = pd.to_datetime(silver_df["Date"])
silver_df.sort_values("Date", inplace=True)
silver_df["Vol."] = silver_df["Vol."].replace("-", "0")
silver_df["Vol."] = silver_df["Vol."].str.replace("K", "e3").str.replace("M", "e6")
silver_df["Vol."] = pd.to_numeric(silver_df["Vol."])
silver_df.drop(columns=["Open", "High", "Low", "Change %"], inplace=True)
silver_df.set_index("Date", inplace=True)
silver_df = silver_df["2010-01-01":"2025-06-01"]
silver_df.index = silver_df.index.to_period("M").to_timestamp()

# --- 2. Načtení a úprava kurzů USD/CZK z ČNB ---
kurzy_df = pd.read_excel("Kurzy_CNB_USD.xlsx")
kurzy_df = kurzy_df.melt(id_vars=["rok"], var_name="měsíc", value_name="USD_CZK")

mesic_map = {
    "leden": 1, "únor": 2, "březen": 3, "duben": 4,
    "květen": 5, "červen": 6, "červenec": 7, "srpen": 8,
    "září": 9, "říjen": 10, "listopad": 11, "prosinec": 12
}

kurzy_df["měsíc"] = kurzy_df["měsíc"].map(mesic_map)
kurzy_df["Date"] = pd.to_datetime(dict(year=kurzy_df["rok"], month=kurzy_df["měsíc"], day=1))
kurzy_df = kurzy_df[["Date", "USD_CZK"]].set_index("Date")
kurzy_df = kurzy_df.sort_index()
kurzy_df = kurzy_df["2010-01-01":"2025-06-01"]
kurzy_df.index = kurzy_df.index.to_period("M").to_timestamp()

# --- 3. Načtení a úprava inflace z ECB ---
inflace_df = pd.read_csv("ECB Data Portal_20250625125836.csv")
inflace_df = inflace_df[["DATE", "HICP - Overall index (ICP.M.CZ.N.000000.4.ANR)"]].copy()
inflace_df.columns = ["Date", "Inflace (%)"]
inflace_df["Date"] = pd.to_datetime(inflace_df["Date"])
inflace_df.set_index("Date", inplace=True)
inflace_df = inflace_df["2010-01-01":"2025-06-01"]
inflace_df.index = inflace_df.index.to_period("M").to_timestamp()

# --- 4. Spojení všech dat do jednoho DataFrame ---
df = silver_df.join(kurzy_df, how="inner")
df = df.join(inflace_df, how="inner")

# --- 5. Výpočty ---
df["CZK_Price"] = df["Price"] * df["USD_CZK"]
start_price = df["CZK_Price"].iloc[0]
df["silver_growth"] = df["CZK_Price"] / start_price
df["rel_return (%)"] = (df["silver_growth"] - 1) * 100
df["inflace_decimal"] = df["Inflace (%)"] / 100 / 12
df["cum_inflation_index"] = (1 + df["inflace_decimal"]).cumprod()
df["real_growth"] = df["silver_growth"] / df["cum_inflation_index"]
df["real_return (%)"] = (df["real_growth"] - 1) * 100

# ❗️DOPLNĚNO: poměr stříbro / inflace
df["silver_vs_inflation"] = df["CZK_Price"] / (df["cum_inflation_index"] * df["CZK_Price"].iloc[0])

# --- 6. Výstup ---
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
print(df[["Price", "USD_CZK", "CZK_Price", "Inflace (%)", "rel_return (%)", "real_return (%)"]].tail(12))

# Uložení výsledného DataFrame do Excel souboru
output_file = "Silver_Analysis.xlsx"
df.to_excel(output_file)

# --- 7. Vizualizace dat (uložení do PNG s inflací) ---
matplotlib.use('Agg')

df = df.reset_index()
plt.figure(figsize=(14, 6))
plt.plot(df["Date"], df["CZK_Price"], label="Cena stříbra (CZK)", linewidth=2)
plt.plot(df["Date"], df["real_growth"] * df["CZK_Price"].iloc[0],
         label="Reálná hodnota (očištěno o inflaci)", linestyle="--", linewidth=2)
inflacni_index_v_czk = df["cum_inflation_index"] * df["CZK_Price"].iloc[0]
plt.plot(df["Date"], inflacni_index_v_czk,
         label="Index kumulativní inflace", linestyle=":", linewidth=2, color="gray")
plt.title("Vývoj ceny stříbra vs. inflace (CZK, 2010–2025)")
plt.xlabel("Datum")
plt.ylabel("Hodnota v CZK")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("graf_stribro_s_inflaci.png")

# --- 8. Poměr stříbra k inflaci ---
plt.figure(figsize=(14, 4))
plt.plot(df["Date"], df["silver_vs_inflation"], label="Poměr stříbro / inflace", color="green", linewidth=2)
plt.axhline(1, color="gray", linestyle="--", linewidth=1)
plt.title("Relativní síla stříbra vůči inflaci")
plt.xlabel("Datum")
plt.ylabel("Poměr (stříbro/inflace)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("graf_stribro_vs_inflace_pomer.png")
