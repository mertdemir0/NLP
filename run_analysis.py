"""
Script to run the nuclear energy content analysis.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import and run analysis
from src.analysis.database_analysis import DatabaseAnalyzer

def main():
    # Set the path to your database
    db_path = project_root / "data" / "db" / "IAEA.db"
    
    # Initialize analyzer
    analyzer = DatabaseAnalyzer(db_path)
    
    # Read data
    print("Loading IAEA data...")
    iaea_df = analyzer.read_iaea_data()
    print(f"Loaded {len(iaea_df) if iaea_df is not None else 0} IAEA articles")
    
    print("\nLoading Bloomberg data...")
    bloomberg_df = analyzer.read_bloomberg_data()
    print(f"Loaded {len(bloomberg_df) if bloomberg_df is not None else 0} Bloomberg articles")
    
    # Generate reports and start dashboard
    print("\nGenerating reports and starting dashboard...")
    app = analyzer.generate_reports(iaea_df, bloomberg_df)
    print("\nStarting dashboard at http://localhost:8050")
    app.run_server(debug=True)

if __name__ == "__main__":
    main()
