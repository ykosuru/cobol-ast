import pandas as pd
import requests
from lxml import etree
import xmlschema
from datetime import datetime
import logging
import os
import sys
from decimal import Decimal
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrueXSDPacs008Validator:
    def __init__(self, xsd_file_path=None):
        # Use provided XSD file path or default
        self.xsd_file = xsd_file_path or "pacs.008.001.08.xsd"
        self.schema = None
        
        # CSV column order from your specification
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
        
        # Initialize the XSD schema
        self.load_xsd_schema()
    
    def load_xsd_schema(self):
        """Load the local pacs.008 XSD schema"""
        print(f"📥 Loading local pacs.008.001.08 XSD schema from: {self.xsd_file}")
        
        try:
            # Check if XSD file exists
            if not os.path.exists(self.xsd_file):
                print(f"❌ XSD file not found: {self.xsd_file}")
                print(f"💡 Please ensure you have downloaded the XSD file to: {os.path.abspath(self.xsd_file)}")
                print(f"🌐 Download from: https://github.com/phoughton/pyiso20022/raw/main/xsd/payments_clearing_and_settlement/pacs.008/pacs.008.001.08.xsd")
                self.schema = None
                return
            
            print(f"📄 Found XSD file: {os.path.abspath(self.xsd_file)}")
            print(f"📊 File size: {os.path.getsize(self.xsd_file)} bytes")
            
            # Load schema using xmlschema
            self.schema = xmlschema.XMLSchema(self.xsd_file)
            print(f"✅ XSD schema loaded successfully!")
            print(f"   Schema target namespace: {self.schema.target_namespace}")
            print(f"   Schema elements: {len(self.schema.elements)} root elements")
            print(f"   Schema types: {len(self.schema.types)} defined types")
            
        except Exception as e:
            print(f"❌ Error loading XSD schema: {str(e)}")
            print(f"💡 Make sure the XSD file is valid and not corrupted")
            self.schema = None
    
    def preprocess_csv_file(self, file_path):
        """Preprocess Mac CSV file with ^M line endings"""
        print(f"🔄 Preprocessing CSV file: {file_path}")
        
        try:
            # Read the raw file content
            with open(file_path, 'rb') as f:
                raw_content = f.read()
            
            # Handle encoding
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = raw_content.decode('latin-1')
                except UnicodeDecodeError:
                    content = raw_content.decode('cp1252')
            
            # Handle Mac line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            print(f"📊 Found {len(lines)} non-empty lines")
            
            if len(lines) < 2:
                raise ValueError("CSV file must have at least header and one data row")
            
            # Parse CSV
            headers = [h.strip().strip('"') for h in lines[0].split(',')]
            data_rows = []
            
            for line in lines[1:]:
                values = [v.strip().strip('"') for v in line.split(',')]
                while len(values) < len(headers):
                    values.append('')
                values = values[:len(headers)]
                data_rows.append(values)
            
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.replace(['', 'NULL', 'null', 'N/A', 'n/a'], pd.NA)
            
            print(f"✅ Parsed {len(data_rows)} data rows with {len(headers)} columns")
            return df
            
        except Exception as e:
            print(f"❌ Error preprocessing CSV: {str(e)}")
            return None
    
    def is_empty_or_null(self, value):
        """Check if value is empty or null"""
        if pd.isna(value):
            return True
        if value is None:
            return True
        if str(value).strip() == '' or str(value).strip().lower() in ['null', 'nan', 'none', 'n/a']:
            return True
        return False
    
    def clean_value(self, value):
        """Clean value for XML generation"""
        if self.is_empty_or_null(value):
            return None
        
        value_str = str(value).strip()
        
        # XML escape special characters
        value_str = value_str.replace('&', '&amp;')
        value_str = value_str.replace('<', '&lt;')
        value_str = value_str.replace('>', '&gt;')
        value_str = value_str.replace('"', '&quot;')
        value_str = value_str.replace("'", '&apos;')
        
        return value_str
    
    def concatenate_name_fields(self, name1, name2, name3, name4):
        """Concatenate name fields with proper spacing"""
        names = []
        for name in [name1, name2, name3, name4]:
            clean_name = self.clean_value(name)
            if clean_name:
                names.append(clean_name)
        return ' '.join(names) if names else None
    
    def format_datetime(self, date_value):
        """Format date/datetime for ISO 8601"""
        if self.is_empty_or_null(date_value):
            return None
        
        date_str = str(date_value).strip()
        
        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError:
                continue
        
        return date_str  # Return as-is if can't parse
    
    def format_date(self, date_value):
        """Format date for ISO 8601 date only"""
        if self.is_empty_or_null(date_value):
            return None
        
        date_str = str(date_value).strip()
        
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str
    
    def format_amount(self, amount_value):
        """Format amount for pacs.008"""
        if self.is_empty_or_null(amount_value):
            return None
        
        try:
            # Clean amount value - remove currency symbols and formatting
            clean_value = str(amount_value).replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('¥', '').strip()
            
            # Handle accounting format negatives
            if clean_value.startswith('(') and clean_value.endswith(')'):
                clean_value = '-' + clean_value[1:-1]
            
            amount = Decimal(clean_value)
            
            # Format to max 5 decimal places
            formatted = f"{amount:.5f}".rstrip('0').rstrip('.')
            return formatted
            
        except Exception:
            return str(amount_value)
    
    def determine_clearing_system(self, row_dict):
        """Intelligently determine clearing system code based on other fields"""
        source_cd = str(row_dict.get('SOURCE_CD', '')).strip().upper()
        instr_adv_type = str(row_dict.get('INSTR_ADV_TYPE', '')).strip().upper()
        wire_type = str(row_dict.get('WIRE_TYPE', '')).strip().upper()
        
        # Log the decision process
        print(f"    🔍 Determining CLRG from: SOURCE_CD={source_cd}, INSTR_ADV_TYPE={instr_adv_type}, WIRE_TYPE={wire_type}")
        
        # Decision tree for clearing system
        clearing_system = None
        decision_reason = ""
        
        # Priority 1: INSTR_ADV_TYPE (most specific for settlement routing)
        if instr_adv_type == 'CHP':
            clearing_system = 'CHI'  # CHIPS
            decision_reason = "INSTR_ADV_TYPE=CHP indicates CHIPS processing"
        elif instr_adv_type == 'FED':
            clearing_system = 'FDW'  # Fedwire
            decision_reason = "INSTR_ADV_TYPE=FED indicates Fedwire processing"
        
        # Priority 2: WIRE_TYPE (if INSTR_ADV_TYPE not conclusive)
        elif wire_type in ['CHO', 'CHP', 'CHIPS']:
            clearing_system = 'CHI'  # CHIPS
            decision_reason = f"WIRE_TYPE={wire_type} indicates CHIPS processing"
        elif wire_type in ['FED', 'FEDWIRE', 'FDW']:
            clearing_system = 'FDW'  # Fedwire
            decision_reason = f"WIRE_TYPE={wire_type} indicates Fedwire processing"
        elif wire_type in ['ACH', 'NACHA']:
            clearing_system = 'ACH'  # ACH
            decision_reason = f"WIRE_TYPE={wire_type} indicates ACH processing"
        elif wire_type in ['RTP', 'RTN', 'REALTIME']:
            clearing_system = 'RTP'  # Real-time payments
            decision_reason = f"WIRE_TYPE={wire_type} indicates Real-time processing"
        
        # Priority 3: SOURCE_CD (fallback logic)
        elif source_cd == 'RTN':
            clearing_system = 'RTP'  # Real-time network
            decision_reason = "SOURCE_CD=RTN indicates Real-time network"
        elif source_cd == 'FED':
            clearing_system = 'FDW'  # Fedwire
            decision_reason = "SOURCE_CD=FED indicates Fedwire processing"
        elif source_cd == 'SWF':
            # SWIFT can route through different systems, need additional logic
            # Check for CHIPS-specific indicators
            if not self.is_empty_or_null(row_dict.get('CHP_ISN')) or not self.is_empty_or_null(row_dict.get('CHP_OSN')):
                clearing_system = 'CHI'
                decision_reason = "SOURCE_CD=SWF with CHIPS indicators"
            else:
                clearing_system = 'SWI'  # SWIFT
                decision_reason = "SOURCE_CD=SWF indicates SWIFT processing"
        
        # Priority 4: Check for specific network sequence numbers
        elif not self.is_empty_or_null(row_dict.get('CHP_ISN')) or not self.is_empty_or_null(row_dict.get('CHP_OSN')):
            clearing_system = 'CHI'  # CHIPS
            decision_reason = "CHIPS sequence numbers present"
        elif not self.is_empty_or_null(row_dict.get('FED_IMAD')) or not self.is_empty_or_null(row_dict.get('FED_OMAD')):
            clearing_system = 'FDW'  # Fedwire
            decision_reason = "Fedwire IMAD/OMAD present"
        elif not self.is_empty_or_null(row_dict.get('SWF_IN_MIR')) or not self.is_empty_or_null(row_dict.get('SWF_OUT_MIR')):
            clearing_system = 'SWI'  # SWIFT
            decision_reason = "SWIFT MIR present"
        
        # Default fallback
        if not clearing_system:
            clearing_system = 'CLRG'  # Generic clearing
            decision_reason = "Default - insufficient data to determine specific system"
        
        print(f"    💡 CLRG Decision: {clearing_system} ({decision_reason})")
        return clearing_system
    
    def determine_settlement_method(self, row_dict):
        """Determine settlement method based on payment characteristics"""
        source_cd = str(row_dict.get('SOURCE_CD', '')).strip().upper()
        instr_adv_type = str(row_dict.get('INSTR_ADV_TYPE', '')).strip().upper()
        is_cover_payment = str(row_dict.get('IS_COVER_PAYMENT', '')).strip().upper()
        
        # Cover payment logic
        if is_cover_payment in ['TRUE', '1', 'YES', 'Y']:
            return 'COVE'  # Cover method
        
        # Network-based settlement method
        if instr_adv_type in ['CHP', 'FED'] or source_cd in ['FED', 'RTN']:
            return 'CLRG'  # Clearing
        elif source_cd == 'SWF':
            # SWIFT can be either clearing or cover
            if not self.is_empty_or_null(row_dict.get('CHP_ISN')) or not self.is_empty_or_null(row_dict.get('FED_IMAD')):
                return 'CLRG'  # Clearing through domestic system
            else:
                return 'COVE'  # Cover method for international
        
        return 'CLRG'  # Default to clearing
    
    def csv_row_to_pacs008_xml(self, row, headers):
        """Convert CSV row to pacs.008 XML format with intelligent field mapping"""
        # Create row dictionary
        row_dict = {header: (row[i] if i < len(row) else None) for i, header in enumerate(headers)}
        
        # Get TRAN_ID (first column)
        tran_id = self.clean_value(row_dict.get('TRAN_ID', f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}'))
        
        print(f"    🔄 Converting CSV to pacs.008 XML...")
        
        # Intelligent field determination
        clearing_system = self.determine_clearing_system(row_dict)
        settlement_method = self.determine_settlement_method(row_dict)
        
        # Build XML structure
        xml_parts = []
        xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        xml_parts.append('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">')
        xml_parts.append('  <FIToFICstmrCdtTrf>')
        
        # Group Header
        xml_parts.append('    <GrpHdr>')
        xml_parts.append(f'      <MsgId>{tran_id}</MsgId>')
        
        creation_datetime = self.format_datetime(row_dict.get('TXN_DATE'))
        if creation_datetime:
            xml_parts.append(f'      <CreDtTm>{creation_datetime}</CreDtTm>')
        else:
            xml_parts.append(f'      <CreDtTm>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}</CreDtTm>')
        
        xml_parts.append('      <NbOfTxs>1</NbOfTxs>')
        
        # Settlement Information - ENHANCED with intelligent mapping
        xml_parts.append('      <SttlmInf>')
        xml_parts.append(f'        <SttlmMtd>{settlement_method}</SttlmMtd>')
        
        # Add clearing system if determined
        if clearing_system and clearing_system != 'CLRG':
            xml_parts.append('        <ClrSys>')
            xml_parts.append(f'          <Cd>{clearing_system}</Cd>')
            xml_parts.append('        </ClrSys>')
        
        # Add settlement account if available
        settlement_account = self.clean_value(row_dict.get('NETWORK_SND_ACC'))
        if settlement_account:
            xml_parts.append('        <SttlmAcct>')
            xml_parts.append('          <Id>')
            xml_parts.append('            <Othr>')
            xml_parts.append(f'              <Id>{settlement_account}</Id>')
            xml_parts.append('            </Othr>')
            xml_parts.append('          </Id>')
            xml_parts.append('        </SttlmAcct>')
        
        xml_parts.append('      </SttlmInf>')
        xml_parts.append('    </GrpHdr>')
        
        # Credit Transfer Transaction Information
        xml_parts.append('    <CdtTrfTxInf>')
        
        # Payment Identification
        xml_parts.append('      <PmtId>')
        xml_parts.append(f'        <InstrId>{tran_id}</InstrId>')
        
        end_to_end_id = self.clean_value(row_dict.get('FRONTIER_REF_NO'))
        if end_to_end_id:
            xml_parts.append(f'        <EndToEndId>{end_to_end_id}</EndToEndId>')
        
        tx_id = self.clean_value(row_dict.get('TDN_NUMBER'))
        if tx_id:
            xml_parts.append(f'        <TxId>{tx_id}</TxId>')
        
        # Add UETR if available
        uetr = self.clean_value(row_dict.get('SBK_REF_NUM'))
        if uetr:
            xml_parts.append(f'        <UETR>{uetr}</UETR>')
        
        xml_parts.append('      </PmtId>')
        
        # Interbank Settlement Amount
        amount = self.format_amount(row_dict.get('FEXCH_RATE_AMOUNT'))
        currency = self.clean_value(row_dict.get('CURRENCY_CODE', 'USD'))
        
        if amount and currency:
            xml_parts.append(f'      <IntrBkSttlmAmt Ccy="{currency}">{amount}</IntrBkSttlmAmt>')
        
        # Settlement Date
        settlement_date = self.format_date(row_dict.get('PROC_DATE'))
        if settlement_date:
            xml_parts.append(f'      <IntrBkSttlmDt>{settlement_date}</IntrBkSttlmDt>')
        
        # Debtor
        debtor_name = self.concatenate_name_fields(
            row_dict.get('DBT_NAME1'), row_dict.get('DBT_NAME_2'),
            row_dict.get('DBT_NAME_3'), row_dict.get('DBT_NAME_4')
        )
        
        if debtor_name:
            xml_parts.append('      <Dbtr>')
            xml_parts.append(f'        <Nm>{debtor_name}</Nm>')
            xml_parts.append('      </Dbtr>')
        
        # Debtor Account
        debtor_account = self.clean_value(row_dict.get('DBT_ACCTG_ACCOUNT'))
        if debtor_account:
            xml_parts.append('      <DbtrAcct>')
            xml_parts.append('        <Id>')
            xml_parts.append(f'          <Othr>')
            xml_parts.append(f'            <Id>{debtor_account}</Id>')
            xml_parts.append(f'          </Othr>')
            xml_parts.append('        </Id>')
            xml_parts.append('      </DbtrAcct>')
        
        # Debtor Agent
        debtor_agent_bic = self.clean_value(row_dict.get('OBK_ID'))
        debtor_agent_name = self.concatenate_name_fields(
            row_dict.get('OBK_NAME1'), row_dict.get('OBK_NAME2'),
            row_dict.get('OBK_NAME3'), row_dict.get('OBK_NAME4')
        )
        
        if debtor_agent_bic or debtor_agent_name:
            xml_parts.append('      <DbtrAgt>')
            xml_parts.append('        <FinInstnId>')
            if debtor_agent_bic:
                xml_parts.append(f'          <BICFI>{debtor_agent_bic}</BICFI>')
            if debtor_agent_name:
                xml_parts.append(f'          <Nm>{debtor_agent_name}</Nm>')
            xml_parts.append('        </FinInstnId>')
            xml_parts.append('      </DbtrAgt>')
        
        # Creditor Agent
        creditor_agent_bic = self.clean_value(row_dict.get('BBK_ID'))
        creditor_agent_name = self.concatenate_name_fields(
            row_dict.get('BBK_NAME1'), row_dict.get('BBK_NAME2'),
            row_dict.get('BBK_NAME3'), row_dict.get('BBK_NAME4')
        )
        
        if creditor_agent_bic or creditor_agent_name:
            xml_parts.append('      <CdtrAgt>')
            xml_parts.append('        <FinInstnId>')
            if creditor_agent_bic:
                xml_parts.append(f'          <BICFI>{creditor_agent_bic}</BICFI>')
            if creditor_agent_name:
                xml_parts.append(f'          <Nm>{creditor_agent_name}</Nm>')
            xml_parts.append('        </FinInstnId>')
            xml_parts.append('      </CdtrAgt>')
        
        # Creditor
        creditor_name = self.concatenate_name_fields(
            row_dict.get('CDT_NAME1'), row_dict.get('CDT_NAME2'),
            row_dict.get('CDT_NAME3'), row_dict.get('CDT_NAME4')
        )
        
        if creditor_name:
            xml_parts.append('      <Cdtr>')
            xml_parts.append(f'        <Nm>{creditor_name}</Nm>')
            xml_parts.append('      </Cdtr>')
        
        # Creditor Account
        creditor_account = self.clean_value(row_dict.get('CDT_ACCTG_ACCOUNT'))
        if creditor_account:
            xml_parts.append('      <CdtrAcct>')
            xml_parts.append('        <Id>')
            xml_parts.append(f'          <Othr>')
            xml_parts.append(f'            <Id>{creditor_account}</Id>')
            xml_parts.append(f'          </Othr>')
            xml_parts.append('        </Id>')
            xml_parts.append('      </CdtrAcct>')
        
        # Remittance Information
        remittance_info = self.clean_value(row_dict.get('TXN_MEMO'))
        if remittance_info:
            xml_parts.append('      <RmtInf>')
            xml_parts.append(f'        <Ustrd>{remittance_info}</Ustrd>')
            xml_parts.append('      </RmtInf>')
        
        # Supplementary Data - Network specific information
        xml_parts.append('      <SplmtryData>')
        xml_parts.append('        <PlcAndNm>NetworkInfo</PlcAndNm>')
        xml_parts.append('        <Envlp>')
        xml_parts.append(f'          <SourceCode>{row_dict.get("SOURCE_CD", "")}</SourceCode>')
        xml_parts.append(f'          <InstructionAdviceType>{row_dict.get("INSTR_ADV_TYPE", "")}</InstructionAdviceType>')
        xml_parts.append(f'          <WireType>{row_dict.get("WIRE_TYPE", "")}</WireType>')
        xml_parts.append(f'          <ClearingSystem>{clearing_system}</ClearingSystem>')
        xml_parts.append('        </Envlp>')
        xml_parts.append('      </SplmtryData>')
        
        xml_parts.append('    </CdtTrfTxInf>')
        xml_parts.append('  </FIToFICstmrCdtTrf>')
        xml_parts.append('</Document>')
        
        print(f"    ✅ XML generated with CLRG={clearing_system}, SttlmMtd={settlement_method}")
        
        return '\n'.join(xml_parts)
    
    def validate_xml_against_xsd(self, xml_content):
        """Validate XML against the pacs.008 XSD schema"""
        if not self.schema:
            return False, ["XSD schema not loaded"]
        
        try:
            # Parse XML
            xml_doc = etree.fromstring(xml_content.encode('utf-8'))
            
            # Validate against schema
            self.schema.validate(xml_doc)
            
            return True, []
            
        except xmlschema.XMLSchemaException as e:
            return False, [f"XSD Validation Error: {str(e)}"]
        except etree.XMLSyntaxError as e:
            return False, [f"XML Syntax Error: {str(e)}"]
        except Exception as e:
            return False, [f"Validation Error: {str(e)}"]
    
    def validate_csv_row_against_xsd(self, row, headers, row_index):
        """Validate a CSV row by converting to XML and validating against XSD"""
        tran_id = row[0] if len(row) > 0 else f'Row{row_index}'
        
        print(f"🔍 Row {row_index:4d}: TRAN_ID = '{tran_id}'")
        
        try:
            # Convert CSV row to pacs.008 XML
            xml_content = self.csv_row_to_pacs008_xml(row, headers)
            
            # Validate against XSD
            is_valid, errors = self.validate_xml_against_xsd(xml_content)
            
            if is_valid:
                print(f"    ✅ Row {row_index} is XSD compliant!")
                return []
            else:
                print(f"    ❌ Row {row_index} has {len(errors)} XSD violations:")
                for error in errors:
                    print(f"       🚨 {error}")
                return errors
                
        except Exception as e:
            error_msg = f"XML Generation Error: {str(e)}"
            print(f"    ❌ Row {row_index} XML generation failed:")
            print(f"       🚨 {error_msg}")
            return [error_msg]
    
    def process_csv_file(self, file_path):
        """Main processing function"""
        if not self.schema:
            print("❌ Cannot proceed without valid XSD schema")
            return None
        
        print("🚀 Starting TRUE XSD pacs.008 Validation")
        print("="*80)
        
        # Preprocess CSV
        df = self.preprocess_csv_file(file_path)
        if df is None:
            return None
        
        print(f"\n📊 Processing {len(df)} rows against pacs.008.001.08.xsd")
        print("="*80)
        
        all_issues = []
        
        # Process each row
        for index, row in df.iterrows():
            row_values = row.tolist()
            headers = df.columns.tolist()
            
            xsd_errors = self.validate_csv_row_against_xsd(row_values, headers, index + 1)
            
            if xsd_errors:
                tran_id = row_values[0] if len(row_values) > 0 else f'Row{index + 1}'
                all_issues.append({
                    'row': index + 1,
                    'tran_id': tran_id,
                    'xsd_errors': xsd_errors
                })
        
        # Generate final report
        self.generate_xsd_report(all_issues, len(df))
        
        return all_issues
    
    def generate_xsd_report(self, all_issues, total_rows):
        """Generate XSD validation report"""
        print("\n" + "="*80)
        print("📊 TRUE XSD VALIDATION REPORT - pacs.008.001.08")
        print("="*80)
        
        print(f"\n📈 XSD VALIDATION RESULTS:")
        print(f"   Total Rows Processed: {total_rows:,}")
        print(f"   XSD Compliant Rows: {total_rows - len(all_issues):,}")
        print(f"   XSD Violation Rows: {len(all_issues):,}")
        print(f"   XSD Compliance Rate: {((total_rows - len(all_issues)) / total_rows * 100):.1f}%")
        
        if all_issues:
            print(f"\n🚨 XSD VIOLATIONS BY TRAN_ID:")
            print("-" * 60)
            
            for i, issue_data in enumerate(all_issues[:20], 1):  # Show first 20
                print(f"   {i:2d}. Row {issue_data['row']:4d} | TRAN_ID: '{issue_data['tran_id']}' | {len(issue_data['xsd_errors'])} XSD errors")
                
                for error in issue_data['xsd_errors'][:3]:  # Show first 3 errors
                    print(f"       🚨 {error}")
                
                if len(issue_data['xsd_errors']) > 3:
                    print(f"       ... and {len(issue_data['xsd_errors']) - 3} more XSD errors")
            
            if len(all_issues) > 20:
                print(f"\n   ... and {len(all_issues) - 20} more rows with XSD violations")
        
        print(f"\n🎯 XSD COMPLIANCE SUMMARY:")
        print("   ✅ XSD compliant rows can be processed as valid pacs.008 messages")
        print("   ❌ XSD violation rows must be fixed before Fed processing")
        print("   🚨 All errors are based on official pacs.008.001.08.xsd schema")
        print("   📋 Fix XSD violations to ensure Fed ISO 20022 compliance")
        
        print("="*80)

# Interactive input functions
def get_csv_filename():
    """Get CSV filename from user input"""
    while True:
        csv_file = input("\n📄 Enter CSV filename (or full path): ").strip()
        
        if not csv_file:
            print("❌ Please enter a filename")
            continue
        
        # Add .csv extension if not provided
        if not csv_file.lower().endswith('.csv'):
            csv_file += '.csv'
        
        # Check if file exists
        if os.path.exists(csv_file):
            print(f"✅ Found CSV file: {os.path.abspath(csv_file)}")
            return csv_file
        else:
            print(f"❌ File not found: {os.path.abspath(csv_file)}")
            retry = input("🔄 Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return None

def get_xsd_filename():
    """Get XSD filename from user input"""
    while True:
        print("\n📋 XSD File Options:")
        print("1. Use default: pacs.008.001.08.xsd (in current directory)")
        print("2. Enter custom XSD file path")
        
        choice = input("Choose option (1 or 2): ").strip()
        
        if choice == '1':
            xsd_file = "pacs.008.001.08.xsd"
        elif choice == '2':
            xsd_file = input("📄 Enter XSD filename (or full path): ").strip()
            if not xsd_file:
                print("❌ Please enter a filename")
                continue
        else:
            print("❌ Invalid choice. Please enter 1 or 2")
            continue
        
        # Check if file exists
        if os.path.exists(xsd_file):
            print(f"✅ Found XSD file: {os.path.abspath(xsd_file)}")
            return xsd_file
        else:
            print(f"❌ XSD file not found: {os.path.abspath(xsd_file)}")
            print(f"💡 Download from: https://github.com/phoughton/pyiso20022/raw/main/xsd/payments_clearing_and_settlement/pacs.008/pacs.008.001.08.xsd")
            retry = input("🔄 Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return None

# Main functions
def main():
    """Interactive mode - prompts user for files"""
    print("🚀 TRUE XSD pacs.008.001.08 Validator")
    print("="*60)
    print("📄 Uses official ISO 20022 XSD schema")
    print("🔍 Converts CSV to XML and validates against XSD")
    print("📋 Handles Mac CSV files with ^M line endings")
    print("🧠 Intelligent field mapping for CLRG determination")
    
    # Get XSD file
    print("\n" + "="*60)
    print("STEP 1: XSD SCHEMA FILE")
    print("="*60)
    xsd_file = get_xsd_filename()
    if not xsd_file:
        print("❌ Cannot proceed without XSD file. Exiting.")
        return
    
    # Get CSV file
    print("\n" + "="*60)
    print("STEP 2: CSV DATA FILE") 
    print("="*60)
    csv_file = get_csv_filename()
    if not csv_file:
        print("❌ Cannot proceed without CSV file. Exiting.")
        return
    
    # Initialize validator with local XSD
    print("\n" + "="*60)
    print("STEP 3: INITIALIZING VALIDATOR")
    print("="*60)
    print(f"🔧 Loading XSD schema from: {xsd_file}")
    print(f"📊 Preparing to process CSV: {csv_file}")
    
    validator = TrueXSDPacs008Validator(xsd_file)
    
    # Check if schema loaded successfully
    if not validator.schema:
        print("❌ Failed to load XSD schema. Cannot proceed.")
        print("💡 Make sure you have the correct pacs.008.001.08.xsd file")
        return
    
    # Process the CSV file
    print("\n" + "="*60)
    print("STEP 4: VALIDATION PROCESS")
    print("="*60)
    print(f"🚀 Starting validation of {csv_file}")
    print("🧠 Using intelligent CLRG field determination")
    
    issues = validator.process_csv_file(csv_file)
    
    # Final results
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if issues is not None:
        if len(issues) == 0:
            print("🎉 SUCCESS! All rows are XSD compliant!")
            print("✅ Your data is ready for Fed ISO 20022 processing")
            print("📤 Generated XML messages will pass XSD validation")
        else:
            print(f"⚠️  PARTIAL SUCCESS: {len(issues)} rows have XSD violations")
            print("🔧 Fix the reported issues for full compliance")
            print("📋 Review the detailed report above for specific problems")
        
        print(f"\n📊 Validation Summary:")
        print(f"   ✅ XSD Schema: {xsd_file}")
        print(f"   📄 CSV File: {csv_file}")
        print(f"   🎯 Compliance: {'100%' if len(issues) == 0 else 'Partial'}")
        
    else:
        print("❌ VALIDATION FAILED")
        print("🔍 Check file format and try again")
        print("💡 Ensure CSV has proper headers and XSD is valid")

def main_with_args():
    """Command line mode - accepts arguments"""
    if len(sys.argv) < 2:
        print("🚀 TRUE XSD pacs.008.001.08 Validator")
        print("="*50)
        print("Usage: python validator.py <csv_file> [xsd_file]")
        print("")
        print("Arguments:")
        print("  csv_file    Path to your CSV file (required)")
        print("  xsd_file    Path to XSD file (optional, default: pacs.008.001.08.xsd)")
        print("")
        print("Examples:")
        print("  python validator.py data.csv")
        print("  python validator.py /path/to/data.csv /path/to/schema.xsd")
        print("")
        print("Or run without arguments for interactive mode:")
        print("  python validator.py")
        print("")
        main()
        return
    
    csv_file = sys.argv[1]
    xsd_file = sys.argv[2] if len(sys.argv) > 2 else "pacs.008.001.08.xsd"
    
    print(f"🚀 TRUE XSD pacs.008.001.08 Validator (Command Line Mode)")
    print("="*70)
    print(f"📄 CSV File: {csv_file}")
    print(f"📋 XSD File: {xsd_file}")
    print(f"🧠 Intelligent CLRG field determination: ENABLED")
    
    # Validate files exist
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print(f"💡 Make sure the file path is correct")
        return
    
    if not os.path.exists(xsd_file):
        print(f"❌ XSD file not found: {xsd_file}")
        print(f"💡 Download from: https://github.com/phoughton/pyiso20022/raw/main/xsd/payments_clearing_and_settlement/pacs.008/pacs.008.001.08.xsd")
        return
    
    # Initialize and run validator
    print(f"\n🔧 Initializing validator...")
    validator = TrueXSDPacs008Validator(xsd_file)
    
    if not validator.schema:
        print("❌ Failed to load XSD schema.")
        return
    
    print(f"🚀 Starting validation...")
    issues = validator.process_csv_file(csv_file)
    
    # Command line results
    if issues is not None:
        total_issues = len(issues)
        if total_issues == 0:
            print(f"\n✅ SUCCESS: All rows are XSD compliant!")
            sys.exit(0)
        else:
            print(f"\n⚠️  ISSUES FOUND: {total_issues} rows with XSD violations")
            sys.exit(1)
    else:
        print("❌ VALIDATION FAILED")
        sys.exit(2)

if __name__ == "__main__":
    try:
        # Check if command line arguments provided
        if len(sys.argv) > 1:
            main_with_args()
        else:
            main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error occurred: {str(e)}")
        print("💡 Please check your input files and try again")
        sys.exit(3)
