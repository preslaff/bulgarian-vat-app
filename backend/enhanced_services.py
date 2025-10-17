from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from enhanced_models import (
    EnhancedCompany, EnhancedPurchaseEntry, EnhancedSalesEntry, 
    EnhancedVATDeclaration, VIESReport, DocumentTypeMapping, ExportLog,
    PurchaseDocumentType, SalesDocumentType
)
from enhanced_schemas import (
    EnhancedCompanyCreate, EnhancedPurchaseEntryCreate, EnhancedSalesEntryCreate,
    EnhancedVATDeclarationCreate, VIESReportCreate, DocumentTypeValidator
)
from vies_validation_service import VIESValidationService

logger = logging.getLogger(__name__)

class EnhancedCompanyService:
    """Enhanced company service with additional NRA features"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def create_company(self, company_data: EnhancedCompanyCreate) -> EnhancedCompany:
        """Create a new enhanced company with validation"""
        
        # Check if UIC already exists
        existing_company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_data.uic
        ).first()
        if existing_company:
            raise ValueError(f"Company with UIC {company_data.uic} already exists")
        
        # Check if VAT number already exists
        existing_vat = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.vat_number == company_data.vat_number
        ).first()
        if existing_vat:
            raise ValueError(f"Company with VAT {company_data.vat_number} already exists")
            
        # Create company
        db_company = EnhancedCompany(**company_data.dict())
        self.db.add(db_company)
        self.db.commit()
        self.db.refresh(db_company)
        
        logger.info(f"Created enhanced company: {db_company.name} (UIC: {db_company.uic})")
        return db_company
        
    def get_company(self, uic: str) -> Optional[EnhancedCompany]:
        """Get company by UIC"""
        return self.db.query(EnhancedCompany).filter(EnhancedCompany.uic == uic).first()
        
    def list_companies(self, active_only: bool = True) -> List[EnhancedCompany]:
        """List all companies"""
        query = self.db.query(EnhancedCompany)
        if active_only:
            query = query.filter(EnhancedCompany.is_active == True)
        return query.all()

class EnhancedPurchaseService:
    """Enhanced purchase service supporting all NRA document types"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vies_service = VIESValidationService()
        
    def create_purchase_entry(self, company_uic: str, entry_data: EnhancedPurchaseEntryCreate) -> EnhancedPurchaseEntry:
        """Create purchase entry with document type validation"""
        
        # Get company
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        # Validate document type specific requirements
        validation_errors = DocumentTypeValidator.validate_purchase_document_type(
            entry_data.document_type.value, entry_data.dict()
        )
        if validation_errors:
            raise ValueError(f"Validation errors: {', '.join(validation_errors)}")
            
        # Auto-validate EU VAT numbers if present
        vies_data = {}
        if entry_data.supplier_vat and entry_data.supplier_country and entry_data.supplier_country != "BG":
            try:
                country_code = entry_data.supplier_country
                vat_number = entry_data.supplier_vat[2:]  # Remove country prefix
                
                vies_result = self.vies_service.validate_vat_number(
                    country_code=country_code,
                    vat_number=vat_number,
                    requester_country_code="BG",
                    requester_vat=company.vat_number
                )
                
                if vies_result.is_valid:
                    vies_data = {
                        'vies_validated': True,
                        'vies_validation_date': datetime.utcnow(),
                        'vies_company_name': vies_result.company_name or entry_data.supplier_name
                    }
                    logger.info(f"VIES validation successful for {entry_data.supplier_vat}")
                else:
                    logger.warning(f"VIES validation failed for {entry_data.supplier_vat}: {vies_result.error_message}")
                    
            except Exception as e:
                logger.error(f"VIES validation error: {str(e)}")
                
        # Create entry
        entry_dict = entry_data.dict()
        entry_dict.update(vies_data)
        entry_dict['company_id'] = company.id
        
        db_entry = EnhancedPurchaseEntry(**entry_dict)
        self.db.add(db_entry)
        self.db.commit()
        self.db.refresh(db_entry)
        
        logger.info(f"Created purchase entry type {entry_data.document_type.value} for company {company_uic}")
        return db_entry
        
    def get_purchases(self, company_uic: str, period: str, document_type: Optional[int] = None) -> List[EnhancedPurchaseEntry]:
        """Get purchase entries with optional document type filter"""
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        query = self.db.query(EnhancedPurchaseEntry).filter(
            and_(
                EnhancedPurchaseEntry.company_id == company.id,
                EnhancedPurchaseEntry.period == period
            )
        )
        
        if document_type:
            query = query.filter(EnhancedPurchaseEntry.document_type == document_type)
            
        return query.all()
        
    def get_purchase_summary_by_type(self, company_uic: str, period: str) -> Dict[int, Dict[str, Any]]:
        """Get purchase summary grouped by document type"""
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        results = self.db.query(
            EnhancedPurchaseEntry.document_type,
            func.count(EnhancedPurchaseEntry.id).label('count'),
            func.sum(EnhancedPurchaseEntry.tax_base).label('total_tax_base'),
            func.sum(EnhancedPurchaseEntry.vat_amount).label('total_vat'),
            func.sum(EnhancedPurchaseEntry.total_amount).label('total_amount')
        ).filter(
            and_(
                EnhancedPurchaseEntry.company_id == company.id,
                EnhancedPurchaseEntry.period == period
            )
        ).group_by(EnhancedPurchaseEntry.document_type).all()
        
        summary = {}
        for result in results:
            doc_type = PurchaseDocumentType(result.document_type)
            summary[result.document_type] = {
                'document_type': doc_type.name,
                'count': result.count,
                'total_tax_base': float(result.total_tax_base or 0),
                'total_vat': float(result.total_vat or 0),
                'total_amount': float(result.total_amount or 0)
            }
            
        return summary

