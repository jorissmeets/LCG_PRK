#!/usr/bin/env python3
"""
Test script to verify that the lookup folder functionality works correctly.
"""

import os
import pandas as pd
from optimized_country_processing_with_lookup import load_lookup_file, save_lookup_file

def test_lookup_folder_functionality():
    """Test that lookup files are properly saved to and loaded from the lookup_tables folder."""
    
    print("Testing lookup folder functionality...")
    
    # Test 1: Check if lookup_tables directory exists
    if not os.path.exists("lookup_tables"):
        print("❌ lookup_tables directory does not exist")
        return False
    else:
        print("✅ lookup_tables directory exists")
    
    # Test 2: Test loading a non-existent lookup file
    df_lookup = load_lookup_file("test_country")
    if df_lookup is None:
        print("✅ Correctly returns None for non-existent lookup file")
    else:
        print("❌ Should return None for non-existent lookup file")
        return False
    
    # Test 3: Test saving a new lookup file
    test_matches = {
        "test_id_1": "PRK001",
        "test_id_2": "PRK002"
    }
    
    try:
        save_lookup_file(None, "test_country", test_matches, "test_id_column")
        print("✅ Successfully saved test lookup file")
    except Exception as e:
        print(f"❌ Error saving lookup file: {e}")
        return False
    
    # Test 4: Test loading the newly created lookup file
    df_lookup = load_lookup_file("test_country")
    if df_lookup is not None and len(df_lookup) == 2:
        print("✅ Successfully loaded the created lookup file")
    else:
        print("❌ Failed to load the created lookup file")
        return False
    
    # Test 5: Test updating an existing lookup file
    new_matches = {
        "test_id_3": "PRK003"
    }
    
    try:
        save_lookup_file(df_lookup, "test_country", new_matches, "test_id_column")
        print("✅ Successfully updated existing lookup file")
    except Exception as e:
        print(f"❌ Error updating lookup file: {e}")
        return False
    
    # Test 6: Verify the updated file
    df_updated = load_lookup_file("test_country")
    if df_updated is not None and len(df_updated) == 3:
        print("✅ Successfully loaded the updated lookup file")
    else:
        print("❌ Failed to load the updated lookup file")
        return False
    
    # Clean up test file
    test_file = "lookup_tables/test_country_lookup.xlsx"
    if os.path.exists(test_file):
        os.remove(test_file)
        print("✅ Cleaned up test file")
    
    print("\n🎉 All tests passed! The lookup folder functionality is working correctly.")
    return True

if __name__ == "__main__":
    test_lookup_folder_functionality()

