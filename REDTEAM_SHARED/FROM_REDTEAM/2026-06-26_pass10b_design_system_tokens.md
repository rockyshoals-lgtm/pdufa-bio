# pdufa.bio — Design System: light-teal tokens (drop-in for the builder)

Direction: **light-first public site + dark "pro" mode for the gated dashboard**, unified by a **clinical-teal** signature. Welcoming + crisp for retail, calm for traders, legible for institutions. Flat (no gradients/glow), generous whitespace, bordered rows, tabular numerals, and **colour reserved for meaning** (outcomes + provenance), not decoration.

## 1. Tokens — paste into `:root` (light) and `[data-theme="pro"]` (dark)

```css
:root{
  /* surfaces */
  --bg:#F7FAFC;            /* page canvas */
  --surface:#FFFFFF;        /* cards, rows */
  --surface-2:#F2F6F9;      /* subtle fill / hover */
  /* text (all AA on --surface) */
  --ink:#0B1F2A;            /* primary  ~14:1 */
  --text-secondary:#51677A; /* secondary ~6.4:1 */
  --text-muted:#66798A;     /* hints/captions ~4.7:1 */
  /* lines */
  --border:#E3EBF2;
  --border-strong:#CFDBE6;
  /* brand — clinical teal (the signature) */
  --brand:#0E7C86;
  --brand-strong:#0A5A62;   /* hover/active, text-on-tint */
  --brand-tint:#E6F6F7;     /* "verified / sourced" chip bg */
  --link:#0E7C86;
  /* semantics — OUTCOMES ONLY */
  --pos:#15803D; --pos-tint:#E7F4EC; --pos-text:#105C2C;  /* approved */
  --neg:#B42318; --neg-tint:#FDECEA; --neg-text:#8A1B12;  /* CRL */
  --warn:#B25E09; --warn-tint:#FBF0E1; --warn-text:#7C4206;/* estimated date / caution */
  /* daily price change — muted, text-only (not filled chips) */
  --up:#157F46; --down:#C2371F;
  /* layout */
  --radius:8px; --radius-card:12px;
}
[data-theme="pro"]{       /* gated dashboard only */
  --bg:#0B1B26; --surface:#102A36; --surface-2:#13262F;
  --ink:#EAF2F6; --text-secondary:#9DB1BE; --text-muted:#7C93A1;
  --border:#16313B; --border-strong:#21434E;
  --brand:#3BD6C6; --brand-strong:#8EE9DC; --brand-tint:#0E3A3B; --link:#5FE0D2;
  --pos:#3FBF6B; --pos-tint:#0F3320; --pos-text:#8FE2A8;
  --neg:#FF6B5E; --neg-tint:#3A1512; --neg-text:#FF9B90;
  --warn:#E0A94B; --warn-tint:#2E2208; --warn-text:#F2C97E;
  --up:#3FBF6B; --down:#FF6B5E;
}
```
Switch the app to dark with `<html data-theme="pro">` (or a toggle). The public/marketing/SEO surface stays light.

## 2. Typography
```css
:root{
  --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
body{ font-family:var(--font-sans); color:var(--ink); background:var(--bg); line-height:1.5; -webkit-font-smoothing:antialiased; }
```
- Load **Inter** (Google Fonts) for the crisp, clinical feel; the system stack is the fallback.
- **Weights: 400 regular + 600 semibold only.** Headings/labels/emphasis = 600; everything else 400.
- Sizes: h1 28 · h2 20 · h3 16 · body 15 · small 13 · caption 12 (never below 12 on data; 11 absolute floor).
- **Every number gets `font-variant-numeric: tabular-nums`** (prices, dates, %, T-minus) so columns align — this alone makes data look "crisp".
- Sentence case everywhere. No ALL-CAPS section headers (retire the current `text-transform:uppercase` labels — they read as "terminal").

