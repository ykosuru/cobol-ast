#!/usr/bin/env python3
"""
Test script for the flow-based indexer to verify it works correctly.
"""

import os
import tempfile
import sys

# Add the parent directory to Python path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_tal_files():
    """Create test TAL files for indexing."""
    test_dir = tempfile.mkdtemp(prefix="tal_test_")
    print(f"Creating test files in: {test_dir}")
    
    # Test file 1: SWIFT processing
    swift_content = """
PROC VALIDATE_MT103_MESSAGE(message_buffer);
BEGIN
    ! Validate SWIFT MT103 customer credit transfer
    INT validation_result := 0;
    STRING bic_code[11];
    STRING amount_field[15];
    
    ! Extract BIC from instructing agent field
    CALL EXTRACT_BIC_FROM_FIELD(message_buffer, bic_code);
    
    ! Validate BIC format
    IF VALIDATE_BIC_FORMAT(bic_code) THEN
        validation_result := 1;
    ELSE
        CALL LOG_VALIDATION_ERROR("Invalid BIC format", bic_code);
        validation_result := 0;
    END;
    
    ! Validate amount field
    CALL EXTRACT_AMOUNT_FIELD(message_buffer, amount_field);
    IF VALIDATE_AMOUNT_FORMAT(amount_field) THEN
        validation_result := validation_result AND 1;
    ELSE
        CALL LOG_VALIDATION_ERROR("Invalid amount format", amount_field);
        validation_result := 0;
    END;
    
    RETURN validation_result;
END;

PROC PROCESS_SWIFT_GPI_TRACKING(uetr, message_id);
BEGIN
    ! Process SWIFT gpi tracking for real-time payment tracking
    STRING tracker_id[36];
    INT tracking_status;
    
    CALL GENERATE_TRACKER_ID(uetr, tracker_id);
    CALL UPDATE_PAYMENT_STATUS(message_id, "IN_PROGRESS");
    
    ! Send tracking update to gpi network
    CALL SEND_GPI_TRACKING_UPDATE(tracker_id, tracking_status);
END;
"""
    
    # Test file 2: Fedwire processing
    fedwire_content = """
PROC PROCESS_FEDWIRE_TYPE_1000(wire_message);
BEGIN
    ! Process Fedwire customer transfer (type code 1000)
    STRING imad[9];
    STRING omad[9];
    STRING originator_info[140];
    STRING beneficiary_info[140];
    
    ! Generate IMAD for tracking
    CALL GENERATE_IMAD(imad);
    CALL LOG_WIRE_TRANSACTION("TYPE_1000", imad);
    
    ! Extract originator information
    CALL EXTRACT_ORIGINATOR_DATA(wire_message, originator_info);
    
    ! Validate beneficiary information
    CALL EXTRACT_BENEFICIARY_DATA(wire_message, beneficiary_info);
    IF VALIDATE_BENEFICIARY_ACCOUNT(beneficiary_info) THEN
        CALL PROCESS_CUSTOMER_TRANSFER(wire_message, imad);
    ELSE
        CALL REJECT_WIRE_TRANSFER(imad, "Invalid beneficiary account");
    END;
END;

PROC HANDLE_FEDWIRE_EXCEPTION(error_code, wire_data);
BEGIN
    ! Handle Fedwire processing exceptions and errors
    STRING repair_action[50];
    INT retry_count := 0;
    
    CASE error_code OF
        "FED001" -> repair_action := "RETRY_TRANSMISSION";
        "FED002" -> repair_action := "MANUAL_INTERVENTION";
        "FED003" -> repair_action := "RETURN_TO_ORIGINATOR";
        DEFAULT -> repair_action := "INVESTIGATE";
    END;
    
    ! Implement retry logic for transient errors
    WHILE retry_count < 3 AND repair_action = "RETRY_TRANSMISSION" DO
        retry_count := retry_count + 1;
        CALL RETRY_FEDWIRE_TRANSMISSION(wire_data);
    END;
END;
"""
    
    # Test file 3: ISO 20022 validation
    iso_content = """
PROC VALIDATE_PACS008_MESSAGE(iso_message);
BEGIN
    ! Validate ISO 20022 pacs.008 customer credit transfer
    INT field_validation_result := 1;
    STRING instructing_agent[11];
    STRING instructed_agent[11];
    STRING currency_code[3];
    
    ! Mandatory field validation
    IF VALIDATE_MANDATORY_FIELDS(iso_message) THEN
        CALL LOG_INFO("Mandatory fields validation passed");
    ELSE
        field_validation_result := 0;
        CALL LOG_VALIDATION_ERROR("Missing mandatory fields", "PACS008");
    END;
    
    ! Cross-field validation for currency and amount consistency
    CALL EXTRACT_CURRENCY_CODE(iso_message, currency_code);
    IF VALIDATE_CURRENCY_AMOUNT_CONSISTENCY(iso_message, currency_code) THEN
        CALL LOG_INFO("Currency-amount validation passed");
    ELSE
        field_validation_result := 0;
        CALL LOG_VALIDATION_ERROR("Currency-amount inconsistency", currency_code);
    END;
    
    RETURN field_validation_result;
END;

PROC SCREEN_PAYMENT_FOR_COMPLIANCE(payment_data);
BEGIN
    ! Screen payment for OFAC, AML, and sanctions compliance
    INT screening_result := 1;
    STRING originator_name[140];
    STRING beneficiary_name[140];
    
    ! OFAC sanctions screening
    CALL EXTRACT_PARTY_NAMES(payment_data, originator_name, beneficiary_name);
    
    IF SCREEN_OFAC_SANCTIONS(originator_name) = 0 THEN
        screening_result := 0;
        CALL LOG_COMPLIANCE_HIT("OFAC_ORIGINATOR", originator_name);
        CALL HOLD_PAYMENT_FOR_REVIEW(payment_data);
    END;
    
    IF SCREEN_OFAC_SANCTIONS(beneficiary_name) = 0 THEN
        screening_result := 0;
        CALL LOG_COMPLIANCE_HIT("OFAC_BENEFICIARY", beneficiary_name);
        CALL HOLD_PAYMENT_FOR_REVIEW(payment_data);
    END;
    
    ! AML monitoring
    IF CHECK_AML_THRESHOLDS(payment_data) = 0 THEN
        CALL LOG_AML_ALERT("Threshold exceeded", payment_data);
        CALL GENERATE_SUSPICIOUS_ACTIVITY_REPORT(payment_data);
    END;
    
    RETURN screening_result;
END;
"""
    
    # Write test files
    with open(os.path.join(test_dir, "swift_processing.tal"), 'w') as f:
        f.write(swift_content)
    
    with open(os.path.join(test_dir, "fedwire_processing.tal"), 'w') as f:
        f.write(fedwire_content)
    
    with open(os.path.join(test_dir, "iso20022_validation.tal"), 'w') as f:
        f.write(iso_content)
    
    return test_dir

