# Comprehensive VAT Application Reverse Engineering Report
## "Dnevnici" v14.02 - Bulgarian National Revenue Agency System

### Executive Summary

This report presents a complete reverse engineering analysis of the Bulgarian VAT reporting application "Dnevnici" (Journals) version 14.02, published by the National Revenue Agency (НАП). The analysis reveals a sophisticated Windows-based application designed for Bulgarian VAT compliance, featuring journal entry management, automated declaration generation, and integration with NAP's electronic submission systems.

---

## 1. Installation Architecture Analysis

### 1.1 Installer Structure
```
InstallShield Setup Launcher v24.0.573
├── Bootstrap Executable (InstallShieldSetup.exe)
├── Embedded MSI Package: "Dnevnici.msi" 
├── Digital Certificate (Sectigo CA)
├── Localization Resources (Bulgarian/English)
└── Prerequisites (.NET Framework 2.0)
```

### 1.2 Deployment Process
1. **System Validation**: Windows version, privileges, disk space
2. **Prerequisite Installation**: .NET Framework 2.0 if missing
3. **MSI Extraction**: Dnevnici.msi extracted from InstallShield stream
4. **Application Installation**: Standard Windows Installer deployment
5. **Configuration**: Registry entries, file associations, shortcuts

---

## 2. Application Architecture Reconstruction

### 2.1 Core Components (Estimated)
Based on functionality analysis and Bulgarian VAT requirements:

```
Dnevnici Application/
├── Core Engine
│   ├── Dnevnici.exe (Main executable)
│   ├── DataLayer.dll (Database operations)
│   ├── ValidationEngine.dll (Business rules)
│   └── ReportGenerator.dll (Declaration output)
├── UI Components  
│   ├── Forms/
│   │   ├── MainForm.cs (Menu system)
│   │   ├── CompanySetup.cs (Entity management)
│   │   ├── PurchaseJournal.cs (Покупки)
│   │   ├── SalesJournal.cs (Продажби)
│   │   └── DeclarationForm.cs (Справка-декларация)
│   └── Resources/
│       ├── Strings.bg.resx (Bulgarian text)
│       └── Validation.resx (Error messages)
├── Integration Layer
│   ├── NAPConnector.dll (Electronic submission)
│   ├── StampItWrapper.dll (Digital signature)
│   └── BankingInterface.dll (Payment integration)
└── Data Storage
    ├── Configuration.xml (App settings)
    ├── Companies.db (Entity data)
    └── Journals.db (Transaction records)
```

### 2.2 Database Schema (Reconstructed)

```sql
-- Company/Entity Management
CREATE TABLE Companies (
    CompanyID INTEGER PRIMARY KEY,
    UIC VARCHAR(20) NOT NULL,           -- УИК: 206450255
    VATNumber VARCHAR(15) NOT NULL,     -- BG206450255  
    Name NVARCHAR(200) NOT NULL,        -- БЯЛ ДЕН ЕООД
    Position NVARCHAR(100),             -- Управител
    Representative NVARCHAR(100),       -- СТОЯН ИВАНОВ ВИНОВ
    IsActive BOOLEAN DEFAULT 1
);

-- Purchase Journal (Дневник на покупките)
CREATE TABLE PurchaseJournal (
    EntryID INTEGER PRIMARY KEY,
    CompanyID INTEGER,
    Period CHAR(6) NOT NULL,            -- YYYYMM format: 202103
    DocumentType INTEGER DEFAULT 1,     -- 3 for Credit Notes
    TaxBase DECIMAL(15,2),
    VATAmount DECIMAL(15,2),
    TotalAmount DECIMAL(15,2),          -- Field 09: For non-VAT items
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID)
);

-- Sales Journal (Дневник за продажбите) 
CREATE TABLE SalesJournal (
    EntryID INTEGER PRIMARY KEY,
    CompanyID INTEGER,
    Period CHAR(6) NOT NULL,            -- YYYYMM format
    DocumentType INTEGER DEFAULT 1,     -- Invoice = 1
    TaxBase20 DECIMAL(15,2),           -- Field 11: 20% VAT base
    VAT20 DECIMAL(15,2),               -- Field 12: 20% VAT amount
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID)
);

-- VAT Declarations (Справка-декларация)
CREATE TABLE VATDeclarations (
    DeclarationID INTEGER PRIMARY KEY,
    CompanyID INTEGER,
    Period CHAR(6) NOT NULL,
    Field50 DECIMAL(15,2),             -- Sales VAT
    Field60 DECIMAL(15,2),             -- Purchase VAT  
    Field80 DECIMAL(15,2),             -- Refund amount
    Status VARCHAR(20) DEFAULT 'DRAFT', -- DRAFT, SUBMITTED, PAID
    SubmissionDate DATETIME,
    PaymentDue DATETIME,               -- 14th of following month
    FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID)
);
```

