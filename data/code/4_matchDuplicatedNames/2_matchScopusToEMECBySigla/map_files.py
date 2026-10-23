import pandas as pd
import ast
import re
import unicodedata

EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)
SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/1_matchScopusToEMECByName/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()

def normalize_text(text):
    if pd.isna(text):
        return text
    text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', errors='ignore').decode('utf-8').lower()    
    text = re.sub(r'[\[\]()/\\-]', ' ', text).strip()
    return text

SCOPUS['normalized_variants'] = SCOPUS['variants'].apply(ast.literal_eval)
SCOPUS['normalized_variants'] = SCOPUS['normalized_variants'].apply(lambda lst: [normalize_text(item) for item in lst])
SCOPUS['normalized_name'] = SCOPUS['name'].apply(normalize_text)
# Extract Sigla from parentheses
SCOPUS['Sigla'] = SCOPUS['name'].str.extract(r'\(([^)]+)\)', expand=False)


# Extract sigla from each variant and combine with original sigla
def extract_siglas(row):
    siglas = []
    # Add original sigla if exists
    if pd.notna(row['Sigla']):
        siglas.append(str(row['Sigla']).upper())
    # Extract siglas from variants
    if pd.notna(row['variants']):
        variants_list = ast.literal_eval(row['variants']) if isinstance(row['variants'], str) else row['variants']
        for variant in variants_list:
            match = re.search(r'\(([^)]+)\)', str(variant))
            if match and str(match).upper() not in siglas:
                siglas.append(str(match.group(1)).upper())

    # If no sigla found, try to extract everything after the last '-'
    if pd.notna(row['name']):
        name = str(row['name']).strip()
        if '-' in name:
            splitted_name = name.split('-')
            filtered = [s for s in splitted_name if len(s.strip()) >= 3]
            shortest_string = min(filtered, key=len) if filtered else None
            if shortest_string:
                possible_sigla = normalize_text(shortest_string.strip()).upper()
                if possible_sigla:
                    siglas.append(possible_sigla)
    
    return siglas if siglas else [None]

SCOPUS['Sigla'] = SCOPUS.apply(extract_siglas, axis=1)

# Extract Sigla for EMEC too
EMEC['Sigla'] = EMEC['Instituição(IES)'].str.extract(r'\(([^)]+)\)', expand=False)
EMEC['normalized_Instituição(IES)'] = EMEC['Instituição(IES)'].apply(normalize_text)

