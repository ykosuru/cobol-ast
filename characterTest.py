import pandas as pd
import re
import unicodedata
from typing import Dict, List, Set
from collections import defaultdict

class TranIDCharacterValidator:
    """
    Validator that reports special character issues in CSV columns against ISO 20022 guidelines
    """
    
    def __init__(self):
        # IMPORTANT: This validator uses general ISO 20022 character guidelines
        # For EXACT Federal Reserve Fedwire specifications, consult:
        # - MyStandards platform: Fedwire Funds Service Release 2025 Usage Guidelines
        # - Federal Reserve ISO 20022 Implementation Guide
        # - Contact your Federal Reserve liaison for official character set documentation
        
        # General ISO 20022 character pattern (explicit space, not \s)
        self.iso20022_pattern = r'^[A-Za-z0-9 \/\-\?\:\(\)\.\,\'\+]*$'
        
        # Define allowed character sets
        self.allowed_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
        self.allowed_numbers = set('0123456789')
        self.allowed_special = set('/-?:().,\'+ ')
        self.allowed_chars = self.allowed_letters | self.allowed_numbers | self.allowed_special
        
        # Common problematic characters with unique Unicode keys
        self.problematic_chars = {
            '\u0022': 'Double quote',
            '\u201C': 'Smart double quote (left)',
            '\u201D': 'Smart double quote (right)',
            '\u2018': 'Smart single quote (left)',
            '\u2019': 'Smart single quote (right)',
            '\u2013': 'En dash',
            '\u2014': 'Em dash',
            '\u2026': 'Ellipsis',
            '\u00A9': 'Copyright symbol',
            '\u00AE': 'Registered trademark',
            '\u2122': 'Trademark',
            '\u00B0': 'Degree symbol',
            '\u20AC': 'Euro symbol',
            '\u00A3': 'Pound symbol',
            '\u00A5': 'Yen symbol',
            '\u0024': 'Dollar symbol',
            '\u0025': 'Percent symbol',
            '\u0026': 'Ampersand',
            '\u0040': 'At symbol',
            '\u0023': 'Hash/pound sign',
            '\u002A': 'Asterisk',
            '\u007E': 'Tilde',
            '\u0060': 'Grave accent',
            '\u005E': 'Caret',
            '\u005F': 'Underscore',
            '\u003D': 'Equals sign',
            '\u005B': 'Left square bracket',
            '\u005D': 'Right square bracket',
            '\u007B': 'Left curly brace',
            '\u007D': 'Right curly brace',
            '\u007C': 'Pipe/vertical bar',
            '\u005C': 'Backslash',
            '\u003C': 'Less than',
            '\u003E': 'Greater than',
            '\u003B': 'Semicolon',
            '\u0009': 'Tab character',
            '\u000A': 'Newline character',
            '\u000D': 'Carriage return'
        }

    def has_invalid_chars(self, text: str) -> bool:
        """
        Check if text contains invalid characters
        
        Args:
            text: String to check
            
        Returns:
            True if contains invalid characters
        """
        if pd.isna(text) or text is None or text == '':
            return False
        text = unicodedata.normalize('NFC', str(text))
        return not bool(re.match(self.iso20022_pattern, text))

    def get_invalid_chars(self, text: str) -> List[Dict]:
        """
        Get list of invalid characters with details
        
        Args:
            text: String to analyze
            
        Returns:
            List of invalid character details
        """
        if pd.isna(text) or text is None or text == '':
            return []
        text = unicodedata.normalize('NFC', str(text))
        invalid_chars = []
        for i, char in enumerate(text):
            if char not in self.allowed_chars:
                invalid_chars.append({
                    'char': char,
                    'position': i,
                    'description': self.problematic_chars.get(char, f'Unknown special character (U+{ord(char):04X})')
                })
        return invalid_chars

    def validate_csv_with_tran_id(self, csv_file: str):
        """
        Validate CSV and print summary of column name, error name, and count of invalid characters
        
        Args:
            csv_file: Path to CSV file
        """
        try:
            print(f"Reading CSV file: {csv_file}")
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            if df.empty:
                print("CSV file is empty!")
                return
            
            print(f"Analyzing {len(df)} rows and {len(df.columns)} columns...")
            print("=" * 80)
            
            # Check if TRAN_ID column exists (should be first column)
            first_col = df.columns[0]
            if 'TRAN_ID' not in first_col.upper():
                print(f"WARNING: First column is '{first_col}', expected TRAN_ID")
                print(f"Using '{first_col}' as transaction identifier")
            
            # Dictionary to store error counts: {column: {error_description: count}}
            error_counts = defaultdict(lambda: defaultdict(int))
            
            # Process each row
            for row_idx, row in df.iterrows():
                for col_name in df.columns:
                    cell_value = row[col_name]
                    if self.has_invalid_chars(cell_value):
                        invalid_chars = self.get_invalid_chars(cell_value)
                        for char_info in invalid_chars:
                            error_desc = char_info['description']
                            error_counts[col_name][error_desc] += 1
                
                # Progress indicator for large files
                if (row_idx + 1) % 1000 == 0:
                    print(f"[Progress: {row_idx + 1:,} rows processed...]")
            
            # Print summary table
            print("\nInvalid Character Summary:")
            print("-" * 80)
            print(f"{'Column Name':<30} {'Error Name':<40} {'Count':<10}")
            print("-" * 80)
            
            total_errors = 0
            for col_name in sorted(error_counts.keys()):
                for error_desc, count in sorted(error_counts[col_name].items()):
                    print(f"{col_name:<30} {error_desc:<40} {count:<10}")
                    total_errors += count
            
            print("-" * 80)
            print(f"SUMMARY:")
            print(f"Total rows processed: {len(df):,}")
            print(f"Total invalid character occurrences: {total_errors:,}")
            
            if total_errors == 0:
                print("✅ No special character issues found! All data is ISO 20022 compliant.")
            else:
                print(f"❌ Found {total_errors:,} invalid character occurrences across all columns")

        except FileNotFoundError:
            print(f"Error: File '{csv_file}' not found!")
        except pd.errors.EmptyDataError:
            print("Error: CSV file is empty!")
        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")

    def validate_specific_columns(self, csv_file: str, columns_to_check: List[str] = None):
        """
        Validate specific columns and print summary of column name, error name, and count
        
        Args:
            csv_file: Path to CSV file
            columns_to_check: List of column names to check (if None, checks all)
        """
        try:
            print(f"Reading CSV file: {csv_file}")
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            if df.empty:
                print("CSV file is empty!")
                return
            
            # Determine which columns to check
            if columns_to_check:
                cols_to_check = [col for col in columns_to_check if col in df.columns]
                missing_cols = [col for col in columns_to_check if col not in df.columns]
                if missing_cols:
                    print(f"Warning: These columns don't exist: {missing_cols}")
                if not cols_to_check:
                    print("Error: None of the specified columns exist in the CSV!")
                    return
                print(f"Checking specific columns: {cols_to_check}")
            else:
                cols_to_check = df.columns.tolist()
                print(f"Checking all {len(cols_to_check)} columns")
            
            print("=" * 80)
            
            # Dictionary to store error counts: {column: {error_description: count}}
            error_counts = defaultdict(lambda: defaultdict(int))
            
            # Process each row
            for row_idx, row in df.iterrows():
                for col_name in cols_to_check:
                    cell_value = row[col_name]
                    if self.has_invalid_chars(cell_value):
                        invalid_chars = self.get_invalid_chars(cell_value)
                        for char_info in invalid_chars:
                            error_desc = char_info['description']
                            error_counts[col_name][error_desc] += 1
            
            # Print summary table
            print("\nInvalid Character Summary:")
            print("-" * 80)
            print(f"{'Column Name':<30} {'Error Name':<40} {'Count':<10}")
            print("-" * 80)
            
            total_errors = 0
            for col_name in sorted(error_counts.keys()):
                for error_desc, count in sorted(error_counts[col_name].items()):
                    print(f"{col_name:<30} {error_desc:<40} {count:<10}")
                    total_errors += count
            
            print("-" * 80)
            print(f"SUMMARY:")
            print(f"Total rows processed: {len(df):,}")
            print(f"Total invalid character occurrences: {total_errors:,}")
            
            if total_errors == 0:
                print("✅ No special character issues found in specified columns!")

        except FileNotFoundError:
            print(f"Error: File '{csv_file}' not found!")
        except pd.errors.EmptyDataError:
            print("Error: CSV file is empty!")
        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")

