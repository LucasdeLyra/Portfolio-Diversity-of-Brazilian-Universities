import pandas as pd

# Read both counting files
counting_3 = pd.read_csv('./data/code/matchDuplicatedNames/3_matchScopusToEMECSpecialCases/2_matchFATEC/counting.csv', encoding='utf-8')
counting_3 = counting_3[counting_3['match_count'] == 0].copy()

counting_5 = pd.read_csv('./data/code/matchDuplicatedNames/5_matchRORToEMEC/counting.csv', encoding='utf-8')

# Find items in counting_5 with match_count > 0
matched_indices = counting_5[counting_5['match_count'].astype(int) > 0][['eid', 'afid']].copy()

# Remove rows from counting_3 that have a match in counting_5
# Use isin to filter out matched items
unmatched = counting_3[~counting_3.set_index(['eid', 'afid']).index.isin(
    matched_indices.set_index(['eid', 'afid']).index
)].reset_index(drop=True)

print(f"Items in counting_3: {len(counting_3)}")
print(f"Items in counting_5 with match_count > 0: {len(matched_indices)}")
print(f"Items remaining (unmatched): {len(unmatched)}")

# Save the result
unmatched.to_csv('./data/code/matchDuplicatedNames/6_fuzzyMatch/0_filter/counting.csv', index=False, encoding='utf-8', errors='replace')
print("Saved to ./data/code/matchDuplicatedNames/6_fuzzyMatch/0_filter/counting.csv")
