import pandas as pd
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
import sys
from datetime import datetime

class PACS008XSDValidator:
    """
    Enhanced PACS.008.001.08 validator with XSD compliance and Federal Reserve requirements
    """
    
    def __init__(self):
        # XSD-based validation patterns from PACS.008.001.08
        self.xsd_patterns = {
            'Max35Text': r'^.{1,35}$',
            'Max140Text': r'^.{1,140}$',
            'Max15NumericText': r'^[0-9]{1,15}$',
            'IBAN2007Identifier': r'^[A-Z]{2,2}[0-9]{2,2}[a-zA-Z0-9]{1,30}$',
            'BICFIDec2014Identifier': r'^[A-Z0-9]{4,4}[A-Z]{2,2}[A-Z0-9]{2,2}([A-Z0-9]{3,3}){0,1}$',
            'ActiveCurrencyCode': r'^[A-Z]{3,3}$',
            'CountryCode': r'^[A-Z]{2,2}$',
            'LEIIdentifier': r'^[A-Z0-9]{18,18}[0-9]{2,2}$',
            'UUIDv4Identifier': r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
        }
        
        # Valid enumeration values from XSD
        self.valid_enums = {
            'ChargeBearerType1Code': {'DEBT', 'CRED', 'SHAR', 'SLEV'},
            'ClearingChannel2Code': {'RTGS', 'RTNS', 'MPNS', 'BOOK'},
            'SettlementMethod1Code': {'INDA', 'INGA', 'COVE', 'CLRG'},
            'Priority2Code': {'HIGH', 'NORM'},
            'Priority3Code': {'URGT', 'HIGH', 'NORM'},
            'CreditDebitCode': {'CRDT', 'DBIT'},
            'AddressType2Code': {'ADDR', 'PBOX', 'HOME', 'BIZZ', 'MLTO', 'DLVY'},
            'Instruction4Code': {'PHOA', 'TELA'},
            'NamePrefix2Code': {'DOCT', 'MADM', 'MISS', 'MIST', 'MIKS'},
            'PreferredContactMethod1Code': {'LETT', 'MAIL', 'PHON', 'FAXX', 'CELL'},
            'RegulatoryReportingType1Code': {'CRED', 'DEBT', 'BOTH'},
            'RemittanceLocationMethod2Code': {'FAXI', 'EDIC', 'URID', 'EMAL', 'POST', 'SMSM'},
            'DocumentType3Code': {'RADM', 'RPIN', 'FXDR', 'DISP', 'PUOR', 'SCOR'},
            'DocumentType6Code': {'MSIN', 'CNFA', 'DNFA', 'CINV', 'CREN', 'DEBN', 'HIRI', 'SBIN', 'CMCN', 'SOAC', 'DISP', 'BOLD', 'VCHR', 'AROI', 'TSUT', 'PUOR'},
            'MandateClassification1Code': {'FIXE', 'USGB', 'VARI'},
            'Frequency6Code': {'YEAR', 'MNTH', 'QURT', 'MIAN', 'WEEK', 'DAIL', 'ADHO', 'INDA', 'FRTN'},
            'TaxRecordPeriod1Code': {'MM01', 'MM02', 'MM03', 'MM04', 'MM05', 'MM06', 'MM07', 'MM08', 'MM09', 'MM10', 'MM11', 'MM12', 'QTR1', 'QTR2', 'QTR3', 'QTR4', 'HLF1', 'HLF2'}
        }
        
        # Federal Reserve specific validation for wire transfers
        self.fed_wire_patterns = {
            'FED_IMAD': r'^[0-9]{8}[0-9A-Z]{4}[0-9]{6}$',  # YYYYMMDDSSSSRRRRRR format
            'FED_OMAD': r'^[0-9]{8}[0-9A-Z]{4}[0-9]{6}$',  # Same as IMAD format
            'FED_ISN': r'^[A-Z0-9]{16}$',                   # 16 alphanumeric characters
            'FED_OSN': r'^[A-Z0-9]{16}$'                    # 16 alphanumeric characters
        }
        
        # External code restrictions from XSD (length limits)
        self.external_codes = {
            'ExternalAccountIdentification1Code': (1, 4),
            'ExternalCashAccountType1Code': (1, 4),
            'ExternalCashClearingSystem1Code': (1, 3),
            'ExternalCategoryPurpose1Code': (1, 4),
            'ExternalClearingSystemIdentification1Code': (1, 5),
            'ExternalCreditorAgentInstruction1Code': (1, 4),
            'ExternalDiscountAmountType1Code': (1, 4),
            'ExternalDocumentLineType1Code': (1, 4),
            'ExternalFinancialInstitutionIdentification1Code': (1, 4),
            'ExternalGarnishmentType1Code': (1, 4),
            'ExternalLocalInstrument1Code': (1, 35),
            'ExternalMandateSetupReason1Code': (1, 4),
            'ExternalOrganisationIdentification1Code': (1, 4),
            'ExternalPersonIdentification1Code': (1, 4),
            'ExternalProxyAccountType1Code': (1, 4),
            'ExternalPurpose1Code': (1, 4),
            'ExternalServiceLevel1Code': (1, 4),
            'ExternalTaxAmountType1Code': (1, 4)
        }
        
        # Your specific data element validation
        self.valid_source_cd = {'FED', 'ACH', 'WIRE', 'BOOK', 'SWIFT'}
        self.valid_instr_adv_type = {'FED', 'SWIFT', 'TELEX', 'PHONE', 'EMAIL'}
        self.valid_tran_type = {'FTR', 'CHK', 'TRF', 'ACH', 'WIRE'}
        self.valid_wire_type = {'FWI', 'COVER', 'BOOK', 'FEDWIRE'}
        
        # Required columns for validation
        self.required_columns = [
            'SOURCE_CD', 'INSTR_ADV_TYPE', 'TRAN_TYPE', 'WIRE_TYPE',
            'FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN'
        ]

    def validate_xsd_pattern(self, value: str, pattern_name: str) -> Tuple[bool, str]:
        """Validate value against XSD pattern"""
        if pattern_name not in self.xsd_patterns:
            return True, ""
        
        pattern = self.xsd_patterns[pattern_name]
        if not re.match(pattern, str(value)):
            return False, f"Value '{value}' does not match XSD pattern for {pattern_name}"
        return True, ""

    def validate_xsd_enum(self, value: str, enum_name: str) -> Tuple[bool, str]:
        """Validate value against XSD enumeration"""
        if enum_name not in self.valid_enums:
            return True, ""
        
        if value not in self.valid_enums[enum_name]:
            valid_values = ', '.join(sorted(self.valid_enums[enum_name]))
            return False, f"Invalid {enum_name} '{value}'. Valid values: {valid_values}"
        return True, ""

    def validate_external_code(self, value: str, code_type: str) -> Tuple[bool, str]:
        """Validate external code length restrictions"""
        if code_type not in self.external_codes:
            return True, ""
        
        min_len, max_len = self.external_codes[code_type]
        if not (min_len <= len(value) <= max_len):
            return False, f"{code_type} length must be between {min_len} and {max_len} characters"
        return True, ""

    def validate_decimal_format(self, value: str, total_digits: int, fraction_digits: int) -> Tuple[bool, str]:
        """Validate decimal format according to XSD restrictions"""
        try:
            decimal_val = float(value)
            if decimal_val < 0:
                return False, f"Value must be non-negative"
            
            # Check total digits and fraction digits
            str_val = str(decimal_val)
            if '.' in str_val:
                integer_part, fraction_part = str_val.split('.')
                if len(fraction_part) > fraction_digits:
                    return False, f"Maximum {fraction_digits} fraction digits allowed"
                total_used = len(integer_part) + len(fraction_part)
            else:
                total_used = len(str_val)
            
            if total_used > total_digits:
                return False, f"Maximum {total_digits} total digits allowed"
                
            return True, ""
        except ValueError:
            return False, f"Invalid decimal format"

    def validate_fed_reference(self, value: str, ref_type: str) -> Tuple[bool, str]:
        """Validate Federal Reserve reference number formats with enhanced rules"""
        if pd.isna(value) or value == '':
            return False, f"{ref_type} cannot be empty"
        
        value = str(value).strip().upper()
        
        if ref_type in ['FED_IMAD', 'FED_OMAD']:
            # Enhanced IMAD/OMAD validation: YYYYMMDDSSSSRRRRRR
            if not re.match(self.fed_wire_patterns[ref_type], value):
                return False, f"{ref_type} must follow YYYYMMDDSSSSRRRRRR format (18 characters: 8-digit date + 4-char sequence + 6-digit routing)"
            
            # Validate date portion
            date_part = value[:8]
            try:
                datetime.strptime(date_part, '%Y%m%d')
            except ValueError:
                return False, f"{ref_type} contains invalid date: {date_part}"
            
            # Validate routing number portion (last 6 digits should be valid routing format)
            routing_part = value[-6:]
            if not routing_part.isdigit():
                return False, f"{ref_type} routing portion must be 6 digits"
        
        elif ref_type in ['FED_ISN', 'FED_OSN']:
            # ISN/OSN validation: 16 alphanumeric characters
            if not re.match(self.fed_wire_patterns[ref_type], value):
                return False, f"{ref_type} must be exactly 16 alphanumeric characters (A-Z, 0-9)"
        
        return True, ""

    def validate_amount_format(self, value: str) -> Tuple[bool, str]:
        """Validate amount according to ActiveCurrencyAndAmount XSD type"""
        return self.validate_decimal_format(value, 18, 5)

    def validate_row(self, row: pd.Series, row_index: int) -> Dict:
        """Enhanced row validation with XSD compliance"""
        errors = []
        warnings = []
        
        # Check required columns
        missing_columns = [col for col in self.required_columns if col not in row.index]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            return {
                'row_index': row_index,
                'is_valid': False,
                'errors': errors,
                'warnings': warnings
            }
        
        # Validate SOURCE_CD against XSD Max35Text and custom enum
        source_cd = str(row.get('SOURCE_CD', '')).strip().upper()
        is_valid, error = self.validate_xsd_pattern(source_cd, 'Max35Text')
        if not is_valid:
            errors.append(f"SOURCE_CD XSD validation: {error}")
        elif source_cd not in self.valid_source_cd:
            errors.append(f"Invalid SOURCE_CD '{source_cd}'. Valid values: {', '.join(self.valid_source_cd)}")
        
        # Validate INSTR_ADV_TYPE
        instr_adv_type = str(row.get('INSTR_ADV_TYPE', '')).strip().upper()
        is_valid, error = self.validate_xsd_pattern(instr_adv_type, 'Max35Text')
        if not is_valid:
            errors.append(f"INSTR_ADV_TYPE XSD validation: {error}")
        elif instr_adv_type not in self.valid_instr_adv_type:
            errors.append(f"Invalid INSTR_ADV_TYPE '{instr_adv_type}'. Valid values: {', '.join(self.valid_instr_adv_type)}")
        
        # Validate TRAN_TYPE
        tran_type = str(row.get('TRAN_TYPE', '')).strip().upper()
        is_valid, error = self.validate_xsd_pattern(tran_type, 'Max35Text')
        if not is_valid:
            errors.append(f"TRAN_TYPE XSD validation: {error}")
        elif tran_type not in self.valid_tran_type:
            errors.append(f"Invalid TRAN_TYPE '{tran_type}'. Valid values: {', '.join(self.valid_tran_type)}")
        
        # Validate WIRE_TYPE
        wire_type = str(row.get('WIRE_TYPE', '')).strip().upper()
        is_valid, error = self.validate_xsd_pattern(wire_type, 'Max35Text')
        if not is_valid:
            errors.append(f"WIRE_TYPE XSD validation: {error}")
        elif wire_type not in self.valid_wire_type:
            errors.append(f"Invalid WIRE_TYPE '{wire_type}'. Valid values: {', '.join(self.valid_wire_type)}")
        
        # Validate Federal Reserve reference numbers
        for fed_field in ['FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN']:
            is_valid, error_msg = self.validate_fed_reference(row.get(fed_field), fed_field)
            if not is_valid:
                errors.append(error_msg)
        
        # Cross-validation rules for PACS.008.001.08 Federal Reserve compliance
        if source_cd == 'FED':
            if wire_type not in ['FWI', 'FEDWIRE']:
                warnings.append("Federal source requires FWI or FEDWIRE wire type")
            if tran_type != 'FTR':
                warnings.append("Federal source typically uses FTR transaction type")
        
        if tran_type == 'FTR' and source_cd != 'FED':
            warnings.append("FTR transaction type typically requires FED source")
        
        if wire_type == 'FWI' and source_cd != 'FED':
            warnings.append("FWI wire type typically requires FED source")
        
        # Additional XSD-based validations for optional fields if present
        optional_validations = {
            'CURRENCY_CODE': ('ActiveCurrencyCode', None),
            'AMOUNT': ('amount_format', None),
            'BIC_CODE': ('BICFIDec2014Identifier', None),
            'IBAN': ('IBAN2007Identifier', None),
            'COUNTRY_CODE': ('CountryCode', None),
            'CHARGE_BEARER': (None, 'ChargeBearerType1Code'),
            'CLEARING_CHANNEL': (None, 'ClearingChannel2Code'),
            'SETTLEMENT_METHOD': (None, 'SettlementMethod1Code'),
            'PRIORITY': (None, 'Priority3Code')
        }
        
        for field, (pattern, enum) in optional_validations.items():
            if field in row.index and pd.notna(row[field]) and str(row[field]).strip():
                value = str(row[field]).strip().upper()
                
                if pattern == 'amount_format':
                    is_valid, error = self.validate_amount_format(value)
                    if not is_valid:
                        warnings.append(f"{field}: {error}")
                elif pattern:
                    is_valid, error = self.validate_xsd_pattern(value, pattern)
                    if not is_valid:
                        warnings.append(f"{field}: {error}")
                elif enum:
                    is_valid, error = self.validate_xsd_enum(value, enum)
                    if not is_valid:
                        warnings.append(f"{field}: {error}")
        
        return {
            'row_index': row_index,
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def validate_csv_file(self, file_path: str) -> Dict:
        """Validate CSV file with enhanced error handling"""
        try:
            print(f"Reading CSV file: {file_path}")
            df = pd.read_csv(file_path)
            print(f"Found {len(df)} rows and {len(df.columns)} columns")
            print(f"Available columns: {', '.join(df.columns)}")
            
            # Check if required columns exist
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f"CSV missing required columns: {', '.join(missing_columns)}",
                    'available_columns': list(df.columns),
                    'required_columns': self.required_columns
                }
            
            # Validate each row
            print("Starting validation...")
            results = []
            valid_count = 0
            
            for index, row in df.iterrows():
                row_result = self.validate_row(row, index + 2)  # +2 for header and 0-based index
                results.append(row_result)
                if row_result['is_valid']:
                    valid_count += 1
                
                # Progress indicator
                if (index + 1) % 100 == 0:
                    print(f"Processed {index + 1} rows...")
            
            total_rows = len(df)
            invalid_count = total_rows - valid_count
            
            print(f"Validation complete: {valid_count}/{total_rows} rows valid")
            
            return {
                'success': True,
                'total_rows': total_rows,
                'valid_rows': valid_count,
                'invalid_rows': invalid_count,
                'validation_rate': (valid_count / total_rows * 100) if total_rows > 0 else 0,
                'results': results,
                'summary': {
                    'total_errors': sum(len(r['errors']) for r in results),
                    'total_warnings': sum(len(r['warnings']) for r in results)
                }
            }
            
        except FileNotFoundError:
            return {
                'success': False,
                'error': f"File not found: {file_path}"
            }
        except pd.errors.EmptyDataError:
            return {
                'success': False,
                'error': "CSV file is empty"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error processing CSV file: {str(e)}"
            }

    def generate_detailed_report(self, validation_results: Dict, output_file: Optional[str] = None) -> str:
        """Generate comprehensive validation report"""
        if not validation_results.get('success'):
            return f"Validation failed: {validation_results.get('error', 'Unknown error')}"
        
        report_lines = []
        report_lines.append("PACS.008.001.08 XSD Compliance Validation Report")
        report_lines.append("=" * 55)
        report_lines.append(f"Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary statistics
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 20)
        report_lines.append(f"Total rows processed: {validation_results['total_rows']:,}")
        report_lines.append(f"Valid rows: {validation_results['valid_rows']:,}")
        report_lines.append(f"Invalid rows: {validation_results['invalid_rows']:,}")
        report_lines.append(f"Validation rate: {validation_results['validation_rate']:.2f}%")
        report_lines.append(f"Total errors: {validation_results['summary']['total_errors']:,}")
        report_lines.append(f"Total warnings: {validation_results['summary']['total_warnings']:,}")
        report_lines.append("")
        
        # Error analysis
        if validation_results['invalid_rows'] > 0:
            error_counts = {}
            warning_counts = {}
            
            for result in validation_results['results']:
                for error in result['errors']:
                    error_type = error.split(':')[0] if ':' in error else error
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                for warning in result['warnings']:
                    warning_type = warning.split(':')[0] if ':' in warning else warning
                    warning_counts[warning_type] = warning_counts.get(warning_type, 0) + 1
            
            if error_counts:
                report_lines.append("ERROR FREQUENCY ANALYSIS")
                report_lines.append("-" * 25)
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"{error_type}: {count:,} occurrences")
                report_lines.append("")
            
            if warning_counts:
                report_lines.append("WARNING FREQUENCY ANALYSIS")
                report_lines.append("-" * 27)
                for warning_type, count in sorted(warning_counts.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"{warning_type}: {count:,} occurrences")
                report_lines.append("")
        
        # Detailed errors (first 50 to avoid huge reports)
        if validation_results['invalid_rows'] > 0:
            report_lines.append("DETAILED VALIDATION ISSUES (First 50)")
            report_lines.append("-" * 40)
            
            count = 0
            for result in validation_results['results']:
                if not result['is_valid'] and count < 50:
                    report_lines.append(f"Row {result['row_index']}:")
                    for error in result['errors']:
                        report_lines.append(f"  ERROR: {error}")
                    for warning in result['warnings']:
                        report_lines.append(f"  WARNING: {warning}")
                    report_lines.append("")
                    count += 1
            
            if validation_results['invalid_rows'] > 50:
                report_lines.append(f"... and {validation_results['invalid_rows'] - 50} more invalid rows")
                report_lines.append("")
        
        # Recommendations
        report_lines.append("RECOMMENDATIONS")
        report_lines.append("-" * 15)
        
        if validation_results['validation_rate'] == 100:
            report_lines.append("✓ All rows passed validation! Your data is compliant with PACS.008.001.08 XSD.")
        elif validation_results['validation_rate'] >= 95:
            report_lines.append("• Excellent compliance rate. Review and fix the few remaining issues.")
        elif validation_results['validation_rate'] >= 80:
            report_lines.append("• Good compliance rate. Focus on the most frequent error types first.")
        else:
            report_lines.append("• Significant validation issues detected. Systematic review required.")
            report_lines.append("• Consider reviewing data source and validation processes.")
        
        report_lines.append("• Ensure Federal Reserve reference numbers follow exact format requirements.")
        report_lines.append("• Verify all enumerated values match XSD specifications.")
        report_lines.append("• Cross-check business logic rules for FED wire transfers.")
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Detailed report saved to: {output_file}")
        
        return report


