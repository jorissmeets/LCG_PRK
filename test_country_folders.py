#!/usr/bin/env python3
"""
Test script to verify that country-specific folders are created correctly
and files are saved in the right locations.
"""

import os
import pandas as pd
import time
from pathlib import Path

def test_country_folder_structure():
    """
    Test the country-specific folder structure functionality.
    """
    print("Testing country-specific folder structure...")
    
    # Test countries
    test_countries = ["sweden", "germany", "belgium", "austria"]
    
    for country in test_countries:
        print(f"\n--- Testing {country.upper()} ---")
        
        # 1. Test folder creation
        country_folder = f"data/{country}_tekorten"
        print(f"Creating folder: {country_folder}")
        
        # Create the folder
        os.makedirs(country_folder, exist_ok=True)
        
        # Check if folder exists
        if os.path.exists(country_folder):
            print(f"✅ Folder created successfully: {country_folder}")
        else:
            print(f"❌ Failed to create folder: {country_folder}")
            continue
        
        # 2. Test file saving in country folder
        # Create a sample DataFrame
        sample_data = {
            'test_column': [f'test_value_{i}' for i in range(5)],
            'country': [country] * 5
        }
        df_sample = pd.DataFrame(sample_data)
        
        # Test saving best matches file
        best_matches_file = f"{country_folder}/{country}_tekorten_met_best_matches.csv"
        print(f"Saving best matches file: {best_matches_file}")
        df_sample.to_csv(best_matches_file, index=False)
        
        if os.path.exists(best_matches_file):
            print(f"✅ Best matches file saved: {best_matches_file}")
        else:
            print(f"❌ Failed to save best matches file: {best_matches_file}")
        
        # Test saving final results file with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        final_results_file = f"{country_folder}/{country}_tekortmeldingen_met_PRK_{timestamp}.csv"
        print(f"Saving final results file: {final_results_file}")
        df_sample.to_csv(final_results_file, index=False)
        
        if os.path.exists(final_results_file):
            print(f"✅ Final results file saved: {final_results_file}")
        else:
            print(f"❌ Failed to save final results file: {final_results_file}")
        
        # 3. List files in the country folder
        print(f"Files in {country_folder}:")
        try:
            files = os.listdir(country_folder)
            for file in files:
                print(f"  - {file}")
        except Exception as e:
            print(f"❌ Error listing files: {e}")
    
    # 4. Test overall structure
    print(f"\n--- Overall Structure Test ---")
    data_path = "data"
    if os.path.exists(data_path):
        print(f"✅ Main data folder exists")
        
        # List all contents
        print("Contents of data folder:")
        try:
            items = os.listdir(data_path)
            for item in items:
                item_path = os.path.join(data_path, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/ (directory)")
                    # List contents of subdirectory
                    try:
                        sub_items = os.listdir(item_path)
                        for sub_item in sub_items:
                            print(f"    - {sub_item}")
                    except Exception as e:
                        print(f"    ❌ Error listing subdirectory contents: {e}")
                else:
                    print(f"  📄 {item}")
        except Exception as e:
            print(f"❌ Error listing data contents: {e}")
    else:
        print(f"❌ Main data folder does not exist")
    
    print(f"\n--- Test Complete ---")

def cleanup_test_files():
    """
    Clean up test files and folders created during testing.
    """
    print("\nCleaning up test files...")
    
    test_countries = ["sweden", "germany", "belgium", "austria"]
    
    for country in test_countries:
        country_folder = f"data/{country}_tekorten"
        if os.path.exists(country_folder):
            try:
                # Remove all files in the folder
                for file in os.listdir(country_folder):
                    file_path = os.path.join(country_folder, file)
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                
                # Remove the folder itself
                os.rmdir(country_folder)
                print(f"Removed folder: {country_folder}")
            except Exception as e:
                print(f"Error cleaning up {country_folder}: {e}")

if __name__ == "__main__":
    # Run the test
    test_country_folder_structure()
    
    # Ask if user wants to clean up
    response = input("\nDo you want to clean up the test files? (y/n): ")
    if response.lower() in ['y', 'yes']:
        cleanup_test_files()
    else:
        print("Test files left in place for inspection.")
