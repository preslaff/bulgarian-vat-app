from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ============================================================================
# COMPANY SCHEMAS (Служебни функции - Задължено лице)
# ============================================================================

class CompanyBase(BaseModel):
    uic: str = Field(..., description="ЕИК (Единен идентификационен код)", example="206450255")
    name: str = Field(..., description="Company name", example="БЯЛ ДЕН ЕООД")
    position: Optional[str] = Field(None, description="Position", example="Управител")
    representative: Optional[str] = Field(None, description="Representative", example="СТОЯН ИВАНОВ ВИНОВ")
    address: Optional[str] = None

class CompanyCreate(CompanyBase):
    vat_number: str = Field(..., description="VAT number", example="BG206450255")
    is_active: bool = Field(True, description="Company is active")
    
    @validator('uic')
    def validate_uic(cls, v):
        """Validate Bulgarian EIK format"""
        if not v or not v.isdigit() or len(v) != 9:
            raise ValueError("ЕИК трябва да бъде 9 цифри")
        return v

class CompanyResponse(CompanyBase):
    id: int
    vat_number: str = Field(..., description="VAT number", example="BG206450255")
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# PURCHASE JOURNAL SCHEMAS (Дневник на покупките)
# ============================================================================

class PurchaseJournalBase(BaseModel):
    period: str = Field(..., description="Period in YYYYMM format", example="202103")
    document_type: int = Field(1, description="1=Invoice, 3=Credit Note")
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    supplier_name: Optional[str] = None
    supplier_vat: Optional[str] = None
    
    # Regular amounts
    tax_base: Optional[Decimal] = Field(0, ge=0, description="Tax base amount")
    vat_amount: Optional[Decimal] = Field(0, ge=0, description="VAT amount")
    total_amount: Optional[Decimal] = Field(0, ge=0, description="Field 09: Total for non-VAT items")
    
    # Credit note amounts (negative)
    credit_tax_base: Optional[Decimal] = Field(0, le=0, description="Field 10: Negative tax base")
    credit_vat: Optional[Decimal] = Field(0, le=0, description="Field 11: Negative VAT")
    
    notes: Optional[str] = None

class PurchaseJournalCreate(PurchaseJournalBase):
    @validator('period')
    def validate_period(cls, v):
        """Validate YYYYMM period format"""
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Некоректна година в полето Период - използвайте YYYYMM формат")
        
        year = int(v[:4])
        month = int(v[4:])
        
        if year < 2000 or year > 2030:
            raise ValueError("Невалидна година")
        if month < 1 or month > 12:
            raise ValueError("Невалиден месец")
        
        return v
    
    @validator('document_type')
    def validate_document_type(cls, v):
        if v not in [1, 3]:  # 1=Invoice, 3=Credit Note
            raise ValueError("Document type must be 1 (Invoice) or 3 (Credit Note)")
        return v

class PurchaseJournalResponse(PurchaseJournalBase):
    id: int
    company_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# SALES JOURNAL SCHEMAS (Дневник за продажбите)
# ============================================================================

class SalesJournalBase(BaseModel):
    period: str = Field(..., description="Period in YYYYMM format", example="202103")
    document_type: int = Field(1, description="1=Invoice")
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_vat: Optional[str] = None
    
    # VAT calculations
    tax_base_20: Decimal = Field(0, ge=0, description="Field 11: Tax base for 20% VAT")
    vat_20: Decimal = Field(0, ge=0, description="Field 12: 20% VAT amount")
    
    tax_base_0: Optional[Decimal] = Field(0, ge=0, description="0% VAT deliveries")
    tax_base_exempt: Optional[Decimal] = Field(0, ge=0, description="Exempt deliveries")
    total_amount: Optional[Decimal] = Field(0, ge=0, description="Total invoice amount")
    
    notes: Optional[str] = None

class SalesJournalCreate(SalesJournalBase):
    @validator('period')
    def validate_period(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Period must be YYYYMM format")
        return v
    
    @validator('vat_20', always=True)
    def calculate_vat_20(cls, v, values):
        """Auto-calculate 20% VAT if not provided"""
        if 'tax_base_20' in values and values['tax_base_20']:
            calculated_vat = values['tax_base_20'] * Decimal('0.20')
            return v if v > 0 else calculated_vat
        return v

class SalesJournalResponse(SalesJournalBase):
    id: int
    company_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# VAT DECLARATION SCHEMAS (Справка-декларация по ЗДДС)
# ============================================================================

class DeclarationBase(BaseModel):
    period: str = Field(..., description="Period in YYYYMM format")
    field_50: Decimal = Field(0, description="Sales VAT (ДДС от продажби)")
    field_60: Decimal = Field(0, description="Purchase VAT (ДДС от покупки)")
    field_80: Decimal = Field(0, description="Refund amount (Възстановяване)")

class DeclarationGenerate(BaseModel):
    period: str = Field(..., description="Period to generate declaration for")
    
    @validator('period')
    def validate_period(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Некоректна година в полето Период")
        return v

class DeclarationResponse(DeclarationBase):
    id: int
    company_id: int
    payment_due: Decimal
    refund_due: Decimal
    status: str
    payment_deadline: Optional[datetime]
    submission_date: Optional[datetime]
    nap_submission_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# VAT CALCULATION SCHEMAS
# ============================================================================

class VATCalculationRequest(BaseModel):
    tax_base: Decimal = Field(..., ge=0, description="Tax base amount")
    vat_rate: Decimal = Field(0.20, ge=0, le=1, description="VAT rate (default 20%)")

class VATCalculationResponse(BaseModel):
    tax_base: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount: Decimal

class PaymentDeadlineResponse(BaseModel):
    period: str
    deadline: datetime
    business_days_remaining: int
    bank_iban: str = "BG88 BNBG 9661 8000 1950 01"  # NAP account

# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None

class ValidationError(BaseModel):
    field: str
    message: str
    code: str

# ============================================================================
# API RESPONSE WRAPPERS
# ============================================================================

class ListResponse(BaseModel):
    items: List[dict]
    total: int
    page: int = 1
    page_size: int = 50

class StatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None