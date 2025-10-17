"""
VAT Excel Template Generator
Generates Excel templates for Bulgarian VAT journal imports
"""

import pandas as pd
import tempfile
import os
from datetime import datetime
from typing import Dict, List


class VATTemplateGenerator:
    """Generate Excel templates for VAT data import"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def create_template(self, journal_type: str = "purchase") -> str:
        """Create Excel template with sample data and formatting"""
        
        if journal_type == "purchase":
            return self._create_purchase_template()
        elif journal_type == "sales":
            return self._create_sales_template()
        else:
            raise ValueError("Journal type must be 'purchase' or 'sales'")
    
    def _create_purchase_template(self) -> str:
        """Create purchase journal template"""
        
        # Sample purchase data
        sample_data = [
            {
                'document_number': 'INV-2024-001',
                'document_date': '2024-01-15',
                'document_type': 1,  # Invoice
                'supplier_name': 'ООД "Техносервиз"',
                'supplier_uic': '123456789',
                'supplier_vat_number': 'BG123456789',
                'description': 'Доставка на офис материали',
                'tax_base': 100.00,
                'vat_rate': 0.20,
                'vat_amount': 20.00,
                'total_amount': 120.00,
                'notes': 'Фактура за офис консумативи'
            },
            {
                'document_number': 'INV-2024-002', 
                'document_date': '2024-01-20',
                'document_type': 1,  # Invoice
                'supplier_name': 'ЕООД "Софтуер Плюс"',
                'supplier_uic': '987654321',
                'supplier_vat_number': 'BG987654321',
                'description': 'Лицензи за софтуер',
                'tax_base': 500.00,
                'vat_rate': 0.20,
                'vat_amount': 100.00,
                'total_amount': 600.00,
                'notes': 'Годишни лицензи за Microsoft Office'
            },
            {
                'document_number': 'CN-2024-001',
                'document_date': '2024-01-25',
                'document_type': 3,  # Credit Note
                'supplier_name': 'ООД "Техносервиз"',
                'supplier_uic': '123456789', 
                'supplier_vat_number': 'BG123456789',
                'description': 'Кредитно известие - връщане стоки',
                'tax_base': -25.00,
                'vat_rate': 0.20,
                'vat_amount': -5.00,
                'total_amount': -30.00,
                'notes': 'Връщане на дефектни материали'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        # Generate template file
        template_path = os.path.join(self.temp_dir, f"VAT_purchase_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        with pd.ExcelWriter(template_path, engine='xlsxwriter') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Purchase_Journal', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Purchase_Journal']
            
            # Add formatting
            self._format_purchase_worksheet(workbook, worksheet, df)
            
            # Add instructions sheet
            self._add_instructions_sheet(writer, workbook, 'purchase')
            
            # Add validation sheet
            self._add_validation_sheet(writer, workbook)
        
        return template_path
    
    def _create_sales_template(self) -> str:
        """Create sales journal template"""
        
        # Sample sales data  
        sample_data = [
            {
                'document_number': 'SALE-2024-001',
                'document_date': '2024-01-10',
                'document_type': 1,  # Invoice
                'customer_name': 'ООД "Клиент Партнер"',
                'customer_uic': '555666777',
                'customer_vat_number': 'BG555666777',
                'description': 'Продажба на стоки',
                'tax_base': 200.00,
                'vat_rate': 0.20,
                'vat_amount': 40.00,
                'total_amount': 240.00,
                'notes': 'Месечна доставка'
            },
            {
                'document_number': 'SALE-2024-002',
                'document_date': '2024-01-15',
                'document_type': 1,  # Invoice
                'customer_name': 'ЕООД "Търговец"',
                'customer_uic': '888999000',
                'customer_vat_number': 'BG888999000',
                'description': 'Предоставяне на услуги',
                'tax_base': 300.00,
                'vat_rate': 0.20,
                'vat_amount': 60.00,
                'total_amount': 360.00,
                'notes': 'Консултантски услуги'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        # Generate template file
        template_path = os.path.join(self.temp_dir, f"VAT_sales_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        with pd.ExcelWriter(template_path, engine='xlsxwriter') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Sales_Journal', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Sales_Journal']
            
            # Add formatting
            self._format_sales_worksheet(workbook, worksheet, df)
            
            # Add instructions sheet
            self._add_instructions_sheet(writer, workbook, 'sales')
            
            # Add validation sheet
            self._add_validation_sheet(writer, workbook)
        
        return template_path
    
    def _format_purchase_worksheet(self, workbook, worksheet, df):
        """Format purchase template worksheet"""
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00 лв.',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd.mm.yyyy',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1
        })
        
        # Set column widths and formats
        column_formats = {
            'A': (15, text_format),    # document_number
            'B': (12, date_format),    # document_date  
            'C': (12, text_format),    # document_type
            'D': (25, text_format),    # supplier_name
            'E': (15, text_format),    # supplier_uic
            'F': (15, text_format),    # supplier_vat_number
            'G': (30, text_format),    # description
            'H': (12, currency_format), # tax_base
            'I': (8, text_format),     # vat_rate
            'J': (12, currency_format), # vat_amount
            'K': (12, currency_format), # total_amount
            'L': (30, text_format)     # notes
        }
        
        for col, (width, format_obj) in column_formats.items():
            worksheet.set_column(f'{col}:{col}', width)
            worksheet.set_column(f'{col}2:{col}1000', None, format_obj)
        
        # Format headers
        for col_num, column in enumerate(df.columns):
            worksheet.write(0, col_num, column, header_format)
        
        # Freeze first row
        worksheet.freeze_panes(1, 0)
    
    def _format_sales_worksheet(self, workbook, worksheet, df):
        """Format sales template worksheet"""
        
        # Define formats (similar to purchase)
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'fg_color': '#C6E0B4',  # Different color for sales
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00 лв.',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd.mm.yyyy',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1
        })
        
        # Set column widths and formats (same structure as purchase)
        column_formats = {
            'A': (15, text_format),    # document_number
            'B': (12, date_format),    # document_date
            'C': (12, text_format),    # document_type
            'D': (25, text_format),    # customer_name
            'E': (15, text_format),    # customer_uic
            'F': (15, text_format),    # customer_vat_number
            'G': (30, text_format),    # description
            'H': (12, currency_format), # tax_base
            'I': (8, text_format),     # vat_rate
            'J': (12, currency_format), # vat_amount
            'K': (12, currency_format), # total_amount
            'L': (30, text_format)     # notes
        }
        
        for col, (width, format_obj) in column_formats.items():
            worksheet.set_column(f'{col}:{col}', width)
            worksheet.set_column(f'{col}2:{col}1000', None, format_obj)
        
        # Format headers
        for col_num, column in enumerate(df.columns):
            worksheet.write(0, col_num, column, header_format)
        
        # Freeze first row
        worksheet.freeze_panes(1, 0)
    
    def _add_instructions_sheet(self, writer, workbook, journal_type):
        """Add instructions sheet to template"""
        
        instructions_data = {
            'purchase': [
                ['ИНСТРУКЦИИ ЗА ПОПЪЛВАНЕ - ДНЕВНИК НА ПОКУПКИТЕ', ''],
                ['', ''],
                ['Задължителни полета:', ''],
                ['document_number', 'Номер на документа (фактура, кредитно известие)'],
                ['document_date', 'Дата на документа (формат: YYYY-MM-DD)'],
                ['document_type', '1 = Фактура, 3 = Кредитно известие'],
                ['supplier_name', 'Име на доставчика'],
                ['supplier_uic', 'ЕИК/БУЛСТАТ на доставчика'],
                ['tax_base', 'Данъчна основа (без ДДС)'],
                ['vat_rate', 'ДДС ставка (0.20 за 20%)'],
                ['vat_amount', 'Сума ДДС'],
                ['total_amount', 'Обща сума (с ДДС)'],
                ['', ''],
                ['Незадължителни полета:', ''],
                ['supplier_vat_number', 'ДДС номер на доставчика (BGxxxxxxxxx)'],
                ['description', 'Описание на стоките/услугите'],
                ['notes', 'Допълнителни бележки'],
                ['', ''],
                ['ВАЖНИ ЗАБЕЛЕЖКИ:', ''],
                ['• За кредитни известия използвайте отрицателни стойности', ''],
                ['• ЕИК трябва да е 9 или 13 цифри', ''],
                ['• ДДС номер трябва да започва с "BG"', ''],
                ['• Датите трябва да са във формат YYYY-MM-DD', ''],
                ['• Не изтривайте заглавията на колоните', '']
            ],
            'sales': [
                ['ИНСТРУКЦИИ ЗА ПОПЪЛВАНЕ - ДНЕВНИК ЗА ПРОДАЖБИТЕ', ''],
                ['', ''],
                ['Задължителни полета:', ''],
                ['document_number', 'Номер на документа (фактура, кредитно известие)'],
                ['document_date', 'Дата на документа (формат: YYYY-MM-DD)'],
                ['document_type', '1 = Фактура, 3 = Кредитно известие'],
                ['customer_name', 'Име на клиента'],
                ['customer_uic', 'ЕИК/БУЛСТАТ на клиента'],
                ['tax_base', 'Данъчна основа (без ДДС)'],
                ['vat_rate', 'ДДС ставка (0.20 за 20%)'],
                ['vat_amount', 'Сума ДДС'],
                ['total_amount', 'Обща сума (с ДДС)'],
                ['', ''],
                ['Незадължителни полета:', ''],
                ['customer_vat_number', 'ДДС номер на клиента (BGxxxxxxxxx)'],
                ['description', 'Описание на стоките/услугите'],
                ['notes', 'Допълнителни бележки'],
                ['', ''],
                ['ВАЖНИ ЗАБЕЛЕЖКИ:', ''],
                ['• За кредитни известия използвайте отрицателни стойности', ''],
                ['• ЕИК трябва да е 9 или 13 цифри', ''],
                ['• ДДС номер трябва да започва с "BG"', ''],
                ['• Датите трябва да са във формат YYYY-MM-DD', ''],
                ['• Не изтривайте заглавията на колоните', '']
            ]
        }
        
        # Create instructions DataFrame
        instructions_df = pd.DataFrame(instructions_data[journal_type], columns=['Поле', 'Описание'])
        
        # Write instructions
        instructions_df.to_excel(writer, sheet_name='Инструкции', index=False)
        
        # Format instructions sheet
        worksheet = writer.sheets['Инструкции']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'fg_color': '#FFE699'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#D6EAF8'
        })
        
        # Format title
        worksheet.write(0, 0, instructions_data[journal_type][0][0], title_format)
        worksheet.merge_range('A1:B1', instructions_data[journal_type][0][0], title_format)
        
        # Set column widths
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 50)
    
    def _add_validation_sheet(self, writer, workbook):
        """Add validation reference sheet"""
        
        validation_data = [
            ['РЕФЕРЕНТНИ СТОЙНОСТИ', ''],
            ['', ''],
            ['Типове документи:', ''],
            ['1', 'Фактура'],
            ['3', 'Кредитно известие'],
            ['', ''],
            ['ДДС ставки:', ''],
            ['0.20', '20% (стандартна ставка)'],
            ['0.09', '9% (намалена ставка - хотели, ресторанти)'],
            ['0.00', '0% (освободени доставки)'],
            ['', ''],
            ['Формати:', ''],
            ['Дата', 'YYYY-MM-DD (напр. 2024-01-15)'],
            ['ЕИК', '9 или 13 цифри (напр. 123456789)'],
            ['ДДС номер', 'BG + 9 цифри (напр. BG123456789)'],
            ['Суми', 'Число с до 2 знака след запетаята'],
        ]
        
        # Create validation DataFrame
        validation_df = pd.DataFrame(validation_data, columns=['Тип', 'Стойност/Описание'])
        
        # Write validation data
        validation_df.to_excel(writer, sheet_name='Валидация', index=False)
        
        # Format validation sheet
        worksheet = writer.sheets['Валидация']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'fg_color': '#FFEAA7'
        })
        
        # Set column widths
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 40)