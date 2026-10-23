import pandas as pd
from rapidfuzz import fuzz, process
import concurrent.futures
import os
from collections import defaultdict
import re
import time


# Load and prepare data
EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)
EMEC.drop_duplicates(subset=['Código IES'], inplace=True)
print(len(EMEC))
# Drop specific institutions
EMEC = EMEC[~EMEC['Código IES'].isin(['13716', '17590', '24410', '26343', '12916', '1585', '21592', '4091', '16513', '21165', '23383', '715', '319', '22093', '202', '2656', '3979', '4598', '2500', '3981', '1652'])]
print(len(EMEC))

SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/6_fuzzyMatch/0_filter/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()
SCOPUS.drop(['match_count'], axis=1, inplace=True)


def normalize_name(name):
    """
    Normalize institution name for matching:
    - Convert to lowercase
    - Remove common institutional words
    - Remove special characters
    - Strip extra whitespace
    """
    if pd.isna(name):
        return ""
    
    name = str(name).lower().strip()
    
    # Remove common institutional words
    words_to_remove = [
        r'\bfundacao\b', r'\bfundaçao\b',
        r'\buniversidade\b', r'\buniv\b',
        r'\bcentro\b', r'\bcentro\s+universit\w*\b',
        r'\bfaculdade\b',
        r'\binstituto\b', r'\binst\b',
        r'\bcampus\b',
        r'\bescola\b',
        r'\bsociedade\b', r'\bsoc\b',
        r'\bempresa\b',
        r'\bltda\b', r'\bs\.?a\.?\b', r'\bs\.?a\.\s*$',
        r'\bme\b', r'\bepp\b',
        r'\bde\b', r'\bdo\b', r'\bda\b', r'\bdos\b', r'\bdas\b'
    ]
    
    for pattern in words_to_remove:
        name = re.sub(pattern, ' ', name)
    
    # Remove special characters
    name = re.sub(r'[^\w\s]', ' ', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def hierarchical_matching(scopus_df, emec_df, output_path='./data/code/matchDuplicatedNames/6_fuzzyMatch/matches_fast.csv'):
    """
    Hierarchical matching approach:
    1. Exact match on normalized names
    2. Fuzzy match (>90% similarity)
    3. Fuzzy match (>80% similarity)
    4. Fuzzy match (>70% similarity) for manual review
    """
    
    # Initialize results lists
    exact_matches = []
    fuzzy_90_matches = []
    fuzzy_80_matches = []
    fuzzy_70_matches = []
    unmatched = []
    
    # Prepare EMEC data (lists/dicts for faster access)
    emec_df['normalized_name'] = emec_df['Instituição(IES)'].apply(normalize_name)

    # Convert EMEC rows to list of dicts to avoid pandas overhead in inner loop
    emec_rows = []
    full_names = []
    name_to_indices = defaultdict(list)
    state_map = defaultdict(list)

    for list_idx, (df_idx, row) in enumerate(emec_df.iterrows()):
        norm = row['normalized_name']
        emec_rows.append(row.to_dict())
        full_names.append(norm)
        name_to_indices[norm].append(list_idx)  # Store list index, not df index
        st = str(row.get('UF', '')).strip().upper()
        state_map[st].append(norm)

    # Deduplicate candidate lists for faster searching
    for st in list(state_map.keys()):
        state_map[st] = list(dict.fromkeys(state_map[st]))

    print(f"Processing {len(scopus_df)} SCOPUS records (optimized)...")
    start = time.time()

    # Helper: match a single scopus row using RapidFuzz process.extractOne
    def match_one(scopus_row):
        scopus_name = scopus_row.get('name', '')
        scopus_state = scopus_row.get('state', '')
        scopus_normalized = normalize_name(scopus_name)

        if not scopus_normalized:
            return {'type': 'unmatched', 'record': {**scopus_row.to_dict(), 'match_type': 'no_normalized_name'}}

        st = str(scopus_state).strip().upper()

        # First, try candidates within same state (blocking)
        candidates = state_map.get(st, [])

        # If state candidates exist, check exact match first
        if candidates and scopus_normalized in candidates:
            # find emec index(es)
            emec_idxs = name_to_indices.get(scopus_normalized, [])
            if emec_idxs:
                emec_row = emec_rows[emec_idxs[0]]
                match_record = {}
                for col, val in emec_row.items():
                    if col != 'normalized_name':
                        match_record[col] = val
                for col in scopus_row.index:
                    match_record[f'{col}'] = scopus_row[col]
                match_record['similarity_score'] = 100
                match_record['match_type'] = 'exact_match'
                return {'type': 'matched', 'category': 'exact_match', 'record': match_record}

        # Use RapidFuzz to find best candidate among blocked candidates first (score cutoff 70)
        best = None
        if candidates:
            best = process.extractOne(scopus_normalized, candidates, scorer=fuzz.token_set_ratio, score_cutoff=70)

        # If no good match in state block, search global list
        if not best:
            best = process.extractOne(scopus_normalized, full_names, scorer=fuzz.token_set_ratio, score_cutoff=70)

        if best:
            matched_name, score, choice_idx = best
            # map matched_name to emec index (use first if multiple)
            emec_idxs = name_to_indices.get(matched_name, [])
            if not emec_idxs:
                return {'type': 'unmatched', 'record': {**scopus_row.to_dict(), 'match_type': 'no_match_found'}}
            emec_row = emec_rows[emec_idxs[0]]
            match_record = {}
            for col, val in emec_row.items():
                if col != 'normalized_name':
                    match_record[col] = val
            for col in scopus_row.index:
                match_record[f'{col}'] = scopus_row[col]
            match_record['similarity_score'] = score

            if score > 90:
                mt = 'fuzzy_90'
            elif score > 80:
                mt = 'fuzzy_80'
            else:
                mt = 'fuzzy_70'

            match_record['match_type'] = mt
            return {'type': 'matched', 'category': mt, 'record': match_record}

        # No match found
        return {'type': 'unmatched', 'record': {**scopus_row.to_dict(), 'match_type': 'no_match_found'}}

    # Use ThreadPoolExecutor to parallelize without pickling large structures
    max_workers = min(8, (os.cpu_count() or 1))
    i = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as exe:
        futures = []
        for idx, scopus_row in scopus_df.iterrows():
            futures.append(exe.submit(match_one, scopus_row))

        for fut in concurrent.futures.as_completed(futures):
            if not i%1000:
                print(i)
            i += 1
            res = fut.result()
            if res['type'] == 'matched':
                mr = res['record']
                if res['category'] == 'exact_match':
                    exact_matches.append(mr)
                elif res['category'] == 'fuzzy_90':
                    fuzzy_90_matches.append(mr)
                elif res['category'] == 'fuzzy_80':
                    fuzzy_80_matches.append(mr)
                elif res['category'] == 'fuzzy_70':
                    fuzzy_70_matches.append(mr)
            else:
                unmatched.append(res['record'])
            
    
    # Create results dataframe
    all_matches = exact_matches + fuzzy_90_matches + fuzzy_80_matches + fuzzy_70_matches
    results_df = pd.DataFrame(all_matches)
    
    # Save detailed results
    results_df.to_csv(output_path, index=False, encoding='utf-8')
    
    # Print summary statistics
    print("\n" + "="*60)
    print("HIERARCHICAL MATCHING RESULTS")
    print("="*60)
    print(f"Exact matches (100%):                {len(exact_matches):5d}")
    print(f"Fuzzy matches (>90%):                {len(fuzzy_90_matches):5d}")
    print(f"Fuzzy matches (80-90%):              {len(fuzzy_80_matches):5d}")
    print(f"Fuzzy matches (70-80%):              {len(fuzzy_70_matches):5d}")
    print(f"Unmatched records:                   {len(unmatched):5d}")
    print("-"*60)
    print(f"Total matched:                       {len(all_matches):5d}")
    print(f"Total records processed:             {len(scopus_df):5d}")
    print(f"Match rate:                          {len(all_matches)/len(scopus_df)*100:.1f}%")
    print("="*60)
    
    # Save unmatched for manual review
    if unmatched:
        unmatched_df = pd.DataFrame(unmatched)
        unmatched_df.to_csv('./data/code/matchDuplicatedNames/6_fuzzyMatch/unmatched_records_fast.csv', 
                            index=False, encoding='utf-8')
        print(f"\nUnmatched records saved to: unmatched_records_fast.csv")
    
    print(f"Detailed results saved to: {output_path}\n")
    
    return results_df, unmatched


# Run hierarchical matching
if __name__ == '__main__':
    results, unmatched = hierarchical_matching(SCOPUS, EMEC)