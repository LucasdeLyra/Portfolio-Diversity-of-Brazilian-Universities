# Institution matching

This folder contains the scripts and intermediate data used to link Scopus
affiliations to Brazilian higher-education institutions in e-MEC. The matching
process combines several approaches, uses ROR (Research Organization Registry)
as an additional source, and consolidates the selected matches into a unified
institution dataset.

## Contents

- `0_matchScopusToEMECByDomain/` — matches Scopus affiliations to e-MEC records
  using website and email-domain information.
- `1_matchScopusToEMECByName/` — matches institution names and name variants.
- `2_matchScopusToEMECBySigla/` — matches names and variants using institutional
  abbreviations (siglas).
- `3_matchScopusToEMECSpecialCases/` — separate matching scripts for UNESP,
  PUC, and FATEC.
- `4_matchScopusToROR/` — filters the ROR registry data to Brazilian
  organizations and matches Scopus affiliations to ROR records.
- `5_matchRORToEMEC/` — links ROR organizations to e-MEC institutions.
- `6_fuzzyMatch/` — applies fuzzy name matching to remaining unmatched records;
  includes a filter for prior ROR matches and a script for match statistics.
- `7_manualValidation/` — supports review and correction of candidate matches
  and records unmatched institutions.
- `8_unifyAllData/` — combines the matching outputs into
  `data/data/refined/csvs/institutions.csv`.

The subfolders contain Python scripts and, where applicable, CSV files with
candidate matches, match counts, manually reviewed results, and unmatched
records. The ROR matching folder also contains a Brazil-filtered ROR JSON
dataset. The matching scripts use the e-MEC institution file at
`data/data/raw/EMEC/EMEC_institutions.csv`.
