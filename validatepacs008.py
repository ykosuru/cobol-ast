def generate_report(self, all_issues, issue_summary, total_rows, completeness_report):
        """Generate validation report"""
        print("\n" + "="*80)
        print("PACS.008 COMPLIANCE VALIDATION REPORT")
        print("="*80)
        
        print(f"\nDATA OVERVIEW:")
        print("-" * 40)
        print(f"Total Rows Processed: {total_rows}")
        print(f"Rows with Issues: {len(all_issues)}")
        print(f"Clean Rows: {total_rows - len(all_issues)}")
        print(f"Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        print(f"\nDATA COMPLETENESS BY FIELD GROUP:")
        print("-" * 60)
        for group_name, fields in completeness_report.items():
            print(f"\n{group_name}:")
            for field_name, stats in fields.items():
                status = "✓" if stats['percentage'] > 50 else "⚠" if stats['percentage'] > 10 else "✗"
                print(f"  {status} {field_name:<25}: {stats['populated']:>4}/{total_rows} ({stats['percentage']:>5.1f}%)")
        
        if issue_summary:
            print(f"\nISSUE SUMMARY:")
            print("-" * 40)
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"{issue_type:<35}: {count:>5} occurrences")
        
        if all_issues:
            print(f"\nDETAILED ISSUES (First 20 rows):")
            print("-" * 80)
            
            for issue_data in all_issues[:20]:
                print(f"\nRow {issue_data['row']} (TRAN_ID: {issue_data['tran_id']}):")
                for issue in issue_data['issues']:
                    if issue.startswith('MISSING REQUIRED'):
                        print(f"  ⚠ {issue}")
                    else:
                        print(f"  • {issue}")
        
        print(f"\nRECOMMENDations FOR NULL/EMPTY DATA:")
        print("-" * 50)
        
        null_handling_tips = [
            "1. REQUIRED FIELDS: Must be populated for valid pacs.008 messages",
            "2. OPTIONAL FIELDS: Empty/null values are acceptable and will be omitted from XML",
            "3. CONDITIONAL FIELDS: Some fields depend on network type (SOURCE_CD/INSTR_ADV_TYPE)",
            "4. NAME CONCATENATION: Multiple name fields will be combined with spaces",
            "5. DEFAULT VALUES: Consider setting defaults for missing boolean fields (false)",
            "6. NETWORK-SPECIFIC: Only include relevant network sections based on routing"
        ]
        
        for tip in null_handling_tips:
            print(f"  {tip}")
        
        print(f"\nGENERAL COMPLIANCE RECOMMENDATIONS:")import pandas as pd
