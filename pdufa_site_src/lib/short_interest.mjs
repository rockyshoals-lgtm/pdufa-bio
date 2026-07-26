/**
 * Short-interest display rules.
 *
 * WHY THIS EXISTS
 * days_to_cover = short_qty / average_daily_volume. For an illiquid nano-cap the denominator
 * collapses and the ratio explodes: 18.3% of our 3.63M-row FINRA panel exceeds 100 days, and
 * the series clips at a sentinel value of exactly 1,000.
 *
 * "Short interest: 4,200 days to cover" is not a fact. It is arithmetic that happens to be true
 * and information that is false — it says nothing about squeeze risk, only that the stock barely
 * trades. Printing it destroys credibility on sight.
 *
 * So: above ~60 days we stop reporting a number and report the thing that is actually true —
 * the stock is very illiquid. And we ALWAYS print the settlement date, because short interest is
 * a bi-monthly snapshot, not a live figure, and a stale number presented as current is a lie of
 * omission.
 */
export const DTC_SENTINEL = 1000;   // FINRA/vendor clip value — not a real measurement
export const DTC_ABSURD   = 60;     // above this, the ratio is noise, not signal
export const DTC_CAUTION  = 30;     // above this, always show context

export function formatDaysToCover(dtc) {
  if (dtc === null || dtc === undefined || Number.isNaN(dtc)) {
    return { text: 'not reported', qualifier: null, show_number: false };
  }
  if (dtc >= DTC_SENTINEL) {
    return { text: 'very illiquid', qualifier: 'the stock barely trades; days-to-cover is not meaningful here',
             show_number: false };
  }
  if (dtc > DTC_ABSURD) {
    return { text: 'very illiquid', qualifier: `days-to-cover exceeds ${DTC_ABSURD}; the average-volume denominator is too small for this ratio to mean anything`,
             show_number: false };
  }
  if (dtc > DTC_CAUTION) {
    return { text: `${dtc.toFixed(1)} days`, qualifier: 'thinly traded — treat with caution', show_number: true };
  }
  return { text: `${dtc.toFixed(1)} days`, qualifier: null, show_number: true };
}

/** Short interest is a BI-MONTHLY SNAPSHOT. Never render it without its settlement date. */
export function renderShortInterest(dtc, settlementDate) {
  if (!settlementDate) {
    throw new Error('renderShortInterest: settlement date is REQUIRED. Short interest is a ' +
                    'bi-monthly snapshot; presenting it without its as-of date implies it is live.');
  }
  const f = formatDaysToCover(dtc);
  return { ...f, settlement: settlementDate,
           line: `Short interest into this event: ${f.text} (settlement ${settlementDate})` };
}
