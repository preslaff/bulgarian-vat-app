"""
NRA Export Service
Exports VAT declarations in formats required by the Bulgarian National Revenue Agency (НАП)
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date
import tempfile
import os
from io import BytesIO
import zipfile

from models_sync import VATDeclaration, Company, PurchaseJournal, SalesJournal


class NRAExportService:
    """Service for exporting VAT declarations to NRA formats"""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def export_declaration_xml(self, declaration_id: int) -> str:
        """Export VAT declaration as XML file for NRA submission"""
        
        # Get declaration with company info
        declaration = self.db_session.query(VATDeclaration).filter(
            VATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")
        
        company = declaration.company
        
        # Create XML structure according to NRA specifications
        root = ET.Element("Declaration")
        root.set("version", "1.0")
        root.set("xmlns", "http://nra.bg/vat/declaration/2024")
        
        # Header information
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "DeclarationType").text = "VAT_MONTHLY"
        ET.SubElement(header, "Period").text = declaration.period
        ET.SubElement(header, "SubmissionDate").text = datetime.now().strftime("%Y-%m-%d")
        
        # Company information
        company_elem = ET.SubElement(root, "TaxPayer")
        ET.SubElement(company_elem, "UIC").text = company.uic
        ET.SubElement(company_elem, "VATNumber").text = company.vat_number
        ET.SubElement(company_elem, "Name").text = company.name
        ET.SubElement(company_elem, "Address").text = company.address or ""
        ET.SubElement(company_elem, "Representative").text = company.representative or ""
        
        # VAT calculation fields
        vat_data = ET.SubElement(root, "VATData")
        
        # Field 50 - Output VAT (Sales)
        field_50 = ET.SubElement(vat_data, "Field50")
        ET.SubElement(field_50, "Description").text = "ДДС върху доставки и услуги"
        ET.SubElement(field_50, "Amount").text = str(declaration.field_50 or 0)
        
        # Field 60 - Input VAT (Purchases) 
        field_60 = ET.SubElement(vat_data, "Field60")
        ET.SubElement(field_60, "Description").text = "ДДС за възстановяване"
        ET.SubElement(field_60, "Amount").text = str(declaration.field_60 or 0)
        
        # Field 80 - Net VAT amount
        field_80 = ET.SubElement(vat_data, "Field80")
        ET.SubElement(field_80, "Description").text = "ДДС за доплащане/възстановяване"
        ET.SubElement(field_80, "Amount").text = str(declaration.field_80 or 0)
        
        # Payment information
        payment = ET.SubElement(root, "Payment")
        if declaration.payment_due and declaration.payment_due > 0:
            ET.SubElement(payment, "PaymentDue").text = str(declaration.payment_due)
            ET.SubElement(payment, "PaymentDeadline").text = declaration.payment_deadline.strftime("%Y-%m-%d") if declaration.payment_deadline else ""
        elif declaration.refund_due and declaration.refund_due > 0:
            ET.SubElement(payment, "RefundDue").text = str(declaration.refund_due)
        
        # Status and submission info
        status = ET.SubElement(root, "Status")
        ET.SubElement(status, "CurrentStatus").text = declaration.status
        ET.SubElement(status, "CreatedAt").text = declaration.created_at.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Pretty print XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8')
        temp_file.write(pretty_xml)
        temp_file.close()
        
        return temp_file.name
    
    def export_declaration_json(self, declaration_id: int) -> str:
        """Export VAT declaration as JSON file"""
        
        declaration = self.db_session.query(VATDeclaration).filter(
            VATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")
        
        company = declaration.company
        
        # Create JSON structure
        export_data = {
            "declaration": {
                "id": declaration.id,
                "period": declaration.period,
                "status": declaration.status,
                "created_at": declaration.created_at.isoformat(),
                "updated_at": declaration.updated_at.isoformat() if declaration.updated_at else None
            },
            "company": {
                "uic": company.uic,
                "vat_number": company.vat_number,
                "name": company.name,
                "address": company.address,
                "representative": company.representative,
                "position": company.position
            },
            "vat_calculation": {
                "field_50": {
                    "description": "ДДС върху доставки и услуги",
                    "amount": float(declaration.field_50 or 0)
                },
                "field_60": {
                    "description": "ДДС за възстановяване", 
                    "amount": float(declaration.field_60 or 0)
                },
                "field_80": {
                    "description": "ДДС за доплащане/възстановяване",
                    "amount": float(declaration.field_80 or 0)
                }
            },
            "payment": {
                "payment_due": float(declaration.payment_due or 0),
                "refund_due": float(declaration.refund_due or 0),
                "payment_deadline": declaration.payment_deadline.isoformat() if declaration.payment_deadline else None
            }
        }
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(export_data, temp_file, indent=2, ensure_ascii=False)
        temp_file.close()
        
        return temp_file.name
    
    def export_declaration_package(self, declaration_id: int) -> str:
        """Export complete declaration package as ZIP file for NRA submission"""
        
        declaration = self.db_session.query(VATDeclaration).filter(
            VATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")
        
        company = declaration.company
        
        # Create temporary directory for files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Generate individual files
            xml_file = self.export_declaration_xml(declaration_id)
            json_file = self.export_declaration_json(declaration_id)
            
            # Generate supporting documents
            purchase_csv = self._export_purchase_journal_csv(declaration)
            sales_csv = self._export_sales_journal_csv(declaration)
            summary_txt = self._generate_summary_file(declaration)
            
            # Create ZIP package
            zip_filename = f"VAT_Declaration_{company.uic}_{declaration.period}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add declaration files
                zipf.write(xml_file, f"declaration_{declaration.period}.xml")
                zipf.write(json_file, f"declaration_{declaration.period}.json")
                
                # Add supporting documents
                if purchase_csv:
                    zipf.write(purchase_csv, f"purchases_{declaration.period}.csv")
                if sales_csv:
                    zipf.write(sales_csv, f"sales_{declaration.period}.csv")
                if summary_txt:
                    zipf.write(summary_txt, f"summary_{declaration.period}.txt")
            
            # Clean up temporary files
            for temp_file in [xml_file, json_file, purchase_csv, sales_csv, summary_txt]:
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            return zip_path
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
            raise e
    
    def _export_purchase_journal_csv(self, declaration: VATDeclaration) -> Optional[str]:
        """Export purchase journal entries as CSV"""
        
        purchases = self.db_session.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == declaration.company_id,
            PurchaseJournal.period == declaration.period
        ).all()
        
        if not purchases:
            return None
        
        import csv
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')
        
        writer = csv.writer(temp_file, delimiter=';')
        
        # Write header
        writer.writerow([
            'Номер документ',
            'Дата документ',
            'Тип документ', 
            'Име на доставчик',
            'ДДС номер доставчик',
            'Данъчна основа',
            'ДДС сума',
            'Обща сума',
            'Бележки'
        ])
        
        # Write data rows
        for purchase in purchases:
            writer.writerow([
                purchase.document_number,
                purchase.document_date,
                'Фактура' if purchase.document_type == 1 else 'Кредитно известие',
                purchase.supplier_name,
                purchase.supplier_vat or '',
                purchase.tax_base or 0,
                purchase.vat_amount or 0,
                purchase.total_amount or 0,
                purchase.notes or ''
            ])
        
        temp_file.close()
        return temp_file.name
    
    def _export_sales_journal_csv(self, declaration: VATDeclaration) -> Optional[str]:
        """Export sales journal entries as CSV"""
        
        sales = self.db_session.query(SalesJournal).filter(
            SalesJournal.company_id == declaration.company_id,
            SalesJournal.period == declaration.period
        ).all()
        
        if not sales:
            return None
        
        import csv
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')
        
        writer = csv.writer(temp_file, delimiter=';')
        
        # Write header
        writer.writerow([
            'Номер документ',
            'Дата документ',
            'Тип документ',
            'Име на клиент', 
            'ДДС номер клиент',
            'Данъчна основа 20%',
            'ДДС 20%',
            'Данъчна основа 0%',
            'Освободени доставки',
            'Обща сума',
            'Бележки'
        ])
        
        # Write data rows
        for sale in sales:
            writer.writerow([
                sale.document_number,
                sale.document_date,
                'Фактура' if sale.document_type == 1 else 'Кредитно известие',
                sale.customer_name,
                sale.customer_vat or '',
                sale.tax_base_20 or 0,
                sale.vat_20 or 0,
                sale.tax_base_0 or 0,
                sale.tax_base_exempt or 0,
                sale.total_amount or 0,
                sale.notes or ''
            ])
        
        temp_file.close()
        return temp_file.name
    
    def _generate_summary_file(self, declaration: VATDeclaration) -> str:
        """Generate summary text file with declaration overview"""
        
        company = declaration.company
        
        summary_text = f"""СПРАВКА-ДЕКЛАРАЦИЯ ПО ЗДДС И VIES
