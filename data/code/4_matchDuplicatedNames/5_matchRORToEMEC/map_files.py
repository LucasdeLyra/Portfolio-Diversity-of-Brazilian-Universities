from collections import defaultdict
import pandas as pd
import ast
import re
import unicodedata


EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)
ROR = pd.read_csv(f'./data/code/matchDuplicatedNames/4_matchScopusToROR/ror_matches.csv', encoding='utf-8', dtype=object)

def normalize_site(url):
    if pd.isna(url):
        return url
    
    url = str(url).lower().strip()
    url = url.replace('http://', '')
    url = url.replace('https://', '') 
    url = url.replace('www.', '')
    url = url.replace('www2.', '')
    url = url.replace('www3.', '')
    url = url.replace('www4.', '')
    url = url.replace('www5.', '')
    url = url.replace('internacional.', '')
    url = url.replace('international.', '')
    url = url.replace('portal.', '')
    url = url.replace('\'', '')
    url = url.replace('[', '')
    
    # Find the last occurring domain extension and truncate after it
    extensions = ['.br', '.org', '.com', '.rio', '.edu', '.net', '.vc', '.online', '.school']
    last_index = -1
    for ext in extensions:
        index = url.rfind(ext)
        if index > last_index:
            last_index = index
    
    if last_index != -1:
        url = url[:last_index + len([ext for ext in extensions if url.rfind(ext) == last_index][0])]
        
    url = url.replace('/', '')
    return url

EMEC['normalized_Sitio'] = EMEC['Sitio'].apply(normalize_site)
ROR['normalized_domain'] = ROR['domain'].apply(normalize_site)
ROR['normalized_url'] = ROR['url'].apply(normalize_site)

def normalize_text(text):
    if pd.isna(text):
        return text
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', errors='ignore').decode('utf-8')
    return re.sub(r'\s*\([^)]*\)', '', text)

EMEC['normalized_Instituição(IES)'] = EMEC['Instituição(IES)'].apply(normalize_text)
ROR['normalized_ror_name'] = ROR['ror_name'].apply(normalize_text)
ROR['normalized_scopus_name'] = ROR['scopus_name'].apply(normalize_text)
if 'related_institution' in ROR.columns:
    ROR['normalized_related_institution'] = ROR['related_institution'].apply(normalize_text)

def match_institutions(inst_EMEC, inst_ROR):
    inst_EMEC = inst_EMEC.reset_index().rename(columns={'index': 'A_original_index'})
    inst_ROR = inst_ROR.reset_index().rename(columns={'index': 'B_original_index'})

    # Split ROR data: hospitals with related_institution vs others
    ror_with_related = inst_ROR[(inst_ROR['is_hospital'] == 'True') | (inst_ROR['is_hospital'] == True)].copy()
    ror_with_related = ror_with_related.dropna(subset=['normalized_related_institution'])
    
    ror_without_related = inst_ROR[~inst_ROR.index.isin(ror_with_related['B_original_index'].values)]

    # Match1a: Hospitals with related_institution using related_institution name
    match1a = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Instituição(IES)']),
        ror_with_related.dropna(subset=['normalized_related_institution']),
        left_on='normalized_Instituição(IES)',
        right_on='normalized_related_institution',
        suffixes=('_A', '_B')
    )
    match1a['name_match'] = 1
    print(f'Name matches found: {len(match1a)}')

    # Match1b: Regular institutions and hospitals without related_institution using ror_name
    match1b = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Instituição(IES)']),
        ror_without_related.dropna(subset=['normalized_ror_name']),
        left_on='normalized_Instituição(IES)',
        right_on='normalized_ror_name',
        suffixes=('_A', '_B')
    )
    match1b['name_match'] = 1
    print(f'Hospital matches found: {len(match1b)}')
    
    match1 = pd.concat([match1a, match1b], ignore_index=True)
    print(f'Total name and hospital matches found: {len(match1)}')


    match2 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Sitio']),
        inst_ROR.dropna(subset=['normalized_url']),
        left_on='normalized_Sitio',
        right_on='normalized_url',
        suffixes=('_A', '_B')
    )
    match2['url_match'] = 1
    print(f'Url matches found: {len(match2)}')
    

    match3 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Sitio']),
        inst_ROR.dropna(subset=['normalized_domain']),
        left_on='normalized_Sitio',
        right_on='normalized_domain',
        suffixes=('_A', '_B')
    )
    match3['domain_match'] = 1
    print(f'Domain matches found: {len(match3)}')
    
    match4 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Sitio']),
        inst_ROR.dropna(subset=['link']),
        left_on='normalized_Sitio',
        right_on='link',
        suffixes=('_A', '_B')
    )
    match4['link_match'] = 1
    print(f'Link matches found: {len(match4)}')
    
    all_matches = pd.concat([match1, match2, match3, match4], ignore_index=True)
    
    agg_dict = {col: 'first' for col in all_matches.columns if col not in ['A_original_index', 'B_original_index']}
    agg_dict.update({
        'name_match': 'sum',
        'url_match': 'sum',
        'domain_match': 'sum',
        'link_match': 'sum',
    })
    
    final_matches = all_matches.groupby(['A_original_index', 'B_original_index']).agg(agg_dict).reset_index()
    final_matches = final_matches.drop_duplicates(subset=['B_original_index'], keep='first')
    flag_columns = ['name_match', 'url_match', 'domain_match', 'link_match']
    final_matches[flag_columns] = final_matches[flag_columns].fillna(0).astype(int)
    
    return final_matches

def count_matches_for_b(source_b_df, matches_df):
    match_counts = matches_df['B_original_index'].value_counts().reset_index()
    match_counts.columns = ['B_original_index', 'match_count']

    source_b_df = source_b_df.reset_index().rename(columns={'index': 'B_original_index'})
    
    result_df = pd.merge(source_b_df, match_counts, on='B_original_index', how='left')
    result_df['match_count'] = result_df['match_count'].fillna(0).astype(int)
    result_df = result_df.drop(columns='B_original_index')

    return result_df

matched_df = match_institutions(EMEC, ROR)
institutions_b_with_counts = count_matches_for_b(ROR, matched_df)

matched_df.drop(['A_original_index', 'normalized_Instituição(IES)', 'level_0', 'B_original_index', 'normalized_ror_name', 'normalized_scopus_name', 'normalized_related_institution', 'normalized_domain', 'normalized_url', 'normalized_Sitio'], axis=1, inplace=True, errors='ignore')
institutions_b_with_counts.drop(['level_0', 'normalized_ror_name', 'normalized_scopus_name', 'normalized_related_institution', 'normalized_domain', 'normalized_url'], axis=1, inplace=True, errors='ignore')

matched_df.to_csv('./data/code/matchDuplicatedNames/5_matchRORToEMEC/matches.csv', index=False)
institutions_b_with_counts.to_csv('./data/code/matchDuplicatedNames/5_matchRORToEMEC/counting.csv', index=False)
