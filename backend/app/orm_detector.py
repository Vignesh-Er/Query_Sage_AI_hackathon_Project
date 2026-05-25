import re
import sqlglot
import sqlglot.expressions as exp

def detect_orm(sql: str) -> str | None:
    if not sql:
        return None

    # Parse using sqlglot (lenient parsing, ignore errors)
    parsed = None
    try:
        # We can try to parse it with general or postgres dialect
        parsed = sqlglot.parse_one(sql)
    except Exception:
        pass

    # Extract aliases from AST if successfully parsed
    ast_aliases = []
    has_limit_21 = False
    if parsed:
        for table in parsed.find_all(exp.Table):
            if table.alias:
                ast_aliases.append(table.alias)
        for subquery in parsed.find_all(exp.Subquery):
            if subquery.alias:
                ast_aliases.append(subquery.alias)
        
        # Check for LIMIT 21 in AST
        for limit in parsed.find_all(exp.Limit):
            if limit.expression and str(limit.expression).strip() == "21":
                has_limit_21 = True

    # 1. Django
    # - table aliases matching pattern T followed by one or more digits (T1, T2, T99)
    # - LIMIT clause with the literal value 21
    # - column references containing double underscore patterns in the original raw string
    django_alias_pattern = re.compile(r"\bT\d+\b")
    has_django_alias = any(django_alias_pattern.match(alias) for alias in ast_aliases)
    if not has_django_alias:
        # Fallback to regex check on raw SQL
        if django_alias_pattern.search(sql):
            has_django_alias = True

    if not has_limit_21:
        # Check raw SQL for LIMIT 21
        if re.search(r"\bLIMIT\s+21\b", sql, re.IGNORECASE):
            has_limit_21 = True

    has_double_underscore = "__" in sql

    if has_django_alias or has_limit_21 or has_double_underscore:
        # Note: double underscore is a very specific signature for Django ORM
        # But wait, double underscore in prisma __prisma_data__ shouldn't be matched as django.
        # So we check prisma first, or exclude "__prisma_data__" from double underscore check.
        if "__prisma_data__" not in sql:
            return "django"

    # 2. SQLAlchemy
    # - subquery aliases or table aliases matching anon_ followed by digits
    # - parameter names in the format param_1, param_2 in the raw SQL string
    sqlalchemy_alias_pattern = re.compile(r"\banon_\d+\b", re.IGNORECASE)
    has_sa_alias = any(sqlalchemy_alias_pattern.match(alias) for alias in ast_aliases)
    if not has_sa_alias:
        if sqlalchemy_alias_pattern.search(sql):
            has_sa_alias = True

    has_sa_param = re.search(r"\bparam_\d+\b", sql) is not None

    if has_sa_alias or has_sa_param:
        return "sqlalchemy"

    # 3. Prisma
    # - __prisma_data__ anywhere in the raw SQL
    # - JSON aggregation functions combined with lowercase two-character table aliases like t1 or t2
    if "__prisma_data__" in sql:
        return "prisma"

    # Lowercase two-character table alias check: t followed by a single digit (like t1, t2)
    prisma_alias_pattern = re.compile(r"\bt\d\b")
    has_prisma_alias = any(prisma_alias_pattern.match(alias) for alias in ast_aliases)
    if not has_prisma_alias:
        if prisma_alias_pattern.search(sql):
            has_prisma_alias = True

    # JSON aggregation functions like json_agg, json_build_object, jsonb_agg, etc.
    has_json_agg = False
    json_agg_patterns = ["json_agg", "jsonb_agg", "json_build_object", "json_object_agg", "jsonb_object_agg"]
    if any(pattern in sql.lower() for pattern in json_agg_patterns):
        has_json_agg = True

    if has_json_agg and has_prisma_alias:
        return "prisma"

    # 4. Sequelize
    # - -> operator in JOIN conditions or alias definitions in the raw SQL string
    if "->" in sql:
        return "sequelize"

    # 5. Hibernate
    # - table aliases ending with underscore followed by digits (user0_, post1_, this_, category2_) in raw SQL
    hibernate_alias_pattern = re.compile(r"\b[a-zA-Z_]\w*_\d*\b")
    # Let's check specifically for: words ending with _ and optional digits
    # e.g. user0_, post1_, this_, category2_
    # Note that table aliases are usually followed by a dot for column references, e.g. user0_.id
    # So we can search for pattern like: user0_., post1_., this_., category2_.
    # Or just search raw SQL for these aliases.
    hibernate_matches = re.findall(r"\b(\w+_\d*)\b", sql)
    for match in hibernate_matches:
        if match.endswith("_") or re.match(r"\w+_\d+$", match):
            # Check if this matches one of user0_, post1_, this_, category2_ or generic Hibernate pattern
            # Hibernate table aliases are typically generated as tablealias0_, tablealias1_, etc., or "this_"
            if match == "this_" or re.match(r"^[a-zA-Z]+\d+_$", match) or re.match(r"^[a-zA-Z]+_\d+$", match):
                # Wait, standard hibernate generates aliases like: user0_, post1_, category2_, this_
                # Let's match any lowercase word + digits + underscore, or "this_"
                if match == "this_" or re.match(r"^[a-zA-Z_]+\d+_$", match):
                    return "hibernate"

    # Let's do another check: search for aliases in AST as well
    for alias in ast_aliases:
        if alias == "this_" or re.match(r"^[a-zA-Z_]+\d+_$", alias):
            return "hibernate"

    return None
