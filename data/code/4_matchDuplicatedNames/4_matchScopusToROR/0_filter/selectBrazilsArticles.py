import json


RAW_DIR = './data/data/raw'
with open(f'{RAW_DIR}/v1.70-2025-08-26-ror-data.json', 'r') as raw_ROR:
    ROR_with_all_countries = json.load(raw_ROR)

only_brazil = [record for record in ROR_with_all_countries if record['country']['country_name'] == 'Brazil']

output_path = f'data/code/matchDuplicatedNames/4_matchScopusToROR/ror_brazil.json'
with open(output_path, 'w', encoding='utf-8') as filtered_ROR:
    json.dump(only_brazil, filtered_ROR, ensure_ascii=False, indent=4)

print(f"Saved {len(only_brazil)} records to {output_path}")