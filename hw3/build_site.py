"""Render the analysis results as a static HTML page in ``docs/``."""

import html

from . import data_prep
from .questions import RECENCY_THRESHOLD_DAYS

REPO_URL = "https://github.com/Ziheng-Qi/15561-fa26-hw3"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def money(value):
    """Format a dollar amount without cents.

    Args:
        value (float): Amount in USD.

    Returns:
        str: Amount such as ``$1,234``.
    """
    return f"${value:,.0f}"


def pct(value, digits=0):
    """Format a fraction as a percentage.

    Args:
        value (float): Fraction, where 1.0 is 100%.
        digits (int): Decimal places to show.

    Returns:
        str: Percentage such as ``25%``.
    """
    return f"{value:.{digits}%}"


def fig_html(fig):
    """Convert a Plotly figure to an embeddable HTML fragment.

    Plotly.js is not included; the page loads it once from a CDN.

    Args:
        fig (plotly.graph_objects.Figure): Figure to embed.

    Returns:
        str: ``<div>`` and ``<script>`` markup for the figure.
    """
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False, "responsive": True})


def table_html(df, formats, caption):
    """Render selected DataFrame columns as an HTML table.

    Args:
        df (pandas.DataFrame): Rows to show, in display order.
        formats (dict[str, Callable | None]): Column name to formatter,
            in display order; keys are also the headers, and ``None``
            uses ``str``.
        caption (str): Table caption.

    Returns:
        str: Escaped HTML table inside a horizontally scrollable div.
    """
    head = "".join(f"<th>{html.escape(col)}</th>" for col in formats)
    rows = []
    for _, row in df.iterrows():
        cells = "".join(
            f"<td>{html.escape(fmt(row[col]) if fmt else str(row[col]))}</td>"
            for col, fmt in formats.items()
        )
        rows.append(f"<tr>{cells}</tr>")
    return (f'<div class="table-wrap"><table><caption>{html.escape(caption)}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def section(number, anchor, question, why, approach, visuals, finding, implication):
    """Assemble one business-question section of the page.

    Args:
        number (int): Question number shown above the heading.
        anchor (str): HTML id targeted by the navigation links.
        question (str): The business question, used as the heading.
        why (str): HTML for "Why it matters".
        approach (str): HTML for "Approach".
        visuals (str): HTML for the figures and tables.
        finding (str): HTML for "Main finding".
        implication (str): HTML for "Business implication".

    Returns:
        str: The ``<section>`` HTML.
    """
    return f"""
<section class="q" id="{anchor}">
  <p class="eyebrow">Question {number}</p>
  <h2>{question}</h2>
  <div class="grid2">
    <div><h3>Why it matters</h3>{why}</div>
    <div><h3>Approach</h3>{approach}</div>
  </div>
  {visuals}
  <div class="callouts">
    <div class="callout finding"><h3>Main finding</h3>{finding}</div>
    <div class="callout implication"><h3>Business implication</h3>{implication}</div>
  </div>
</section>"""


def render_market(r):
    """Build the Question 1 section on market growth.

    Args:
        r (dict): Result of ``questions.market_growth``.

    Returns:
        str: Section HTML.
    """
    m = r["metrics"]
    declining = ", ".join(
        f"{d['Country']} ({money(d['Rev1997'])} &rarr; {money(d['Rev1998'])})"
        for d in sorted(m["declining"], key=lambda d: d["Change"])
    )
    tbl = r["by_country"].copy()
    tbl["Growth"] = tbl["Multiple"]
    watch = tbl[(tbl["Change"] < 0) | (~tbl["BeatsCompany"] & tbl["Rev1997"].gt(0))]
    watch = watch.rename(columns={"Rev1997": "Jan-Apr 1997", "Rev1998": "Jan-Apr 1998"})
    table = table_html(
        watch.sort_values("Growth"),
        {"Country": None, "Jan-Apr 1997": money, "Jan-Apr 1998": money,
         "Change": money, "Growth": lambda v: f"{v:.2f}x"},
        f"Markets growing slower than the company's {m['company_multiple']:.1f}x, or shrinking",
    )
    check = r["decline_check"].rename(columns={
        "TopCustomer": "Largest 1997 order from", "TopOrder": "Order size",
        "ChangeExTop": "Change without it", "Prior6": "May-Oct 1997",
        "Last6": "Nov 1997-Apr 1998"})
    table += table_html(
        check,
        {"Country": None, "Largest 1997 order from": None, "Order size": money,
         "Change without it": money, "May-Oct 1997": money,
         "Nov 1997-Apr 1998": money, "Verdict": None},
        "Is the decline real? Order-level check of the shrinking markets",
    )
    verdicts = " ".join(
        f"<b>{c['Country']}</b>: {html.escape(c['Verdict'])}." for c in m["decline_check"]
    )
    broad = [c["Country"] for c in m["decline_check"] if c["Verdict"].startswith("Broad")]
    lost = [c for c in m["decline_check"] if c["Verdict"].startswith("One lost")]
    soft = [c["Country"] for c in m["decline_check"] if c["Verdict"].startswith("Soft")]
    oneoff = [c["Country"] for c in m["decline_check"] if c["Verdict"].startswith("No real")]
    return section(
        1, "markets",
        "Which customer markets are growing or shrinking, and where should sales attention go?",
        "<p>The company is expanding quickly. Overall growth can hide markets that are "
        "stalling. A shrinking market while the business doubles usually means lost "
        "accounts or a competitor, and it calls for a different response than a market "
        "that is simply small.</p>",
        "<p>Net revenue is unit price &times; quantity &times; (1 &minus; discount), summed "
        "by the customer's country. The data ends on "
        f"{m['last_date']:%B %d, %Y}, so comparing calendar years would be unfair. I compare "
        "the same window, <b>January 1 to April 30</b>, in 1997 and 1998. Countries are "
        "ranked by dollar change, not percent, so tiny bases (Spain grew from $338) "
        "do not dominate. Small markets have only a few orders per window, so each "
        "shrinking market gets an order-level check: redo the comparison without its "
        "largest Jan-Apr 1997 order, compare the last six full months with the six "
        "before, and see whether that customer is still ordering.</p>",
        fig_html(r["figures"][0]) + fig_html(r["figures"][1]) + table,
        f"<p>Jan-Apr revenue grew from {money(m['total_1997'])} to {money(m['total_1998'])} "
        f"(<b>{m['company_multiple']:.1f}x</b>). {', '.join(m['top3'])} supplied "
        f"{pct(m['top3_share_of_growth'])} of the dollar growth. {len(m['declining'])} "
        f"markets show lower Jan-Apr revenue: {declining}. The order-level check shows "
        f"<b>{'none' if not broad else ', '.join(broad)} of them "
        f"{'is' if len(broad) == 1 else 'are'} a broad decline</b>; "
        + ("in every case the drop disappears once the single largest 1997 order is "
           "removed. " if not broad else "")
        + f"{verdicts} Another five ({', '.join(m['lagging'])}) grew, but slower "
        "than the company; France was nearly flat.</p>",
        "<p>Keep investing in the USA, Germany and Brazil, where growth is concentrated. "
        "Do not treat the shrinking markets as one problem. "
        + (f"{', '.join(oneoff)}: no action beyond normal account care; the dip is one "
           "large order not repeated. " if oneoff else "")
        + (f"{', '.join(c['Country'] for c in lost)}: a <b>win-back call</b> to "
           f"{', '.join(c['TopCustomer'] for c in lost)} (see Question 2). " if lost else "")
        + (f"{', '.join(soft)}: small markets that are softening; check in with the "
           "main customers, but this is not yet a loss. " if soft else "")
        + "France is a large market with flat sales, so it is the best place to test a "
        "growth push. Lesson for the dashboard: in small markets, a year-over-year drop "
        "should always be checked order by order before anyone acts on it.</p>",
    )


def render_concentration(r):
    """Build the Question 2 section on key accounts.

    Args:
        r (dict): Result of ``questions.customer_concentration``.

    Returns:
        str: Section HTML.
    """
    m = r["metrics"]
    quiet = "; ".join(
        f"#{q['Rank']} {html.escape(q['CompanyName'])} ({q['Country']}, {money(q['Revenue'])}, "
        f"last order {q['LastOrder']:%b %d, %Y})" for q in m["quiet_top"]
    )
    top = r["by_customer"].head(10).copy()
    top["Last order"] = top["LastOrder"].dt.strftime("%Y-%m-%d")
    top = top.rename(columns={"CompanyName": "Customer", "CumShare": "Cumulative"})
    table = table_html(
        top,
        {"Rank": str, "Customer": None, "Country": None, "Revenue": money,
         "Share": lambda v: pct(v, 1), "Cumulative": lambda v: pct(v, 1),
         "Orders": str, "Last order": None},
        "Top 10 customers by lifetime net revenue",
    )
    return section(
        2, "concentration",
        "How dependent is revenue on a few customers, and are any key accounts going quiet?",
        "<p>If a handful of accounts drive the business, losing one is a material risk, and "
        "those accounts deserve dedicated account management. Spotting a big customer that "
        "has stopped ordering early gives sales a chance to win it back.</p>",
        "<p>Lifetime net revenue per customer, sorted into a Pareto curve. For recency, "
        f"I flag customers with no order in the last {RECENCY_THRESHOLD_DAYS} days before "
        "the data ends. The median gap between a customer's orders is 35 days and 75% of "
        "gaps are under 76 days, so 90 days is unusually long. I focus on the top quarter "
        "of customers by revenue.</p>",
        fig_html(r["figures"][0]) + table,
        f"<p>{m['n_customers']} of {m['n_registered']} registered customers placed orders "
        f"({len(m['never_ordered'])} never did). The top 3 ({', '.join(m['top3_names'])}) "
        f"generate <b>{pct(m['top3_share'])}</b> of revenue and the top 10 generate "
        f"{pct(m['top10_share'])}. It takes {m['n_for_80']} customers to reach 80%. The base "
        f"is concentrated at the top but not dangerously overall (HHI {m['hhi']:.3f}). In the "
        f"top {m['top_quarter_n']}, two accounts have gone quiet: {quiet}. Together they "
        f"represent {money(m['quiet_top_revenue'])} of lifetime revenue.</p>",
        "<p>Assign named account managers to the top 3 accounts: losing any one of them "
        "would erase roughly 8-9% of revenue. Call Mère Paillarde and Blondel père et fils "
        "now. Mère Paillarde bought $10,420 in Jan-Apr 1997 and nothing in Jan-Apr 1998, "
        "which is more than Canada's entire decline in Question 1. "
        "A simple monthly \"top customers with no order in 90 days\" report, as built here, "
        "would catch the next case automatically.</p>",
    )


def render_discounts(r):
    """Build the Question 3 section on discounts.

    Args:
        r (dict): Result of ``questions.discount_effectiveness``.

    Returns:
        str: Section HTML.
    """
    m = r["metrics"]
    t = r["by_tier"].rename(columns={"TierLabel": "Discount", "MedianQty": "Median units",
                                     "MeanQty": "Mean units", "NetRevenue": "Net revenue",
                                     "DiscountCost": "Discount given"})
    table = table_html(
        t, {"Discount": None, "Lines": str, "Median units": lambda v: f"{v:.0f}",
            "Mean units": lambda v: f"{v:.1f}", "Net revenue": money,
            "Discount given": money},
        "Order lines by discount tier",
    )
    return section(
        3, "discounts",
        "Are discounts buying extra volume, or just giving away margin?",
        "<p>Discounts cost real money. If deeper discounts do not lead to bigger orders, the "
        "company can tighten its discount policy and keep the difference with little risk "
        "to volume.</p>",
        "<p>I compare units per order line across the standard discount tiers (0, 5, 10, 15, "
        f"20, 25%). {m['odd_lines']} lines with one-off discounts (1-6%) are excluded from the "
        "tier view. To control for product mix, I also compare each product's average "
        "quantity with and without a discount. Discount cost = list-price revenue minus net "
        "revenue. This is observational data, so differences are associations, not proof "
        "of cause.</p>",
        fig_html(r["figures"][0]) + table,
        f"<p>Discounts cost {money(m['total_discount_cost'])} "
        f"({pct(m['discount_cost_share_of_gross'], 1)} of list-price revenue) across "
        f"{pct(m['share_lines_discounted'])} of order lines. Discounted lines are larger "
        f"(mean {m['mean_qty_disc']:.1f} vs {m['mean_qty_none']:.1f} units), and "
        f"{pct(m['share_products_more_qty'])} of products sell more units per line when "
        f"discounted. <b>Deeper discounts, however, buy nothing extra</b>: lines at 25% "
        f"average {m['tier25_mean']:.1f} units, the same as lines at 5% "
        f"({m['tier05_mean']:.1f}; Mann-Whitney p = {m['tier25_vs_05_p']:.2f}). Tiers above "
        f"5% account for {money(m['deep_tier_cost'])} of the discount cost.</p>",
        "<p>Some discount seems to help: discounted lines are bigger. But 15-25% discounts "
        "show no volume gain over 5%. If those lines had been given 5% at the same quantity, "
        f"the company would have kept about <b>{money(m['savings_if_capped'])}</b>, which "
        "is roughly 4.6% of total revenue. Recommendation: make 5% the default, require "
        "manager approval above 10%, and run a short A/B-style pilot with a few accounts "
        "to confirm volume holds.</p>",
    )


def render_delivery(r):
    """Build the Question 4 section on late deliveries.

    Args:
        r (dict): Result of ``questions.delivery_reliability``.

    Returns:
        str: Section HTML.
    """
    m = r["metrics"]
    emp = r["by_employee"].rename(columns={"EmployeeName": "Sales rep", "LateOrders": "Late",
                                           "LateRate": "Late rate",
                                           "MeanLeadDays": "Avg days to ship"})
    table = table_html(
        emp, {"Sales rep": None, "Orders": str, "Late": str,
              "Late rate": lambda v: pct(v, 1), "Avg days to ship": lambda v: f"{v:.1f}"},
        "Late rate by sales representative (shipped orders)",
    )
    return section(
        4, "delivery",
        "Where do late deliveries come from: the shipper, the sales rep, or the deadline?",
        "<p>Late deliveries hurt customer retention, especially for wholesale food "
        "customers restocking shelves. Fixing them requires knowing the cause. Switching "
        "shippers will not help if the problem is internal.</p>",
        "<p>An order is late if it shipped after its required date (the only delivery "
        f"commitment in the data). {m['n_unshipped']} orders placed after early April 1998 "
        "had not shipped by the end of the data and are excluded; none were already past "
        "due. I compare late rates by shipper, sales rep, and the time the customer allowed "
        "(order date to required date, which is always 14, 28 or 42 days), and use "
        "Fisher's exact and chi-square tests to check whether gaps exceed chance.</p>",
        fig_html(r["figures"][0]) + table,
        f"<p>Overall {pct(m['late_rate'], 1)} of shipped orders were late ({m['n_late']} of "
        f"{m['n_shipped']}). Shippers barely differ ({pct(m['shipper_min'], 1)} to "
        f"{pct(m['shipper_max'], 1)}; chi-square p = {m['shipper_p']:.2f}). The real "
        f"driver is the deadline: orders with only {m['tight_days']} days allowed are late "
        f"<b>{pct(m['tight_late_rate'])}</b> of the time vs {pct(m['standard_late_rate'], 1)} "
        f"for the standard 28 days (Fisher p &lt; 0.001), and they account for "
        f"{pct(m['tight_share_of_late'])} of all late orders while being only "
        f"{m['tight_orders']} orders. Worse, these rush orders are not handled faster. They "
        f"take {m['tight_lead']:.1f} days to ship on average vs {m['standard_lead']:.1f} "
        f"for standard orders (p = {m['lead_p']:.2f}).</p>",
        "<p>Do not renegotiate shipping contracts over lateness; the shippers perform about "
        "the same. Instead, <b>flag 14-day orders in the warehouse and ship them first</b>. "
        "Today they wait in the same queue as everything else. Rep-level differences are "
        "based on few late orders (1-10 each). Treat them as a coaching conversation, not "
        "a performance verdict.</p>",
    )


CSS = """
:root{--ink:#1f2933;--muted:#52606d;--line:#e4e7eb;--bg:#f7f8fa;--card:#fff;
--accent:#2f5d8a;--good:#3a8a5c;--warn:#b7791f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,Helvetica,Arial,sans-serif}
header{background:#1f3a56;color:#fff;padding:48px 16px 40px}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
header h1{margin:0 0 8px;font-size:2rem;line-height:1.2}
header p{margin:0;color:#d9e2ec;max-width:760px}
nav{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:20px}
nav a{color:#fff;opacity:.85;font-size:.95rem}
main{padding:24px 0 48px}
.summary,.q,.notes{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:24px;margin:24px 0}
.summary ol{padding-left:20px;margin:8px 0 0}.summary li{margin:6px 0}
.eyebrow{text-transform:uppercase;letter-spacing:.08em;font-size:.75rem;color:var(--accent);
font-weight:700;margin:0}
h2{margin:4px 0 16px;font-size:1.45rem;line-height:1.3}
h3{font-size:.95rem;margin:0 0 4px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.grid2,.callouts{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.callouts{margin-top:16px}
.callout{border-left:4px solid var(--accent);background:#f0f4f8;padding:14px 16px;border-radius:6px}
.callout.implication{border-color:var(--good);background:#eef6f1}
.callout p,.grid2 p{margin:0}
.table-wrap{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:.9rem}
caption{text-align:left;font-weight:600;padding:4px 0 8px;color:var(--muted)}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{background:#f5f7fa}
footer{color:var(--muted);font-size:.85rem;text-align:center;padding:24px 16px}
a{color:var(--accent)}
@media (max-width:760px){.grid2,.callouts{grid-template-columns:1fr}header h1{font-size:1.5rem}}
"""


def render_page(market, conc, disc, deliv, lines):
    """Build the complete HTML page.

    Args:
        market (dict): Result of ``questions.market_growth``.
        conc (dict): Result of ``questions.customer_concentration``.
        disc (dict): Result of ``questions.discount_effectiveness``.
        deliv (dict): Result of ``questions.delivery_reliability``.
        lines (pandas.DataFrame): Order lines, for headline totals.

    Returns:
        str: Full HTML document.
    """
    total = lines["Revenue"].sum()
    n_orders = lines["OrderID"].nunique()
    start, end = lines["OrderDate"].min(), lines["OrderDate"].max()
    mm, cm, dm, lm = (x["metrics"] for x in (market, conc, disc, deliv))
    summary = f"""
<section class="summary">
  <h2>Executive summary</h2>
  <p>Northwind Traders sold {money(total)} across {n_orders} orders from
  {start:%b %Y} to {end:%b %Y}. Four things a manager should act on:</p>
  <ol>
    <li><a href="#markets">Growth is strong but uneven.</a> Jan-Apr revenue grew
    {mm['company_multiple']:.1f}x year over year. Four small markets dipped, but an
    order-level check shows no broad decline: Denmark's dip is one large 1997 order, Canada
    lost one account, and Mexico and Finland are softening.</li>
    <li><a href="#concentration">Three customers bring in {pct(cm['top3_share'])} of revenue</a>,
    and two top-25 accounts have not ordered in 90+ days.</li>
    <li><a href="#discounts">Discounts above 5% buy no extra volume.</a> Capping them could
    have kept about {money(dm['savings_if_capped'])}.</li>
    <li><a href="#delivery">Late deliveries come from tight deadlines, not shippers.</a>
    14-day orders are late {pct(lm['tight_late_rate'])} of the time and are not prioritized.</li>
  </ol>
</section>"""
    notes = f"""
<section class="notes" id="method">
  <h2>Data and method notes</h2>
  <ul>
    <li>Source: the course-provided Northwind workbook (Orders, Order Details, Customers,
    Products, Categories, Employees, Shippers, Suppliers).</li>
    <li>Net revenue = UnitPrice &times; Quantity &times; (1 &minus; Discount), using the price
    on each order line (prices changed over time, so the product list price is not used).
    Total net revenue is {money(total)}. It is cross-checked against an independent SQL
    calculation in <code>hw3/verify.py</code>.</li>
    <li>Discounts are stored as 32-bit floats (5% is read as 0.0500000007), so they are
    rounded to two decimals before grouping.</li>
    <li>Data ends {end:%B %d, %Y}. Year-over-year comparisons use Jan-Apr only.</li>
    <li>All results are associations in historical data. The discount and delivery
    recommendations should be confirmed with a small pilot.</li>
    <li>Code, data and reproduction steps: <a href="{REPO_URL}">{REPO_URL}</a>.</li>
  </ul>
</section>"""
    body = "".join([
        summary, render_market(market), render_concentration(conc),
        render_discounts(disc), render_delivery(deliv), notes,
    ])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Business Review</title>
<script src="{PLOTLY_CDN}"></script>
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
  <h1>Northwind Traders: where to focus next</h1>
  <p>A data review for the sales and operations manager: market growth, customer risk,
  discount policy and delivery reliability. 15.561 HW3.</p>
  <nav><a href="#markets">1. Markets</a><a href="#concentration">2. Key accounts</a>
  <a href="#discounts">3. Discounts</a><a href="#delivery">4. Delivery</a>
  <a href="#method">Method</a></nav>
</div></header>
<main><div class="wrap">{body}</div></main>
<footer>Built with Python (pandas, SciPy, Plotly). Charts are interactive: hover for values.</footer>
</body>
</html>"""


def write_site(out_path=data_prep.REPO_ROOT / "docs" / "index.html", **results):
    """Write the webpage to disk.

    Args:
        out_path (pathlib.Path): Destination file; parent folders are
            created and an existing file is overwritten.
        **results (Any): Arguments for ``render_page``: ``market``,
            ``conc``, ``disc``, ``deliv`` and ``lines``.

    Returns:
        pathlib.Path: ``out_path``.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_page(**results), encoding="utf-8")
    return out_path
