from fastapi import FastAPI, HTTPException, Depends, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from datetime import datetime
import logging
import tempfile
import os

# Use synchronous database for simplicity
from database_sync import engine, Base, get_db, create_tables
from models_sync import Company, PurchaseJournal, SalesJournal, VATDeclaration
from schemas import (
    CompanyCreate, CompanyResponse, 
    PurchaseJournalCreate, PurchaseJournalResponse,
    SalesJournalCreate, SalesJournalResponse,
    DeclarationResponse
)
from services_sync import (
    CompanyService, 
    JournalService, 
    DeclarationService,
    VATCalculationService
)
from nra_export_service import NRAExportService

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
create_tables()

# FastAPI app initialization
app = FastAPI(
    title="Bulgarian VAT Management System",
    description="Modern web service for Bulgarian VAT compliance - Reverse engineered from Dnevnici v14.02",
    version="2.0.0"
)

# CORS middleware for Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Svelte dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# COMPANY MANAGEMENT ENDPOINTS (Служебни функции)
# ============================================================================

@app.post("/api/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, db = Depends(get_db)):
    """Register a new company (Избор на задължено лице)"""
    try:
        service = CompanyService(db)
        return service.create_company(company)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}", response_model=CompanyResponse)
def get_company(uic: str, db = Depends(get_db)):
    """Get company details by UIC"""
    service = CompanyService(db)
    company = service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.get("/api/companies", response_model=List[CompanyResponse])
def list_companies(db = Depends(get_db)):
    """List all registered companies"""
    service = CompanyService(db)
    return service.list_companies()

@app.delete("/api/companies/{company_id}")
def delete_company(company_id: int, force: bool = False, db = Depends(get_db)):
    """Delete a company by ID
    
    Args:
        company_id: ID of company to delete
        force: If True, deletes all associated records (purchases, sales, declarations)
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Count associated records
    purchases_count = db.query(PurchaseJournal).filter(PurchaseJournal.company_id == company_id).count()
    sales_count = db.query(SalesJournal).filter(SalesJournal.company_id == company_id).count()
    declarations_count = db.query(VATDeclaration).filter(VATDeclaration.company_id == company_id).count()
    
    if (purchases_count > 0 or sales_count > 0 or declarations_count > 0) and not force:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Cannot delete company with existing data",
                "message": f"Company has {purchases_count} purchase entries, {sales_count} sales entries, and {declarations_count} declarations",
                "suggestion": "Use force=true parameter to delete all associated data, or delete the data manually first",
                "counts": {
                    "purchases": purchases_count,
                    "sales": sales_count, 
                    "declarations": declarations_count
                }
            }
        )
    
    # If force=True, delete all associated records first
    if force:
        # Delete VAT declarations
        db.query(VATDeclaration).filter(VATDeclaration.company_id == company_id).delete()
        
        # Delete purchase journal entries
        db.query(PurchaseJournal).filter(PurchaseJournal.company_id == company_id).delete()
        
        # Delete sales journal entries  
        db.query(SalesJournal).filter(SalesJournal.company_id == company_id).delete()
        
        db.commit()  # Commit the deletions
    
    # Delete the company
    db.delete(company)
    db.commit()
    
    return {
        "message": "Company deleted successfully",
        "deleted_records": {
            "purchases": purchases_count if force else 0,
            "sales": sales_count if force else 0,
            "declarations": declarations_count if force else 0
        }
    }

@app.put("/api/companies/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, company_update: CompanyCreate, db = Depends(get_db)):
    """Update company details"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update company fields
    company.name = company_update.name
    company.uic = company_update.uic
    company.vat_number = company_update.vat_number
    company.address = company_update.address
    company.is_active = company_update.is_active
    
    db.commit()
    db.refresh(company)
    
    return CompanyResponse(
        id=company.id,
        uic=company.uic,
        vat_number=company.vat_number,
        name=company.name,
        address=company.address,
        is_active=company.is_active,
        created_at=company.created_at
    )

# ============================================================================
# PURCHASE JOURNAL ENDPOINTS (Дневник на покупките)
# ============================================================================

@app.post("/api/companies/{uic}/purchases", response_model=PurchaseJournalResponse)
def add_purchase_entry(uic: str, entry: PurchaseJournalCreate, db = Depends(get_db)):
    """Add entry to purchase journal"""
    try:
        service = JournalService(db)
        return service.add_purchase_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/purchases/{period}", response_model=List[PurchaseJournalResponse])
def get_purchases(uic: str, period: str, db = Depends(get_db)):
    """Get purchase entries for specific period (YYYYMM format)"""
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
    
    service = JournalService(db)
    return service.get_purchases(uic, period)

