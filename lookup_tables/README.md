# Lookup Tables Folder

This folder contains lookup files for the medication matching system.

## Folder Structure

### Lookup Files (`*_lookup.xlsx`)
- These files contain mappings between country-specific medication identifiers and Dutch PRK codes
- Used to avoid re-processing medications that have already been matched
- Automatically created and updated when new matches are found
- **Location**: Directly in `lookup_tables/` folder

## Usage

The system automatically:
1. Reads existing lookup files from the `lookup_tables/` folder when processing new data
2. Saves updated lookup files to the `lookup_tables/` folder when new matches are found

## File Naming Convention

- Lookup files: `lookup_tables/{country}_lookup.xlsx`

Where `{country}` is the lowercase country name (e.g., "sweden", "belgium", "germany").

## Example Structure
```
lookup_tables/
├── sweden_lookup.xlsx
├── germany_lookup.xlsx
└── belgium_lookup.xlsx
```

---

# Data Folder

The `data/` folder contains all processed country outcomes organized by country.

## Folder Structure

### Country-Specific Folders (`data/{country}_tekorten/`)
Each country has its own subfolder named `{country}_tekorten/` (e.g., `data/sweden_tekorten/`, `data/germany_tekorten/`, `data/belgium_tekorten/`) containing:
- **Best Matches Files** (`*_tekorten_met_best_matches.csv`)
- **Final Results Files** (`*_tekortmeldingen_met_PRK_*.csv`)

## File Types

### Best Matches Files (`*_tekorten_met_best_matches.csv`)
- Intermediate results showing the best matches found for each medication
- Contains ATC-based combinations and their corresponding PRK codes
- **Location**: `data/{country}_tekorten/` folder

### Final Results Files (`*_tekortmeldingen_met_PRK_*.csv`)
- Final processed datasets with PRK codes added to the original country data
- Timestamped to avoid overwriting previous results
- These are the main output files for analysis
- **Location**: `data/{country}_tekorten/` folder

## File Naming Convention

- Best matches: `data/{country}_tekorten/{country}_tekorten_met_best_matches.csv`
- Final results: `data/{country}_tekorten/{country}_tekortmeldingen_met_PRK_{timestamp}.csv`

Where `{country}` is the lowercase country name (e.g., "sweden", "belgium", "germany").

## Example Structure
```
data/
├── sweden_tekorten/
│   ├── sweden_tekorten_met_best_matches.csv
│   └── sweden_tekortmeldingen_met_PRK_20241201_143022.csv
├── germany_tekorten/
│   ├── germany_tekorten_met_best_matches.csv
│   └── germany_tekortmeldingen_met_PRK_20241201_143045.csv
└── belgium_tekorten/
    ├── belgium_tekorten_met_best_matches.csv
    └── belgium_tekortmeldingen_met_PRK_20241201_143012.csv
```
