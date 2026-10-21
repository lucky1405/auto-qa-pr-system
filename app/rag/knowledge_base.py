"""
Project Knowledge Base containing conventions, security policies, and historical fix patterns for RAG.
"""
from typing import List, Dict, Any

DEFAULT_KNOWLEDGE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "KB-SEC-001",
        "category": "Security Policy",
        "title": "SQL Injection Prevention & Parameterized Queries",
        "content": (
            "Rule: Direct interpolation of user-supplied input into SQL strings (f-strings, %, or + concatenation) "
            "is strictly prohibited (CWE-89, OWASP A03). "
            "All SQL executions must utilize parameterized placeholders (e.g., 'SELECT * FROM users WHERE username = ?' "
            "or ':username' with an argument tuple/dict). "
            "Never construct dynamic SQL without query builder parameter binding."
        ),
        "tags": ["sql", "security", "injection", "owasp", "cwe-89", "database"],
        "fix_pattern": (
            "# Vulnerable:\n"
            "cursor.execute(f'SELECT * FROM users WHERE email = \"{email}\"')\n"
            "# Compliant:\n"
            "cursor.execute('SELECT * FROM users WHERE email = ?', (email,))"
        )
    },
    {
        "id": "KB-REL-002",
        "category": "Reliability & Resource Management",
        "title": "Deterministic Resource Cleanup and Context Managers",
        "content": (
            "Rule: All I/O resources, network connections, file handles, and database cursors must be managed via context managers "
            "('with' or 'async with' blocks) to prevent file descriptor exhaustion and memory leaks under high concurrency. "
            "Manual .close() calls are prone to being skipped during unhandled exceptions. "
            "Always wrap opened files, sockets, and connections in 'with open(...) as f:' or try...finally."
        ),
        "tags": ["resource_leak", "memory_leak", "files", "cursor", "context_manager", "reliability"],
        "fix_pattern": (
            "# Vulnerable:\n"
            "f = open(filepath, 'w')\n"
            "f.write(data)\n"
            "f.close()\n"
            "# Compliant:\n"
            "with open(filepath, 'w', encoding='utf-8') as f:\n"
            "    f.write(data)"
        )
    },
    {
        "id": "KB-LOGIC-003",
        "category": "Correctness & Boundary Conditions",
        "title": "Tiered Calculation Boundary Safety and Off-By-One Defenses",
        "content": (
            "Rule: When evaluating tiered rates, volume discounts, or ranges, boundary conditions must be mutually exclusive and exhaustive. "
            "Ensure inequality operators (<, <=, >, >=) align exactly with business tier definitions. "
            "Verify edge cases: 0, negative values, exact threshold values, and maximum integer bounds. "
            "Always validate preconditions and reject negative amounts with ValueError."
        ),
        "tags": ["boundary", "off_by_one", "logic_error", "discount", "calculation", "edge_cases"],
        "fix_pattern": (
            "# Vulnerable (skips threshold 100):\n"
            "if amount < 100: return rate1\n"
            "elif amount > 100: return rate2\n"
            "# Compliant:\n"
            "if amount <= 100: return rate1\n"
            "else: return rate2"
        )
    },
    {
        "id": "KB-STYLE-004",
        "category": "Coding Conventions",
        "title": "Pythonic Typing, Docstrings, and Clean Architecture",
        "content": (
            "Rule: Public functions and methods must include PEP 484 type annotations and Google-style docstrings. "
            "Variables and function names must use snake_case. Classes must use PascalCase. "
            "Limit function cyclomatic complexity to <= 10. Avoid deeply nested conditionals by using early returns guard clauses."
        ),
        "tags": ["pep8", "style", "typing", "docstrings", "complexity", "clean_code"],
        "fix_pattern": (
            "def calculate_total(price: float, tax_rate: float) -> float:\n"
            "    \"\"\"Calculates total price including tax.\"\"\"\n"
            "    if price < 0 or tax_rate < 0:\n"
            "        raise ValueError('Price and tax rate must be non-negative')\n"
            "    return round(price * (1.0 + tax_rate), 2)"
        )
    },
    {
        "id": "KB-TEST-005",
        "category": "Testing Standards",
        "title": "Unit Test Coverage and Mocking External Dependencies",
        "content": (
            "Rule: Any modified business logic must have corresponding unit test assertions with >= 85% branch coverage. "
            "Every public method must have at least one test case for happy path and two test cases for edge/error conditions. "
            "External network and database services must be mocked using pytest fixtures or unittest.mock."
        ),
        "tags": ["testing", "coverage", "pytest", "assertions", "edge_cases", "mocking"],
        "fix_pattern": (
            "def test_edge_case():\n"
            "    with pytest.raises(ValueError):\n"
            "        calculate_total(-10.0, 0.05)"
        )
    }
]
