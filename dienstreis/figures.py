"""Figures: itinerary map on health zones, reconstructed epidemic curve. Both check themselves."""
from __future__ import annotations

import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from . import data

warnings.filterwarnings("ignore", message=".*geographic CRS.*")
BLUE, RED = "#1f4e9e", "#b30000"
BINS = [(0, "#f5f2ec", "Geen bevestigde gevallen"), (1, "#fee8c8", "1 - 9"), (10, "#fdbb84", "10 - 49"),
        (50, "#ef6548", "50 - 199"), (200, "#990000", ">= 200")]
HALO = [pe.withStroke(linewidth=3, foreground="white")]


def _colour(n: int) -> str:
    c = BINS[0][1]
    for lo, col, _ in BINS:
        if n >= lo:
            c = col
    return c


def _fmt_d(d) -> str:
    return "" if d is None else f"{d.day} {['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'][d.month-1]}"


def _grouped(rs):
    """One label per distinct place, listing every period spent there."""
    out = {}
    for r in rs:
        k = (r.place, round(r.lon, 2), round(r.lat, 2))
        out.setdefault(k, []).append(r)
    labs = []
    for (place, lon, lat), grp in out.items():
        periods = []
        for r in grp:
            if r.start and r.end and r.start != r.end:
                periods.append(f"{_fmt_d(r.start)}-{_fmt_d(r.end)}")
            elif r.start:
                periods.append(_fmt_d(r.start) + (" (transit)" if r.transit_only else ""))
        labs.append((grp[0], place + ("\n" + "; ".join(periods) if periods else "")))
    return labs


def _extent(rs, zones, pad=1.6, min_span=6.0, near_km=450):
    """Frame the stops that matter epidemiologically; far stops (e.g. Kinshasa) only appear in the inset."""
    near = [r for r in rs if r.category in "ABCDE" or (r.nearest_active and r.nearest_active["km"] <= near_km)]
    use = near or rs
    xs, ys = [r.lon for r in use], [r.lat for r in use]
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    # keep a sensible landscape frame (width ~1.3 x height)
    w, h = max(x1 - x0, min_span), max(y1 - y0, min_span / 1.3)
    if w / h < 1.3:
        w = h * 1.3
    else:
        h = w / 1.3
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    far = [r for r in rs if not (x0 <= r.lon <= x1 and y0 <= r.lat <= y1)]
    return (x0, x1, y0, y1), far


