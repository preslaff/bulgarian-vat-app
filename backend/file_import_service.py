"""
VAT System File Import Service

Handles Excel/JSON imports from PaperlessAI exports for automatic
journal entry creation in the Bulgarian VAT system.
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime
import re

from models_sync import Company
from services_sync import JournalService


class VATFileImportService:
    """Service for importing PaperlessAI exports into VAT system"""
    
    def __init__(self):
        self.journal_service = None
        self.validation_errors = []
        self.imported_entries = []
    
    def set_db_session(self, db_session):
        """Set database session for journal operations"""
        self.journal_service = JournalService(db_session)
    
    def import_excel_file(self, file_path: str, company_uic: str, 
                         journal_type: str = 'purchase') -> Tuple[bool, Dict]:
        """
        Import PaperlessAI Excel export into VAT system
        
        Args:
            file_path: Path to Excel file
            company_uic: Target company УИК
            journal_type: 'purchase' or 'sales'
            
        Returns:
            tuple: (success, result_data)
        """
        try:
            # Read Excel file with multiple sheets
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            # Process each sheet
            result = {
                'total_records': 0,
                'imported_count': 0,
                'validation_errors': [],
                'imported_entries': [],
                'preview_data': []
            }
            
            # Determine which sheet to process based on journal type
            if journal_type == 'purchase':
                processed_entries, error_messages = self._process_purchase_excel(excel_data, company_uic)
            elif journal_type == 'sales':
                processed_entries, error_messages = self._process_sales_excel(excel_data, company_uic)
            else:
                return False, {'error': f'Invalid journal type: {journal_type}'}
            
            result['total_records'] = len(processed_entries)
            result['preview_data'] = processed_entries[:10]  # First 10 for preview
            result['import_messages'] = error_messages  # Add error messages for user
            result['has_warnings'] = any('⚠️' in msg for msg in error_messages)
            result['has_errors'] = any('❌' in msg for msg in error_messages)
            
            # Serialize all decimal values for JSON compatibility
            result = self._serialize_decimals(result)
            
            return True, result
            
        except Exception as e:
            return False, {'error': f'Failed to process Excel file: {str(e)}'}
    
    def import_json_file(self, file_path: str, company_uic: str,
                        journal_type: str = 'purchase') -> Tuple[bool, Dict]:
        """
        Import PaperlessAI JSON export into VAT system
        
        Args:
            file_path: Path to JSON file
            company_uic: Target company УИК
            journal_type: 'purchase' or 'sales'
            
        Returns:
            tuple: (success, result_data)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            result = {
                'total_records': 0,
                'imported_count': 0,
                'validation_errors': [],
                'imported_entries': [],
                'preview_data': []
            }
            
            # Process JSON data
            if journal_type == 'purchase':
                processed_entries = self._process_purchase_json(json_data, company_uic)
            elif journal_type == 'sales':
                processed_entries = self._process_sales_json(json_data, company_uic)
            else:
                return False, {'error': f'Invalid journal type: {journal_type}'}
            
            result['total_records'] = len(processed_entries)
            result['preview_data'] = processed_entries[:10]
            
            # Serialize all decimal values for JSON compatibility
            result = self._serialize_decimals(result)
            
            return True, result
            
        except Exception as e:
            return False, {'error': f'Failed to process JSON file: {str(e)}'}
    
    def validate_and_import(self, processed_entries: List[Dict], 
                          auto_approve: bool = False) -> Tuple[bool, Dict]:
        """
        Validate processed entries and optionally import them
        
        Args:
            processed_entries: List of processed journal entries
            auto_approve: Whether to automatically import valid entries
            
        Returns:
            tuple: (success, result_summary)
        """
        valid_entries = []
        validation_errors = []
        
        for idx, entry in enumerate(processed_entries):
            is_valid, errors = self._validate_vat_entry(entry)
            
            if is_valid:
                valid_entries.append(entry)
            else:
                validation_errors.append({
                    'row': idx + 1,
                    'entry': entry,
                    'errors': errors
                })
        
        result = {
            'total_processed': len(processed_entries),
            'valid_entries': len(valid_entries),
            'validation_errors': len(validation_errors),
            'errors': validation_errors,
            'imported_count': 0
        }
        
        # Import valid entries if auto-approved
        if auto_approve and valid_entries and self.journal_service:
            imported_count = 0
            import_errors = []
            
            for entry in valid_entries:
                try:
                    if entry['journal_type'] == 'purchase':
                        self.journal_service.add_purchase_entry(
                            entry['company_uic'], entry['data']
                        )
                    elif entry['journal_type'] == 'sales':
                        self.journal_service.add_sales_entry(
                            entry['company_uic'], entry['data']
                        )
                    imported_count += 1
                    
                except Exception as e:
                    import_errors.append({
                        'entry': entry,
                        'error': str(e)
                    })
            
            result['imported_count'] = imported_count
            result['import_errors'] = import_errors
        
        # Serialize all decimal values for JSON compatibility
        result = self._serialize_decimals(result)
        
        return len(validation_errors) == 0, result
    
    def _process_purchase_excel(self, excel_data: Dict, company_uic: str) -> Tuple[List[Dict], List[str]]:
        """Process PaperlessAI Excel export for purchase journal entries"""
        processed_entries = []
        error_messages = []
        
        # Get main summary sheet
        summary_df = excel_data.get('Summary', excel_data.get('Sheet1'))
        if summary_df is None:
            available_sheets = list(excel_data.keys())
            error_messages.append(f"❌ Missing required sheet 'Summary' or 'Sheet1'. Available sheets: {available_sheets}")
            return [], error_messages
        
        error_messages.append(f"✅ Found data sheet with {len(summary_df)} rows")
        
        # Get supplier details if available
        supplier_df = excel_data.get('Supplier Details', pd.DataFrame())
        if not supplier_df.empty:
            error_messages.append(f"✅ Found supplier details sheet with {len(supplier_df)} suppliers")
        
        for row_idx, row in summary_df.iterrows():
            row_num = row_idx + 2  # +2 because Excel is 1-based and has header
            row_errors = []
            
            try:
                # Check for required fields
                if pd.isna(row.get('Invoice Number')) or str(row.get('Invoice Number', '')).strip() == '':
                    row_errors.append(f"Row {row_num}: Missing invoice number")
                
                if pd.isna(row.get('Supplier Name')) or str(row.get('Supplier Name', '')).strip() == '':
                    row_errors.append(f"Row {row_num}: Missing supplier name")
                
                # Process decimal fields with error tracking
                tax_base, tax_base_error = self._to_decimal(row.get('Subtotal (€)', 0), 'Subtotal (€)', row_num)
                if tax_base_error:
                    row_errors.append(tax_base_error)
                
                vat_amount, vat_error = self._to_decimal(row.get('VAT Amount (€)', 0), 'VAT Amount (€)', row_num)
                if vat_error:
                    row_errors.append(vat_error)
                
                total_amount, total_error = self._to_decimal(row.get('Total Due (€)', 0), 'Total Due (€)', row_num)
                if total_error:
                    row_errors.append(total_error)
                
                # Map PaperlessAI columns to VAT system fields
                entry_data = {
                    'period': self._calculate_period_from_date(row.get('Invoice Date')),
                    'document_type': 1,  # Invoice
                    'document_number': str(row.get('Invoice Number', '')),
                    'document_date': self._format_date(row.get('Invoice Date')),
                    'supplier_name': str(row.get('Supplier Name', '')),
                    'supplier_vat': self._extract_supplier_vat(row, supplier_df),
                    'tax_base': tax_base,
                    'vat_amount': vat_amount,
                    'total_amount': total_amount,
                    'notes': f'Imported from PaperlessAI - {row.get("Filename", "")}'
                }
                
                # Validate business logic
                if tax_base > 0 and vat_amount == 0:
                    row_errors.append(f"Row {row_num}: ⚠️ Tax base {tax_base} but no VAT amount")
                
                if abs(float(tax_base + vat_amount) - float(total_amount)) > 0.01:
                    row_errors.append(f"Row {row_num}: ⚠️ Tax base + VAT ({tax_base + vat_amount}) doesn't equal total ({total_amount})")
                
                processed_entries.append({
                    'journal_type': 'purchase',
                    'company_uic': company_uic,
                    'data': entry_data,
                    'original_row': row.to_dict(),
                    'row_errors': row_errors
                })
                
                # Add row errors to main error list
                error_messages.extend(row_errors)
                
            except Exception as e:
                error_msg = f"Row {row_num}: ❌ Critical error processing row - {str(e)}"
                error_messages.append(error_msg)
                continue
        
        error_messages.append(f"✅ Successfully processed {len(processed_entries)} entries")
        return processed_entries, error_messages
    
    def _process_sales_excel(self, excel_data: Dict, company_uic: str) -> Tuple[List[Dict], List[str]]:
        """Process PaperlessAI Excel export for sales journal entries"""
        processed_entries = []
        error_messages = []
        
        summary_df = excel_data.get('Summary', excel_data.get('Sheet1'))
        if summary_df is None:
            available_sheets = list(excel_data.keys())
            error_messages.append(f"❌ Missing required sheet 'Summary' or 'Sheet1'. Available sheets: {available_sheets}")
            return [], error_messages
        
        error_messages.append(f"✅ Found data sheet with {len(summary_df)} rows")
        
        customer_df = excel_data.get('Customer Details', pd.DataFrame())
        if not customer_df.empty:
            error_messages.append(f"✅ Found customer details sheet with {len(customer_df)} customers")
        
        for row_idx, row in summary_df.iterrows():
            row_num = row_idx + 2  # +2 because Excel is 1-based and has header
            row_errors = []
            
            try:
                # Check for required fields
                if pd.isna(row.get('Invoice Number')) or str(row.get('Invoice Number', '')).strip() == '':
                    row_errors.append(f"Row {row_num}: Missing invoice number")
                
                if pd.isna(row.get('Customer Name')) or str(row.get('Customer Name', '')).strip() == '':
                    row_errors.append(f"Row {row_num}: Missing customer name")
                
                # Process decimal fields with error tracking
                tax_base_20, tax_base_error = self._to_decimal(row.get('Subtotal (€)', 0), 'Subtotal (€)', row_num)
                if tax_base_error:
                    row_errors.append(tax_base_error)
                
                vat_20, vat_error = self._to_decimal(row.get('VAT Amount (€)', 0), 'VAT Amount (€)', row_num)
                if vat_error:
                    row_errors.append(vat_error)
                
                tax_base_0, _ = self._to_decimal(0, 'tax_base_0', row_num)
                tax_base_exempt, _ = self._to_decimal(0, 'tax_base_exempt', row_num)
                
                total_amount, total_error = self._to_decimal(row.get('Total Due (€)', 0), 'Total Due (€)', row_num)
                if total_error:
                    row_errors.append(total_error)
                
                entry_data = {
                    'period': self._calculate_period_from_date(row.get('Invoice Date')),
                    'document_type': 1,  # Invoice
                    'document_number': str(row.get('Invoice Number', '')),
                    'document_date': self._format_date(row.get('Invoice Date')),
                    'customer_name': str(row.get('Customer Name', '')),
                    'customer_vat': self._extract_customer_vat(row, customer_df),
                    'tax_base_20': tax_base_20,
                    'vat_20': vat_20,
                    'tax_base_0': tax_base_0,
                    'tax_base_exempt': tax_base_exempt,
                    'total_amount': total_amount,
                    'notes': f'Imported from PaperlessAI - {row.get("Filename", "")}'
                }
                
                # Validate business logic
                if tax_base_20 > 0 and vat_20 == 0:
                    row_errors.append(f"Row {row_num}: ⚠️ Tax base {tax_base_20} but no VAT amount")
                
                if abs(float(tax_base_20 + vat_20) - float(total_amount)) > 0.01:
                    row_errors.append(f"Row {row_num}: ⚠️ Tax base + VAT ({tax_base_20 + vat_20}) doesn't equal total ({total_amount})")
                
                processed_entries.append({
                    'journal_type': 'sales',
                    'company_uic': company_uic,
                    'data': entry_data,
                    'original_row': row.to_dict(),
                    'row_errors': row_errors
                })
                
                # Add row errors to main error list
                error_messages.extend(row_errors)
                
            except Exception as e:
                error_msg = f"Row {row_num}: ❌ Critical error processing row - {str(e)}"
                error_messages.append(error_msg)
                continue
        
        error_messages.append(f"✅ Successfully processed {len(processed_entries)} entries")
        return processed_entries, error_messages
    
    def _process_purchase_json(self, json_data: Any, company_uic: str) -> List[Dict]:
        """Process PaperlessAI JSON export for purchase journal entries"""
        processed_entries = []
        
        # Handle different JSON structures
        if isinstance(json_data, list):
            extractions = json_data
        elif isinstance(json_data, dict):
            extractions = json_data.get('extractions', [json_data])
        else:
            return []
        
        for extraction in extractions:
            try:
                extracted_data = extraction.get('extracted_data', {})
                supplier_details = extracted_data.get('supplier_details', {})
                financial_summary = extracted_data.get('financial_summary', {})
                
                entry_data = {
                    'period': self._calculate_period_from_date(extracted_data.get('invoice_date')),
                    'document_type': 1,
                    'document_number': str(extracted_data.get('invoice_number', '')),
                    'document_date': extracted_data.get('invoice_date'),
                    'supplier_name': supplier_details.get('name', ''),
                    'supplier_vat': supplier_details.get('vat_id', ''),
                    'tax_base': self._to_decimal(financial_summary.get('subtotal', 0)),
                    'vat_amount': self._to_decimal(financial_summary.get('vat_amount', 0)),
                    'total_amount': self._to_decimal(financial_summary.get('total_due', 0)),
                    'notes': f'Imported from PaperlessAI - {extraction.get("filename", "")}'
                }
                
                processed_entries.append({
                    'journal_type': 'purchase',
                    'company_uic': company_uic,
                    'data': entry_data,
                    'original_extraction': extraction
                })
                
            except Exception as e:
                print(f"Error processing JSON extraction: {e}")
                continue
        
        return processed_entries
    
    def _process_sales_json(self, json_data: Any, company_uic: str) -> List[Dict]:
        """Process PaperlessAI JSON export for sales journal entries"""
        processed_entries = []
        
        if isinstance(json_data, list):
            extractions = json_data
        elif isinstance(json_data, dict):
            extractions = json_data.get('extractions', [json_data])
        else:
            return []
        
        for extraction in extractions:
            try:
                extracted_data = extraction.get('extracted_data', {})
                customer_details = extracted_data.get('customer_details', {})
                financial_summary = extracted_data.get('financial_summary', {})
                
                entry_data = {
                    'period': self._calculate_period_from_date(extracted_data.get('invoice_date')),
                    'document_type': 1,
                    'document_number': str(extracted_data.get('invoice_number', '')),
                    'document_date': extracted_data.get('invoice_date'),
                    'customer_name': customer_details.get('name', ''),
                    'customer_vat': customer_details.get('vat_id', ''),
                    'tax_base_20': self._to_decimal(financial_summary.get('subtotal', 0)),
                    'vat_20': self._to_decimal(financial_summary.get('vat_amount', 0)),
                    'tax_base_0': self._to_decimal(0),
                    'tax_base_exempt': self._to_decimal(0),
                    'total_amount': self._to_decimal(financial_summary.get('total_due', 0)),
                    'notes': f'Imported from PaperlessAI - {extraction.get("filename", "")}'
                }
                
                processed_entries.append({
                    'journal_type': 'sales',
                    'company_uic': company_uic,
                    'data': entry_data,
                    'original_extraction': extraction
                })
                
            except Exception as e:
                print(f"Error processing JSON extraction: {e}")
                continue
        
        return processed_entries
    
    def _validate_vat_entry(self, entry: Dict) -> Tuple[bool, List[str]]:
        """Validate a VAT journal entry for Bulgarian compliance"""
        errors = []
        data = entry.get('data', {})
        
        # Required fields validation
        if not data.get('document_number'):
            errors.append('Document number is required')
        
        if not data.get('document_date'):
            errors.append('Document date is required')
        
        # VAT number validation
        if entry['journal_type'] == 'purchase':
            vat_field = 'supplier_vat'
            name_field = 'supplier_name'
        else:
            vat_field = 'customer_vat'
            name_field = 'customer_name'
        
        vat_number = data.get(vat_field)
        if vat_number and not self._validate_bg_vat_format(vat_number):
            errors.append(f'Invalid VAT number format: {vat_number}')
        
        if not data.get(name_field):
            errors.append(f'{name_field.replace("_", " ").title()} is required')
        
        # Amount validation
        if entry['journal_type'] == 'purchase':
            tax_base = data.get('tax_base', 0)
            vat_amount = data.get('vat_amount', 0)
        else:
            tax_base = data.get('tax_base_20', 0)
            vat_amount = data.get('vat_20', 0)
        
        if tax_base and vat_amount:
            expected_vat = float(tax_base) * 0.20
            if abs(float(vat_amount) - expected_vat) > 0.01:
                errors.append(f'VAT calculation error: Expected {expected_vat:.2f}, got {vat_amount}')
        
        # Period validation
        period = data.get('period')
        if period and not re.match(r'^\d{6}$', str(period)):
            errors.append(f'Invalid period format: {period} (expected YYYYMM)')
        
        return len(errors) == 0, errors
    
    def _extract_supplier_vat(self, row: pd.Series, supplier_df: pd.DataFrame) -> str:
        """Extract supplier VAT from supplier details sheet"""
        if supplier_df.empty:
            return ''
        
        invoice_number = row.get('Invoice Number')
        if not invoice_number:
            return ''
        
        # Find matching supplier by invoice number
        matching_suppliers = supplier_df[
            supplier_df['Invoice Number'] == invoice_number
        ]
        
        if not matching_suppliers.empty:
            return str(matching_suppliers.iloc[0].get('VAT ID', ''))
        
        return ''
    
    def _extract_customer_vat(self, row: pd.Series, customer_df: pd.DataFrame) -> str:
        """Extract customer VAT from customer details sheet"""
        # Similar to supplier VAT extraction
        if customer_df.empty:
            return ''
        
        invoice_number = row.get('Invoice Number')
        if not invoice_number:
            return ''
        
        matching_customers = customer_df[
            customer_df['Invoice Number'] == invoice_number
        ]
        
        if not matching_customers.empty:
            # Note: Customer details might not have VAT ID field
            return str(matching_customers.iloc[0].get('Company ID', ''))
        
        return ''
    
    def _validate_bg_vat_format(self, vat_number: str) -> bool:
        """Validate Bulgarian VAT number format"""
        if not vat_number:
            return False
        
        vat_clean = vat_number.replace(' ', '').upper()
        return bool(re.match(r'^BG\d{9,10}$', vat_clean))
    
    def _calculate_period_from_date(self, date_value: Any) -> str:
        """Calculate YYYYMM period from date"""
        if not date_value:
            return self._get_current_period()
        
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, '%Y-%m-%d')
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return self._get_current_period()
            
            return f"{date_obj.year}{date_obj.month:02d}"
        except:
            return self._get_current_period()
    
    def _get_current_period(self) -> str:
        """Get current period in YYYYMM format"""
        now = datetime.now()
        return f"{now.year}{now.month:02d}"
    
    def _format_date(self, date_value: Any) -> Optional[str]:
        """Format date for database storage"""
        if not date_value:
            return None
        
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, '%Y-%m-%d')
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return None
            
            return date_obj.strftime('%Y-%m-%d')
        except:
            return None
    
    def _to_decimal(self, value: Any, field_name: str = "unknown", row_num: int = 0) -> Tuple[Decimal, Optional[str]]:
        """
        Convert value to Decimal for database storage
        Returns (decimal_value, error_message)
        """
        if value is None or value == '':
            return Decimal('0'), None
            
        # Handle pandas NaN values
        if pd.isna(value):
            return Decimal('0'), f"Row {row_num}: Empty value in field '{field_name}' - using 0.00"
            
        try:
            # Check for NaN values from pandas
            if isinstance(value, float) and (pd.isna(value) or value != value):  # NaN check
                return Decimal('0'), f"Row {row_num}: Invalid number (NaN) in field '{field_name}' - using 0.00"
            
            # Clean the value first - remove any non-numeric characters except decimal point and minus
            if isinstance(value, str):
                original_value = value
                # Remove currency symbols, spaces, and other non-numeric chars
                cleaned_value = re.sub(r'[^\d.-]', '', str(value))
                if not cleaned_value or cleaned_value in ['-', '.']:
                    return Decimal('0'), f"Row {row_num}: Invalid text '{original_value}' in field '{field_name}' - using 0.00"
                return Decimal(cleaned_value), None
            else:
                # For numeric types, convert directly
                float_value = float(value)
                if pd.isna(float_value) or float_value != float_value:  # Additional NaN check
                    return Decimal('0'), f"Row {row_num}: Invalid number in field '{field_name}' - using 0.00"
                return Decimal(str(float_value)), None
                
        except (ValueError, TypeError, AttributeError) as e:
            return Decimal('0'), f"Row {row_num}: Cannot convert '{value}' to number in field '{field_name}' - {str(e)} - using 0.00"
    
    def _serialize_decimals(self, obj: Any) -> Any:
        """Convert Decimal objects to floats for JSON serialization"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_decimals(item) for item in obj]
        else:
            return obj


class ImportPreviewGenerator:
    """Generate preview of import data for user review"""
    
    @staticmethod
    def generate_preview_table(processed_entries: List[Dict]) -> Dict:
        """Generate HTML table preview of entries to be imported"""
        if not processed_entries:
            return {'html': '<p>No entries to preview</p>', 'count': 0}
        
        # Take first 20 entries for preview
        preview_entries = processed_entries[:20]
        
        html_rows = []
        for entry in preview_entries:
            data = entry['data']
            journal_type = entry['journal_type']
            
            if journal_type == 'purchase':
                partner_name = data.get('supplier_name', '')
                partner_vat = data.get('supplier_vat', '')
                tax_base = data.get('tax_base', 0)
                vat_amount = data.get('vat_amount', 0)
            else:
                partner_name = data.get('customer_name', '')
                partner_vat = data.get('customer_vat', '')
                tax_base = data.get('tax_base_20', 0)
                vat_amount = data.get('vat_20', 0)
            
            html_rows.append(f"""
                <tr>
                    <td>{journal_type.title()}</td>
                    <td>{data.get('document_number', '')}</td>
                    <td>{data.get('document_date', '')}</td>
                    <td>{partner_name}</td>
                    <td>{partner_vat}</td>
                    <td class="text-right">{tax_base}</td>
                    <td class="text-right">{vat_amount}</td>
                    <td class="text-right">{data.get('total_amount', 0)}</td>
                </tr>
            """)
        
        html = f"""
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Document #</th>
                    <th>Date</th>
                    <th>Partner</th>
                    <th>VAT Number</th>
                    <th>Tax Base</th>
                    <th>VAT Amount</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
        """
        
        return {
            'html': html,
            'count': len(processed_entries),
            'preview_count': len(preview_entries)
        }