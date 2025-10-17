#!/usr/bin/env python3
"""
Enhanced Bulgarian VAT System - Comprehensive Test Suite
Tests all major functionality of the enhanced system
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8001/api/v2"
TEST_COMPANY = {
    "uic": "123456789",
    "vat_number": "BG123456789",
    "name": "Test Company Ltd",
    "address": "Sofia, Bulgaria",
    "is_active": True
}

class EnhancedSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.company_id = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f" ({details})"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def test_system_info(self):
        """Test system information endpoints"""
        print("\n🔍 TESTING SYSTEM INFORMATION")
        
        # Test document types
        purchase_types = self.make_request("GET", "/purchase-document-types")
        if "document_types" in purchase_types:
            count = len(purchase_types["document_types"])
            self.log_test("Purchase Document Types", count == 14, f"{count} types found")
        else:
            self.log_test("Purchase Document Types", False, "Failed to retrieve")
        
        sales_types = self.make_request("GET", "/sales-document-types")
        if "document_types" in sales_types:
            count = len(sales_types["document_types"])
            self.log_test("Sales Document Types", count >= 6, f"{count} types found")
        else:
            self.log_test("Sales Document Types", False, "Failed to retrieve")
        
        # Test VAT field definitions
        vat_fields = self.make_request("GET", "/vat-field-definitions")
        if "field_definitions" in vat_fields:
            count = len(vat_fields["field_definitions"])
            self.log_test("VAT Field Definitions", count >= 20, f"{count} fields defined")
        else:
            self.log_test("VAT Field Definitions", False, "Failed to retrieve")
    
    def test_vies_validation(self):
        """Test VIES VAT validation"""
        print("\n🌍 TESTING VIES VALIDATION")
        
        # Test EU VAT validation
        test_request = {
            "country_code": "DE",
            "vat_number": "123456789",
            "requester_country_code": "BG",
            "requester_vat": "BG123456789"
        }
        
        result = self.make_request("POST", "/vat/validate-eu-vat", test_request)
        if "validation_status" in result:
            self.log_test("VIES EU VAT Validation", True, f"Status: {result.get('validation_status')}")
        else:
            self.log_test("VIES EU VAT Validation", False, "No validation status returned")
    
    def test_company_management(self):
        """Test enhanced company management"""
        print("\n🏢 TESTING COMPANY MANAGEMENT")
        
        # Test company creation
        result = self.make_request("POST", "/companies", TEST_COMPANY)
        if "id" in result:
            self.company_id = result["id"]
            self.log_test("Create Enhanced Company", True, f"Company ID: {self.company_id}")
        else:
            self.log_test("Create Enhanced Company", False, result.get("error", "Unknown error"))
            return
        
        # Test company retrieval
        company = self.make_request("GET", f"/companies/{TEST_COMPANY['uic']}")
        if "id" in company:
            self.log_test("Get Enhanced Company", True, f"Name: {company.get('name')}")
        else:
            self.log_test("Get Enhanced Company", False, "Failed to retrieve company")
        
        # Test company list
        companies = self.make_request("GET", "/companies")
        if isinstance(companies, list):
            self.log_test("List Enhanced Companies", True, f"{len(companies)} companies found")
        else:
            self.log_test("List Enhanced Companies", False, "Failed to list companies")
    
    def test_purchase_entries(self):
        """Test enhanced purchase entries with different document types"""
        print("\n📥 TESTING PURCHASE ENTRIES")
        
        if not self.company_id:
            self.log_test("Purchase Entries", False, "No company ID available")
            return
        
        test_entries = [
            {
                "name": "Standard Invoice",
                "data": {
                    "period": "202409",
                    "document_type": 1,
                    "document_number": "INV-001",
                    "supplier_name": "Test Supplier",
                    "tax_base": 1000,
                    "vat_amount": 200
                }
            },
            {
                "name": "Customs Document",
                "data": {
                    "period": "202409", 
                    "document_type": 2,
                    "document_number": "CU-001",
                    "supplier_name": "Import Supplier",
                    "customs_document_ref": "CU2024001234",
                    "customs_office": "Sofia Airport",
                    "tax_base": 2000,
                    "vat_amount": 400
                }
            },
            {
                "name": "Triangular Operation",
                "data": {
                    "period": "202409",
                    "document_type": 11,
                    "triangular_operation_type": 11,
                    "supplier_name": "EU Intermediary",
                    "intermediary_vat": "DE123456789",
                    "final_customer_vat": "FR987654321",
                    "tax_base": 5000,
                    "vat_amount": 1000
                }
            }
        ]
        
        for entry in test_entries:
            result = self.make_request("POST", f"/companies/{TEST_COMPANY['uic']}/purchases", entry["data"])
            if "id" in result:
                self.log_test(f"Create {entry['name']}", True, f"Entry ID: {result['id']}")
            else:
                self.log_test(f"Create {entry['name']}", False, result.get("error", "Unknown error"))
        
        # Test purchase retrieval
        purchases = self.make_request("GET", f"/companies/{TEST_COMPANY['uic']}/purchases/202409")
        if isinstance(purchases, list):
            self.log_test("Get Purchase Entries", True, f"{len(purchases)} entries found")
        else:
            self.log_test("Get Purchase Entries", False, "Failed to retrieve purchases")
        
        # Test purchase summary
        summary = self.make_request("GET", f"/companies/{TEST_COMPANY['uic']}/purchases/202409/summary")
        if isinstance(summary, dict):
            types_count = len(summary)
            self.log_test("Purchase Summary by Type", True, f"{types_count} document types")
        else:
            self.log_test("Purchase Summary by Type", False, "Failed to get summary")
    
    def test_sales_entries(self):
        """Test enhanced sales entries with field mapping"""
        print("\n📤 TESTING SALES ENTRIES")
        
        if not self.company_id:
            self.log_test("Sales Entries", False, "No company ID available")
            return
        
        test_entries = [
            {
                "name": "Domestic Sale",
                "data": {
                    "period": "202409",
                    "document_type": 1,
                    "document_number": "SALE-001",
                    "customer_name": "Domestic Customer",
                    "field_09": 1000,  # Tax base 20%
                    "field_10": 200,   # VAT 20%
                    "total_amount": 1200
                }
            },
            {
                "name": "EU Sale",
                "data": {
                    "period": "202409",
                    "document_type": 2,
                    "document_number": "EU-001",
                    "customer_name": "EU Customer",
                    "customer_vat": "DE123456789",
                    "customer_country": "DE",
                    "field_13": 3000,  # Intra-community delivery
                    "total_amount": 3000
                }
            }
        ]
        
        for entry in test_entries:
            result = self.make_request("POST", f"/companies/{TEST_COMPANY['uic']}/sales", entry["data"])
            if "id" in result:
                self.log_test(f"Create {entry['name']}", True, f"Entry ID: {result['id']}")
            else:
                self.log_test(f"Create {entry['name']}", False, result.get("error", "Unknown error"))
        
        # Test field totals calculation
        totals = self.make_request("GET", f"/companies/{TEST_COMPANY['uic']}/sales/202409/field-totals")
        if isinstance(totals, dict):
            field_count = len([k for k in totals.keys() if k.startswith("field_")])
            self.log_test("Sales Field Totals", True, f"{field_count} fields calculated")
        else:
            self.log_test("Sales Field Totals", False, "Failed to calculate totals")
    
    def test_vat_declaration(self):
        """Test enhanced VAT declaration generation"""
        print("\n📋 TESTING VAT DECLARATIONS")
        
        if not self.company_id:
            self.log_test("VAT Declaration", False, "No company ID available")
            return
        
        # Generate declaration
        result = self.make_request("POST", f"/companies/{TEST_COMPANY['uic']}/declarations/202409")
        if "declaration" in result:
            declaration = result["declaration"]
            field_count = len([k for k in declaration.keys() if k.startswith("field_")])
            self.log_test("Generate VAT Declaration", True, f"{field_count} fields populated")
            
            # Test declaration validation
            if "id" in declaration:
                validation = self.make_request("POST", f"/declarations/{declaration['id']}/validate")
                if "is_valid" in validation:
                    self.log_test("Validate VAT Declaration", validation["is_valid"], 
                                f"Errors: {len(validation.get('validation_errors', []))}")
                else:
                    self.log_test("Validate VAT Declaration", False, "No validation result")
        else:
            self.log_test("Generate VAT Declaration", False, result.get("error", "Unknown error"))
    
    def test_triangular_operations(self):
        """Test triangular operations summary"""
        print("\n🔺 TESTING TRIANGULAR OPERATIONS")
        
        result = self.make_request("GET", f"/companies/{TEST_COMPANY['uic']}/triangular-operations/202409")
        if "summary" in result:
            summary = result["summary"]
            purchase_count = summary.get("purchase_count", 0)
            sales_count = summary.get("sales_count", 0)
            self.log_test("Triangular Operations Summary", True, 
                        f"Purchases: {purchase_count}, Sales: {sales_count}")
        else:
            self.log_test("Triangular Operations Summary", False, "Failed to get summary")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 STARTING ENHANCED SYSTEM TEST SUITE")
        print("="*60)
        
        start_time = time.time()
        
        # Run all test categories
        self.test_system_info()
        self.test_vies_validation()
        self.test_company_management()
        self.test_purchase_entries()
        self.test_sales_entries()
        self.test_vat_declaration()
        self.test_triangular_operations()
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        
        passed = len([r for r in self.test_results if r["success"]])
        failed = len([r for r in self.test_results if not r["success"]])
        total = len(self.test_results)
        
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}% ({passed}/{total})")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        return passed, failed, total

def main():
    """Main test execution"""
    print("Enhanced Bulgarian VAT System - Test Suite")
    print("Testing API at: http://localhost:8001/api/v2")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/purchase-document-types", timeout=5)
        if response.status_code == 200:
            print("✅ Enhanced API server is running")
        else:
            print("❌ Enhanced API server returned error:", response.status_code)
            return
    except requests.exceptions.RequestException:
        print("❌ Enhanced API server is not accessible at http://localhost:8001")
        print("   Please make sure the enhanced API is running:")
        print("   cd E:\\Inst_DnevZDDS_v1402\\backend && python enhanced_api.py")
        return
    
    # Run tests
    tester = EnhancedSystemTester()
    passed, failed, total = tester.run_all_tests()
    
    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump({
            "summary": {
                "passed": passed,
                "failed": failed,
                "total": total,
                "success_rate": (passed/total)*100,
                "timestamp": datetime.now().isoformat()
            },
            "details": tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: test_results.json")

if __name__ == "__main__":
    main()