def itinerary_map(rs, ob, title: str, subtitle: str, out: str, annotate_neighbours: bool = True) -> dict:
    zones = ob.zones.copy()
    zones["fc"] = zones.cases.map(_colour)
    countries = data.fetch_countries()
    prov = zones.dissolve(by="PROVINCE").reset_index()
    (x0, x1, y0, y1), far = _extent(rs, zones)

    fig, ax = plt.subplots(figsize=(12.5, 10), dpi=300)
    countries.plot(ax=ax, color="#eef3ee", edgecolor="#9aa89a", linewidth=0.7)
    zones.plot(ax=ax, color=zones.fc, edgecolor="#c9c4bb", linewidth=0.2)
    prov.plot(ax=ax, facecolor="none", edgecolor="#555555", linewidth=0.8)
    act = zones[zones.new14 > 0]
    act.plot(ax=ax, facecolor="none", edgecolor="#000000", linewidth=1.1, hatch="....")
    dest = zones[zones.Nom.isin({r.zone for r in rs if r.zone})]
    dest.plot(ax=ax, facecolor="none", edgecolor=BLUE, linewidth=2.4)

    texts = []
    inside = [r for r in rs if r not in far]
    ax.plot([r.lon for r in rs], [r.lat for r in rs], ls=(0, (4, 3)), color=BLUE, lw=2.2, zorder=6)
    for r, lab in _grouped(inside):
        ax.plot(r.lon, r.lat, marker="s", ms=9, mfc=BLUE, mec="white", mew=1.3, zorder=8)
        texts.append(ax.text(r.lon, r.lat, lab, fontsize=9.3, fontweight="bold", color=BLUE, zorder=9,
                             path_effects=HALO))
    # context: largest zones in view and active neighbours of destinations
    view = zones.cx[x0:x1, y0:y1]
    ctx = set(view.nlargest(4, "cases").Nom)
    if annotate_neighbours:
        for r in rs:
            ctx |= {n["zone"] for n in r.neighbours_active[:3]}
            if r.nearest_active and r.category not in "A":
                ctx.add(r.nearest_active["zone"])
    ctx -= {r.zone for r in rs}
    for _, z in zones[zones.Nom.isin(ctx) & (zones.cases > 0)].iterrows():
        c = z.geometry.representative_point()
        if x0 <= c.x <= x1 and y0 <= c.y <= y1:
            ax.plot(c.x, c.y, marker="o", ms=4, mfc="#1a1a1a", mec="white", mew=0.6, zorder=7)
            texts.append(ax.text(c.x, c.y, f"{z.Nom} ({z.cases})", fontsize=8.2, color="#1a1a1a", zorder=9,
                                 path_effects=HALO))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
    if all(r.category in "FX" for r in rs):   # trip far from the outbreak: say how far instead
        na = min((r.nearest_active for r in rs if r.nearest_active), key=lambda x: x["km"], default=None)
        if na:
            ax.text(0.02, 0.97, f"Geen bevestigde gevallen in het getoonde gebied.\nDichtstbijzijnde zone met recente gevallen: "
                    f"{na['zone']} ({na['province']}), circa " + f"{round(na['km'], -1):,.0f}".replace(",", " ") + " km",
                    transform=ax.transAxes, va="top", fontsize=9, color="#333",
                    bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#999", lw=0.8), zorder=12)
    try:
        from adjustText import adjust_text
        adjust_text(texts, ax=ax, expand=(1.4, 1.7), force_text=(0.6, 0.9), max_move=(40, 40),
                    arrowprops=dict(arrowstyle="-", color="#777", lw=0.6))
    except Exception:
        pass

    legend = [mpatches.Patch(fc=c, ec="#999", label=l) for _, c, l in reversed(BINS)] + [
        mpatches.Patch(fc="none", ec="#000", hatch="....", label="Nieuwe gevallen laatste 14 dagen"),
        mpatches.Patch(fc="none", ec=BLUE, lw=2.2, label="Gezondheidszone van een stop"),
        Line2D([0], [0], marker="s", color=BLUE, ls=(0, (4, 3)), mfc=BLUE, mec="white", ms=8, label="Reisschema")]
    inset_corner, legend_corner = _free_corners(inside, (x0, x1, y0, y1))
    leg = ax.legend(handles=legend, loc=legend_corner, fontsize=8.3, framealpha=0.96, edgecolor="#999",
                    title="Bevestigde BVD-gevallen per gezondheidszone", title_fontsize=8.8)

    # locator inset (whole DRC), shows far stops such as Kinshasa; placed in a corner without stops
    axi = ax.inset_axes(CORNERS[inset_corner], zorder=20)
    countries.plot(ax=axi, color="#f4f4f4", edgecolor="#bbbbbb", linewidth=0.3)
    prov.plot(ax=axi, color="#eeeeee", edgecolor="#999999", linewidth=0.3)
    zones[zones.cases > 0].plot(ax=axi, color="#ef6548", linewidth=0)
    axi.plot([r.lon for r in rs], [r.lat for r in rs], ls=(0, (3, 2)), color=BLUE, lw=1.0)
    placed = []
    for r, _ in _grouped(far):
        axi.plot(r.lon, r.lat, marker="s", ms=4.5, color=BLUE)
        if any(abs(r.lon - a) < 2.5 and abs(r.lat - b) < 1.5 for a, b in placed):
            continue   # neighbouring far stops share the first label
        placed.append((r.lon, r.lat))
        axi.text(r.lon + 0.6, r.lat - 0.4, r.place, fontsize=6.5, color=BLUE, fontweight="bold", va="top",
                 clip_on=True, path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    axi.add_patch(mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="#333", lw=0.8))
    b = prov.total_bounds
    axi.set_xlim(min(b[0], min(r.lon for r in rs)) - 1, max(b[2], max(r.lon for r in rs)) + 1)
    axi.set_ylim(min(b[1], min(r.lat for r in rs)) - 1, max(b[3], max(r.lat for r in rs)) + 1)
    axi.set_xticks([]); axi.set_yticks([]); axi.set_facecolor("white")

    ax.set_title(f"{title}\n{subtitle}", fontsize=11.2, pad=10)
    ax.text(0.0, -0.015,
             f"Onafhankelijke kaart. Gevallen per gezondheidszone: INSP/RDC situatierapporten, verwerkt door INRB-UMIE "
             f"(github.com/INRB-UMIE/Ebola_DRC_2026), data tot {ob.asof:%d-%m-%Y}. Zonegrenzen: INRB/GRID3.\n"
             "Landgrenzen: Natural Earth. Posities van stops benaderend; route tussen stops hemelsbreed, niet de werkelijke weg.",
             fontsize=7.1, color="#444444", transform=ax.transAxes, va="top")
    fig.canvas.draw()
    overlaps = _overlaps(texts, fig)
    clipped = _clipped(texts, fig, ax, [axi, leg])
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"path": out, "label_overlaps": overlaps, "labels_clipped": clipped, "extent": (x0, x1, y0, y1),
            "far_stops_in_inset": [r.place for r in far]}


CORNERS = {"lower left": [0.0, 0.0, 0.24, 0.26], "lower right": [0.76, 0.0, 0.24, 0.26],
           "upper left": [0.0, 0.74, 0.24, 0.26], "upper right": [0.76, 0.74, 0.24, 0.26]}


