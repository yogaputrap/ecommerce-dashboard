"""Dashboard analisis E-Commerce Public Dataset (Olist) dengan Streamlit.

Jalankan dari folder utama proyek:
    streamlit run dashboard/dashboard.py
"""
import os
from datetime import date

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="🛒", layout="wide")

# ---------------------------------------------------------------------------
# Gaya visualisasi (konsisten dengan notebook)
# ---------------------------------------------------------------------------
ACCENT, GREY, ALERT = "#1f6f8b", "#c5cbd1", "#d1495b"
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.labelsize": 10,
})

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_data.csv")
PERIOD_START, PERIOD_END = date(2017, 1, 1), date(2018, 8, 31)

DELAY_LABELS = ["Tepat waktu / lebih cepat", "Terlambat 1-3 hari", "Terlambat 4-7 hari", "Terlambat > 7 hari"]
SEGMENT_ORDER = ["Champions (repeat, aktif)", "Repeat - Dormant", "New High Spender",
                 "Pelanggan Baru", "Lapsed High Value", "Lapsed (satu kali beli, lama pergi)"]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["purchase_date"])
    df["purchase_month"] = df["purchase_date"].dt.to_period("M").astype(str)
    return df


def brl(x):
    return f"R$ {x:,.0f}"


def order_level(df):
    """Satu baris = satu pesanan (data asli berada di tingkat item pesanan)."""
    return df.drop_duplicates("order_id").copy()


def compute_rfm(df, snapshot_date):
    rfm = (df.groupby("customer_unique_id")
           .agg(last_purchase=("purchase_date", "max"),
                frequency=("order_id", "nunique"),
                monetary=("price", "sum"))
           .reset_index())
    rfm["recency"] = (snapshot_date - rfm["last_purchase"].dt.normalize()).dt.days
    rfm["monetary_tier"] = pd.qcut(rfm["monetary"].rank(method="first"), q=[0, 0.5, 0.9, 1],
                                   labels=["Rendah", "Menengah", "Tinggi"])
    high = rfm["monetary_tier"] == "Tinggi"
    conditions = [
        (rfm["frequency"] >= 2) & (rfm["recency"] <= 180),
        (rfm["frequency"] >= 2) & (rfm["recency"] > 180),
        (rfm["frequency"] == 1) & (rfm["recency"] <= 180) & high,
        (rfm["frequency"] == 1) & (rfm["recency"] <= 180),
        (rfm["frequency"] == 1) & (rfm["recency"] > 180) & high,
    ]
    rfm["segment"] = np.select(conditions, SEGMENT_ORDER[:5], default=SEGMENT_ORDER[5])
    return rfm


# ---------------------------------------------------------------------------
# Grafik
# ---------------------------------------------------------------------------
def chart_categories(cat, metric, n):
    """Top-N dan bottom-N kategori berdasarkan metrik terpilih."""
    cat = cat.sort_values(metric, ascending=False)
    n = min(n, len(cat) // 2) if len(cat) >= 2 else len(cat)
    top = cat.head(n).iloc[::-1]
    bottom = cat.tail(n).iloc[::-1]
    unit = "R$" if metric == "revenue" else "item"
    fmt = (lambda v: f"R$ {v:,.0f}") if metric == "revenue" else (lambda v: f"{v:,.0f}")

    fig, axes = plt.subplots(1, 2, figsize=(14, max(4, 0.45 * n + 1.8)))
    colors = [GREY] * max(len(top) - 3, 0) + [ACCENT] * min(3, len(top))
    bars = axes[0].barh(top.index.str.replace("_", " "), top[metric], color=colors)
    axes[0].bar_label(bars, labels=[fmt(v) for v in top[metric]], padding=4, fontsize=9)
    axes[0].set_title(f"{n} kategori teratas", loc="left")
    axes[0].set_xlim(0, max(top[metric].max(), 1) * 1.3)

    bars = axes[1].barh(bottom.index.str.replace("_", " "), bottom[metric], color=ALERT, alpha=0.85)
    axes[1].bar_label(bars, labels=[fmt(v) for v in bottom[metric]], padding=4, fontsize=9)
    axes[1].set_title(f"{n} kategori terbawah", loc="left")
    axes[1].set_xlim(0, max(bottom[metric].max(), 1) * 1.3)
    for ax, part in zip(axes, [top, bottom]):
        ax.set_xlabel("Total revenue (R$)" if metric == "revenue" else "Jumlah item terjual")
        if part[metric].max() >= 100_000:   # angka besar diringkas agar label sumbu tidak bertumpuk
            ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x / 1000:,.0f}K"))
        else:
            ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.tick_params(axis="y", length=0)
    plt.tight_layout()
    return fig


