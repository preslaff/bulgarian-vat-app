import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio

from main import app
from database import get_db
from models import Base

# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_test_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Override dependency
app.dependency_overrides[get_db] = get_test_db

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client

# ============================================================================
# BASIC API TESTS
# ============================================================================

def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Bulgarian VAT Management System API" in data["message"]

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

# ============================================================================
# COMPANY MANAGEMENT TESTS
# ============================================================================

def test_create_company(client):
    """Test creating a new company."""
    company_data = {
        "uic": "206450255",
        "name": "БЯЛ ДЕН ЕООД",
        "position": "Управител",
        "representative": "СТОЯН ИВАНОВ ВИНОВ"
    }
    
    response = client.post("/api/companies", json=company_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["uic"] == "206450255"
    assert data["name"] == "БЯЛ ДЕН ЕООД"
    assert data["vat_number"] == "BG206450255"
    assert data["is_active"] is True

def test_get_company(client):
    """Test getting company by UIC."""
    # First create a company
    company_data = {
        "uic": "123456789",
        "name": "Test Company",
    }
    client.post("/api/companies", json=company_data)
    
    # Then get it
    response = client.get("/api/companies/123456789")
    assert response.status_code == 200
    
    data = response.json()
    assert data["uic"] == "123456789"
    assert data["name"] == "Test Company"

def test_create_duplicate_company(client):
    """Test creating company with duplicate UIC."""
    company_data = {
        "uic": "999999999",
        "name": "Duplicate Test",
    }
    
    # Create first company
    response1 = client.post("/api/companies", json=company_data)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/companies", json=company_data)
    assert response2.status_code == 400
    assert "вече съществува" in response2.json()["detail"]

def test_invalid_uic(client):
    """Test creating company with invalid UIC."""
    company_data = {
        "uic": "invalid",
        "name": "Invalid UIC Test",
    }
    
    response = client.post("/api/companies", json=company_data)
    assert response.status_code == 422  # Validation error

# ============================================================================
# PURCHASE JOURNAL TESTS
# ============================================================================

def test_add_purchase_entry(client):
    """Test adding a purchase journal entry."""
    # First create a company
    company_data = {
        "uic": "111111111",
        "name": "Purchase Test Company",
    }
    client.post("/api/companies", json=company_data)
    
    # Add purchase entry
    purchase_data = {
        "period": "202103",
        "document_type": 1,
        "document_number": "F-001",
        "supplier_name": "Test Supplier",
        "tax_base": 100.00,
        "vat_amount": 20.00,
        "total_amount": 120.00
    }
    
    response = client.post("/api/companies/111111111/purchases", json=purchase_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "202103"
    assert data["document_type"] == 1
    assert data["supplier_name"] == "Test Supplier"
    assert data["tax_base"] == 100.00
    assert data["vat_amount"] == 20.00

def test_get_purchases(client):
    """Test getting purchases for a period."""
    response = client.get("/api/companies/111111111/purchases/202103")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # At least the one we created

def test_invalid_period_format(client):
    """Test adding purchase with invalid period format."""
    purchase_data = {
        "period": "invalid",
        "document_type": 1,
        "tax_base": 100.00,
        "vat_amount": 20.00
    }
    
    response = client.post("/api/companies/111111111/purchases", json=purchase_data)
    assert response.status_code == 422  # Validation error

# ============================================================================
# SALES JOURNAL TESTS
# ============================================================================

def test_add_sales_entry(client):
    """Test adding a sales journal entry."""
    sales_data = {
        "period": "202103",
        "document_type": 1,
        "document_number": "S-001",
        "customer_name": "Test Customer",
        "tax_base_20": 200.00,
        "vat_20": 40.00
    }
    
    response = client.post("/api/companies/111111111/sales", json=sales_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "202103"
    assert data["tax_base_20"] == 200.00
    assert data["vat_20"] == 40.00

def test_auto_calculate_vat(client):
    """Test automatic VAT calculation."""
    sales_data = {
        "period": "202104",
        "document_type": 1,
        "tax_base_20": 100.00,
        # vat_20 not provided - should be auto-calculated
    }
    
    response = client.post("/api/companies/111111111/sales", json=sales_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["tax_base_20"] == 100.00
    assert data["vat_20"] == 20.00  # 20% of 100

# ============================================================================
# VAT DECLARATION TESTS
# ============================================================================

def test_generate_declaration(client):
    """Test generating a VAT declaration."""
    response = client.post("/api/companies/111111111/declarations/202103")
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "202103"
    assert data["field_50"] == 40.00  # Sales VAT from previous test
    assert data["field_60"] == 20.00  # Purchase VAT from previous test
    assert data["payment_due"] == 20.00  # 40 - 20 = 20
    assert data["status"] == "DRAFT"

def test_get_existing_declaration(client):
    """Test getting an existing declaration."""
    response = client.get("/api/companies/111111111/declarations/202103")
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "202103"
    assert data["status"] == "DRAFT"

def test_submit_declaration(client):
    """Test submitting a declaration."""
    # First get the declaration to get its ID
    response = client.get("/api/companies/111111111/declarations/202103")
    declaration = response.json()
    
    # Submit it
    response = client.post(f"/api/declarations/{declaration['id']}/submit")
    assert response.status_code == 200
    
    result = response.json()
    assert result["success"] is True
    assert "успешно" in result["message"]

# ============================================================================
# VAT CALCULATION TESTS
# ============================================================================

def test_vat_calculation(client):
    """Test VAT calculation endpoint."""
    response = client.get("/api/vat/calculate?tax_base=100&vat_rate=0.20")
    assert response.status_code == 200
    
    data = response.json()
    assert data["tax_base"] == 100
    assert data["vat_rate"] == 0.20
    assert data["vat_amount"] == 20.00
    assert data["total_amount"] == 120.00

def test_payment_deadline(client):
    """Test payment deadline calculation."""
    response = client.get("/api/deadlines/202103")
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "202103"
    assert "deadline" in data
    assert "business_days_remaining" in data

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_company_not_found(client):
    """Test accessing non-existent company."""
    response = client.get("/api/companies/999999999")
    assert response.status_code == 404

def test_invalid_period_in_url(client):
    """Test invalid period format in URL."""
    response = client.get("/api/companies/111111111/purchases/invalid")
    assert response.status_code == 400
    assert "YYYYMM format" in response.json()["detail"]

# ============================================================================
# BUSINESS LOGIC TESTS
# ============================================================================

def test_credit_note_processing(client):
    """Test credit note processing with negative amounts."""
    credit_note_data = {
        "period": "202105",
        "document_type": 3,  # Credit note
        "document_number": "CN-001",
        "supplier_name": "Credit Supplier",
        "credit_tax_base": -50.00,
        "credit_vat": -10.00
    }
    
    response = client.post("/api/companies/111111111/purchases", json=credit_note_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["document_type"] == 3
    assert data["credit_tax_base"] == -50.00
    assert data["credit_vat"] == -10.00

def test_zero_declaration(client):
    """Test generating a zero (null) declaration."""
    # Create company with no entries
    company_data = {
        "uic": "000000000", 
        "name": "Zero Declaration Test",
    }
    client.post("/api/companies", json=company_data)
    
    # Generate declaration
    response = client.post("/api/companies/000000000/declarations/202106")
    assert response.status_code == 200
    
    data = response.json()
    assert data["field_50"] == 0  # No sales VAT
    assert data["field_60"] == 0  # No purchase VAT
    assert data["field_80"] == 0  # No refund
    assert data["payment_due"] == 0
    assert data["refund_due"] == 0