#!/usr/bin/env python3
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, HRFlowable, KeepTogether)

NAVY  = colors.HexColor("#0f2f4a")
TEAL  = colors.HexColor("#0b7285")
LIGHT = colors.HexColor("#eef2f5")
GRAY  = colors.HexColor("#5b6b78")
RULE  = colors.HexColor("#c9d3da")
GREEN = colors.HexColor("#2f9e44")
AMBER = colors.HexColor("#f08c00")
RED   = colors.HexColor("#e03131")

OUT   = "Odin_Catalyst_Surge_Study.pdf"
CHART = "surge_chart.png"
TODAY = dt.date.today().strftime("%B %-d, %Y")

# ---------------- data (final study results) ----------------
p3 = [  # early vol/ADV, events, %closed up, %held 1h, %new high after 1h, close-in-range
    ("< 0.5x", "1,072", "96.0%", "95.8%", "95.1%", "0.77"),
    ("0.5-1x", "325",   "97.2%", "93.8%", "93.5%", "0.76"),
    ("1-2x",   "369",   "93.5%", "87.5%", "87.8%", "0.74"),
    ("2-5x",   "360",   "92.8%", "81.7%", "80.6%", "0.72"),
    ("5-10x",  "210",   "89.0%", "75.2%", "75.2%", "0.66"),
    ("10x +",  "644",   "68.5%", "62.7%", "56.4%", "0.50"),
]
p4v = [  # first-hour vol/ADV, events, %continued, avg further gain
    ("< 1x",  "1,397", "95.0%", "+29.0%"),
    ("1-2x",  "369",   "87.3%", "+15.6%"),
    ("2-5x",  "360",   "81.1%", "+12.9%"),
    ("5-10x", "210",   "75.2%", "+13.2%"),
    ("10x +", "644",   "61.8%", "+12.0%"),
]
p4m = [  # first-hour move, events, %continued, avg further gain
    ("< 10%",   "1,679", "86.5%", "+24.1%"),
    ("10-25%",  "899",   "88.9%", "+17.2%"),
    ("25-50%",  "305",   "68.2%", "+14.2%"),
    ("50% +",   "97",    "39.2%", "+12.7%"),
]

# ---------------- chart ----------------
def make_chart():
    labels = ["<1x", "1-2x", "2-5x", "5-10x", "10x+"]
    cont   = [95.0, 87.3, 81.1, 75.2, 61.8]
    fwd    = [29.0, 15.6, 12.9, 13.2, 12.0]
    bar_c  = ["#2f9e44", "#66a80f", "#f08c00", "#e8590c", "#e03131"]
    fig, ax = plt.subplots(figsize=(7.1, 3.15), dpi=150)
    bars = ax.bar(labels, cont, color=bar_c, width=0.62, zorder=3)
    ax.set_ylim(0, 108)
    ax.set_ylabel("% that continued higher into the close", fontsize=8.5)
    ax.set_xlabel("First-hour volume vs. the stock's normal daily volume (ADV)", fontsize=8.5)
    ax.set_title("Lower early volume -> higher continuation", fontsize=10.5, fontweight="bold", color="#0f2f4a", pad=8)
    ax.tick_params(labelsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#dde3e8", linewidth=0.6, zorder=0)
    for b, c, f in zip(bars, cont, fwd):
        ax.text(b.get_x()+b.get_width()/2, c+2.0, f"{c:.0f}%", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#0f2f4a")
        ax.text(b.get_x()+b.get_width()/2, c/2, f"avg\n{f:+.0f}%", ha="center", va="center",
                fontsize=7.5, color="white", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHART, bbox_inches="tight")
    plt.close(fig)

make_chart()

# ---------------- styles ----------------
ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5,
                      leading=13.5, textColor=colors.HexColor("#20303c"), spaceAfter=6)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
                    textColor=NAVY, spaceBefore=10, spaceAfter=5)
small = ParagraphStyle("small", parent=body, fontSize=8, textColor=GRAY, leading=11)
white_title = ParagraphStyle("wt", parent=body, fontName="Helvetica-Bold", fontSize=19,
                             textColor=colors.white, leading=22)
white_sub = ParagraphStyle("ws", parent=body, fontName="Helvetica", fontSize=10.5,
                           textColor=colors.HexColor("#c7dbe8"), leading=14, spaceBefore=2)
