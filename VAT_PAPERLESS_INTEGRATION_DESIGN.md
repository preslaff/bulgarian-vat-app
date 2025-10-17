# VAT System ↔ PaperlessAI Integration Design

## Overview
Integration between PaperlessAI document scanning system and the Bulgarian VAT Management System for automated journal entry creation.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PaperlessAI   │    │  Integration    │    │   VAT System    │
│   (Port 5000)   │───▶│     Layer       │───▶│   (Port 8000)   │
│                 │    │                 │    │                 │
│ • OCR Scanning  │    │ • Data Mapping  │    │ • Purchase Logs │
│ • AI Extraction │    │ • Validation    │    │ • Sales Logs    │
│ • Bulgarian PDFs│    │ • Auto-posting  │    │ • Declarations  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Data Mapping

### Purchase Invoices (Покупки)
| PaperlessAI Field | VAT System Field | Validation |
|-------------------|------------------|------------|
| `supplier_details.name` | `supplier_name` | Required |
| `supplier_details.vat_id` | `supplier_vat` | BG + 9 digits |
| `invoice_number` | `document_number` | String |
| `invoice_date` | `document_date` | YYYY-MM-DD |
| `financial_summary.subtotal` | `tax_base` | Numeric(15,2) |
| `financial_summary.vat_amount` | `vat_amount` | Numeric(15,2) |
| `financial_summary.total_due` | `total_amount` | Numeric(15,2) |

### Sales Invoices (Продажби)  
| PaperlessAI Field | VAT System Field | Validation |
|-------------------|------------------|------------|
| `customer_details.name` | `customer_name` | Required |
| `customer_details.vat_id` | `customer_vat` | BG + 9 digits |
| `invoice_number` | `document_number` | String |
| `invoice_date` | `document_date` | YYYY-MM-DD |
| `financial_summary.subtotal` | `tax_base_20` | Numeric(15,2) |
| `financial_summary.vat_amount` | `vat_20` | Numeric(15,2) |
| `financial_summary.total_due` | `total_amount` | Numeric(15,2) |

## Integration Endpoints

### 1. Document Upload & Processing
```http
POST /api/vat/process-document
Content-Type: multipart/form-data

{
  "file": <invoice.pdf>,
  "company_uic": "123456789",
  "document_type": "purchase|sales"
}
```

### 2. Batch Processing
```http
POST /api/vat/batch-process
Content-Type: application/json

{
  "paperless_extraction_ids": [1, 2, 3],
  "company_uic": "123456789",
  "target_journal": "purchase|sales"
}
```

### 3. Review & Approve
```http
GET /api/vat/pending-extractions/{company_uic}
POST /api/vat/approve-extraction/{extraction_id}
```

## Workflow

### Automated Flow
1. **Document Upload**: User uploads invoice to PaperlessAI
2. **AI Extraction**: PaperlessAI extracts structured data
3. **VAT Integration**: System automatically maps and creates journal entries
4. **Validation**: System validates Bulgarian VAT compliance
5. **Journal Creation**: Entries added to Purchase/Sales journals
6. **Declaration Update**: Monthly declarations auto-updated

### Manual Review Flow
1. **Extract & Hold**: Process but hold for review
2. **User Review**: Show mapped data for approval
3. **Corrections**: Allow manual corrections
4. **Approve & Post**: User approves, system posts entries

## Error Handling

### Validation Errors
- Invalid УИК/ДДС numbers
- Missing required fields  
- Invalid dates/amounts
- Duplicate document detection

### Recovery Actions
- Hold for manual review
- Email notifications
- Audit trail logging
- Rollback capabilities

## Configuration

### Company Mapping
```json
{
  "company_uic": "123456789",
  "paperless_folder": "Company_A_Invoices",
  "auto_post_purchases": true,
  "auto_post_sales": false,
  "require_approval": ["sales"],
  "notification_email": "accountant@company.bg"
}
```

### VAT Rules
```json
{
  "default_vat_rate": 0.20,
  "exempt_suppliers": ["BG123456789"],
  "auto_detect_credit_notes": true,
  "duplicate_detection": true
}
```

## Implementation Phases

### Phase 1: Basic Integration
- [ ] Create integration API endpoints
- [ ] Implement data mapping
- [ ] Basic validation rules
- [ ] Manual approval workflow

### Phase 2: Automation
- [ ] Auto-posting capabilities  
- [ ] Duplicate detection
- [ ] Email notifications
- [ ] Batch processing

### Phase 3: Advanced Features
- [ ] Credit note auto-detection
- [ ] Multi-company support
- [ ] Custom validation rules
- [ ] Analytics & reporting

## Security Considerations

- **Authentication**: JWT tokens between systems
- **Data Validation**: Strict input validation
- **Audit Trail**: Full logging of all operations
- **Access Control**: Role-based permissions
- **Data Protection**: GDPR compliance for document storage

## Bulgarian VAT Compliance

- **НАП Integration**: Ready for NAP submission
- **Field Mapping**: Proper mapping to Fields 50, 60, 80
- **Period Management**: Automatic YYYYMM period detection
- **УИК Validation**: Bulgarian company identifier validation
- **ДДС Calculation**: 20% standard rate application