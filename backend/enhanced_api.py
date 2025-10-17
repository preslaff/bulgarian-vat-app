from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# Enhanced imports
from enhanced_database import get_enhanced_db, create_enhanced_tables, get_database_stats
from enhanced_models import (
    EnhancedCompany, EnhancedPurchaseEntry, EnhancedSalesEntry,
    EnhancedVATDeclaration, VIESReport, DocumentTypeMapping, ExportLog,
    PurchaseDocumentType, SalesDocumentType
)
from enhanced_schemas import (
    EnhancedCompanyCreate, EnhancedCompanyResponse,
    EnhancedPurchaseEntryCreate, EnhancedPurchaseEntryResponse,
    EnhancedSalesEntryCreate, EnhancedSalesEntryResponse,
    EnhancedVATDeclarationCreate, EnhancedVATDeclarationResponse,
    VIESReportCreate, VIESReportResponse,
    DocumentTypeMappingResponse, ExportLogResponse
)
from enhanced_services import (
    EnhancedCompanyService, EnhancedPurchaseService, EnhancedSalesService,
    EnhancedVATDeclarationService, EnhancedVIESService,
    DocumentTypeMappingService, ExportService
)

# VIES validation service (existing)
from vies_validation_service import vies_validator

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create enhanced tables on startup
create_enhanced_tables()

# FastAPI app initialization
app = FastAPI(
    title="Enhanced Bulgarian VAT Management System",
    description="Complete VAT compliance system with all NRA document types - Enhanced version",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ENHANCED COMPANY MANAGEMENT
# ============================================================================

@app.post("/api/v2/companies", response_model=EnhancedCompanyResponse, status_code=status.HTTP_201_CREATED)
def create_enhanced_company(company: EnhancedCompanyCreate, db=Depends(get_enhanced_db)):
    """Create enhanced company with additional NRA fields"""
    try:
        service = EnhancedCompanyService(db)
        return service.create_company(company)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}", response_model=EnhancedCompanyResponse)
def get_enhanced_company(uic: str, db=Depends(get_enhanced_db)):
    """Get enhanced company by UIC"""
    service = EnhancedCompanyService(db)
    company = service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.get("/api/v2/companies", response_model=List[EnhancedCompanyResponse])
def list_enhanced_companies(active_only: bool = Query(True), db=Depends(get_enhanced_db)):
    """List all enhanced companies"""
    service = EnhancedCompanyService(db)
    return service.list_companies(active_only=active_only)

# ============================================================================
# ENHANCED PURCHASE LEDGER (All Document Types)
# ============================================================================

@app.post("/api/v2/companies/{uic}/purchases", response_model=EnhancedPurchaseEntryResponse)
def create_enhanced_purchase_entry(
    uic: str, 
    entry: EnhancedPurchaseEntryCreate, 
    db=Depends(get_enhanced_db)
):
    """Create purchase entry supporting all NRA document types (01-94)"""
    try:
        service = EnhancedPurchaseService(db)
        return service.create_purchase_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/purchases/{period}", response_model=List[EnhancedPurchaseEntryResponse])
