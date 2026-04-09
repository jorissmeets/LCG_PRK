# Data Folder

This folder contains all processed country outcomes organized by country.

## Folder Structure

### Country-Specific Folders (`{country}_tekorten/`)
Each country has its own subfolder named `{country}_tekorten/` (e.g., `sweden_tekorten/`, `germany_tekorten/`, `belgium_tekorten/`) containing:
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

## Usage

The system automatically:
1. Creates country-specific subfolders (`{country}_tekorten/`) for each run
2. Stores all intermediate and final results in the appropriate country subfolder
3. Uses timestamps to avoid overwriting previous results

