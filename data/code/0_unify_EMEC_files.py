"""
Purpose:
    This script consolidates multiple EMEC (Ministério da Educação - Brazilian Education Ministry)
    institution data files into a single unified CSV file.

Description:
    The script reads all Excel files (.xls) from the EMEC directory, extracts the first table
    from each file using pandas' HTML parsing capability, and combines them into a single
    DataFrame. The consolidated data is then exported to a CSV file for further analysis.

Data Source:
    - Input: Multiple .xls files located in './data/data/raw/EMEC/'
    - Output: Single unified CSV file at './data/data/raw/EMEC/EMEC_institutions.csv'
"""

import pandas as pd
import os


def unify_emec_files():
    """
    Unify multiple EMEC institution files into a single CSV.
    
    Process:
        1. Lists all files in the './data/data/raw/EMEC/' directory
        2. Filters for Excel files (.xls extension)
        3. Reads each .xls file using pandas' HTML parser
        4. Extracts the first table from each file
        5. Concatenates all tables into a single DataFrame
        6. Saves the unified data to a CSV file
    
    Returns:
        None
        
    Side Effects:
        Creates/overwrites './data/data/raw/EMEC/EMEC_institutions.csv'
        
    Raises:
        FileNotFoundError: If the EMEC directory does not exist
        Exception: If Excel files cannot be parsed
    """
    files = []
    
    for file in os.listdir('./data/data/raw/EMEC'):
        if file.endswith('.xls'):
            print(f'Processing file: {file}')
            try:
                df = pd.read_html(f'./data/data/raw/EMEC/{file}')[0]
                files.append(df)
                print(f'  ✓ Successfully loaded: {len(df)} rows')
            except Exception as e:
                print(f'  ✗ Error processing {file}: {str(e)}')
    
    if not files:
        print('Warning: No .xls files found or loaded from EMEC directory')
        return
    
    print(f'\nCombining {len(files)} files...')
    
    combined = pd.concat(files, ignore_index=True)
    
    print(f'Combined dataset shape: {combined.shape[0]} rows × {combined.shape[1]} columns')
    print(f'Columns: {list(combined.columns)}')
    
    output_file = './data/data/raw/EMEC/EMEC_institutions.csv'
    combined.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f'\n✓ Successfully saved to: {output_file}')
    print(f'File size: {combined.memory_usage(deep=True).sum() / 1024:.2f} KB')


if __name__ == '__main__':
    unify_emec_files()