"""Analyses and Plotly figures for the four business questions."""

import pandas as pd
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ACCENT = "#2f5d8a"
GOOD = "#3a8a5c"
BAD = "#c0504d"
MUTED = "#9aa5b1"
FONT = dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color="#1f2933")

# The data ends on 1998-05-06, so May 1998 is a partial month. Year-over-year
# comparisons use the same calendar window (Jan 1 - Apr 30) in both years.
YOY_START_MONTH = 1
YOY_END_MONTH = 4
RECENCY_THRESHOLD_DAYS = 90
# Six full months before the data ends vs the six months before that.
ROLLING_PRIOR = (pd.Timestamp("1997-05-01"), pd.Timestamp("1997-11-01"))
ROLLING_LAST = (pd.Timestamp("1997-11-01"), pd.Timestamp("1998-05-01"))
STANDARD_TIERS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
BENCHMARK_TIER = 0.05


def _style(fig, title, height=420):
    """Apply the shared layout to a Plotly figure.

    Args:
        fig (plotly.graph_objects.Figure): Figure to style.
        title (str): Chart title; may contain Plotly HTML tags.
        height (int): Figure height in pixels.

    Returns:
        plotly.graph_objects.Figure: ``fig``, modified in place.
    """
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16)),
        font=FONT,
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=1, xanchor="right"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#cbd2d9")
    fig.update_yaxes(gridcolor="#e4e7eb", zeroline=False)
    return fig


def market_growth(lines):
    """Compare revenue by customer country, Jan-Apr 1997 vs 1998.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.

    Returns:
        dict: ``monthly`` (revenue per month, last month flagged
        partial), ``by_country`` (Jan-Apr revenue per year, change and
        growth multiple, sorted by change), ``metrics`` (summary values
        for the webpage) and ``figures`` (trend line, country bars).
    """
    monthly = (
        lines.groupby(lines["OrderDate"].dt.to_period("M"))["Revenue"]
        .sum()
        .rename("Revenue")
        .reset_index()
    )
    monthly["Month"] = monthly["OrderDate"].dt.to_timestamp()
    last_date = lines["OrderDate"].max()
    monthly["Partial"] = monthly["OrderDate"] == last_date.to_period("M")

    window = lines[lines["OrderDate"].dt.month.between(YOY_START_MONTH, YOY_END_MONTH)]
    by_country = (
        window.pivot_table(index="Country", columns=window["OrderDate"].dt.year,
                           values="Revenue", aggfunc="sum")
        .reindex(columns=[1997, 1998])
        .fillna(0.0)
    )
    by_country.columns = ["Rev1997", "Rev1998"]
    by_country["Change"] = by_country["Rev1998"] - by_country["Rev1997"]
    total_1997 = by_country["Rev1997"].sum()
    total_1998 = by_country["Rev1998"].sum()
    company_multiple = total_1998 / total_1997
    by_country["Multiple"] = by_country["Rev1998"] / by_country["Rev1997"].where(
        by_country["Rev1997"] > 0
    )
    by_country["BeatsCompany"] = by_country["Multiple"] >= company_multiple
    by_country = by_country.sort_values("Change", ascending=False).reset_index()

    fig_trend = go.Figure()
    full = monthly[~monthly["Partial"]]
    fig_trend.add_trace(go.Scatter(
        x=full["Month"], y=full["Revenue"], mode="lines+markers",
        line=dict(color=ACCENT, width=2.5), name="Monthly revenue",
        hovertemplate="%{x|%b %Y}: $%{y:,.0f}<extra></extra>",
    ))
    part = monthly[monthly["Partial"]]
    fig_trend.add_trace(go.Scatter(
        x=part["Month"], y=part["Revenue"], mode="markers",
        marker=dict(color=MUTED, size=9, symbol="circle-open"),
        name=f"Partial month (data ends {last_date:%b %d, %Y})",
        hovertemplate="%{x|%b %Y} (partial): $%{y:,.0f}<extra></extra>",
    ))
    fig_trend.update_yaxes(title_text="Net revenue (USD)", tickprefix="$", tickformat=",.0f")
    fig_trend.update_xaxes(title_text="Order month")
    _style(fig_trend, "Monthly net revenue, Jul 1996 - May 1998", height=360)

    colors = [GOOD if b else (BAD if c < 0 else MUTED)
              for b, c in zip(by_country["BeatsCompany"], by_country["Change"])]
    plot_df = by_country.iloc[::-1]
    fig_country = go.Figure(go.Bar(
        x=plot_df["Change"], y=plot_df["Country"], orientation="h",
        marker_color=colors[::-1],
        customdata=plot_df[["Rev1997", "Rev1998", "Multiple"]],
        hovertemplate=("%{y}<br>Jan-Apr 1997: $%{customdata[0]:,.0f}"
                       "<br>Jan-Apr 1998: $%{customdata[1]:,.0f}"
                       "<br>Change: $%{x:,.0f}<extra></extra>"),
    ))
    fig_country.update_xaxes(title_text="Change in net revenue, Jan-Apr 1998 vs Jan-Apr 1997 (USD)",
                             tickprefix="$", tickformat=",.0f")
    _style(fig_country,
           (f"Revenue change by customer country (company grew {company_multiple:.1f}x)"
            "<br><sup>Green = grew faster than the company, grey = slower or new market, "
            "red = shrank</sup>"),
           height=620)

    declining = by_country[by_country["Change"] < 0]
    decline_check = _decline_check(lines, declining["Country"].tolist())
    lagging = by_country[(by_country["Change"] >= 0) & (~by_country["BeatsCompany"])
                         & by_country["Rev1997"].gt(0)]
    top3 = by_country.head(3)
    metrics = {
        "decline_check": decline_check.to_dict("records"),
        "total_1997": total_1997,
        "total_1998": total_1998,
        "company_multiple": company_multiple,
        "declining": declining[["Country", "Rev1997", "Rev1998", "Change"]].to_dict("records"),
        "declining_loss": -declining["Change"].sum(),
        "lagging": lagging["Country"].tolist(),
        "top3": top3["Country"].tolist(),
        "top3_share_of_growth": top3["Change"].sum() / by_country["Change"].sum(),
        "last_date": last_date,
    }
    return {"monthly": monthly, "by_country": by_country,
            "decline_check": decline_check, "metrics": metrics,
            "figures": [fig_trend, fig_country]}


