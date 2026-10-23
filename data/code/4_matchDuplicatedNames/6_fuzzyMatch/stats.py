import pandas as pd
from collections import Counter

# Read the CSV file
df = pd.read_csv('./data/code/matchDuplicatedNames/6_fuzzyMatch/matches_fast.csv')

print("=" * 80)
print("BASIC STATISTICS ABOUT matches.csv")
print("=" * 80)

# Basic info
print(f"\nTotal records: {len(df)}")
print(f"Total columns: {len(df.columns)}")

# Most repeated Código Mantenedora
print("\n" + "=" * 80)
print("TOP 15 MOST REPEATED 'Código Mantenedora'")
print("=" * 80)
top_mantenedora = df['Código Mantenedora'].value_counts().head(15)
for i, (codigo, count) in enumerate(top_mantenedora.items(), 1):
    print(f"{i:2d}. Código {codigo}: {count} occurrences")

# Most repeated Código IES
print("\n" + "=" * 80)
print("TOP 15 MOST REPEATED 'Código IES'")
print("=" * 80)
top_ies = df['Código IES'].value_counts().head(15)
for i, (codigo, count) in enumerate(top_ies.items(), 1):
    print(f"{i:2d}. Código {codigo}: {count} occurrences")

# Most repeated Sigla (if available)
print("\n" + "=" * 80)
print("TOP 15 MOST REPEATED 'Sigla'")
print("=" * 80)
top_sigla = df['Sigla'].value_counts().head(15)
for i, (sigla, count) in enumerate(top_sigla.items(), 1):
    if pd.isna(sigla) or sigla == '':
        sigla_display = "[Empty/NaN]"
    else:
        sigla_display = sigla
    print(f"{i:2d}. {sigla_display}: {count} occurrences")

# Most repeated Institution names
print("\n" + "=" * 80)
print("TOP 15 MOST REPEATED 'Instituição(IES)'")
print("=" * 80)
top_inst = df['Instituição(IES)'].value_counts().head(15)
for i, (inst, count) in enumerate(top_inst.items(), 1):
    print(f"{i:2d}. {inst}: {count} occurrences")

# Statistics by UF
print("\n" + "=" * 80)
print("DISTRIBUTION BY STATE (UF)")
print("=" * 80)
uf_counts = df['UF'].value_counts().sort_values(ascending=False)
for uf, count in uf_counts.items():
    print(f"{uf}: {count}")

# Statistics by Categoria Administrativa
print("\n" + "=" * 80)
print("DISTRIBUTION BY 'Categoria Administrativa'")
print("=" * 80)
cat_admin = df['Categoria Administrativa'].value_counts()
for cat, count in cat_admin.items():
    print(f"{cat}: {count}")

# Statistics by Organização Acadêmica
print("\n" + "=" * 80)
print("DISTRIBUTION BY 'Organização Acadêmica'")
print("=" * 80)
org_acad = df['Organização Acadêmica'].value_counts()
for org, count in org_acad.items():
    print(f"{org}: {count}")

# Match type distribution
print("\n" + "=" * 80)
print("DISTRIBUTION BY 'match_type'")
print("=" * 80)
match_type = df['match_type'].value_counts()
for mtype, count in match_type.items():
    print(f"{mtype}: {count}")

# Similarity score statistics
print("\n" + "=" * 80)
print("SIMILARITY SCORE STATISTICS")
print("=" * 80)
print(f"Min: {df['similarity_score'].min()}")
print(f"Max: {df['similarity_score'].max()}")
print(f"Mean: {df['similarity_score'].mean():.4f}")
print(f"Median: {df['similarity_score'].median():.4f}")

# Most repeated Razão Social
print("\n" + "=" * 80)
print("TOP 15 MOST REPEATED 'Razão Social'")
print("=" * 80)
top_razao = df['Razão Social'].value_counts().head(15)
for i, (razao, count) in enumerate(top_razao.items(), 1):
    print(f"{i:2d}. {razao}: {count} occurrences")

print("\n" + "=" * 80)
