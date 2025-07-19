import pandas as pd
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CSVFedPacs008Validator:
    def __init__(self):
        # ISO 4217 Currency codes
        self.valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'SEK', 'NOK', 'DKK',
            'PLN', 'CZK', 'HUF', 'BGN', 'HRK', 'RON', 'TRY', 'RUB', 'CNY', 'KRW',
            'SGD', 'HKD', 'NZD', 'ZAR', 'BRL', 'MXN', 'INR', 'THB', 'MYR', 'IDR'
        }
        
        # Expected CSV column order (based on your original field list)
        self.expected_columns = [
            'TRAN_ID', 'TXN_DATE', 'TDN_NUMBER', 'SBK_REF_NUM', 'PROC_DATE', 'PAY_DATE', 
            'TXN_MEMO', 'SEND_DATE', 'REPETITIVE_ID', 'SOURCE_CD', 'INSTR_ADV_TYPE', 'STS_CD', 
            'CAN_MOUNT_TYPE_CD', 'SUBTYPE_IN_TYPE_CD', 'IN_SUBTYPE', 'ISO20022_MSGTYPE_IN', 
            'IS_COVER_PAYMENT', 'FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN', 'SWF_ISN', 
            'SWF_OSN', 'CHP_ISN', 'CHP_OSN', 'CHP_SSN_1', 'CHP_SSN_6', 'SWF_IN_MIR', 
            'SWF_OUT_MIR', 'ENTRY_PERSON', 'VERIFY_PERSON', 'REPAIR_PERSON', 'EXCEPT_PERSON', 
            'WIRE_TYPE', 'STRAIGHT_THR_U', 'NETWORK_SND_IDTYPE', 'NETWORK_SND_ACC', 'RCV_DATE', 
            'RCV_TIME', 'DLV_MEMO', 'DLVRY_PERSON', 'FEXCH_RATE_AMOUNT', 'CURRENCY_CODE', 
            'FRONTIER_REF_NO', 'IDTYPE', 'CDT_ID', 'CDT_NAME1', 'CDT_NAME2', 'CDT_NAME3', 
            'CDT_NAME4', 'CDT_ACCTG_IDTYPE', 'CDT_ACCTG_SLASH', 'CDT_ACCTG_ACCOUNT', 
            'BBK_IDTYPE', 'BBK_ID', 'BBK_NAME1', 'BBK_NAME2', 'BBK_NAME3', 'BBK_NAME4', 
            'IBK_IDTYPE', 'IBK_ID', 'IBK_NAME1', 'IBK_NAME2', 'IBK_NAME3', 'IBK_NAME4', 
            'ORP_BEN_INF1', 'ORP_BEN_INF2', 'ORP_BEN_INF3', 'ORP_BEN_INF4', 'DBT_IDTYPE', 
            'DBT_ID', 'DBT_NAME1', 'DBT_NAME_2', 'DBT_NAME_3', 'DBT_NAME_4', 'DBT_ACCTG_IDTYPE', 
            'DBT_ACCTG_SLASH', 'DBT_ACCTG_ACCOUNT', 'SBK_IDTYPE', 'SBK_ID', 'SBK_NAME', 
            'SBK_NAME2', 'SBK_NAME3', 'SBK_NAME4', 'OBK_IDTYPE', 'OBK_ID', 'OBK_NAME1', 
            'OBK_NAME2', 'OBK_NAME3', 'OBK_NAME4', 'OBK_REF_NUM', 'ORP_IDTYPE', 'ORP_ID', 
            'ORP_NAME1', 'ORP_NAME2', 'ORP_NAME3', 'ORP_NAME4', 'ORP_REF_NUM', 'FTR_EXP_STATE', 
            'FTR_EXP_SUBSTATE'
        ]
        
        # Field mappings to pacs.008 elements (from your document)
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
            
            # Network Specific Fields
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
            'fedwire_id': r'^[0-9]{8}[0-9]{8}$',
            'swift_mir': r'^[0-9]{6}[A-Z]{4}[A-Z0-9]{4}[0-9]{6}[0-9]{4}$',
            'uuid': r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
        }
    
    def preprocess_csv_file(self, file_path):
        """Preprocess Mac CSV file with ^M line endings"""
        print(f"🔄 Preprocessing CSV file: {file_path}")
        
        try:
            # Read the raw file content
            with open(file_path, 'rb') as f:
                raw_content = f.read()
            
            # Decode and handle different encodings
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = raw_content.decode('latin-1')
                except UnicodeDecodeError:
                    content = raw_content.decode('cp1252')
            
            print(f"📄 File encoding detected and decoded")
            
            # Handle Mac line endings (^M = \r)
            content = content.replace('\r\n', '\n')  # Windows to Unix
            content = content.replace('\r', '\n')    # Mac to Unix
            
            # Split into lines
            lines = content.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            print(f"📊 Found {len(lines)} non-empty lines")
            
            if len(lines) < 2:
                raise ValueError("CSV file must have at least header and one data row")
            
            # Parse header
            header_line = lines[0]
            headers = [h.strip().strip('"') for h in header_line.split(',')]
            
            print(f"📋 CSV Headers found: {len(headers)} columns")
            print(f"   First 10 headers: {headers[:10]}")
            
            # Parse data rows
            data_rows = []
            for i, line in enumerate(lines[1:], 1):
                if line.strip():
                    # Simple CSV parsing (handles basic cases)
                    values = [v.strip().strip('"') for v in line.split(',')]
                    
                    # Pad with empty values if row has fewer columns
                    while len(values) < len(headers):
                        values.append('')
                    
                    # Truncate if row has more columns
                    values = values[:len(headers)]
                    
                    data_rows.append(values)
            
            print(f"✅ Parsed {len(data_rows)} data rows")
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Clean up common issues
            df = df.replace(['', 'NULL', 'null', 'N/A', 'n/a'], pd.NA)
            
            return df
            
        except Exception as e:
            print(f"❌ Error preprocessing CSV: {str(e)}")
            return None
    
    def is_empty_or_null(self, value):
        """Check if value is null, NaN, empty string, or whitespace only"""
        if pd.isna(value):
            return True
        if value is None:
            return True
        if str(value).strip() == '' or str(value).strip().lower() in ['null', 'nan', 'none', 'n/a']:
            return True
        return False
    
    def validate_pacs008_field(self, value, field_name, mapping):
        """Validate field against pacs.008 XSD rules"""
        issues = []
        
        # Check if required field is missing
        if mapping.get('required', False) and self.is_empty_or_null(value):
            issues.append(f"❌ REQUIRED field '{field_name}' is missing (pacs.008: {mapping['pacs_element']})")
            return issues
        
        # Skip validation if empty and not required
        if self.is_empty_or_null(value):
            return issues
        
        field_type = mapping.get('type', 'text')
        value_str = str(value).strip()
        
        # Universal validations first
        # 1. Length validation
        if 'max_length' in mapping and len(value_str) > mapping['max_length']:
            issues.append(f"⚠️ {field_name}: Length {len(value_str)} exceeds pacs.008 limit of {mapping['max_length']}")
        
        # 2. XML reserved characters
        for char in self.xml_reserved:
            if char in value_str:
                issues.append(f"⚠️ {field_name}: Contains XML reserved character '{char}' - needs escaping")
        
        # 3. ASCII compliance
        if not all(ord(c) < 128 for c in value_str):
            issues.append(f"⚠️ {field_name}: Contains non-ASCII characters - may not be pacs.008 compliant")
        
        # Type-specific validations
        if field_type == 'amount':
            issues.extend(self.validate_amount(value, field_name))
        elif field_type == 'currency':
            issues.extend(self.validate_currency(value, field_name))
        elif field_type in ['date', 'datetime']:
            issues.extend(self.validate_date(value, field_name, field_type))
        elif field_type == 'bic':
            issues.extend(self.validate_bic(value, field_name))
        elif field_type == 'boolean':
            issues.extend(self.validate_boolean(value, field_name))
        elif field_type == 'code':
            issues.extend(self.validate_code(value, field_name, mapping))
        elif field_type == 'fedwire_id':
            issues.extend(self.validate_fedwire_id(value, field_name))
        elif field_type == 'swift_mir':
            issues.extend(self.validate_swift_mir(value, field_name))
        elif field_type == 'uuid':
            issues.extend(self.validate_uuid(value, field_name))
        elif field_type == 'numeric':
            issues.extend(self.validate_numeric(value, field_name))
        elif field_type == 'account':
            issues.extend(self.validate_account(value, field_name))
        
        return issues
    
    def validate_amount(self, value, field_name):
        """Validate amount field"""
        issues = []
        try:
            clean_value = str(value).replace(',', '').replace('$', '').replace('€', '').strip()
            if clean_value.startswith('(') and clean_value.endswith(')'):
                clean_value = '-' + clean_value[1:-1]
            
            amount = Decimal(clean_value)
            
            if amount < 0:
                issues.append(f"⚠️ {field_name}: Negative amounts not typically allowed in pacs.008")
            if amount == 0:
                issues.append(f"ℹ️ {field_name}: Zero amount - verify business logic")
            
            # Check decimal places (max 5)
            if '.' in clean_value and len(clean_value.split('.')[1]) > 5:
                issues.append(f"⚠️ {field_name}: Too many decimal places (max 5 for pacs.008)")
            
            # Check total digits (max 18 before decimal)
            integer_part = str(int(abs(amount)))
            if len(integer_part) > 18:
                issues.append(f"⚠️ {field_name}: Too many digits (max 18 for pacs.008)")
                
        except (ValueError, InvalidOperation):
            issues.append(f"❌ {field_name}: Invalid amount format")
        
        return issues
    
    def validate_currency(self, value, field_name):
        """Validate ISO 4217 currency code"""
        issues = []
        currency = str(value).strip().upper()
        
        if len(currency) != 3:
            issues.append(f"❌ {field_name}: Currency code must be 3 characters")
        
        if currency not in self.valid_currencies:
            issues.append(f"❌ {field_name}: '{currency}' not a valid ISO 4217 currency")
        
        if str(value) != currency:
            issues.append(f"⚠️ {field_name}: Should be uppercase")
        
        return issues
    
    def validate_date(self, value, field_name, field_type):
        """Validate date format for pacs.008 (ISO 8601)"""
        issues = []
        date_str = str(value).strip()
        
        formats = ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
        
        parsed = False
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                parsed = True
                if fmt not in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                    issues.append(f"⚠️ {field_name}: Should use ISO 8601 format (YYYY-MM-DD)")
                break
            except ValueError:
                continue
        
        if not parsed:
            issues.append(f"❌ {field_name}: Invalid date format")
        
        return issues
    
    def validate_bic(self, value, field_name):
        """Validate BIC code"""
        issues = []
        bic = str(value).strip().upper()
        
        if not re.match(self.patterns['bic'], bic):
            issues.append(f"❌ {field_name}: Invalid BIC format")
        
        if len(bic) not in [8, 11]:
            issues.append(f"❌ {field_name}: BIC must be 8 or 11 characters")
        
        return issues
    
    def validate_boolean(self, value, field_name):
        """Validate boolean field"""
        issues = []
        value_str = str(value).strip().lower()
        valid_values = ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']
        
        if value_str not in valid_values:
            issues.append(f"❌ {field_name}: Invalid boolean value")
        
        return issues
    
    def validate_code(self, value, field_name, mapping):
        """Validate code field with predefined values"""
        issues = []
        if 'values' in mapping:
            value_str = str(value).strip().upper()
            if value_str not in mapping['values']:
                issues.append(f"❌ {field_name}: Invalid value '{value}' - allowed: {mapping['values']}")
        
        return issues
    
    def validate_fedwire_id(self, value, field_name):
        """Validate Fedwire ID format"""
        issues = []
        if not re.match(self.patterns['fedwire_id'], str(value).strip()):
            issues.append(f"❌ {field_name}: Invalid Fedwire ID format (should be 16 digits)")
        
        return issues
    
    def validate_swift_mir(self, value, field_name):
        """Validate SWIFT MIR format"""
        issues = []
        if not re.match(self.patterns['swift_mir'], str(value).strip()):
            issues.append(f"❌ {field_name}: Invalid SWIFT MIR format")
        
        return issues
    
    def validate_uuid(self, value, field_name):
        """Validate UUID format"""
        issues = []
        if not re.match(self.patterns['uuid'], str(value).strip()):
            issues.append(f"❌ {field_name}: Invalid UUID format")
        
        return issues
    
    def validate_numeric(self, value, field_name):
        """Validate numeric field"""
        issues = []
        try:
            int(str(value).strip())
        except ValueError:
            issues.append(f"❌ {field_name}: Should be numeric")
        
        return issues
    
    def validate_account(self, value, field_name):
        """Validate account number"""
        issues = []
        value_str = str(value).strip()
        
        if len(value_str) > 34:
            issues.append(f"⚠️ {field_name}: Account number too long (max 34 chars)")
        
        if not re.match(r'^[A-Za-z0-9]+, value_str):
            issues.append(f"⚠️ {field_name}: Account contains invalid characters")
        
        return issues
    
    def validate_csv_row(self, row, row_index, headers):
        """Validate a complete CSV row against pacs.008"""
        issues = []
        tran_id = row[0] if len(row) > 0 else 'N/A'  # First column is TRAN_ID
        
        print(f"🔍 Row {row_index:4d}: TRAN_ID = '{tran_id}'")
        
        # Validate each field
        for col_index, (header, value) in enumerate(zip(headers, row)):
            if header in self.field_mappings:
                mapping = self.field_mappings[header]
                field_issues = self.validate_pacs008_field(value, header, mapping)
                
                if field_issues:
                    print(f"    📋 Column {col_index+1:2d} ({header}): {len(field_issues)} issues")
                    for issue in field_issues:
                        print(f"       {issue}")
                    issues.extend(field_issues)
                else:
                    print(f"    ✅ Column {col_index+1:2d} ({header}): Valid")
            else:
                if not self.is_empty_or_null(value):
                    print(f"    ⚠️ Column {col_index+1:2d} ({header}): No pacs.008 mapping defined")
                    issues.append(f"ℹ️ {header}: No pacs.008 mapping defined")
                else:
                    print(f"    📝 Column {col_index+1:2d} ({header}): Empty (no mapping)")
        
        # Business rule validations
        business_issues = self.validate_business_rules(row, headers)
        if business_issues:
            print(f"    🚨 Business Rules: {len(business_issues)} violations")
            for issue in business_issues:
                print(f"       {issue}")
            issues.extend(business_issues)
        
        if not issues:
            print(f"    ✅ Row {row_index} is fully compliant!")
        else:
            print(f"    ❌ Row {row_index} has {len(issues)} total issues")
        
        print("-" * 80)
        
        return issues, tran_id
    
    def validate_business_rules(self, row, headers):
        """Validate business rules across fields"""
        issues = []
        
        # Create a dictionary for easier field access
        row_dict = {header: (row[i] if i < len(row) else '') for i, header in enumerate(headers)}
        
        # Rule 1: At least one debtor identification
        debtor_id_fields = ['DBT_ID', 'DBT_ACCTG_ACCOUNT']
        has_debtor_id = any(not self.is_empty_or_null(row_dict.get(field, '')) for field in debtor_id_fields)
        if not has_debtor_id:
            issues.append("❌ BUSINESS RULE: Missing debtor identification (DBT_ID or DBT_ACCTG_ACCOUNT)")
        
        # Rule 2: At least one creditor identification
        creditor_id_fields = ['CDT_ID', 'CDT_ACCTG_ACCOUNT']
        has_creditor_id = any(not self.is_empty_or_null(row_dict.get(field, '')) for field in creditor_id_fields)
        if not has_creditor_id:
            issues.append("❌ BUSINESS RULE: Missing creditor identification (CDT_ID or CDT_ACCTG_ACCOUNT)")
        
        # Rule 3: Network consistency
        source_cd = row_dict.get('SOURCE_CD', '').strip().upper()
        instr_adv_type = row_dict.get('INSTR_ADV_TYPE', '').strip().upper()
        
        if source_cd == 'FED':
            fed_fields = ['FED_IMAD', 'FED_OMAD', 'FED_ISN', 'FED_OSN']
            has_fed_data = any(not self.is_empty_or_null(row_dict.get(field, '')) for field in fed_fields)
            if not has_fed_data:
                issues.append("⚠️ BUSINESS RULE: SOURCE_CD=FED but no Fed data populated")
        
        if source_cd == 'SWF':
            swift_fields = ['SWF_IN_MIR', 'SWF_OUT_MIR', 'SWF_ISN', 'SWF_OSN']
            has_swift_data = any(not self.is_empty_or_null(row_dict.get(field, '')) for field in swift_fields)
            if not has_swift_data:
                issues.append("⚠️ BUSINESS RULE: SOURCE_CD=SWF but no SWIFT data populated")
        
        if instr_adv_type == 'CHP':
            chips_fields = ['CHP_ISN', 'CHP_OSN', 'CHP_SSN_1', 'CHP_SSN_6']
            has_chips_data = any(not self.is_empty_or_null(row_dict.get(field, '')) for field in chips_fields)
            if not has_chips_data:
                issues.append("⚠️ BUSINESS RULE: INSTR_ADV_TYPE=CHP but no CHIPS data populated")
        
        return issues
    
    def process_csv_file(self, file_path):
        """Main processing function for CSV file"""
        print("🚀 Starting CSV Fed ISO 20022 pacs.008 Validation")
        print("="*80)
        
        # Step 1: Preprocess CSV
        df = self.preprocess_csv_file(file_path)
        if df is None:
            return None
        
        print(f"\n📊 DataFrame created with {len(df)} rows and {len(df.columns)} columns")
        print(f"📋 Columns: {list(df.columns)[:10]}{'...' if len(df.columns) > 10 else ''}")
        
        # Step 2: Check column mapping coverage
        mapped_columns = set(self.field_mappings.keys())
        csv_columns = set(df.columns)
        
        mapped_in_csv = mapped_columns.intersection(csv_columns)
        unmapped_in_csv = csv_columns - mapped_columns
        
        print(f"\n🗺️ COLUMN MAPPING ANALYSIS:")
        print(f"   Mapped columns in CSV: {len(mapped_in_csv)}")
        print(f"   Unmapped columns in CSV: {len(unmapped_in_csv)}")
        if unmapped_in_csv:
            print(f"   Unmapped: {list(unmapped_in_csv)[:5]}{'...' if len(unmapped_in_csv) > 5 else ''}")
        
        # Step 3: Process each row
        print(f"\n🔍 VALIDATING {len(df)} ROWS AGAINST PACS.008 XSD")
        print("="*80)
        
        all_issues = []
        issue_summary = {}
        
        for index, row in df.iterrows():
            row_values = row.tolist()
            headers = df.columns.tolist()
            
            row_issues, tran_id = self.validate_csv_row(row_values, index + 1, headers)
            
            if row_issues:
                all_issues.append({
                    'row': index + 1,
                    'tran_id': tran_id,
                    'issues': row_issues
                })
                
                # Count issue types
                for issue in row_issues:
                    issue_type = issue.split(':')[0].strip('❌⚠️ℹ️🚨 ')
                    issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
        
        # Step 4: Generate summary report
        self.generate_summary_report(all_issues, issue_summary, len(df), mapped_in_csv, unmapped_in_csv)
        
        return all_issues
    
    def generate_summary_report(self, all_issues, issue_summary, total_rows, mapped_columns, unmapped_columns):
        """Generate comprehensive summary report"""
        print("\n" + "="*80)
        print("📊 FINAL VALIDATION SUMMARY REPORT")
        print("="*80)
        
        print(f"\n📈 PROCESSING STATISTICS:")
        print(f"   Total Rows Processed: {total_rows:,}")
        print(f"   Rows with Issues: {len(all_issues):,}")
        print(f"   Clean Rows: {total_rows - len(all_issues):,}")
        print(f"   Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        print(f"\n🗺️ FIELD MAPPING COVERAGE:")
        print(f"   Mapped to pacs.008: {len(mapped_columns)} fields")
        print(f"   Unmapped fields: {len(unmapped_columns)} fields")
        print(f"   Mapping Coverage: {(len(mapped_columns) / (len(mapped_columns) + len(unmapped_columns)) * 100):.1f}%")
        
        if issue_summary:
            print(f"\n🚨 ISSUE BREAKDOWN:")
            print("-" * 50)
            
            critical_issues = {k: v for k, v in issue_summary.items() if 'REQUIRED' in k or 'BUSINESS RULE' in k}
            format_issues = {k: v for k, v in issue_summary.items() if k not in critical_issues}
            
            if critical_issues:
                print("   CRITICAL ISSUES:")
                for issue_type, count in sorted(critical_issues.items(), key=lambda x: x[1], reverse=True):
                    print(f"   ❌ {issue_type:<40}: {count:>5} occurrences")
            
            if format_issues:
                print("   FORMAT/VALIDATION ISSUES:")
                for issue_type, count in sorted(format_issues.items(), key=lambda x: x[1], reverse=True):
                    print(f"   ⚠️ {issue_type:<40}: {count:>5} occurrences")
        
        if all_issues:
            print(f"\n📋 SAMPLE PROBLEMATIC TRAN_IDs (First 10):")
            print("-" * 50)
            for i, issue_data in enumerate(all_issues[:10], 1):
                severity = "🔥" if len(issue_data['issues']) > 5 else "⚠️" if len(issue_data['issues']) > 2 else "ℹ️"
                print(f"   {i:2d}. {severity} Row {issue_data['row']:4d} | TRAN_ID: '{issue_data['tran_id']}' | {len(issue_data['issues'])} issues")
        
        print(f"\n🎯 NEXT STEPS:")
        print("   1. ❌ Fix all REQUIRED field violations first")
        print("   2. 🚨 Address BUSINESS RULE violations")
        print("   3. ⚠️ Clean up format and validation issues")
        print("   4. 🗺️ Consider mapping unmapped fields if relevant to pacs.008")
        print("   5. ✅ Re-run validation after fixes")
        
        print("="*80)

# Usage function
def main():
    validator = CSVFedPacs008Validator()
    
    # Update with your CSV file path
    csv_file_path = "wire_transfer_data.csv"  # Change this to your file path
    
    print("🚀 CSV Federal Reserve ISO 20022 pacs.008 Validator")
    print("📄 Designed for Mac CSV files with ^M line endings")
    print("🗺️ Using comprehensive field mapping to pacs.008 XSD")
    
    issues = validator.process_csv_file(csv_file_path)
    
    if issues is not None:
        print(f"\n✅ Validation completed successfully!")
        print(f"📊 Found {len(issues)} rows with pacs.008 compliance issues")
        print(f"🔍 Each TRAN_ID and its issues were printed above")
    else:
        print("❌ Validation failed. Please check the file path and format.")

if __name__ == "__main__":
    main()