def chart_monthly(monthly):
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.2, 1]})
    x = np.arange(len(monthly))
    labels = list(monthly.index)

    axes[0].plot(x, monthly["orders"], color=ACCENT, marker="o", linewidth=2)
    axes[0].set_ylabel("Jumlah pesanan")
    axes[0].set_title("Jumlah pesanan bulanan", loc="left")

    axes[1].plot(x, monthly["revenue"] / 1000, color=ACCENT, marker="o", linewidth=2)
    axes[1].set_ylabel("Revenue (R$ ribu)")
    axes[1].set_title("Revenue bulanan", loc="left")
    peak = monthly["revenue"].idxmax()
    i_peak = labels.index(peak)
    axes[1].annotate(f"Puncak {peak}\n{brl(monthly.loc[peak, 'revenue'])}",
                     xy=(i_peak, monthly.loc[peak, "revenue"] / 1000),
                     xytext=(max(i_peak - 4, 0), monthly["revenue"].max() / 1000 * 0.55),
                     arrowprops=dict(arrowstyle="->", color="black"), fontsize=10)
    for ax in axes[:2]:
        ax.set_ylim(0, None)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.axvline(i_peak, color=GREY, linestyle="--", linewidth=1, zorder=0)

    mom = monthly["revenue_mom_pct"].iloc[1:]
    if len(mom):
        bars = axes[2].bar(x[1:], mom, color=[ACCENT if v >= 0 else ALERT for v in mom])
        axes[2].bar_label(bars, labels=[f"{v:+.0f}%" for v in mom], fontsize=8, padding=2)
        lo, hi = min(mom.min(), 0), max(mom.max(), 0)
        axes[2].set_ylim(lo - 0.15 * (hi - lo + 1), hi + 0.15 * (hi - lo + 1))
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_ylabel("Pertumbuhan MoM (%)")
    axes[2].set_title("Pertumbuhan revenue dibanding bulan sebelumnya", loc="left")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=45, ha="right")
    plt.tight_layout()
    return fig


def chart_delivery(delay_stats, state_rank, late_share, n_state=10):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1, 1.1]})

    ds = delay_stats.dropna(subset=["avg_review"])
    colors = [ACCENT if lab == DELAY_LABELS[0] else ALERT for lab in ds.index]
    bars = axes[0].bar([lab.replace(" ", "\n", 1) for lab in ds.index], ds["avg_review"], color=colors)
    axes[0].bar_label(bars, labels=[f"{v:.2f}" for v in ds["avg_review"]], padding=3, fontsize=11, fontweight="bold")
    axes[0].set_ylim(0, 5)
    axes[0].set_ylabel("Rata-rata review score (1-5)")
    axes[0].set_title("Review score menurut ketepatan pengiriman", loc="left")

    top = state_rank.head(n_state).iloc[::-1]
    if len(top):
        colors = [GREY] * max(len(top) - 3, 0) + [ALERT] * min(3, len(top))
        bars = axes[1].barh(top.index, top["late_pct"], color=colors)
        axes[1].bar_label(bars, labels=[f"{v:.1f}%" for v in top["late_pct"]], padding=3, fontsize=9)
        axes[1].axvline(late_share, color="black", linestyle="--", linewidth=1)
        axes[1].set_ylim(-0.6, len(top) + 0.2)
        axes[1].text(late_share + 0.3, len(top) - 0.25, f"rata-rata {late_share:.1f}%", fontsize=9, va="center")
        axes[1].set_xlim(0, max(top["late_pct"].max(), late_share) * 1.2)
    axes[1].set_xlabel("% pesanan tiba terlambat")
    axes[1].set_title("State dengan keterlambatan tertinggi", loc="left")
    axes[1].tick_params(axis="y", length=0)
    plt.tight_layout()
    return fig


