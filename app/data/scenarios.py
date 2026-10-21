"""
Preset realistic PR Scenarios for demonstration and benchmarking.
"""
from typing import List, Dict, Any

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario-sql-injection",
        "title": "Auth Service: CWE-89 SQL Injection Vulnerability",
        "category": "SECURITY",
        "description": "PR modifies login query using raw string interpolation instead of parameterized placeholders, exposing user database to authentication bypass.",
        "author": "dev_alex",
        "branch": "feature/auth-speedup",
        "filename": "auth_service.py",
        "content": '''"""User Authentication Service Module."""
import sqlite3

class AuthService:
    def __init__(self, db_conn):
        self.conn = db_conn

    def authenticate_user(self, email: str, password_hash: str):
        cursor = self.conn.cursor()
        # Vulnerable dynamic SQL query using f-string interpolation
        cursor.execute(f"SELECT id, email, role FROM users WHERE email = '{email}' AND password = '{password_hash}'")
        user = cursor.fetchone()
        return user
''',
        "test_content": '''import sqlite3
import pytest

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, role TEXT, password TEXT)")
    cursor.execute("INSERT INTO users (id, email, role, password) VALUES (1, 'admin@acme.com', 'admin', 'hash123')")
    conn.commit()
    return conn

def test_legitimate_login(db_conn):
    from auth_service import AuthService
    auth = AuthService(db_conn)
    user = auth.authenticate_user("admin@acme.com", "hash123")
    assert user is not None
    assert user[1] == "admin@acme.com"

def test_sql_injection_defense(db_conn):
    from auth_service import AuthService
    auth = AuthService(db_conn)
    # Malicious SQL injection payload designed to bypass auth
    payload = "' OR '1'='1"
    user = auth.authenticate_user(payload, "wrongpass")
    assert user is None, "SQL Injection payload succeeded! Must be neutralized."
'''
    },
    {
        "id": "scenario-resource-leak",
        "title": "Data Pipeline: File Descriptor & Memory Leak",
        "category": "RELIABILITY",
        "description": "PR performs direct open() calls without a context manager, causing file descriptor exhaustion and memory leaks under heavy workloads.",
        "author": "data_sarah",
        "branch": "fix/batch-exporter",
        "filename": "data_exporter.py",
        "content": '''"""Data Exporter Pipeline."""
import os

class DataExporter:
    def __init__(self, export_dir: str):
        self.export_dir = export_dir

    def export_records(self, filename: str, data: str) -> bool:
        filepath = os.path.join(self.export_dir, filename)
        # Unmanaged open() risks descriptor leak if write fails
        f = open(filepath, 'w')
        f.write(data)
        f.close()
        return True
''',
        "test_content": '''import os
import tempfile
import pytest

def test_export_success():
    from data_exporter import DataExporter
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(tmpdir)
        ok = exporter.export_records("test.txt", "Sample Data Payload")
        assert ok is True
        assert os.path.exists(os.path.join(tmpdir, "test.txt"))
        with open(os.path.join(tmpdir, "test.txt"), "r") as f:
            assert f.read() == "Sample Data Payload"
'''
    },
    {
        "id": "scenario-boundary-bug",
        "title": "Billing Engine: Off-By-One Discount Tier Defect",
        "category": "CORRECTNESS",
        "description": "PR introduces pricing tiers with strict inequality ('< 100'), causing customers with exact threshold values (100) to fail calculation.",
        "author": "fintech_david",
        "branch": "feature/volume-discount",
        "filename": "discount_engine.py",
        "content": '''"""Volume Discount Calculation Engine."""

def calculate_discounted_price(amount: float) -> float:
    # Defect: Exact threshold 100 is not covered properly by strict inequality
    # Defect: Negative inputs are not validated
    if amount < 100:
        discount = 0.05
    elif amount > 100:
        discount = 0.15
    else:
        discount = 0.05
    return round(amount * (1.0 - discount), 2)
''',
        "test_content": '''import pytest

def test_low_tier():
    from discount_engine import calculate_discounted_price
    assert calculate_discounted_price(50.0) == 47.50

def test_exact_boundary():
    from discount_engine import calculate_discounted_price
    # Threshold 100 must receive 5% tier: 100 * 0.95 = 95.0
    assert calculate_discounted_price(100.0) == 95.0

def test_high_tier():
    from discount_engine import calculate_discounted_price
    assert calculate_discounted_price(200.0) == 170.0

def test_negative_input_rejection():
    from discount_engine import calculate_discounted_price
    with pytest.raises(ValueError):
        calculate_discounted_price(-25.0)
'''
    },
    {
        "id": "scenario-clean-pr",
        "title": "Crypto Utility: Production-Grade Clean PR",
        "category": "CLEAN",
        "description": "Exemplary PR with strict type annotations, docstrings, secure parameterized handling, and exhaustive unit test assertions.",
        "author": "principal_rachel",
        "branch": "chore/crypto-utils",
        "filename": "token_utils.py",
        "content": '''"""Token generation and validation utilities."""
import hmac
import hashlib

def generate_signature(secret_key: str, message: str) -> str:
    """Generates a secure HMAC-SHA256 signature for API payloads.
    
    Args:
        secret_key: Shared secret key string.
        message: Raw message payload.
        
    Returns:
        Hexadecimal HMAC digest.
    """
    if not secret_key or not message:
        raise ValueError("Secret key and message must be non-empty strings")
    return hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
''',
        "test_content": '''import pytest

def test_generate_signature_valid():
    from token_utils import generate_signature
    sig = generate_signature("my-secret", "payload-data")
    assert isinstance(sig, str)
    assert len(sig) == 64

def test_empty_arguments():
    from token_utils import generate_signature
    with pytest.raises(ValueError):
        generate_signature("", "data")
'''
    }
]
