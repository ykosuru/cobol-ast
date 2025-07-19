import pandas as pd
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FedPacs008Validator:
    def __init__(self):
        # ISO 4217 Currency codes
        self.valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'SEK', 'NOK', 'DKK',
            'PLN', 'CZK', 'HUF', 'BGN', 'HRK', 'RON', 'TRY', 'RUB', 'CNY', 'KRW',
            'SGD', 'HKD', 'NZD', 'ZAR', 'BRL', 'MXN', 'INR', 'THB', 'MYR', 'IDR'
        }
        
        # Field mappings to pacs.008 elements
        self.field_mappings = {
            # Message Header
            'TRAN_ID': {'pacs_element': 'GrpHdr/MsgId', 'max_length': 35, 'required': True, 'type': 'alphanumeric'},
            'TXN_DATE': {'pacs_element': 'GrpHdr/CreDtTm', 'required': True, 'type': 'datetime'},
            'TDN_NUMBER': {'pacs_element': 'CdtTrfTxInf/PmtId/TxId', 'max_length': 35, 'required': False, 'type': 'alphanumeric'},
            'SBK_REF_NUM': {'pacs_element': 'CdtTrfTxInf/PmtId/UETR', 'max_length': 36, 'required': False, 'type': 'uuid'},
            'FRONTIER_REF_NO': {'pacs_element': 'CdtTrfTxInf/PmtId/EndToEndId', 'max_length': 35, 'required': False, 'type': 'alphanumeric'},
            
            # Transaction Information
            'FEXCH_RATE_AMOUNT': {'pacs_element': 'CdtTrfTxInf/IntrBkSttlmAmt', 'required': True, 'type': 'amount'},
            'CURRENCY_CODE': {'pacs_element': 'CdtTrfTxInf/IntrBkSttlmAmt/@Ccy', 'required': True, 'type': 'currency'},
            'PROC_DATE': {'pacs_element': 'CdtTrfTxInf/IntrBkSttlmDt', 'required': False, 'type': 'date'},
            'PAY_DATE': {'pacs_element': 'CdtTrfTxInf/ReqdExctnDt', 'required': False, 'type': 'date'},
            
            # Debtor Information
            'DBT_ID': {'pacs_element': 'CdtTrfTxInf/Dbtr/Id', 'max_length': 35, 'required': False, 'type': 'alphanumeric'},
            'DBT_NAME1': {'pacs_element': 'CdtTrfTxInf/Dbtr/Nm', 'max_length': 70, 'required': True, 'type': 'text'},
            'DBT_NAME_2': {'pacs_element': 'CdtTrfTxInf/Dbtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'DBT_NAME_3': {'pacs_element': 'CdtTrfTxInf/Dbtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'DBT_NAME_4': {'pacs_element': 'CdtTrfTxInf/Dbtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'DBT_ACCTG_ACCOUNT': {'pacs_element': 'CdtTrfTxInf/DbtrAcct/Id', 'max_length': 34, 'required': False, 'type': 'account'},
            'DBT_ACCTG_IDTYPE': {'pacs_element': 'CdtTrfTxInf/DbtrAcct/Id/SchmeNm', 'required': False, 'type': 'code'},
            
            # Creditor Information
            'CDT_ID': {'pacs_element': 'CdtTrfTxInf/Cdtr/Id', 'max_length': 35, 'required': False, 'type': 'alphanumeric'},
            'CDT_NAME1': {'pacs_element': 'CdtTrfTxInf/Cdtr/Nm', 'max_length': 70, 'required': True, 'type': 'text'},
            'CDT_NAME2': {'pacs_element': 'CdtTrfTxInf/Cdtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'CDT_NAME3': {'pacs_element': 'CdtTrfTxInf/Cdtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'CDT_NAME4': {'pacs_element': 'CdtTrfTxInf/Cdtr/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'CDT_ACCTG_ACCOUNT': {'pacs_element': 'CdtTrfTxInf/CdtrAcct/Id', 'max_length': 34, 'required': False, 'type': 'account'},
            'CDT_ACCTG_IDTYPE': {'pacs_element': 'CdtTrfTxInf/CdtrAcct/Id/SchmeNm', 'required': False, 'type': 'code'},
            
            # Bank Information
            'BBK_ID': {'pacs_element': 'CdtTrfTxInf/CdtrAgt/FinInstnId/BICFI', 'max_length': 11, 'required': False, 'type': 'bic'},
            'BBK_NAME1': {'pacs_element': 'CdtTrfTxInf/CdtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'BBK_NAME2': {'pacs_element': 'CdtTrfTxInf/CdtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'BBK_NAME3': {'pacs_element': 'CdtTrfTxInf/CdtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'BBK_NAME4': {'pacs_element': 'CdtTrfTxInf/CdtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            
            'OBK_ID': {'pacs_element': 'CdtTrfTxInf/DbtrAgt/FinInstnId/BICFI', 'max_length': 11, 'required': False, 'type': 'bic'},
            'OBK_NAME1': {'pacs_element': 'CdtTrfTxInf/DbtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'OBK_NAME2': {'pacs_element': 'CdtTrfTxInf/DbtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'OBK_NAME3': {'pacs_element': 'CdtTrfTxInf/DbtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'OBK_NAME4': {'pacs_element': 'CdtTrfTxInf/DbtrAgt/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            
            'IBK_ID': {'pacs_element': 'CdtTrfTxInf/IntrmyAgt1/FinInstnId/BICFI', 'max_length': 11, 'required': False, 'type': 'bic'},
            'IBK_NAME1': {'pacs_element': 'CdtTrfTxInf/IntrmyAgt1/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'IBK_NAME2': {'pacs_element': 'CdtTrfTxInf/IntrmyAgt1/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'IBK_NAME3': {'pacs_element': 'CdtTrfTxInf/IntrmyAgt1/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            'IBK_NAME4': {'pacs_element': 'CdtTrfTxInf/IntrmyAgt1/FinInstnId/Nm', 'max_length': 70, 'required': False, 'type': 'text'},
            
            # Remittance Information
            'TXN_MEMO': {'pacs_element': 'CdtTrfTxInf/RmtInf/Ustrd', 'max_length': 140, 'required': False, 'type': 'text'},
            'ORP_BEN_INF1': {'pacs_element': 'CdtTrfTxInf/RmtInf/Strd/RfrdDocInf/Nb', 'max_length': 35, 'required': False, 'type': 'text'},
            'ORP_BEN_INF2': {'pacs_element': 'CdtTrfTxInf/RmtInf/Strd/RfrdDocInf/RltdDt', 'required': False, 'type': 'date'},
            'ORP_BEN_INF3': {'pacs_element': 'CdtTrfTxInf/RmtInf/Strd/AddtlRmtInf', 'max_length': 140, 'required': False, 'type': 'text'},
            'ORP_BEN_INF4': {'pacs_element': 'CdtTrfTxInf/RmtInf/Strd/AddtlRmtInf', 'max_length': 140, 'required': False, 'type': 'text'},
            
            # Boolean Fields
            'IS_COVER_PAYMENT': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/IsCoverPayment', 'required': False, 'type': 'boolean'},
            'STRAIGHT_THR_U': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/StraightThrough', 'required': False, 'type': 'boolean'},
            
            # Network Specific Fields (Supplementary Data)
            'SOURCE_CD': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SourceCode', 'required': False, 'type': 'code', 'values': ['SWF', 'FED', 'RTN']},
            'INSTR_ADV_TYPE': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/InstructionAdviceType', 'required': False, 'type': 'code', 'values': ['CHP', 'FED']},
            
            # Federal Reserve Fields
            'FED_IMAD': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/FedwireMessage/IMAD', 'max_length': 16, 'required': False, 'type': 'fedwire_id'},
            'FED_OMAD': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/FedwireMessage/OMAD', 'max_length': 16, 'required': False, 'type': 'fedwire_id'},
            'FED_ISN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/FedwireMessage/ISN', 'required': False, 'type': 'numeric'},
            'FED_OSN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/FedwireMessage/OSN', 'required': False, 'type': 'numeric'},
            
            # SWIFT Fields
            'SWF_IN_MIR': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SWIFTMessage/InputMIR', 'max_length': 28, 'required': False, 'type': 'swift_mir'},
            'SWF_OUT_MIR': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SWIFTMessage/OutputMIR', 'max_length': 28, 'required': False, 'type': 'swift_mir'},
            'SWF_ISN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SWIFTMessage/ISN', 'required': False, 'type': 'numeric'},
            'SWF_OSN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SWIFTMessage/OSN', 'required': False, 'type': 'numeric'},
            
            # CHIPS Fields
            'CHP_ISN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/CHIPSMessage/ISN', 'required': False, 'type': 'numeric'},
            'CHP_OSN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/CHIPSMessage/OSN', 'required': False, 'type': 'numeric'},
            'CHP_SSN_1': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/CHIPSMessage/SSN1', 'required': False, 'type': 'numeric'},
            'CHP_SSN_6': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/CHIPSMessage/SSN6', 'required': False, 'type': 'numeric'},
            
            # Operational Fields
            'SEND_DATE': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/SendDate', 'required': False, 'type': 'date'},
            'RCV_DATE': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/ReceiveDate', 'required': False, 'type': 'date'},
            'RCV_TIME': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/ReceiveTime', 'required': False, 'type': 'time'},
            'ENTRY_PERSON': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/EntryPerson', 'max_length': 35, 'required': False, 'type': 'text'},
            'VERIFY_PERSON': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/VerifyPerson', 'max_length': 35, 'required': False, 'type': 'text'},
            'REPAIR_PERSON': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/RepairPerson', 'max_length': 35, 'required': False, 'type': 'text'},
            'EXCEPT_PERSON': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/ExceptPerson', 'max_length': 35, 'required': False, 'type': 'text'},
            'DLVRY_PERSON': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/DeliveryPerson', 'max_length': 35, 'required': False, 'type': 'text'},
            'DLV_MEMO': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/DeliveryMemo', 'max_length': 140, 'required': False, 'type': 'text'},
            
            # Status and Control Fields
            'STS_CD': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/StatusCode', 'required': False, 'type': 'code'},
            'WIRE_TYPE': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/WireType', 'required': False, 'type': 'code'},
            'REPETITIVE_ID': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/RepetitiveId', 'required': False, 'type': 'alphanumeric'},
            'ISO20022_MSGTYPE_IN': {'pacs_element': 'CdtTrfTxInf/SplmtryData/Envlp/MessageType', 'required': False, 'type': 'code'},
        }
        
        # XML reserved characters
        self.xml_reserved = ['&', '<', '>', '"', "'"]
        
        # Validation patterns
        self.patterns = {
            'bic': r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$',
            'fedwire_id': r'^[0-9]{8}[0-9]{8}$',  # YYYYMMDDXXXXXXXX format
            'swift_mir': r'^[0-9]{6}[A-Z]{4}[A-Z0-9]{4}[0-9]{6}[0-9]{4}$',  # SWIFT MIR format
            'uuid': r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
            'iban': r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$'
        }
    
    def is_empty_or_null(self, value):
        """Check if value is null, NaN, empty string, or whitespace only"""
        if pd.isna(value):
            return True
        if value is None:
            return True
        if str(value).strip() == '' or str(value).strip().lower() in ['null', 'nan', 'none']:
            return True
        return False
    
    def validate_text_field(self, value, field_name, mapping):
        """Validate text fields for XML compliance and length"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        value_str = str(value).strip()
        
        # Check XML reserved characters
        for char in self.xml_reserved:
            if char in value_str:
                issues.append(f"{field_name}: Contains XML reserved character '{char}' - needs escaping")
        
        # Check length limits
        if 'max_length' in mapping and len(value_str) > mapping['max_length']:
            issues.append(f"{field_name}: Length {len(value_str)} exceeds pacs.008 limit of {mapping['max_length']}")
        
        # Check for invalid characters (basic ASCII check)
        if not all(ord(c) < 128 for c in value_str):
            issues.append(f"{field_name}: Contains non-ASCII characters that may not be pacs.008 compliant")
        
        return issues
    
    def validate_amount(self, value, field_name):
        """Validate monetary amount according to pacs.008 standards"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        try:
            # Clean the value
            clean_value = str(value).strip()
            
            # Remove currency symbols and formatting
            for symbol in ['$', '€', '£', '¥', '₹', ',', ' ']:
                clean_value = clean_value.replace(symbol, '')
            
            # Handle accounting format negatives
            if clean_value.startswith('(') and clean_value.endswith(')'):
                clean_value = '-' + clean_value[1:-1]
            
            if not clean_value:
                return issues
            
            # Convert to Decimal for precision
            amount = Decimal(clean_value)
            
            # pacs.008 validations
            if amount < 0:
                issues.append(f"{field_name}: Negative amounts not typically allowed in pacs.008")
            
            if amount == 0:
                issues.append(f"{field_name}: Zero amounts should be validated for business logic")
            
            # Check decimal places (max 5 for pacs.008)
            if '.' in clean_value:
                decimal_places = len(clean_value.split('.')[1])
                if decimal_places > 5:
                    issues.append(f"{field_name}: Too many decimal places ({decimal_places}), pacs.008 allows max 5")
            
            # Check total digits (max 18 digits before decimal)
            integer_part = str(int(abs(amount)))
            if len(integer_part) > 18:
                issues.append(f"{field_name}: Too many digits ({len(integer_part)}), pacs.008 allows max 18")
            
        except (ValueError, InvalidOperation):
            issues.append(f"{field_name}: Invalid amount format - cannot convert to decimal")
        
        return issues
    
    def validate_date(self, value, field_name):
        """Validate date format for pacs.008 (ISO 8601)"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        date_str = str(value).strip()
        
        # Common date formats to try
        date_formats = [
            '%Y-%m-%d',              # ISO format (preferred)
            '%Y-%m-%dT%H:%M:%S',     # ISO datetime
            '%Y-%m-%d %H:%M:%S',     # Space separated datetime
            '%m/%d/%Y',              # US format
            '%d/%m/%Y',              # European format
            '%Y/%m/%d',              # Alternative
        ]
        
        parsed = False
        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                parsed = True
                if fmt not in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                    issues.append(f"{field_name}: Date format '{date_str}' should be ISO 8601 (YYYY-MM-DD)")
                break
            except ValueError:
                continue
        
        if not parsed:
            issues.append(f"{field_name}: Invalid date format '{date_str}' - not pacs.008 compliant")
        
        return issues
    
    def validate_currency_code(self, value):
        """Validate ISO 4217 currency code"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        currency = str(value).strip().upper()
        
        if len(currency) != 3:
            issues.append(f"CURRENCY_CODE: '{currency}' must be exactly 3 characters")
        
        if currency not in self.valid_currencies:
            issues.append(f"CURRENCY_CODE: '{currency}' is not a valid ISO 4217 currency code")
        
        if str(value) != currency:
            issues.append(f"CURRENCY_CODE: Should be uppercase ('{currency}' instead of '{value}')")
        
        return issues
    
    def validate_bic_code(self, value, field_name):
        """Validate BIC/SWIFT code format"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        bic = str(value).strip().upper()
        
        if not re.match(self.patterns['bic'], bic):
            issues.append(f"{field_name}: Invalid BIC format '{value}' - should be 8 or 11 characters (BANK CODE + COUNTRY + LOCATION + optional BRANCH)")
        
        if len(bic) not in [8, 11]:
            issues.append(f"{field_name}: BIC length should be 8 or 11 characters, got {len(bic)}")
        
        return issues
    
    def validate_boolean_field(self, value, field_name):
        """Validate boolean fields"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        value_str = str(value).strip().lower()
        valid_values = ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']
        
        if value_str not in valid_values:
            issues.append(f"{field_name}: Invalid boolean value '{value}' - should be true/false or equivalent")
        
        return issues
    
    def validate_code_field(self, value, field_name, mapping):
        """Validate code fields with predefined values"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        value_str = str(value).strip().upper()
        
        if 'values' in mapping:
            if value_str not in mapping['values']:
                issues.append(f"{field_name}: Invalid value '{value}' - allowed values: {mapping['values']}")
        
        return issues
    
    def validate_specialized_field(self, value, field_name, field_type):
        """Validate specialized field types"""
        issues = []
        if self.is_empty_or_null(value):
            return issues
        
        value_str = str(value).strip()
        
        if field_type == 'fedwire_id':
            if not re.match(self.patterns['fedwire_id'], value_str):
                issues.append(f"{field_name}: Invalid Fedwire ID format - should be 16 digits (YYYYMMDDXXXXXXXX)")
        
        elif field_type == 'swift_mir':
            if not re.match(self.patterns['swift_mir'], value_str):
                issues.append(f"{field_name}: Invalid SWIFT MIR format")
        
        elif field_type == 'uuid':
            if not re.match(self.patterns['uuid'], value_str):
                issues.append(f"{field_name}: Invalid UUID format")
        
        elif field_type == 'numeric':
            try:
                int(value_str)
            except ValueError:
                issues.append(f"{field_name}: Should be numeric")
        
        elif field_type == 'account':
            # Basic account number validation
            if len(value_str) > 34:
                issues.append(f"{field_name}: Account number too long (max 34 characters)")
            if not re.match(r'^[A-Za-z0-9]+$', value_str):
                issues.append(f"{field_name}: Account number contains invalid characters")
        
        return issues
    
    def concatenate_name_fields(self, name_fields):
        """Concatenate multiple name fields"""
        names = []
        for name in name_fields:
            if not self.is_empty_or_null(name):
                clean_name = str(name).strip()
                if clean_name:
                    names.append(clean_name)
        return ' '.join(names)
    
    def validate_field(self, value, field_name, mapping):
        """Main field validation dispatcher"""
        issues = []
        
        # Check if required field is missing
        if mapping.get('required', False) and self.is_empty_or_null(value):
            issues.append(f"{field_name}: REQUIRED field is missing - mapped to pacs.008 {mapping['pacs_element']}")
            return issues
        
        # Skip validation if empty and not required
        if self.is_empty_or_null(value):
            return issues
        
        field_type = mapping.get('type', 'text')
        
        # Dispatch to appropriate validator
        if field_type == 'text':
            issues.extend(self.validate_text_field(value, field_name, mapping))
        elif field_type == 'amount':
            issues.extend(self.validate_amount(value, field_name))
        elif field_type == 'currency':
            issues.extend(self.validate_currency_code(value))
        elif field_type in ['date', 'datetime']:
            issues.extend(self.validate_date(value, field_name))
        elif field_type == 'bic':
            issues.extend(self.validate_bic_code(value, field_name))
        elif field_type == 'boolean':
            issues.extend(self.validate_boolean_field(value, field_name))
        elif field_type == 'code':
            issues.extend(self.validate_code_field(value, field_name, mapping))
        elif field_type in ['fedwire_id', 'swift_mir', 'uuid', 'numeric', 'account']:
            issues.extend(self.validate_specialized_field(value, field_name, field_type))
        elif field_type == 'alphanumeric':
            issues.extend(self.validate_text_field(value, field_name, mapping))
        
        return issues
    
    def validate_business_rules(self, row):
        """Validate business rules and cross-field dependencies"""
        issues = []
        
        # Rule 1: At least one debtor identification method required
        debtor_id_fields = ['DBT_ID', 'DBT_ACCTG_ACCOUNT']
        has_debtor_id = any(not self.is_empty_or_null(row.get(field)) for field in debtor_id_fields)
        if not has_debtor_id:
            issues.append("BUSINESS RULE: At least one debtor identification (DBT_ID or DBT_ACCTG_ACCOUNT) required")
        
        # Rule 2: At least one creditor identification method required
        creditor_id_fields = ['CDT_ID', 'CDT_ACCTG_ACCOUNT']
        has_creditor_id = any(not self.is_empty_or_null(row.get(field)) for field in creditor_id_fields)
        if not has_creditor_id:
            issues.append("BUSINESS RULE: At least one creditor identification (CDT_ID or CDT_ACCTG_ACCOUNT) required")
        
        # Rule 3: Combined name fields length check
        debtor_name = self.concatenate_name_fields([
            row.get('DBT_NAME1'), row.get('DBT_NAME_2'), 
            row.get('DBT_NAME_3'), row.get('DBT_NAME_4')
        ])
        if debtor_name and len(debtor_name) > 70:
            issues.append(f"BUSINESS RULE: Combined debtor name too long ({len(debtor_name)} chars, max 70)")
        
        creditor_name = self.concatenate_name_fields([
            row.get('CDT_NAME1'), row.get('CDT_NAME2'), 
            row.get('CDT_NAME3'), row.get('CDT_NAME4')
        ])
        if creditor_name and len(creditor_name) > 70:
            issues.append(f"BUSINESS RULE: Combined creditor name too long ({len(creditor_name)} chars, max 70)")
        
        # Rule 4: Network-specific field consistency
        source_cd = row.get('SOURCE_CD', '').strip().upper()
        instr_adv_type = row.get('INSTR_ADV_TYPE', '').strip().upper()
        
        # If SOURCE_CD is FED, check for FED-specific fields
        if source_cd == 'FED':
            fed_fields = ['FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN']
            has_fed_data = any(not self.is_empty_or_null(row.get(field)) for field in fed_fields)
            if not has_fed_data:
                issues.append("BUSINESS RULE: SOURCE_CD=FED but no Federal Reserve data fields populated")
        
        # If SOURCE_CD is SWF, check for SWIFT-specific fields
        if source_cd == 'SWF':
            swift_fields = ['SWF_IN_MIR', 'SWF_OUT_MIR', 'SWF_ISN', 'SWF_OSN']
            has_swift_data = any(not self.is_empty_or_null(row.get(field)) for field in swift_fields)
            if not has_swift_data:
                issues.append("BUSINESS RULE: SOURCE_CD=SWF but no SWIFT data fields populated")
        
        # If INSTR_ADV_TYPE is CHP, check for CHIPS-specific fields
        if instr_adv_type == 'CHP':
            chips_fields = ['CHP_ISN', 'CHP_OSN', 'CHP_SSN_1', 'CHP_SSN_6']
            has_chips_data = any(not self.is_empty_or_null(row.get(field)) for field in chips_fields)
            if not has_chips_data:
                issues.append("BUSINESS RULE: INSTR_ADV_TYPE=CHP but no CHIPS data fields populated")
        
        # Rule 5: Date consistency checks
        txn_date = row.get('TXN_DATE')
        proc_date = row.get('PROC_DATE')
        pay_date = row.get('PAY_DATE')
        
        try:
            if not self.is_empty_or_null(txn_date) and not self.is_empty_or_null(proc_date):
                txn_dt = datetime.strptime(str(txn_date).strip(), '%Y-%m-%d')
                proc_dt = datetime.strptime(str(proc_date).strip(), '%Y-%m-%d')
                if proc_dt < txn_dt:
                    issues.append("BUSINESS RULE: Processing date cannot be before transaction date")
        except ValueError:
            pass  # Date format issues will be caught by individual field validation
        
        return issues
    
    def validate_row(self, row, row_index):
        """Validate a complete row of data"""
        issues = []
        
        # Validate each mapped field
        for field_name, mapping in self.field_mappings.items():
            if field_name in row:
                field_issues = self.validate_field(row[field_name], field_name, mapping)
                issues.extend(field_issues)
        
        # Validate business rules
        business_issues = self.validate_business_rules(row)
        issues.extend(business_issues)
        
        return issues
    
    def analyze_data_completeness(self, df):
        """Analyze field completeness and mapping coverage"""
        completeness_report = {}
        
        # Group fields by pacs.008 sections
        field_groups = {
            'Message Header': ['TRAN_ID', 'TXN_DATE', 'TDN_NUMBER', 'SBK_REF_NUM', 'FRONTIER_REF_NO'],
            'Transaction Info': ['FEXCH_RATE_AMOUNT', 'CURRENCY_CODE', 'PROC_DATE', 'PAY_DATE'],
            'Debtor Party': ['DBT_ID', 'DBT_NAME1', 'DBT_NAME_2', 'DBT_NAME_3', 'DBT_NAME_4', 'DBT_ACCTG_ACCOUNT'],
            'Creditor Party': ['CDT_ID', 'CDT_NAME1', 'CDT_NAME2', 'CDT_NAME3', 'CDT_NAME4', 'CDT_ACCTG_ACCOUNT'],
            'Agent Banks': ['BBK_ID', 'BBK_NAME1', 'OBK_ID', 'OBK_NAME1', 'IBK_ID', 'IBK_NAME1'],
            'Remittance Info': ['TXN_MEMO', 'ORP_BEN_INF1', 'ORP_BEN_INF2', 'ORP_BEN_INF3', 'ORP_BEN_INF4'],
            'Federal Reserve': ['FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN'],
            'SWIFT Network': ['SWF_IN_MIR', 'SWF_OUT_MIR', 'SWF_ISN', 'SWF_OSN'],
            'CHIPS Network': ['CHP_ISN', 'CHP_OSN', 'CHP_SSN_1', 'CHP_SSN_6'],
            'Control Fields': ['SOURCE_CD', 'INSTR_ADV_TYPE', 'STS_CD', 'WIRE_TYPE', 'IS_COVER_PAYMENT']
        }
        
        total_rows = len(df)
        
        for group_name, fields in field_groups.items():
            group_stats = {}
            
            for field in fields:
                if field in df.columns:
                    non_empty_count = sum(1 for val in df[field] if not self.is_empty_or_null(val))
                    percentage = (non_empty_count / total_rows) * 100
                    
                    # Get pacs.008 mapping info
                    mapping_info = self.field_mappings.get(field, {})
                    pacs_element = mapping_info.get('pacs_element', 'Not mapped')
                    is_required = mapping_info.get('required', False)
                    
                    group_stats[field] = {
                        'populated': non_empty_count,
                        'percentage': percentage,
                        'pacs_element': pacs_element,
                        'required': is_required
                    }
                else:
                    group_stats[field] = {
                        'populated': 0,
                        'percentage': 0.0,
                        'pacs_element': 'Field not found',
                        'required': False
                    }
            
            completeness_report[group_name] = group_stats
        
        # Check for unmapped fields
        mapped_fields = set(self.field_mappings.keys())
        excel_fields = set(df.columns)
        unmapped_fields = excel_fields - mapped_fields
        
        if unmapped_fields:
            completeness_report['Unmapped Fields'] = {
                field: {
                    'populated': sum(1 for val in df[field] if not self.is_empty_or_null(val)),
                    'percentage': (sum(1 for val in df[field] if not self.is_empty_or_null(val)) / total_rows) * 100,
                    'pacs_element': 'NO MAPPING DEFINED',
                    'required': False
                } for field in unmapped_fields
            }
        
        return completeness_report
    
    def generate_detailed_report(self, all_issues, issue_summary, total_rows, completeness_report):
        """Generate comprehensive validation report"""
        print("\n" + "="*100)
        print("FEDERAL RESERVE ISO 20022 PACS.008 COMPLIANCE VALIDATION REPORT")
        print("="*100)
        
        print(f"\nEXECUTIVE SUMMARY:")
        print("-" * 50)
        print(f"Total Rows Processed: {total_rows:,}")
        print(f"Rows with Issues: {len(all_issues):,}")
        print(f"Clean Rows: {total_rows - len(all_issues):,}")
        print(f"Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        print(f"\nFIELD MAPPING & COMPLETENESS ANALYSIS:")
        print("-" * 80)
        for group_name, fields in completeness_report.items():
            print(f"\n{group_name.upper()}:")
            for field_name, stats in fields.items():
                required_indicator = "⚠ REQ" if stats['required'] else "    "
                status = "✓" if stats['percentage'] > 50 else "⚠" if stats['percentage'] > 10 else "✗"
                
                print(f"  {status} {required_indicator} {field_name:<25}: {stats['populated']:>4}/{total_rows} ({stats['percentage']:>5.1f}%)")
                print(f"      └─ pacs.008: {stats['pacs_element']}")
        
        # Critical issues summary
        critical_issues = {}
        format_issues = {}
        business_issues = {}
        
        for issue_type, count in issue_summary.items():
            if 'REQUIRED' in issue_type or 'BUSINESS RULE' in issue_type:
                critical_issues[issue_type] = count
            elif any(keyword in issue_type for keyword in ['format', 'Invalid', 'Length', 'decimal']):
                format_issues[issue_type] = count
            else:
                business_issues[issue_type] = count
        
        if critical_issues:
            print(f"\nCRITICAL ISSUES (Required Fields & Business Rules):")
            print("-" * 60)
            for issue_type, count in sorted(critical_issues.items(), key=lambda x: x[1], reverse=True):
                print(f"❌ {issue_type:<50}: {count:>5} occurrences")
        
        if format_issues:
            print(f"\nFORMAT & VALIDATION ISSUES:")
            print("-" * 40)
            for issue_type, count in sorted(format_issues.items(), key=lambda x: x[1], reverse=True):
                print(f"⚠️  {issue_type:<50}: {count:>5} occurrences")
        
        if business_issues:
            print(f"\nOTHER ISSUES:")
            print("-" * 20)
            for issue_type, count in sorted(business_issues.items(), key=lambda x: x[1], reverse=True):
                print(f"ℹ️  {issue_type:<50}: {count:>5} occurrences")
        
        # Sample problematic rows
        if all_issues:
            print(f"\nSAMPLE PROBLEMATIC ROWS (First 10):")
            print("-" * 80)
            
            for i, issue_data in enumerate(all_issues[:10], 1):
                print(f"\n{i}. Row {issue_data['row']} (TRAN_ID: {issue_data['tran_id']}):")
                
                # Group issues by type
                critical = [issue for issue in issue_data['issues'] if 'REQUIRED' in issue or 'BUSINESS RULE' in issue]
                format_errs = [issue for issue in issue_data['issues'] if 'Invalid' in issue or 'format' in issue]
                other = [issue for issue in issue_data['issues'] if issue not in critical and issue not in format_errs]
                
                for issue in critical:
                    print(f"    ❌ {issue}")
                for issue in format_errs:
                    print(f"    ⚠️  {issue}")
                for issue in other:
                    print(f"    ℹ️  {issue}")
        
        print(f"\nPACS.008 COMPLIANCE RECOMMENDATIONS:")
        print("-" * 60)
        
        recommendations = [
            "CRITICAL ACTIONS:",
            "1. ❌ Populate all REQUIRED fields (TRAN_ID, TXN_DATE, FEXCH_RATE_AMOUNT, CURRENCY_CODE)",
            "2. ❌ Ensure at least one debtor and creditor identification method",
            "3. ❌ Verify network-specific field consistency (FED/SWF/CHP data)",
            "",
            "FORMAT FIXES:",
            "4. ⚠️  Convert dates to ISO 8601 format (YYYY-MM-DD)",
            "5. ⚠️  Validate BIC codes are 8 or 11 characters with proper format",
            "6. ⚠️  Ensure currency codes are 3-letter ISO 4217 uppercase",
            "7. ⚠️  Escape XML reserved characters (&, <, >, \", ') in text fields",
            "8. ⚠️  Check field length limits per pacs.008 specifications",
            "",
            "BUSINESS LOGIC:",
            "9. ℹ️  Validate cross-field dependencies and date consistency",
            "10. ℹ️ Consider data enrichment for low-populated critical fields",
            "11. ℹ️ Review unmapped fields for potential pacs.008 relevance",
            "",
            "NETWORK ROUTING:",
            "12. 🌐 Ensure SOURCE_CD/INSTR_ADV_TYPE match populated network fields",
            "13. 🌐 Validate Fedwire IDs, SWIFT MIRs, and CHIPS sequence numbers"
        ]
        
        for rec in recommendations:
            print(f"  {rec}")
        
        # Field mapping reference
        print(f"\nFIELD MAPPING REFERENCE (Key Fields):")
        print("-" * 50)
        key_mappings = [
            ('TRAN_ID', 'GrpHdr/MsgId'),
            ('FEXCH_RATE_AMOUNT', 'CdtTrfTxInf/IntrBkSttlmAmt'),
            ('DBT_NAME1', 'CdtTrfTxInf/Dbtr/Nm'),
            ('CDT_NAME1', 'CdtTrfTxInf/Cdtr/Nm'),
            ('BBK_ID', 'CdtTrfTxInf/CdtrAgt/FinInstnId/BICFI'),
            ('FED_IMAD', 'CdtTrfTxInf/SplmtryData/Envlp/FedwireMessage/IMAD')
        ]
        
        for field, pacs_path in key_mappings:
            print(f"  {field:<20} → {pacs_path}")
    
    def process_excel_file(self, file_path):
        """Main processing function"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Analyze completeness
            completeness_report = self.analyze_data_completeness(df)
            
            # Validate each row
            all_issues = []
            issue_summary = {}
            
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
                        issue_type = issue.split(':')[0] if ':' in issue else issue
                        issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # Generate report
            self.generate_detailed_report(all_issues, issue_summary, len(df), completeness_report)
            
            return all_issues
            
        except Exception as e:
            logging.error(f"Error processing Excel file: {str(e)}")
            return None

# Usage
def main():
    validator = FedPacs008Validator()
    
    # Update with your Excel file path
    excel_file_path = "wire_transfer_data.xlsx"
    
    print("Starting Federal Reserve ISO 20022 pacs.008 compliance validation...")
    print("Analyzing field mappings and applying Fed-specific business rules...")
    
    issues = validator.process_excel_file(excel_file_path)
    
    if issues is not None:
        print(f"\n✅ Validation completed successfully!")
        print(f"📊 Found {len(issues)} rows with compliance issues")
        print(f"📋 Review the detailed report above for specific recommendations")
    else:
        print("❌ Validation failed. Please check the file path and format.")

if __name__ == "__main__":
    main()
