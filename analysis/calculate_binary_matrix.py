import pandas as pd
import numpy as np
from pathlib import Path

# Define the base path for data
base_path = Path(__file__).parent / "data"

# Define all folder paths to process
folder_paths = [
    # Macro folders
    base_path / "macro" / "macro_no_quality",
    base_path / "macro" / "macro_percentile",
    base_path / "macro" / "macro_q1",
    base_path / "macro" / "macro_q2",
    base_path / "macro" / "macro_q3",
    base_path / "macro" / "macro_q4",
    base_path / "macro" / "macro_quartile",
    # Sub folders
    base_path / "sub" / "sub_no_quality",
    base_path / "sub" / "sub_percentile",
    base_path / "sub" / "sub_q1",
    base_path / "sub" / "sub_q2",
    base_path / "sub" / "sub_q3",
    base_path / "sub" / "sub_q4",
    base_path / "sub" / "sub_quartile",
]

def process_folder(folder_path):
    """
    Process a folder containing rank.txt, labels.csv, and institutions_names.csv files.
    Creates a binary matrix where 1 = value >= row_average, 0 = value < row_average
    
    Returns a dataframe with:
    - Index: institution names (from institutions_names.csv)
    - Columns: area labels (from labels.csv)
    - Values: 1 or 0 based on comparison with row average
    """
    rank_file = folder_path / "rank.txt"
    labels_file = folder_path / "labels.csv"
    institutions_file = folder_path / "institutions_names.csv"
    
    if not rank_file.exists() or not labels_file.exists() or not institutions_file.exists():
        print(f"Warning: Missing files in {folder_path}")
        return None
    
    # Read the files
    # rank.txt: one row per area, one column per institution
    rank_data = pd.read_csv(rank_file, header=None)
    
    # labels.csv: area names (correspond to rows in rank.txt)
    labels_df = pd.read_csv(labels_file, header=None)
    area_labels = labels_df.iloc[:, 0].tolist()
    
    # institutions_names.csv: institution names (correspond to columns in rank.txt)
    # Note: First row is a header, so we skip it
    institutions_df = pd.read_csv(institutions_file, header=0)
    institution_labels = institutions_df.iloc[:, 0].tolist()
    
    # Transpose so rows are institutions and columns are areas
    rank_data_T = rank_data.T
    
    # Calculate row averages (average value for each institution across all areas)
    row_averages = rank_data_T.mean(axis=1).values
    
    # Create binary matrix: 1 if value >= row_average, 0 otherwise
    # Broadcasting row_averages for comparison
    binary_matrix = (rank_data_T >= row_averages[:, np.newaxis]).astype(int)
    
    # Create result dataframe with proper labels
    result_df = pd.DataFrame(
        binary_matrix.values,
        columns=area_labels,
        index=institution_labels
    )
    
    return result_df, folder_path.name

# Process all folders
for folder_path in folder_paths:
    if not folder_path.exists():
        print(f"Folder does not exist: {folder_path}")
        continue
    
    result = process_folder(folder_path)
    if result is not None:
        result_df, folder_name = result
        
        # Save to CSV in the same folder
        output_file = folder_path / "binary_matrix.csv"
        result_df.to_csv(output_file)
        print(f"✓ Processed {folder_name}")
        print(f"  Shape: {result_df.shape[0]} institutions × {result_df.shape[1]} areas")
        print(f"  Saved to: {output_file}")
        print(f"  Sample:\n{result_df.iloc[:3, :5]}\n")
    else:
        print(f"✗ Failed to process {folder_path.name}\n")

print("Done! All binary matrices have been calculated and saved.")
