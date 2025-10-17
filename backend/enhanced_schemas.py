from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Document Type Enums
class PurchaseDocumentType(int, Enum):
    INVOICE = 1
    CUSTOMS_DOCUMENT = 2
    CREDIT_NOTE = 3
    ARTICLE_15A_DOC = 5
    AGGREGATE_INVOICE = 7
    NO_TAX_CREDIT = 9
    TRIANGULAR_ART15 = 11
    TRIANGULAR_ART14 = 12
    ACQUISITIONS_ART14 = 13
    ARTICLE_126A_DOC = 23
    VAT_APP_151A_1 = 91
    VAT_APP_151A_2 = 92
    VAT_APP_151A_3 = 93
    VAT_APP_151A_4 = 94

class SalesDocumentType(int, Enum):
    DOMESTIC_INVOICE = 1
    EU_SALES = 2
    EXPORT_SALES = 3
    TRIANGULAR_SALES = 4
    DISTANCE_SELLING = 5
    INTRA_COMMUNITY = 6

# Enhanced Company Schemas
class EnhancedCompanyBase(BaseModel):
    uic: str = Field(..., min_length=9, max_length=9, description="УИК (9 digits)")
    vat_number: str = Field(..., pattern=r"^BG\d{9,10}$", description="VAT Number (BG + 9-10 digits)")
    name: str = Field(..., min_length=1, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    representative: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    is_active: bool = True
    tax_office_code: Optional[str] = Field(None, max_length=10)
    activity_code: Optional[str] = Field(None, max_length=10)
    registration_date: Optional[datetime] = None

class EnhancedCompanyCreate(EnhancedCompanyBase):
    pass

class EnhancedCompanyResponse(EnhancedCompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced Purchase Entry Schemas
class EnhancedPurchaseEntryBase(BaseModel):
    period: str = Field(..., pattern=r"^\d{6}$", description="Period in YYYYMM format")
    document_type: PurchaseDocumentType
    document_number: Optional[str] = Field(None, max_length=50)
    document_date: Optional[datetime] = None
    supplier_name: Optional[str] = Field(None, max_length=200)
    supplier_vat: Optional[str] = Field(None, pattern=r"^[A-Z]{2}\d{8,12}$")
    supplier_country: Optional[str] = Field(None, min_length=2, max_length=2)
    
    # Basic amounts
    tax_base: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    vat_amount: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    total_amount: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    credit_tax_base: Optional[Decimal] = Field(Decimal('0.00'), le=0)
    credit_vat: Optional[Decimal] = Field(Decimal('0.00'), le=0)
    
    # Enhanced fields for different document types
    customs_document_ref: Optional[str] = Field(None, max_length=100)
    customs_office: Optional[str] = Field(None, max_length=100)
    article_15a_type: Optional[int] = Field(None, ge=1, le=4)
    article_15a_details: Optional[Dict[str, Any]] = None
    aggregate_period_from: Optional[str] = Field(None, pattern=r"^\d{6}$")
    aggregate_period_to: Optional[str] = Field(None, pattern=r"^\d{6}$")
    aggregate_details: Optional[Dict[str, Any]] = None
    tax_credit_excluded: Optional[bool] = False
    exclusion_reason: Optional[str] = Field(None, max_length=200)
    triangular_operation_type: Optional[int] = Field(None, ge=11, le=13)
    intermediary_vat: Optional[str] = Field(None, pattern=r"^[A-Z]{2}\d{8,12}$")
    final_customer_vat: Optional[str] = Field(None, pattern=r"^[A-Z]{2}\d{8,12}$")
    triangular_details: Optional[Dict[str, Any]] = None
    article_126a_details: Optional[Dict[str, Any]] = None
    vat_application_type: Optional[int] = Field(None, ge=91, le=94)
    application_reference: Optional[str] = Field(None, max_length=100)
    application_details: Optional[Dict[str, Any]] = None
    vies_validated: Optional[bool] = False
    vies_validation_date: Optional[datetime] = None
    vies_company_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None

class EnhancedPurchaseEntryCreate(EnhancedPurchaseEntryBase):
    pass

class EnhancedPurchaseEntryResponse(EnhancedPurchaseEntryBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced Sales Entry Schemas
class EnhancedSalesEntryBase(BaseModel):
    period: str = Field(..., pattern=r"^\d{6}$", description="Period in YYYYMM format")
    document_type: SalesDocumentType
    document_number: Optional[str] = Field(None, max_length=50)
    document_date: Optional[datetime] = None
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_vat: Optional[str] = Field(None, pattern=r"^[A-Z]{2}\d{8,12}$")
    customer_country: Optional[str] = Field(None, min_length=2, max_length=2)
    
    # Basic VAT fields
    tax_base_20: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    vat_20: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    tax_base_0: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    tax_base_exempt: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    total_amount: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    
    # Enhanced field mapping (9-25)
    field_09: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_10: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_11: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_12: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_13: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_14: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_15: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_16: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_17: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_18: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_19: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_20: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_21: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_22: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_23: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative for corrections
    field_24: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative for corrections
    field_25: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative for corrections
    
    # EU/Triangular specific fields
    eu_distance_selling: Optional[bool] = False
    intra_community_type: Optional[str] = Field(None, max_length=10)
    triangular_sales_type: Optional[int] = None
    triangular_details: Optional[Dict[str, Any]] = None
    vies_validated: Optional[bool] = False
    vies_validation_date: Optional[datetime] = None
    vies_company_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None

class EnhancedSalesEntryCreate(EnhancedSalesEntryBase):
    pass

class EnhancedSalesEntryResponse(EnhancedSalesEntryBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced VAT Declaration Schemas
class EnhancedVATDeclarationBase(BaseModel):
    period: str = Field(..., pattern=r"^\d{6}$")
    period_type: Optional[str] = Field("MONTHLY", pattern=r"^(MONTHLY|QUARTERLY)$")
    
    # All declaration fields (9-82)
    field_09: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_10: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_11: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_12: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_13: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_14: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_15: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_16: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_17: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_18: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_19: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_20: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_21: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_22: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    field_23: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative
    field_24: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative
    field_25: Optional[Decimal] = Field(Decimal('0.00'))  # Can be negative
    
    # Fields 26-40 (reserved)
    field_26: Optional[Decimal] = Field(Decimal('0.00'))
    field_27: Optional[Decimal] = Field(Decimal('0.00'))
    field_28: Optional[Decimal] = Field(Decimal('0.00'))
    field_29: Optional[Decimal] = Field(Decimal('0.00'))
    field_30: Optional[Decimal] = Field(Decimal('0.00'))
    field_31: Optional[Decimal] = Field(Decimal('0.00'))
    field_32: Optional[Decimal] = Field(Decimal('0.00'))
    field_33: Optional[Decimal] = Field(Decimal('0.00'))
    field_34: Optional[Decimal] = Field(Decimal('0.00'))
    field_35: Optional[Decimal] = Field(Decimal('0.00'))
    field_36: Optional[Decimal] = Field(Decimal('0.00'))
    field_37: Optional[Decimal] = Field(Decimal('0.00'))
    field_38: Optional[Decimal] = Field(Decimal('0.00'))
    field_39: Optional[Decimal] = Field(Decimal('0.00'))
    field_40: Optional[Decimal] = Field(Decimal('0.00'))
    
    # Fields 41-69 (calculations)
    field_41: Optional[Decimal] = Field(Decimal('0.00'))
    field_42: Optional[Decimal] = Field(Decimal('0.00'))
    field_43: Optional[Decimal] = Field(Decimal('0.00'))
    field_44: Optional[Decimal] = Field(Decimal('0.00'))
    field_45: Optional[Decimal] = Field(Decimal('0.00'))
    field_46: Optional[Decimal] = Field(Decimal('0.00'))
    field_47: Optional[Decimal] = Field(Decimal('0.00'))
    field_48: Optional[Decimal] = Field(Decimal('0.00'))
    field_49: Optional[Decimal] = Field(Decimal('0.00'))
    field_50: Optional[Decimal] = Field(Decimal('0.00'))  # Sales VAT
    field_51: Optional[Decimal] = Field(Decimal('0.00'))
    field_52: Optional[Decimal] = Field(Decimal('0.00'))
    field_53: Optional[Decimal] = Field(Decimal('0.00'))
    field_54: Optional[Decimal] = Field(Decimal('0.00'))
    field_55: Optional[Decimal] = Field(Decimal('0.00'))
    field_56: Optional[Decimal] = Field(Decimal('0.00'))
    field_57: Optional[Decimal] = Field(Decimal('0.00'))
    field_58: Optional[Decimal] = Field(Decimal('0.00'))
    field_59: Optional[Decimal] = Field(Decimal('0.00'))
    field_60: Optional[Decimal] = Field(Decimal('0.00'))  # Purchase VAT
    field_61: Optional[Decimal] = Field(Decimal('0.00'))
    field_62: Optional[Decimal] = Field(Decimal('0.00'))
    field_63: Optional[Decimal] = Field(Decimal('0.00'))
    field_64: Optional[Decimal] = Field(Decimal('0.00'))
    field_65: Optional[Decimal] = Field(Decimal('0.00'))
    field_66: Optional[Decimal] = Field(Decimal('0.00'))
    field_67: Optional[Decimal] = Field(Decimal('0.00'))
    field_68: Optional[Decimal] = Field(Decimal('0.00'))
    field_69: Optional[Decimal] = Field(Decimal('0.00'))
    
    # Fields 70-82 (final calculations)
    field_70: Optional[Decimal] = Field(Decimal('0.00'))  # VAT due
    field_71: Optional[Decimal] = Field(Decimal('0.00'))  # VAT refund due
    field_72: Optional[Decimal] = Field(Decimal('0.00'))
    field_73: Optional[Decimal] = Field(Decimal('0.00'))
    field_74: Optional[Decimal] = Field(Decimal('0.00'))
    field_75: Optional[Decimal] = Field(Decimal('0.00'))
    field_76: Optional[Decimal] = Field(Decimal('0.00'))
    field_77: Optional[Decimal] = Field(Decimal('0.00'))
    field_78: Optional[Decimal] = Field(Decimal('0.00'))
    field_79: Optional[Decimal] = Field(Decimal('0.00'))
    field_80: Optional[Decimal] = Field(Decimal('0.00'))  # Refund amount
    field_81: Optional[Decimal] = Field(Decimal('0.00'))  # Amount to pay
    field_82: Optional[Decimal] = Field(Decimal('0.00'))  # Amount to refund
    
    # Enhanced fields
    calculation_method: Optional[str] = Field("AUTOMATIC", pattern=r"^(AUTOMATIC|MANUAL)$")
    conditional_fields: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[str]] = None
    status: Optional[str] = Field("DRAFT", pattern=r"^(DRAFT|CALCULATED|SUBMITTED|PAID|REJECTED)$")

class EnhancedVATDeclarationCreate(EnhancedVATDeclarationBase):
    pass

class EnhancedVATDeclarationResponse(EnhancedVATDeclarationBase):
    id: int
    company_id: int
    payment_due: Decimal
    refund_due: Decimal
    submission_date: Optional[datetime] = None
    payment_deadline: Optional[datetime] = None
    nap_submission_id: Optional[str] = None
    nap_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# VIES Report Schemas
class VIESReportBase(BaseModel):
    period: str = Field(..., pattern=r"^\d{6}$")
    eu_customers: Optional[List[Dict[str, Any]]] = []
    total_eu_sales: Optional[Decimal] = Field(Decimal('0.00'), ge=0)
    total_triangular_ops: Optional[Decimal] = Field(Decimal('0.00'), ge=0)

class VIESReportCreate(VIESReportBase):
    pass

class VIESReportResponse(VIESReportBase):
    id: int
    company_id: int
    generated_date: datetime
    submitted_date: Optional[datetime] = None
    vies_reference: Optional[str] = None

    class Config:
        from_attributes = True

# Document Type Mapping Schemas
class DocumentTypeMappingBase(BaseModel):
    document_type: int
    document_category: str = Field(..., pattern=r"^(PURCHASE|SALES)$")
    name_bg: str = Field(..., max_length=200)
    name_en: str = Field(..., max_length=200)
    description: Optional[str] = None
    required_fields: Optional[List[str]] = []
    validation_rules: Optional[Dict[str, Any]] = None
    calculation_rules: Optional[Dict[str, Any]] = None
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

class DocumentTypeMappingCreate(DocumentTypeMappingBase):
    pass

class DocumentTypeMappingResponse(DocumentTypeMappingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Export Log Schemas
class ExportLogBase(BaseModel):
    export_type: str = Field(..., max_length=50)
    period: Optional[str] = Field(None, pattern=r"^\d{6}$")
    export_format: str = Field(..., max_length=20)
    file_name: Optional[str] = Field(None, max_length=200)
    export_status: str = Field("PENDING", pattern=r"^(PENDING|SUCCESS|FAILED)$")
    error_message: Optional[str] = None
    external_reference: Optional[str] = Field(None, max_length=100)
    response_data: Optional[Dict[str, Any]] = None

class ExportLogCreate(ExportLogBase):
    pass

class ExportLogResponse(ExportLogBase):
    id: int
    company_id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Validation utilities
class DocumentTypeValidator:
    @staticmethod
    def validate_purchase_document_type(doc_type: int, entry_data: Dict[str, Any]) -> List[str]:
        """Validate purchase document type specific requirements"""
        errors = []
        
        if doc_type == PurchaseDocumentType.CUSTOMS_DOCUMENT:
            if not entry_data.get("customs_document_ref"):
                errors.append("Customs document reference is required for type 02")
                
        elif doc_type == PurchaseDocumentType.ARTICLE_15A_DOC:
            if not entry_data.get("article_15a_type"):
                errors.append("Article 15a type is required for type 05")
                
        elif doc_type == PurchaseDocumentType.AGGREGATE_INVOICE:
            if not entry_data.get("aggregate_period_from") or not entry_data.get("aggregate_period_to"):
                errors.append("Aggregate period range is required for type 07")
                
        elif doc_type in [PurchaseDocumentType.TRIANGULAR_ART15, 
                         PurchaseDocumentType.TRIANGULAR_ART14,
                         PurchaseDocumentType.ACQUISITIONS_ART14]:
            if not entry_data.get("triangular_operation_type"):
                errors.append("Triangular operation type is required for triangular operations")
                
        elif doc_type in [PurchaseDocumentType.VAT_APP_151A_1,
                         PurchaseDocumentType.VAT_APP_151A_2,
                         PurchaseDocumentType.VAT_APP_151A_3,
                         PurchaseDocumentType.VAT_APP_151A_4]:
            if not entry_data.get("application_reference"):
                errors.append("Application reference is required for VAT applications")
                
        return errors
    
    @staticmethod
    def validate_sales_document_type(doc_type: int, entry_data: Dict[str, Any]) -> List[str]:
        """Validate sales document type specific requirements"""
        errors = []
        
        if doc_type == SalesDocumentType.EU_SALES:
            if not entry_data.get("customer_vat"):
                errors.append("Customer VAT number is required for EU sales")
            if not entry_data.get("customer_country") or entry_data.get("customer_country") == "BG":
                errors.append("Non-Bulgarian EU country code is required for EU sales")
                
        elif doc_type == SalesDocumentType.DISTANCE_SELLING:
            if not entry_data.get("eu_distance_selling"):
                errors.append("EU distance selling flag must be set for distance selling")
                
        elif doc_type == SalesDocumentType.TRIANGULAR_SALES:
            if not entry_data.get("triangular_sales_type"):
                errors.append("Triangular sales type is required")
                
        return errors