"""
Purpose:
    Processes article subject area data from a JSON source file and outputs
    a structured CSV file containing subject area codes, descriptions, and
    standardized abbreviations.

Description:
    This module reads a hierarchical JSON file containing main subject areas
    and their child subject areas (subareas), generates standardized 4-letter
    abbreviations for each subarea, and exports the results to a CSV file in
    the staging directory.

Data Structure:
    Input JSON Format:
        {
            'code': <int>,
            'desc': <str>,
            'child': [
                {
                    'code': <int>,
                    'desc': <str>
                },
                ...
            ]
        }
    
    Output CSV Columns:
        - code: Unique identifier for the subarea
        - area: Description/name of the subarea
        - abbreviation: 4-letter standardized abbreviation

Special Cases:
    - Main area code 15 (Computer Engineering) receives special abbreviation 'CENG'
      instead of the standard first 4 characters abbreviation
    - All other areas use uppercase first 4 characters of description as abbreviation

Input File:
    ./data/data/raw/article_subareas.json

Output File:
    ./data/data/staging/subject_area.csv
"""

import json
import csv
import os

STAGING_DIR = './data/data/staging'
REFINED_DIR = './data/data/refined'
os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(f'{REFINED_DIR}/csvs', exist_ok=True)

with open('./data/data/raw/article_subareas.json', 'r') as subject_areas_file:
    """
    Load the raw subject areas data from JSON file.
    
    Expects a list of area objects, each containing:
    - code: integer identifier
    - desc: string description of the area
    - child: list of subarea objects with their own code and desc
    """
    all_areas = json.load(subject_areas_file)
    subjareas = []
    for area in all_areas:
        abbreviation = area['desc'][:4].upper()
        if area['code'] == '15':
            abbreviation = 'CENG'
        for subarea in area['child']:
            subjareas.append({'code': subarea['code'], 'area': subarea['desc'], 'abbreviation': abbreviation})

with open(f'{STAGING_DIR}/subject_area.csv', 'w', encoding="utf-8", newline='') as articles:
    writer = csv.DictWriter(articles, fieldnames=['code', 'area', 'abbreviation'])
    writer.writerows(subjareas)
    
with open(f'{REFINED_DIR}/csvs/subject_area.csv', 'w', encoding="utf-8", newline='') as articles:
    writer = csv.DictWriter(articles, fieldnames=['code', 'area', 'abbreviation'])
    writer.writerows(subjareas)