@app.post("/api/purchases/{entry_id}/credit-note")
def convert_to_credit_note(entry_id: int, db = Depends(get_db)):
    """Convert purchase entry to credit note"""
    entry = db.query(PurchaseJournal).filter(PurchaseJournal.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Purchase entry not found")
    
    # Convert to credit note by making amounts negative
    entry.document_type = 3  # Credit note type
    if entry.tax_base:
        entry.credit_tax_base = abs(entry.tax_base)
        entry.tax_base = -abs(entry.tax_base)
    if entry.vat_amount:
        entry.credit_vat = abs(entry.vat_amount)  
        entry.vat_amount = -abs(entry.vat_amount)
    if entry.total_amount:
        entry.total_amount = -abs(entry.total_amount)
    
    entry.notes = (entry.notes or "") + " [Converted to credit note]"
    
    db.commit()
    return {"message": "Purchase entry converted to credit note successfully"}

# ============================================================================
# SALES JOURNAL ENDPOINTS (Дневник за продажбите)  
# ============================================================================

@app.post("/api/companies/{uic}/sales", response_model=SalesJournalResponse)
def add_sales_entry(uic: str, entry: SalesJournalCreate, db = Depends(get_db)):
    """Add entry to sales journal"""
    try:
        service = JournalService(db)
        return service.add_sales_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/sales/{period}", response_model=List[SalesJournalResponse])
def get_sales(uic: str, period: str, db = Depends(get_db)):
    """Get sales entries for specific period"""
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
    
    service = JournalService(db)
    return service.get_sales(uic, period)

@app.delete("/api/purchases/{entry_id}")
def delete_purchase_entry(entry_id: int, db = Depends(get_db)):
    """Delete a purchase journal entry"""
    try:
        service = JournalService(db)
        success = service.delete_purchase_entry(entry_id)
        if success:
            return {"message": "Entry deleted successfully", "deleted_id": entry_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

@app.delete("/api/sales/{entry_id}")
def delete_sales_entry(entry_id: int, db = Depends(get_db)):
    """Delete a sales journal entry"""
    try:
        service = JournalService(db)
        success = service.delete_sales_entry(entry_id)
        if success:
            return {"message": "Entry deleted successfully", "deleted_id": entry_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

# ============================================================================
# VAT DECLARATION ENDPOINTS (Справка-декларация по ЗДДС)
# ============================================================================

@app.post("/api/companies/{uic}/declarations/{period}", response_model=DeclarationResponse)
def generate_declaration(uic: str, period: str, db = Depends(get_db)):
    """Generate VAT declaration for period"""
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Некоректна година в полето Период")
    
    try:
        service = DeclarationService(db)
        return service.generate_declaration(uic, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/declarations/{period}", response_model=DeclarationResponse)
def get_declaration(uic: str, period: str, db = Depends(get_db)):
    """Get existing VAT declaration"""
    service = DeclarationService(db)
    declaration = service.get_declaration(uic, period)
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")
    return declaration

@app.post("/api/declarations/{declaration_id}/submit")
def submit_declaration(declaration_id: int, db = Depends(get_db)):
    """Submit VAT declaration to NAP (National Revenue Agency)"""
    try:
        service = DeclarationService(db)
        
        # Get the declaration by ID
        declaration = db.query(VATDeclaration).filter(VATDeclaration.id == declaration_id).first()
        if not declaration:
            raise HTTPException(status_code=404, detail="Declaration not found")
        
        # Check if already submitted
        if declaration.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Declaration already submitted")
        
        # Update declaration status and submission info
        now = datetime.now()
        declaration.status = "SUBMITTED"
        declaration.submission_date = now
        declaration.nap_submission_id = f"NAP{now.strftime('%Y%m%d')}{declaration_id:06d}"
        
        # Set payment deadline if there's amount due
        if declaration.payment_due > 0:
            calculator = VATCalculationService()
            deadline = calculator.calculate_payment_deadline(declaration.period)
            declaration.payment_deadline = deadline
        
        db.commit()
        
        return {
            "message": "Declaration submitted successfully",
            "nap_submission_id": declaration.nap_submission_id,
            "status": declaration.status,
            "submission_date": declaration.submission_date.isoformat() if declaration.submission_date else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")

@app.post("/api/declarations/{declaration_id}/revert")
def revert_declaration(declaration_id: int, db = Depends(get_db)):
    """Revert a submitted declaration back to DRAFT status"""
    try:
        service = DeclarationService(db)
        declaration = service.revert_declaration(declaration_id)
        
        return {
            "message": "Declaration reverted to draft successfully",
            "declaration_id": declaration.id,
            "status": declaration.status,
            "submission_date": None,
            "nap_submission_id": None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revert failed: {str(e)}")

@app.delete("/api/declarations/{declaration_id}")
def delete_declaration(declaration_id: int, db = Depends(get_db)):
    """Delete a VAT declaration (DRAFT status only)"""
    try:
        service = DeclarationService(db)
        success = service.delete_declaration(declaration_id)
        
        if success:
            return {
                "message": "Declaration deleted successfully",
                "deleted_id": declaration_id
            }
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# ============================================================================
# COMPANY REPORTS ENDPOINTS  
# ============================================================================

@app.get("/api/companies/{company_id}/reports/vat-summary")
def get_company_vat_summary(
    company_id: int, 
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    db = Depends(get_db)
):
    """Get VAT summary report for a company"""
    try:
        from datetime import datetime
        
        # Validate company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get purchase data
        purchases = db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.document_date >= start_dt,
            PurchaseJournal.document_date <= end_dt
        ).all()
        
        # Get sales data
        sales = db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.document_date >= start_dt,
            SalesJournal.document_date <= end_dt
        ).all()
        
        # Calculate totals
        total_purchase_amount = sum(float(p.amount) for p in purchases)
        total_purchase_vat = sum(float(p.vat_amount) for p in purchases)
        total_sales_amount = sum(float(s.amount) for s in sales) 
        total_sales_vat = sum(float(s.vat_amount) for s in sales)
        
        # Group by document type
        purchase_by_type = {}
        for purchase in purchases:
            doc_type = purchase.document_type
            if doc_type not in purchase_by_type:
                purchase_by_type[doc_type] = {"count": 0, "amount": 0, "vat": 0}
            purchase_by_type[doc_type]["count"] += 1
            purchase_by_type[doc_type]["amount"] += float(purchase.amount)
            purchase_by_type[doc_type]["vat"] += float(purchase.vat_amount)
            
        sales_by_type = {}
        for sale in sales:
            doc_type = sale.document_type
            if doc_type not in sales_by_type:
                sales_by_type[doc_type] = {"count": 0, "amount": 0, "vat": 0}
            sales_by_type[doc_type]["count"] += 1
            sales_by_type[doc_type]["amount"] += float(sale.amount)
            sales_by_type[doc_type]["vat"] += float(sale.vat_amount)
        
        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "vat_number": company.vat_number,
                "uic": company.uic
            },
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "purchases": {
                    "total_amount": total_purchase_amount,
                    "total_vat": total_purchase_vat,
                    "count": len(purchases),
                    "by_type": purchase_by_type
                },
                "sales": {
                    "total_amount": total_sales_amount,
                    "total_vat": total_sales_vat,
                    "count": len(sales),
                    "by_type": sales_by_type
                },
                "net_vat_position": total_sales_vat - total_purchase_vat
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.get("/api/companies/{company_id}/reports/monthly-breakdown")
def get_company_monthly_breakdown(
    company_id: int,
    year: int = Query(..., description="Year YYYY"),
    db = Depends(get_db)
):
    """Get monthly breakdown of VAT transactions for a company"""
    try:
        from datetime import datetime
        from collections import defaultdict
        
        # Validate company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        # Get all data for the year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        purchases = db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.document_date >= start_date,
            PurchaseJournal.document_date <= end_date
        ).all()
        
        sales = db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.document_date >= start_date,
            SalesJournal.document_date <= end_date
        ).all()
        
        # Group by month
        monthly_data = defaultdict(lambda: {
            "purchases": {"amount": 0, "vat": 0, "count": 0},
            "sales": {"amount": 0, "vat": 0, "count": 0}
        })
        
        for purchase in purchases:
            month = purchase.document_date.month
            monthly_data[month]["purchases"]["amount"] += float(purchase.amount)
            monthly_data[month]["purchases"]["vat"] += float(purchase.vat_amount)
            monthly_data[month]["purchases"]["count"] += 1
            
        for sale in sales:
            month = sale.document_date.month
            monthly_data[month]["sales"]["amount"] += float(sale.amount)
            monthly_data[month]["sales"]["vat"] += float(sale.vat_amount)
            monthly_data[month]["sales"]["count"] += 1
        
        # Convert to sorted list
        months = []
        month_names = [
            "Януари", "Февруари", "Март", "Април", "Май", "Юни",
            "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"
        ]
        
        for month in range(1, 13):
            data = monthly_data[month]
            months.append({
                "month": month,
                "month_name": month_names[month-1],
                "purchases": data["purchases"],
                "sales": data["sales"],
                "net_vat": data["sales"]["vat"] - data["purchases"]["vat"]
            })
        
        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "vat_number": company.vat_number
            },
            "year": year,
            "months": months,
            "totals": {
                "purchases": {
                    "amount": sum(m["purchases"]["amount"] for m in months),
                    "vat": sum(m["purchases"]["vat"] for m in months),
                    "count": sum(m["purchases"]["count"] for m in months)
                },
                "sales": {
                    "amount": sum(m["sales"]["amount"] for m in months),
                    "vat": sum(m["sales"]["vat"] for m in months),
                    "count": sum(m["sales"]["count"] for m in months)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.get("/api/companies/{company_id}/reports/eu-transactions")
def get_company_eu_transactions(
    company_id: int,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    db = Depends(get_db)
):
    """Get EU (VIES) transactions report for a company"""
    try:
        from datetime import datetime
        
        # Validate company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get EU transactions (VAT numbers starting with EU country codes)
        eu_countries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK']
        
        eu_purchases = []
        purchases = db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.document_date >= start_dt,
            PurchaseJournal.document_date <= end_dt
        ).all()
        
        for purchase in purchases:
            if purchase.supplier_vat_number:
                vat_upper = purchase.supplier_vat_number.upper()
                if any(vat_upper.startswith(country) for country in eu_countries):
                    eu_purchases.append(purchase)
        
        eu_sales = []
        sales = db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.document_date >= start_dt,
            SalesJournal.document_date <= end_dt
        ).all()
        
        for sale in sales:
            if sale.customer_vat_number:
                vat_upper = sale.customer_vat_number.upper()
                if any(vat_upper.startswith(country) for country in eu_countries):
                    eu_sales.append(sale)
        
        # Group by country
        country_summary = {}
        
        for purchase in eu_purchases:
            country = purchase.supplier_vat_number[:2].upper()
            if country not in country_summary:
                country_summary[country] = {
                    "acquisitions": {"amount": 0, "vat": 0, "count": 0},
                    "supplies": {"amount": 0, "vat": 0, "count": 0}
                }
            country_summary[country]["acquisitions"]["amount"] += float(purchase.amount)
            country_summary[country]["acquisitions"]["vat"] += float(purchase.vat_amount)
            country_summary[country]["acquisitions"]["count"] += 1
            
        for sale in eu_sales:
            country = sale.customer_vat_number[:2].upper()
            if country not in country_summary:
                country_summary[country] = {
                    "acquisitions": {"amount": 0, "vat": 0, "count": 0},
                    "supplies": {"amount": 0, "vat": 0, "count": 0}
                }
            country_summary[country]["supplies"]["amount"] += float(sale.amount)
            country_summary[country]["supplies"]["vat"] += float(sale.vat_amount)
            country_summary[country]["supplies"]["count"] += 1
        
        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "vat_number": company.vat_number
            },
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "eu_transactions": {
                "purchases": [
                    {
                        "id": p.id,
                        "document_date": p.document_date.isoformat(),
                        "document_type": p.document_type,
                        "document_number": p.document_number,
                        "supplier_name": p.supplier_name,
                        "supplier_vat_number": p.supplier_vat_number,
                        "amount": float(p.amount),
                        "vat_amount": float(p.vat_amount),
                        "country": p.supplier_vat_number[:2].upper() if p.supplier_vat_number else None
                    } for p in eu_purchases
                ],
                "sales": [
                    {
                        "id": s.id,
                        "document_date": s.document_date.isoformat(),
                        "document_type": s.document_type,
                        "document_number": s.document_number,
                        "customer_name": s.customer_name,
                        "customer_vat_number": s.customer_vat_number,
                        "amount": float(s.amount),
                        "vat_amount": float(s.vat_amount),
                        "country": s.customer_vat_number[:2].upper() if s.customer_vat_number else None
                    } for s in eu_sales
                ],
                "country_summary": country_summary
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

# ============================================================================
# VIES AND REPORTING PROTOCOL ENDPOINTS
# ============================================================================

@app.get("/api/companies/{uic}/vies/{period}")
def generate_vies_declaration(uic: str, period: str, db = Depends(get_db)):
    """Generate VIES declaration for EU transactions"""
    try:
        from vies_service import VIESService
        
        if not period or len(period) != 6 or not period.isdigit():
            raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
        
        service = VIESService(db)
        vies_declaration = service.generate_vies_declaration(uic, period)
        
        return {
            "company_uic": uic,
            "period": period,
            "total_supplies": float(vies_declaration.total_supplies),
            "total_acquisitions": float(vies_declaration.total_acquisitions),
            "eu_partners": len(vies_declaration.entries),
            "created_at": vies_declaration.created_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VIES generation failed: {str(e)}")

@app.get("/api/companies/{uic}/vies/{period}/export")
def export_vies_xml(uic: str, period: str, db = Depends(get_db)):
    """Export VIES declaration as XML"""
    try:
        from vies_service import VIESService
        import tempfile
        import os
        
        service = VIESService(db)
        vies_declaration = service.generate_vies_declaration(uic, period)
        xml_content = service.export_vies_xml(vies_declaration)
        
        # Create temporary XML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(xml_content)
            temp_file_path = temp_file.name
        
        filename = f"VIES_Declaration_{uic}_{period}.xml"
        
        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type='application/xml',
            background=lambda: os.unlink(temp_file_path)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VIES export failed: {str(e)}")

@app.get("/api/companies/{uic}/reporting-protocol/{period}")
def generate_reporting_protocol(uic: str, period: str, db = Depends(get_db)):
    """Generate comprehensive reporting protocol (СПРАВКА-ПРОТОКОЛ)"""
    try:
        from vies_service import ReportingProtocolService
        import tempfile
        import os
        
        if not period or len(period) != 6 or not period.isdigit():
            raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
        
        service = ReportingProtocolService(db)
        protocol_text = service.generate_reporting_protocol(uic, period)
        
        # Create temporary text file with Bulgarian encoding
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(protocol_text)
            temp_file_path = temp_file.name
        
        filename = f"Reporting_Protocol_{uic}_{period}.txt"
        
        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type='text/plain; charset=utf-8',
            background=lambda: os.unlink(temp_file_path)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Protocol generation failed: {str(e)}")

# ============================================================================
# FILE IMPORT ENDPOINTS (PaperlessAI Integration)
# ============================================================================

@app.post("/api/vat/import-excel")
def import_excel_file(
    file: UploadFile = File(...),
    company_uic: str = Form(...),
    journal_type: str = Form(default="purchase")
):
    """Import PaperlessAI Excel export file"""
    try:
        from file_import_service import VATFileImportService
        import tempfile
        import os
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are supported")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process the file
            import_service = VATFileImportService()
            import_service.set_db_session(get_db().__next__())
            
            success, result = import_service.import_excel_file(
                temp_file_path, company_uic, journal_type
            )
            
            if success:
                return {
                    "status": "success",
                    "message": f"Successfully processed {result['total_records']} records",
                    "data": result
                }
            else:
                raise HTTPException(status_code=400, detail=result.get('error', 'Import failed'))
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.post("/api/vat/import-json")
def import_json_file(
    file: UploadFile = File(...),
    company_uic: str = Form(...),
    journal_type: str = Form(default="purchase")
):
    """Import PaperlessAI JSON export file"""
    try:
        from file_import_service import VATFileImportService
        import tempfile
        import os
        
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w+b') as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process the file
            import_service = VATFileImportService()
            import_service.set_db_session(get_db().__next__())
            
            success, result = import_service.import_json_file(
                temp_file_path, company_uic, journal_type
            )
            
            if success:
                return {
                    "status": "success",
                    "message": f"Successfully processed {result['total_records']} records",
                    "data": result
                }
            else:
                raise HTTPException(status_code=400, detail=result.get('error', 'Import failed'))
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.post("/api/vat/validate-import")
def validate_import_entries(request: Dict):
    """Validate and optionally import processed entries"""
    try:
        from file_import_service import VATFileImportService
        
        # Extract entries and auto_approve from request
        entries = request.get('entries', [])
        auto_approve = request.get('auto_approve', False)
        
        import_service = VATFileImportService()
        if auto_approve:
            import_service.set_db_session(get_db().__next__())
        
        success, result = import_service.validate_and_import(entries, auto_approve)
        
        return {
            "status": "success" if success else "validation_errors",
            "message": f"Processed {result['total_processed']} entries, {result['valid_entries']} valid",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.post("/api/vat/preview-import")
def preview_import_data(entries: List[Dict]):
    """Generate preview of entries to be imported"""
    try:
        from file_import_service import ImportPreviewGenerator
        
        preview = ImportPreviewGenerator.generate_preview_table(entries)
        
        return {
            "status": "success",
            "message": f"Preview generated for {preview['count']} entries",
            "preview": preview
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

@app.get("/api/vat/download-template")
def download_excel_template(journal_type: str = "purchase"):
    """Download Excel template for data import"""
    try:
        from template_generator import VATTemplateGenerator
        
        # Validate journal type
        if journal_type not in ['purchase', 'sales']:
            raise HTTPException(status_code=400, detail="Journal type must be 'purchase' or 'sales'")
        
        # Generate template
        generator = VATTemplateGenerator()
        template_path = generator.create_template(journal_type)
        
        # Set appropriate filename
        filename = f"VAT_{journal_type}_template.xlsx"
        
        return FileResponse(
            path=template_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template generation failed: {str(e)}")

# ============================================================================
# NRA EXPORT ENDPOINTS
# ============================================================================

@app.get("/api/declarations/{declaration_id}/export/xml")
def export_declaration_xml(declaration_id: int, db = Depends(get_db)):
    """Export VAT declaration as XML file for NRA submission"""
    try:
        
        export_service = NRAExportService(db)
        
        # Validate before export
        errors = export_service.validate_declaration_for_export(declaration_id)
        if errors:
            raise HTTPException(status_code=400, detail=f"Validation errors: {'; '.join(errors)}")
        
        xml_file_path = export_service.export_declaration_xml(declaration_id)
        
        return FileResponse(
            path=xml_file_path,
            filename=f"VAT_Declaration_{declaration_id}.xml",
            media_type="application/xml"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/declarations/{declaration_id}/export/json")
def export_declaration_json(declaration_id: int, db = Depends(get_db)):
    """Export VAT declaration as JSON file"""
    try:
        
        export_service = NRAExportService(db)
        
        # Validate before export
        errors = export_service.validate_declaration_for_export(declaration_id)
        if errors:
            raise HTTPException(status_code=400, detail=f"Validation errors: {'; '.join(errors)}")
        
        json_file_path = export_service.export_declaration_json(declaration_id)
        
        return FileResponse(
            path=json_file_path,
            filename=f"VAT_Declaration_{declaration_id}.json",
            media_type="application/json"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/declarations/{declaration_id}/export/package")
def export_declaration_package(declaration_id: int, db = Depends(get_db)):
    """Export complete VAT declaration package as ZIP file"""
    try:
        
        export_service = NRAExportService(db)
        
        # Validate before export
        errors = export_service.validate_declaration_for_export(declaration_id)
        if errors:
            raise HTTPException(status_code=400, detail=f"Validation errors: {'; '.join(errors)}")
        
        zip_file_path = export_service.export_declaration_package(declaration_id)
        
        # Get declaration info for filename
        declaration = db.query(VATDeclaration).filter(VATDeclaration.id == declaration_id).first()
        company_uic = declaration.company.uic
        period = declaration.period
        
        return FileResponse(
            path=zip_file_path,
            filename=f"VAT_Declaration_{company_uic}_{period}.zip",
            media_type="application/zip"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/declarations/{declaration_id}/validate")
def validate_declaration_for_export(declaration_id: int, db = Depends(get_db)):
    """Validate declaration before export"""
    try:
        
        export_service = NRAExportService(db)
        errors = export_service.validate_declaration_for_export(declaration_id)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "message": "Ready for export" if len(errors) == 0 else f"Found {len(errors)} validation errors"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

# ============================================================================
# VAT CALCULATION ENDPOINTS
# ============================================================================

@app.get("/api/vat/calculate")
def calculate_vat(tax_base: float, vat_rate: float = 0.20):
    """Calculate VAT amount (20% standard rate)"""
    calculator = VATCalculationService()
    return {
        "tax_base": tax_base,
        "vat_rate": vat_rate,
        "vat_amount": calculator.calculate_vat(tax_base, vat_rate),
        "total_amount": calculator.calculate_total(tax_base, vat_rate)
    }

@app.get("/api/deadlines/{period}")
def get_payment_deadline(period: str):
    """Get payment deadline for period (14th of following month)"""
    if not period or len(period) != 6:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
    calculator = VATCalculationService()
    deadline = calculator.calculate_payment_deadline(period)
    
    return {
        "period": period,
        "deadline": deadline,
        "business_days_remaining": calculator.get_business_days_until(deadline)
    }

# ============================================================================
# VIES VAT VALIDATION ENDPOINTS
# ============================================================================

@app.post("/api/vat/validate-eu-vat")
def validate_eu_vat_number(request: Dict):
    """
    Validate EU VAT number using official VIES REST API
    
    Args:
        country_code: Two-letter EU country code (e.g., DE, FR)
        vat_number: National VAT number without country prefix  
        requester_vat: VAT number of requesting company (optional)
        trader_name: Company name for verification (optional)
        trader_address: Company address for verification (optional)
    
    Returns:
        Validation result with company details if valid
    """
    try:
        from vies_validation_service import vies_validator
        
        # Extract parameters from request
        country_code = request.get("country_code")
        vat_number = request.get("vat_number")
        requester_vat = request.get("requester_vat")
        trader_name = request.get("trader_name")
        trader_address = request.get("trader_address")
        
        if not country_code or not vat_number:
            raise HTTPException(status_code=400, detail="country_code and vat_number are required")
        
        # Extract requester country code from VAT number if provided
        requester_country = "BG"
        requester_number = None
        
        if requester_vat:
            if requester_vat.startswith("BG"):
                requester_number = requester_vat[2:]
            else:
                requester_number = requester_vat
        
        result = vies_validator.validate_vat_number(
            country_code=country_code,
            vat_number=vat_number,
            requester_country_code=requester_country,
            requester_vat_number=requester_number,
            trader_name=trader_name,
            trader_address=trader_address
        )
        
        return {
            "country_code": result.country_code,
            "vat_number": result.vat_number,
            "full_vat_number": f"{result.country_code}{result.vat_number}",
            "is_valid": result.is_valid,
            "company_name": result.company_name,
            "company_address": result.company_address,
            "request_date": result.request_date.isoformat() if result.request_date else None,
            "request_identifier": result.request_identifier,
            "trader_name_match": result.trader_name_match,
            "trader_address_match": result.trader_address_match,
            "error_message": result.error_message,
            "validation_status": "valid" if result.is_valid else "invalid" if not result.error_message else "error"
        }
        
    except Exception as e:
        logger.error(f"VAT validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.post("/api/vat/validate-full-vat")
def validate_full_vat_number(request: Dict):
    """
    Validate full EU VAT number (e.g., DE123456789)
    
    Args:
        full_vat_number: Complete VAT number with country prefix
        requester_vat: VAT number of requesting company (optional)
        trader_name: Company name for verification (optional)
        trader_address: Company address for verification (optional)
    
    Returns:
        Validation result with company details if valid
    """
    try:
        from vies_validation_service import vies_validator
        
        # Extract parameters from request
        full_vat_number = request.get("full_vat_number")
        requester_vat = request.get("requester_vat")
        trader_name = request.get("trader_name")
        trader_address = request.get("trader_address")
        
        # Validate format
        if not full_vat_number or len(full_vat_number) < 4:
            raise HTTPException(status_code=400, detail="Invalid VAT number format")
        
        result = vies_validator.validate_vat_from_full_number(
            full_vat_number=full_vat_number,
            requester_vat_number=requester_vat,
            trader_name=trader_name,
            trader_address=trader_address
        )
        
        return {
            "country_code": result.country_code,
            "vat_number": result.vat_number,
            "full_vat_number": f"{result.country_code}{result.vat_number}",
            "is_valid": result.is_valid,
            "company_name": result.company_name,
            "company_address": result.company_address,
            "request_date": result.request_date.isoformat() if result.request_date else None,
            "request_identifier": result.request_identifier,
            "trader_name_match": result.trader_name_match,
            "trader_address_match": result.trader_address_match,
            "error_message": result.error_message,
            "validation_status": "valid" if result.is_valid else "invalid" if not result.error_message else "error"
        }
        
    except Exception as e:
        logger.error(f"Full VAT validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.get("/api/vat/vies-status")
def check_vies_service_status():
    """
    Check the status of VIES service for all EU member states
    
    Returns:
        Service availability status for each EU country
    """
    try:
        from vies_validation_service import vies_validator
        
        status_info = vies_validator.check_service_status()
        
        return {
            "service_available": status_info.get("vow", {}).get("available", False),
            "countries": status_info.get("countries", []),
            "checked_at": datetime.now().isoformat(),
            "error": status_info.get("error")
        }
        
    except Exception as e:
        logger.error(f"VIES status check error: {str(e)}")
        return {
            "service_available": False,
            "error": str(e),
            "checked_at": datetime.now().isoformat()
        }

@app.post("/api/vat/batch-validate")
def batch_validate_vat_numbers(request: Dict):
    """
    Validate multiple EU VAT numbers in batch
    
    Args:
        vat_numbers: List of full VAT numbers to validate
        requester_vat: VAT number of requesting company (optional)
    
    Returns:
        List of validation results with summary statistics
    """
    try:
        from vies_validation_service import vies_validator
        
        # Extract parameters from request
        vat_numbers = request.get("vat_numbers", [])
        requester_vat = request.get("requester_vat")
        
        if not vat_numbers:
            raise HTTPException(status_code=400, detail="vat_numbers list is required")
        
        if len(vat_numbers) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 VAT numbers allowed per batch")
        
        results = []
        for vat_num in vat_numbers:
            result = vies_validator.validate_vat_from_full_number(
                full_vat_number=vat_num,
                requester_vat_number=requester_vat
            )
            
            results.append({
                "country_code": result.country_code,
                "vat_number": result.vat_number,
                "full_vat_number": f"{result.country_code}{result.vat_number}",
                "is_valid": result.is_valid,
                "company_name": result.company_name,
                "company_address": result.company_address,
                "error_message": result.error_message,
                "validation_status": "valid" if result.is_valid else "invalid" if not result.error_message else "error"
            })
        
        # Generate summary
        from vies_validation_service import VATValidationResult
        result_objects = [VATValidationResult(**{
            'country_code': r['country_code'],
            'vat_number': r['vat_number'],
            'is_valid': r['is_valid'],
            'error_message': r['error_message']
        }) for r in results]
        
        summary = vies_validator.get_validation_summary(result_objects)
        
        return {
            "results": results,
            "summary": summary,
            "total_processed": len(results),
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}")

@app.get("/api/vat/eu-countries")
def get_eu_countries():
    """
    Get list of EU member states for VAT validation
    
    Returns:
        List of EU country codes and names
    """
    eu_countries = {
        'AT': 'Austria',
        'BE': 'Belgium',
        'BG': 'Bulgaria',
        'HR': 'Croatia',
        'CY': 'Cyprus',
        'CZ': 'Czech Republic',
        'DK': 'Denmark',
        'EE': 'Estonia',
        'FI': 'Finland',
        'FR': 'France',
        'DE': 'Germany',
        'GR': 'Greece',
        'HU': 'Hungary',
        'IE': 'Ireland',
        'IT': 'Italy',
        'LV': 'Latvia',
        'LT': 'Lithuania',
        'LU': 'Luxembourg',
        'MT': 'Malta',
        'NL': 'Netherlands',
        'PL': 'Poland',
        'PT': 'Portugal',
        'RO': 'Romania',
        'SK': 'Slovakia',
        'SI': 'Slovenia',
        'ES': 'Spain',
        'SE': 'Sweden'
    }
    
    return {
        "countries": [
            {"code": code, "name": name} 
            for code, name in eu_countries.items()
        ],
        "total_countries": len(eu_countries)
    }

# ============================================================================
# HEALTH CHECK & INFO
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Bulgarian VAT Management System API",
        "description": "Modern reproduction of Dnevnici v14.02",
        "original_publisher": "National Revenue Agency (НАП)",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

# ============================================================================
# ENHANCED DOCUMENT TYPES (Added for enhanced frontend support)
# ============================================================================

@app.get("/api/v2/purchase-document-types")
def get_purchase_document_types():
    """Get all supported purchase document types (NRA Complete)"""
    return {
        "document_types": [
            {"code": 1, "name": "INVOICE", "description": "Standard invoice for purchases"},
            {"code": 2, "name": "CUSTOMS_DOCUMENT", "description": "Customs import document"},
            {"code": 3, "name": "CREDIT_NOTE", "description": "Credit note/protocol document"},
            {"code": 5, "name": "ARTICLE_15A_DOC", "description": "Documents per Article 15a (since 01.04.2020)"},
            {"code": 7, "name": "AGGREGATE_INVOICE", "description": "Aggregate invoices"},
            {"code": 9, "name": "NO_TAX_CREDIT", "description": "Documents without tax credit rights"},
            {"code": 11, "name": "TRIANGULAR_ART15", "description": "Triangular operations per Article 15"},
            {"code": 12, "name": "TRIANGULAR_ART14", "description": "Triangular operations per Article 14"},
            {"code": 13, "name": "ACQUISITIONS_ART14", "description": "Acquisitions per Article 14"},
            {"code": 23, "name": "ARTICLE_126A_DOC", "description": "Documents per Article 126a"},
            {"code": 91, "name": "VAT_APP_151A_1", "description": "VAT application per Article 151a, par. 1"},
            {"code": 92, "name": "VAT_APP_151A_2", "description": "VAT application per Article 151a, par. 2"},
            {"code": 93, "name": "VAT_APP_151A_3", "description": "VAT application per Article 151a, par. 3"},
            {"code": 94, "name": "VAT_APP_151A_4", "description": "VAT application per Article 151a, par. 4"}
        ]
    }

@app.get("/api/v2/sales-document-types")
def get_sales_document_types():
    """Get all supported sales document types"""
    return {
        "document_types": [
            {"code": 1, "name": "DOMESTIC_INVOICE", "description": "Domestic sales invoice"},
            {"code": 2, "name": "EU_SALES", "description": "EU sales (intra-community delivery)"},
            {"code": 3, "name": "EXPORT_SALES", "description": "Export sales (outside EU)"},
            {"code": 4, "name": "TRIANGULAR_SALES", "description": "Triangular sales operations"},
            {"code": 5, "name": "DISTANCE_SELLING", "description": "Distance selling"},
            {"code": 6, "name": "INTRA_COMMUNITY", "description": "Intra-community acquisitions"}
        ]
    }

@app.get("/api/v2/vat-field-definitions")
def get_vat_field_definitions():
    """Get VAT declaration field definitions"""
    return {
        "field_definitions": {
            "field_09": "Deliveries/services taxable at 20%",
            "field_10": "VAT amount for field 09",
            "field_11": "Deliveries/services taxable at 0%", 
            "field_12": "Exempt deliveries/services",
            "field_13": "Intra-community deliveries",
            "field_14": "Exports",
            "field_15": "Other deliveries outside Bulgaria",
            "field_16": "Distance sales to Bulgaria",
            "field_17": "VAT for distance sales",
            "field_18": "Intra-community acquisitions",
            "field_19": "VAT for intra-community acquisitions",
            "field_20": "Other acquisitions subject to reverse charge",
            "field_21": "VAT for other acquisitions",
            "field_22": "Import VAT",
            "field_23": "Corrections of previous periods",
            "field_24": "VAT corrections", 
            "field_25": "Other corrections",
            "field_50": "Total sales VAT due",
            "field_60": "Total purchase VAT deductible",
            "field_70": "VAT due to budget",
            "field_71": "VAT refund due from budget",
            "field_80": "Refund amount",
            "field_81": "Amount to pay",
            "field_82": "Amount to refund"
        }
    }

# Also add v2 CORS-compatible company endpoint
@app.get("/api/v2/companies")
def list_companies_v2(db = Depends(get_db)):
    """List companies (v2 API compatibility)"""
    service = CompanyService(db)
    return service.list_companies()

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Check if port argument provided
    port = 8000
        # Windows multiprocessing fix
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = 8001
    else:
        port = 8001
    
    print(f"Starting Bulgarian VAT API on port {port}")
    print(f"Enhanced document types: 14 purchase + 6 sales")  
    print(f"VIES integration: Active")
    print(f"Company reports: Enabled")
    
    uvicorn.run(
        "main_simple:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True,
        log_level="info"
    )