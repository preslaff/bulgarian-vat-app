from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
from typing import List, Optional
from datetime import datetime, date
import logging

from database import engine, Base, get_db
from models import Company, PurchaseJournal, SalesJournal, VATDeclaration
from schemas import (
    CompanyCreate, CompanyResponse, 
    PurchaseJournalCreate, PurchaseJournalResponse,
    SalesJournalCreate, SalesJournalResponse,
    DeclarationResponse, DeclarationGenerate
)
from services import (
    CompanyService, 
    JournalService, 
    DeclarationService,
    VATCalculationService
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# FastAPI app initialization
app = FastAPI(
    title="Bulgarian VAT Management System",
    description="Modern web service for Bulgarian VAT compliance - Reverse engineered from Dnevnici v14.02",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Svelte dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# ============================================================================
# COMPANY MANAGEMENT ENDPOINTS (Служебни функции)
# ============================================================================

@app.post("/api/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company: CompanyCreate,
    db = Depends(get_db)
):
    """Register a new company (Избор на задължено лице)"""
    try:
        service = CompanyService(db)
        return await service.create_company(company)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}", response_model=CompanyResponse)
async def get_company(uic: str, db = Depends(get_db)):
    """Get company details by UIC"""
    service = CompanyService(db)
    company = await service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.get("/api/companies", response_model=List[CompanyResponse])
async def list_companies(db = Depends(get_db)):
    """List all registered companies"""
    service = CompanyService(db)
    return await service.list_companies()

# ============================================================================
# PURCHASE JOURNAL ENDPOINTS (Дневник на покупките)
# ============================================================================

@app.post("/api/companies/{uic}/purchases", response_model=PurchaseJournalResponse)
async def add_purchase_entry(
    uic: str,
    entry: PurchaseJournalCreate,
    db = Depends(get_db)
):
    """Add entry to purchase journal"""
    try:
        service = JournalService(db)
        return await service.add_purchase_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/purchases/{period}", response_model=List[PurchaseJournalResponse])
async def get_purchases(
    uic: str, 
    period: str,
    db = Depends(get_db)
):
    """Get purchase entries for specific period (YYYYMM format)"""
    # Validate period format
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
    
    service = JournalService(db)
    return await service.get_purchases(uic, period)

@app.post("/api/purchases/{entry_id}/credit-note")
async def convert_to_credit_note(
    entry_id: int,
    db = Depends(get_db)
):
    """Convert purchase entry to credit note (Кредитно известие)"""
    service = JournalService(db)
    return await service.convert_to_credit_note(entry_id)

# ============================================================================
# SALES JOURNAL ENDPOINTS (Дневник за продажбите)  
# ============================================================================

@app.post("/api/companies/{uic}/sales", response_model=SalesJournalResponse)
async def add_sales_entry(
    uic: str,
    entry: SalesJournalCreate,
    db = Depends(get_db)
):
    """Add entry to sales journal"""
    try:
        service = JournalService(db)
        return await service.add_sales_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/sales/{period}", response_model=List[SalesJournalResponse])
async def get_sales(
    uic: str,
    period: str, 
    db = Depends(get_db)
):
    """Get sales entries for specific period"""
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Period must be YYYYMM format")
    
    service = JournalService(db)
    return await service.get_sales(uic, period)

# ============================================================================
# VAT DECLARATION ENDPOINTS (Справка-декларация по ЗДДС)
# ============================================================================

@app.post("/api/companies/{uic}/declarations/{period}", response_model=DeclarationResponse)
async def generate_declaration(
    uic: str,
    period: str,
    db = Depends(get_db)
):
    """Generate VAT declaration for period (Справка-декларация по ЗДДС и VIES)"""
    if not period or len(period) != 6 or not period.isdigit():
        raise HTTPException(status_code=400, detail="Некоректна година в полето Период")
    
    try:
        service = DeclarationService(db)
        return await service.generate_declaration(uic, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/companies/{uic}/declarations/{period}", response_model=DeclarationResponse)
async def get_declaration(
    uic: str,
    period: str,
    db = Depends(get_db)
):
    """Get existing VAT declaration"""
    service = DeclarationService(db)
    declaration = await service.get_declaration(uic, period)
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")
    return declaration

@app.post("/api/declarations/{declaration_id}/submit")
async def submit_declaration(
    declaration_id: int,
    db = Depends(get_db)
):
    """Submit declaration to NAP (НАП submission)"""
    # This would integrate with actual NAP systems
    service = DeclarationService(db)
    return await service.submit_to_nap(declaration_id)

# ============================================================================
# VAT CALCULATION ENDPOINTS
# ============================================================================

@app.get("/api/vat/calculate")
async def calculate_vat(
    tax_base: float,
    vat_rate: float = 0.20
):
    """Calculate VAT amount (20% standard rate)"""
    calculator = VATCalculationService()
    return {
        "tax_base": tax_base,
        "vat_rate": vat_rate,
        "vat_amount": calculator.calculate_vat(tax_base, vat_rate),
        "total_amount": calculator.calculate_total(tax_base, vat_rate)
    }

@app.get("/api/deadlines/{period}")
async def get_payment_deadline(period: str):
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
# HEALTH CHECK & INFO
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Bulgarian VAT Management System API",
        "description": "Modern reproduction of Dnevnici v14.02",
        "original_publisher": "National Revenue Agency (НАП)",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )