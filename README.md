# Ranking-Interdisciplinaridade

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Rebuilding the Scopus data

The raw Scopus records are not included in this repository. They must be
retrieved again through an account with Scopus API access. Your access may
depend on an institutional subscription. Obtain an API key from Elsevier and
configure `pybliometrics` on your computer before running the scripts. Keep the
key and any institutional token in the local `pybliometrics` configuration;
do not put credentials in this repository or share them.


The acquisition scripts call `ScopusInit()` from `pybliometrics` and use
relative paths from the repository root. The first run may ask you to configure
the API credentials. Check the `pybliometrics` configuration documentation if
you need to configure it manually.

### Scopus APIs used

The data collection workflow uses three Elsevier Scopus APIs through
`pybliometrics`:

| API | Purpose in this project | View used | Views documentation | Script |
| --- | --- | --- | --- | --- |
| [Scopus Search API](https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl) | Finds Brazilian articles by publication year and subject area. | `STANDARD` | [Search API views](https://dev.elsevier.com/sc_search_views.html) | `data/code/0_brazilian_scopus_articles.py` |
| [Abstract Retrieval API](https://dev.elsevier.com/documentation/AbstractRetrievalAPI.wadl) | Retrieves full article metadata, including authors and their affiliations, for each search result. | `FULL` | [Abstract Retrieval views](https://dev.elsevier.com/sc_abstract_retrieval_views.html) | `data/code/1_fetchArticle/fetch_article.py` |
| [Affiliation Retrieval API](https://dev.elsevier.com/documentation/AffiliationRetrievalAPI.wadl) | Retrieves additional details for each institution using its Scopus affiliation ID. | `STANDARD` | [Affiliation Retrieval views](https://dev.elsevier.com/sc_affil_retrieval_views.html) | `data/code/2_fetchInstitutions/get_scopus_institutions.py` |

### 1. Search for Brazilian articles

Run:

```powershell
python .\data\code\0_brazilian_scopus_articles.py
```

This queries publication years 2015–2024 for Brazil and the subject-area codes
in `data/code/subject_areas_abbreviation.json`. It writes one search-results
CSV per year and subject area under `data/data/raw/scopus/`. These search
results are the input to the full-record retrieval step.

### 2. Retrieve full article and author-affiliation records

Run the sequential mode:

```powershell
python .\data\code\1_fetchArticle\fetch_article.py single
```

For each search result, the script requests the full Scopus record and writes
yearly CSVs for articles, subject areas, authors, and author-institution
affiliations under `data/data/staging/<year>/`. Sequential mode is slower but
limits concurrent API requests. The script records progress in
`data/code/1_fetchArticle/CHECKPOINT` and failed EIDs in
`data/code/1_fetchArticle/ERRORS`. Review the error log before continuing:
failed EIDs may need a targeted retry because a later checkpoint can advance
past an earlier failed record.

If you need to rebuild the files from the beginning, first back up any staging
CSV files and the checkpoint. Then remove only the generated checkpoint and
staging outputs for the years being rebuilt; otherwise completed checkpoint
entries may cause records to be skipped, or reruns may append duplicate rows.
For a full rebuild of the institution details, also back up and remove
`data/code/2_fetchInstitutions/CHECKPOINT` and
`data/data/staging/aux_institutions.csv` before rerunning that step. Do not
remove the raw inputs or other project data.

### 3. Consolidate and normalize the records

After the retrieval step has completed, run:

```powershell
python .\data\code\3_refine_data.py
```

This combines the yearly staging CSVs, removes duplicates, and writes refined
CSVs to `data/data/refined/csvs/`. It also creates
`data/data/staging/articles_institution.csv`, which is required by the next
step.

### 4. Retrieve Scopus institution details

Run:

```powershell
python .\data\code\2_fetchInstitutions\get_scopus_institutions.py
```

This uses Brazilian affiliation IDs from
`data/data/staging/articles_institution.csv` to request affiliation details.
Results are written to `data/data/staging/aux_institutions.csv`, with progress
in `data/code/2_fetchInstitutions/CHECKPOINT` and errors in
`data/code/2_fetchInstitutions/ERRORS`.

### 5. Prepare subject areas and other source data

The repository includes `data/data/raw/article_subareas.json`. Generate its
CSV form with:

```powershell
python .\data\code\1_subject_areas.py
```

The CiteScore and Brazilian education-institution (EMEC) data are separate
inputs, not fetched by the Scopus article scripts:

- `0_refine_citescore.py` expects
  `data/data/raw/CiteScore_2024_annual_values.csv` and
  `data/data/raw/article_subareas.json`. Obtain the CiteScore source file
  through an authorized Elsevier source, place it at that path, and run
  `python .\data\code\0_refine_citescore.py`. In our case, we got those by requesting Elsevier's support through e-mail.
- `0_unify_EMEC_files.py` combines `.xls` files placed in
  `data/data/raw/EMEC/` into `EMEC_institutions.csv`. Obtain those source files
  from the relevant official source before running it.

These scripts prepare CSV data; they do not create the Parquet files required
by the analysis workflow below. Raw Scopus and other proprietary source data
are not redistributed by this project. API availability, quota, subscription
rights, and current Scopus records determine what can be recovered.


## Analysis

The analysis requires the data acquisition and preparation described above, as
well as the Parquet inputs listed below. The acquisition scripts produce CSVs;
this repository does not currently provide a CSV-to-Parquet conversion step.

The main analysis is available as python a notebook at `analysis/basic_analysis.ipynb`

The analysis prints the number of distinct IES codes (`ins_code`) associated
with at least one `Article` after its data joins. It also writes
`analysis/data/institution_article_counts.csv`, with one row per IES code and
the number of distinct articles associated with that institution, plus its
`ins_category` and `ins_status`.

The implementation reads the affiliation data in bounded Arrow batches, uses a
short-lived SQLite database for article-level author counts, and runs its
counting and aggregation stages in separate Python processes. This avoids the
full in-memory merge that can exhaust system memory. Arrow is configured to run
single-threaded in the documented smoke command:

The input Parquet directory must contain at least:

- `article.parquet`
- `citescore.parquet`
- `authors_institution.parquet`
- `institutions.parquet`
- `subject_area.parquet`

The analysis writes macro- and subject-area ranking folders under
`analysis/data/macro`, `analysis/data/sub`, and `analysis/data/sensitivity`. Each
ranking folder contains `rank.txt`, `labels.csv`, `institutions_names.csv`, and
`zeros_count.csv`.

## External Interdisc step

`interdis.csv` is produced by the external Leydesdorff/Zhang Interdisc 2020
program, not by this Python repository. The software documentation is available
at <https://www.leydesdorff.net/software/interdisc.2020/index.htm>.

That tool expects the matrix and labels in its documented format and computes
fields including `DIV_STAR`, `DIV`, Rao-Stirling, Simpson, variety, disparity,
and Gini measures. The external executable is Windows-oriented and is not
installed by `requirements.txt`. Raw Scopus records and other proprietary data
are not redistributed by this project.

Once external `interdis.csv` files are placed beside their corresponding
`institutions_names.csv`, sort and merge them with RUF data using:

```bash
python3 analysis/order_interdis.py
```

This writes `sorted_interdis.csv` beside each valid Interdisc result.
