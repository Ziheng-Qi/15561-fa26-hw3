"""Cross-check key results against independent SQL queries."""

import math
import sqlite3

from . import data_prep

TOLERANCE = 0.01


def load_sqlite(tables):
    """Copy workbook sheets into an in-memory SQLite database.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``data_prep.load_tables``; spaces in names become ``_``.

    Returns:
        sqlite3.Connection: Open connection to the database.
    """
    conn = sqlite3.connect(":memory:")
    for name, df in tables.items():
        df.to_sql(name.replace(" ", "_"), conn, index=False)
    return conn


def scalar(conn, sql):
    """Run a query and return the first column of the first row.

    Args:
        conn (sqlite3.Connection): Database to query.
        sql (str): Query returning at least one row.

    Returns:
        Any: The single value, such as a float or int.
    """
    return conn.execute(sql).fetchone()[0]


def check(label, expected, actual, failures):
    """Print whether a pandas result matches SQL within 0.01.

    Args:
        label (str): Name of the quantity being checked.
        expected (float): Value computed with pandas.
        actual (float): Value computed with SQL.
        failures (list[str]): Failed check labels; ``label`` is
            appended on mismatch.

    Returns:
        None. Prints an OK or FAIL line.
    """
    ok = math.isclose(expected, actual, rel_tol=1e-9, abs_tol=TOLERANCE)
    print(f"[{'OK' if ok else 'FAIL'}] {label}: pandas={expected:,.4f} sql={actual:,.4f}")
    if not ok:
        failures.append(label)


def run_checks(results, tables=None):
    """Recompute headline numbers in SQL and compare with pandas.

    Args:
        results (dict): Analysis results from ``main.main``, with keys
            ``lines``, ``market``, ``concentration``, ``discounts`` and
            ``delivery``.
        tables (dict[str, pandas.DataFrame] | None): Workbook sheets;
            loaded from disk if None.

    Returns:
        bool: True when every check passes.

    Raises:
        AssertionError: If any check fails.
    """
    tables = tables or data_prep.load_tables()
    conn = load_sqlite(tables)
    failures = []
    rev = "od.UnitPrice * od.Quantity * (1 - ROUND(od.Discount, 2))"

    total_sql = scalar(conn, f"SELECT SUM({rev}) FROM Orders_Details od")
    check("Total net revenue", results["lines"]["Revenue"].sum(), total_sql, failures)

    m = results["market"]["metrics"]
    for year, key in ((1997, "total_1997"), (1998, "total_1998")):
        sql = (f"SELECT SUM({rev}) FROM Orders_Details od JOIN Orders o USING (OrderID) "
               f"WHERE o.OrderDate >= '{year}-01-01' AND o.OrderDate < '{year}-05-01'")
        check(f"Jan-Apr {year} revenue", m[key], scalar(conn, sql), failures)

    top3_sql = scalar(conn, f"""
        WITH c AS (SELECT o.CustomerID, SUM({rev}) AS r FROM Orders_Details od
                   JOIN Orders o USING (OrderID) GROUP BY o.CustomerID)
        SELECT (SELECT SUM(r) FROM (SELECT r FROM c ORDER BY r DESC LIMIT 3))
               / (SELECT SUM(r) FROM c)""")
    check("Top-3 customer share", results["concentration"]["metrics"]["top3_share"],
          top3_sql, failures)

    disc_sql = scalar(conn, "SELECT SUM(UnitPrice * Quantity * ROUND(Discount, 2)) "
                            "FROM Orders_Details")
    check("Total discount cost", results["discounts"]["metrics"]["total_discount_cost"],
          disc_sql, failures)

    d = results["delivery"]["metrics"]
    late_sql = scalar(conn, """
        SELECT AVG(ShippedDate > RequiredDate) FROM Orders
        WHERE ShippedDate IS NOT NULL
          AND CAST(julianday(RequiredDate) - julianday(OrderDate) AS INT) = 14""")
    check("Late rate, 14-day orders", d["tight_late_rate"], late_sql, failures)
    n_late_sql = scalar(conn, "SELECT COUNT(*) FROM Orders WHERE ShippedDate > RequiredDate")
    check("Late order count", d["n_late"], n_late_sql, failures)

    conn.close()
    if failures:
        raise AssertionError(f"Verification failed: {failures}")
    print("All cross-checks passed.")
    return True
