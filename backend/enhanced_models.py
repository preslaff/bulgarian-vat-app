from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from database_sync import Base

# Document Type Constants based on NRA analysis
class PurchaseDocumentType(Enum):
    INVOICE = 1                    # 01-Фактура  
    CUSTOMS_DOCUMENT = 2           # 02-Митнически документ
    CREDIT_NOTE = 3               # 03-Протокол документ (Credit Note)
    ARTICLE_15A_DOC = 5           # 05-Документи по чл.15а (since 01.04.2020)
    AGGREGATE_INVOICE = 7         # 07-Обобщени фактури
    NO_TAX_CREDIT = 9            # 09-Документи без право на данъчен кредит
    TRIANGULAR_ART15 = 11        # 11-Триъгълни операции по чл.15
    TRIANGULAR_ART14 = 12        # 12-Триъгълни операции по чл.14
    ACQUISITIONS_ART14 = 13      # 13-Придобивания по чл.14
    ARTICLE_126A_DOC = 23        # 23-Документи по чл.126а
    VAT_APP_151A_1 = 91         # 91-Заявление ЗДДС по чл.151а, ал.1
    VAT_APP_151A_2 = 92         # 92-Заявление ЗДДС по чл.151а, ал.2
    VAT_APP_151A_3 = 93         # 93-Заявление ЗДДС по чл.151а, ал.3
    VAT_APP_151A_4 = 94         # 94-Заявление ЗДДС по чл.151а, ал.4

class SalesDocumentType(Enum):
    DOMESTIC_INVOICE = 1          # Domestic sales
    EU_SALES = 2                  # EU sales
    EXPORT_SALES = 3              # Export sales
    TRIANGULAR_SALES = 4          # Triangular operations
    DISTANCE_SELLING = 5          # Distance selling
    INTRA_COMMUNITY = 6           # Intra-community acquisitions

class VATDeclarationStatus(Enum):
    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    SUBMITTED = "SUBMITTED"
    PAID = "PAID"
    REJECTED = "REJECTED"

