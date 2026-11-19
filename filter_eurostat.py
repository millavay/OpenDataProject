
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent

CITY_CODES = [
    'FI001C', 'FI003C', 'FI002C',
    'BE001C', 'BE002C', 'BE003C',
    'DE001C', 'DE002C', 'DE003C',
    'EE001C', 'EE002C', 'EE003C',
    'ES006C', 'ES002C', 'ES004C',
    'FR001C', 'FR004C', 'FR008C', 'FR002C',
    'IT002C', 'IT007C', 'IT011C', 'IT001C',
    'LV001C', 'LV002C',
    'HU001C',
    'MT001C',
    'NL001C', 'NL003C',
    'PL001C', 'PL005C', 'PL003C',
    'PT001C',
    'SI002C', 'SI001C',
    'CH002C', 'CH003C', 'CH007C',
    'NO001C'
]

INDICATORS = [
    "population",
    "unemployment_rate",
    "annual_rent_per_m2",
    "monthly_transport_ticket"
]

# Read the downloaded Eurostat data
df = pd.read_csv(BASE / "eurostat_clean.csv")

# Select cities and indicators
df = df[
    df["city_code"].isin(CITY_CODES) &
    df["indicator"].isin(INDICATORS)
].copy()

# Check for duplicate observations
if df.duplicated(["city_code", "indicator"]).any():
    raise ValueError("Duplicate city/indicator observations")

# Save selected observations
df.to_csv(
    BASE / "eurostat_selected.csv",
    index=False,
    encoding="utf-8-sig"
)

# Create one row per city
names = df[
    df["indicator"] == "population"
].set_index("city_code")[["country_code", "city"]]

if not set(CITY_CODES).issubset(names.index):
    raise ValueError("Missing population records")

result = names.reindex(CITY_CODES).copy()

# Add indicator values and observation years
for metric in INDICATORS:

    observations = df[
        df["indicator"] == metric
    ].set_index("city_code")

    result[metric] = observations["value"]

    result[metric + "_year"] = (
        observations["year"].astype("Int64")
    )

# Save the combined city data
result.to_csv(
    BASE / "eurostat_cities.csv",
    encoding="utf-8-sig",
    index_label="city_code"
)

print("Cities:", len(result))

print("Available observations:")
print(result[INDICATORS].count())