class EnhancedSalesService:
    """Enhanced sales service with field mapping system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vies_service = VIESValidationService()
        
    def create_sales_entry(self, company_uic: str, entry_data: EnhancedSalesEntryCreate) -> EnhancedSalesEntry:
        """Create sales entry with field mapping validation"""
        
        # Get company
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        # Validate document type specific requirements
        validation_errors = DocumentTypeValidator.validate_sales_document_type(
            entry_data.document_type.value, entry_data.dict()
        )
        if validation_errors:
            raise ValueError(f"Validation errors: {', '.join(validation_errors)}")
            
        # Auto-validate EU VAT numbers if present
        vies_data = {}
        if entry_data.customer_vat and entry_data.customer_country and entry_data.customer_country != "BG":
            try:
                country_code = entry_data.customer_country
                vat_number = entry_data.customer_vat[2:]  # Remove country prefix
                
                vies_result = self.vies_service.validate_vat_number(
                    country_code=country_code,
                    vat_number=vat_number,
                    requester_country_code="BG",
                    requester_vat=company.vat_number
                )
                
                if vies_result.is_valid:
                    vies_data = {
                        'vies_validated': True,
                        'vies_validation_date': datetime.utcnow(),
                        'vies_company_name': vies_result.company_name or entry_data.customer_name
                    }
                    logger.info(f"VIES validation successful for {entry_data.customer_vat}")
                    
            except Exception as e:
                logger.error(f"VIES validation error: {str(e)}")
                
        # Create entry with field mapping
        entry_dict = entry_data.dict()
        entry_dict.update(vies_data)
        entry_dict['company_id'] = company.id
        
        db_entry = EnhancedSalesEntry(**entry_dict)
        self.db.add(db_entry)
        self.db.commit()
        self.db.refresh(db_entry)
        
        logger.info(f"Created sales entry type {entry_data.document_type.value} for company {company_uic}")
        return db_entry
        
    def get_sales(self, company_uic: str, period: str, document_type: Optional[int] = None) -> List[EnhancedSalesEntry]:
        """Get sales entries with optional document type filter"""
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        query = self.db.query(EnhancedSalesEntry).filter(
            and_(
                EnhancedSalesEntry.company_id == company.id,
                EnhancedSalesEntry.period == period
            )
        )
        
        if document_type:
            query = query.filter(EnhancedSalesEntry.document_type == document_type)
            
        return query.all()
        
    def calculate_field_totals(self, company_uic: str, period: str) -> Dict[str, Decimal]:
        """Calculate totals for all declaration fields (9-25)"""
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        entries = self.db.query(EnhancedSalesEntry).filter(
            and_(
                EnhancedSalesEntry.company_id == company.id,
                EnhancedSalesEntry.period == period
            )
        ).all()
        
        field_totals = {}
        for field_num in range(9, 26):  # Fields 9-25
            field_name = f'field_{field_num:02d}'
            total = sum(getattr(entry, field_name, Decimal('0.00')) or Decimal('0.00') for entry in entries)
            field_totals[field_name] = total
            
        return field_totals

class EnhancedVATDeclarationService:
    """Enhanced VAT declaration service with full field support"""
    
    def __init__(self, db: Session):
        self.db = db
        self.purchase_service = EnhancedPurchaseService(db)
        self.sales_service = EnhancedSalesService(db)
        
    def generate_declaration(self, company_uic: str, period: str) -> EnhancedVATDeclaration:
        """Generate VAT declaration with automatic field calculations"""
        
        # Get company
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        # Check if declaration already exists
        existing = self.db.query(EnhancedVATDeclaration).filter(
            and_(
                EnhancedVATDeclaration.company_id == company.id,
                EnhancedVATDeclaration.period == period
            )
        ).first()
        
        if existing:
            raise ValueError(f"Declaration for period {period} already exists")
            
        # Calculate sales field totals
        sales_totals = self.sales_service.calculate_field_totals(company_uic, period)
        
        # Calculate purchase totals
        purchase_entries = self.purchase_service.get_purchases(company_uic, period)
        total_purchase_vat = sum(
            (entry.vat_amount or Decimal('0.00')) - (entry.credit_vat or Decimal('0.00'))
            for entry in purchase_entries
            if not entry.tax_credit_excluded
        )
        
        # Create declaration with calculated fields
        declaration_data = {
            'company_id': company.id,
            'period': period,
            'calculation_method': 'AUTOMATIC',
            'status': 'CALCULATED'
        }
        
        # Add sales field totals
        declaration_data.update(sales_totals)
        
        # Calculate key fields
        declaration_data['field_50'] = sales_totals.get('field_10', Decimal('0.00'))  # Sales VAT
        declaration_data['field_60'] = total_purchase_vat  # Purchase VAT
        
        # Calculate final amounts (fields 70-82)
        sales_vat = declaration_data['field_50']
        purchase_vat = declaration_data['field_60']
        
        if sales_vat >= purchase_vat:
            # VAT to pay
            declaration_data['field_70'] = sales_vat - purchase_vat
            declaration_data['field_81'] = declaration_data['field_70']
            declaration_data['payment_due'] = declaration_data['field_70']
        else:
            # VAT refund
            declaration_data['field_71'] = purchase_vat - sales_vat
            declaration_data['field_82'] = declaration_data['field_71']
            declaration_data['refund_due'] = declaration_data['field_71']
            
        # Set payment deadline (14th of following month)
        year = int(period[:4])
        month = int(period[4:6])
        if month == 12:
            deadline_year = year + 1
            deadline_month = 1
        else:
            deadline_year = year
            deadline_month = month + 1
        declaration_data['payment_deadline'] = datetime(deadline_year, deadline_month, 14)
        
        # Create declaration
        db_declaration = EnhancedVATDeclaration(**declaration_data)
        self.db.add(db_declaration)
        self.db.commit()
        self.db.refresh(db_declaration)
        
        logger.info(f"Generated VAT declaration for company {company_uic}, period {period}")
        return db_declaration
        
    def validate_declaration(self, declaration_id: int) -> List[str]:
        """Validate declaration according to NRA rules"""
        declaration = self.db.query(EnhancedVATDeclaration).filter(
            EnhancedVATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")
            
        validation_errors = []
        
        # Validate field 42 calculation (if field 42 > 0.00 and field 33 is per Art. 73, par. 5)
        if declaration.field_42 > 0:
            if declaration.field_33 and declaration.field_33 > 0:
                # Art. 73, par. 5 validation logic
                validation_errors.append("Field 33 validation required per Art. 73, par. 5")
                
        # Validate sections A and B totals
        section_a_total = (declaration.field_20 or 0) + (declaration.field_40 or 0)
        if section_a_total < 0:
            if not (declaration.field_70 and declaration.field_71):
                validation_errors.append("Fields 70 and 71 required when (field 20 - field 40) >= 0.00")
                
        # Validate conditional field logic according to NRA requirements
        if declaration.field_70 > 0 and declaration.field_71 > 0:
            validation_errors.append("Both field 70 and 71 cannot have positive values")
            
        return validation_errors

class EnhancedVIESService:
    """Enhanced VIES service with reporting capabilities"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def generate_vies_report(self, company_uic: str, period: str) -> VIESReport:
        """Generate VIES report for EU transactions"""
        
        # Get company
        company = self.db.query(EnhancedCompany).filter(
            EnhancedCompany.uic == company_uic
        ).first()
        if not company:
            raise ValueError(f"Company with UIC {company_uic} not found")
            
        # Get EU sales entries
        eu_sales = self.db.query(EnhancedSalesEntry).filter(
            and_(
                EnhancedSalesEntry.company_id == company.id,
                EnhancedSalesEntry.period == period,
                EnhancedSalesEntry.document_type.in_([
                    SalesDocumentType.EU_SALES.value,
                    SalesDocumentType.TRIANGULAR_SALES.value,
                    SalesDocumentType.DISTANCE_SELLING.value
                ])
            )
        ).all()
        
        # Calculate totals
        total_eu_sales = sum(entry.field_13 or Decimal('0.00') for entry in eu_sales)
        total_triangular = sum(
            entry.field_13 or Decimal('0.00') for entry in eu_sales
            if entry.document_type == SalesDocumentType.TRIANGULAR_SALES.value
        )
        
        # Group by customer
        eu_customers = {}
        for entry in eu_sales:
            if entry.customer_vat and entry.customer_country:
                key = f"{entry.customer_country}_{entry.customer_vat}"
                if key not in eu_customers:
                    eu_customers[key] = {
                        'country_code': entry.customer_country,
                        'vat_number': entry.customer_vat,
                        'company_name': entry.customer_name or entry.vies_company_name,
                        'total_amount': Decimal('0.00'),
                        'transaction_count': 0
                    }
                eu_customers[key]['total_amount'] += entry.field_13 or Decimal('0.00')
                eu_customers[key]['transaction_count'] += 1
                
        # Create VIES report
        report_data = {
            'company_id': company.id,
            'period': period,
            'eu_customers': list(eu_customers.values()),
            'total_eu_sales': total_eu_sales,
            'total_triangular_ops': total_triangular
        }
        
        db_report = VIESReport(**report_data)
        self.db.add(db_report)
        self.db.commit()
        self.db.refresh(db_report)
        
        logger.info(f"Generated VIES report for company {company_uic}, period {period}")
        return db_report

