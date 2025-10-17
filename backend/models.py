from sqlalchemy import Column, Integer, String, Decimal, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class Company(Base):
    """Company/Entity model (Задължено лице)"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    uic = Column(String(20), unique=True, index=True, nullable=False)  # УИК: 206450255
    vat_number = Column(String(15), unique=True, nullable=False)       # BG206450255
    name = Column(String(200), nullable=False)                         # БЯЛ ДЕН ЕООД  
    position = Column(String(100))                                     # Управител
    representative = Column(String(100))                               # СТОЯН ИВАНОВ ВИНОВ
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_journals = relationship("PurchaseJournal", back_populates="company")
    sales_journals = relationship("SalesJournal", back_populates="company")  
    declarations = relationship("VATDeclaration", back_populates="company")

class PurchaseJournal(Base):
    """Purchase Journal model (Дневник на покупките)"""
    __tablename__ = "purchase_journals"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)  # YYYYMM format: 202103
    
    # Document details
    document_type = Column(Integer, default=1)              # 1=Invoice, 3=Credit Note (Кредитно известие)
    document_number = Column(String(50))
    document_date = Column(DateTime)
    supplier_name = Column(String(200))
    supplier_vat = Column(String(15))
    
    # Amounts
    tax_base = Column(Decimal(15, 2), default=0)           # Данъчна основа
    vat_amount = Column(Decimal(15, 2), default=0)         # ДДС сума
    total_amount = Column(Decimal(15, 2), default=0)       # Field 09: For non-VAT items (ДО + ДДС)
    
    # Credit note fields (negative amounts)
    credit_tax_base = Column(Decimal(15, 2), default=0)    # Field 10: negative tax base
    credit_vat = Column(Decimal(15, 2), default=0)         # Field 11: negative VAT
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="purchase_journals")

class SalesJournal(Base):
    """Sales Journal model (Дневник за продажбите)"""
    __tablename__ = "sales_journals"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)  # YYYYMM format
    
    # Document details
    document_type = Column(Integer, default=1)              # 1=Invoice
    document_number = Column(String(50))
    document_date = Column(DateTime)
    customer_name = Column(String(200))
    customer_vat = Column(String(15))
    
    # VAT amounts
    tax_base_20 = Column(Decimal(15, 2), default=0)        # Field 11: Tax base for 20% VAT
    vat_20 = Column(Decimal(15, 2), default=0)             # Field 12: 20% VAT amount
    
    # Other rates (if needed in future)
    tax_base_0 = Column(Decimal(15, 2), default=0)         # 0% VAT deliveries
    tax_base_exempt = Column(Decimal(15, 2), default=0)    # Exempt deliveries
    
    total_amount = Column(Decimal(15, 2), default=0)       # Total invoice amount
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="sales_journals")

class VATDeclaration(Base):
    """VAT Declaration model (Справка-декларация по ЗДДС)"""
    __tablename__ = "vat_declarations"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period = Column(String(6), nullable=False, index=True)  # YYYYMM
    
    # Declaration fields (based on original form structure)
    field_50 = Column(Decimal(15, 2), default=0)           # Sales VAT (ДДС от продажби)
    field_60 = Column(Decimal(15, 2), default=0)           # Purchase VAT (ДДС от покупки)  
    field_80 = Column(Decimal(15, 2), default=0)           # Refund amount (Възстановяване)
    
    # Calculated amounts
    payment_due = Column(Decimal(15, 2), default=0)        # Amount to pay (Field 50 - Field 60)
    refund_due = Column(Decimal(15, 2), default=0)         # Amount to refund (Field 60 - Field 50)
    
    # Status tracking
    status = Column(String(20), default="DRAFT")           # DRAFT, SUBMITTED, PAID, REFUNDED
    submission_date = Column(DateTime)                      # When submitted to NAP
    payment_deadline = Column(DateTime)                     # 14th of following month
    
    # NAP integration
    nap_submission_id = Column(String(100))                # NAP reference number
    nap_status = Column(String(50))                        # NAP processing status
    
    # Generated XML/files
    declaration_xml = Column(Text)                          # Generated XML for NAP
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="declarations")

class AuditLog(Base):
    """Audit log for tracking changes"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100))                          # User identifier
    action = Column(String(100), nullable=False)           # CREATE, UPDATE, DELETE, SUBMIT
    entity_type = Column(String(50), nullable=False)       # Company, Purchase, Sales, Declaration
    entity_id = Column(Integer, nullable=False)
    old_values = Column(Text)                              # JSON of old values
    new_values = Column(Text)                              # JSON of new values  
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)