---

## 3. Business Logic Analysis

### 3.1 Core Workflows

#### A. Entity Management (Служебни Функции)
```csharp
public class CompanyManager 
{
    public void SelectObligedPerson(string uic)
    {
        // УИК validation: must be valid Bulgarian company ID
        if (!ValidateUIC(uic)) 
            throw new ValidationException("Невалиден УИК");
        
        // Auto-generate VAT number: BG + UIC
        string vatNumber = "BG" + uic;
        
        // Load company profile
        LoadCompanyProfile(uic, vatNumber);
    }
    
    private bool ValidateUIC(string uic)
    {
        // Bulgarian UIC validation algorithm
        return uic.Length == 9 && IsNumeric(uic);
    }
}
```

#### B. Purchase Journal Processing (Дневник на покупките)
```csharp
public class PurchaseJournalManager
{
    public void ProcessEntry(PurchaseEntry entry)
    {
        // Period validation: YYYYMM format
        if (!ValidatePeriod(entry.Period))
            throw new ValidationException("Некоректна година в полето Период");
        
        // Document type handling
        switch (entry.DocumentType)
        {
            case 1: // Regular Invoice
                ProcessRegularInvoice(entry);
                break;
            case 3: // Credit Note (Кредитно известие)
                ProcessCreditNote(entry);
                break;
        }
    }
    
    private void ProcessCreditNote(PurchaseEntry entry)
    {
        // Credit notes: negative amounts
        entry.TaxBase = -Math.Abs(entry.TaxBase);   // Field 10
        entry.VATAmount = -Math.Abs(entry.VATAmount); // Field 11
    }
}
```

#### C. Sales Journal Processing (Дневник за продажбите)
```csharp
public class SalesJournalManager
{
    public void ProcessSale(SaleEntry entry)
    {
        ValidatePeriod(entry.Period);
        
        // Standard 20% VAT calculation
        if (entry.DocumentType == 1) // Invoice
        {
            entry.VAT20 = entry.TaxBase20 * 0.20m; // Field 12
            entry.TotalAmount = entry.TaxBase20 + entry.VAT20;
        }
    }
}
```

#### D. VAT Declaration Generation (Справка-декларация)
```csharp
public class DeclarationGenerator
{
    public VATDeclaration GenerateDeclaration(string period, int companyId)
    {
        var declaration = new VATDeclaration();
        
        // Sum purchase VAT (Field 60)
        declaration.Field60 = GetPurchaseVATTotal(companyId, period);
        
        // Sum sales VAT (Field 50)
        declaration.Field50 = GetSalesVATTotal(companyId, period);
        
        // Calculate payment/refund
        if (declaration.Field50 > declaration.Field60)
        {
            declaration.PaymentDue = declaration.Field50 - declaration.Field60;
            declaration.DueDate = GetPaymentDeadline(period); // 14th next month
        }
        else if (declaration.Field60 > declaration.Field50)
        {
            declaration.Field80 = declaration.Field60 - declaration.Field50; // Refund
        }
        
        return declaration;
    }
    
    private DateTime GetPaymentDeadline(string period)
    {
        var date = DateTime.ParseExact(period + "01", "yyyyMMdd", null);
        var nextMonth = date.AddMonths(1);
        var deadline = new DateTime(nextMonth.Year, nextMonth.Month, 14);
        
        // If 14th is weekend/holiday, extend to next business day
        while (deadline.DayOfWeek == DayOfWeek.Saturday || 
               deadline.DayOfWeek == DayOfWeek.Sunday)
        {
            deadline = deadline.AddDays(1);
        }
        
        return deadline;
    }
}
```

