from pybliometrics.scopus import AffiliationRetrieval
from pybliometrics.scopus import init as ScopusInit
import pandas as pd
from collections import defaultdict
import json
import concurrent.futures
import os

ScopusInit()

CURRENT_DIR = './data/code/2_fetchInstitutions'
CHECKPOINT_PATH = f'{CURRENT_DIR}/CHECKPOINT'
ERROR_PATH = f'{CURRENT_DIR}/ERRORS'

def load_checkpoint():
    if not os.path.exists(CHECKPOINT_PATH):
        return set()
    try:
        with open(CHECKPOINT_PATH, 'r') as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()

def save_checkpoint(processed_afids):
    with open(CHECKPOINT_PATH, 'w') as f:
        json.dump(list(processed_afids), f)

def log_error(afid, error_msg):
    with open(ERROR_PATH, 'a+') as error_log:
        error_log.write(f'{afid}: {error_msg}\n')
        
def fetch_affiliation(index, afid, processed_afids):
    try:
        affiliation = AffiliationRetrieval(afid)
        result = {
            'eid': affiliation.eid,
            'index': index,
            'afid': afid,
            'name': affiliation.affiliation_name,
            'domain': affiliation.org_domain,
            'url': affiliation.org_URL,
            'org_type': affiliation.org_type,
            'state': affiliation.state,
            'city': affiliation.city,
            'variants': [v.name for v in (affiliation.name_variants or [])]
        }
        processed_afids.add(afid)
        save_checkpoint(processed_afids)
        return result
    except Exception as e:
        print(f'Error retrieving affiliation {afid}: {e}')
        log_error(afid, str(e))
        return None
    
def main():
    df = pd.read_csv(f'./data/data/staging/articles_institution.csv', encoding='utf-8', dtype=object)
    df.drop_duplicates(subset=['afid'], inplace=True)
    df = df.loc[df['country'].isin(['Brazil', 'Brasil'])]
    df = df.reset_index(drop=True)

    processed_afids = load_checkpoint()
    # Filter out already processed AFIDs
    df = df[~df['afid'].isin(processed_afids)]
    df = df.reset_index(drop=True)
    
    affiliations_data = []
    # Load existing data if file exists
    if os.path.exists('./data/data/staging/aux_institutions.csv'):
        try:
            existing_df = pd.read_csv('./data/data/staging/aux_institutions.csv', encoding='utf-8', dtype=object)
            affiliations_data = existing_df.to_dict('records')
        except Exception as e:
            print(f'Could not load existing aux_institutions.csv: {e}')
    
    max_workers = 5  # Adjust as needed

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        length = len(df)
        j = 0
        
        for i, row in df.iterrows():
            futures.append(executor.submit(fetch_affiliation, i, row.afid, processed_afids))
        
        for future in concurrent.futures.as_completed(futures):
            j += 1
            if j % 100 == 0:
                print(f'Processed {j}/{length} affiliations')
            result = future.result()
            if result:
                affiliations_data.append(result)
    
    # Only write if there's data to write
    if affiliations_data:
        df = pd.DataFrame(affiliations_data)
        df.to_csv('./data/data/staging/aux_institutions.csv', index=False, encoding='utf-8')
    else:
        print('No new affiliations to process')
    
    # Process the results
    name_map = defaultdict(list)
    domain_map = defaultdict(list)
    url_map = defaultdict(list)
    variant_map = defaultdict(list)

    for aff in affiliations_data:
        if aff['name']:
            name_map[str(aff['name']).lower()].append(aff['afid'])
        if aff['domain']:
            domain_map[str(aff['domain']).lower()].append(aff['afid'])
        if aff['url']:
            url_map[str(aff['url']).lower()].append(aff['afid'])
        for v in aff['variants']:
            variant_map[str(v).lower()].append(aff['afid'])

    name_map_json = {k: list(set(v)) for k, v in name_map.items()}
    
    with open('./data/code/fetchInstitutions/duplicates.json', 'w', encoding='utf-8') as json_file:
        json.dump(name_map_json, json_file, indent=4)

if __name__ == '__main__':
    main()