callout = ParagraphStyle("callout", parent=body, fontSize=10.5, leading=15, textColor=NAVY, spaceAfter=0)
capt = ParagraphStyle("capt", parent=small, alignment=TA_LEFT, spaceBefore=2)

def cell(txt, bold=False, color=None, size=9, align=TA_CENTER):
    st = ParagraphStyle("c", parent=body, fontSize=size, leading=12,
                        alignment=align, fontName="Helvetica-Bold" if bold else "Helvetica",
                        textColor=color or colors.HexColor("#20303c"))
    return Paragraph(txt, st)

def data_table(header, rows, widths, highlight_last=False):
    head = [cell(h, bold=True, color=colors.white, size=8.5, align=(TA_LEFT if i == 0 else TA_CENTER))
            for i, h in enumerate(header)]
    data = [head]
    for r in rows:
        data.append([cell(c, align=(TA_LEFT if i == 0 else TA_CENTER), bold=(i == 0)) for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, TEAL),
        ("GRID", (0, 1), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]
    if highlight_last:
        style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff0f0")))
    t.setStyle(TableStyle(style))
    return t

def box(flowables, bg, border):
    inner = Table([[flowables]], colWidths=[7.0*inch])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, border),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return inner

# ---------------- story ----------------
story = []
title_tbl = Table([[Paragraph("Small-Cap Surge Continuation Study", white_title)],
                   [Paragraph("Does early-session volume tell you whether a 30%+ mover keeps running?", white_sub)]],
                  colWidths=[7.0*inch])
title_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("TOPPADDING", (0, 0), (-1, 0), 14), ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
    ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
]))
story += [title_tbl, Spacer(1, 4),
          Paragraph(f"Odin Catalyst LLC &nbsp;&middot;&nbsp; Momentum / UOA Radar research &nbsp;&middot;&nbsp; {TODAY} "
                    f"&nbsp;&middot;&nbsp; 2,980 events analyzed &nbsp;&middot;&nbsp; 2-year lookback", small),
          Spacer(1, 8)]

story += [Paragraph("Executive summary", h2),
          Paragraph("We examined every small- and micro-cap U.S. stock that jumped 30% or more in a single day "
                    "over the past two years &mdash; <b>3,122 surges</b> &mdash; and reconstructed how each traded intraday, "
                    "30 minutes at a time, against its own normal volume. The question: does the volume behind a "
                    "surge tell you whether it keeps trending up or fades?", body),
          Paragraph("The answer is counterintuitive and consistent: <b>heavier early volume predicts less "
                    "continuation, not more.</b> Quiet, orderly surges tend to grind higher and close near their "
                    "highs; explosive, high-volume blow-offs tend to spike early and fade. The cleanest &lsquo;ride it&rsquo; "
                    "setups are moderate moves on moderate volume &mdash; not the loudest names on the tape.", body)]

story += [box([Paragraph("Key finding", ParagraphStyle("kf", parent=callout, fontName="Helvetica-Bold",
                                                        fontSize=9, textColor=TEAL, spaceAfter=3)),
               Paragraph("When first-hour volume was under ~1&times; the stock&rsquo;s normal daily volume, the surge "
                         "continued higher into the close <b>95%</b> of the time (avg <b>+29%</b> further). When "
                         "first-hour volume topped <b>10&times;</b> normal, continuation fell to <b>62%</b> (avg +12%). "
                         "More volume meant more exhaustion risk.", callout)], LIGHT, TEAL),
          Spacer(1, 10)]

story += [Paragraph("What we tested", h2),
          Paragraph("<b>Universe:</b> 3,257 currently-listed U.S. small/micro-caps (market cap &le; $2B, price &ge; $0.50, "
                    "non-ETF; NASDAQ / NYSE / AMEX).", body),
          Paragraph("<b>Event:</b> a &ge;30% single-day gain (close vs. prior close). 3,122 events found; 2,980 had "
                    "complete intraday + volume history and were analyzed.", body),
          Paragraph("<b>Data:</b> end-of-day and 30-minute intraday bars (price and volume) from institutional "
                    "market-data APIs.", body),
          Paragraph("<b>&lsquo;Relative volume&rsquo;:</b> each surge&rsquo;s volume is measured against that stock&rsquo;s own trailing "
                    "20-day average daily volume (ADV) as of the surge &mdash; the same read a live screen sees at the open.", body),
          Paragraph("<b>Continuation:</b> measured two ways &mdash; <i>same-day</i> (did it hold and extend after the first "
                    "hour) and <i>forward</i> (from the ~10:30 a.m. ET mark to the close).", body)]

