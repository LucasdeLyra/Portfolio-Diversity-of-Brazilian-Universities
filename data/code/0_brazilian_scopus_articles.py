"""
Purpose:
    Retrieves scientific articles authored by Brazilian institutions from the
    SCOPUS database across multiple years and subject areas.

Description:
    This script queries the SCOPUS API using the pybliometrics library to fetch
    articles matching specific criteria:
    - Publication year: 2015-2024
    - Author affiliation country: Brazil
    - Subject areas: Defined in subject_areas_abbreviation.json
    
    For each year-subject area combination, the script performs a SCOPUS search,
    retrieves results in STANDARD view format, converts results to a DataFrame,
    and exports to a CSV file for further processing.

Data Flow:
    1. Initialize SCOPUS API authentication using stored credentials
    2. Load subject area abbreviations from JSON configuration file
    3. For each year (2015-2024):
       - For each subject area:
         - Query SCOPUS API with year, country, and subject area filters
         - Convert results to pandas DataFrame
         - Export to CSV file in year-specific directory
    
    Input File:
        ./data/code/subject_areas_abbreviation.json
        
    Output Directory Structure:
        ./data/data/raw/scopus/
        ├── 2015/
        │   ├── AGRI_2015.csv
        │   ├── ARTS_2015.csv
        │   └── ...
        ├── 2016/
        │   └── ...
        └── 2024/
            └── ...

Output Format:
    CSV files with STANDARD view SCOPUS data including:
    - Article metadata (title, authors, publication year)
    - Citation information
    - Affiliation data
    - Subject area classifications
"""
from pybliometrics.scopus import ScopusSearch
from pybliometrics.scopus import init as ScopusInit
import pandas as pd
import json
import os

ScopusInit()

with open(f'./data/code/subject_areas_abbreviation.json', 'r') as subjareas_file:
    SUBJECT_AREAS = json.load(subjareas_file)['subject_areas']
    
    
for year in range(2015, 2025):
    for area in SUBJECT_AREAS:
        query = f'PUBYEAR = {year} AND AFFILCOUNTRY ( Brazil ) AND SUBJAREA ( {area} )'
        search = ScopusSearch(query, view='STANDARD', verbose=True)
        df = pd.DataFrame(search.results)
        output_file = f'./data/data/raw/scopus/{year}/{area}_{year}.csv'
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f'Saved results to {output_file}')
        