def chart_map(orders, state_stats):
    fig, ax = plt.subplots(figsize=(8, 8))
    bg = orders.dropna(subset=["customer_lat"])
    bg = bg.sample(min(20000, len(bg)), random_state=42)
    ax.scatter(bg["customer_lng"], bg["customer_lat"], s=2, color="#e3e6e9", zorder=1)
    sc = ax.scatter(state_stats["lng"], state_stats["lat"], s=state_stats["orders"] / 40 + 25,
                    c=state_stats["late_pct"], cmap="Reds", edgecolor="black", linewidth=0.6,
                    alpha=0.9, zorder=2, vmin=0)
    cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("% pesanan terlambat")
    labelled = set(state_stats.nlargest(4, "orders").index) | set(state_stats.nlargest(5, "late_pct").index)
    for code in labelled:
        r = state_stats.loc[code]
        ax.annotate(code, (r["lng"], r["lat"]), xytext=(6, 6), textcoords="offset points", fontsize=10, fontweight="bold")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Peta pelanggan: ukuran = jumlah pesanan, warna = % terlambat", loc="left")
    ax.set_aspect("equal")
    plt.tight_layout()
    return fig


def chart_rfm(segment_stats):
    seg = segment_stats.iloc[::-1]
    labels = [s.replace(" (", "\n(") for s in seg.index]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, col, title, xlabel in [
        (axes[0], "customer_pct", "Sebaran pelanggan per segmen", "% pelanggan unik"),
        (axes[1], "revenue_pct", "Kontribusi revenue per segmen", "% total revenue"),
    ]:
        colors = [ACCENT if s == seg[col].idxmax() else GREY for s in seg.index]
        bars = ax.barh(labels, seg[col], color=colors)
        if col == "customer_pct":
            texts = [f"{v:.1f}% ({c:,.0f})" for v, c in zip(seg[col], seg["customers"])]
        else:
            texts = [f"{v:.1f}%" for v in seg[col]]
        ax.bar_label(bars, labels=texts, padding=4, fontsize=9)
        ax.set_xlim(0, max(seg[col].max(), 1) * 1.3)
        ax.set_title(title, loc="left")
        ax.set_xlabel(xlabel)
        ax.tick_params(axis="y", length=0)
    plt.tight_layout()
    return fig


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------
st.title("🛒 Dashboard Analisis E-Commerce Olist")
st.caption("Pesanan berstatus *delivered*, Januari 2017 – Agustus 2018. "
           "Revenue = jumlah harga produk (tanpa ongkos kirim), dalam Real Brasil (R$).")

if not os.path.exists(DATA_PATH):
    st.error(f"Berkas data tidak ditemukan: {DATA_PATH}. Jalankan notebook.ipynb terlebih dahulu untuk membuat main_data.csv.")
    st.stop()

data = load_data()

# ---- Sidebar: filter ----
st.sidebar.header("Filter")
date_range = st.sidebar.date_input("Rentang tanggal pembelian", value=(PERIOD_START, PERIOD_END),
                                   min_value=PERIOD_START, max_value=PERIOD_END)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pilih tanggal awal dan tanggal akhir pada filter di sisi kiri.")
    st.stop()
start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

all_states = sorted(data["customer_state"].unique())
chosen_states = st.sidebar.multiselect("State pelanggan", options=all_states, default=all_states)
top_n = st.sidebar.slider("Jumlah kategori ditampilkan (Top/Bottom N)", min_value=5, max_value=15, value=10)
min_orders = st.sidebar.slider("Minimum pesanan per state (untuk persentase terlambat)",
                               min_value=50, max_value=1000, value=300, step=50)

