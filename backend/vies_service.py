"""
VIES (VAT Information Exchange System) Service

Handles EU VAT reporting requirements for intra-community transactions
as required by Bulgarian ЗДДС (VAT Law) for EU member state transactions.
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session

from models_sync import Company, VATDeclaration
from services_sync import DeclarationService


class VIESEntry:
    """Single VIES entry for intra-EU transaction"""
    
    def __init__(self):
        self.eu_country_code: str = ""          # EU country code (e.g., "DE", "FR")
        self.eu_vat_number: str = ""            # EU VAT number without country prefix
        self.supply_value: Decimal = Decimal('0')    # Value of supplies
        self.acquisition_value: Decimal = Decimal('0')  # Value of acquisitions
        self.triangular_supply: Decimal = Decimal('0')  # Triangular operations


class VIESDeclaration:
    """VIES Declaration for EU VAT reporting"""
    
    def __init__(self):
        self.company_id: int = 0
        self.period: str = ""                   # YYYYMM format
        self.declaration_type: str = "VIES"     # VIES type
        self.entries: List[VIESEntry] = []      # List of EU transactions
        self.total_supplies: Decimal = Decimal('0')
        self.total_acquisitions: Decimal = Decimal('0')
        self.created_at: datetime = datetime.now()


class VIESService:
    """Service for VIES declaration generation and management"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.declaration_service = DeclarationService(db_session)
    
    def generate_vies_declaration(self, company_uic: str, period: str) -> VIESDeclaration:
        """Generate VIES declaration from EU transactions"""
        
        company = self.db.query(Company).filter(Company.uic == company_uic).first()
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        vies_declaration = VIESDeclaration()
        vies_declaration.company_id = company.id
        vies_declaration.period = period
        
        # Extract EU transactions from sales and purchase journals
        eu_entries = self._extract_eu_transactions(company.id, period)
        vies_declaration.entries = eu_entries
        
        # Calculate totals
        vies_declaration.total_supplies = sum(entry.supply_value for entry in eu_entries)
        vies_declaration.total_acquisitions = sum(entry.acquisition_value for entry in eu_entries)
        
        return vies_declaration
    
    def _extract_eu_transactions(self, company_id: int, period: str) -> List[VIESEntry]:
        """Extract EU transactions from journals"""
        
        from models_sync import SalesJournal, PurchaseJournal
        
        eu_entries_dict = {}  # Key: country_code + vat_number, Value: VIESEntry
        
        # Query sales journal for EU customers
        sales_query = self.db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.period == period,
            SalesJournal.customer_vat.isnot(None)
        )
        
        for sale in sales_query:
            if sale.customer_vat and self._is_eu_vat_number(sale.customer_vat):
                country_code, vat_number = self._parse_eu_vat_number(sale.customer_vat)
                if country_code and vat_number:
                    key = f"{country_code}:{vat_number}"
                    if key not in eu_entries_dict:
                        entry = VIESEntry()
                        entry.eu_country_code = country_code
                        entry.eu_vat_number = vat_number
                        eu_entries_dict[key] = entry
                    
                    # Add supply value (sales to EU customers)
                    eu_entries_dict[key].supply_value += sale.tax_base_20 or Decimal('0')
        
        # Query purchase journal for EU suppliers
        purchase_query = self.db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.period == period,
            PurchaseJournal.supplier_vat.isnot(None)
        )
        
        for purchase in purchase_query:
            if purchase.supplier_vat and self._is_eu_vat_number(purchase.supplier_vat):
                country_code, vat_number = self._parse_eu_vat_number(purchase.supplier_vat)
                if country_code and vat_number:
                    key = f"{country_code}:{vat_number}"
                    if key not in eu_entries_dict:
                        entry = VIESEntry()
                        entry.eu_country_code = country_code
                        entry.eu_vat_number = vat_number
                        eu_entries_dict[key] = entry
                    
                    # Add acquisition value (purchases from EU suppliers)
                    eu_entries_dict[key].acquisition_value += purchase.tax_base or Decimal('0')
        
        return list(eu_entries_dict.values())
    
    def _is_eu_vat_number(self, vat_number: str) -> bool:
        """Check if VAT number is EU format (excludes BG numbers)"""
        if not vat_number or len(vat_number) < 4:
            return False
        
        eu_countries = {
            'AT', 'BE', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 
            'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 
            'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
        }
        
        country_code = vat_number[:2].upper()
        return country_code in eu_countries
    
    def _parse_eu_vat_number(self, vat_number: str) -> Tuple[str, str]:
        """Parse EU VAT number into country code and national number"""
        if len(vat_number) < 4:
            return "", ""
        
        country_code = vat_number[:2].upper()
        national_number = vat_number[2:].strip()
        
        return country_code, national_number
    
    def export_vies_xml(self, vies_declaration: VIESDeclaration) -> str:
        """Export VIES declaration as XML for EU submission"""
        
        company = self.db.query(Company).filter(Company.id == vies_declaration.company_id).first()
        
        root = ET.Element("VIESDeclaration")
        root.set("version", "1.0")
        root.set("xmlns", "http://ec.europa.eu/taxation_customs/vies/2024")
        
        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "DeclarationType").text = "VIES"
        ET.SubElement(header, "Period").text = vies_declaration.period
        ET.SubElement(header, "SubmissionDate").text = datetime.now().strftime("%Y-%m-%d")
        
        # Declarant (Bulgarian company)
        declarant = ET.SubElement(root, "Declarant")
        ET.SubElement(declarant, "CountryCode").text = "BG"
        ET.SubElement(declarant, "VATNumber").text = company.vat_number.replace("BG", "")
        ET.SubElement(declarant, "Name").text = company.name
        
        # EU Partners
        if vies_declaration.entries:
            partners = ET.SubElement(root, "EUPartners")
            
            for entry in vies_declaration.entries:
                partner = ET.SubElement(partners, "Partner")
                ET.SubElement(partner, "CountryCode").text = entry.eu_country_code
                ET.SubElement(partner, "VATNumber").text = entry.eu_vat_number
                
                if entry.supply_value > 0:
                    ET.SubElement(partner, "SupplyValue").text = str(entry.supply_value)
                
                if entry.acquisition_value > 0:
                    ET.SubElement(partner, "AcquisitionValue").text = str(entry.acquisition_value)
                
                if entry.triangular_supply > 0:
                    ET.SubElement(partner, "TriangularSupply").text = str(entry.triangular_supply)
        
        # Summary
        summary = ET.SubElement(root, "Summary")
        ET.SubElement(summary, "TotalSupplies").text = str(vies_declaration.total_supplies)
        ET.SubElement(summary, "TotalAcquisitions").text = str(vies_declaration.total_acquisitions)
        ET.SubElement(summary, "NumberOfPartners").text = str(len(vies_declaration.entries))
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def validate_vies_declaration(self, vies_declaration: VIESDeclaration) -> List[str]:
        """Validate VIES declaration for errors"""
        
        errors = []
        warnings = []
        
        # Check if period is valid
        if not self._validate_period(vies_declaration.period):
            errors.append("Некоректен формат на периода (YYYYMM)")
        
        # Check if period is not in the future
        from datetime import datetime
        current_period = datetime.now().strftime("%Y%m")
        if vies_declaration.period > current_period:
            errors.append("Периодът не може да бъде в бъдещето")
        
        # Check if there are EU transactions
        if not vies_declaration.entries:
            warnings.append("Няма записи за ЕС операции за избрания период")
        
        # Validate each EU entry
        duplicate_partners = set()
        for i, entry in enumerate(vies_declaration.entries):
            partner_key = f"{entry.eu_country_code}{entry.eu_vat_number}"
            
            # Check for duplicate partners
            if partner_key in duplicate_partners:
                errors.append(f"Дублиращ се ЕС партньор в запис {i+1}: {partner_key}")
            else:
                duplicate_partners.add(partner_key)
            
            # Validate VAT number format
            if not self._validate_eu_vat_number(entry.eu_country_code, entry.eu_vat_number):
                errors.append(f"Некоректен ЕС ДДС номер за запис {i+1}: {entry.eu_country_code}{entry.eu_vat_number}")
            
            # Check for negative values
            if entry.supply_value < 0 or entry.acquisition_value < 0:
                errors.append(f"Отрицателни стойности в запис {i+1}")
            
            # Check for zero values (warning only)
            if entry.supply_value == 0 and entry.acquisition_value == 0:
                warnings.append(f"Нулеви стойности в запис {i+1} за партньор {partner_key}")
            
            # Validate triangular operations
            if entry.triangular_supply > 0:
                if entry.supply_value == 0:
                    errors.append(f"Тристранна операция без основна доставка в запис {i+1}")
            
            # Check for very large amounts (potential data entry errors)
            if entry.supply_value > Decimal('10000000') or entry.acquisition_value > Decimal('10000000'):
                warnings.append(f"Много голяма сума в запис {i+1} - моля проверете: {partner_key}")
        
        # Validate totals consistency
        calculated_supplies = sum(entry.supply_value for entry in vies_declaration.entries)
        calculated_acquisitions = sum(entry.acquisition_value for entry in vies_declaration.entries)
        
        if abs(calculated_supplies - vies_declaration.total_supplies) > Decimal('0.01'):
            errors.append(f"Несъответствие в общите доставки: изчислено {calculated_supplies}, записано {vies_declaration.total_supplies}")
        
        if abs(calculated_acquisitions - vies_declaration.total_acquisitions) > Decimal('0.01'):
            errors.append(f"Несъответствие в общите придобивания: изчислено {calculated_acquisitions}, записано {vies_declaration.total_acquisitions}")
        
        # Combine errors and warnings
        all_issues = errors.copy()
        if warnings:
            all_issues.extend([f"ПРЕДУПРЕЖДЕНИЕ: {w}" for w in warnings])
        
        return all_issues
    
    def _validate_period(self, period: str) -> bool:
        """Validate YYYYMM period format"""
        if not period or len(period) != 6 or not period.isdigit():
            return False
        
        year = int(period[:4])
        month = int(period[4:])
        
        return (2000 <= year <= 2030) and (1 <= month <= 12)
    
    def _validate_eu_vat_number(self, country_code: str, vat_number: str) -> bool:
        """Validate EU VAT number format with country-specific rules"""
        
        # EU country codes with their VAT number length requirements
        eu_vat_rules = {
            'AT': (8, 8),    # Austria: U12345678
            'BE': (9, 10),   # Belgium: 0123456789
            'BG': (9, 10),   # Bulgaria: 123456789
            'HR': (11, 11),  # Croatia: 12345678901
            'CY': (8, 8),    # Cyprus: 12345678L
            'CZ': (8, 10),   # Czech Republic: 12345678 or 1234567890
            'DK': (8, 8),    # Denmark: 12345678
            'EE': (9, 9),    # Estonia: 123456789
            'FI': (8, 8),    # Finland: 12345678
            'FR': (11, 11),  # France: 12345678901 or AB123456789
            'DE': (9, 9),    # Germany: 123456789
            'GR': (9, 9),    # Greece: 123456789
            'HU': (8, 8),    # Hungary: 12345678
            'IE': (8, 9),    # Ireland: 1234567A or 1A23456A
            'IT': (11, 11),  # Italy: 12345678901
            'LV': (11, 11),  # Latvia: 12345678901
            'LT': (9, 12),   # Lithuania: 123456789 or 123456789012
            'LU': (8, 8),    # Luxembourg: 12345678
            'MT': (8, 8),    # Malta: 12345678
            'NL': (12, 12),  # Netherlands: 123456789B01
            'PL': (10, 10),  # Poland: 1234567890
            'PT': (9, 9),    # Portugal: 123456789
            'RO': (2, 10),   # Romania: 12 to 1234567890
            'SK': (10, 10),  # Slovakia: 1234567890
            'SI': (8, 8),    # Slovenia: 12345678
            'ES': (9, 9),    # Spain: 123456789 or A12345674
            'SE': (12, 12),  # Sweden: 123456789012
        }
        
        if country_code not in eu_vat_rules:
            return False
        
        min_len, max_len = eu_vat_rules[country_code]
        
        if not vat_number or len(vat_number) < min_len or len(vat_number) > max_len:
            return False
        
        # Additional country-specific validation
        if country_code == 'FR':
            # French VAT can be numeric or start with letters
            return vat_number.isdigit() or (len(vat_number) == 11 and vat_number[2:].isdigit())
        elif country_code == 'IE':
            # Irish VAT format: 7digits + letter or 1letter + 6digits + 1letter
            return (len(vat_number) == 8 and vat_number[:7].isdigit() and vat_number[7].isalpha()) or \
                   (len(vat_number) == 9 and vat_number[0].isalpha() and vat_number[1:7].isdigit() and vat_number[8].isalpha())
        elif country_code == 'ES':
            # Spanish VAT: all digits or letter + 7digits + letter/digit
            return vat_number.isdigit() or (vat_number[0].isalpha() and vat_number[1:8].isdigit())
        elif country_code == 'NL':
            # Dutch VAT: 9 digits + 'B' + 2 digits
            return len(vat_number) == 12 and vat_number[:9].isdigit() and vat_number[9] == 'B' and vat_number[10:].isdigit()
        else:
            # For other countries, basic digit validation
            return vat_number.isdigit()
        
        return True


