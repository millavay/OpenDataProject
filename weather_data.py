
import requests
import pandas as pd
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent

GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

WEATHER_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)

cities = pd.read_csv(BASE / "eurostat_cities.csv")

if (BASE / "weather_clean.csv").exists():
    previous = pd.read_csv(BASE / "weather_clean.csv")
    rows = previous.to_dict("records")
else:
    rows = []

FIX_COORDINATES = {
    "IT002C": (45.4642, 9.1900, "Milan"),
    "IT007C": (43.7696, 11.2558, "Florence"),
    "IT011C": (45.4408, 12.3155, "Venice"),
    "IT001C": (41.9028, 12.4964, "Rome")
}

rows = [
    row for row in rows
    if row["city_code"] not in FIX_COORDINATES
]

completed = {row["city_code"] for row in rows}

errors = []

for _, city in cities.iterrows():

    city_code = city["city_code"]
    if city_code in completed:
        continue
    country_code = city["country_code"]
    city_name = city["city"]

    print(f"Downloading weather: {city_name}")

    # Clean Eurostat city name
        
    search_name = city_name.split("(")[0].strip()
    search_name = search_name.split("/")[0].strip()
    search_name = search_name.removeprefix("Greater ")

    CITY_ALIASES = {
        "BE001C": "Brussels",
        "PL001C": "Warsaw",
        "PT001C": "Lisbon"
    }

    search_name = CITY_ALIASES.get(city_code, search_name)

    try:

        
        # Get city coordinates
        if city_code in FIX_COORDINATES:

            latitude, longitude, matched_name = (
                FIX_COORDINATES[city_code]
            )

            location = {"name": matched_name}

        else:

            response = requests.get(
                GEOCODING_URL,
                params={
                    "name": search_name,
                    "countryCode": country_code,
                    "count": 10,
                    "language": "en"
                },
                timeout=60
            )

            response.raise_for_status()

            locations = response.json().get("results", [])

            locations = [
                loc for loc in locations
                if loc.get("country_code") == country_code
            ]

            if not locations:
                raise ValueError("City not found")

            location = locations[0]

            latitude = location["latitude"]
            longitude = location["longitude"]


        # Download historical weather
        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "daily": (
                    "temperature_2m_mean,"
                    "precipitation_sum,"
                    "sunshine_duration,"
                    "snowfall_sum"
                ),
                "models": "era5",
                "timezone": "auto"
            },
            timeout=120
        )

        response.raise_for_status()

        weather = pd.DataFrame(
            response.json()["daily"]
        )

        # Check data quality
        if len(weather) != 1827:
            raise ValueError("Incomplete date range")

        if weather.isna().any().any():
            raise ValueError("Missing weather values")

        # Calculate five-year averages
        rows.append({
            "city_code": city_code,
            "country_code": country_code,
            "city": city_name,
            "matched_city": location["name"],
            "latitude": latitude,
            "longitude": longitude,

            "avg_temperature_c": round(
                weather["temperature_2m_mean"].mean(), 2
            ),

            "annual_precipitation_mm": round(
                weather["precipitation_sum"].sum() / 5, 2
            ),

            "annual_sunshine_hours": round(
                weather["sunshine_duration"].sum() / 3600 / 5, 2
            ),

            "annual_snowfall_cm": round(
                weather["snowfall_sum"].sum() / 5, 2
            ),

            "period_start": 2020,
            "period_end": 2024,
            "source": "Open-Meteo ERA5"
        })

    except Exception as error:

        print(f"Error: {city_name} - {error}")

        errors.append({
            "city_code": city_code,
            "city": city_name,
            "error": str(error)
        })

        if "429" in str(error):
            print("API rate limit reached. Stopping.")
            break

    time.sleep(20)

# Save results
pd.DataFrame(rows).to_csv(
    BASE / "weather_clean.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    errors,
    columns=["city_code", "city", "error"]
).to_csv(
    BASE / "weather_errors.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nDone!")
print("Successful cities:", len(rows))
print("Failed cities:", len(errors))
