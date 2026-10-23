import pandas as pd
import ast
import re
import unicodedata


EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)
SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/0_matchScopusToEMECByDomain/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()

def normalize_text(text):
    if pd.isna(text):
        return text
    text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', errors='ignore').decode('utf-8').lower()    
    text = re.sub(r'[\[\]()/\\-]', '', text)
    text = re.sub(r'\b(da|de|di|do|du) ', '', text)
    return text

SCOPUS['normalized_variants'] = SCOPUS['variants'].apply(ast.literal_eval)
EMEC['normalized_Instituição(IES)'] = EMEC['Instituição(IES)'].apply(normalize_text)
SCOPUS['normalized_name'] = SCOPUS['name'].apply(normalize_text)
SCOPUS['normalized_variants'] = SCOPUS['normalized_variants'].apply(lambda lst: [normalize_text(item) for item in lst])

def match_institutions(inst_EMEC, inst_SCOPUS):
    inst_EMEC = inst_EMEC.reset_index().rename(columns={'index': 'A_original_index'})
    inst_SCOPUS = inst_SCOPUS.reset_index().rename(columns={'index': 'B_original_index'})

    match1 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Instituição(IES)']),
        inst_SCOPUS.dropna(subset=['normalized_name']),
        left_on='normalized_Instituição(IES)',
        right_on='normalized_name',
        suffixes=('_A', '_B')
    )
    match1['name_match'] = 1
    print(f'Name matches found: {len(match1)}')
    
    inst_EMEC_filtered = inst_EMEC.dropna(subset=['normalized_Instituição(IES)'])
    inst_SCOPUS_filtered = inst_SCOPUS.dropna(subset=['normalized_variants'])
    
    inst_SCOPUS_exploded = inst_SCOPUS_filtered.explode('normalized_variants')
    inst_SCOPUS_exploded = inst_SCOPUS_exploded.dropna(subset=['normalized_variants'])
    
    match4 = pd.merge(
        inst_EMEC_filtered,
        inst_SCOPUS_exploded,
        left_on='normalized_Instituição(IES)',
        right_on='normalized_variants',
        suffixes=('_A', '_B')
    )
    match4['variant_match'] = 1
    print(f'Variant matches found: {len(match4)}')
    
    all_matches = pd.concat([match1, match4], ignore_index=True)
    all_matches = all_matches.drop_duplicates(subset=['B_original_index'], keep='first')
    
    agg_dict = {col: 'first' for col in all_matches.columns if col not in ['A_original_index', 'B_original_index']}
    agg_dict.update({
        'name_match': 'sum',
        'variant_match': 'sum',
    })
    
    final_matches = all_matches.groupby(['A_original_index', 'B_original_index']).agg(agg_dict).reset_index()
    flag_columns = ['name_match', 'variant_match']
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
cols_to_drop = ['A_original_index', 'normalized_Instituição(IES)', 'level_0', 'B_original_index', 'normalized_variants', 'normalized_name']
cols_to_drop = [col for col in cols_to_drop if col in matched_df.columns]
matched_df.drop(cols_to_drop, axis=1, inplace=True)

cols_to_drop_b = ['level_0', 'normalized_variants', 'normalized_name']
cols_to_drop_b = [col for col in cols_to_drop_b if col in institutions_b_with_counts.columns]
institutions_b_with_counts.drop(cols_to_drop_b, axis=1, inplace=True)

matched_df.to_csv('./data/code/matchDuplicatedNames/1_matchScopusToEMECByName/matches.csv', index=False)
institutions_b_with_counts.to_csv('./data/code/matchDuplicatedNames/1_matchScopusToEMECByName/counting.csv', index=False)