from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging

# Database URL - using SQLite for simplicity (can be changed to PostgreSQL/MySQL)
DATABASE_URL = "sqlite:///./enhanced_vat_system.db"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
    poolclass=StaticPool,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_enhanced_db():
    """Dependency to get database session for enhanced models"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_enhanced_tables():
    """Create all enhanced tables"""
    try:
        # Import all models to ensure they're registered with Base
        from enhanced_models import (
            EnhancedCompany, EnhancedPurchaseEntry, EnhancedSalesEntry,
            EnhancedVATDeclaration, VIESReport, DocumentTypeMapping, ExportLog
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Enhanced database tables created successfully")
        
        # Initialize default document type mappings after tables are created
        try:
            from enhanced_services import DocumentTypeMappingService
            db = SessionLocal()
            try:
                mapping_service = DocumentTypeMappingService(db)
                mapping_service.initialize_default_mappings()
            finally:
                db.close()
        except Exception as mapping_error:
            logger.warning(f"Could not initialize document mappings: {str(mapping_error)}")
            
    except Exception as e:
        logger.error(f"Error creating enhanced tables: {str(e)}")
        raise

def migrate_existing_data():
    """Migrate data from existing models to enhanced models"""
    from models_sync import Company, PurchaseJournal, SalesJournal, VATDeclaration
    from enhanced_models import EnhancedCompany, EnhancedPurchaseEntry, EnhancedSalesEntry, EnhancedVATDeclaration
    from database_sync import SessionLocal as OldSessionLocal
    
    old_db = OldSessionLocal()
    new_db = SessionLocal()
    
    try:
        logger.info("Starting data migration...")
        
        # Migrate companies
        old_companies = old_db.query(Company).all()
        company_mapping = {}
        
        for old_company in old_companies:
            # Check if already migrated
            existing = new_db.query(EnhancedCompany).filter(
                EnhancedCompany.uic == old_company.uic
            ).first()
            
            if not existing:
                new_company = EnhancedCompany(
                    uic=old_company.uic,
                    vat_number=old_company.vat_number,
                    name=old_company.name,
                    position=old_company.position,
                    representative=old_company.representative,
                    address=old_company.address,
                    is_active=old_company.is_active,
                    created_at=old_company.created_at,
                    updated_at=old_company.updated_at
                )
                new_db.add(new_company)
                new_db.flush()  # Get the ID
                company_mapping[old_company.id] = new_company.id
            else:
                company_mapping[old_company.id] = existing.id
        
        new_db.commit()
        logger.info(f"Migrated {len(old_companies)} companies")
        
        # Migrate purchase journals
        old_purchases = old_db.query(PurchaseJournal).all()
        for old_purchase in old_purchases:
            new_company_id = company_mapping.get(old_purchase.company_id)
            if new_company_id:
                # Check if already migrated
                existing = new_db.query(EnhancedPurchaseEntry).filter(
                    EnhancedPurchaseEntry.company_id == new_company_id,
                    EnhancedPurchaseEntry.period == old_purchase.period,
                    EnhancedPurchaseEntry.document_number == old_purchase.document_number
                ).first()
                
                if not existing:
                    new_purchase = EnhancedPurchaseEntry(
                        company_id=new_company_id,
                        period=old_purchase.period,
                        document_type=old_purchase.document_type,
                        document_number=old_purchase.document_number,
                        document_date=old_purchase.document_date,
                        supplier_name=old_purchase.supplier_name,
                        supplier_vat=old_purchase.supplier_vat,
                        tax_base=old_purchase.tax_base,
                        vat_amount=old_purchase.vat_amount,
                        total_amount=old_purchase.total_amount,
                        credit_tax_base=old_purchase.credit_tax_base,
                        credit_vat=old_purchase.credit_vat,
                        notes=old_purchase.notes,
                        created_at=old_purchase.created_at
                    )
                    new_db.add(new_purchase)
        
        new_db.commit()
        logger.info(f"Migrated {len(old_purchases)} purchase entries")
        
        # Migrate sales journals
        old_sales = old_db.query(SalesJournal).all()
        for old_sale in old_sales:
            new_company_id = company_mapping.get(old_sale.company_id)
            if new_company_id:
                # Check if already migrated
                existing = new_db.query(EnhancedSalesEntry).filter(
                    EnhancedSalesEntry.company_id == new_company_id,
                    EnhancedSalesEntry.period == old_sale.period,
                    EnhancedSalesEntry.document_number == old_sale.document_number
                ).first()
                
                if not existing:
                    new_sale = EnhancedSalesEntry(
                        company_id=new_company_id,
                        period=old_sale.period,
                        document_type=1,  # Default to domestic invoice
                        document_number=old_sale.document_number,
                        document_date=old_sale.document_date,
                        customer_name=old_sale.customer_name,
                        customer_vat=old_sale.customer_vat,
                        tax_base_20=old_sale.tax_base_20,
                        vat_20=old_sale.vat_20,
                        tax_base_0=old_sale.tax_base_0,
                        tax_base_exempt=old_sale.tax_base_exempt,
                        total_amount=old_sale.total_amount,
                        field_09=old_sale.tax_base_20,  # Map to field 09
                        field_10=old_sale.vat_20,       # Map to field 10
                        field_11=old_sale.tax_base_0,   # Map to field 11
                        field_12=old_sale.tax_base_exempt,  # Map to field 12
                        notes=old_sale.notes,
                        created_at=old_sale.created_at
                    )
                    new_db.add(new_sale)
        
        new_db.commit()
        logger.info(f"Migrated {len(old_sales)} sales entries")
        
        # Migrate VAT declarations
        old_declarations = old_db.query(VATDeclaration).all()
        for old_decl in old_declarations:
            new_company_id = company_mapping.get(old_decl.company_id)
            if new_company_id:
                # Check if already migrated
                existing = new_db.query(EnhancedVATDeclaration).filter(
                    EnhancedVATDeclaration.company_id == new_company_id,
                    EnhancedVATDeclaration.period == old_decl.period
                ).first()
                
                if not existing:
                    new_decl = EnhancedVATDeclaration(
                        company_id=new_company_id,
                        period=old_decl.period,
                        field_50=old_decl.field_50,
                        field_60=old_decl.field_60,
                        field_80=old_decl.field_80,
                        payment_due=old_decl.payment_due,
                        refund_due=old_decl.refund_due,
                        status=old_decl.status,
                        submission_date=old_decl.submission_date,
                        payment_deadline=old_decl.payment_deadline,
                        nap_submission_id=old_decl.nap_submission_id,
                        created_at=old_decl.created_at,
                        updated_at=old_decl.updated_at
                    )
                    new_db.add(new_decl)
        
        new_db.commit()
        logger.info(f"Migrated {len(old_declarations)} VAT declarations")
        logger.info("Data migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during data migration: {str(e)}")
        new_db.rollback()
        raise
    finally:
        old_db.close()
        new_db.close()

def get_database_stats():
    """Get statistics about the enhanced database"""
    db = SessionLocal()
    try:
        from enhanced_models import (
            EnhancedCompany, EnhancedPurchaseEntry, EnhancedSalesEntry,
            EnhancedVATDeclaration, VIESReport, DocumentTypeMapping, ExportLog
        )
        
        stats = {
            'companies': db.query(EnhancedCompany).count(),
            'purchase_entries': db.query(EnhancedPurchaseEntry).count(),
            'sales_entries': db.query(EnhancedSalesEntry).count(),
            'vat_declarations': db.query(EnhancedVATDeclaration).count(),
            'vies_reports': db.query(VIESReport).count(),
            'document_type_mappings': db.query(DocumentTypeMapping).count(),
            'export_logs': db.query(ExportLog).count()
        }
        
        return stats
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database
    create_enhanced_tables()
    
    # Optional: Migrate existing data
    try:
        migrate_existing_data()
    except Exception as e:
        logger.warning(f"Migration skipped: {str(e)}")
    
    # Show stats
    stats = get_database_stats()
    print("Enhanced Database Statistics:")
    for table, count in stats.items():
        print(f"  {table}: {count} records")