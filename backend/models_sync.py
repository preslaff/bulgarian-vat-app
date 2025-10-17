from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from database_sync import Base

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
    document_type = Column(Integer, default=1)              # 1=Invoice, 3=Credit Note
    document_number = Column(String(50))
    document_date = Column(DateTime)
    supplier_name = Column(String(200))
    supplier_vat = Column(String(15))
    
    # Amounts
    tax_base = Column(Numeric(15, 2), default=0)           # Данъчна основа
    vat_amount = Column(Numeric(15, 2), default=0)         # ДДС сума
    total_amount = Column(Numeric(15, 2), default=0)       # Field 09: For non-VAT items
    
    # Credit note fields (negative amounts)
    credit_tax_base = Column(Numeric(15, 2), default=0)    # Field 10: negative tax base
    credit_vat = Column(Numeric(15, 2), default=0)         # Field 11: negative VAT
    
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
    tax_base_20 = Column(Numeric(15, 2), default=0)        # Field 11: Tax base for 20% VAT
    vat_20 = Column(Numeric(15, 2), default=0)             # Field 12: 20% VAT amount
    
    # Other rates (if needed in future)
    tax_base_0 = Column(Numeric(15, 2), default=0)         # 0% VAT deliveries
    tax_base_exempt = Column(Numeric(15, 2), default=0)    # Exempt deliveries
    
    total_amount = Column(Numeric(15, 2), default=0)       # Total invoice amount
    
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
    
    # Declaration fields
    field_50 = Column(Numeric(15, 2), default=0)           # Sales VAT
    field_60 = Column(Numeric(15, 2), default=0)           # Purchase VAT
    field_80 = Column(Numeric(15, 2), default=0)           # Refund amount
    
    # Calculated amounts
    payment_due = Column(Numeric(15, 2), default=0)        # Amount to pay
    refund_due = Column(Numeric(15, 2), default=0)         # Amount to refund
    
    # Status tracking
    status = Column(String(20), default="DRAFT")           # DRAFT, SUBMITTED, PAID
    submission_date = Column(DateTime)                      # When submitted to NAP
    payment_deadline = Column(DateTime)                     # 14th of following month
    
    # NAP integration
    nap_submission_id = Column(String(100))                # NAP reference number
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="declarations")