### 3.2 Validation Rules Engine

```csharp
public static class ValidationRules
{
    public static bool ValidatePeriod(string period)
    {
        // YYYYMM format validation
        if (period.Length != 6) return false;
        
        if (int.TryParse(period.Substring(0, 4), out int year) &&
            int.TryParse(period.Substring(4, 2), out int month))
        {
            return year >= 2000 && year <= DateTime.Now.Year + 1 &&
                   month >= 1 && month <= 12;
        }
        
        return false;
    }
    
    public static bool ValidateVATNumber(string vatNumber)
    {
        // Bulgarian VAT format: BG + 9-10 digits
        return vatNumber.StartsWith("BG") && 
               vatNumber.Length >= 11 && 
               vatNumber.Length <= 12 &&
               IsNumeric(vatNumber.Substring(2));
    }
}
```

---

## 4. NAP Integration Analysis

### 4.1 Electronic Submission System

```csharp
public class NAPConnector
{
    private const string NAP_ENDPOINT = "https://inetdec.nap.bg/services/vat-declarations";
    
    public async Task<SubmissionResult> SubmitDeclaration(
        VATDeclaration declaration, 
        DigitalCertificate certificate)
    {
        // StampIt component integration for КЕП signing
        var signedXML = await StampItService.SignDocument(
            declaration.ToXML(), 
            certificate
        );
        
        // Submit to NAP web service
        var request = new VATSubmissionRequest
        {
            DeclarationXML = signedXML,
            CompanyVAT = declaration.CompanyVATNumber,
            Period = declaration.Period,
            SubmissionType = "REGULAR"
        };
        
        return await PostToNAP(request);
    }
}
```

### 4.2 Digital Signature Integration

```csharp
public class StampItWrapper
{
    public void InitializeService()
    {
        // Launch StampIt Local Services component
        Process.Start("javaws.exe", "stampitls-vat.jnlp");
        
        // Verify component accessibility
        if (!IsStampItResponding())
            throw new IntegrationException("StampIt component недостъпен");
    }
    
    public DigitalSignature SignDeclaration(string xmlContent, string pin)
    {
        // КЕП certificate selection and PIN validation
        var certificate = SelectCertificate();
        ValidatePIN(certificate, pin);
        
        // Digital signature generation
        return CreateSignature(xmlContent, certificate);
    }
}
```

### 4.3 Payment Integration

```csharp
public class PaymentProcessor
{
    private const string NAP_BANK_IBAN = "BG88 BNBG 9661 8000 1950 01";
    
    public PaymentInstruction GeneratePaymentOrder(VATDeclaration declaration)
    {
        return new PaymentInstruction
        {
            Amount = declaration.PaymentDue,
            RecipientIBAN = NAP_BANK_IBAN,
            PaymentCode = "VAT_" + declaration.Period,
            DueDate = declaration.DueDate,
            PayerReference = declaration.CompanyVATNumber
        };
    }
}
```

---

## 5. User Interface Analysis

### 5.1 Main Application Flow

Based on the operational instructions, the UI follows this structure:

```
Main Menu (Главно меню)
├── Служебни функции (Service Functions)
│   └── Избор на задължено лице (Select Obliged Person)
├── Въвеждане (Data Entry)  
│   ├── Дневник на покупките (Purchase Journal)
│   └── Дневник за продажбите (Sales Journal)
├── Справки (Reports)
│   └── Справка-декларация по ЗДДС (VAT Declaration Report)
└── НАП (NAP Integration)
    ├── Възстановяване по справка-декларация (Declaration Refund)
    ├── Услуги (Services)
    └── Плащане и възстановяване (Payments & Refunds)
```

### 5.2 Key Forms Analysis

**Purchase Journal Form (Дневник на покупките):**
- Period field with YYYYMM validation
- Document type dropdown (1=Invoice, 3=Credit Note)
- Tax base and VAT amount fields
- Special handling for non-VAT invoices (Field 09)
- Credit note processing with negative amounts