def main():
    """Main function with user interaction"""
    print("ISO 20022 Character Issue Reporter")
    print("=" * 45)
    print("Reports column name, error name, and count of invalid characters")
    print()
    print("⚠️  IMPORTANT NOTICE:")
    print("This validator uses general ISO 20022 character guidelines.")
    print("For EXACT Federal Reserve Fedwire character requirements:")
    print("• Access MyStandards platform: Fedwire Funds Service Release 2025")
    print("• Consult Federal Reserve ISO 20022 Implementation Guide")
    print("• Contact your Federal Reserve liaison for official specs")
    print()
    
    while True:
        csv_file = input("Enter the path to your CSV file: ").strip().strip('"\'')
        if csv_file:
            break
        print("Please enter a valid file path.")
    
    check_specific = input("\nCheck specific columns only? (y/n): ").strip().lower()
    
    validator = TranIDCharacterValidator()
    
    if check_specific in ['y', 'yes']:
        columns_input = input("Enter column names separated by commas: ").strip()
        if columns_input:
            columns_to_check = [col.strip() for col in columns_input.split(',')]
            print(f"\nChecking columns: {columns_to_check}")
            print()
            validator.validate_specific_columns(csv_file, columns_to_check)
        else:
            print("\nNo columns specified, checking all columns...")
            validator.validate_csv_with_tran_id(csv_file)
    else:
        print("\nChecking all columns for special character issues...")
        print()
        validator.validate_csv_with_tran_id(csv_file)

if __name__ == "__main__":
    main()
