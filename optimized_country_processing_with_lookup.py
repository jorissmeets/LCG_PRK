import pandas as pd
from openai import OpenAI
import json
import time
import os
import re
import argparse

import csv, unicodedata
from pathlib import Path

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def read_z_index(path="LCG.csv"):
    """
    Lees de Z‑index op een robuuste manier.
    - automatische scheidingsteken‑detectie
    - UTF‑8 én Latin‑1 fallback
    - duidelijke foutmelding als het bestand echt ontbreekt
    """
    import csv, pandas as pd, io, os

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Z‑index bestand ‘{path}’ niet gevonden. "
            "Zorg dat het in dezelfde map staat of geef een volledig pad mee."
        )

    # delimiter bepalen
    with open(path, "rb") as fh:
        sample = fh.read(4096)
    try:
        dialect = csv.Sniffer().sniff(
            sample.decode("utf‑8", errors="ignore"), delimiters=";,|\t"
        )
        sep = dialect.delimiter
    except csv.Error:
        sep = ";" if sample.count(b";") > sample.count(b",") else ","

    # encoding‑fallback
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, sep=sep, encoding=enc, engine="python")
        except UnicodeDecodeError:
            continue

    # laatste poging laat de echte fout zien
    return pd.read_csv(path, sep=sep, engine="python")

def read_csv_flexible(path: str | Path, *, encodings=("utf-8", "latin-1")) -> pd.DataFrame:
    """
    Lees een CSV met automatische delimiter‑detectie en encoding fallback.
    Probeer eerst utf‑8, daarna latin‑1.
    """
    path = Path(path)

    # -------- detect delimiter op basis van eerste 4 kB
    with path.open("rb") as fh:
        sample = fh.read(4096)
    try:
        dialect = csv.Sniffer().sniff(
            sample.decode("utf-8", errors="ignore"), delimiters=";,|\t"
        )
        sep = dialect.delimiter
    except csv.Error:
        text = sample.decode("utf-8", errors="ignore")
        sep  = ";" if text.count(";") > text.count(",") else ","

    # -------- probeer verschillende encodings ----------
    for enc in encodings:
        try:
            return pd.read_csv(
                path, sep=sep, engine="python", encoding=enc, on_bad_lines="skip"
            )
        except UnicodeDecodeError:
            continue       # volgende encoding
    # laatste poging – laat de originele fout omhoog komen
    return pd.read_csv(path, sep=sep, engine="python", on_bad_lines="skip")


def clean_atc_code(atc_code):
    """
    Clean ATC code by extracting just the code part.
    ATC codes typically follow the pattern: letter + 2 digits + letter + 2 digits + letter
    
    Args:
        atc_code: The ATC code string that may contain additional text
        
    Returns:
        Cleaned ATC code or None if invalid
    """
    if pd.isna(atc_code):
        return None
    
    # Convert to string
    atc_str = str(atc_code)
    
    # First try to extract the code before the hyphen
    if " - " in atc_str:
        atc_str = atc_str.split(" - ")[0].strip()
    
    # Try to extract the ATC code using regex
    # Pattern: letter + 2 digits + letter + 2 digits + letter
    match = re.search(r'([A-Z]\d{2}[A-Z]\d{2}[A-Z])', atc_str)
    if match:
        return match.group(1)
    
    # If no match found, return the original code
    return atc_str

def load_lookup_file(country_name):
    """
    Load the lookup file for a specific country from the country-specific data folder.
    
    Args:
        country_name: Name of the country (e.g., "Belgium", "Austria", "Sweden")
        
    Returns:
        DataFrame with lookup data or None if file doesn't exist
    """
    # Store lookup files in country-specific data folders
    country_folder = f"data/{country_name.lower()}_tekorten"
    lookup_filename = f"{country_folder}/{country_name.lower()}_lookup.xlsx"
    
    if not os.path.exists(lookup_filename):
        print(f"Lookup file {lookup_filename} not found. Will create new matches.")
        return None
    
    try:
        print(f"Loading lookup file: {lookup_filename}")
        df_lookup = pd.read_excel(lookup_filename)
        print(f"Loaded {len(df_lookup)} existing matches from lookup file")
        return df_lookup
    except Exception as e:
        print(f"Error loading lookup file {lookup_filename}: {e}")
        return None

def find_existing_matches(df_country, df_lookup, country_id_column):
    """
    Find existing matches in the lookup file based on country ID.
    
    Args:
        df_country: DataFrame with country medication data
        df_lookup: DataFrame with existing lookup data
        country_id_column: Column name containing the country identification number
        
    Returns:
        Dictionary mapping country IDs to PRK code for existing matches
    """
    if df_lookup is None:
        return {}
    
    existing_matches = {}
    

    
    # Check if the standardized country_id column exists in the lookup data
    if 'country_id' not in df_lookup.columns:
        print(f"Warning: Standardized 'country_id' column not found in lookup data.")
        return {}
    
    # Create lookup dictionary from the lookup file
    lookup_dict = {}
    for idx, row in df_lookup.iterrows():
        country_id = row['country_id']
        if pd.notna(country_id):
            if 'PRK' in row:
                lookup_dict[country_id] = row['PRK']
            elif 'PRK code' in row:
                lookup_dict[country_id] = row['PRK code']
    
    print(f"Created lookup dictionary with {len(lookup_dict)} entries")
    
    # Find matches in the country data
    for idx, row in df_country.iterrows():
        country_id = row[country_id_column]
        if pd.notna(country_id) and country_id in lookup_dict:
            existing_matches[country_id] = lookup_dict[country_id]
    
    print(f"Found {len(existing_matches)} existing matches in lookup file")
    return existing_matches

def save_lookup_file(df_lookup, country_name, new_matches, country_id_column):
    """
    Save or update the lookup file with new matches.

    Each row now carries three fields:
      • country_id              – the project‑wide key (unchanged)
      • <country_id_column>     – the raw identifier column from the source file
      • PRK                     – the matched PRK code
    """
    # Ensure the country-specific data directory exists
    country_folder = f"data/{country_name.lower()}_tekorten"
    os.makedirs(country_folder, exist_ok=True)
    
    lookup_filename = f"{country_folder}/{country_name.lower()}_lookup.xlsx"

    # ----------------------------------------------------------------------
    # 1. Build a DataFrame from the new matches
    # ----------------------------------------------------------------------
    new_rows = []
    for country_id, prk_code in new_matches.items():
        if prk_code is None:          # keep only successful matches
            continue

        new_rows.append({
            "country_id": country_id,              # existing canonical key
            "PRK": prk_code
        })

    if not new_rows:                  # nothing new to persist
        return

    df_new = pd.DataFrame(new_rows)

    # ----------------------------------------------------------------------
    # 2. Combine with an existing lookup file, if there is one
    # ----------------------------------------------------------------------
    if df_lookup is not None:
        # Ensure the old file also has the raw-ID column so we
        # don’t lose that information when concatenating.

        df_combined = (
            pd.concat([df_lookup, df_new], ignore_index=True)
              .drop_duplicates(subset=["country_id"], keep="last")
        )
    else:
        df_combined = df_new

    # ----------------------------------------------------------------------
    # 3. Write the updated table back to disk
    # ----------------------------------------------------------------------
    df_combined.to_excel(lookup_filename, index=False)
    print(f"Saved {len(df_combined)} rows to “{lookup_filename}”.")