def _free_corners(stops, ext) -> tuple[str, str]:
    """Corner for the inset and for the legend: the two with the fewest stops (and stop labels) nearby."""
    x0, x1, y0, y1 = ext
    pts = [((r.lon - x0) / (x1 - x0), (r.lat - y0) / (y1 - y0)) for r in stops]

    def load(name):
        bx, by, bw, bh = CORNERS[name]
        m = 0.08   # labels sit to the right of and around a stop
        return sum(1 for px, py in pts if bx - m <= px <= bx + bw + m and by - m <= py <= by + bh + m)

    order = sorted(CORNERS, key=lambda c: (load(c), ["lower left", "lower right", "upper left", "upper right"].index(c)))
    return order[0], order[1]


def _clipped(texts, fig, ax, covers) -> int:
    """Labels that stick out of the map frame or disappear under the inset or the legend."""
    r = fig.canvas.get_renderer()
    frame = ax.get_window_extent(r)
    boxes = [c.get_window_extent(r) for c in covers if c is not None]
    n = 0
    for t in texts:
        b = t.get_window_extent(r)
        outside = b.x0 < frame.x0 or b.x1 > frame.x1 or b.y0 < frame.y0 or b.y1 > frame.y1
        if outside or any(b.overlaps(c) for c in boxes):
            n += 1
    return n


def _overlaps(texts, fig) -> int:
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in texts]
    return sum(1 for i in range(len(boxes)) for j in range(i + 1, len(boxes)) if boxes[i].overlaps(boxes[j]))


def epicurve(ob, out: str, ecdc: dict | None = None) -> dict:
    nat = ob.national.copy()
    nat["cases"] = nat.cases.cummax()
    nat["deaths"] = nat.deaths.ffill().cummax()
    wk = nat.resample("W-SUN").last().ffill()
    inc = wk.diff().clip(lower=0).iloc[1:]
    last_full = inc.index[-1] if nat.index[-1] >= inc.index[-1] else inc.index[-2]

    fig, (a, b) = plt.subplots(2, 1, figsize=(11, 8.6), dpi=300, sharex=True, gridspec_kw={"height_ratios": [1.1, 1]})
    a.plot(nat.index, nat.cases, color="#333333", lw=2, label="Bevestigde gevallen (cumulatief)")
    a.plot(nat.index, nat.deaths, color="#999999", lw=2, label="Bevestigde overlijdens (cumulatief)")
    a.fill_between(nat.index, nat.deaths, color="#999999", alpha=0.12)
    last = nat.dropna(subset=["cases"]).iloc[-1]
    cfr = 100 * last.deaths / last.cases
    a.annotate(f"{int(last.cases):,} gevallen / {int(last.deaths):,} overlijdens\nCFR {cfr:.1f}% ({nat.index[-1]:%d-%m})".replace(",", " "),
               xy=(nat.index[-1], last.cases), xytext=(0.52, 0.9), textcoords="axes fraction", fontsize=9,
               arrowprops=dict(arrowstyle="->", color="#666", lw=1))
    a.set_ylabel("Cumulatief", fontweight="bold"); a.legend(loc="upper left", frameon=False, fontsize=9)
    a.grid(axis="y", color="#e0e0e0"); a.set_axisbelow(True)
    a.text(-0.06, 1.03, "A", transform=a.transAxes, fontsize=16, fontweight="bold")
    b.bar(inc.index - pd.Timedelta(days=6), inc.cases, width=6.3, align="edge", color="#666666", label="Gevallen per week")
    b.bar(inc.index - pd.Timedelta(days=6), inc.deaths, width=6.3, align="edge", color=RED, alpha=0.85, label="Overlijdens per week")
    if nat.index[-1] < inc.index[-1]:
        b.bar(inc.index[-1] - pd.Timedelta(days=6), inc.cases.iloc[-1], width=6.3, align="edge", fill=False,
              hatch="///", edgecolor="#333", lw=0)
        b.text(inc.index[-1] - pd.Timedelta(days=3), inc.cases.iloc[-1], "onvolledige\nweek", ha="center", va="bottom", fontsize=7)
    b.set_ylabel("Nieuw per week (ma-zo)", fontweight="bold"); b.legend(loc="upper left", frameon=False, fontsize=9)
    b.grid(axis="y", color="#e0e0e0"); b.set_axisbelow(True)
    b.text(-0.06, 1.03, "B", transform=b.transAxes, fontsize=16, fontweight="bold")
    b.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); b.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
    fig.suptitle(f"Ebola (Bundibugyo-virus), DRC: epidemiecurve uit officiële cumulatieve cijfers, tot {ob.asof:%d-%m-%Y}", fontsize=12.5)
    src = "INSP/RDC nationale cumulatieve reeks via INRB-UMIE; per rapportdatum, niet per symptoomdatum."
    if ecdc and ecdc.get("ok"):
        src += f" ECDC-controle: {ecdc['cases']:,} gevallen (data tot {ecdc['data_until']}).".replace(",", " ")
    fig.text(0.08, 0.01, src, fontsize=7.4, color="#444")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)
    recent = inc.loc[:last_full].tail(4)
    return {"path": out, "weekly_cases_last4_full_weeks": {f"{d:%d-%m}": int(v) for d, v in recent.cases.items()},
            "last_total": int(last.cases), "last_deaths": int(last.deaths), "cfr": round(cfr, 1)}