import re
from datetime import datetime
import xml.sax.saxutils as saxutils
from decimal import Decimal, InvalidOperation
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Pacs008Validator:
    def __init__(self):
        # ISO 4217 Currency codes (common ones)
        self.valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'SEK', 'NOK', 'DKK',
            'PLN', 'CZK', 'HUF', 'BGN', 'HRK', 'RON', 'TRY', 'RUB', 'CNY', 'KRW',
            'SGD', 'HKD', 'NZD', 'ZAR', 'BRL', 'MXN', 'INR', 'THB', 'MYR', 'IDR'
        }
        
        # XML reserved characters
        self.xml_reserved = ['&', '<', '>', '"', "'"]
        
        # Field length limits per pacs.008 standard
        self.field_limits = {
            'message_id': 35,
            'instruction_id': 35,
            'end_to_end_id': 35,
            'transaction_id': 35,
            'debtor_name': 70,
            'creditor_name': 70,
            'bank_name': 70,
            'account_id': 34,
            'remittance_unstructured': 140,
            'bic': 11,
            'amount_digits': 18,
            'amount_decimals': 5
        }
    
    def is_empty_or_null(self, value):
        """Check if value is null, NaN, empty string, or whitespace only"""
        if pd.isna(value):
            return True
        if value is None:
            return True
        if str(value).strip() == '' or str(value).strip().lower() == 'null':
            return True
        return False
    
    def validate_xml_characters(self, value, field_name):
        """Check for XML reserved characters"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
            
        value_str = str(value).strip()
        for char in self.xml_reserved:
            if char in value_str:
                issues.append(f"{field_name}: Contains XML reserved character '{char}'")
        return issues
    
    def validate_length(self, value, max_length, field_name):
        """Check field length limits"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
            
        value_str = str(value).strip()
        if len(value_str) > max_length:
            issues.append(f"{field_name}: Length {len(value_str)} exceeds limit of {max_length}")
        return issues
    
    def validate_date_format(self, value, field_name):
        """Validate date format (should be YYYY-MM-DD for ISO)"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
            
        date_str = str(value).strip()
        
        # Try parsing common date formats
        date_formats = [
            '%Y-%m-%d',      # ISO format
            '%m/%d/%Y',      # US format
            '%d/%m/%Y',      # European format
            '%Y/%m/%d',      # Alternative
            '%Y-%m-%d %H:%M:%S',  # With time
        ]
        
        parsed = False
        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                parsed = True
                if fmt != '%Y-%m-%d':
                    issues.append(f"{field_name}: Date format '{date_str}' should be YYYY-MM-DD")
                break
            except ValueError:
                continue
        
        if not parsed:
            issues.append(f"{field_name}: Invalid date format '{date_str}'")
        
        return issues
    
    def validate_currency_code(self, value):
        """Validate ISO 4217 currency code"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
            
        currency = str(value).strip().upper()
        if currency not in self.valid_currencies:
            issues.append(f"CURRENCY_CODE: '{currency}' is not a valid ISO 4217 currency code")
        elif str(value) != currency:
            issues.append(f"CURRENCY_CODE: Should be uppercase ('{currency}' instead of '{value}')")
        
        return issues
    
    def validate_amount(self, value, field_name):
        """Validate monetary amount"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        try:
            # Remove any currency symbols or commas
            clean_value = str(value).replace(',', '').replace('
    
    def validate_row(self, row, row_index):
        """Validate a single row of data"""
        issues = []
        
        # First check for missing required fields
        issues.extend(self.check_required_fields(row, row_index))
        
        # Only validate format/content if fields have values
        # Validate message identification fields
        issues.extend(self.validate_length(row.get('TRAN_ID'), self.field_limits['message_id'], 'TRAN_ID'))
        issues.extend(self.validate_length(row.get('TDN_NUMBER'), self.field_limits['transaction_id'], 'TDN_NUMBER'))
        issues.extend(self.validate_length(row.get('FRONTIER_REF_NO'), self.field_limits['end_to_end_id'], 'FRONTIER_REF_NO'))
        
        # Validate date fields
        date_fields = ['TXN_DATE', 'PROC_DATE', 'PAY_DATE', 'SEND_DATE', 'RCV_DATE']
        for field in date_fields:
            if field in row:
                issues.extend(self.validate_date_format(row[field], field))
        
        # Validate currency
        issues.extend(self.validate_currency_code(row.get('CURRENCY_CODE')))
        
        # Validate amount
        issues.extend(self.validate_amount(row.get('FEXCH_RATE_AMOUNT'), 'FEXCH_RATE_AMOUNT'))
        
        # Validate boolean fields
        boolean_fields = ['IS_COVER_PAYMENT', 'STRAIGHT_THR_U']
        for field in boolean_fields:
            if field in row:
                issues.extend(self.validate_boolean_field(row[field], field))
        
        # Validate BIC codes (bank IDs)
        bic_fields = ['BBK_ID', 'OBK_ID', 'IBK_ID']
        for field in bic_fields:
            if field in row:
                issues.extend(self.validate_bic_code(row[field], field))
        
        # Validate name fields (concatenated)
        creditor_name = self.concatenate_name_fields(
            row.get('CDT_NAME1'), row.get('CDT_NAME2'), 
            row.get('CDT_NAME3'), row.get('CDT_NAME4')
        )
        if creditor_name:
            issues.extend(self.validate_length(creditor_name, self.field_limits['creditor_name'], 'Creditor Name (combined)'))
            issues.extend(self.validate_xml_characters(creditor_name, 'Creditor Name'))
        
        debtor_name = self.concatenate_name_fields(
            row.get('DBT_NAME1'), row.get('DBT_NAME_2'), 
            row.get('DBT_NAME_3'), row.get('DBT_NAME_4')
        )
        if debtor_name:
            issues.extend(self.validate_length(debtor_name, self.field_limits['debtor_name'], 'Debtor Name (combined)'))
            issues.extend(self.validate_xml_characters(debtor_name, 'Debtor Name'))
        
        # Validate bank name fields
        bank_name_groups = [
            ('BBK_NAME1', 'BBK_NAME2', 'BBK_NAME3', 'BBK_NAME4', 'Beneficiary Bank'),
            ('OBK_NAME1', 'OBK_NAME2', 'OBK_NAME3', 'OBK_NAME4', 'Ordering Bank'),
            ('IBK_NAME1', 'IBK_NAME2', 'IBK_NAME3', 'IBK_NAME4', 'Intermediary Bank')
        ]
        
        for name1, name2, name3, name4, bank_type in bank_name_groups:
            bank_name = self.concatenate_name_fields(
                row.get(name1), row.get(name2), row.get(name3), row.get(name4)
            )
            if bank_name:
                issues.extend(self.validate_length(bank_name, self.field_limits['bank_name'], f'{bank_type} Name'))
                issues.extend(self.validate_xml_characters(bank_name, f'{bank_type} Name'))
        
        # Validate account fields
        account_fields = ['CDT_ACCTG_ACCOUNT', 'DBT_ACCTG_ACCOUNT']
        for field in account_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['account_id'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate free text fields
        text_fields = ['TXN_MEMO', 'DLV_MEMO']
        for field in text_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['remittance_unstructured'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate remittance information fields
        remittance_fields = ['ORP_BEN_INF1', 'ORP_BEN_INF2', 'ORP_BEN_INF3', 'ORP_BEN_INF4']
        for field in remittance_fields:
            if field in row:
                issues.extend(self.validate_xml_characters(row[field], field))
        
        return issues
    
    def process_excel_file(self, file_path):
        """Process the Excel file and validate all rows"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Track all issues
            all_issues = []
            issue_summary = {}
            
            # Validate each row
            for index, row in df.iterrows():
                row_issues = self.validate_row(row, index + 1)
                
                if row_issues:
                    all_issues.append({
                        'row': index + 1,
                        'tran_id': row.get('TRAN_ID', 'N/A'),
                        'issues': row_issues
                    })
                    
                    # Count issue types
                    for issue in row_issues:
                        issue_type = issue.split(':')[0]
                        issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # Generate report
            self.generate_report(all_issues, issue_summary, len(df))
            
            return all_issues
            
        except Exception as e:
            logging.error(f"Error processing Excel file: {str(e)}")
            return None
    
    def generate_report(self, all_issues, issue_summary, total_rows):
        """Generate validation report"""
        print("\n" + "="*80)
        print("PACS.008 COMPLIANCE VALIDATION REPORT")
        print("="*80)
        
        print(f"\nTotal Rows Processed: {total_rows}")
        print(f"Rows with Issues: {len(all_issues)}")
        print(f"Clean Rows: {total_rows - len(all_issues)}")
        print(f"Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        if issue_summary:
            print(f"\nISSUE SUMMARY:")
            print("-" * 40)
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"{issue_type:<30}: {count:>5} occurrences")
        
        if all_issues:
            print(f"\nDETAILED ISSUES (First 20 rows):")
            print("-" * 80)
            
            for issue_data in all_issues[:20]:
                print(f"\nRow {issue_data['row']} (TRAN_ID: {issue_data['tran_id']}):")
                for issue in issue_data['issues']:
                    print(f"  • {issue}")
        
        print(f"\nGENERAL COMPLIANCE RECOMMENDATIONS:")
        print("-" * 50)
        
        common_fixes = [
            "1. Escape XML reserved characters (&, <, >, \", ') in text fields",
            "2. Convert dates to YYYY-MM-DD format",
            "3. Ensure currency codes are uppercase and ISO 4217 compliant", 
            "4. Validate BIC codes are 8 or 11 characters with proper format",
            "5. Check field length limits for names and text fields",
            "6. Convert boolean values to 'true'/'false' format",
            "7. Remove currency symbols from amount fields",
            "8. Concatenate multiple name fields with proper spacing",
            "9. Focus on populating required fields first",
            "10. Consider data enrichment for low-populated critical fields"
        ]
        
        for fix in common_fixes:
            print(f"  {fix}")

    def process_excel_file(self, file_path):
        """Process the Excel file and validate all rows"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Analyze data completeness first
            completeness_report = self.analyze_data_completeness(df)
            
            # Track all issues
            all_issues = []
            issue_summary = {}
            
            # Validate each row
            for index, row in df.iterrows():
                row_issues = self.validate_row(row, index + 1)
                
                if row_issues:
                    all_issues.append({
                        'row': index + 1,
                        'tran_id': row.get('TRAN_ID', 'N/A'),
                        'issues': row_issues
                    })
                    
                    # Count issue types
                    for issue in row_issues:
                        issue_type = issue.split(':')[0]
                        issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # Generate report
            self.generate_report(all_issues, issue_summary, len(df), completeness_report)
            
            return all_issues
            
        except Exception as e:
            logging.error(f"Error processing Excel file: {str(e)}")
            return None, '').replace('€', '').strip()
            
            # Convert to Decimal for precision
            amount = Decimal(clean_value)
            
            # Check if negative
            if amount < 0:
                issues.append(f"{field_name}: Amount cannot be negative ({amount})")
            
            # Check decimal places
            if amount.as_tuple().exponent < -self.field_limits['amount_decimals']:
                issues.append(f"{field_name}: Too many decimal places (max {self.field_limits['amount_decimals']})")
            
            # Check total digits
            digits = len(str(amount).replace('.', '').replace('-', ''))
            if digits > self.field_limits['amount_digits']:
                issues.append(f"{field_name}: Too many digits (max {self.field_limits['amount_digits']})")
                
        except (InvalidOperation, ValueError):
            issues.append(f"{field_name}: Invalid amount format '{value}'")
        
        return issues
    
    def validate_boolean_field(self, value, field_name):
        """Validate boolean fields"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        value_str = str(value).strip().lower()
        valid_true = ['true', '1', 'yes', 'y']
        valid_false = ['false', '0', 'no', 'n']
        
        if value_str not in valid_true + valid_false:
            issues.append(f"{field_name}: Invalid boolean value '{value}' (should be true/false)")
        
        return issues
    
    def validate_bic_code(self, value, field_name):
        """Validate BIC/SWIFT code format"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        bic = str(value).strip().upper()
        
        # BIC format: 4 letters (bank) + 2 letters (country) + 2 alphanumeric (location) + optional 3 alphanumeric (branch)
        bic_pattern = r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?
    
    def validate_row(self, row, row_index):
        """Validate a single row of data"""
        issues = []
        
        # Validate message identification fields
        issues.extend(self.validate_length(row.get('TRAN_ID'), self.field_limits['message_id'], 'TRAN_ID'))
        issues.extend(self.validate_length(row.get('TDN_NUMBER'), self.field_limits['transaction_id'], 'TDN_NUMBER'))
        issues.extend(self.validate_length(row.get('FRONTIER_REF_NO'), self.field_limits['end_to_end_id'], 'FRONTIER_REF_NO'))
        
        # Validate date fields
        date_fields = ['TXN_DATE', 'PROC_DATE', 'PAY_DATE', 'SEND_DATE', 'RCV_DATE']
        for field in date_fields:
            if field in row:
                issues.extend(self.validate_date_format(row[field], field))
        
        # Validate currency
        issues.extend(self.validate_currency_code(row.get('CURRENCY_CODE')))
        
        # Validate amount
        issues.extend(self.validate_amount(row.get('FEXCH_RATE_AMOUNT'), 'FEXCH_RATE_AMOUNT'))
        
        # Validate boolean fields
        boolean_fields = ['IS_COVER_PAYMENT', 'STRAIGHT_THR_U']
        for field in boolean_fields:
            if field in row:
                issues.extend(self.validate_boolean_field(row[field], field))
        
        # Validate BIC codes (bank IDs)
        bic_fields = ['BBK_ID', 'OBK_ID', 'IBK_ID']
        for field in bic_fields:
            if field in row:
                issues.extend(self.validate_bic_code(row[field], field))
        
        # Validate name fields (concatenated)
        creditor_name = self.concatenate_name_fields(
            row.get('CDT_NAME1'), row.get('CDT_NAME2'), 
            row.get('CDT_NAME3'), row.get('CDT_NAME4')
        )
        if creditor_name:
            issues.extend(self.validate_length(creditor_name, self.field_limits['creditor_name'], 'Creditor Name (combined)'))
            issues.extend(self.validate_xml_characters(creditor_name, 'Creditor Name'))
        
        debtor_name = self.concatenate_name_fields(
            row.get('DBT_NAME1'), row.get('DBT_NAME_2'), 
            row.get('DBT_NAME_3'), row.get('DBT_NAME_4')
        )
        if debtor_name:
            issues.extend(self.validate_length(debtor_name, self.field_limits['debtor_name'], 'Debtor Name (combined)'))
            issues.extend(self.validate_xml_characters(debtor_name, 'Debtor Name'))
        
        # Validate bank name fields
        bank_name_groups = [
            ('BBK_NAME1', 'BBK_NAME2', 'BBK_NAME3', 'BBK_NAME4', 'Beneficiary Bank'),
            ('OBK_NAME1', 'OBK_NAME2', 'OBK_NAME3', 'OBK_NAME4', 'Ordering Bank'),
            ('IBK_NAME1', 'IBK_NAME2', 'IBK_NAME3', 'IBK_NAME4', 'Intermediary Bank')
        ]
        
        for name1, name2, name3, name4, bank_type in bank_name_groups:
            bank_name = self.concatenate_name_fields(
                row.get(name1), row.get(name2), row.get(name3), row.get(name4)
            )
            if bank_name:
                issues.extend(self.validate_length(bank_name, self.field_limits['bank_name'], f'{bank_type} Name'))
                issues.extend(self.validate_xml_characters(bank_name, f'{bank_type} Name'))
        
        # Validate account fields
        account_fields = ['CDT_ACCTG_ACCOUNT', 'DBT_ACCTG_ACCOUNT']
        for field in account_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['account_id'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate free text fields
        text_fields = ['TXN_MEMO', 'DLV_MEMO']
        for field in text_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['remittance_unstructured'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate remittance information fields
        remittance_fields = ['ORP_BEN_INF1', 'ORP_BEN_INF2', 'ORP_BEN_INF3', 'ORP_BEN_INF4']
        for field in remittance_fields:
            if field in row:
                issues.extend(self.validate_xml_characters(row[field], field))
        
        return issues
    
    def process_excel_file(self, file_path):
        """Process the Excel file and validate all rows"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Track all issues
            all_issues = []
            issue_summary = {}
            
            # Validate each row
            for index, row in df.iterrows():
                row_issues = self.validate_row(row, index + 1)
                
                if row_issues:
                    all_issues.append({
                        'row': index + 1,
                        'tran_id': row.get('TRAN_ID', 'N/A'),
                        'issues': row_issues
                    })
                    
                    # Count issue types
                    for issue in row_issues:
                        issue_type = issue.split(':')[0]
                        issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # Generate report
            self.generate_report(all_issues, issue_summary, len(df))
            
            return all_issues
            
        except Exception as e:
            logging.error(f"Error processing Excel file: {str(e)}")
            return None
    
    def generate_report(self, all_issues, issue_summary, total_rows):
        """Generate validation report"""
        print("\n" + "="*80)
        print("PACS.008 COMPLIANCE VALIDATION REPORT")
        print("="*80)
        
        print(f"\nTotal Rows Processed: {total_rows}")
        print(f"Rows with Issues: {len(all_issues)}")
        print(f"Clean Rows: {total_rows - len(all_issues)}")
        print(f"Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        if issue_summary:
            print(f"\nISSUE SUMMARY:")
            print("-" * 40)
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"{issue_type:<30}: {count:>5} occurrences")
        
        if all_issues:
            print(f"\nDETAILED ISSUES (First 20 rows):")
            print("-" * 80)
            
            for issue_data in all_issues[:20]:
                print(f"\nRow {issue_data['row']} (TRAN_ID: {issue_data['tran_id']}):")
                for issue in issue_data['issues']:
                    print(f"  • {issue}")
        
        print(f"\nRECOMMENDATIONS:")
        print("-" * 40)
        
        common_fixes = [
            "1. Escape XML reserved characters (&, <, >, \", ') in text fields",
            "2. Convert dates to YYYY-MM-DD format",
            "3. Ensure currency codes are uppercase and ISO 4217 compliant", 
            "4. Validate BIC codes are 8 or 11 characters with proper format",
            "5. Check field length limits for names and text fields",
            "6. Convert boolean values to 'true'/'false' format",
            "7. Remove currency symbols from amount fields",
            "8. Concatenate multiple name fields with proper spacing"
        ]
        
        for fix in common_fixes:
            print(f"  {fix}")

