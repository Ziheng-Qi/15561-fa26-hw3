"""Run the HW3 pipeline: analysis, checks, CSV export and webpage."""

from . import build_site, data_prep, questions, verify

OUTPUT_DIR = data_prep.REPO_ROOT / "outputs"


def export_tables(results):
    """Save the analysis tables as CSV files in ``outputs/``.

    Args:
        results (dict): Analysis results keyed by question, as built in
            ``main``.

    Returns:
        list[str]: Sorted names of the CSV files written.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    exports = {
        "q1_monthly_revenue.csv": results["market"]["monthly"],
        "q1_country_jan_apr.csv": results["market"]["by_country"],
        "q1_decline_check.csv": results["market"]["decline_check"],
        "q2_customer_revenue.csv": results["concentration"]["by_customer"],
        "q3_discount_tiers.csv": results["discounts"]["by_tier"],
        "q4_late_by_window.csv": results["delivery"]["by_window"],
        "q4_late_by_shipper.csv": results["delivery"]["by_shipper"],
        "q4_late_by_employee.csv": results["delivery"]["by_employee"],
    }
    for name, df in exports.items():
        df.to_csv(OUTPUT_DIR / name, index=False)
    return sorted(exports)


def main():
    """Run every analysis, verify it, and write the CSVs and webpage.

    Args:
        None.

    Returns:
        dict: Order lines and each question's result, keyed by
        ``lines``, ``market``, ``concentration``, ``discounts`` and
        ``delivery``.

    Raises:
        AssertionError: If an SQL cross-check fails.
    """
    tables = data_prep.load_tables()
    lines = data_prep.build_order_lines(tables)
    orders = data_prep.build_orders(tables)
    results = {
        "lines": lines,
        "market": questions.market_growth(lines),
        "concentration": questions.customer_concentration(lines, tables["Customers"]),
        "discounts": questions.discount_effectiveness(lines),
        "delivery": questions.delivery_reliability(orders),
    }
    verify.run_checks(results, tables)
    written = export_tables(results)
    page = build_site.write_site(
        market=results["market"], conc=results["concentration"],
        disc=results["discounts"], deliv=results["delivery"], lines=lines,
    )
    print(f"Wrote {len(written)} tables to {OUTPUT_DIR} and the webpage to {page}")
    return results


if __name__ == "__main__":
    main()