def match_institutions(inst_EMEC, inst_SCOPUS):
    inst_EMEC = inst_EMEC.reset_index().rename(columns={'index': 'A_original_index'})
    inst_SCOPUS = inst_SCOPUS.reset_index().rename(columns={'index': 'B_original_index'})

    special_siglas = ['FAP', 'FATEC', 'FSA']
    
    # Helper function to check if city is in normalized text
    def city_in_text(row):
        if pd.isna(row['Sigla']) or row['Sigla'] not in special_siglas:
            return True
        city = str(row['city']).lower() if pd.notna(row['city']) else ''
        if not city:
            return False
        # Check if city is in normalized_name
        if pd.notna(row['normalized_Instituição(IES)']) and normalize_text(city) in str(row['normalized_Instituição(IES)']).lower():
            return True
        return False

    # Match 1: SCOPUS Sigla list vs EMEC Sigla
    inst_SCOPUS_exploded = inst_SCOPUS.explode('Sigla')
    inst_SCOPUS_exploded = inst_SCOPUS_exploded.dropna(subset=['Sigla'])
    
    match1 = pd.merge(
        inst_EMEC.dropna(subset=['Sigla']),
        inst_SCOPUS_exploded.dropna(subset=['Sigla']),
        left_on=['Sigla'],
        right_on=['Sigla'],
        suffixes=('_A', '_B')
    )
    match1['sigla_match'] = 1
    # Filter for special siglas
    match1 = match1[match1.apply(city_in_text, axis=1)]
    print(f'Sigla in sigla matches found: {len(match1)}')

    # Match 2: SCOPUS normalized_name vs EMEC Sigla
    match2 = pd.merge(
        inst_EMEC.dropna(subset=['Sigla']),
        inst_SCOPUS.dropna(subset=['normalized_name']),
        left_on=['Sigla'],
        right_on=['normalized_name'],
        suffixes=('_A', '_B')
    )
    match2['name_to_sigla_match'] = 1
    # Filter for special siglas
    match2 = match2[match2.apply(city_in_text, axis=1)]
    print(f'Sigla in normalized name matches found: {len(match2)}')
    

    # Match 3: SCOPUS normalized_variants vs EMEC Sigla (with UF/state filter)
    inst_SCOPUS_variants_exploded = inst_SCOPUS.explode('normalized_variants')
    inst_SCOPUS_variants_exploded = inst_SCOPUS_variants_exploded.dropna(subset=['normalized_variants'])
    
    match3 = pd.merge(
        inst_EMEC.dropna(subset=['Sigla']),
        inst_SCOPUS_variants_exploded.dropna(subset=['normalized_variants']),
        left_on=['Sigla'],
        right_on=['normalized_variants'],
        suffixes=('_A', '_B')
    )
    match3['variants_to_sigla_match'] = 1
    # Filter for special siglas
    match3 = match3[match3.apply(city_in_text, axis=1)]
    print(f'Sigla in variants matches found: {len(match3)}')
    
    # Match 4: SCOPUS normalized_name vs EMEC Sigla
    match4 = pd.merge(
        inst_EMEC.dropna(subset=['Sigla']),
        inst_SCOPUS.dropna(subset=['name']),
        left_on=['Sigla'],
        right_on=['name'],
        suffixes=('_A', '_B')
    )
    match4['name_to_sigla_match'] = 1
    # Filter for special siglas
    print(f'Sigla in name matches found: {len(match4)}')
    

    all_matches = pd.concat([match1, match2, match3], ignore_index=True)
    all_matches = all_matches.drop_duplicates(subset=['B_original_index'], keep='first')
    
    agg_dict = {col: 'first' for col in all_matches.columns if col not in ['A_original_index', 'B_original_index']}
    agg_dict.update({
        'sigla_match': 'sum',
        'name_to_sigla_match': 'sum',
        'variants_to_sigla_match': 'sum'
    })
    
    final_matches = all_matches.groupby(['A_original_index', 'B_original_index']).agg(agg_dict).reset_index()
    flag_columns = ['sigla_match', 'name_to_sigla_match', 'variants_to_sigla_match']
    final_matches[flag_columns] = final_matches[flag_columns].fillna(0).astype(int)
    
    return final_matches

def count_matches_for_b(source_b_df, matches_df):
    match_counts = matches_df['B_original_index'].value_counts().reset_index()
    match_counts.columns = ['B_original_index', 'match_count']

    source_b_df = source_b_df.reset_index().rename(columns={'index': 'B_original_index'})
    
    # Drop existing match_count column if it exists
    if 'match_count' in source_b_df.columns:
        source_b_df = source_b_df.drop(columns='match_count')
    
    result_df = pd.merge(source_b_df, match_counts, on='B_original_index', how='left')
    result_df['match_count'] = result_df['match_count'].fillna(0).astype(int)
    result_df = result_df.drop(columns='B_original_index')

    return result_df

matched_df = match_institutions(EMEC, SCOPUS)
institutions_b_with_counts = count_matches_for_b(SCOPUS, matched_df)

# Drop columns that exist in the dataframe
cols_to_drop = ['A_original_index', 'level_0', 'B_original_index', 'normalized_variants', 'normalized_name']
cols_to_drop = [col for col in cols_to_drop if col in matched_df.columns]
matched_df.drop(cols_to_drop, axis=1, inplace=True)

cols_to_drop_b = ['level_0', 'normalized_variants', 'normalized_name']
cols_to_drop_b = [col for col in cols_to_drop_b if col in institutions_b_with_counts.columns]
institutions_b_with_counts.drop(cols_to_drop_b, axis=1, inplace=True)

matched_df.to_csv('./data/code/matchDuplicatedNames/2_matchScopusToEMECBySigla/matches.csv', index=False)
institutions_b_with_counts.to_csv('./data/code/matchDuplicatedNames/2_matchScopusToEMECBySigla/counting.csv', index=False)