def main():
    """Enhanced main function with user input and better error handling"""
    print("PACS.008.001.08 XSD Compliance Validator")
    print("=" * 40)
    print("This validator checks your CSV data against:")
    print("• ISO 20022 PACS.008.001.08 XSD schema requirements")
    print("• Federal Reserve Fedwire format specifications")
    print("• Business logic rules for wire transfers")
    print()
    
    # Get CSV file path from user
    while True:
        csv_file_path = input("Enter the path to your CSV file: ").strip()
        if csv_file_path:
            # Remove quotes if present
            csv_file_path = csv_file_path.strip('"\'')
            break
        print("Please enter a valid file path.")
    
    # Initialize validator
    validator = PACS008XSDValidator()
    
    print("\nStarting validation...")
    print("-" * 25)
    
    # Validate CSV file
    results = validator.validate_csv_file(csv_file_path)
    
    if results['success']:
        # Generate and display report
        report_filename = f"pacs008_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report = validator.generate_detailed_report(results, report_filename)
        
        # Display summary
        print("\nVALIDATION SUMMARY:")
        print(f"Total rows: {results['total_rows']:,}")
        print(f"Valid rows: {results['valid_rows']:,}")
        print(f"Invalid rows: {results['invalid_rows']:,}")
        print(f"Success rate: {results['validation_rate']:.1f}%")
        
        if results['invalid_rows'] > 0:
            print(f"\nFirst few validation errors:")
            count = 0
            for result in results['results']:
                if not result['is_valid'] and count < 3:
                    print(f"  Row {result['row_index']}: {result['errors'][0]}")
                    count += 1
        
        print(f"\nFull report saved to: {report_filename}")
        
        # Ask if user wants to see the full report
        show_full = input("\nShow full report in console? (y/n): ").strip().lower()
        if show_full in ['y', 'yes']:
            print("\n" + "=" * 60)
            print(report)
    else:
        print(f"Validation failed: {results['error']}")
        if 'available_columns' in results:
            print(f"Available columns in CSV: {', '.join(results['available_columns'])}")
            print(f"Required columns: {', '.join(results['required_columns'])}")


if __name__ == "__main__":
    main()
