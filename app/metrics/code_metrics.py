"""
Static Code Complexity & Maintainability Metrics Calculator.
Computes LOC, Cyclomatic Complexity (McCabe), Halstead Metrics, and Maintainability Index (MI).
"""
import ast
import math
import tokenize
import io
from app.models.metrics import CodeComplexityMetrics

class CodeComplexityAnalyzer:
    @staticmethod
    def analyze(code: str) -> CodeComplexityMetrics:
        if not code or not code.strip():
            return CodeComplexityMetrics()

        lines = code.splitlines()
        loc = len(lines)
        sloc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

        # AST Cyclomatic Complexity
        cyclomatic = 1
        cognitive = 0
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Branching points that increase McCabe cyclomatic complexity
                if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                    cyclomatic += 1
                elif isinstance(node, ast.BoolOp):
                    cyclomatic += len(node.values) - 1
                elif isinstance(node, (ast.Assert, ast.IfExp)):
                    cyclomatic += 1

            # Simple Cognitive Complexity estimation based on nested structures
            def compute_cognitive(node, depth=0):
                cog = 0
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        cog += (1 + depth)
                        cog += compute_cognitive(child, depth + 1)
                    else:
                        cog += compute_cognitive(child, depth)
                return cog

            cognitive = compute_cognitive(tree)
        except Exception:
            cyclomatic = max(1, code.count("if ") + code.count("for ") + code.count("while ") + 1)
            cognitive = cyclomatic

        # Halstead Metrics Approximation via Tokenize
        operators = set()
        operands = set()
        total_operators = 0
        total_operands = 0

        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
            for tok_type, tok_str, _, _, _ in tokens:
                if tok_type in (tokenize.OP, tokenize.NAME) and tok_str in {
                    "+", "-", "*", "/", "%", "**", "//", "==", "!=", "<", ">", "<=", ">=",
                    "and", "or", "not", "is", "in", "=", "+=", "-=", "*=", "/=", ":", "(", ")", "[", "]"
                }:
                    operators.add(tok_str)
                    total_operators += 1
                elif tok_type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING):
                    operands.add(tok_str)
                    total_operands += 1
        except Exception:
            total_operators = max(1, loc * 2)
            total_operands = max(1, loc * 3)
            operators = set(range(10))
            operands = set(range(15))

        n1 = max(len(operators), 1)
        n2 = max(len(operands), 1)
        N1 = max(total_operators, 1)
        N2 = max(total_operands, 1)

        vocabulary = n1 + n2
        length = N1 + N2
        volume = length * math.log2(vocabulary) if vocabulary > 1 else 10.0
        difficulty = (n1 / 2.0) * (N2 / n2)

        # SEI Maintainability Index formula (standard 0-100 normalization)
        # MI = 171 - 5.2 * ln(V) - 0.23 * V(G) - 16.2 * ln(LOC)
        # Normalized = max(0, MI * 100 / 171)
        safe_loc = max(loc, 1)
        raw_mi = 171.0 - (5.2 * math.log(max(volume, 1.0))) - (0.23 * cyclomatic) - (16.2 * math.log(safe_loc))
        normalized_mi = max(0.0, min(100.0, (raw_mi * 100.0) / 171.0))

        return CodeComplexityMetrics(
            loc=loc,
            sloc=sloc,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            maintainability_index=round(normalized_mi, 2),
            halstead_volume=round(volume, 2),
            halstead_difficulty=round(difficulty, 2)
        )
