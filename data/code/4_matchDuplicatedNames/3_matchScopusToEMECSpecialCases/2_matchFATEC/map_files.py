import pandas as pd
import ast
import re
import unicodedata

def normalize_text(text):
    if pd.isna(text):
        return text
    text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', errors='ignore').decode('utf-8').lower()    
    text = re.sub(r'[\[\]()/\\-]', ' ', text)
    return text

EMEC = pd.read_csv(f'./data/data/raw/EMEC/EMEC_institutions.csv', encoding='utf-8', dtype=object)

# Load and prepare data
SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/1_matchPUC/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()

SCOPUS['normalized_variants'] = SCOPUS['variants'].apply(ast.literal_eval)
SCOPUS['normalized_variants'] = SCOPUS['normalized_variants'].apply(lambda lst: [normalize_text(item) for item in lst])
SCOPUS['normalized_name'] = SCOPUS['name'].apply(normalize_text)

# Filter EMEC where Sigla contains 'FATEC' or name contains 'FATEC'
EMEC_FATEC = EMEC[
    (EMEC['Sigla'].str.contains('FATEC', case=False, na=False)) | 
    (EMEC['Instituição(IES)'].str.contains('FATEC', case=False, na=False))
].copy()

EMEC_FATEC['normalized_name'] = EMEC_FATEC['Instituição(IES)'].apply(normalize_text)
EMEC_FATEC['normalized_state'] = EMEC_FATEC['UF'].apply(normalize_text)
EMEC_FATEC['normalized_municipio'] = EMEC_FATEC['Município'].apply(normalize_text)

print(f"EMEC rows with FATEC: {len(EMEC_FATEC)}")
print(EMEC_FATEC[['Instituição(IES)', 'Sigla', 'UF', 'Município']])
print("\n" + "="*80 + "\n")

# Search terms to look for in SCOPUS
search_terms = ['FATEC']
normalized_search_terms = [normalize_text(term) for term in search_terms]

# Check each SCOPUS row for matches
print("SCOPUS rows containing FATEC search terms:\n")
matches = []

for scopus_idx, scopus_row in SCOPUS.iterrows():
    scopus_name = str(scopus_row['normalized_name'])
    scopus_state = normalize_text(scopus_row['state'])
    scopus_city = normalize_text(scopus_row['city'])
    scopus_variants = scopus_row['normalized_variants']
    
    # Check if SCOPUS record contains FATEC
    if any(search_term in scopus_name for search_term in normalized_search_terms):
        # Find all possible EMEC matches in the same state
        best_match = None
        best_match_type = None
        
        for emec_idx, emec_row in EMEC_FATEC.iterrows():
            emec_name = str(emec_row['normalized_name'])
            emec_state = str(emec_row['normalized_state'])
            emec_city = str(emec_row['normalized_municipio'])
            
            # Only consider EMEC records in the same state
            if scopus_state != emec_state:
                continue
            
            # Check match types with priority
            state_match = scopus_state == emec_state
            city_match = scopus_city and emec_city and scopus_city == emec_city
            city_in_variants = False
            if isinstance(scopus_variants, list) and emec_city:
                city_in_variants = any(emec_city.lower() in str(var).lower() for var in scopus_variants)

            # Priority: city match > city in variants > state match
            if city_match:
                best_match = (emec_idx, emec_row)
                best_match_type = 'city'
                break  # Exact city match is best, use it immediately
            elif not best_match and city_in_variants:
                best_match = (emec_idx, emec_row)
                best_match_type = 'city_variant'
            elif not best_match and state_match:
                # Only set state match if no better match found yet
                best_match = (emec_idx, emec_row)
                best_match_type = 'state'

        if best_match:
            emec_idx, emec_row = best_match
            emec_name = str(emec_row['normalized_name'])
            emec_state = str(emec_row['normalized_state'])
            emec_city = str(emec_row['normalized_municipio'])
            matches.append({
                'scopus_idx': scopus_idx,
                'emec_idx': emec_idx,
                'scopus_row': scopus_row,
                'emec_row': emec_row,
                'match_type': best_match_type
            })

            print(f"Match found - SCOPUS {scopus_row['afid']}: {scopus_row['name']} ({scopus_state}, {scopus_city}) -> EMEC {emec_idx}: {emec_row['Instituição(IES)']} ({emec_state}, {emec_city})")
            print(f"  Match type: {best_match_type}")
            print()

print(f"\nTotal matches found: {len(matches)}")

# Save matches and counting CSVs
if matches:
    matches_list = []
    for m in matches:
        emec_row = m['emec_row'].to_dict()
        scopus_row = m['scopus_row'].to_dict()
        
        # Build the merged row with EMEC columns first, then SCOPUS with _B suffix
        merged_row = {**emec_row}
        
        # Add SCOPUS columns with _B suffix (except for normalized columns)
        for col, val in scopus_row.items():
            if col not in ['normalized_variants', 'normalized_name']:
                merged_row[col + '_B'] = val
        
        # Add identifiers and match info
        merged_row['B_original_index'] = m['scopus_idx']
        merged_row['FATEC_match'] = 1
        
        matches_list.append(merged_row)
    
    final_matches = pd.DataFrame(matches_list)
    final_matches = final_matches.drop_duplicates(subset=['B_original_index'], keep='first')
    # Remove _B suffix from column names
    final_matches.columns = [col.replace('_B', '') if '_B' in col else col for col in final_matches.columns]
    
    # Drop the normalized columns that shouldn't be in output
    final_matches = final_matches.drop(columns=['normalized_name', 'normalized_state', 'normalized_municipio'], errors='ignore')
    
    # Save matches
    final_matches.to_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/2_matchFATEC/matches.csv', index=False, encoding='utf-8', errors='replace')
    print(f"\nMatches saved to matches.csv with {len(final_matches)} rows")
    
    # Create counting dataframe (match counts per SCOPUS row)
    counting_df = SCOPUS.copy()
    counting_df.drop(['normalized_variants', 'normalized_name'], axis=1, inplace=True, errors='ignore')
    counting_df['match_count'] = 0
    
    for m in matches:
        counting_df.loc[m['scopus_idx'], 'match_count'] = 1
    
    # Save counting
    counting_df.to_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/2_matchFATEC/counting.csv', index=False, encoding='utf-8', errors='replace')
    print(f"Counting saved to counting.csv")
else:
    print("\nNo matches found. No CSV files created.")