def get_enhanced_purchases(
    uic: str, 
    period: str, 
    document_type: Optional[int] = Query(None, description="Filter by document type"),
    db=Depends(get_enhanced_db)
):
    """Get purchase entries with optional document type filter"""
    try:
        service = EnhancedPurchaseService(db)
        return service.get_purchases(uic, period, document_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/purchases/{period}/summary")
def get_purchase_summary_by_type(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Get purchase summary grouped by document type"""
    try:
        service = EnhancedPurchaseService(db)
        return service.get_purchase_summary_by_type(uic, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/purchase-document-types")
def get_purchase_document_types():
    """Get all supported purchase document types"""
    return {
        "document_types": [
            {"code": doc_type.value, "name": doc_type.name, "description": _get_document_description(doc_type.value)}
            for doc_type in PurchaseDocumentType
        ]
    }

# ============================================================================
# ENHANCED SALES LEDGER (Field Mapping System)
# ============================================================================

@app.post("/api/v2/companies/{uic}/sales", response_model=EnhancedSalesEntryResponse)
def create_enhanced_sales_entry(
    uic: str, 
    entry: EnhancedSalesEntryCreate, 
    db=Depends(get_enhanced_db)
):
    """Create sales entry with field mapping system (fields 9-25)"""
    try:
        service = EnhancedSalesService(db)
        return service.create_sales_entry(uic, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/sales/{period}", response_model=List[EnhancedSalesEntryResponse])
def get_enhanced_sales(
    uic: str, 
    period: str, 
    document_type: Optional[int] = Query(None, description="Filter by document type"),
    db=Depends(get_enhanced_db)
):
    """Get sales entries with optional document type filter"""
    try:
        service = EnhancedSalesService(db)
        return service.get_sales(uic, period, document_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/sales/{period}/field-totals")
def get_sales_field_totals(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Calculate totals for all declaration fields (9-25)"""
    try:
        service = EnhancedSalesService(db)
        return service.calculate_field_totals(uic, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/sales-document-types")
def get_sales_document_types():
    """Get all supported sales document types"""
    return {
        "document_types": [
            {"code": doc_type.value, "name": doc_type.name, "description": _get_sales_document_description(doc_type.value)}
            for doc_type in SalesDocumentType
        ]
    }

# ============================================================================
# ENHANCED VAT DECLARATIONS (Fields 1-82)
# ============================================================================

@app.post("/api/v2/companies/{uic}/declarations/{period}")
def generate_enhanced_declaration(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Generate enhanced VAT declaration with automatic field calculations"""
    try:
        service = EnhancedVATDeclarationService(db)
        declaration = service.generate_declaration(uic, period)
        return {
            "declaration": declaration,
            "message": "Enhanced VAT declaration generated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/declarations/{period}", response_model=EnhancedVATDeclarationResponse)
def get_enhanced_declaration(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Get enhanced VAT declaration"""
    service = EnhancedCompanyService(db)
    company = service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    declaration = db.query(EnhancedVATDeclaration).filter(
        EnhancedVATDeclaration.company_id == company.id,
        EnhancedVATDeclaration.period == period
    ).first()
    
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")
    return declaration

@app.post("/api/v2/declarations/{declaration_id}/validate")
def validate_enhanced_declaration(declaration_id: int, db=Depends(get_enhanced_db)):
    """Validate declaration according to NRA rules"""
    try:
        service = EnhancedVATDeclarationService(db)
        validation_errors = service.validate_declaration(declaration_id)
        return {
            "declaration_id": declaration_id,
            "is_valid": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/vat-field-definitions")
def get_vat_field_definitions():
    """Get definitions for all VAT declaration fields (9-82)"""
    return {
        "field_definitions": _get_field_definitions()
    }

# ============================================================================
# VIES REPORTING INTEGRATION
# ============================================================================

@app.post("/api/v2/companies/{uic}/vies-reports/{period}", response_model=VIESReportResponse)
def generate_vies_report(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Generate VIES report for EU transactions"""
    try:
        service = EnhancedVIESService(db)
        return service.generate_vies_report(uic, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/companies/{uic}/vies-reports/{period}", response_model=VIESReportResponse)
def get_vies_report(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Get existing VIES report"""
    service = EnhancedCompanyService(db)
    company = service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    report = db.query(VIESReport).filter(
        VIESReport.company_id == company.id,
        VIESReport.period == period
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="VIES report not found")
    return report

# ============================================================================
# EXPORT FUNCTIONALITY (NAP Format)
# ============================================================================

@app.post("/api/v2/declarations/{declaration_id}/export")
def export_declaration_to_nap(
    declaration_id: int, 
    export_format: str = Query("XML", pattern="^(XML|JSON)$"),
    db=Depends(get_enhanced_db)
):
    """Export VAT declaration to NAP format"""
    try:
        service = ExportService(db)
        export_log = service.export_vat_declaration(declaration_id, export_format)
        
        if export_log.export_status == "SUCCESS":
            return {
                "export_id": export_log.id,
                "file_name": export_log.file_name,
                "export_status": export_log.export_status,
                "message": "Declaration exported successfully"
            }
        else:
            return {
                "export_id": export_log.id,
                "export_status": export_log.export_status,
                "error": export_log.error_message
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/exports/{export_id}", response_model=ExportLogResponse)
def get_export_status(export_id: int, db=Depends(get_enhanced_db)):
    """Get export status and details"""
    export_log = db.query(ExportLog).filter(ExportLog.id == export_id).first()
    if not export_log:
        raise HTTPException(status_code=404, detail="Export not found")
    return export_log

@app.get("/api/v2/exports/{export_id}/download")
def download_export_file(export_id: int, db=Depends(get_enhanced_db)):
    """Download exported file"""
    export_log = db.query(ExportLog).filter(ExportLog.id == export_id).first()
    if not export_log:
        raise HTTPException(status_code=404, detail="Export not found")
        
    if export_log.export_status != "SUCCESS" or not export_log.file_path:
        raise HTTPException(status_code=400, detail="Export file not available")
        
    # Return file (implementation depends on file storage)
    return FileResponse(
        path=export_log.file_path,
        filename=export_log.file_name,
        media_type='application/xml' if export_log.export_format == 'XML' else 'application/json'
    )

# ============================================================================
# DOCUMENT TYPE MANAGEMENT
# ============================================================================

@app.get("/api/v2/document-types", response_model=List[DocumentTypeMappingResponse])
def get_document_type_mappings(
    category: Optional[str] = Query(None, pattern="^(PURCHASE|SALES)$"),
    active_only: bool = Query(True),
    db=Depends(get_enhanced_db)
):
    """Get document type mappings and validation rules"""
    query = db.query(DocumentTypeMapping)
    
    if category:
        query = query.filter(DocumentTypeMapping.document_category == category)
    if active_only:
        query = query.filter(DocumentTypeMapping.is_active == True)
        
    return query.all()

# ============================================================================
# TRIANGULAR OPERATIONS SUPPORT
# ============================================================================

@app.get("/api/v2/companies/{uic}/triangular-operations/{period}")
def get_triangular_operations(uic: str, period: str, db=Depends(get_enhanced_db)):
    """Get all triangular operations for a period"""
    service = EnhancedCompanyService(db)
    company = service.get_company(uic)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get triangular purchase operations
    triangular_purchases = db.query(EnhancedPurchaseEntry).filter(
        EnhancedPurchaseEntry.company_id == company.id,
        EnhancedPurchaseEntry.period == period,
        EnhancedPurchaseEntry.document_type.in_([11, 12, 13])  # Triangular types
    ).all()
    
    # Get triangular sales operations  
    triangular_sales = db.query(EnhancedSalesEntry).filter(
        EnhancedSalesEntry.company_id == company.id,
        EnhancedSalesEntry.period == period,
        EnhancedSalesEntry.document_type == SalesDocumentType.TRIANGULAR_SALES.value
    ).all()
    
    return {
        "period": period,
        "triangular_purchases": triangular_purchases,
        "triangular_sales": triangular_sales,
        "summary": {
            "purchase_count": len(triangular_purchases),
            "sales_count": len(triangular_sales),
            "total_purchase_amount": sum(p.total_amount or 0 for p in triangular_purchases),
            "total_sales_amount": sum(s.total_amount or 0 for s in triangular_sales)
        }
    }

# ============================================================================
# ENHANCED VIES VALIDATION (Existing but integrated)
# ============================================================================

@app.post("/api/v2/vat/validate-eu-vat")
def validate_eu_vat_number_v2(request: Dict):
    """Enhanced EU VAT validation with logging"""
    try:
        result = vies_validator.validate_vat_number(
            country_code=request.get("country_code"),
            vat_number=request.get("vat_number"),
            requester_country_code=request.get("requester_country_code", "BG"),
            requester_vat=request.get("requester_vat"),
            trader_name=request.get("trader_name"),
            trader_address=request.get("trader_address")
        )
        
        return {
            "country_code": result.country_code,
            "vat_number": result.vat_number,
            "full_vat_number": result.full_vat_number,
            "is_valid": result.is_valid,
            "company_name": result.company_name,
            "company_address": result.company_address,
            "request_date": result.request_date,
            "request_identifier": result.request_identifier,
            "trader_name_match": result.trader_name_match,
            "trader_address_match": result.trader_address_match,
            "error_message": result.error_message,
            "validation_status": result.validation_status
        }
    except Exception as e:
        logger.error(f"VIES validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"VIES validation failed: {str(e)}")

# ============================================================================
# SYSTEM INFORMATION AND STATISTICS
# ============================================================================

@app.get("/api/v2/system/stats")
def get_enhanced_system_stats(db=Depends(get_enhanced_db)):
    """Get enhanced system statistics"""
    stats = get_database_stats()
    
    # Add additional statistics
    stats["system_info"] = {
        "api_version": "3.0.0",
        "supported_document_types": {
            "purchase": len(PurchaseDocumentType),
            "sales": len(SalesDocumentType)
        },
        "features": [
            "All NRA document types (01-94)",
            "Field mapping system (9-25)", 
            "Advanced VAT declarations (fields 1-82)",
            "VIES integration with reporting",
            "NAP export functionality",
            "Triangular operations support",
            "Real-time VIES validation"
        ]
    }
    
    return stats

@app.get("/api/v2/system/health")
def health_check_v2():
    """Enhanced health check"""
    try:
        stats = get_database_stats()
        vies_status = vies_validator.get_vies_availability()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": "3.0.0",
            "database": "connected",
            "vies_service": "available" if vies_status.get("service_available") else "unavailable",
            "features_active": [
                "enhanced_models",
                "all_document_types", 
                "field_mapping",
                "vies_integration",
                "nap_export"
            ]
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
        )

# ============================================================================
# Helper Functions
# ============================================================================

def _get_document_description(doc_type: int) -> str:
    """Get description for purchase document type"""
    descriptions = {
        1: "Standard invoice for purchases",
        2: "Customs import document", 
        3: "Credit note/protocol document",
        5: "Documents per Article 15a (since 01.04.2020)",
        7: "Aggregate invoices",
        9: "Documents without tax credit rights",
        11: "Triangular operations per Article 15",
        12: "Triangular operations per Article 14", 
        13: "Acquisitions per Article 14",
        23: "Documents per Article 126a",
        91: "VAT application per Article 151a, par. 1",
        92: "VAT application per Article 151a, par. 2",
        93: "VAT application per Article 151a, par. 3",
        94: "VAT application per Article 151a, par. 4"
    }
    return descriptions.get(doc_type, "Unknown document type")

def _get_sales_document_description(doc_type: int) -> str:
    """Get description for sales document type"""
    descriptions = {
        1: "Domestic sales invoice",
        2: "EU sales (intra-community delivery)",
        3: "Export sales (outside EU)",
        4: "Triangular sales operations",
        5: "Distance selling",
        6: "Intra-community acquisitions"
    }
    return descriptions.get(doc_type, "Unknown document type")

def _get_field_definitions() -> Dict[str, str]:
    """Get VAT declaration field definitions"""
    return {
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Different port to avoid conflicts