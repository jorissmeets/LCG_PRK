#!/usr/bin/env python3
"""
Script to organize existing files in lookup_tables into country-specific folders.

NOTE: This script is for ONE-TIME MIGRATION of old files only.
After running the updated processing script, new lookup files will automatically
be saved in data/{country}_tekorten/ folders.
"""

import os
import shutil
from pathlib import Path

def organize_existing_files():
    """
    Move existing files from lookup_tables root into appropriate country-specific folders in data/.
    """
    lookup_tables_path = "lookup_tables"
    data_path = "data"
    
    if not os.path.exists(lookup_tables_path):
        print("lookup_tables folder does not exist!")
        return
    
    # Create data folder if it doesn't exist
    os.makedirs(data_path, exist_ok=True)
    print(f"Created data folder: {data_path}")
    
    # Define country mappings based on file prefixes
    country_mappings = {
        'sweden': ['sweden', 'zweden'],
        'germany': ['germany', 'duitsland'],
        'belgium': ['belgium', 'belgie'],
        'austria': ['austria', 'oostenrijk']
    }
    
    # Create country folders if they don't exist
    for country in country_mappings.keys():
        country_folder = f"{data_path}/{country}_tekorten"
        os.makedirs(country_folder, exist_ok=True)
        print(f"Created folder: {country_folder}")
    
    # Get all files in lookup_tables
    files = os.listdir(lookup_tables_path)
    
    moved_files = []
    skipped_files = []
    
    for file in files:
        file_path = os.path.join(lookup_tables_path, file)
        
        # Skip directories and README
        if os.path.isdir(file_path) or file == "README.md":
            continue
        
        # Determine which country this file belongs to
        file_lower = file.lower()
        target_country = None
        
        for country, prefixes in country_mappings.items():
            for prefix in prefixes:
                if file_lower.startswith(prefix):
                    target_country = country
                    break
            if target_country:
                break
        
        if target_country:
            # Move file to appropriate country folder
            target_folder = f"{data_path}/{target_country}_tekorten"
            target_path = os.path.join(target_folder, file)
            
            try:
                shutil.move(file_path, target_path)
                moved_files.append((file, target_folder))
                print(f"Moved: {file} -> {target_folder}/")
            except Exception as e:
                print(f"Error moving {file}: {e}")
        else:
            # Handle files with no clear country prefix
            if file.startswith('_'):
                # These seem to be generic files, let's keep them in root for now
                skipped_files.append(file)
                print(f"Skipped (generic): {file}")
            else:
                skipped_files.append(file)
                print(f"Skipped (unknown country): {file}")
    
    # Summary
    print(f"\n--- Summary ---")
    print(f"Files moved: {len(moved_files)}")
    for file, folder in moved_files:
        print(f"  {file} -> {folder}")
    
    print(f"\nFiles skipped: {len(skipped_files)}")
    for file in skipped_files:
        print(f"  {file}")
    
    # Show final structure
    print(f"\n--- Final Structure ---")
    print("Lookup tables folder:")
    show_folder_structure(lookup_tables_path)
    print("\nData folder:")
    show_folder_structure(data_path)

def show_folder_structure(path, indent=""):
    """
    Recursively show the folder structure.
    """
    try:
        items = os.listdir(path)
        for item in sorted(items):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                print(f"{indent}📁 {item}/")
                show_folder_structure(item_path, indent + "  ")
            else:
                print(f"{indent}📄 {item}")
    except Exception as e:
        print(f"{indent}❌ Error listing {path}: {e}")

if __name__ == "__main__":
    print("Organizing existing files in lookup_tables...")
    organize_existing_files()
    print("\nOrganization complete!")
