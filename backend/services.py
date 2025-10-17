from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import calendar

from models import Company, PurchaseJournal, SalesJournal, VATDeclaration
from schemas import (
    CompanyCreate, PurchaseJournalCreate, SalesJournalCreate,
    CompanyResponse, PurchaseJournalResponse, SalesJournalResponse, DeclarationResponse
)

class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_company(self, company_data: CompanyCreate) -> Company:
        """Create a new company (Избор на задължено лице)"""
        
        # Generate VAT number: BG + UIC
        vat_number = f"BG{company_data.uic}"
        
        # Check if company already exists
        existing = await self.db.execute(
            select(Company).where(Company.uic == company_data.uic)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Фирма с УИК {company_data.uic} вече съществува")
        
        company = Company(
            uic=company_data.uic,
            vat_number=vat_number,
            name=company_data.name,
            position=company_data.position,
            representative=company_data.representative,
            address=company_data.address
        )
        
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        
        return company
    
    async def get_company(self, uic: str) -> Optional[Company]:
        """Get company by UIC"""
        result = await self.db.execute(
            select(Company).where(Company.uic == uic)
        )
        return result.scalar_one_or_none()
    
    async def list_companies(self) -> List[Company]:
        """List all active companies"""
        result = await self.db.execute(
            select(Company).where(Company.is_active == True).order_by(Company.name)
        )
        return result.scalars().all()

class JournalService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add_purchase_entry(self, uic: str, entry_data: PurchaseJournalCreate) -> PurchaseJournal:
        """Add entry to purchase journal (Дневник на покупките)"""
        
        # Get company
        company = await self._get_company_by_uic(uic)
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        # Validate period format
        if not self._validate_period(entry_data.period):
            raise ValueError("Некоректна година в полето Период - използвайте YYYYMM формат")
        
        entry = PurchaseJournal(
            company_id=company.id,
            period=entry_data.period,
            document_type=entry_data.document_type,
            document_number=entry_data.document_number,
            document_date=entry_data.document_date,
            supplier_name=entry_data.supplier_name,
            supplier_vat=entry_data.supplier_vat,
            tax_base=entry_data.tax_base or 0,
            vat_amount=entry_data.vat_amount or 0,
            total_amount=entry_data.total_amount or 0,
            credit_tax_base=entry_data.credit_tax_base or 0,
            credit_vat=entry_data.credit_vat or 0,
            notes=entry_data.notes
        )
        
        # Handle credit notes (Кредитно известие)
        if entry_data.document_type == 3:
            entry.credit_tax_base = -abs(entry.credit_tax_base or 0)
            entry.credit_vat = -abs(entry.credit_vat or 0)
        
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        
        return entry
    
    async def get_purchases(self, uic: str, period: str) -> List[PurchaseJournal]:
        """Get purchase entries for period"""
        company = await self._get_company_by_uic(uic)
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        result = await self.db.execute(
            select(PurchaseJournal).where(
                and_(
                    PurchaseJournal.company_id == company.id,
                    PurchaseJournal.period == period
                )
            ).order_by(PurchaseJournal.created_at.desc())
        )
        return result.scalars().all()
    
    async def add_sales_entry(self, uic: str, entry_data: SalesJournalCreate) -> SalesJournal:
        """Add entry to sales journal (Дневник за продажбите)"""
        
        company = await self._get_company_by_uic(uic)
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        if not self._validate_period(entry_data.period):
            raise ValueError("Некоректна година в полето Период")
        
        # Auto-calculate 20% VAT if not provided
        vat_20 = entry_data.vat_20
        if entry_data.tax_base_20 and not vat_20:
            vat_20 = entry_data.tax_base_20 * Decimal('0.20')
        
        entry = SalesJournal(
            company_id=company.id,
            period=entry_data.period,
            document_type=entry_data.document_type,
            document_number=entry_data.document_number,
            document_date=entry_data.document_date,
            customer_name=entry_data.customer_name,
            customer_vat=entry_data.customer_vat,
            tax_base_20=entry_data.tax_base_20,
            vat_20=vat_20,
            tax_base_0=entry_data.tax_base_0 or 0,
            tax_base_exempt=entry_data.tax_base_exempt or 0,
            total_amount=(entry_data.tax_base_20 or 0) + (vat_20 or 0),
            notes=entry_data.notes
        )
        
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        
        return entry
    
    async def get_sales(self, uic: str, period: str) -> List[SalesJournal]:
        """Get sales entries for period"""
        company = await self._get_company_by_uic(uic)
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        result = await self.db.execute(
            select(SalesJournal).where(
                and_(
                    SalesJournal.company_id == company.id,
                    SalesJournal.period == period
                )
            ).order_by(SalesJournal.created_at.desc())
        )
        return result.scalars().all()
    
    async def convert_to_credit_note(self, entry_id: int):
        """Convert purchase entry to credit note (Кредитно известие)"""
        result = await self.db.execute(
            select(PurchaseJournal).where(PurchaseJournal.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise ValueError("Записът не е намерен")
        
        # Convert to credit note
        entry.document_type = 3
        entry.credit_tax_base = -abs(entry.tax_base or 0)
        entry.credit_vat = -abs(entry.vat_amount or 0)
        entry.tax_base = 0
        entry.vat_amount = 0
        
        await self.db.commit()
        return entry
    
    async def _get_company_by_uic(self, uic: str) -> Optional[Company]:
        """Helper to get company by UIC"""
        result = await self.db.execute(
            select(Company).where(Company.uic == uic)
        )
        return result.scalar_one_or_none()
    
    def _validate_period(self, period: str) -> bool:
        """Validate YYYYMM period format"""
        if not period or len(period) != 6 or not period.isdigit():
            return False
        
        year = int(period[:4])
        month = int(period[4:])
        
        return (2000 <= year <= 2030) and (1 <= month <= 12)

class DeclarationService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_declaration(self, uic: str, period: str) -> VATDeclaration:
        """Generate VAT declaration (Справка-декларация по ЗДДС и VIES)"""
        
        # Get company
        result = await self.db.execute(
            select(Company).where(Company.uic == uic)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        # Check if declaration already exists
        existing_result = await self.db.execute(
            select(VATDeclaration).where(
                and_(
                    VATDeclaration.company_id == company.id,
                    VATDeclaration.period == period
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            return existing
        
        # Calculate totals from journals
        field_50 = await self._calculate_sales_vat(company.id, period)  # Sales VAT
        field_60 = await self._calculate_purchase_vat(company.id, period)  # Purchase VAT
        
        # Calculate payment or refund
        payment_due = Decimal('0')
        refund_due = Decimal('0')
        field_80 = Decimal('0')
        
        if field_50 > field_60:
            payment_due = field_50 - field_60
        elif field_60 > field_50:
            refund_due = field_60 - field_50
            field_80 = refund_due
        
        # Calculate payment deadline (14th of following month)
        payment_deadline = self._calculate_payment_deadline(period)
        
        declaration = VATDeclaration(
            company_id=company.id,
            period=period,
            field_50=field_50,
            field_60=field_60,
            field_80=field_80,
            payment_due=payment_due,
            refund_due=refund_due,
            payment_deadline=payment_deadline,
            status="DRAFT"
        )
        
        self.db.add(declaration)
        await self.db.commit()
        await self.db.refresh(declaration)
        
        return declaration
    
    async def get_declaration(self, uic: str, period: str) -> Optional[VATDeclaration]:
        """Get existing VAT declaration"""
        result = await self.db.execute(
            select(VATDeclaration)
            .join(Company)
            .where(
                and_(
                    Company.uic == uic,
                    VATDeclaration.period == period
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def submit_to_nap(self, declaration_id: int):
        """Submit declaration to NAP (НАП submission)"""
        result = await self.db.execute(
            select(VATDeclaration).where(VATDeclaration.id == declaration_id)
        )
        declaration = result.scalar_one_or_none()
        
        if not declaration:
            raise ValueError("Декларацията не е намерена")
        
        # TODO: Implement actual NAP integration
        # For now, just mark as submitted
        declaration.status = "SUBMITTED"
        declaration.submission_date = datetime.utcnow()
        declaration.nap_submission_id = f"NAP_{declaration_id}_{int(datetime.utcnow().timestamp())}"
        
        await self.db.commit()
        
        return {
            "success": True,
            "message": "Декларацията е подадена успешно",
            "nap_id": declaration.nap_submission_id
        }
    
    async def _calculate_sales_vat(self, company_id: int, period: str) -> Decimal:
        """Calculate total sales VAT for period (Field 50)"""
        result = await self.db.execute(
            select(SalesJournal).where(
                and_(
                    SalesJournal.company_id == company_id,
                    SalesJournal.period == period
                )
            )
        )
        entries = result.scalars().all()
        
        total = Decimal('0')
        for entry in entries:
            total += entry.vat_20 or 0
        
        return total
    
    async def _calculate_purchase_vat(self, company_id: int, period: str) -> Decimal:
        """Calculate total purchase VAT for period (Field 60)"""
        result = await self.db.execute(
            select(PurchaseJournal).where(
                and_(
                    PurchaseJournal.company_id == company_id,
                    PurchaseJournal.period == period
                )
            )
        )
        entries = result.scalars().all()
        
        total = Decimal('0')
        for entry in entries:
            # Regular VAT
            total += entry.vat_amount or 0
            # Credit note VAT (negative)
            total += entry.credit_vat or 0
        
        return total
    
    def _calculate_payment_deadline(self, period: str) -> datetime:
        """Calculate payment deadline (14th of following month)"""
        year = int(period[:4])
        month = int(period[4:])
        
        # Next month
        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1
        
        deadline = datetime(next_year, next_month, 14)
        
        # If 14th is weekend, extend to next business day
        while deadline.weekday() >= 5:  # Saturday = 5, Sunday = 6
            deadline += timedelta(days=1)
        
        return deadline

class VATCalculationService:
    """VAT calculation utilities"""
    
    def calculate_vat(self, tax_base: Decimal, vat_rate: Decimal = Decimal('0.20')) -> Decimal:
        """Calculate VAT amount"""
        return tax_base * vat_rate
    
    def calculate_total(self, tax_base: Decimal, vat_rate: Decimal = Decimal('0.20')) -> Decimal:
        """Calculate total amount (tax base + VAT)"""
        return tax_base + self.calculate_vat(tax_base, vat_rate)
    
    def calculate_payment_deadline(self, period: str) -> datetime:
        """Calculate payment deadline for period (14th of following month)"""
        year = int(period[:4])
        month = int(period[4:])
        
        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1
        
        deadline = datetime(next_year, next_month, 14)
        
        # Extend to next business day if weekend
        while deadline.weekday() >= 5:
            deadline += timedelta(days=1)
        
        return deadline
    
    def get_business_days_until(self, target_date: datetime) -> int:
        """Calculate business days until target date"""
        current = datetime.now()
        if target_date <= current:
            return 0
        
        days = 0
        while current < target_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days += 1
            current += timedelta(days=1)
        
        return days