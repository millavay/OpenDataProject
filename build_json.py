import argparse
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--eurostat-only', action='store_true')
args = parser.parse_args()

COUNTRIES = {'FI': 'Finland', 'BE': 'Belgium', 'DE': 'Germany',
             'EE': 'Estonia', 'ES': 'Spain', 'FR': 'France',
             'IT': 'Italy', 'LV': 'Latvia', 'HU': 'Hungary',
             'MT': 'Malta', 'NL': 'Netherlands', 'PL': 'Poland',
             'PT': 'Portugal', 'SI': 'Slovenia', 'CH': 'Switzerland',
             'NO': 'Norway'}

EUROSTAT = ['population', 'unemployment_rate', 'annual_rent_per_m2',
            'monthly_transport_ticket']
WEATHER = ['avg_temperature_c', 'annual_precipitation_mm',
           'annual_sunshine_hours', 'annual_snowfall_cm',
           'latitude', 'longitude', 'matched_city', 'period_start',
           'period_end', 'source']

eurostat = pd.read_csv(BASE / 'eurostat_cities.csv')
assert len(eurostat) == 39 and eurostat['city_code'].is_unique
assert set(eurostat['country_code']) == set(COUNTRIES)

if args.eurostat_only:
    data = eurostat.copy()
    for field in WEATHER:
        data[field] = None
else:
    weather = pd.read_csv(BASE / 'weather_clean.csv')
    assert weather['city_code'].is_unique, 'Duplicate weather city codes'
    assert set(weather['city_code']) == set(eurostat['city_code']), 'City codes do not match'
    assert weather[WEATHER].notna().all().all(), 'Missing weather values'
    data = eurostat.merge(weather[['city_code'] + WEATHER], on='city_code',
                          how='left', validate='one_to_one')

# Preserve nulls and source years. Do not replace missing values with zero.
def clean(value, integer=False):
    if pd.isna(value):
        return None
    if integer:
        return int(value)
    return value.item() if hasattr(value, 'item') else value

countries = []
for code, group in data.groupby('country_code', sort=False):
    country = {'country': COUNTRIES[code], 'country_code': code, 'cities': []}
    for _, row in group.iterrows():
        city = {'city': row['city'], 'city_code': row['city_code']}
        for field in EUROSTAT:
            city[field] = clean(row[field], field == 'population')
            city[field + '_year'] = clean(row[field + '_year'], True)
        for field in WEATHER:
            key = {'period_start': 'weather_period_start', 'period_end': 'weather_period_end',
                   'source': 'weather_source', 'matched_city': 'weather_matched_city'}.get(field, field)
            city[key] = clean(row[field], field in ('period_start', 'period_end'))
        country['cities'].append(city)
    countries.append(country)

output = BASE / ('countries_eurostat_draft.json' if args.eurostat_only else 'countries.json')
with output.open('w', encoding='utf-8') as f:
    json.dump(countries, f, ensure_ascii=False, indent=2, allow_nan=False)
print(f'Created {output.name}: {len(countries)} countries, {len(data)} cities')
