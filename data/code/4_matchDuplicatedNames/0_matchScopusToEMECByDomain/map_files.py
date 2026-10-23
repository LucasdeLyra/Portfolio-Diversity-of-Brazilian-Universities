import pandas as pd

EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)
SCOPUS = pd.read_csv(f'./data/data/staging/aux_institutions.csv', encoding='utf-8', dtype=object)
EMEC = EMEC[~EMEC['Código IES'].isin(['17613', '17612'])]

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

def extract_email_domain(email):
    if pd.isna(email):
        return None
    email = str(email).lower().strip()
    if '@' in email:
        return email.split('@')[-1]
    return None

EMEC['normalized_Sitio'] = EMEC['Sitio'].apply(normalize_site)
EMEC['formated_email'] = EMEC['e-Mail'].apply(extract_email_domain)
SCOPUS['normalized_domain'] = SCOPUS['domain'].apply(normalize_site)
SCOPUS['normalized_url'] = SCOPUS['url'].apply(normalize_site)

def match_institutions(inst_EMEC, inst_SCOPUS):
    inst_EMEC = inst_EMEC.reset_index().rename(columns={'index': 'A_original_index'})
    inst_SCOPUS = inst_SCOPUS.reset_index().rename(columns={'index': 'B_original_index'})

    match2 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Sitio']),
        inst_SCOPUS.dropna(subset=['normalized_url']),
        left_on='normalized_Sitio',
        right_on='normalized_url',
        suffixes=('_A', '_B')
    )
    match2['url_match'] = 1
    print(f'URL matches found: {len(match2)}')

    match3 = pd.merge(
        inst_EMEC.dropna(subset=['normalized_Sitio']),
        inst_SCOPUS.dropna(subset=['normalized_domain']),
        left_on='normalized_Sitio',
        right_on='normalized_domain',
        suffixes=('_A', '_B')
    )
    match3['domain_match'] = 1
    print(f'Domain matches found: {len(match3)}')
    
    # Match email domain with normalized domain and url
    match4 = pd.merge(
        inst_EMEC.dropna(subset=['formated_email']),
        inst_SCOPUS.dropna(subset=['normalized_domain']),
        left_on='formated_email',
        right_on='normalized_domain',
        suffixes=('_A', '_B')
    )
    match4['email_domain_match'] = 1
    print(f'Email to domain matches found: {len(match4)}')
    

    match5 = pd.merge(
        inst_EMEC.dropna(subset=['formated_email']),
        inst_SCOPUS.dropna(subset=['normalized_url']),
        left_on='formated_email',
        right_on='normalized_url',
        suffixes=('_A', '_B')
    )
    match5['email_url_match'] = 1
    print(f'Email to URL matches found: {len(match5)}')
    

    all_matches = pd.concat([match2, match3, match4, match5], ignore_index=True)
    all_matches = all_matches.drop_duplicates(subset=['B_original_index'], keep='first')

    agg_dict = {col: 'first' for col in all_matches.columns if col not in ['A_original_index', 'B_original_index']}
    agg_dict.update({
        'url_match': 'sum',
        'domain_match': 'sum',
        'email_domain_match': 'sum',
        'email_url_match': 'sum',
    })
    
    final_matches = all_matches.groupby(['A_original_index', 'B_original_index']).agg(agg_dict).reset_index()
    flag_columns = ['url_match', 'domain_match', 'email_domain_match', 'email_url_match']
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

matched_df = match_institutions(EMEC, SCOPUS)
institutions_b_with_counts = count_matches_for_b(SCOPUS, matched_df)

matched_df.drop(['A_original_index', 'level_0', 'B_original_index', 'normalized_domain', 'normalized_url', 'normalized_Sitio', 'formated_email'], axis=1, inplace=True, errors='ignore')
institutions_b_with_counts.drop(['level_0', 'normalized_domain', 'normalized_url'], axis=1, inplace=True, errors='ignore')

matched_df.to_csv('./data/code/matchDuplicatedNames/0_matchScopusToEMECByDomain/matches.csv', index=False)
institutions_b_with_counts.to_csv('./data/code/matchDuplicatedNames/0_matchScopusToEMECByDomain/counting.csv', index=False)