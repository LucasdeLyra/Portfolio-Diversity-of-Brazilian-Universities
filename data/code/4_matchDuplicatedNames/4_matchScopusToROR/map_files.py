from collections import defaultdict
import pandas as pd
import json
import re

def normalize_site(url):
    url = str(url).lower().strip()
    url = url.replace('http://', '')
    url = url.replace('https://', '') 
    url = url.replace('www.', '')
    url = url.replace('www2.', '')
    url = url.replace('www3.', '')
    url = url.replace('www4.', '')
    url = url.replace('www5.', '')
    url = url.replace('internacional.', '')
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

def normalize_name(text):
    if pd.isna(text):
        return text
    return str(text).normalize('NFKD').encode('ascii', errors='ignore').decode('utf-8').lower()

# Load and prepare data
SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/2_matchFATEC/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()

with open('./data/code/matchDuplicatedNames/4_matchScopusToROR/ror_brazil.json', 'r', encoding='utf-8') as f:
    ROR_DATA = json.load(f)

# Convert ROR data to DataFrame
ror_rows = []
for inst in ROR_DATA:
    if not inst:
        continue
    labels_list = []
    for label_obj in inst.get('labels', []):
        if isinstance(label_obj, dict) and 'label' in label_obj:
            labels_list.append(label_obj['label'])
        elif isinstance(label_obj, str):
            labels_list.append(label_obj)
    
    acronyms_list = inst.get('acronyms', [])
    
    aliases_list = inst.get('aliases', [])
    
    row = {
        'ror_id': inst.get('id', ''),
        'name': inst.get('name', ''),
        'links': inst.get('links', []),
        'labels': labels_list,
        'acronyms': acronyms_list,
        'aliases': aliases_list,
        'relationships': inst.get('relationships', [])
    }
    ror_rows.append(row)

ROR = pd.DataFrame(ror_rows)