def _decline_check(lines, countries):
    """Test whether each country's Jan-Apr decline is a real trend.

    For each country, the largest single Jan-Apr 1997 order is removed
    and the comparison is redone, and the last six full months are
    compared with the six before. A verdict combines both checks with
    whether the customer behind that order has gone quiet.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.
        countries (list[str]): Customer countries to check.

    Returns:
        pandas.DataFrame: One row per country with the largest 1997
        order (``TopCustomer``, ``TopOrder``), ``ChangeExTop`` (USD),
        ``Prior6``/``Last6`` revenue (USD), ``Last6Change`` (fraction)
        and ``Verdict``.
    """
    last_date = lines["OrderDate"].max()
    window = lines[lines["OrderDate"].dt.month.between(YOY_START_MONTH, YOY_END_MONTH)]
    orders = (
        window.groupby(["Country", "CompanyName", "OrderID", "OrderDate"])["Revenue"]
        .sum().reset_index()
    )
    last_order = lines.groupby("CompanyName")["OrderDate"].max()
    rows = []
    for country in countries:
        o = orders[orders["Country"] == country]
        y97 = o[o["OrderDate"].dt.year == 1997]
        y98 = o[o["OrderDate"].dt.year == 1998]
        top = y97.loc[y97["Revenue"].idxmax()]
        change_ex_top = y98["Revenue"].sum() - (y97["Revenue"].sum() - top["Revenue"])
        c = lines[lines["Country"] == country]
        prior6 = c.loc[c["OrderDate"].between(*ROLLING_PRIOR, inclusive="left"), "Revenue"].sum()
        last6 = c.loc[c["OrderDate"].between(*ROLLING_LAST, inclusive="left"), "Revenue"].sum()
        quiet_days = (last_date - last_order[top["CompanyName"]]).days
        if change_ex_top < 0:
            verdict = "Broad decline across accounts"
        elif quiet_days > RECENCY_THRESHOLD_DAYS:
            verdict = f"One lost account ({top['CompanyName']}); rest of market growing"
        elif last6 >= prior6:
            verdict = "No real decline: driven by one large 1997 order"
        else:
            verdict = (f"Softening (last 6 months {last6 / prior6 - 1:.0%}), "
                       "no account lost")
        rows.append({
            "Country": country, "TopCustomer": top["CompanyName"],
            "TopOrder": top["Revenue"], "ChangeExTop": change_ex_top,
            "Prior6": prior6, "Last6": last6, "Last6Change": last6 / prior6 - 1,
            "TopCustomerQuietDays": quiet_days, "Verdict": verdict,
        })
    return pd.DataFrame(rows)