class ReportingProtocolService:
    """Service for generating comprehensive reporting protocol (СПРАВКА-ПРОТОКОЛ)"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.declaration_service = DeclarationService(db_session)
    
    def generate_reporting_protocol(self, company_uic: str, period: str) -> str:
        """Generate comprehensive reporting protocol in Bulgarian"""
        
        company = self.db.query(Company).filter(Company.uic == company_uic).first()
        if not company:
            raise ValueError("Фирмата не е намерена")
        
        # Get VAT declaration
        vat_declaration = self.declaration_service.generate_declaration(company_uic, period)
        
        # Build reporting protocol text
        protocol = []
        protocol.append("СПРАВКА-ПРОТОКОЛ")
        protocol.append(f"Текуща дата:{datetime.now().strftime('%d/%m/%Y')}")
        protocol.append("")
        protocol.append(f"Идентификационен номер:{company.vat_number}")
        protocol.append(f"Наименование:{company.name}")
        protocol.append(f"Данъчен период:{period}")
        protocol.append(f"Лице, подаващо данните:{company.representative or ''}")
        protocol.append("")
        
        # Sales Journal Section
        protocol.append("Дневник за продажбите             Суми по колони  | Сума от СД за ДДС")
        sales_entries = self._get_sales_summary(company.id, period)
        protocol.append(f"Брой записи:               {sales_entries['count']}")
        protocol.append(f"/в deklar/:                {sales_entries['count']}")
        protocol.append("")
        
        # Detailed sales fields
        protocol.extend(self._generate_sales_fields(sales_entries, vat_declaration))
        protocol.append("")
        
        # Purchase Journal Section
        protocol.append("Дневник за покупките                 Суми по колони  | Сума от СД за ДДС")
        purchase_entries = self._get_purchase_summary(company.id, period)
        protocol.append(f"Брой записи:               {purchase_entries['count']}")
        protocol.append(f"/в deklar/:                {purchase_entries['count']}")
        protocol.append("")
        
        # Detailed purchase fields
        protocol.extend(self._generate_purchase_fields(purchase_entries, vat_declaration))
        protocol.append("")
        
        # VAT Declaration Summary
        protocol.append("СПРАВКА ДЕКЛАРАЦИЯ ЗА ДДС")
        protocol.extend(self._generate_declaration_summary(vat_declaration))
        protocol.append("")
        
        # File Validation Results
        protocol.extend(self._generate_validation_results(company.id, period))
        
        return "\n".join(protocol)
    
    def _get_sales_summary(self, company_id: int, period: str) -> Dict:
        """Get summary of sales journal entries"""
        from models_sync import SalesJournal
        
        sales_query = self.db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.period == period
        )
        
        # Initialize all VAT fields according to Bulgarian requirements
        summary = {
            'count': sales_query.count(),
            'field_09': Decimal('0'),  # Общ размер на ДО за облагане с ДДС
            'field_10': Decimal('0'),  # Всичко начислен ДДС
            'field_11': Decimal('0'),  # ДО на обл.дост.20%
            'field_12': Decimal('0'),  # Начислен ДДС за доставки по к.11
            'field_13': Decimal('0'),  # ДО на ВОП (вътрешно-общностни поставки)
            'field_14': Decimal('0'),  # ДО на пол.доставки по чл.82,ал2-6 ЗДДС
            'field_15': Decimal('0'),  # ДО на освободени доставки
            'field_16': Decimal('0'),  # ДО освободени от ДДС с право на ДК
            'field_17': Decimal('0'),  # ДО освободени от ДДС без право на ДК
            'field_18': Decimal('0'),  # ДО на туристически услуги
            'field_19': Decimal('0'),  # ДО на обложими стоки и услуги на 9%
            'field_20': Decimal('0'),  # Начислен ДДС 9%
            'field_21': Decimal('0'),  # ДО на други обложими доставки
            'field_22': Decimal('0'),  # Начислен ДДС за други доставки
            'field_23': Decimal('0'),  # ДО на самоначисляване
            'field_24': Decimal('0'),  # ДДС при самоначисляване
            'field_25': Decimal('0'),  # Получени аванси
        }
        
        # Calculate actual values from sales journal
        for sale in sales_query:
            # Standard 20% VAT deliveries
            summary['field_11'] += sale.tax_base_20 or Decimal('0')
            summary['field_12'] += sale.vat_20 or Decimal('0')
            
            # Check if customer is EU (for field_13 - intra-community supplies)
            if sale.customer_vat and self._is_eu_vat_number(sale.customer_vat):
                summary['field_13'] += sale.tax_base_20 or Decimal('0')
            
            # 0% deliveries
            summary['field_15'] += sale.tax_base_0 or Decimal('0')
            summary['field_16'] += sale.tax_base_exempt or Decimal('0')
        
        # Calculate totals
        summary['field_09'] = summary['field_11'] + summary['field_13'] + summary['field_15']
        summary['field_10'] = summary['field_12'] + summary['field_20'] + summary['field_22'] + summary['field_24']
        
        return summary
    
    def _get_purchase_summary(self, company_id: int, period: str) -> Dict:
        """Get summary of purchase journal entries"""
        from models_sync import PurchaseJournal
        
        purchase_query = self.db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.period == period
        )
        
        # Initialize all purchase VAT fields according to Bulgarian requirements
        summary = {
            'count': purchase_query.count(),
            'field_09': Decimal('0'),  # ДО и данък на доставките без ДК
            'field_10': Decimal('0'),  # ДО на доставки с пълен ДК
            'field_11': Decimal('0'),  # ДДС - пълен ДК
            'field_12': Decimal('0'),  # ДО на доставки с частичен ДК
            'field_13': Decimal('0'),  # ДДС - частичен ДК
            'field_14': Decimal('0'),  # Годишна корекция
            'field_15': Decimal('0'),  # ДО тристранна операция
            'total_tax_base': Decimal('0'),
            'total_vat': Decimal('0'),
        }
        
        # Calculate actual values from purchase journal
        for purchase in purchase_query:
            # Most purchases have full deduction rights
            tax_base = purchase.tax_base or Decimal('0')
            vat_amount = purchase.vat_amount or Decimal('0')
            
            # Check if supplier is EU (for triangular operations)
            if purchase.supplier_vat and self._is_eu_vat_number(purchase.supplier_vat):
                summary['field_15'] += tax_base
            else:
                # Domestic purchases with full deduction
                summary['field_10'] += tax_base
                summary['field_11'] += vat_amount
            
            # Handle non-VAT items
            summary['field_09'] += purchase.total_amount or Decimal('0')
            
            summary['total_tax_base'] += tax_base
            summary['total_vat'] += vat_amount
        
        return summary
    
    def _generate_sales_fields(self, sales_data: Dict, declaration) -> List[str]:
        """Generate detailed sales fields for protocol"""
        return [
            f" 9. Общ размер на ДО за облагане с ДДС    :    {sales_data['field_09']:12.2f} |    {sales_data['field_09']:12.2f}",
            f"10. Всичко начислен ДДС            :    {sales_data['field_10']:12.2f} |    {sales_data['field_10']:12.2f}",
            f"11. ДО на обл.дост.20%            :    {sales_data['field_11']:12.2f} |    {sales_data['field_11']:12.2f}",
            f"12. Начислен ДДС за доставки по к.11 и нач.",
            f"данък 20%, предвиден в закона в др.случаи:    {sales_data['field_12']:12.2f} |    {sales_data['field_12']:12.2f}",
            f"13. ДО на ВОП                    :    {sales_data['field_13']:12.2f} |",
            f"14. ДО на пол.доставки по чл.82,ал2-6 ЗДДС:    {sales_data['field_14']:12.2f} |    {sales_data['field_14']:12.2f}",
            f"15. ДО на освободени доставки            :    {sales_data['field_15']:12.2f} |",
            f"16. ДО освободени от ДДС с право на ДК    :    {sales_data['field_16']:12.2f} |",
            f"17. ДО освободени от ДДС без право на ДК    :    {sales_data['field_17']:12.2f} |",
            f"18. ДО на туристически услуги        :    {sales_data['field_18']:12.2f} |",
            f"19. ДО на обложими стоки и услуги на 9%    :    {sales_data['field_19']:12.2f} |    {sales_data['field_19']:12.2f}",
            f"20. Начислен ДДС 9%                :    {sales_data['field_20']:12.2f} |    {sales_data['field_20']:12.2f}",
            f"21. ДО на други обложими доставки        :    {sales_data['field_21']:12.2f} |    {sales_data['field_21']:12.2f}",
            f"22. Начислен ДДС за други доставки        :    {sales_data['field_22']:12.2f} |    {sales_data['field_22']:12.2f}",
            f"23. ДО на самоначисляване            :    {sales_data['field_23']:12.2f} |    {sales_data['field_23']:12.2f}",
            f"24. ДДС при самоначисляване            :    {sales_data['field_24']:12.2f} |    {sales_data['field_24']:12.2f}",
            f"25. Получени аванси                :    {sales_data['field_25']:12.2f} |    {sales_data['field_25']:12.2f}"
        ]
    
    def _generate_purchase_fields(self, purchase_data: Dict, declaration) -> List[str]:
        """Generate detailed purchase fields for protocol"""
        total_fields_9_15 = purchase_data['field_09'] + purchase_data['field_15']
        return [
            f" 9. ДО и данък на доставките без ДК    :    {purchase_data['field_09']:12.2f}",
            f"10. ДО на доставки с пълен ДК        :    {purchase_data['field_10']:12.2f} |    {purchase_data['field_10']:12.2f}",
            f"11. ДДС - пълен ДК                :    {purchase_data['field_11']:12.2f} |    {purchase_data['field_11']:12.2f}",
            f"12. ДО на доставки с частичен ДК        :    {purchase_data['field_12']:12.2f} |    {purchase_data['field_12']:12.2f}",
            f"13. ДДС - частичен ДК            :    {purchase_data['field_13']:12.2f} |    {purchase_data['field_13']:12.2f}",
            f"14. Годишна корекция                :    {purchase_data['field_14']:12.2f} |    {purchase_data['field_14']:12.2f}",
            f"15. ДО тристранна операция            :    {purchase_data['field_15']:12.2f}",
            f"                        Общо к.9 +к.15    :    {total_fields_9_15:12.2f} |    {purchase_data['total_vat']:12.2f}"
        ]
    
    def _generate_declaration_summary(self, declaration) -> List[str]:
        """Generate VAT declaration summary"""
        return [
            f"                        Общо ДДС                :                |            {declaration.field_50}",
            f"Общо ДК (кл.41+кл.42*кл.33+кл.43)            :           0.00 |           {declaration.field_60}",
            f"ДДС за внасяне (кл.20-кл.40>=0)            :           0.00 |           {declaration.payment_due}",
            f"ДДС за възстановяване (кл.20-кл.40<0)        :                |           {declaration.refund_due}"
        ]
    
    def _generate_validation_results(self, company_id: int, period: str) -> List[str]:
        """Generate comprehensive validation results"""
        from models_sync import SalesJournal, PurchaseJournal
        
        validation_errors = []
        validation_warnings = []
        
        # Validate sales journal
        sales_query = self.db.query(SalesJournal).filter(
            SalesJournal.company_id == company_id,
            SalesJournal.period == period
        )
        
        for sale in sales_query:
            # Check for missing required fields
            if not sale.document_number:
                validation_errors.append(f"Продажби: Липсва номер на документа за запис ID {sale.id}")
            
            if not sale.document_date:
                validation_errors.append(f"Продажби: Липсва дата на документа за запис ID {sale.id}")
            
            if not sale.customer_name:
                validation_warnings.append(f"Продажби: Липсва име на клиента за запис ID {sale.id}")
            
            # Validate VAT calculations
            if sale.tax_base_20 and sale.vat_20:
                expected_vat = sale.tax_base_20 * Decimal('0.20')
                if abs(expected_vat - sale.vat_20) > Decimal('0.01'):
                    validation_errors.append(f"Продажби: Некоректен ДДС за запис ID {sale.id} - очакван {expected_vat}, намерен {sale.vat_20}")
            
            # Check for negative amounts
            if sale.tax_base_20 and sale.tax_base_20 < 0:
                validation_errors.append(f"Продажби: Отрицателна данъчна основа за запис ID {sale.id}")
            
            if sale.vat_20 and sale.vat_20 < 0:
                validation_errors.append(f"Продажби: Отрицателен ДДС за запис ID {sale.id}")
        
        # Validate purchase journal
        purchase_query = self.db.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == company_id,
            PurchaseJournal.period == period
        )
        
        for purchase in purchase_query:
            # Check for missing required fields
            if not purchase.document_number:
                validation_errors.append(f"Покупки: Липсва номер на документа за запис ID {purchase.id}")
            
            if not purchase.document_date:
                validation_errors.append(f"Покупки: Липсва дата на документа за запис ID {purchase.id}")
            
            if not purchase.supplier_name:
                validation_warnings.append(f"Покупки: Липсва име на доставчика за запис ID {purchase.id}")
            
            # Validate VAT calculations
            if purchase.tax_base and purchase.vat_amount:
                expected_vat = purchase.tax_base * Decimal('0.20')
                if abs(expected_vat - purchase.vat_amount) > Decimal('0.01'):
                    validation_errors.append(f"Покупки: Некоректен ДДС за запис ID {purchase.id} - очакван {expected_vat}, намерен {purchase.vat_amount}")
            
            # Check for negative amounts
            if purchase.tax_base and purchase.tax_base < 0:
                validation_errors.append(f"Покупки: Отрицателна данъчна основа за запис ID {purchase.id}")
            
            if purchase.vat_amount and purchase.vat_amount < 0:
                validation_errors.append(f"Покупки: Отрицателен ДДС за запис ID {purchase.id}")
        
        # Build validation report
        results = [
            "",
            "Проверка на файл DEKLAR",
            "",
        ]
        
        if not validation_errors:
            results.append("Няма открити грешки в DEKLAR")
        else:
            results.extend([f"ГРЕШКА: {error}" for error in validation_errors[:5]])  # Show first 5 errors
            if len(validation_errors) > 5:
                results.append(f"... и още {len(validation_errors) - 5} грешки")
        
        results.extend([
            "",
            "Проверка на файл ПОКУПКИ",
            "",
        ])
        
        purchase_errors = [e for e in validation_errors if "Покупки:" in e]
        if not purchase_errors:
            results.append("Няма открити грешки в ПОКУПКИ")
        else:
            results.extend([f"ГРЕШКА: {error}" for error in purchase_errors[:3]])
        
        results.extend([
            "",
            "Проверка на файл ПРОДАЖБИ",
            "",
        ])
        
        sales_errors = [e for e in validation_errors if "Продажби:" in e]
        if not sales_errors:
            results.append("Няма открити грешки в ПРОДАЖБИ")
        else:
            results.extend([f"ГРЕШКА: {error}" for error in sales_errors[:3]])
        
        results.extend([
            "",
            "ФАТАЛНИ ГРЕШКИ",
            "",
        ])
        
        fatal_errors = [e for e in validation_errors if "Отрицателн" in e or "Некоректен" in e]
        if not fatal_errors:
            results.append("Няма открити фатални грешки")
        else:
            results.append(f"ВНИМАНИЕ: Открити {len(fatal_errors)} фатални грешки!")
            results.extend([f"ФАТАЛНО: {error}" for error in fatal_errors[:3]])
        
        if validation_warnings:
            results.extend([
                "",
                "ПРЕДУПРЕЖДЕНИЯ",
                "",
            ])
            results.extend([f"ВНИМАНИЕ: {warning}" for warning in validation_warnings[:5]])
        
        return results