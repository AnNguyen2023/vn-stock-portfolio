import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# df cần có: time (datetime), value (float), volume (float/int, optional)
# Ví dụ demo: df = pd.read_csv("vnindex_intraday.csv", parse_dates=["time"])

def plot_vnindex_intraday(df, ref_level=None):
    df = df.sort_values("time").copy()

    # Style nền tối
    plt.rcParams.update({
        "figure.facecolor": "#0b1020",
        "axes.facecolor": "#0b1020",
        "axes.edgecolor": "#2a2f3a",
        "axes.labelcolor": "#c9d1d9",
        "xtick.color": "#c9d1d9",
        "ytick.color": "#c9d1d9",
        "grid.color": "#2a2f3a",
        "text.color": "#c9d1d9",
    })

    fig = plt.figure(figsize=(8, 4.5))
    gs = fig.add_gridspec(5, 1, hspace=0.05)
    ax_price = fig.add_subplot(gs[:4, 0])
    ax_vol = fig.add_subplot(gs[4, 0], sharex=ax_price)

    # Price line
    ax_price.plot(df["time"], df["value"], linewidth=2)

    # Ref dashed line (ví dụ 1867.9)
    if ref_level is not None:
        ax_price.axhline(ref_level, linestyle="--", linewidth=1)
        ax_price.text(df["time"].iloc[len(df)//2], ref_level, f"{ref_level}",
                      va="bottom", ha="center")

    # Grid + trục giờ dạng "09h 10h ..."
    ax_price.grid(True, which="major")
    ax_price.xaxis.set_major_locator(mdates.HourLocator(byhour=range(9, 16), interval=1))
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Hh"))
    plt.setp(ax_price.get_xticklabels(), visible=False)

    # Volume (nếu có)
    if "volume" in df.columns:
        ax_vol.fill_between(df["time"], df["volume"], step="pre", alpha=0.6)
        ax_vol.grid(False)
        ax_vol.set_yticks([])

    # Viền
    for ax in (ax_price, ax_vol):
        for spine in ax.spines.values():
            spine.set_linewidth(1)

    ax_price.set_ylabel("")
    ax_vol.set_xlabel("")
    plt.show()

# --- dùng ---
# plot_vnindex_intraday(df, ref_level=1867.9)
