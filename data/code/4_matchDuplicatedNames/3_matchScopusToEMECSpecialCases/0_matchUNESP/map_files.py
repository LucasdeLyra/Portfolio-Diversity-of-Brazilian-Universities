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
SCOPUS = pd.read_csv('./data/code/matchDuplicatedNames/2_matchScopusToEMECBySigla/counting.csv', encoding='utf-8')
SCOPUS = SCOPUS[SCOPUS['match_count'] == 0].copy()


SCOPUS['normalized_variants'] = SCOPUS['variants'].apply(ast.literal_eval)
SCOPUS['normalized_variants'] = SCOPUS['normalized_variants'].apply(lambda lst: [normalize_text(item) for item in lst])
SCOPUS['normalized_name'] = SCOPUS['name'].apply(normalize_text)
# Extract Sigla from parentheses
SCOPUS['Sigla'] = SCOPUS['name'].str.extract(r'\(([^)]+)\)', expand=False)

# Filter EMEC where Sigla equals "UNESP"
EMEC_UNESP = EMEC[EMEC['Sigla'] == 'UNESP']
print(f"EMEC rows with Sigla='UNESP': {len(EMEC_UNESP)}")
print(EMEC_UNESP)
print("\n" + "="*80 + "\n")

# Search terms to look for in SCOPUS
search_terms = ['UNESP', 'UNIVERSIDADE ESTADUAL PAULISTA', 'JULIO DE MESQUITA FILHO']
normalized_search_terms = [normalize_text(term) for term in search_terms]
normalized_exclude_term = normalize_text('UNESPAR')

# Check each SCOPUS row for matches
print("SCOPUS rows containing search terms in normalized_variants, normalized_name, or Sigla:\n")
matches = []

for idx, row in SCOPUS.iterrows():
    found_match = False
    
    # Check normalized_variants
    normalized_variants = row['normalized_variants']
    if isinstance(normalized_variants, list):
        for variant in normalized_variants:
            variant_str = str(variant)
            # Exclude UNESPAR
            if normalized_exclude_term in variant_str:
                continue
            if any(search_term in variant_str for search_term in normalized_search_terms):
                found_match = True
                break
    
    # Check normalized_name
    if not found_match:
        name_str = str(row['normalized_name'])
        if normalized_exclude_term not in name_str and any(search_term in name_str for search_term in normalized_search_terms):
            found_match = True
    
    # Check Sigla
    if not found_match:
        sigla_str = str(row['Sigla'])
        if normalized_exclude_term not in sigla_str and any(search_term in sigla_str for search_term in normalized_search_terms):
            found_match = True
    
    if found_match:
        matches.append((idx, row))
        print(f"Row {idx}: {row['name']}")
        print(f"  Sigla: {row['Sigla']}")
        print(f"  Normalized name: {row['normalized_name']}")
        print(f"  Variants: {row['variants']}")
        print()

print(f"\nTotal matches found: {len(matches)}")

# Save matches and counting CSVs
if matches:
    # Extract SCOPUS indices from matches
    matches_indices = [m[0] for m in matches]
    matches_rows = [m[1] for m in matches]
    
    # Create a dataframe from matched SCOPUS rows and add original index
    scopus_matched_df = pd.DataFrame(matches_rows)
    scopus_matched_df['B_original_index'] = matches_indices
    
    # Perform cross-join between EMEC_UNESP and matched SCOPUS (all EMEC rows match all SCOPUS matches)
    # This is similar to how the other script does matches
    emec_reset = EMEC_UNESP.reset_index().rename(columns={'index': 'A_original_index'})
    scopus_reset = scopus_matched_df.reset_index(drop=True).rename(columns={'B_original_index': 'B_original_index'})
    
    # Create matches by merging - each EMEC_UNESP row gets matched with each SCOPUS match
    matched_df = emec_reset.copy()
    matched_df['key'] = 1
    scopus_reset['key'] = 1
    
    final_matches = pd.merge(matched_df, scopus_reset, on='key', suffixes=('_A', '_B'))
    final_matches = final_matches.drop_duplicates(subset=['B_original_index'], keep='first')

    final_matches.drop(['key', 'Sigla_B'], axis=1, inplace=True)
    
    
    # Add match flag
    final_matches['unesp_match'] = 1
    
    # Save matches
    final_matches.to_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/0_matchUNESP/matches.csv', index=False)
    print(f"\nMatches saved to matches.csv with {len(final_matches)} rows")
    
    # Create counting dataframe (match counts per SCOPUS row)
    counting_df = SCOPUS.copy()
    counting_df.drop(['normalized_variants', 'normalized_name'], axis=1, inplace=True)
    counting_df['match_count'] = 0
    
    for match_idx in matches_indices:
        counting_df.loc[match_idx, 'match_count'] = 1
    
    # Save counting
    counting_df.to_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/0_matchUNESP/counting.csv', index=False)
    print(f"Counting saved to counting.csv")
else:
    print("\nNo matches found. No CSV files created.")
