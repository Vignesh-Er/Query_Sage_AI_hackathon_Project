import hashlib
import sqlglot
import sqlglot.expressions as exp

def fingerprint(sql: str, dialect: str = None) -> str:
    digest, _ = get_fingerprint_and_normalized(sql, dialect)
    return digest

def get_fingerprint_and_normalized(sql: str, dialect: str = None) -> tuple:
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        
        def replace_literals(node):
            if isinstance(node, exp.Literal):
                if node.is_string:
                    return exp.Literal.string("?")
                else:
                    return exp.Literal.number("?")
            elif isinstance(node, exp.Boolean):
                return exp.Literal.number("?")
            return node

        normalized = parsed.transform(replace_literals)
        normalized_sql = normalized.sql(dialect=dialect or "postgres")
        # Clean spacing and casing for consistent hashing
        clean_normalized = " ".join(normalized_sql.split()).lower()
        h = hashlib.sha256(clean_normalized.encode("utf-8"))
        return h.hexdigest(), normalized_sql
    except Exception:
        # Fallback if sqlglot parsing fails
        clean_sql = " ".join(sql.split()).lower()
        h = hashlib.sha256(clean_sql.encode("utf-8"))
        return h.hexdigest(), sql