def customer_concentration(lines, customers):
    """Measure revenue concentration and recency by customer.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.
        customers (pandas.DataFrame): Customers sheet; used to find
            registered customers with no orders.

    Returns:
        dict: ``by_customer`` (revenue, share, cumulative share and
        days since last order, ranked by revenue), ``metrics`` (summary
        values for the webpage) and ``figures`` (Pareto chart).
    """
    last_date = lines["OrderDate"].max()
    by_cust = (
        lines.groupby(["CustomerID", "CompanyName", "Country"])
        .agg(Revenue=("Revenue", "sum"), Orders=("OrderID", "nunique"),
             LastOrder=("OrderDate", "max"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
        .reset_index(drop=True)
    )
    total = by_cust["Revenue"].sum()
    by_cust["Share"] = by_cust["Revenue"] / total
    by_cust["CumShare"] = by_cust["Share"].cumsum()
    by_cust["Rank"] = by_cust.index + 1
    by_cust["DaysSinceLastOrder"] = (last_date - by_cust["LastOrder"]).dt.days
    by_cust["Quiet"] = by_cust["DaysSinceLastOrder"] > RECENCY_THRESHOLD_DAYS

    n_for_80 = int((by_cust["CumShare"] < 0.8).sum() + 1)
    hhi = float((by_cust["Share"] ** 2).sum())
    top_quarter = by_cust.head(len(by_cust) // 4)
    quiet_top = top_quarter[top_quarter["Quiet"]]
    never_ordered = sorted(set(customers["CustomerID"]) - set(by_cust["CustomerID"]))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bar_colors = [BAD if q else ACCENT for q in by_cust["Quiet"]]
    fig.add_trace(go.Bar(
        x=by_cust["Rank"], y=by_cust["Revenue"], marker_color=bar_colors,
        name="Customer revenue", customdata=by_cust[["CompanyName", "DaysSinceLastOrder"]],
        hovertemplate=("#%{x} %{customdata[0]}<br>$%{y:,.0f}"
                       "<br>%{customdata[1]} days since last order<extra></extra>"),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=by_cust["Rank"], y=by_cust["CumShare"], mode="lines",
        line=dict(color="#1f2933", width=2), name="Cumulative share of revenue",
        hovertemplate="Top %{x} customers: %{y:.0%}<extra></extra>",
    ), secondary_y=True)
    fig.add_hline(y=0.8, line_dash="dot", line_color=MUTED, secondary_y=True,
                  annotation_text="80% of revenue", annotation_position="bottom right")
    fig.update_xaxes(title_text="Customer rank by lifetime net revenue")
    fig.update_yaxes(title_text="Net revenue (USD)", tickprefix="$", tickformat=",.0f",
                     secondary_y=False)
    fig.update_yaxes(title_text="Cumulative share", tickformat=".0%", range=[0, 1.02],
                     secondary_y=True, showgrid=False)
    _style(fig, (f"Revenue by customer (red = no order in the last "
                 f"{RECENCY_THRESHOLD_DAYS} days)"), height=440)

    metrics = {
        "n_customers": len(by_cust),
        "n_registered": customers["CustomerID"].nunique(),
        "never_ordered": never_ordered,
        "top3_share": by_cust["Share"].head(3).sum(),
        "top10_share": by_cust["Share"].head(10).sum(),
        "n_for_80": n_for_80,
        "hhi": hhi,
        "top_quarter_n": len(top_quarter),
        "quiet_top": quiet_top[["Rank", "CompanyName", "Country", "Revenue",
                                "LastOrder", "DaysSinceLastOrder"]].to_dict("records"),
        "quiet_top_revenue": quiet_top["Revenue"].sum(),
        "top3_names": by_cust["CompanyName"].head(3).tolist(),
    }
    return {"by_customer": by_cust, "metrics": metrics, "figures": [fig]}


def discount_effectiveness(lines):
    """Compare units ordered and discount cost across discount tiers.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.

    Returns:
        dict: ``by_tier`` (lines, units and revenue per standard tier),
        ``per_product_ratio`` (pandas.Series of each product's mean
        units discounted / undiscounted), ``metrics`` (summary values
        and a Mann-Whitney p-value) and ``figures`` (box plot).
    """
    df = lines.copy()
    df["Tier"] = df["Discount"].where(df["Discount"].isin(STANDARD_TIERS))
    odd = df[df["Tier"].isna()]
    std = df[df["Tier"].notna()]

    by_tier = (
        std.groupby("Tier")
        .agg(Lines=("Quantity", "size"), MedianQty=("Quantity", "median"),
             MeanQty=("Quantity", "mean"), NetRevenue=("Revenue", "sum"),
             DiscountCost=("DiscountAmount", "sum"))
        .reset_index()
    )
    by_tier["TierLabel"] = (by_tier["Tier"] * 100).round().astype(int).astype(str) + "%"

    per_product = (
        df.assign(Discounted=df["Discount"] > 0)
        .groupby(["ProductID", "Discounted"])["Quantity"].mean()
        .unstack()
        .dropna()
    )
    ratio = per_product[True] / per_product[False]

    _, qty_p = stats.mannwhitneyu(
        std.loc[std["Tier"] == 0.25, "Quantity"], std.loc[std["Tier"] == BENCHMARK_TIER, "Quantity"]
    )
    deep = std[std["Tier"] > BENCHMARK_TIER]
    savings_if_capped = (deep["GrossRevenue"] * (deep["Tier"] - BENCHMARK_TIER)).sum()

    fig = go.Figure()
    for _, row in by_tier.iterrows():
        q = std.loc[std["Tier"] == row["Tier"], "Quantity"]
        fig.add_trace(go.Box(
            y=q, name=row["TierLabel"], boxpoints="outliers",
            marker_color=MUTED if row["Tier"] == 0 else ACCENT,
            line_width=1.5, showlegend=False,
            hovertemplate=f"{row['TierLabel']} discount<br>%{{y}} units<extra></extra>",
        ))
    fig.update_xaxes(title_text="Discount on the order line")
    fig.update_yaxes(title_text="Units ordered per line")
    _style(fig, "Units per order line by discount tier", height=420)

    no_disc = by_tier.loc[by_tier["Tier"] == 0].iloc[0]
    disc = std[std["Tier"] > 0]
    metrics = {
        "total_discount_cost": df["DiscountAmount"].sum(),
        "discount_cost_share_of_gross": df["DiscountAmount"].sum() / df["GrossRevenue"].sum(),
        "share_lines_discounted": (df["Discount"] > 0).mean(),
        "median_qty_none": no_disc["MedianQty"],
        "median_qty_disc": disc["Quantity"].median(),
        "mean_qty_none": no_disc["MeanQty"],
        "mean_qty_disc": disc["Quantity"].mean(),
        "n_products_compared": len(ratio),
        "share_products_more_qty": (ratio > 1).mean(),
        "median_product_ratio": ratio.median(),
        "odd_lines": len(odd),
        "deep_tier_cost": deep["DiscountAmount"].sum(),
        "savings_if_capped": savings_if_capped,
        "tier25_vs_05_p": qty_p,
        "tier25_mean": by_tier.loc[by_tier["Tier"] == 0.25, "MeanQty"].iloc[0],
        "tier05_mean": by_tier.loc[by_tier["Tier"] == 0.05, "MeanQty"].iloc[0],
    }
    return {"by_tier": by_tier, "per_product_ratio": ratio, "metrics": metrics,
            "figures": [fig]}


def _late_table(shipped, key):
    """Summarize late rate, lead time and freight per group.

    Args:
        shipped (pandas.DataFrame): Shipped orders from
            ``build_orders``.
        key (str): Column to group by.

    Returns:
        pandas.DataFrame: One row per group with ``Orders``,
        ``LateOrders``, ``LateRate``, ``MeanLeadDays`` and
        ``MeanFreight`` (USD).
    """
    return (
        shipped.groupby(key)
        .agg(Orders=("OrderID", "size"), LateOrders=("IsLate", "sum"),
             LateRate=("IsLate", "mean"), MeanLeadDays=("LeadDays", "mean"),
             MeanFreight=("Freight", "mean"))
        .reset_index()
    )


def delivery_reliability(orders):
    """Break down late shipments by allowed time, shipper and rep.

    Args:
        orders (pandas.DataFrame): Orders from ``build_orders``.

    Returns:
        dict: ``by_window``, ``by_shipper`` and ``by_employee`` late
        tables, ``overdue_unshipped`` (unshipped orders past their
        required date), ``metrics`` (summary values and test p-values)
        and ``figures`` (late-rate bar charts).
    """
    last_date = orders["OrderDate"].max()
    shipped = orders[orders["IsShipped"]]
    by_window = _late_table(shipped, "AllowedDays").sort_values("AllowedDays")
    by_shipper = _late_table(shipped, "ShipperName").sort_values("LateRate")
    by_employee = _late_table(shipped, "EmployeeName").sort_values("LateRate", ascending=False)

    unshipped = orders[~orders["IsShipped"]]
    overdue = unshipped[unshipped["RequiredDate"] < last_date]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("By time allowed (order to required date)",
                                        "By shipper"))
    win_labels = by_window["AllowedDays"].astype(str) + " days"
    fig.add_trace(go.Bar(
        x=win_labels, y=by_window["LateRate"],
        marker_color=[BAD if d == by_window["AllowedDays"].min() else ACCENT
                      for d in by_window["AllowedDays"]],
        text=[f"{r:.0%}<br>({l} of {n})" for r, l, n in
              zip(by_window["LateRate"], by_window["LateOrders"], by_window["Orders"])],
        textposition="outside", showlegend=False,
        hovertemplate="%{x}: %{y:.1%} late<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=by_shipper["ShipperName"], y=by_shipper["LateRate"], marker_color=ACCENT,
        text=[f"{r:.0%}<br>({l} of {n})" for r, l, n in
              zip(by_shipper["LateRate"], by_shipper["LateOrders"], by_shipper["Orders"])],
        textposition="outside", showlegend=False,
        hovertemplate="%{x}: %{y:.1%} late<extra></extra>",
    ), row=1, col=2)
    ymax = max(by_window["LateRate"].max(), by_shipper["LateRate"].max()) * 1.35
    fig.update_yaxes(tickformat=".0%", range=[0, ymax])
    fig.update_yaxes(title_text="Share of shipped orders delivered late", row=1, col=1)
    _style(fig, "Late shipment rate (shipped after the required date)", height=430)

    tight = by_window.iloc[0]
    standard = by_window[by_window["AllowedDays"] == 28].iloc[0]
    _, tight_p = stats.fisher_exact([
        [tight["LateOrders"], tight["Orders"] - tight["LateOrders"]],
        [standard["LateOrders"], standard["Orders"] - standard["LateOrders"]],
    ])
    _, shipper_p, _, _ = stats.chi2_contingency(
        by_shipper[["LateOrders"]].assign(OnTime=by_shipper["Orders"] - by_shipper["LateOrders"])
    )
    _, lead_p = stats.mannwhitneyu(
        shipped.loc[shipped["AllowedDays"] == tight["AllowedDays"], "LeadDays"],
        shipped.loc[shipped["AllowedDays"] == standard["AllowedDays"], "LeadDays"],
    )
    metrics = {
        "n_shipped": len(shipped),
        "n_late": int(shipped["IsLate"].sum()),
        "late_rate": shipped["IsLate"].mean(),
        "tight_days": int(tight["AllowedDays"]),
        "tight_orders": int(tight["Orders"]),
        "tight_late_rate": tight["LateRate"],
        "tight_lead": tight["MeanLeadDays"],
        "standard_late_rate": standard["LateRate"],
        "standard_lead": standard["MeanLeadDays"],
        "tight_share_of_late": tight["LateOrders"] / shipped["IsLate"].sum(),
        "shipper_min": by_shipper["LateRate"].min(),
        "shipper_max": by_shipper["LateRate"].max(),
        "best_shipper": by_shipper.iloc[0]["ShipperName"],
        "tight_p": tight_p,
        "shipper_p": shipper_p,
        "lead_p": lead_p,
        "n_unshipped": len(unshipped),
        "n_overdue_unshipped": len(overdue),
        "last_date": last_date,
    }
    return {"by_window": by_window, "by_shipper": by_shipper, "by_employee": by_employee,
            "overdue_unshipped": overdue, "metrics": metrics, "figures": [fig]}
