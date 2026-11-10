# -*- coding: utf-8 -*-
"""apply_1110_success_rates.py -- /clinical-trial-success-rates checked against its source (audit 2026-11-09 §5 item 4).

The page earns ~840 Bing AI citations in 60 days and had never been audited. Read against the source it names, BIO /
Informa Pharma Intelligence / QLS Advisors, "Clinical Development Success Rates 2011-2020" (February 2021):
  - the four tiles (52%, 29%, 58%, 91%) match the 2011-2020 report: 52.0% (n=4,414), 28.9% (n=4,933),
    57.8% (n=1,928), 90.6% (n=1,453); LOA from Phase I 7.9%; oncology 5.3%; hematology 23.9%.
  - but the caption gave "9,985 phase transitions across 7,455 programs", the sample of the EARLIER 2006-2015 report;
    the 2011-2020 report counts 12,728 transitions across 9,704 programs (1,779 companies).
  - "~86-91%" for filing to approval and "~7.9-9.6%" from Phase 1 blended the two reports (85.3% / 9.6% are 2006-2015).
  - the source link pointed at a biomedtracker.com report page, not the report; now BIO's page and its PDF.
  - "our readout-reaction dataset ... coming soon": /readouts has been live since September; now a link.
Facts only, not investment advice.
"""
import io, os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src", "clinical-trial-success-rates", "index.html")
BIO = "https://www.bio.org/clinical-development-success-rates-and-contributing-factors-2011-2020"
PDF = "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf"
s = io.open(P, encoding="utf-8").read(); o = s
R = [
 ("Source: BIO / Informa Pharma Intelligence (Biomedtracker), \"Clinical Development Success Rates\": 9,985 phase transitions across 7,455 programs.",
  f"Source: BIO, Informa Pharma Intelligence and QLS Advisors, <a href=\"{BIO}\" rel=\"noopener\">Clinical Development Success Rates 2011-2020</a> (February 2021): 12,728 phase transitions across 9,704 development programs at 1,779 companies, Biomedtracker data."),
 ("<b>~52% advance</b>", "<b>52.0% advance</b>"), ("<b>~29% advance</b>", "<b>28.9% advance</b>"),
 ("<b>~58% advance</b>", "<b>57.8% advance</b>"), ("<b>~86-91%</b>", "<b>90.6% approved</b>"),
 ("<b>~8-10%</b>", "<b>7.9%</b>"), ("<b>~5%</b>", "<b>5.3%</b>"),
 ("Of those filed, the FDA ultimately approves roughly 86-91%.",
  "Of those filed, 90.6% were ultimately approved (BIO, Informa and QLS, 2011-2020 data)."),
 ("about 58% of Phase 3 programs advance", "57.8% of Phase 3 programs advanced"),
 ("only about 29% of Phase 2 programs advance to Phase 3", "only 28.9% of Phase 2 programs advanced to Phase 3"),
 ("About 8-10% of drugs that enter Phase 1 are ultimately approved (BIO cites ~7.9-9.6% cumulative). It is lowest in oncology (~5%) and higher in areas like hematology.",
  "7.9% of drug programs that entered Phase 1 in 2011-2020 went on to FDA approval (BIO, Informa and QLS). It was lowest in oncology (5.3%) and highest in hematology (23.9%)."),
 ("<b>We're publishing our own quantified readout-reaction dataset (real stock moves by phase and company size) alongside a live readout calendar: coming soon.</b>",
  "Our <a href=\"/readouts\">readout calendar</a> lists upcoming clinical trial readouts with their source, and the stock moves we measured around readouts that have happened."),
 ("<a href='https://www.biomedtracker.com/ReportDetail.cfm?ReportID=701' rel='nofollow noopener' target='_blank'>BIO/Informa Clinical Development Success Rates</a>. Industry-wide averages; your mileage varies by indication and trial design.",
  f"<a href='{BIO}' rel='noopener'>BIO, Informa Pharma Intelligence and QLS Advisors, Clinical Development Success Rates 2011-2020</a> (<a href='{PDF}' rel='noopener'>report PDF</a>), checked against the report on November 10, 2026. Industry-wide averages for 2011-2020; rates vary by indication and trial design."),
]
miss = []
for a, b in R:
    n = s.count(a)
    if not n:
        miss.append(a[:70])
    s = s.replace(a, b)
io.open(P, "w", encoding="utf-8").write(s)
print("changed" if s != o else "unchanged", "| not found:", miss)
for bad in ("9,985", "86-91", "7.9-9.6", "coming soon", "~8-10%"):
    if bad in s:
        print("  STILL PRESENT:", bad)
