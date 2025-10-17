"""
VIES VAT Number Validation Service

Integrates with the official European Commission VIES REST API
to validate EU VAT numbers in real-time.

API Documentation: https://ec.europa.eu/taxation_customs/vies/rest-api/
"""

import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VATValidationResult:
    """Result of VAT number validation"""
    country_code: str
    vat_number: str
    is_valid: bool
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    request_date: Optional[datetime] = None
    request_identifier: Optional[str] = None
    error_message: Optional[str] = None
    trader_name_match: Optional[str] = None
    trader_address_match: Optional[str] = None

class VIESValidationService:
    """Service for validating EU VAT numbers using VIES REST API"""
    
    def __init__(self):
        self.base_url = "https://ec.europa.eu/taxation_customs/vies/rest-api"
        self.timeout = 10  # seconds
        self.cache = {}  # Simple cache for validated numbers
        self.cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
    def validate_vat_number(
        self, 
        country_code: str, 
        vat_number: str,
        requester_country_code: str = "BG",
        requester_vat_number: str = None,
        trader_name: Optional[str] = None,
        trader_address: Optional[str] = None
    ) -> VATValidationResult:
        """
        Validate EU VAT number using VIES REST API
        
        Args:
            country_code: Two-letter EU country code (e.g., "DE", "FR")
            vat_number: National VAT number without country prefix
            requester_country_code: Country code of the requesting company (default: "BG")
            requester_vat_number: VAT number of the requesting company
            trader_name: Company name for verification (optional)
            trader_address: Company address for verification (optional)
            
        Returns:
            VATValidationResult with validation status and company details
        """
        
        # Check cache first
        cache_key = f"{country_code}:{vat_number}"
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                logger.info(f"Using cached validation result for {cache_key}")
                return cached_result
        
        # Prepare request data
        request_data = {
            "countryCode": country_code.upper(),
            "vatNumber": vat_number,
            "requesterMemberStateCode": requester_country_code.upper()
        }
        
        # Add requester VAT number if provided
        if requester_vat_number:
            # Remove country prefix if present
            clean_requester_vat = requester_vat_number.replace(requester_country_code.upper(), "")
            request_data["requesterNumber"] = clean_requester_vat
        
        # Add trader information for enhanced validation
        if trader_name:
            request_data["traderName"] = trader_name
        if trader_address:
            # Parse address into components if possible
            request_data["traderStreet"] = trader_address
        
        try:
            logger.info(f"Validating VAT number: {country_code}{vat_number}")
            
            # Make request to VIES API
            response = requests.post(
                f"{self.base_url}/check-vat-number",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result_data = response.json()
                result = self._parse_validation_response(result_data, country_code, vat_number)
                
                # Cache successful results
                if result.is_valid is not None:
                    self.cache[cache_key] = (result, datetime.now())
                
                return result
                
            else:
                logger.error(f"VIES API error: {response.status_code} - {response.text}")
                return VATValidationResult(
                    country_code=country_code,
                    vat_number=vat_number,
                    is_valid=False,
                    error_message=f"API error: {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            logger.error("VIES API request timeout")
            return VATValidationResult(
                country_code=country_code,
                vat_number=vat_number,
                is_valid=False,
                error_message="Request timeout - VIES service unavailable"
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"VIES API request failed: {str(e)}")
            return VATValidationResult(
                country_code=country_code,
                vat_number=vat_number,
                is_valid=False,
                error_message=f"Network error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during VAT validation: {str(e)}")
            return VATValidationResult(
                country_code=country_code,
                vat_number=vat_number,
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _parse_validation_response(self, data: Dict[str, Any], country_code: str, vat_number: str) -> VATValidationResult:
        """Parse VIES API response into VATValidationResult"""
        
        try:
            request_date = None
            if 'requestDate' in data and data['requestDate']:
                request_date = datetime.fromisoformat(data['requestDate'].replace('Z', '+00:00'))
            
            return VATValidationResult(
                country_code=country_code,
                vat_number=vat_number,
                is_valid=data.get('valid', False),
                company_name=data.get('name'),
                company_address=data.get('address'),
                request_date=request_date,
                request_identifier=data.get('requestIdentifier'),
                trader_name_match=data.get('traderNameMatch'),
                trader_address_match=data.get('traderStreetMatch')
            )
            
        except Exception as e:
            logger.error(f"Error parsing VIES response: {str(e)}")
            return VATValidationResult(
                country_code=country_code,
                vat_number=vat_number,
                is_valid=False,
                error_message=f"Response parsing error: {str(e)}"
            )
    
    def check_service_status(self) -> Dict[str, Any]:
        """Check the status of VIES service for all EU member states"""
        
        try:
            response = requests.get(
                f"{self.base_url}/check-status",
                headers={"Accept": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Status check failed: {response.status_code}",
                    "available": False
                }
                
        except Exception as e:
            logger.error(f"Error checking VIES service status: {str(e)}")
            return {
                "error": str(e),
                "available": False
            }
    
    def validate_vat_from_full_number(self, full_vat_number: str, **kwargs) -> VATValidationResult:
        """
        Validate VAT number from full format (e.g., "DE123456789")
        
        Args:
            full_vat_number: Full VAT number with country prefix
            **kwargs: Additional parameters passed to validate_vat_number
            
        Returns:
            VATValidationResult
        """
        
        if not full_vat_number or len(full_vat_number) < 4:
            return VATValidationResult(
                country_code="",
                vat_number=full_vat_number or "",
                is_valid=False,
                error_message="Invalid VAT number format"
            )
        
        country_code = full_vat_number[:2].upper()
        vat_number = full_vat_number[2:].strip()
        
        return self.validate_vat_number(country_code, vat_number, **kwargs)
    
    def is_eu_country(self, country_code: str) -> bool:
        """Check if country code is a valid EU member state"""
        
        eu_countries = {
            'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 
            'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 
            'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
        }
        
        return country_code.upper() in eu_countries
    
    def get_validation_summary(self, results: list[VATValidationResult]) -> Dict[str, Any]:
        """Generate summary statistics for a list of validation results"""
        
        if not results:
            return {"total": 0, "valid": 0, "invalid": 0, "errors": 0}
        
        valid_count = sum(1 for r in results if r.is_valid and not r.error_message)
        invalid_count = sum(1 for r in results if not r.is_valid and not r.error_message)
        error_count = sum(1 for r in results if r.error_message)
        
        return {
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "errors": error_count,
            "success_rate": (valid_count / len(results)) * 100 if results else 0
        }

# Global instance
vies_validator = VIESValidationService()