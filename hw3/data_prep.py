"""Load the Northwind workbook and build analysis-ready tables."""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "northwind.xlsx"

# Discounts are stored as 32-bit floats in the workbook (0.05 is read as
# 0.0500000007...), so they are rounded before any grouping or banding.
DISCOUNT_DECIMALS = 2


def load_tables(path=DATA_PATH):
    """Read every sheet of the Northwind workbook.

    Args:
        path (str | pathlib.Path): Excel workbook; defaults to
            ``data/northwind.xlsx`` in the repository.

    Returns:
        dict[str, pandas.DataFrame]: Sheets keyed by name, with
        surrounding whitespace stripped from each name.
    """
    tables = pd.read_excel(path, sheet_name=None)
    return {name.strip(): df for name, df in tables.items()}


def build_order_lines(tables):
    """Join order lines with order, customer and product details.

    Discounts are rounded to two decimals first because the workbook
    stores them as 32-bit floats.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: One row per order line, adding
        ``GrossRevenue``, ``Revenue`` (net of discount) and
        ``DiscountAmount``, all in USD.

    Raises:
        ValueError: If a join changes the number of order lines.
    """
    lines = tables["Orders Details"].copy()
    lines["Discount"] = lines["Discount"].round(DISCOUNT_DECIMALS)
    lines["GrossRevenue"] = lines["UnitPrice"] * lines["Quantity"]
    lines["Revenue"] = lines["GrossRevenue"] * (1 - lines["Discount"])
    lines["DiscountAmount"] = lines["GrossRevenue"] - lines["Revenue"]

    orders = tables["Orders"][
        ["OrderID", "CustomerID", "EmployeeID", "OrderDate",
         "RequiredDate", "ShippedDate", "ShipVia", "Freight"]
    ]
    customers = tables["Customers"][["CustomerID", "CompanyName", "Country"]]
    products = tables["Product"][["ProductID", "ProductName", "CategoryID"]]
    categories = tables["Categories"][["CategoryID", "CategoryName"]]

    merged = (
        lines.merge(orders, on="OrderID", how="left", validate="many_to_one")
        .merge(customers, on="CustomerID", how="left", validate="many_to_one")
        .merge(products, on="ProductID", how="left", validate="many_to_one")
        .merge(categories, on="CategoryID", how="left", validate="many_to_one")
    )
    if len(merged) != len(lines):
        raise ValueError("Join changed the number of order lines.")
    return merged


def build_orders(tables):
    """Add shipper, sales rep and timing fields to each order.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: One row per order, adding ``ShipperName``,
        ``EmployeeName``, ``AllowedDays`` (order to required date),
        ``LeadDays`` (order to ship date; NaN if unshipped),
        ``IsShipped`` and ``IsLate`` (shipped after required date).
    """
    orders = tables["Orders"].copy()
    shippers = tables["Shippers"].rename(
        columns={"ShipperID": "ShipVia", "CompanyName": "ShipperName"}
    )[["ShipVia", "ShipperName"]]
    employees = tables["Employees"][["EmployeeID", "FirstName", "LastName"]]
    orders = orders.merge(shippers, on="ShipVia", how="left").merge(
        employees, on="EmployeeID", how="left"
    )
    orders["EmployeeName"] = orders["FirstName"] + " " + orders["LastName"]
    orders["AllowedDays"] = (orders["RequiredDate"] - orders["OrderDate"]).dt.days
    orders["LeadDays"] = (orders["ShippedDate"] - orders["OrderDate"]).dt.days
    orders["IsShipped"] = orders["ShippedDate"].notna()
    orders["IsLate"] = orders["IsShipped"] & (
        orders["ShippedDate"] > orders["RequiredDate"]
    )
    return orders
