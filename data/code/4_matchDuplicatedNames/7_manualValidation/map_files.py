import csv
import os
from pathlib import Path

# Define paths
SCRIPT_DIR = Path(__file__).parent
MATCHES_FILE = SCRIPT_DIR.parent / "6_fuzzyMatch" / "matches_fast.csv"
EMEC_FILE = SCRIPT_DIR.parent.parent.parent.parent / "data" / "data" / "raw" / "EMEC" / "EMEC_institutions.csv"
OUTPUT_DIR = SCRIPT_DIR
REVIEWED_MATCHES = OUTPUT_DIR / "matches.csv"
CORRECTED_MATCHES = OUTPUT_DIR / "corrected_matches.csv"
NON_MATCHED_MATCHES = OUTPUT_DIR / "non_matched.csv"

# Scopus columns to display
SCOPUS_FIELDS = ["afid", "name", "domain", "url", "state", "city", "variants"]

# EMEC columns to display
EMEC_DISPLAY_FIELDS = ["Razão Social", "Instituição(IES)", "Sigla", "Sitio", "e-Mail", "Município", "UF"]

# Additional fields to include in output
ADDITIONAL_FIELDS = ["similarity_score", "match_type"]

# All EMEC fields for the output CSV
EMEC_ALL_FIELDS = [
    "Código Mantenedora", "Razão Social", "CNPJ", "Natureza Jurídica", "Código IES",
    "Instituição(IES)", "Sigla", "Telefone", "Sitio", "e-Mail", "Endereço Sede",
    "Município", "UF", "Organização Acadêmica", "Tipo de Credenciamento", "Categoria",
    "Categoria Administrativa", "Data do Ato de Criação da IES", "CI", "Ano CI",
    "CI-EaD", "Ano CI-EaD", "IGC", "Ano IGC", "Reitor/Dirigente Principal",
    "Representante Legal", "Sinalizações Vigentes", "Situação da IES",
    "Data de Descredenciamento"
]

# Scopus fields for the output CSV
SCOPUS_OUTPUT_FIELDS = ["eid", "afid", "name", "domain", "url", "org_type", "state", "city", "variants"]