df = data[(data["purchase_date"] >= start_date)
          & (data["purchase_date"] < end_date + pd.Timedelta(days=1))
          & (data["customer_state"].isin(chosen_states))].copy()
if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau state.")
    st.stop()
orders = order_level(df)

# ---- KPI ----
total_orders = orders["order_id"].nunique()
total_revenue = df["price"].sum()
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total pesanan", f"{total_orders:,}")
k2.metric("Total revenue", brl(total_revenue))
k3.metric("Rata-rata nilai pesanan", brl(total_revenue / total_orders))
k4.metric("Rata-rata review score", f"{orders['review_score'].mean():.2f} / 5")
k5.metric("Pesanan terlambat", f"{orders['is_late'].mean() * 100:.1f}%")

tab1, tab2, tab3, tab4 = st.tabs(["📦 Kategori Produk", "📈 Tren Bulanan", "🚚 Pengiriman & Review", "👥 Segmentasi RFM"])

# ---- Tab 1: kategori ----
with tab1:
    st.subheader("Kategori produk mana yang paling dan paling kurang menyumbang?")
    metric_label = st.radio("Urutkan berdasarkan", ["Revenue", "Jumlah item terjual"], horizontal=True)
    metric = "revenue" if metric_label == "Revenue" else "items_sold"
    cat = (df[df["product_category"] != "unknown"].groupby("product_category")
           .agg(revenue=("price", "sum"), items_sold=("order_id", "count")))
    cat["share_pct"] = cat["revenue"] / total_revenue * 100
    if len(cat) < 2:
        st.info("Data kategori tidak cukup untuk filter yang dipilih.")
    else:
        show(chart_categories(cat, metric, top_n))
        ranked = cat.sort_values(metric, ascending=False)
        top_share = ranked.head(top_n)["revenue"].sum() / total_revenue * 100
        st.markdown(f"**Insight:** {top_n} kategori teratas menurut {metric_label.lower()} menyumbang "
                    f"**{top_share:.1f}%** dari total revenue pada filter ini. "
                    f"Kategori nomor satu adalah `{ranked.index[0]}`.")
        with st.expander("Lihat tabel lengkap"):
            st.dataframe(ranked.round(2))

# ---- Tab 2: tren bulanan ----
with tab2:
    st.subheader("Bagaimana tren pesanan dan revenue bulanan?")
    monthly = (df.groupby("purchase_month")
               .agg(orders=("order_id", "nunique"), revenue=("price", "sum")))
    monthly["revenue_mom_pct"] = monthly["revenue"].pct_change() * 100
    if len(monthly) < 2:
        st.info("Pilih rentang tanggal minimal dua bulan untuk melihat tren.")
    else:
        show(chart_monthly(monthly))
        peak = monthly["revenue"].idxmax()
        st.markdown(f"**Insight:** revenue bulanan tertinggi pada rentang ini terjadi pada **{peak}** "
                    f"({brl(monthly.loc[peak, 'revenue'])}; {monthly.loc[peak, 'orders']:,} pesanan).")
        st.caption("Catatan: bulan pertama/terakhir yang tidak terpilih penuh akan tampak lebih rendah karena hanya berisi sebagian hari.")
        with st.expander("Lihat tabel bulanan"):
            st.dataframe(monthly.round(1))