=================================

ЗАДЪЛЖЕНО ЛИЦЕ:
• Наименование: {company.name}
• УИК: {company.uic}  
• ДДС номер: {company.vat_number}
• Адрес: {company.address or 'Не е указан'}
• Представляван от: {company.representative or 'Не е указан'}

ПЕРИОД: {declaration.period} ({declaration.period[:4]} година, {declaration.period[4:]} месец)

ИЗЧИСЛЕНИЕ НА ДДС:
==================
• Поле 50 - ДДС върху доставки и услуги: {declaration.field_50 or 0:.2f} лв.
• Поле 60 - ДДС за възстановяване: {declaration.field_60 or 0:.2f} лв.
• Поле 80 - ДДС за доплащане/възстановяване: {declaration.field_80 or 0:.2f} лв.

"""
        
        if declaration.payment_due and declaration.payment_due > 0:
            summary_text += f"ЗАДЪЛЖЕНИЕ КЪМ НАП: {declaration.payment_due:.2f} лв.\n"
            if declaration.payment_deadline:
                summary_text += f"Срок за плащане: {declaration.payment_deadline.strftime('%d.%m.%Y')}\n"
        elif declaration.refund_due and declaration.refund_due > 0:
            summary_text += f"ВЪЗСТАНОВЯВАНЕ ОТ НАП: {declaration.refund_due:.2f} лв.\n"
        else:
            summary_text += "НЯМА ЗАДЪЛЖЕНИЕ КЪМ НАП\n"
        
        summary_text += f"""