def get_best_match_from_candidates(country_context: str, candidates: list[str], country_name: str, language: str) -> dict:
    """
    Asks an LLM to find the best matching candidate line for the given country context.
    
    Args:
        country_context: Description of the medication from the country
        candidates: List of candidate lines to match against
        country_name: Name of the country (e.g., "Belgian", "Austrian", "Swedish")
        language: Language to use for the prompt (e.g., "English", "Dutch")
        
    Returns:
        Dictionary with best_match_index, best_match, confidence, and explanation
    """
    candidate_str = "\n".join([f"{i+1}) {c}" for i, c in enumerate(candidates)])
    prompt = f"""
We have a {country_name} medication description and a list of Dutch candidate lines.
Pick the single best match from the candidates that aligns best with the {country_name} description.
If there is no good match (e.g. the quantity of the substance is different), return 0.
The number of tablets is not important. 

{country_name} description:
{country_context}

Candidate lines:
{candidate_str}

Return your answer in JSON format (without additional text). For example:
{{
  "best_match_index": 1,
  "best_match": "Exact string from the candidate",
  "confidence": 95,
  "explanation": "Short reason"
}}
    """
    try:
        response = client.chat.completions.create(
            model="o4-mini-2025-04-16",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI assistant that helps match {country_name} medication descriptions to Dutch candidate lines."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        answer_text = response.choices[0].message.content.strip()
        result = json.loads(answer_text)
        return {
            "best_match_index": result.get("best_match_index", 0),
            "best_match": result.get("best_match", ""),
            "confidence": result.get("confidence", 0),
            "explanation": result.get("explanation", "")
        }
    except Exception as e:
        print(f"Error in LLM call or JSON parsing: {e}")
        return {
            "best_match_index": 0,
            "best_match": "",
            "confidence": 0,
            "explanation": f"Error: {str(e)}"
        }

def process_batch(batch_items, df_z_index, country_name, language):
    """
    Process a batch of medication groups to find matches.
    
    Args:
        batch_items: List of tuples (country_keys, group, sub_df, row_indices)
        df_z_index: DataFrame with Z-index data
        country_name: Name of the country (e.g., "Belgian", "Austrian", "Swedish")
        language: Language to use for the prompt (e.g., "English", "Dutch")
        
    Returns:
        Dictionary mapping country_keys to PRK code
    """
    batch_results = {}
    
    for country_keys, group, sub_df, row_indices in batch_items:
        # Create context string from the medication details
        # Handle different numbers of columns
        context_parts = []
        for i, key in enumerate(country_keys):
            if i == 0:
                context_parts.append(f"Name: {key}")
            elif i == 1:
                context_parts.append(f"Strength: {key}")
            elif i == 2:
                context_parts.append(f"Form: {key}")
            elif i == 3:
                context_parts.append(f"Pack Size: {key}")
            else:
                context_parts.append(f"Additional Info {i}: {key}")
        
        country_context = "\n".join(context_parts)
        
        # Build candidates list
        candidates = []
        for idx in row_indices:
            row = df_z_index.iloc[int(sub_df.loc[idx, "z_index_index"])]
            candidate_str = (
                f"{row['PRK code']}; "
                f"{row['Artikelomschrijving']}; "
                f"{row['Toedieningsweg']}; "
                f"{row['PRK omschrijving']}"
            )
            candidates.append(candidate_str)
        
        if not candidates:
            batch_results[country_keys] = None
            continue
            
        # Get best match using GPT
        match_result = get_best_match_from_candidates(country_context, candidates, country_name, language)
        best_idx_1_based = match_result["best_match_index"]
        
        if 1 <= best_idx_1_based <= len(candidates):
            chosen_index = row_indices[best_idx_1_based - 1]
            # Get the PRK code directly from the Z-index data
            z_index_idx = int(sub_df.loc[chosen_index, "z_index_index"])
            prk_code = df_z_index.iloc[z_index_idx]["PRK code"]
            batch_results[country_keys] = prk_code
        else:
            batch_results[country_keys] = None
            
    return batch_results

def update_combinations_df(df_combinations, df_country, best_match_dict, index_column="belgian_index", important_columns=None, country_id_column=None):
    """
    Update the best_z_index_index column in df_combinations efficiently.
    
    Args:
        df_combinations: DataFrame with combinations
        df_country: DataFrame with country medication data
        best_match_dict: Dictionary mapping country_keys or country_ids to PRK code
        index_column: Column name for the country index
        important_columns: List of important columns for grouping
        country_id_column: Column name containing the country identification number
        
    Returns:
        Updated DataFrame with combinations
    """
    # Create a mapping from country_keys to PRK code
    country_to_prk = {}
    for key, prk_code in best_match_dict.items():
        if prk_code is None:
            continue
            
        if isinstance(key, tuple):
            # Handle tuple keys (from original grouping)
            key_parts = []
            for k in key:
                key_parts.append(str(k))
            key_str = "|".join(key_parts)
            country_to_prk[key_str] = prk_code
        else:
            # Handle integer/string keys (country IDs)
            # We need to find the corresponding group key for this country ID
            for idx, row in df_country.iterrows():
                if row[country_id_column] == key:
                    # Get the values for the important columns
                    key_parts = []
                    for col in important_columns:
                        if col in row:
                            key_parts.append(str(row[col]))
                        else:
                            key_parts.append("")
                    key_str = "|".join(key_parts)
                    country_to_prk[key_str] = prk_code
                    break
    
    print(f"Created {len(country_to_prk)} mappings from country keys to PRK codes")
    
    # Create a mapping from country index to key_str
    country_index_to_key = {}
    for idx, row in df_country.iterrows():
        # Get the values for the important columns
        key_parts = []
        for col in important_columns:
            if col in row:
                key_parts.append(str(row[col]))
            else:
                key_parts.append("")
        key_str = "|".join(key_parts)
        country_index_to_key[idx] = key_str
    
    print(f"Created {len(country_index_to_key)} mappings from country indices to key strings")
    
    # Update df_combinations in bulk
    update_count = 0
    for i, row in df_combinations.iterrows():
        country_index = row[index_column]
        if country_index in country_index_to_key:
            key_str = country_index_to_key[country_index]
            if key_str in country_to_prk:
                df_combinations.at[i, "best_z_index_index"] = country_to_prk[key_str]
                update_count += 1
    
    print(f"Updated {update_count} rows in the combinations DataFrame with PRK codes")
    
    return df_combinations

def create_atc_combinations(df_country, df_z_index, atc_column="ATC Code", index_column="belgian_index"):
    """
    Create combinations between country medications and Dutch Z-index entries based on ATC codes.
    Only includes medicines from LCG with different PRK codes.
    
    Args:
        df_country: DataFrame with country medication data
        df_z_index: DataFrame with Dutch Z-index data
        atc_column: Column name for ATC codes in the country data
        index_column: Column name for the country index
        
    Returns:
        DataFrame with combinations
    """
    print("Creating ATC code combinations...")
    
    # Print column names for debugging
    print(f"Country data columns: {df_country.columns.tolist()}")
    print(f"Z-index data columns: {df_z_index.columns.tolist()}")
    
    # Check if ATC code column exists in both dataframes
    if atc_column not in df_country.columns:
        print(f"Warning: ATC code column '{atc_column}' not found in country data. Available columns: {df_country.columns.tolist()}")
        # Try to find a similar column name
        possible_atc_columns = [col for col in df_country.columns if 'atc' in col.lower()]
        if possible_atc_columns:
            print(f"Possible ATC columns found: {possible_atc_columns}")
            # Use the first possible ATC column
            atc_column = possible_atc_columns[0]
            print(f"Using '{atc_column}' as ATC code column")
        else:
            print("No ATC code column found. Creating empty combinations DataFrame.")
            return pd.DataFrame(columns=[index_column, "z_index_index", "ATC_match", "best_z_index_index"])
    
    if 'ATC code' not in df_z_index.columns:
        print(f"Warning: ATC code column 'ATC code' not found in Z-index data. Available columns: {df_z_index.columns.tolist()}")
        # Try to find a similar column name
        possible_atc_columns = [col for col in df_z_index.columns if 'atc' in col.lower()]
        if possible_atc_columns:
            print(f"Possible ATC columns found: {possible_atc_columns}")
            # Use the first possible ATC column
            atc_column_z = possible_atc_columns[0]
            print(f"Using '{atc_column_z}' as ATC code column in Z-index data")
        else:
            print("No ATC code column found in Z-index data. Creating empty combinations DataFrame.")
            return pd.DataFrame(columns=[index_column, "z_index_index", "ATC_match", "best_z_index_index"])
    
    # Clean ATC codes in both dataframes
    print("Cleaning ATC codes...")
    df_country['cleaned_atc'] = df_country[atc_column].apply(clean_atc_code)
    df_z_index['cleaned_atc'] = df_z_index['ATC code'].apply(clean_atc_code)
    
    # Print some examples of cleaned ATC codes
    print("Examples of cleaned ATC codes:")
    print(f"Country ATC codes: {df_country['cleaned_atc'].head(5).tolist()}")
    print(f"Z-index ATC codes: {df_z_index['cleaned_atc'].head(5).tolist()}")
    
    # First, group Z-index entries by ATC code and PRK code
    # We only want to include one entry per unique PRK code for each ATC code
    print("Filtering Z-index entries to include only unique PRK codes per ATC code...")
    df_z_index_filtered = df_z_index.drop_duplicates(subset=['cleaned_atc', 'PRK code'])
    
    # Create a mapping from ATC code to Z-index indices for faster lookup
    atc_to_z_index = {}
    for idx, row in df_z_index_filtered.iterrows():
        if pd.notna(row['cleaned_atc']):
            atc_code = row['cleaned_atc']
            if atc_code not in atc_to_z_index:
                atc_to_z_index[atc_code] = []
            atc_to_z_index[atc_code].append(idx)
    
    # Create combinations based on ATC codes
    combinations = []
    for country_idx, country_row in df_country.iterrows():
        if pd.notna(country_row['cleaned_atc']):
            country_atc = country_row['cleaned_atc']
            if country_atc in atc_to_z_index:
                for z_idx in atc_to_z_index[country_atc]:
                    combinations.append({
                        index_column: country_idx,
                        "z_index_index": z_idx,
                        "ATC_match": True
                    })
    
    # Create DataFrame from combinations
    df_combinations = pd.DataFrame(combinations)
    
    # Add a column for the best match (will be filled later)
    df_combinations["best_z_index_index"] = None
    
    print(f"Created {len(df_combinations)} ATC-based combinations")
    return df_combinations

def process_country_data_with_lookup(input_file, sheet_name, country_name, language, atc_column, 
                                   important_columns, index_column, country_id_column, batch_size=5, delay=0, test_mode=False, checkpoint_frequency=5):
    """
    Process medication data from a country to find matches with Dutch Z-index entries.
    First checks for existing matches in a lookup file based on country ID, then runs LLM matching for new entries.
    
    Args:
        input_file: Path to the input Excel/CSV file with supply problems data
        sheet_name: Name of the sheet in the Excel file (if applicable)
        country_name: Name of the country (e.g., "Belgium", "Austria", "Sweden")
        language: Language to use for the prompt (e.g., "English", "Dutch")
        atc_column: Column name for ATC codes in the country data
        important_columns: List of important columns for grouping
        index_column: Column name for the country index
        country_id_column: Column name containing the country identification number
        batch_size: Number of groups to process in each batch
        delay: Delay between batches in seconds
        test_mode: If True, only process the first 10 batches
        checkpoint_frequency: Save progress every N batches (default: 5)
        
    Returns:
        Tuple of (df_combinations, df_final)
    """
    print(f"Starting {country_name} medication processing with lookup...")
    
    # Load existing lookup file
    df_lookup = load_lookup_file(country_name)
    
    # Read the country Excel file
    print(f"Reading data from {input_file}...")
    if input_file.endswith('.xlsx') or input_file.endswith('.xls'):
        if sheet_name:
            df_country = pd.read_excel(input_file, sheet_name=sheet_name)
        else:
            # Try to read the first sheet if no sheet name is provided
            df_country = pd.read_excel(input_file)
    else:
        # Assume it's a CSV file
        if input_file.endswith(".csv"):
            df_country = read_csv_flexible(input_file)
        else:
            df_country = pd.read_excel(input_file, sheet_name=sheet_name or 0)    

    df_z_index = pd.read_csv("LCG.csv", encoding="ISO-8859-1", delimiter=";")
    # Print column names for debugging
    print(f"Country data columns: {df_country.columns.tolist()}")
    print(f"Z-index data columns: {df_z_index.columns.tolist()}")
    
    # Find existing matches in lookup file based on country ID
    existing_matches = find_existing_matches(df_country, df_lookup, country_id_column)
    
    # Create combinations DataFrame based on ATC codes
    df_combinations = create_atc_combinations(df_country, df_z_index, atc_column, index_column)
    
    # If no combinations were created, exit gracefully
    if len(df_combinations) == 0:
        print("No ATC-based combinations were created. Exiting.")
        return None, None
    
    # Group by relevant columns to match similar medications
    grouped = df_country.groupby(important_columns, dropna=False)
    
    # Filter out groups that already have matches in the lookup file
    groups_to_process = []
    for country_keys, group in grouped:
        # Check if any medication in this group already has a match
        group_has_match = False
        for idx in group.index:
            country_id = df_country.loc[idx, country_id_column]
            if pd.notna(country_id) and country_id in existing_matches:
                group_has_match = True
                break
        
        # Only process if no medications in this group have matches
        if not group_has_match:
            groups_to_process.append((country_keys, group))
    
    print(f"Found {len(existing_matches)} existing matches, {len(groups_to_process)} groups need processing")
    
    # If no new groups to process, skip LLM processing
    if not groups_to_process:
        print("All groups already have matches in lookup file. Skipping LLM processing.")
        best_match_dict = existing_matches
    else:
        # Prepare batches for processing
        batches = []
        current_batch = []
        
        print("Preparing batches for processing...")
        for country_keys, group in groups_to_process:
            # Get all possible Z-index matches for this group
            sub_df = df_combinations[df_combinations[index_column].isin(group.index)]
            row_indices = list(sub_df.index)
            
            current_batch.append((country_keys, group, sub_df, row_indices))
            
            if len(current_batch) >= batch_size:
                batches.append(current_batch)
                current_batch = []
        
        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)
        
        # In test mode, only process the first 10 batches
        if test_mode:
            print("TEST MODE: Only processing the first 10 batches")
            batches = batches[:10]
        
        # Process batches
        best_match_dict = existing_matches.copy()  # Start with existing matches
        counter = 0
        total_groups = len(groups_to_process)
        total_batches = len(batches)
        
        print(f"Processing {total_groups} new groups in {total_batches} batches...")
        for batch_idx, batch in enumerate(batches):
            print(f"Processing batch {batch_idx+1}/{total_batches} ({counter}/{total_groups} groups)")
            
            # Process the batch
            batch_results = process_batch(batch, df_z_index, country_name, language)
            best_match_dict.update(batch_results)
            
            counter += len(batch)
            if counter % 10 == 0:
                print(f"Processed {counter}/{total_groups} groups")
            
            # Save progress incrementally every N batches (configurable)
            # This ensures we don't lose work if the run crashes
            if (batch_idx + 1) % checkpoint_frequency == 0 or batch_idx == len(batches) - 1:
                # Extract new matches from this batch for incremental save
                incremental_matches = {}
                for key, prk_code in batch_results.items():
                    if prk_code is None:
                        continue
                    if isinstance(key, tuple):
                        try:
                            group = grouped.get_group(key)
                            for idx in group.index:
                                country_id = df_country.loc[idx, country_id_column]
                                incremental_matches[country_id] = prk_code
                        except KeyError:
                            continue
                    else:
                        incremental_matches[key] = prk_code
                
                # Save only truly new matches (not already in lookup)
                new_to_save = {
                    k: v for k, v in incremental_matches.items()
                    if k not in existing_matches
                }
                
                if new_to_save:
                    save_lookup_file(df_lookup, country_name, new_to_save, country_id_column)
                    # Reload lookup to keep it in sync
                    df_lookup = load_lookup_file(country_name)
                    # Update existing_matches to avoid re-saving
                    existing_matches.update(new_to_save)
                    print(f"💾 Saved {len(new_to_save)} new matches to lookup file (checkpoint)")
            
            # Add a small delay between batches to avoid rate limits
            if batch_idx < len(batches) - 1:  # Don't sleep after the last batch
                time.sleep(delay)  # Reduced delay between batches
        
        # Final save is already handled incrementally above
        # No need for duplicate save at the end
        print(f"✅ All {len(batches)} batches processed and saved incrementally")
    
    # Update the best_z_index_index column in df_combinations efficiently
    print("Updating combinations DataFrame...")
    df_combinations = update_combinations_df(df_combinations, df_country, best_match_dict, index_column, important_columns, country_id_column)
    
    # Print statistics about the matches
    matches_count = df_combinations["best_z_index_index"].notna().sum()
    print(f"Found {matches_count} matches out of {len(df_combinations)} combinations")
    
    # Save the results
    # Ensure the data directory and country-specific subfolder exist
    country_folder = f"data/{country_name.lower()}_tekorten"
    os.makedirs(country_folder, exist_ok=True)
    
    output_file = f"{country_folder}/{country_name.lower()}_tekorten_met_best_matches.csv"
    if test_mode:
        output_file = f"{country_folder}/{country_name.lower()}_tekorten_met_best_matches_test.csv"
    print(f"Saving results to {output_file}...")
    df_combinations.to_csv(output_file, index=False)
    
    # Create final merged dataset with PRK codes - optimized
    print("Creating final dataset with PRK codes...")
    df_final = df_country.copy()
    df_final["PRK"] = None
    
    # Create a mapping from country index to PRK code for faster lookup
    country_to_prk = {}
    for i, row in df_combinations.iterrows():
        country_index = row[index_column]
        prk_code = row["best_z_index_index"]
        if pd.notna(prk_code):
            country_to_prk[country_index] = prk_code
    
    # Update PRK codes in bulk
    for country_index, prk_code in country_to_prk.items():
        df_final.at[country_index, "PRK"] = prk_code
    
    # Print statistics about the PRK codes
    prk_count = df_final["PRK"].notna().sum()
    print(f"Added PRK codes to {prk_count} out of {len(df_final)} medications")
    
    # Save the final dataset
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    final_output = f"{country_folder}/{country_name.lower()}_tekortmeldingen_met_PRK_{timestamp}.csv"
    if test_mode:
        final_output = f"{country_folder}/{country_name.lower()}_tekortmeldingen_met_PRK_test_{timestamp}.csv"
    print(f"Saving final dataset to {final_output}...")
    df_final.to_csv(final_output, index=False)
    
    print(f"Completed processing. Results saved to {final_output}")
    
    return df_combinations, df_final

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Process medication data from different countries to find matches with Dutch Z-index entries, using lookup files for efficiency.')
    
    # Required arguments
    parser.add_argument('--input', required=True, help='Path to the input Excel/CSV file with supply problems data')
    parser.add_argument('--country', required=True, help='Name of the country (e.g., Belgium, Austria, Sweden)')
    parser.add_argument('--country-id-column', required=True, help='Column name containing the country identification number for lookup mapping')
    
    # Optional arguments
    parser.add_argument('--sheet', help='Name of the sheet in the Excel file (if applicable)')
    parser.add_argument('--language', default='English', help='Language to use for the prompt (default: English)')
    parser.add_argument('--atc-column', default='ATC Code', help='Column name for ATC codes in the country data (default: ATC Code)')
    parser.add_argument('--important-columns', default='Name medicinal product,Strength,Pharmaceutical form,Pack Size',
                        help='Comma-separated list of important columns for grouping (default: Name medicinal product,Strength,Pharmaceutical form,Pack Size)')
    parser.add_argument('--index-column', default='belgian_index', help='Column name for the country index (default: belgian_index)')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of groups to process in each batch (default: 5)')
    parser.add_argument('--delay', type=float, default=2, help='Delay between batches in seconds (default: 2)')
    parser.add_argument('--checkpoint-frequency', type=int, default=5, help='Save progress every N batches to prevent data loss if run crashes (default: 5)')
    parser.add_argument('--api-key', help='OpenAI API key (if not set in environment)')
    parser.add_argument('--test', action='store_true', help='Test mode: only process the first 10 batches')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set OpenAI API key if provided
    if args.api_key:
        global client
        client = OpenAI(api_key=args.api_key)
    
    # Split the important columns string into a list
    important_columns = [col.strip() for col in args.important_columns.split(',')]
    
    # Process the country data with lookup functionality
    process_country_data_with_lookup(
        input_file=args.input,
        sheet_name=args.sheet,
        country_name=args.country,
        language=args.language,
        atc_column=args.atc_column,
        important_columns=important_columns,
        index_column=args.index_column,
        country_id_column=args.country_id_column,
        batch_size=args.batch_size,
        delay=args.delay,
        test_mode=args.test,
        checkpoint_frequency=args.checkpoint_frequency
    )

if __name__ == "__main__":
    main() 