SCOPUS['normalized_domain'] = SCOPUS['domain'].apply(normalize_site)
SCOPUS['normalized_url'] = SCOPUS['url'].apply(normalize_site)
SCOPUS['normalized_name'] = SCOPUS['name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower().apply(lambda x: re.sub(r'\s*\([^)]*\)', '', x)).str.strip().apply(lambda x: re.sub(r'[\[\]()/\\-]', '', x))
SCOPUS['normalized_variants'] = SCOPUS['variants'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower().apply(lambda x: re.sub(r'\s*\([^)]*\)', '', x)).str.strip().apply(lambda x: re.sub(r'[\[\]()/\\-]', '', x))


def normalize_label(label_list):
    """Normalize a list of labels (now they're already extracted as strings)"""
    if not isinstance(label_list, list):
        return []
    normalized_labels = []
    for label in label_list:
        if isinstance(label, str):
            normalized = str(label).lower().strip()
            normalized = normalized.encode('utf-8').decode('utf-8')
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized = re.sub(r'\s*\([^)]*\)', '', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized_labels.append(normalized)
    return normalized_labels

ROR['normalized_name'] = ROR['name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower().apply(lambda x: re.sub(r'\s*\([^)]*\)', '', x)).str.strip().apply(lambda x: re.sub(r'[\[\]()/\\-]', '', x))
ROR['normalized_labels'] = ROR['labels'].apply(normalize_label)
ROR['normalized_links'] = ROR['links'].apply(normalize_site)

print(ROR['normalized_links'])

# Build a dictionary to map ROR IDs to their institution names (for hospital relationships)
ROR_ID_TO_NAME = dict(zip(ROR['ror_id'], ROR['name']))

# Check if institution is a hospital
ROR['is_hospital'] = ROR['name'].str.lower().str.contains('hospital', na=False)

# For hospitals, find their related institutions
def get_related_institution(relationships):
    """Extract the name of related institutions from relationships"""
    if not isinstance(relationships, list) or len(relationships) == 0:
        return ''
    
    related_names = []
    for rel in relationships:
        if isinstance(rel, dict):
            # Get the related institution ID
            related_id = rel.get('id', '')
            # Look up the name in ROR_ID_TO_NAME
            if related_id in ROR_ID_TO_NAME:
                related_names.append(ROR_ID_TO_NAME[related_id])
    
    # Return the first related institution name, or empty string if none
    return related_names[0] if related_names else ''

ROR['related_institution'] = ROR['relationships'].apply(get_related_institution)


def match_with_ror_data():
    all_matches = []
    
    # 1. Match by domain
    if 'normalized_domain' in SCOPUS.columns:
        ror_links = ROR.explode('normalized_links').dropna(subset=['normalized_links'])
        domain_matches = pd.merge(
            SCOPUS.dropna(subset=['normalized_domain']),
            ror_links,
            left_on='normalized_domain',
            right_on='normalized_links',
            how='inner'
        )
        domain_matches['match_type'] = 'domain'
        domain_matches['matched_label'] = ''
        print(f'Domain matches found: {len(domain_matches)}')
        all_matches.append(domain_matches)
    
    # 2. Match by URL
    if 'normalized_url' in SCOPUS.columns:
        ror_links = ROR.explode('normalized_links').dropna(subset=['normalized_links'])
        url_matches = pd.merge(
            SCOPUS.dropna(subset=['normalized_url']),
            ror_links,
            left_on='normalized_url',
            right_on='normalized_links',
            how='inner'
        )
        url_matches['match_type'] = 'url'
        url_matches['matched_label'] = ''
        print(f'URL matches found: {len(url_matches)}')
        all_matches.append(url_matches)
    
    # 3. Match by exact name
    if 'normalized_name' in SCOPUS.columns:
        name_matches = pd.merge(
            SCOPUS.dropna(subset=['normalized_name']),
            ROR,
            left_on='normalized_name',
            right_on='normalized_name',
            how='inner'
        )
        name_matches['match_type'] = 'name'
        name_matches['matched_label'] = ''
        print(f'Name matches found: {len(name_matches)}')
        all_matches.append(name_matches)
    
    # 4. Match SCOPUS variants with ROR labels (English labels)
    if 'normalized_variants' in SCOPUS.columns:
        scopus_variants = SCOPUS.explode('normalized_variants').dropna(subset=['normalized_variants'])
        ror_labels = ROR.explode('normalized_labels').dropna(subset=['normalized_labels'])
        
        variant_label_matches = pd.merge(
            scopus_variants,
            ror_labels,
            left_on='normalized_variants',
            right_on='normalized_labels',
            how='inner'
        )
        # Store the matched label
        variant_label_matches['matched_label'] = variant_label_matches['normalized_labels']
        variant_label_matches['match_type'] = 'variant_label'
        print(f'Variant-Label matches found: {len(variant_label_matches)}')
        all_matches.append(variant_label_matches)
    
    # 5. Match SCOPUS name with ROR labels
    if 'normalized_name' in SCOPUS.columns:
        scopus_names = SCOPUS[['eid', 'afid', 'name', 'normalized_name', 'domain', 'url']].copy()
        ror_labels = ROR.explode('normalized_labels').dropna(subset=['normalized_labels'])
        
        name_label_matches = pd.merge(
            scopus_names,
            ror_labels,
            left_on='normalized_name',
            right_on='normalized_labels',
            how='inner'
        )
        # Store the matched label
        name_label_matches['matched_label'] = name_label_matches['normalized_labels']
        name_label_matches['match_type'] = 'name_label'
        print(f'Name-Label matches found: {len(name_label_matches)}')
        all_matches.append(name_label_matches)
    
    if not all_matches:
        print("No matches found!")
        return pd.DataFrame()
    
    # Combine all matches
    combined_matches = pd.concat(all_matches, ignore_index=True)
    
    # Build the result with available columns
    result_list = []
    for _, row in combined_matches.iterrows():
        ror_name = row.get('name_y') or row.get('name')
        # Check if the ROR institution is a hospital
        is_hospital = 'hospital' in ror_name.lower() if isinstance(ror_name, str) else False
        
        # Get related institution (for hospitals, get the related university)
        related_institution = ''
        if is_hospital:
            # Find the ROR entry for this institution to get relationships
            ror_id = row.get('ror_id')
            matching_ror = ROR[ROR['ror_id'] == ror_id]
            if not matching_ror.empty:
                related_institution = matching_ror.iloc[0]['related_institution']
        
        result_row = {
            'eid': row.get('eid'),
            'afid': row.get('afid'),
            'scopus_name': row.get('name_x') or row.get('name'),
            'domain': row.get('domain', ''),
            'url': row.get('url', ''),
            'ror_name': ror_name,
            'ror_id': row.get('ror_id'),
            'matched_label': row.get('matched_label', ''),
            'match_type': row.get('match_type'),
            'link': row.get('normalized_links'),
            'city': row.get('city'),
            'state': row.get('state'),
            'is_hospital': is_hospital,
            'related_institution': related_institution
        }
        result_list.append(result_row)

    final_matches = pd.DataFrame(result_list)
    final_matches = final_matches.drop_duplicates(subset=['eid', 'ror_id'], keep='first')
    
    return final_matches

def main():
    exact_matches = match_with_ror_data()
    print(f"\nExact matches found: {len(exact_matches)}")
    
    exact_matches.to_csv('./data/code/matchDuplicatedNames/4_matchScopusToROR/ror_matches.csv', index=False, encoding='utf-8')
    print(f"\nTotal matches found: {len(exact_matches)}")
    print("Matches saved to ror_matches.csv")
    
    print("\nMatches by type:")
    print(exact_matches['match_type'].value_counts())


if __name__ == "__main__":
    main()
