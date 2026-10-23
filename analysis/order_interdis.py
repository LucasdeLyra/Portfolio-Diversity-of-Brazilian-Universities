import pandas as pd
from pathlib import Path
import re

def normalize_text(text):
    """Normalize text: NFKD, remove accents, lowercase, remove parentheses content"""
    return text.str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower().apply(lambda x: re.sub(r'\s*\([^)]*\)', '', x))

# Load RUF data once at the start
ruf = pd.read_csv('./analysis/data/RUF.csv', encoding="utf-8", delimiter=';')
ruf['normalized_Universidade'] = normalize_text(ruf['Universidade'])
print(f"✓ Loaded RUF data: {len(ruf)} rows\n")

sensitivity_macro_folder = Path('./analysis/data/sensitivity/macro')
sensitivity_sub_folder = Path('./analysis/data/sensitivity/sub')
macro_folder = Path('./analysis/data/macro')
sub_folder = Path('./analysis/data/sub')

sensitivity_macro_files = list(sensitivity_macro_folder.glob('**/interdis.csv'))
sensitivity_sub_files = list(sensitivity_sub_folder.glob('**/interdis.csv'))
macro_files = list(macro_folder.glob('**/interdis.csv'))
sub_files = list(sub_folder.glob('**/interdis.csv'))

interdis_files = macro_files + sub_files + sensitivity_macro_files + sensitivity_sub_files

print(f"Found {len(macro_files)} interdis.csv files in macro folder")
print(f"Found {len(sensitivity_macro_files)} interdis.csv files in sensitivity macro folder")
print(f"Found {len(sub_files)} interdis.csv files in sub folder")
print(f"Found {len(sensitivity_sub_files)} interdis.csv files in sensitivity sub folder")
print(f"Total: {len(interdis_files)} files\n")

for file_path in interdis_files:
    print(f"\nProcessing: {file_path}")
    
    df = pd.read_csv(file_path, encoding='utf-8')
    
    # Load institution names from the same folder
    institutions_file = file_path.parent / 'institutions_names.csv'
    if institutions_file.exists():
        institutions = pd.read_csv(institutions_file, encoding='utf-8')
        df['LABEL'] = institutions['ins_name']
        df['normalized_name'] = normalize_text(df['LABEL'])
        
        # Merge with RUF data using normalized names
        df = df.merge(ruf[['normalized_Universidade', 'Ranking', 'Universidade']], 
                      left_on='normalized_name', 
                      right_on='normalized_Universidade', 
                      how='left')
        print(f"  Merged with RUF: {df['Ranking'].notna().sum()} institutions matched")
    else:
        print(f"  ⚠ No institutions_names.csv found in {file_path.parent}")
    
    # Sort by DIV_STAR
    df_sorted = df.sort_values('DIV_STAR', ascending=False)
    df_sorted.index = pd.RangeIndex(start=1, stop=len(df) + 1)

    output_path = file_path.parent / 'sorted_interdis.csv'
    df_sorted.to_csv(output_path, encoding='utf-8')
    
    print(f"✓ Sorted {len(df_sorted)} rows by DIV_STAR (descending)")
    print(f"  Saved to: {output_path}")

print("\n✓ All files ordered successfully!")
