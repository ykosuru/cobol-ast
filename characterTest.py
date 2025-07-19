import pandas as pd
import re
import unicodedata
from typing import Dict, List, Set
import sys

class TranIDCharacterValidator:
    """
    Validator that reports TRAN_ID and specific fields with special character issues
    """
    
    def __init__(self):
        # IMPORTANT: This validator uses general ISO 20022 character guidelines
        # For EXACT Federal Reserve Fedwire specifications, consult:
        # - MyStandards platform: Fedwire Funds Service Release 2025 Usage Guidelines
        # - Federal Reserve ISO 20022 Implementation Guide
        # - Contact your Federal Reserve liaison for official character set documentation
        
        # General ISO 20022 character pattern (may not match exact Fed requirements)
        self.iso20022_pattern = r'^[A-Za-z0-9\s\/\-\?\:\(\)\.\,\'\+]*$'
        
        # Define allowed character sets
        self.allowed_letters = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
        self.allowed_numbers = set('0123456789')
        self.allowed_special = set('/-?:().,\'+ ')  # space included
        self.allowed_chars = self.allowed_letters | self.allowed_numbers | self.allowed_special
        
        # Common problematic characters for better error messages
        self.problematic_chars = {
            '"': 'Double quote',
            '"': 'Smart double quote (left)',
            '"': 'Smart double quote (right)',
            ''': 'Smart single quote (left)', 
            ''': 'Smart single quote (right)',
            '–': 'En dash',
            '—': 'Em dash',
            '…': 'Ellipsis',
            '©': 'Copyright symbol',
            '®': 'Registered trademark',
            '™': 'Trademark',
            '°': 'Degree symbol',
            '€': 'Euro symbol',
            '£': 'Pound symbol',
            '¥': 'Yen symbol',
            '$': 'Dollar symbol',
            '%': 'Percent symbol',
            '&': 'Ampersand',
            '@': 'At symbol',
            '#': 'Hash/pound sign',
            '*': 'Asterisk',
            '~': 'Tilde',
            '`': 'Grave accent',
            '^': 'Caret',
            '_': 'Underscore',
            '=': 'Equals sign',
            '[': 'Left square bracket',
            ']': 'Right square bracket',
            '{': 'Left curly brace',
            '}': 'Right curly brace',
            '|': 'Pipe/vertical bar',
            '\\': 'Backslash',
            '<': 'Less than',
            '>': 'Greater than',
            ';': 'Semicolon',
            '\t': 'Tab character',
            '\n': 'Newline character',
            '\r': 'Carriage return'
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
        
        text = str(text)
        return not bool(re.match(self.iso20022_pattern, text))

    def get_invalid_chars(self, text: str) -> List[Dict]:
        """
        Get list of invalid characters with details
        
        Args:
            text: String to analyze
            
        Returns:
            List of invalid character details
        """
        if pd.isna(text) or text is None:
            return []
        
        text = str(text)
        invalid_chars = []
        
        for i, char in enumerate(text):
            if char not in self.allowed_chars:
                invalid_chars.append({
                    'char': char,
                    'position': i,
                    'description': self.problematic_chars.get(char, f'Unknown special character'),
                    'unicode_code': f'U+{ord(char):04X}'
                })
        
        return invalid_chars

    def format_invalid_chars(self, invalid_chars: List[Dict]) -> str:
        """
        Format invalid characters for console output
        
        Args:
            invalid_chars: List of invalid character details
            
        Returns:
            Formatted string describing the issues
        """
        if not invalid_chars:
            return ""
        
        char_descriptions = []
        for char_info in invalid_chars:
            char = char_info['char']
            pos = char_info['position']
            desc = char_info['description']
            
            # Handle special display cases
            if char == '\t':
                display_char = '\\t'
            elif char == '\n':
                display_char = '\\n'
            elif char == '\r':
                display_char = '\\r'
            elif char == ' ' and desc != 'Space':  # Non-standard space
                display_char = f'[space-{char_info["unicode_code"]}]'
            else:
                display_char = f"'{char}'"
            
            char_descriptions.append(f"{display_char}@pos{pos}({desc})")
        
        return ", ".join(char_descriptions)

    def validate_csv_with_tran_id(self, csv_file: str):
        """
        Validate CSV and print TRAN_ID with problematic fields to console
        
        Args:
            csv_file: Path to CSV file
        """
        try:
            print(f"Reading CSV file: {csv_file}")
            df = pd.read_csv(csv_file)
            
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
            
            tran_id_col = first_col
            total_rows_with_issues = 0
            total_fields_with_issues = 0
            
            # Process each row
            for row_idx, row in df.iterrows():
                tran_id = row[tran_id_col]
                row_has_issues = False
                row_issues = []
                
                # Check each column in the row for special character issues
                for col_name in df.columns:
                    cell_value = row[col_name]
                    
                    if self.has_invalid_chars(cell_value):
                        invalid_chars = self.get_invalid_chars(cell_value)
                        char_summary = self.format_invalid_chars(invalid_chars)
                        
                        row_issues.append({
                            'column': col_name,
                            'value': cell_value,
                            'invalid_chars': char_summary
                        })
                        
                        total_fields_with_issues += 1
                        row_has_issues = True
                
                # Print results for this row if it has issues
                if row_has_issues:
                    total_rows_with_issues += 1
                    print(f"TRAN_ID: {tran_id} (Row {row_idx + 1})")
                    
                    for issue in row_issues:
                        print(f"  Column: {issue['column']}")
                        print(f"  Value:  {repr(issue['value'])}")
                        print(f"  Issues: {issue['invalid_chars']}")
                        print()
                
                # Progress indicator for large files
                if (row_idx + 1) % 1000 == 0:
                    print(f"[Progress: {row_idx + 1:,} rows processed...]")
            
            print("=" * 80)
            print(f"SUMMARY:")
            print(f"Total rows processed: {len(df):,}")
            print(f"Rows with character issues: {total_rows_with_issues:,}")
            print(f"Total fields with issues: {total_fields_with_issues:,}")
            
            if total_rows_with_issues == 0:
                print("✅ No special character issues found! All data is ISO 20022 compliant.")
            else:
                compliance_rate = ((len(df) - total_rows_with_issues) / len(df)) * 100
                print(f"Row compliance rate: {compliance_rate:.1f}%")
                print(f"❌ {total_rows_with_issues} transactions need character cleanup")

        except FileNotFoundError:
            print(f"Error: File '{csv_file}' not found!")
        except pd.errors.EmptyDataError:
            print("Error: CSV file is empty!")
        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")

    def validate_specific_columns(self, csv_file: str, columns_to_check: List[str] = None):
        """
        Validate only specific columns for special character issues
        
        Args:
            csv_file: Path to CSV file
            columns_to_check: List of column names to check (if None, checks all)
        """
        try:
            print(f"Reading CSV file: {csv_file}")
            df = pd.read_csv(csv_file)
            
            if df.empty:
                print("CSV file is empty!")
                return
            
            # Use first column as TRAN_ID
            tran_id_col = df.columns[0]
            
            # Determine which columns to check
            if columns_to_check:
                # Filter to only existing columns
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
            
            total_rows_with_issues = 0
            
            # Process each row
            for row_idx, row in df.iterrows():
                tran_id = row[tran_id_col]
                row_has_issues = False
                
                # Check specified columns only
                for col_name in cols_to_check:
                    cell_value = row[col_name]
                    
                    if self.has_invalid_chars(cell_value):
                        if not row_has_issues:
                            print(f"TRAN_ID: {tran_id} (Row {row_idx + 1})")
                            row_has_issues = True
                            total_rows_with_issues += 1
                        
                        invalid_chars = self.get_invalid_chars(cell_value)
                        char_summary = self.format_invalid_chars(invalid_chars)
                        
                        print(f"  Column: {col_name}")
                        print(f"  Value:  {repr(cell_value)}")
                        print(f"  Issues: {char_summary}")
                        print()
            
            print("=" * 80)
            print(f"SUMMARY:")
            print(f"Total rows processed: {len(df):,}")
            print(f"Rows with character issues: {total_rows_with_issues:,}")
            
            if total_rows_with_issues == 0:
                print("✅ No special character issues found in specified columns!")

        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")


def main():
    """Main function with user interaction"""
    print("TRAN_ID Special Character Issue Reporter")
    print("=" * 45)
    print("Reports TRAN_ID and columns with ISO 20022 character violations")
    print()
    print("⚠️  IMPORTANT NOTICE:")
    print("This validator uses general ISO 20022 character guidelines.")
    print("For EXACT Federal Reserve Fedwire character requirements:")
    print("• Access MyStandards platform: Fedwire Funds Service Release 2025")
    print("• Consult Federal Reserve ISO 20022 Implementation Guide")
    print("• Contact your Federal Reserve liaison for official specs")
    print()
    
    # Get CSV file from user
    while True:
        csv_file = input("Enter the path to your CSV file: ").strip().strip('"\'')
        if csv_file:
            break
        print("Please enter a valid file path.")
    
    # Ask if user wants to check specific columns
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
