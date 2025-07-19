import pandas as pd
import requests
from lxml import etree
import xmlschema
from datetime import datetime
import logging
import os
from decimal import Decimal
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrueXSDPacs008Validator:
    def __init__(self):
        self.xsd_url = "https://raw.githubusercontent.com/phoughton/pyiso20022/main/xsd/payments_clearing_and_settlement/pacs.008/pacs.008.001.08.xsd"
        self.xsd_file = "pacs.008.001.08.xsd"
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
        """Download and load the pacs.008 XSD schema"""
        print("📥 Loading pacs.008.001.08 XSD schema...")
        
        try:
            # Download XSD if not exists
            if not os.path.exists(self.xsd_file):
                print(f"🌐 Downloading XSD from: {self.xsd_url}")
                response = requests.get(self.xsd_url)
                response.raise_for_status()
                
                with open(self.xsd_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"✅ XSD downloaded and saved as {self.xsd_file}")
            else:
                print(f"📄 Using existing XSD file: {self.xsd_file}")
            
            # Load schema using xmlschema
            self.schema = xmlschema.XMLSchema(self.xsd_file)
            print(f"✅ XSD schema loaded successfully!")
            print(f"   Schema target namespace: {self.schema.target_namespace}")
            print(f"   Schema version: {getattr(self.schema, 'version', 'Not specified')}")
            
        except Exception as e:
            print(f"❌ Error loading XSD schema: {str(e)}")
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
            # Clean amount value
            clean_value = str(amount_value).replace(',', '').replace('$', '').replace('€', '').strip()
            
            if clean_value.startswith('(') and clean_value.endswith(')'):
                clean_value = '-' + clean_value[1:-1]
            
            amount = Decimal(clean_value)
            
            # Format to max 5 decimal places
            formatted = f"{amount:.5f}".rstrip('0').rstrip('.')
            return formatted
            
        except Exception:
            return str(amount_value)
    
    def csv_row_to_pacs008_xml(self, row, headers):
        """Convert CSV row to pacs.008 XML format"""
        # Create row dictionary
        row_dict = {header: (row[i] if i < len(row) else None) for i, header in enumerate(headers)}
        
        # Get TRAN_ID (first column)
        tran_id = self.clean_value(row_dict.get('TRAN_ID', f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}'))
        
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
        
        xml_parts.append('    </CdtTrfTxInf>')
        xml_parts.append('  </FIToFICstmrCdtTrf>')
        xml_parts.append('</Document>')
        
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

# Usage
def main():
    validator = TrueXSDPacs008Validator()
    
    # Update with your CSV file path
    csv_file_path = "wire_transfer_data.csv"  # Change to your file
    
    print("🚀 TRUE XSD pacs.008.001.08 Validator")
    print("📄 Uses official ISO 20022 XSD schema")
    print("🔍 Converts CSV to XML and validates against XSD")
    
    issues = validator.process_csv_file(csv_file_path)
    
    if issues is not None:
        print(f"\n✅ XSD validation completed!")
        print(f"📊 {len(issues)} rows have XSD schema violations")
        print(f"🎯 Fix XSD errors for true Fed ISO 20022 compliance")
    else:
        print("❌ Validation failed. Check file path and XSD schema.")

if __name__ == "__main__":
    main()
