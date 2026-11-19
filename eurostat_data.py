
import requests
import pandas as pd
from itertools import product

BASE_URL = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data/"
)

INDICATORS = {
    "urb_cpop1": {
        "DE1001V": "population"
    },
    "urb_clma": {
        "EC1020I": "unemployment_rate"
    },
    "urb_clivcon": {
        "SA1049V": "annual_rent_per_m2",
        "EC3039V": "median_household_income"
    },
    "urb_cenv": {
        "EN2027V": "pm10_concentration",
        "EN5205V": "green_areas_percentage"
    },
    "urb_ctran": {
        "TT1010V": "public_transport_usage",
        "TT1080V": "monthly_transport_ticket"
    }
}

YEARS = [2024, 2023, 2022]

rows = []

# Download selected indicators
for dataset, indicators in INDICATORS.items():

    for code, name in indicators.items():

        for year in YEARS:

            print(f"Downloading {name} - {year}")

            response = requests.get(
                BASE_URL + dataset,
                params={
                    "lang": "EN",
                    "time": year,
                    "indic_ur": code
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()

            # Read JSON-stat dimensions
            dimensions = data["id"]
            categories = []

            for dim in dimensions:

                index = data["dimension"][dim]["category"]["index"]

                if isinstance(index, dict):
                    keys = sorted(index, key=index.get)
                else:
                    keys = index

                categories.append(keys)

            city_names = data["dimension"]["cities"]["category"]["label"]

            # Read observation values
            values = data.get("value", {})

            for offset, combination in enumerate(product(*categories)):

                if isinstance(values, dict):
                    value = values.get(str(offset))
                else:
                    value = values[offset]

                if value is None:
                    continue

                observation = dict(zip(dimensions, combination))

                city_code = observation["cities"]

                rows.append({
                    "country_code": city_code[:2],
                    "city_code": city_code,
                    "city": city_names[city_code],
                    "indicator": name,
                    "indicator_code": code,
                    "value": value,
                    "year": year,
                    "dataset": dataset
                })

# Convert collected data into DataFrame
df = pd.DataFrame(rows)

if df.empty:
    raise RuntimeError("No observations downloaded.")

# Save all downloaded observations
df.to_csv(
    "eurostat_raw.csv",
    index=False,
    encoding="utf-8-sig"
)

# Prefer the latest available year
df = df.sort_values("year", ascending=False)

df = df.drop_duplicates(
    subset=["city_code", "indicator"],
    keep="first"
)

# Save latest available values
df.to_csv(
    "eurostat_clean.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nDone!")
print("Observations:", len(df))
print("Locations:", df["city_code"].nunique())

print("\nAvailable observations per indicator:")
print(df.groupby("indicator")["city_code"].nunique())

print("\nCreated files:")
print("eurostat_raw.csv")
print("eurostat_clean.csv")