story += [Paragraph("Results &mdash; same-day behavior by early volume", h2),
          data_table(["Early volume (vs ADV)", "Events", "Closed up", "Held 1st-hr gain", "New high after 1st hr", "Close-in-range*"],
                     p3, [1.55*inch, 0.7*inch, 0.85*inch, 1.15*inch, 1.35*inch, 1.0*inch], highlight_last=True),
          Paragraph("*Close-in-range: where the stock closed within its daily high&ndash;low (1.0 = at the high, 0 = at the low). "
                    "Correlation between early volume and closing strength: &minus;0.115.", capt),
          Spacer(1, 8),
          Image(CHART, width=7.0*inch, height=3.10*inch),
          Spacer(1, 10)]

story += [Paragraph("Results &mdash; forward test from the 10:30 a.m. decision point", h2),
          Paragraph("If you entered at the first-hour mark on what you could actually see (the move so far and the "
                    "volume behind it), did price continue up to the close?", body),
          Paragraph("<b>By first-hour volume</b>", ParagraphStyle("lbl", parent=body, spaceAfter=3, textColor=NAVY)),
          data_table(["First-hour volume (vs ADV)", "Events", "Continued to close", "Avg further gain"],
                     p4v, [2.3*inch, 1.0*inch, 1.9*inch, 1.4*inch], highlight_last=True),
          Spacer(1, 6),
          Paragraph("<b>By size of the first-hour move</b>", ParagraphStyle("lbl2", parent=body, spaceAfter=3, textColor=NAVY)),
          data_table(["First-hour move", "Events", "Continued to close", "Avg further gain"],
                     p4m, [2.3*inch, 1.0*inch, 1.9*inch, 1.4*inch], highlight_last=True),
          Spacer(1, 8),
          Paragraph("Read together: the tape you want is a <b>controlled advance</b> &mdash; a moderate opening move that "
                    "keeps making higher highs on ordinary volume. A first hour already up 50%+ or trading 10&times;+ its "
                    "normal volume is far more likely to be a climax than a launchpad (continuation drops to ~39% and "
                    "~62% respectively).", body)]

risk = [Paragraph("Risk &amp; limitations", ParagraphStyle("rk", parent=callout, fontName="Helvetica-Bold",
                                                            fontSize=9, textColor=RED, spaceAfter=3)),
        Paragraph("<b>Survivorship.</b> The universe is currently-listed names, so surges from since-delisted tickers "
                  "(many that pumped and died) are excluded &mdash; real-world continuation is likely <i>lower</i> than shown.", small),
        Paragraph("<b>Selection.</b> Events were chosen because they <i>ended</i> the day &ge;30% up, which favors winners; "
                  "the forward test still inherits this bias. The unbiased version requires logging first-hour movers "
                  "live, going forward (planned).", small),
        Paragraph("<b>Tradeability.</b> Micro-cap spreads, slippage, and trading halts can erase a statistical edge; "
                  "verify liquidity name by name.", small),
        Paragraph("<b>Base rates, not guarantees.</b> News, float, and market regime dominate any single event.", small)]
story += [Spacer(1, 4), box(risk, colors.HexColor("#fff5f5"), RED), Spacer(1, 8),
          Paragraph("This document is for informational and educational purposes only. It is not investment advice, an "
                    "offer, or a solicitation to buy or sell any security. Past behavior does not guarantee future "
                    "results. &copy; Odin Catalyst LLC.", small)]

# ---------------- footer ----------------
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE); canvas.setLineWidth(0.5)
    canvas.line(0.7*inch, 0.62*inch, letter[0]-0.7*inch, 0.62*inch)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(GRAY)
    canvas.drawString(0.7*inch, 0.46*inch, "Odin Catalyst LLC   ·   Informational and educational only — not investment advice.")
    canvas.drawRightString(letter[0]-0.7*inch, 0.46*inch, "Page %d" % doc.page)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.8*inch,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        title="Small-Cap Surge Continuation Study", author="Odin Catalyst LLC")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("WROTE", OUT)