## 3. Component recipes
```css
.card{ background:var(--surface); border:0.5px solid var(--border); border-radius:var(--radius-card); padding:16px 18px; }
/* lists are bordered ROWS, not stacked cards */
.row{ display:flex; gap:14px; align-items:center; padding:14px 4px; border-bottom:0.5px solid var(--border); }
.row:hover{ background:var(--surface-2); }
.tpill{ width:54px; text-align:center; border:0.5px solid var(--border); border-radius:10px; padding:8px 4px; }
.tpill .n{ font-size:18px; font-weight:600; color:var(--brand); font-variant-numeric:tabular-nums; }
.tpill .u{ font-size:11px; color:var(--text-muted); }
/* trust wears the brand colour */
.chip-sourced{ display:inline-flex; gap:4px; align-items:center; font-size:12px;
  color:var(--brand-strong); background:var(--brand-tint); border-radius:6px; padding:3px 9px; }
.chip-approved{ color:var(--pos-text); background:var(--pos-tint); border-radius:6px; padding:3px 9px; }
.chip-crl{ color:var(--neg-text); background:var(--neg-tint); border-radius:6px; padding:3px 9px; }
.chip-est{ color:var(--warn-text); background:var(--warn-tint); border-radius:6px; padding:3px 9px; }
.chip-neutral{ color:var(--text-secondary); background:var(--surface-2); border-radius:6px; padding:3px 9px; }
.btn{ font-weight:600; border:0.5px solid var(--border-strong); border-radius:var(--radius); padding:8px 14px; background:var(--surface); color:var(--ink); }
.btn-primary{ background:var(--brand); border-color:var(--brand); color:#fff; }  /* max ONE per view */
a{ color:var(--link); text-decoration:none; } a:hover{ text-decoration:underline; }
```
Row anatomy (retail-first): `[T-pill] · ticker + cap-tag · ONE plain-English line · [✓ Sourced chip] + ONE base-rate fact · date`. Trader jargon (Vol rich / IV crush / ±exp) goes on a **secondary, muted line or behind a tap** — present for pros, never the first thing a beginner sees.

## 4. The laws (what keeps it on-brand)
1. **Green/red is for outcomes only.** Approved = `--pos`, CRL = `--neg`. Daily price change uses `--up`/`--down` as *text only* (small, with +/−), never a filled chip. Everything else is neutral slate + teal. This is what makes it *calm* vs the competitors' terminal sea of red/green.
2. **Trust wears teal.** The "✓ Sourced — FDA/SEC" chip is the single most confident coloured element on any card. Provenance is a feature, not fine print.
3. **Lists = bordered rows, not floating cards.** Crisp, dense, scannable.
4. **Plain-English + one number lead; jargon is demoted.** Welcoming to retail without losing traders.
5. **Flat.** No gradients, glow, or heavy shadows. At most a 1px hairline border + optional `0 1px 2px rgba(11,31,42,.04)` card ring. Whitespace does the work.
6. **AA always.** Every text/background pair ≥ 4.5:1 (the tokens above are chosen to pass; e.g. `--text-secondary` 6.4:1, `--text-muted` 4.7:1 on white). Re-verify on `--surface-2`.
7. **Tabular numerals on all data.**

## 5. Migration map (current → new)
| Current (dark navy/gold) | New |
|---|---|
| `--navy #050f1f` (page) | light `--bg #F7FAFC` / app `--bg #0B1B26` |
| `--card #0c1d38` | `--surface #FFFFFF` / app `#102A36` |
| `--gold #e3ba5e` (accent) | **retire** → `--brand #0E7C86` (teal). Optional: keep a faint gold only as a "Pro" premium accent. |
| `--ink #f2f6fc` | `--ink #0B1F2A` / app `#EAF2F6` |
| `--mut #a7bcd9` / `--mut2 #7890b3` | `--text-secondary #51677A` / `--text-muted #66798A` (fixes the AA fails) |
| `--green #5fd07a` | `--pos #15803D` (calmer) / app `#3FBF6B` |
| `--red #ff7a7a` | `--neg #B42318` / app `#FF6B5E` |
| `--amber #ffc46b` | `--warn #B25E09` / app `#E0A94B` |
| uppercase labels | sentence case, weight 600 |

Roll out light on the public site + marketing first (biggest welcoming/SEO/contrast win), then theme the gated app with `[data-theme="pro"]`. The dark "pro" strip in the rendered mockup shows the app variant holds up.

*— Red Team Pass 10b (design system tokens).*