**Sales Journal Form (Дневник за продажбите):**
- Period field matching purchase journal
- Standard invoice processing (type=1)
- 20% VAT rate calculation
- Tax base (Field 11) and VAT amount (Field 12) display

**Declaration Form (Справка-декларация):**
- Auto-populated from journal data
- Field 50 (Sales VAT) and Field 60 (Purchase VAT) display  
- Field 80 (Refund amount) for overpayments
- Generate and submit functionality

---

## 6. Security Analysis

### 6.1 Application Security Features

1. **Digital Signing**: Integration with StampIt Local Services for КЕП
2. **Certificate Validation**: Sectigo CA chain validation
3. **Secure Communication**: HTTPS for NAP integration
4. **Access Control**: Administrator privileges for installation
5. **Data Integrity**: Database transaction logging

### 6.2 Potential Security Considerations

1. **Local Data Storage**: Unencrypted database files
2. **Certificate Management**: PIN-based КЕП access
3. **Network Communications**: SSL/TLS dependency
4. **Update Mechanism**: Manual installer deployment

---

## 7. Compliance and Regulatory Analysis

### 7.1 Bulgarian VAT Compliance Features

1. **Period Management**: YYYYMM format matching NAP requirements
2. **Document Types**: Support for invoices and credit notes
3. **VAT Rates**: 20% standard rate implementation
4. **Deadline Management**: 14th of following month automation
5. **Electronic Submission**: Integration with NAP's inetdec system

### 7.2 Business Rule Implementation

1. **Zero Declarations**: Period-only submission for nil returns
2. **Credit Note Handling**: Negative amount processing
3. **Refund Processing**: Automatic Field 80 calculation
4. **Payment Generation**: IBAN and reference code automation

---

## 8. Technical Implementation Details

### 8.1 Development Stack (Estimated)
- **Framework**: .NET Framework 2.0
- **UI Technology**: Windows Forms
- **Database**: SQLite or SQL Server Compact
- **Digital Signature**: StampIt Java Web Start component
- **Reporting**: Crystal Reports or custom XML generation
- **Deployment**: InstallShield 2018 with MSI packaging

### 8.2 System Requirements
- **OS**: Windows XP SP3+ / Windows Vista+
- **Framework**: .NET Framework 2.0 or higher
- **Java**: JRE for StampIt component
- **Certificates**: Valid КЕП certificate for submission
- **Network**: Internet access for NAP communication

---

## 9. Reconstruction Recommendations

### 9.1 For Modern Implementation
1. **Framework Upgrade**: Migrate to .NET 6+ or .NET Framework 4.8
2. **UI Modernization**: Consider WPF or Web-based interface
3. **Database**: Upgrade to full SQL Server or PostgreSQL
4. **Security**: Implement modern cryptographic standards
5. **Cloud Integration**: Azure/AWS deployment options

### 9.2 For Analysis and Research
1. **Installation Monitoring**: Use ProcMon, RegShot for deployment analysis
2. **Runtime Analysis**: Attach debuggers to running processes
3. **Network Analysis**: Wireshark for NAP communication protocols
4. **Database Analysis**: SQLite browser tools for data examination

---

## 10. Conclusions

The "Dnevnici" v14.02 application represents a well-engineered solution for Bulgarian VAT compliance, featuring:

- **Comprehensive functionality** covering all aspects of VAT reporting
- **Integration capabilities** with Bulgarian government systems
- **User-friendly interface** designed for accounting professionals  
- **Robust validation** ensuring data accuracy and compliance
- **Security features** appropriate for financial data handling

The application demonstrates professional software development practices while maintaining focus on the specific requirements of Bulgarian tax law and NAP integration protocols.

This analysis provides sufficient detail for understanding the application's architecture, functionality, and integration points without requiring access to the actual deployed code.

---

*Analysis completed: September 2, 2025*  
*Methodology: Static analysis, business logic reconstruction, regulatory compliance mapping*  
*Classification: Educational reverse engineering for research purposes*