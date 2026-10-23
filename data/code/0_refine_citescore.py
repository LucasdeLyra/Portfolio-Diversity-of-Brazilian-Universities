import polars as pl
import json
import os

# Load CiteScore data
citeScore = pl.read_csv(
    './data/data/raw/CiteScore_2024_annual_values.csv',
    infer_schema_length=10000
)

# Load article subareas JSON
with open('./data/data/raw/article_subareas.json', 'r') as f:
    subareas = json.load(f)

# Create a mapping from main area name to its children
def build_area_mapping(subareas_list):
    """Build a mapping from parent area name to list of child descriptions"""
    mapping = {}

    for area in subareas_list:
        parent_name = area.get('desc')
        children = area.get('child', [])

        child_descriptions = [
            child.get('desc')
            for child in children
            if child.get('desc') is not None
        ]

        if child_descriptions:
            mapping[parent_name] = child_descriptions

    return mapping

area_mapping = build_area_mapping(subareas)

# Find rows with " (all)"
all_rows = citeScore.filter(
    pl.col('Scopus Sub-Subject Area').str.ends_with(' (all)')
)

# If there are rows to expand
if all_rows.height > 0:

    new_rows = []

    # Iterate over rows
    for row in all_rows.iter_rows(named=True):

        area_name = row['Scopus Sub-Subject Area']

        # Remove " (all)"
        parent_area = area_name.replace(' (all)', '')

        # Expand into child areas
        if parent_area in area_mapping:

            for child_area in area_mapping[parent_area]:

                new_row = row.copy()
                new_row['Scopus Sub-Subject Area'] = child_area

                new_rows.append(new_row)

    # Remove original "(all)" rows
    citeScore_filtered = citeScore.filter(
        ~pl.col('Scopus Sub-Subject Area').str.ends_with(' (all)')
    )

    # Add expanded rows
    if new_rows:

        expanded_df = pl.DataFrame(new_rows)

        result = pl.concat(
            [citeScore_filtered, expanded_df],
            how='vertical'
        )

    else:
        result = citeScore_filtered

    print(f"Expanded {all_rows.height} '(all)' records into {len(new_rows)} new records")
    print(f"Total rows after expansion: {result.height}")

    # Save result
    os.makedirs('./data/data/refined/csvs', exist_ok=True)
    result.write_csv('./data/data/refined/csvs/citescore.csv')

    print("\nSaved expanded data to ./data/data/refined/csvs/citescore.csv")

else:
    print("No records with ' (all)' found in Scopus Sub-Subject Area")