def load_emec_data():
    """Load EMEC institutions data into a dictionary for quick lookup."""
    emec_data = {}
    try:
        with open(EMEC_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                codigo = row.get("Código IES", "").strip()
                if codigo:
                    emec_data[codigo] = row
    except FileNotFoundError:
        print(f"Error: EMEC file not found at {EMEC_FILE}")
        exit(1)
    return emec_data


def load_matches():
    """Load matches data from CSV."""
    matches = []
    try:
        with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matches.append(row)
    except FileNotFoundError:
        print(f"Error: Matches file not found at {MATCHES_FILE}")
        exit(1)
    return matches


def load_assessed_codes():
    """Load AFID values from already-reviewed/ corrected/ non-matched files.

    Returns a set of AFID strings (stripped). If files don't exist they are skipped.
    The function looks for a column named 'afid' (case-insensitive). If that column
    isn't present, it will skip that file.
    """
    assessed = set()
    for path in (REVIEWED_MATCHES, CORRECTED_MATCHES, NON_MATCHED_MATCHES):
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    # Determine if there's an AFID-like column in this file
                    afid_key = None
                    for k in (reader.fieldnames or []):
                        if k and k.lower() == 'afid':
                            afid_key = k
                            break

                    if not afid_key:
                        # No explicit afid column found; skip this file
                        continue

                    for row in reader:
                        afid = row.get(afid_key, "").strip()
                        if afid:
                            assessed.add(afid)
            except Exception as e:
                print(f"Warning: could not read {path}: {e}")
    return assessed


def load_name_to_codigo_mapping():
    """Load a mapping from institution names to Código IES from already-reviewed, corrected, and non_matched files.
    
    Returns a dictionary where keys are institution names (Scopus name field) and values are 
    tuples of (Código IES, source_file).
    For non_matched entries, Código IES will be None.
    """
    name_mapping = {}
    
    for source_path, source_name in [(REVIEWED_MATCHES, "reviewed"), (CORRECTED_MATCHES, "corrected"), (NON_MATCHED_MATCHES, "non_matched")]:
        if source_path.exists():
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        scopus_name = row.get("name", "").strip()
                        
                        if source_name == "non_matched":
                            # For non_matched, we just need the name
                            if scopus_name:
                                name_mapping[scopus_name] = (None, source_name)
                        else:
                            # For reviewed and corrected, we need the Código IES
                            codigo_ies = row.get("Código IES", "").strip()
                            if scopus_name and codigo_ies:
                                # Store mapping with source info
                                name_mapping[scopus_name] = (codigo_ies, source_name)
            except Exception as e:
                print(f"Warning: could not read {source_path}: {e}")
    
    return name_mapping


def match_has_assessed_code(match_row, assessed_codes):
    """Return True if any value in match_row contains or equals any assessed AFID.

    We check each value in the CSV row (after stripping). If a value equals an AFID or
    contains the AFID as a substring, we treat the row as already assessed.
    """
    if not assessed_codes:
        return False

    # Prepare a list of non-empty string values from the row
    for val in match_row.values():
        if not val:
            continue
        s = str(val).strip()
        if not s:
            continue
        # Exact match fast path
        if s in assessed_codes:
            return True
        # Substring match (e.g. when Codigo appears inside a larger field)
        for code in assessed_codes:
            if code and code in s:
                return True
    return False


def display_match(scopus_data, emec_data, similarity_score, match_type, index, total):
    """Display a match in two-column format."""
    print("\n" + "="*120)
    print(f"Record {index + 1} of {total}")
    print("="*120)
    
    # Prepare display width
    col_width = 55
    
    # Print header
    print(f"{'Scopus Data':<{col_width}} | {'EMEC Data':<{col_width}}")
    print("-" * 120)
    
    # Display Scopus fields
    scopus_lines = []
    for field in SCOPUS_FIELDS:
        value = scopus_data.get(field, "N/A")
        if field == "variants":
            # Clean up variants display
            value = value.replace("['", "").replace("']", "").replace("', '", ", ")
        scopus_lines.append(f"{field}: {value}")
    
    # Display EMEC fields
    emec_lines = []
    for field in EMEC_DISPLAY_FIELDS:
        value = emec_data.get(field, "N/A")
        emec_lines.append(f"{field}: {value}")
    
    # Print side-by-side
    max_lines = max(len(scopus_lines), len(emec_lines))
    for i in range(max_lines):
        scopus_line = scopus_lines[i] if i < len(scopus_lines) else ""
        emec_line = emec_lines[i] if i < len(emec_lines) else ""
        print(f"{scopus_line:<{col_width}} | {emec_line:<{col_width}}")
    
    print("-" * 120)
    print(f"Similarity Score: {similarity_score}")
    print(f"Match Type: {match_type}")


def get_user_confirmation():
    """Ask user if the match is correct.
    
    Returns:
        'yes': Match is correct
        'no': Match needs correction
        'skip': Skip this match (user entered 0)
    """
    while True:
        response = input("\nIs this match correct? (Y/Yes/S/Sim for Yes, 0 to skip, anything else to correct): ").strip().lower()
        if response in ["y", "yes", "s", "sim"]:
            return "yes"
        elif response == "0":
            return "skip"
        else:
            return "no"


def get_codigo_ies():
    """Ask user for the correct Código Mantenedora."""
    while True:
        codigo = input("\nEnter the correct 'Código IES' from EMEC: ").strip()
        if codigo:
            return codigo
        print("Please enter a valid Código IES.")


def find_emec_by_codigo(codigo, emec_data):
    """Find EMEC record by Código IES."""
    if codigo in emec_data:
        return emec_data[codigo]
    else:
        print(f"Error: Código IES '{codigo}' not found in EMEC data.")
        return None


def build_output_row(scopus_data, emec_data):
    """Build a complete output row combining Scopus and EMEC data."""
    row = {}
    
    # Add EMEC fields
    for field in EMEC_ALL_FIELDS:
        row[field] = emec_data.get(field, "")
    
    # Add Scopus fields
    for field in SCOPUS_OUTPUT_FIELDS:
        row[field] = scopus_data.get(field, "")
    
    # Add similarity score and match type
    row["similarity_score"] = scopus_data.get("similarity_score", "")
    row["match_type"] = scopus_data.get("match_type", "")
    
    return row


def save_match(row, filepath, is_first_write):
    """Save a match to CSV file."""
    # All fields in output
    all_fields = EMEC_ALL_FIELDS + SCOPUS_OUTPUT_FIELDS + ["similarity_score", "match_type"]
    
    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
            
            # Write header only on first write
            if is_first_write:
                writer.writeheader()
            
            writer.writerow(row)
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")


def main():
    """Main function to review matches."""
    print("Loading data...")
    emec_data = load_emec_data()
    matches = load_matches()
    # Load already-assessed Código IES values and remove any matches that contain those codes
    assessed_codes = load_assessed_codes()
    if assessed_codes:
        orig_len = len(matches)
        # Remove any match row that contains any assessed Código IES in any column
        matches = [m for m in matches if not match_has_assessed_code(m, assessed_codes)]
        removed = orig_len - len(matches)
        print(f"Removed {removed} already-assessed matches (Código IES found in any field).")
    
    # Load name-to-codigo mapping from already-reviewed/corrected matches
    name_mapping = load_name_to_codigo_mapping()
    
    # Filter to keep only matches with similarity_score > 0.95
    orig_len = len(matches)
    filtered_matches = []
    for m in matches:
        try:
            score = float(m.get("similarity_score", "0"))
            if score > 90:
                filtered_matches.append(m)
        except (ValueError, TypeError):
            pass
    print(len(filtered_matches))
    removed = orig_len - len(filtered_matches)
    matches = filtered_matches
    if removed > 0:
        print(f"Filtered out {removed} matches with similarity_score <= 100.")
    
    if not matches:
        print("No matches found to review.")
        return
    
    print(f"Found {len(matches)} matches to review.")
    
    # Initialize output files
    reviewed_count = 0
    corrected_count = 0
    non_matched_count = 0
    automatic_count = 0
    
    # Check if files exist to avoid rewriting headers
    reviewed_exists = REVIEWED_MATCHES.exists()
    corrected_exists = CORRECTED_MATCHES.exists()
    non_matched_exists = NON_MATCHED_MATCHES.exists()
    
    for index, match in enumerate(matches):
        # Extract Scopus data
        scopus_data = {
            "eid": match.get("eid", ""),
            "afid": match.get("afid", ""),
            "name": match.get("name", ""),
            "domain": match.get("domain", ""),
            "url": match.get("url", ""),
            "org_type": match.get("org_type", ""),
            "state": match.get("state", ""),
            "city": match.get("city", ""),
            "variants": match.get("variants", ""),
            "similarity_score": match.get("similarity_score", ""),
            "match_type": match.get("match_type", ""),
        }
        
        # Extract EMEC data from match
        emec_from_match = {field: match.get(field, "") for field in EMEC_ALL_FIELDS}
        
        # Check if this institution name was already matched or marked as non_matched
        institution_name = scopus_data["name"].strip()
        if institution_name in name_mapping:
            codigo_ies, source = name_mapping[institution_name]
            
            # Handle non_matched institutions
            if source == "non_matched":
                print("\n" + "="*120)
                print(f"Record {index + 1} of {len(matches)}")
                print("="*120)
                print(f"⊘ PREVIOUSLY NOT FOUND ANY MATCH: Institution '{institution_name}' was already reviewed and no match was found.")
                print("⊘ Skipping this record.\n")
                non_matched_count += 1
                continue
            
            # Handle reviewed/corrected matches
            correct_emec = find_emec_by_codigo(codigo_ies, emec_data)
            
            if correct_emec:
                print("\n" + "="*120)
                print(f"Record {index + 1} of {len(matches)}")
                print("="*120)
                print(f"✓ AUTOMATIC MATCH: Institution '{institution_name}' was found in {source} matches with Código IES: {codigo_ies}")
                
                # Save to reviewed matches
                output_row = build_output_row(scopus_data, correct_emec)
                save_match(output_row, REVIEWED_MATCHES, not reviewed_exists)
                reviewed_exists = True
                reviewed_count += 1
                automatic_count += 1
                print("✓ Automatically saved to reviewed matches.\n")
                continue
        
        # Display the match
        display_match(scopus_data, emec_from_match, scopus_data["similarity_score"], scopus_data["match_type"], index, len(matches))
        
        # Get user confirmation
        user_response = get_user_confirmation()
        
        if user_response == "yes":
            # Save to reviewed matches
            output_row = build_output_row(scopus_data, emec_from_match)
            save_match(output_row, REVIEWED_MATCHES, not reviewed_exists)
            reviewed_exists = True
            reviewed_count += 1
            # Add to name mapping for future matches in this run
            codigo_ies = emec_from_match.get("Código IES", "").strip()
            if codigo_ies:
                name_mapping[institution_name] = (codigo_ies, "reviewed")
            print("✓ Match saved to reviewed matches.")
        elif user_response == "skip":
            # Save to non-matched
            output_row = build_output_row(scopus_data, emec_from_match)
            save_match(output_row, NON_MATCHED_MATCHES, not non_matched_exists)
            non_matched_exists = True
            non_matched_count += 1
            # Add to name mapping for future matches in this run
            name_mapping[institution_name] = (None, "non_matched")
            print("✓ Match skipped and saved to non-matched.")
        else:
            # Ask for correct Código Mantenedora
            codigo = get_codigo_ies()
            correct_emec = find_emec_by_codigo(codigo, emec_data)
            
            if correct_emec:
                # Save to corrected matches
                output_row = build_output_row(scopus_data, correct_emec)
                save_match(output_row, CORRECTED_MATCHES, not corrected_exists)
                corrected_exists = True
                corrected_count += 1
                # Add to name mapping for future matches in this run
                codigo_ies = correct_emec.get("Código IES", "").strip()
                if codigo_ies:
                    name_mapping[institution_name] = (codigo_ies, "corrected")
                print("✓ Corrected match saved.")
    
    # Print summary
    print("\n" + "="*120)
    print("Review Complete!")
    print(f"Automatic matches: {automatic_count}")
    print(f"Reviewed matches saved: {reviewed_count}")
    print(f"Corrected matches saved: {corrected_count}")
    print(f"Non-matched records saved: {non_matched_count}")
    print(f"Reviewed matches file: {REVIEWED_MATCHES}")
    print(f"Corrected matches file: {CORRECTED_MATCHES}")
    print(f"Non-matched file: {NON_MATCHED_MATCHES}")


if __name__ == "__main__":
    main()