# ---- Tab 3: pengiriman & review ----
with tab3:
    st.subheader("Seberapa besar keterlambatan memengaruhi review, dan di mana paling sering terjadi?")
    orders["delay_group"] = pd.cut(orders["delay_days"], bins=[-np.inf, 0, 3, 7, np.inf], labels=DELAY_LABELS)
    delay_stats = (orders.groupby("delay_group", observed=False)
                   .agg(orders=("order_id", "size"), avg_review=("review_score", "mean"))
                   .reindex(DELAY_LABELS))
    state_stats = (orders.groupby("customer_state")
                   .agg(orders=("order_id", "size"), late_pct=("is_late", "mean"), avg_review=("review_score", "mean"),
                        lat=("customer_lat", "mean"), lng=("customer_lng", "mean")))
    state_stats["late_pct"] = state_stats["late_pct"] * 100
    state_rank = state_stats[state_stats["orders"] >= min_orders].sort_values("late_pct", ascending=False)
    late_share = orders["is_late"].mean() * 100

    show(chart_delivery(delay_stats, state_rank, late_share))
    on_time = orders.loc[~orders["is_late"], "review_score"].mean()
    late = orders.loc[orders["is_late"], "review_score"].mean()
    if pd.notna(on_time) and pd.notna(late):
        st.markdown(f"**Insight:** review rata-rata pesanan tepat waktu **{on_time:.2f}** vs terlambat **{late:.2f}** "
                    f"(selisih **{on_time - late:.2f} poin**). Secara keseluruhan {late_share:.1f}% pesanan terlambat.")
    if state_rank.empty:
        st.info("Tidak ada state yang memenuhi minimum pesanan pada filter ini. Turunkan nilai minimum di sidebar.")

    st.subheader("Peta sebaran pelanggan dan keterlambatan")
    map_data = state_stats.dropna(subset=["lat", "lng"])
    if map_data.empty:
        st.info("Koordinat tidak tersedia untuk filter ini.")
    else:
        show(chart_map(orders, map_data))
    with st.expander("Lihat tabel per state"):
        st.dataframe(state_stats.drop(columns=["lat", "lng"]).sort_values("late_pct", ascending=False).round(2))

# ---- Tab 4: RFM ----
with tab4:
    st.subheader("Bagaimana sebaran pelanggan menurut segmen RFM?")
    snapshot_date = end_date + pd.Timedelta(days=1)
    rfm = compute_rfm(df, snapshot_date) if df["customer_unique_id"].nunique() >= 20 else None
    if rfm is None:
        st.info("Jumlah pelanggan terlalu sedikit untuk segmentasi RFM pada filter ini.")
    else:
        segment_stats = (rfm.groupby("segment")
                         .agg(customers=("customer_unique_id", "count"), revenue=("monetary", "sum"),
                              avg_recency=("recency", "mean"), avg_monetary=("monetary", "mean"))
                         .reindex(SEGMENT_ORDER).fillna(0))
        segment_stats["customer_pct"] = segment_stats["customers"] / segment_stats["customers"].sum() * 100
        segment_stats["revenue_pct"] = segment_stats["revenue"] / segment_stats["revenue"].sum() * 100
        st.caption(f"Snapshot date: {snapshot_date.date()} (sehari setelah akhir rentang tanggal terpilih).")
        show(chart_rfm(segment_stats))
        repeat_share = (rfm["frequency"] >= 2).mean() * 100
        top_seg = segment_stats["revenue_pct"].idxmax()
        st.markdown(f"**Insight:** hanya **{repeat_share:.1f}%** pelanggan yang membeli lebih dari satu kali. "
                    f"Segmen penyumbang revenue terbesar adalah **{top_seg}** "
                    f"({segment_stats.loc[top_seg, 'revenue_pct']:.1f}% revenue).")
        with st.expander("Definisi segmen dan tabel"):
            st.markdown(
                "- **Champions**: beli 2+ kali, terakhir beli ≤ 180 hari\n"
                "- **Repeat - Dormant**: beli 2+ kali, terakhir beli > 180 hari\n"
                "- **New High Spender**: beli 1 kali, ≤ 180 hari, belanja termasuk 10% teratas\n"
                "- **Pelanggan Baru**: beli 1 kali, ≤ 180 hari\n"
                "- **Lapsed High Value**: beli 1 kali, > 180 hari, belanja termasuk 10% teratas\n"
                "- **Lapsed**: beli 1 kali, > 180 hari, belanja di bawah 10% teratas"
            )
            st.dataframe(segment_stats.round(1))

st.caption("Sumber data: Brazilian E-Commerce Public Dataset by Olist (Kaggle). Proses analisis lengkap ada di notebook.ipynb.")