# Enhanced Company model (minimal changes needed)
class EnhancedCompany(Base):
    """Enhanced Company model with additional fields"""
    __tablename__ = "companies_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    uic = Column(String(20), unique=True, index=True, nullable=False)
    vat_number = Column(String(15), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    position = Column(String(100))
    representative = Column(String(100))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Additional NRA-specific fields
    tax_office_code = Column(String(10))  # Tax office code
    activity_code = Column(String(10))    # Main activity code
    registration_date = Column(DateTime)   # VAT registration date
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enhanced relationships
    purchase_entries = relationship("EnhancedPurchaseEntry", back_populates="company")
    sales_entries = relationship("EnhancedSalesEntry", back_populates="company")
    vat_declarations = relationship("EnhancedVATDeclaration", back_populates="company")
    vies_reports = relationship("VIESReport", back_populates="company")

class EnhancedPurchaseEntry(Base):
    """Enhanced Purchase Journal with support for all NRA document types"""
    __tablename__ = "purchase_entries_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies_enhanced.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)
    
    # Core document details
    document_type = Column(Integer, nullable=False)  # Using PurchaseDocumentType enum values
    document_number = Column(String(50))
    document_date = Column(DateTime)
    supplier_name = Column(String(200))
    supplier_vat = Column(String(15))
    supplier_country = Column(String(2))  # ISO country code for EU VAT
    
    # Basic amounts (existing fields)
    tax_base = Column(Numeric(15, 2), default=0)
    vat_amount = Column(Numeric(15, 2), default=0) 
    total_amount = Column(Numeric(15, 2), default=0)
    credit_tax_base = Column(Numeric(15, 2), default=0)
    credit_vat = Column(Numeric(15, 2), default=0)
    
    # Enhanced fields for different document types
    customs_document_ref = Column(String(100))        # For type 02 (Customs)
    customs_office = Column(String(100))              # For type 02
    
    article_15a_type = Column(Integer)                # For type 05 (1-4 different scenarios)
    article_15a_details = Column(JSON)                # Additional details for Art.15a
    
    aggregate_period_from = Column(String(6))         # For type 07 (Aggregate invoices)  
    aggregate_period_to = Column(String(6))           # For type 07
    aggregate_details = Column(JSON)                  # Details of aggregated invoices
    
    tax_credit_excluded = Column(Boolean, default=False)  # For type 09
    exclusion_reason = Column(String(200))            # Reason for tax credit exclusion
    
    # Triangular operations fields (types 11,12,13)
    triangular_operation_type = Column(Integer)       # 11, 12, or 13
    intermediary_vat = Column(String(15))            # VAT of intermediary
    final_customer_vat = Column(String(15))          # VAT of final customer
    triangular_details = Column(JSON)                # Additional triangular operation details
    
    # Article 126a fields (type 23)
    article_126a_details = Column(JSON)
    
    # VAT application fields (types 91-94)
    vat_application_type = Column(Integer)            # 91, 92, 93, or 94  
    application_reference = Column(String(100))      # Reference to VAT application
    application_details = Column(JSON)               # Details of VAT application
    
    # VIES related fields
    vies_validated = Column(Boolean, default=False)
    vies_validation_date = Column(DateTime)
    vies_company_name = Column(String(200))          # Company name from VIES
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("EnhancedCompany", back_populates="purchase_entries")

class EnhancedSalesEntry(Base):
    """Enhanced Sales Journal with field mapping system (9-25)"""
    __tablename__ = "sales_entries_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies_enhanced.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)
    
    # Core document details
    document_type = Column(Integer, nullable=False)  # Using SalesDocumentType enum values
    document_number = Column(String(50))
    document_date = Column(DateTime)
    customer_name = Column(String(200))
    customer_vat = Column(String(15))
    customer_country = Column(String(2))  # ISO country code
    
    # Basic VAT fields (existing)
    tax_base_20 = Column(Numeric(15, 2), default=0)
    vat_20 = Column(Numeric(15, 2), default=0)
    tax_base_0 = Column(Numeric(15, 2), default=0)
    tax_base_exempt = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    
    # Enhanced fields mapping to NRA fields 9-25
    field_09 = Column(Numeric(15, 2), default=0)   # Deliveries/services taxable at 20%
    field_10 = Column(Numeric(15, 2), default=0)   # VAT amount for field 09
    field_11 = Column(Numeric(15, 2), default=0)   # Deliveries/services taxable at 0%
    field_12 = Column(Numeric(15, 2), default=0)   # Exempt deliveries/services
    field_13 = Column(Numeric(15, 2), default=0)   # Intra-community deliveries
    field_14 = Column(Numeric(15, 2), default=0)   # Exports
    field_15 = Column(Numeric(15, 2), default=0)   # Other deliveries outside Bulgaria
    field_16 = Column(Numeric(15, 2), default=0)   # Distance sales to Bulgaria
    field_17 = Column(Numeric(15, 2), default=0)   # VAT for distance sales
    field_18 = Column(Numeric(15, 2), default=0)   # Intra-community acquisitions
    field_19 = Column(Numeric(15, 2), default=0)   # VAT for intra-community acquisitions
    field_20 = Column(Numeric(15, 2), default=0)   # Other acquisitions subject to reverse charge
    field_21 = Column(Numeric(15, 2), default=0)   # VAT for other acquisitions
    field_22 = Column(Numeric(15, 2), default=0)   # Import VAT
    field_23 = Column(Numeric(15, 2), default=0)   # Corrections of previous periods
    field_24 = Column(Numeric(15, 2), default=0)   # VAT corrections
    field_25 = Column(Numeric(15, 2), default=0)   # Other corrections
    
    # EU/Triangular operation specific fields
    eu_distance_selling = Column(Boolean, default=False)
    intra_community_type = Column(String(10))        # Type of intra-community transaction
    triangular_sales_type = Column(Integer)          # Type of triangular operation
    triangular_details = Column(JSON)
    
    # VIES related fields
    vies_validated = Column(Boolean, default=False)
    vies_validation_date = Column(DateTime)
    vies_company_name = Column(String(200))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("EnhancedCompany", back_populates="sales_entries")

class EnhancedVATDeclaration(Base):
    """Enhanced VAT Declaration with full field support (fields 1-82)"""
    __tablename__ = "vat_declarations_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies_enhanced.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)
    period_type = Column(String(10), default="MONTHLY")  # MONTHLY or QUARTERLY
    
    # Section A - Sales (Fields 9-40)
    field_09 = Column(Numeric(15, 2), default=0)  # Deliveries/services taxable at 20%
    field_10 = Column(Numeric(15, 2), default=0)  # VAT amount for field 09  
    field_11 = Column(Numeric(15, 2), default=0)  # Deliveries/services taxable at 0%
    field_12 = Column(Numeric(15, 2), default=0)  # Exempt deliveries/services
    field_13 = Column(Numeric(15, 2), default=0)  # Intra-community deliveries
    field_14 = Column(Numeric(15, 2), default=0)  # Exports
    field_15 = Column(Numeric(15, 2), default=0)  # Other deliveries outside Bulgaria
    field_16 = Column(Numeric(15, 2), default=0)  # Distance sales to Bulgaria
    field_17 = Column(Numeric(15, 2), default=0)  # VAT for distance sales
    field_18 = Column(Numeric(15, 2), default=0)  # Intra-community acquisitions
    field_19 = Column(Numeric(15, 2), default=0)  # VAT for intra-community acquisitions
    field_20 = Column(Numeric(15, 2), default=0)  # Other acquisitions subject to reverse charge
    field_21 = Column(Numeric(15, 2), default=0)  # VAT for other acquisitions
    field_22 = Column(Numeric(15, 2), default=0)  # Import VAT
    field_23 = Column(Numeric(15, 2), default=0)  # Corrections of previous periods
    field_24 = Column(Numeric(15, 2), default=0)  # VAT corrections
    field_25 = Column(Numeric(15, 2), default=0)  # Other corrections
    field_26 = Column(Numeric(15, 2), default=0)  # Reserved
    field_27 = Column(Numeric(15, 2), default=0)  # Reserved
    field_28 = Column(Numeric(15, 2), default=0)  # Reserved
    field_29 = Column(Numeric(15, 2), default=0)  # Reserved
    field_30 = Column(Numeric(15, 2), default=0)  # Reserved
    field_31 = Column(Numeric(15, 2), default=0)  # Reserved
    field_32 = Column(Numeric(15, 2), default=0)  # Reserved
    field_33 = Column(Numeric(15, 2), default=0)  # Reserved
    field_34 = Column(Numeric(15, 2), default=0)  # Reserved
    field_35 = Column(Numeric(15, 2), default=0)  # Reserved
    field_36 = Column(Numeric(15, 2), default=0)  # Reserved
    field_37 = Column(Numeric(15, 2), default=0)  # Reserved
    field_38 = Column(Numeric(15, 2), default=0)  # Reserved
    field_39 = Column(Numeric(15, 2), default=0)  # Reserved
    field_40 = Column(Numeric(15, 2), default=0)  # Reserved
    
    # Section B - Calculations (Fields 41-69)
    field_41 = Column(Numeric(15, 2), default=0)  # Total tax base
    field_42 = Column(Numeric(15, 2), default=0)  # Total VAT due
    field_43 = Column(Numeric(15, 2), default=0)  # Reserved
    field_44 = Column(Numeric(15, 2), default=0)  # Reserved
    field_45 = Column(Numeric(15, 2), default=0)  # Reserved
    field_46 = Column(Numeric(15, 2), default=0)  # Reserved
    field_47 = Column(Numeric(15, 2), default=0)  # Reserved
    field_48 = Column(Numeric(15, 2), default=0)  # Reserved
    field_49 = Column(Numeric(15, 2), default=0)  # Reserved
    field_50 = Column(Numeric(15, 2), default=0)  # Sales VAT (existing field)
    field_51 = Column(Numeric(15, 2), default=0)  # Purchase VAT deductible
    field_52 = Column(Numeric(15, 2), default=0)  # Reserved
    field_53 = Column(Numeric(15, 2), default=0)  # Reserved
    field_54 = Column(Numeric(15, 2), default=0)  # Reserved
    field_55 = Column(Numeric(15, 2), default=0)  # Reserved
    field_56 = Column(Numeric(15, 2), default=0)  # Reserved
    field_57 = Column(Numeric(15, 2), default=0)  # Reserved
    field_58 = Column(Numeric(15, 2), default=0)  # Reserved
    field_59 = Column(Numeric(15, 2), default=0)  # Reserved
    field_60 = Column(Numeric(15, 2), default=0)  # Purchase VAT (existing field)
    field_61 = Column(Numeric(15, 2), default=0)  # Reserved
    field_62 = Column(Numeric(15, 2), default=0)  # Reserved
    field_63 = Column(Numeric(15, 2), default=0)  # Reserved
    field_64 = Column(Numeric(15, 2), default=0)  # Reserved
    field_65 = Column(Numeric(15, 2), default=0)  # Reserved
    field_66 = Column(Numeric(15, 2), default=0)  # Reserved
    field_67 = Column(Numeric(15, 2), default=0)  # Reserved
    field_68 = Column(Numeric(15, 2), default=0)  # Reserved
    field_69 = Column(Numeric(15, 2), default=0)  # Reserved
    
    # Section V - Final calculations (Fields 70-82)
    field_70 = Column(Numeric(15, 2), default=0)  # VAT due to budget
    field_71 = Column(Numeric(15, 2), default=0)  # VAT refund due
    field_72 = Column(Numeric(15, 2), default=0)  # Reserved
    field_73 = Column(Numeric(15, 2), default=0)  # Reserved
    field_74 = Column(Numeric(15, 2), default=0)  # Reserved
    field_75 = Column(Numeric(15, 2), default=0)  # Reserved
    field_76 = Column(Numeric(15, 2), default=0)  # Reserved
    field_77 = Column(Numeric(15, 2), default=0)  # Reserved
    field_78 = Column(Numeric(15, 2), default=0)  # Reserved
    field_79 = Column(Numeric(15, 2), default=0)  # Reserved
    field_80 = Column(Numeric(15, 2), default=0)  # Refund amount (existing field)
    field_81 = Column(Numeric(15, 2), default=0)  # Amount to pay
    field_82 = Column(Numeric(15, 2), default=0)  # Amount to refund
    
    # Calculated totals (existing fields)
    payment_due = Column(Numeric(15, 2), default=0)
    refund_due = Column(Numeric(15, 2), default=0)
    
    # Enhanced status tracking
    status = Column(String(20), default="DRAFT")
    calculation_method = Column(String(20), default="AUTOMATIC")  # AUTOMATIC or MANUAL
    
    # Conditional logic tracking
    conditional_fields = Column(JSON)  # Store conditional field calculations
    validation_errors = Column(JSON)   # Store validation errors
    
    # Enhanced submission tracking
    submission_date = Column(DateTime)
    payment_deadline = Column(DateTime)
    nap_submission_id = Column(String(100))
    nap_response = Column(JSON)  # Store NAP response details
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("EnhancedCompany", back_populates="vat_declarations")

class VIESReport(Base):
    """VIES-specific reporting model"""
    __tablename__ = "vies_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies_enhanced.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)
    
    # VIES-specific data
    eu_customers = Column(JSON)           # List of EU customers with transactions
    total_eu_sales = Column(Numeric(15, 2), default=0)
    total_triangular_ops = Column(Numeric(15, 2), default=0)
    
    # Report status
    generated_date = Column(DateTime, default=datetime.utcnow)
    submitted_date = Column(DateTime)
    vies_reference = Column(String(100))
    
    # Relationships
    company = relationship("EnhancedCompany", back_populates="vies_reports")

class DocumentTypeMapping(Base):
    """Document type mapping and validation rules"""
    __tablename__ = "document_type_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(Integer, nullable=False)
    document_category = Column(String(20))  # PURCHASE or SALES
    name_bg = Column(String(200))           # Bulgarian name
    name_en = Column(String(200))           # English name
    description = Column(Text)              # Description of document type
    
    # Validation rules
    required_fields = Column(JSON)          # List of required fields
    validation_rules = Column(JSON)        # Validation rules
    calculation_rules = Column(JSON)       # Field calculation rules
    
    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime)       # When this document type became effective
    effective_to = Column(DateTime)         # When this document type was discontinued
    
    created_at = Column(DateTime, default=datetime.utcnow)

class ExportLog(Base):
    """Track exports to NAP and other systems"""
    __tablename__ = "export_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies_enhanced.id"), nullable=False)
    export_type = Column(String(50))        # DECLARATION, VIES_REPORT, etc.
    period = Column(String(6))              # Period being exported
    
    # Export details
    export_format = Column(String(20))      # XML, JSON, etc.
    file_name = Column(String(200))         # Generated file name
    file_path = Column(String(500))         # Path to exported file
    file_size = Column(Integer)             # File size in bytes
    
    # Status tracking
    export_status = Column(String(20), default="PENDING")  # PENDING, SUCCESS, FAILED
    error_message = Column(Text)            # Error message if failed
    
    # External system response
    external_reference = Column(String(100))  # Reference from external system
    response_data = Column(JSON)            # Response from external system
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships  
    company = relationship("EnhancedCompany")