# Usage example
def main():
    validator = Pacs008Validator()
    
    # Replace with your Excel file path
    excel_file_path = "wire_transfer_data.xlsx"  # Update this path
    
    print("Starting pacs.008 compliance validation...")
    issues = validator.process_excel_file(excel_file_path)
    
    if issues is not None:
        print(f"\nValidation completed. Check the report above for details.")
    else:
        print("Validation failed. Please check the file path and format.")

if __name__ == "__main__":
    main()
        
        if not re.match(bic_pattern, bic):
            issues.append(f"{field_name}: Invalid BIC format '{value}'")
        
        if len(bic) not in [8, 11]:
            issues.append(f"{field_name}: BIC length should be 8 or 11 characters")
        
        return issues
    
    def concatenate_name_fields(self, name1, name2, name3, name4):
        """Concatenate multiple name fields with proper spacing"""
        names = []
        for name in [name1, name2, name3, name4]:
            if not self.is_empty_or_null(name):
                clean_name = str(name).strip()
                if clean_name:
                    names.append(clean_name)
        return ' '.join(names)
    
    def check_required_fields(self, row, row_index):
        """Check for missing required fields per pacs.008 standard"""
        issues = []
        
        # Core required fields for pacs.008
        required_fields = {
            'TRAN_ID': 'Message Identification',
            'TXN_DATE': 'Creation Date Time', 
            'FEXCH_RATE_AMOUNT': 'Instructed Amount',
            'CURRENCY_CODE': 'Currency Code'
        }
        
        # At least one identification method needed
        debtor_identification = any(not self.is_empty_or_null(row.get(field)) 
                                  for field in ['DBT_ID', 'DBT_ACCTG_ACCOUNT'])
        creditor_identification = any(not self.is_empty_or_null(row.get(field)) 
                                    for field in ['CDT_ID', 'CDT_ACCTG_ACCOUNT'])
        
        # At least one name field needed
        debtor_name = self.concatenate_name_fields(
            row.get('DBT_NAME1'), row.get('DBT_NAME_2'), 
            row.get('DBT_NAME_3'), row.get('DBT_NAME_4')
        )
        creditor_name = self.concatenate_name_fields(
            row.get('CDT_NAME1'), row.get('CDT_NAME2'), 
            row.get('CDT_NAME3'), row.get('CDT_NAME4')
        )
        
        # Check required fields
        for field, description in required_fields.items():
            if self.is_empty_or_null(row.get(field)):
                issues.append(f"MISSING REQUIRED: {field} ({description}) is required for pacs.008")
        
        # Check party identification
        if not debtor_identification:
            issues.append("MISSING REQUIRED: Debtor identification (DBT_ID or DBT_ACCTG_ACCOUNT) is required")
        
        if not creditor_identification:
            issues.append("MISSING REQUIRED: Creditor identification (CDT_ID or CDT_ACCTG_ACCOUNT) is required")
        
        # Check party names
        if not debtor_name:
            issues.append("MISSING REQUIRED: Debtor name (at least one DBT_NAME field) is required")
        
        if not creditor_name:
            issues.append("MISSING REQUIRED: Creditor name (at least one CDT_NAME field) is required")
        
        return issues
    
    def analyze_data_completeness(self, df):
        """Analyze overall data completeness"""
        completeness_report = {}
        
        field_groups = {
            'Core Transaction': ['TRAN_ID', 'TXN_DATE', 'FEXCH_RATE_AMOUNT', 'CURRENCY_CODE'],
            'Debtor Info': ['DBT_NAME1', 'DBT_NAME_2', 'DBT_NAME_3', 'DBT_NAME_4', 'DBT_ID', 'DBT_ACCTG_ACCOUNT'],
            'Creditor Info': ['CDT_NAME1', 'CDT_NAME2', 'CDT_NAME3', 'CDT_NAME4', 'CDT_ID', 'CDT_ACCTG_ACCOUNT'],
            'Bank Info': ['BBK_ID', 'BBK_NAME1', 'OBK_ID', 'OBK_NAME1'],
            'Network Info': ['SOURCE_CD', 'INSTR_ADV_TYPE', 'FED_IMAD', 'SWF_IN_MIR'],
            'Remittance': ['TXN_MEMO', 'ORP_BEN_INF1', 'ORP_BEN_INF2']
        }
        
        total_rows = len(df)
        
        for group_name, fields in field_groups.items():
            group_stats = {}
            
            for field in fields:
                if field in df.columns:
                    non_empty = df[field].notna().sum()
                    non_empty_non_blank = sum(1 for val in df[field] if not self.is_empty_or_null(val))
                    group_stats[field] = {
                        'populated': non_empty_non_blank,
                        'percentage': (non_empty_non_blank / total_rows) * 100
                    }
                else:
                    group_stats[field] = {'populated': 0, 'percentage': 0.0}
            
            completeness_report[group_name] = group_stats
        
        return completeness_report
    
    def validate_row(self, row, row_index):
        """Validate a single row of data"""
        issues = []
        
        # Validate message identification fields
        issues.extend(self.validate_length(row.get('TRAN_ID'), self.field_limits['message_id'], 'TRAN_ID'))
        issues.extend(self.validate_length(row.get('TDN_NUMBER'), self.field_limits['transaction_id'], 'TDN_NUMBER'))
        issues.extend(self.validate_length(row.get('FRONTIER_REF_NO'), self.field_limits['end_to_end_id'], 'FRONTIER_REF_NO'))
        
        # Validate date fields
        date_fields = ['TXN_DATE', 'PROC_DATE', 'PAY_DATE', 'SEND_DATE', 'RCV_DATE']
        for field in date_fields:
            if field in row:
                issues.extend(self.validate_date_format(row[field], field))
        
        # Validate currency
        issues.extend(self.validate_currency_code(row.get('CURRENCY_CODE')))
        
        # Validate amount
        issues.extend(self.validate_amount(row.get('FEXCH_RATE_AMOUNT'), 'FEXCH_RATE_AMOUNT'))
        
        # Validate boolean fields
        boolean_fields = ['IS_COVER_PAYMENT', 'STRAIGHT_THR_U']
        for field in boolean_fields:
            if field in row:
                issues.extend(self.validate_boolean_field(row[field], field))
        
        # Validate BIC codes (bank IDs)
        bic_fields = ['BBK_ID', 'OBK_ID', 'IBK_ID']
        for field in bic_fields:
            if field in row:
                issues.extend(self.validate_bic_code(row[field], field))
        
        # Validate name fields (concatenated)
        creditor_name = self.concatenate_name_fields(
            row.get('CDT_NAME1'), row.get('CDT_NAME2'), 
            row.get('CDT_NAME3'), row.get('CDT_NAME4')
        )
        if creditor_name:
            issues.extend(self.validate_length(creditor_name, self.field_limits['creditor_name'], 'Creditor Name (combined)'))
            issues.extend(self.validate_xml_characters(creditor_name, 'Creditor Name'))
        
        debtor_name = self.concatenate_name_fields(
            row.get('DBT_NAME1'), row.get('DBT_NAME_2'), 
            row.get('DBT_NAME_3'), row.get('DBT_NAME_4')
        )
        if debtor_name:
            issues.extend(self.validate_length(debtor_name, self.field_limits['debtor_name'], 'Debtor Name (combined)'))
            issues.extend(self.validate_xml_characters(debtor_name, 'Debtor Name'))
        
        # Validate bank name fields
        bank_name_groups = [
            ('BBK_NAME1', 'BBK_NAME2', 'BBK_NAME3', 'BBK_NAME4', 'Beneficiary Bank'),
            ('OBK_NAME1', 'OBK_NAME2', 'OBK_NAME3', 'OBK_NAME4', 'Ordering Bank'),
            ('IBK_NAME1', 'IBK_NAME2', 'IBK_NAME3', 'IBK_NAME4', 'Intermediary Bank')
        ]
        
        for name1, name2, name3, name4, bank_type in bank_name_groups:
            bank_name = self.concatenate_name_fields(
                row.get(name1), row.get(name2), row.get(name3), row.get(name4)
            )
            if bank_name:
                issues.extend(self.validate_length(bank_name, self.field_limits['bank_name'], f'{bank_type} Name'))
                issues.extend(self.validate_xml_characters(bank_name, f'{bank_type} Name'))
        
        # Validate account fields
        account_fields = ['CDT_ACCTG_ACCOUNT', 'DBT_ACCTG_ACCOUNT']
        for field in account_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['account_id'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate free text fields
        text_fields = ['TXN_MEMO', 'DLV_MEMO']
        for field in text_fields:
            if field in row:
                issues.extend(self.validate_length(row[field], self.field_limits['remittance_unstructured'], field))
                issues.extend(self.validate_xml_characters(row[field], field))
        
        # Validate remittance information fields
        remittance_fields = ['ORP_BEN_INF1', 'ORP_BEN_INF2', 'ORP_BEN_INF3', 'ORP_BEN_INF4']
        for field in remittance_fields:
            if field in row:
                issues.extend(self.validate_xml_characters(row[field], field))
        
        return issues
    
    def process_excel_file(self, file_path):
        """Process the Excel file and validate all rows"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Track all issues
            all_issues = []
            issue_summary = {}
            
            # Validate each row
            for index, row in df.iterrows():
                row_issues = self.validate_row(row, index + 1)
                
                if row_issues:
                    all_issues.append({
                        'row': index + 1,
                        'tran_id': row.get('TRAN_ID', 'N/A'),
                        'issues': row_issues
                    })
                    
                    # Count issue types
                    for issue in row_issues:
                        issue_type = issue.split(':')[0]
                        issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # Generate report
            self.generate_report(all_issues, issue_summary, len(df))
            
            return all_issues
            
        except Exception as e:
            logging.error(f"Error processing Excel file: {str(e)}")
            return None
    
    def generate_report(self, all_issues, issue_summary, total_rows):
        """Generate validation report"""
        print("\n" + "="*80)
        print("PACS.008 COMPLIANCE VALIDATION REPORT")
        print("="*80)
        
        print(f"\nTotal Rows Processed: {total_rows}")
        print(f"Rows with Issues: {len(all_issues)}")
        print(f"Clean Rows: {total_rows - len(all_issues)}")
        print(f"Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        if issue_summary:
            print(f"\nISSUE SUMMARY:")
            print("-" * 40)
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"{issue_type:<30}: {count:>5} occurrences")
        
        if all_issues:
            print(f"\nDETAILED ISSUES (First 20 rows):")
            print("-" * 80)
            
            for issue_data in all_issues[:20]:
                print(f"\nRow {issue_data['row']} (TRAN_ID: {issue_data['tran_id']}):")
                for issue in issue_data['issues']:
                    print(f"  • {issue}")
        
        print(f"\nRECOMMENDATIONS:")
        print("-" * 40)
        
        common_fixes = [
            "1. Escape XML reserved characters (&, <, >, \", ') in text fields",
            "2. Convert dates to YYYY-MM-DD format",
            "3. Ensure currency codes are uppercase and ISO 4217 compliant", 
            "4. Validate BIC codes are 8 or 11 characters with proper format",
            "5. Check field length limits for names and text fields",
            "6. Convert boolean values to 'true'/'false' format",
            "7. Remove currency symbols from amount fields",
            "8. Concatenate multiple name fields with proper spacing"
        ]
        
        for fix in common_fixes:
            print(f"  {fix}")

# Usage example
def main():
    validator = Pacs008Validator()
    
    # Replace with your Excel file path
    excel_file_path = "wire_transfer_data.xlsx"  # Update this path
    
    print("Starting pacs.008 compliance validation...")
    issues = validator.process_excel_file(excel_file_path)
    
    if issues is not None:
        print(f"\nValidation completed. Check the report above for details.")
    else:
        print("Validation failed. Please check the file path and format.")

if __name__ == "__main__":
    main()