def test_indexer():
    """Test the flow-based indexer."""
    try:
        # Import the indexer
        from flow_indexer import FlowBasedCorpusIndexer, FlowType, PaymentNetwork
        
        print("✅ Successfully imported flow indexer")
        
        # Create test files
        test_dir = create_test_tal_files()
        
        # Initialize indexer
        indexer = FlowBasedCorpusIndexer(max_features=1000)
        print("✅ Indexer initialized")
        
        # Index the test directory
        chunks = indexer.index_directory(test_dir)
        print(f"✅ Indexed {len(chunks)} chunks")
        
        # Print statistics
        indexer.print_flow_statistics()
        indexer.print_flow_samples(n=2)
        
        # Test search functions
        validation_chunks = indexer.search_by_flow(FlowType.VALIDATION, threshold=0.1)
        print(f"\n🔍 Found {len(validation_chunks)} validation chunks")
        
        swift_chunks = indexer.search_by_network(PaymentNetwork.SWIFT)
        print(f"🔍 Found {len(swift_chunks)} SWIFT chunks")
        
        # Save corpus for testing searcher
        test_corpus_file = os.path.join(test_dir, "test_corpus.pkl")
        indexer.save_flow_corpus(test_corpus_file)
        
        print(f"\n✅ Test completed successfully!")
        print(f"📁 Test corpus saved to: {test_corpus_file}")
        print(f"🧹 Test files in: {test_dir}")
        print(f"\n🔍 Test the searcher with:")
        print(f"   python payment_flow_searcher.py {test_corpus_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTING FLOW-BASED TAL INDEXER")
    print("="*60)
    
    success = test_indexer()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Tests failed!")
    
    input("\nPress Enter to exit...")
