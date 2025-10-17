#!/usr/bin/env python3
"""
VIES VAT Validation Demo
Tests the VIES integration directly
"""

import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from vies_validation_service import vies_validator

def test_vies_integration():
    """Demonstrate VIES VAT validation functionality"""
    
    print("EU VIES VAT Number Validation Demo")
    print("=" * 50)
    
    # Test cases with real German VAT numbers that should validate
    test_cases = [
        ("DE", "136695976", "Valid German company"),
        ("FR", "40303265045", "Valid French company"),  
        ("BG", "206450255", "Valid Bulgarian company"),
        ("IT", "12345678901", "Invalid Italian VAT format"),
        ("ES", "A12345674", "Test Spanish VAT")
    ]
    
    for country, vat_num, description in test_cases:
        print(f"\nTesting {country}{vat_num} ({description})")
        print("-" * 40)
        
        try:
            result = vies_validator.validate_vat_number(country, vat_num)
            
            if result.is_valid:
                print(f"VALID VAT number")
                print(f"   Company: {result.company_name or 'Name not available'}")
                print(f"   Address: {result.company_address or 'Address not available'}")
            else:
                print(f"INVALID VAT number")
                if hasattr(result, 'error_message') and result.error_message:
                    print(f"   Error: {result.error_message}")
                    
        except Exception as e:
            print(f"ERROR: {str(e)}")
    
    print(f"\nDemo completed")
    
    # Test batch validation 
    print(f"\nTesting Batch Validation")
    print("=" * 30)
    
    batch_vats = ["DE136695976", "FR40303265045", "BG206450255"]
    try:
        # Note: Your API might support batch validation
        print(f"Would validate: {', '.join(batch_vats)}")
        print("(Batch validation available via API endpoint)")
    except Exception as e:
        print(f"Batch validation error: {e}")

if __name__ == "__main__":
    test_vies_integration()