"""Chart images for the on-site deck. Same mart the dashboard uses."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from etl.config import DOCS_DIR

NAVY = "#0B1F3A"
TEAL = "#1F7A8C"
GOLD = "#C48B2F"
CREAM = "#F4F1EA"


def render_charts(mart: dict[str, pd.DataFrame]) -> dict[str, Path]:
    out = DOCS_DIR / "charts"
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "stores": out / "store_revenue.png",
        "products": out / "top_products.png",
        "hourly": out / "hourly_heatmap.png",
        "feed": out / "feed_coverage.png",
    }
    _store_chart(mart, paths["stores"])
    _product_chart(mart, paths["products"])
    _hourly_chart(mart, paths["hourly"])
    _feed_chart(mart, paths["feed"])
    return paths


def _style(ax, title: str) -> None:
    ax.set_title(title, loc="left", color=NAVY, fontsize=13, fontweight="bold", pad=10)
    ax.set_facecolor(CREAM)
    ax.figure.patch.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#333333")


def _store_chart(mart, path: Path) -> None:
    stores = mart["fact_sales"].merge(mart["dim_store"], on="STORE_ID")
    rev = (
        stores.groupby("STORE_NAME", as_index=False)["BASKET_VALUE"]
        .sum()
        .sort_values("BASKET_VALUE")
    )
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.barh(rev["STORE_NAME"], rev["BASKET_VALUE"] / 1_000_000, color=TEAL)
    _style(ax, "Revenue by store ($ millions, item-covered baskets)")
    ax.set_xlabel("")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _product_chart(mart, path: Path) -> None:
    prod = (
        mart["mart_product_perf"]
        .groupby("PRODUCT_NAME", as_index=False)["REVENUE"]
        .sum()
        .sort_values("REVENUE", ascending=False)
        .head(8)
        .sort_values("REVENUE")
    )
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.barh(prod["PRODUCT_NAME"], prod["REVENUE"] / 1_000, color=NAVY)
    _style(ax, "Top products by revenue ($ thousands)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _hourly_chart(mart, path: Path) -> None:
    hourly = mart["mart_hourly_dow"].groupby(["SALE_DOW", "SALE_HOUR"], as_index=False)["TXN_COUNT"].sum()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = hourly.pivot(index="SALE_DOW", columns="SALE_HOUR", values="TXN_COUNT").reindex(order)
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    grid = pivot.apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=float)
    image = ax.imshow(grid, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(list(pivot.index))
    hours = list(pivot.columns)
    ax.set_xticks(range(len(hours)))
    ax.set_xticklabels([f"{int(h):02d}" for h in hours], fontsize=8)
    _style(ax, "Transactions by weekday and hour")
    fig.colorbar(image, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _feed_chart(mart, path: Path) -> None:
    feed = mart["mart_feed_completeness"].copy()
    feed["MONTH"] = pd.to_datetime(feed["SALE_DATE"]).dt.to_period("M").dt.to_timestamp()
    monthly = feed.groupby("MONTH", as_index=False).agg(
        TXN=("TXN_COUNT", "sum"),
        WITH_ITEMS=("TXN_WITH_ITEMS", "sum"),
    )
    monthly["COVERAGE"] = monthly["WITH_ITEMS"] / monthly["TXN"]
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    ax.plot(monthly["MONTH"], monthly["COVERAGE"], color=GOLD, linewidth=2.4, marker="o")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    _style(ax, "Item-feed coverage by month (do not drop the missing headers)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
