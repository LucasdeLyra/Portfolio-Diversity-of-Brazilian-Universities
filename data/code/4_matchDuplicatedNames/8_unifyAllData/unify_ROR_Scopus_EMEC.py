import pandas as pd
import os

# Define file paths
scopus_emec_domain_path = "./data/code/4_matchDuplicatedNames/0_matchScopusToEMECByDomain/matches.csv"
scopus_emec_emec_path = "./data/code/4_matchDuplicatedNames/1_matchScopusToEMECByName/matches.csv"
scopus_emec_emec_sigla = "./data/code/4_matchDuplicatedNames/2_matchScopusToEMECBySigla/matches.csv"
scopus_emec_special_cases1 = "./data/code/4_matchDuplicatedNames/3_matchScopusToEMECSpecialCases/0_matchUNESP/matches.csv"
scopus_emec_special_cases2 = "./data/code/4_matchDuplicatedNames/3_matchScopusToEMECSpecialCases/1_matchPUC/matches.csv"
scopus_emec_special_cases3 = "./data/code/4_matchDuplicatedNames/3_matchScopusToEMECSpecialCases/2_matchFATEC/matches.csv"
ror_emec_path = "./data/code/4_matchDuplicatedNames/5_matchRORToEMEC/matches.csv"
corrected_matches = "./data/code/4_matchDuplicatedNames/7_manualValidation/corrected_matches.csv"
manual_matches = "./data/code/4_matchDuplicatedNames/7_manualValidation/matches.csv"

file_paths = [scopus_emec_domain_path, scopus_emec_emec_path, scopus_emec_emec_sigla, scopus_emec_special_cases1, scopus_emec_special_cases2, scopus_emec_special_cases3,
              ror_emec_path, corrected_matches, manual_matches]
output_dir = "./data/data/refined/csvs"
output_path = os.path.join(output_dir, "institutions.csv")
emec_institutions_path = "./data/data/raw/EMEC/EMEC_institutions.csv"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Read all files from file_paths
dataframes = []
for file_path in file_paths:
    print(f"Reading {file_path}...")
    df = pd.read_csv(file_path)
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    dataframes.append(df)

# Define columns to drop from each file
columns_to_drop = {
    0: ['name_match', 'url_match', 'domain_match', 'variant_match', 'email_domain_match', 'email_url_match'],
    1: ['name_match', 'url_match', 'domain_match', 'variant_match'],
    2: ['name_match', 'url_match', 'domain_match', 'variant_match', 'name_to_sigla_match', 'variants_to_sigla_match', 'Sigla_A', 'Sigla_B', 'sigla_match'],
    3: ['name_match', 'url_match', 'domain_match', 'variant_match', 'unesp_match', 'A_original_index', 'B_original_index', 'Sigla_A'],
    4: ['matched_label', 'match_type', 'is_hospital', 'related_institution', 'name_match', 'url_match', 'domain_match', 'puc_match', 'B_original_index'],
    5: ['Sigla.1', 'match_count', 'B_original_index', 'FATEC_match', 'B_original_index'],
    6: ['eid', 'afid', 'scopus_name', 'ror_name', 'ror_id', 'matched_label', 'match_type', 'link', 'is_hospital', 'related_institution', 'name_match', 'url_match', 'domain_match', 'link_match'],
    7: ['similarity_score', 'match_type'],
    8: ['similarity_score', 'match_type']
}

# Drop columns from each dataframe
for i, df in enumerate(dataframes):
    cols_to_drop = [col for col in columns_to_drop[i] if col in df.columns]
    dataframes[i] = df.drop(columns=cols_to_drop)

# Rename scopus_name to name where it exists
for i, df in enumerate(dataframes):
    if 'scopus_name' in df.columns:
        dataframes[i] = df.rename(columns={'scopus_name': 'name'})

print("\nAfter dropping and renaming columns:")
for i, df in enumerate(dataframes):
    print(f"  File {i} columns: {list(df.columns)}")

# Get all unique columns across all dataframes
all_columns = set()
for df in dataframes:
    all_columns.update(df.columns)

# Add missing columns to each dataframe with NaN values
for i, df in enumerate(dataframes):
    for col in all_columns:
        if col not in df.columns:
            dataframes[i][col] = None

# Keep EMEC columns in their source order, then append non-EMEC columns alphabetically.
emec_columns = pd.read_csv(emec_institutions_path, nrows=0).columns.tolist()
ordered_columns = [col for col in emec_columns if col in all_columns]
ordered_columns.extend(sorted(all_columns - set(emec_columns)))
dataframes = [df[ordered_columns] for df in dataframes]

# Concatenate the dataframes
print("\nUnifying dataframes...")
unified_df = pd.concat(dataframes, ignore_index=True)
print(f"Unified shape: {unified_df.shape}")

# Save to CSV
print(f"\nSaving to {output_path}...")
unified_df.to_csv(output_path, index=False)
print("Done!")

# Print summary
print("\nSummary:")
print(f"Total rows: {len(unified_df)}")
print(f"Total columns: {len(unified_df.columns)}")
print(f"\nColumns in unified file:")
for i, col in enumerate(unified_df.columns, 1):
    print(f"  {i}. {col}")