СТАТУС: {declaration.status}
СЪЗДАНА НА: {declaration.created_at.strftime('%d.%m.%Y %H:%M')}

Този файл е генериран автоматично от VAT Management System v2.0
"""
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(summary_text)
        temp_file.close()
        
        return temp_file.name
    
    def validate_declaration_for_export(self, declaration_id: int) -> List[str]:
        """Validate declaration before export to NRA"""
        
        declaration = self.db_session.query(VATDeclaration).filter(
            VATDeclaration.id == declaration_id
        ).first()
        
        if not declaration:
            return ["Декларацията не е намерена"]
        
        errors = []
        company = declaration.company
        
        # Company validation
        if not company.uic or len(company.uic) not in [9, 13]:
            errors.append("УИК на фирмата трябва да е 9 или 13 цифри")
        
        if not company.vat_number or not company.vat_number.startswith("BG"):
            errors.append("ДДС номерът трябва да започва с 'BG'")
        
        if not company.name:
            errors.append("Наименованието на фирмата е задължително")
        
        # Declaration validation
        if not declaration.period or len(declaration.period) != 6:
            errors.append("Периодът трябва да е във формат YYYYMM")
        
        if declaration.status != "DRAFT":
            errors.append("Само чернови декларации могат да се експортират")
        
        # Check if there are journal entries for the period - allow null declarations
        purchase_count = self.db_session.query(PurchaseJournal).filter(
            PurchaseJournal.company_id == declaration.company_id,
            PurchaseJournal.period == declaration.period
        ).count()
        
        sales_count = self.db_session.query(SalesJournal).filter(
            SalesJournal.company_id == declaration.company_id,
            SalesJournal.period == declaration.period  
        ).count()
        
        # Allow null declarations (no entries is valid for zero declarations)
        # if purchase_count == 0 and sales_count == 0:
        #     errors.append("Няма въведени записи за избрания период")
        
        return errors