class DocumentTypeMappingService:
    """Service for managing document type mappings and validation rules"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def initialize_default_mappings(self):
        """Initialize default document type mappings based on NRA analysis"""
        
        purchase_mappings = [
            {
                'document_type': 1, 'document_category': 'PURCHASE',
                'name_bg': 'Фактура', 'name_en': 'Invoice',
                'description': 'Standard invoice for purchases',
                'required_fields': ['supplier_name', 'tax_base', 'vat_amount'],
                'is_active': True, 'effective_from': datetime(2020, 1, 1)
            },
            {
                'document_type': 2, 'document_category': 'PURCHASE',
                'name_bg': 'Митнически документ', 'name_en': 'Customs Document',
                'description': 'Customs import document',
                'required_fields': ['customs_document_ref', 'customs_office'],
                'is_active': True, 'effective_from': datetime(2020, 1, 1)
            },
            {
                'document_type': 5, 'document_category': 'PURCHASE',
                'name_bg': 'Документи по чл.15а', 'name_en': 'Article 15a Documents',
                'description': 'Documents per Article 15a (since 01.04.2020)',
                'required_fields': ['article_15a_type', 'article_15a_details'],
                'is_active': True, 'effective_from': datetime(2020, 4, 1)
            },
            # Add all other document types...
        ]
        
        for mapping_data in purchase_mappings:
            existing = self.db.query(DocumentTypeMapping).filter(
                and_(
                    DocumentTypeMapping.document_type == mapping_data['document_type'],
                    DocumentTypeMapping.document_category == mapping_data['document_category']
                )
            ).first()
            
            if not existing:
                db_mapping = DocumentTypeMapping(**mapping_data)
                self.db.add(db_mapping)
                
        self.db.commit()
        logger.info("Initialized default document type mappings")

class ExportService:
    """Service for exporting data to NAP and other formats"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def export_vat_declaration(self, declaration_id: int, export_format: str = "XML") -> ExportLog:
        """Export VAT declaration to NAP format"""
        
        declaration = self.db.query(EnhancedVATDeclaration).filter(
            EnhancedVATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")
            
        # Create export log entry
        export_log = ExportLog(
            company_id=declaration.company_id,
            export_type="VAT_DECLARATION",
            period=declaration.period,
            export_format=export_format,
            export_status="PENDING"
        )
        
        try:
            # Generate export file (implementation depends on NAP specifications)
            file_name = f"vat_declaration_{declaration.company.uic}_{declaration.period}.xml"
            
            # This would contain the actual NAP XML generation logic
            export_data = self._generate_nap_xml(declaration)
            
            # Save file (implementation specific)
            file_path = f"/exports/{file_name}"
            # with open(file_path, 'w') as f:
            #     f.write(export_data)
            
            export_log.file_name = file_name
            export_log.file_path = file_path
            export_log.export_status = "SUCCESS"
            export_log.completed_at = datetime.utcnow()
            
        except Exception as e:
            export_log.export_status = "FAILED"
            export_log.error_message = str(e)
            logger.error(f"Export failed: {str(e)}")
            
        self.db.add(export_log)
        self.db.commit()
        self.db.refresh(export_log)
        
        return export_log
        
    def _generate_nap_xml(self, declaration: EnhancedVATDeclaration) -> str:
        """Generate NAP-compatible XML (placeholder implementation)"""
        # This would contain the actual XML generation according to NAP specifications
        xml_template = f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <VATDeclaration>
            <CompanyUIC>{declaration.company.uic}</CompanyUIC>
            <Period>{declaration.period}</Period>
            <Field50>{declaration.field_50}</Field50>
            <Field60>{declaration.field_60}</Field60>
            <!-- Add all other fields -->
        </VATDeclaration>
        """
        return xml_template