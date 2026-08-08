#!/usr/bin/env python3
"""Curate the auto-built 44-row big-pharma PDUFA seed -> publish-safe, fully sourced.
Red-team verification (2 independent passes) found ~19 of 44 rows unsafe: already-approved
'ghost' rows, wrong-ticker (companion-dx/partner), duplicates, non-PDUFAs, and imputed
2026-12-31 dates. This keeps only VERIFIED pending US PDUFAs with a primary-source URL and
HONEST date precision (day=confirmed, month=quarter-deadline/estimate, year=vague). Every
dropped row is logged with a reason in seed_rejected_audit.csv for transparency."""
import csv
COLS=["ticker","company","catalyst_type","catalyst_date","date_precision","drug",
      "indication","source","source_url","confidence","redistribute"]

# (ticker, company, date, precision, drug, indication, source_url, confidence, note)
KEEP=[
 # --- confirmed exact PDUFA date (precision=day) ---
 ("RHHBY","Roche/Genentech","2026-12-18","day","Giredestrant (+ everolimus)","ER+/HER2-, ESR1-mutated metastatic breast cancer","https://www.roche.com/media/releases/med-cor-2026-02-20",0.9,""),
 ("ARQT","Arcutis","2026-06-29","day","ZORYVE (roflumilast) Cream 0.3%","Plaque psoriasis, children ages 2-5 (sNDA)","https://www.arcutis.com/fda-accepts-supplemental-new-drug-application-for-arcutis-zoryve-roflumilast-cream-0-3-for-the-treatment-of-plaque-psoriasis-in-children-ages-2-to-5/",0.9,""),
 ("LNTH","Lantheus","2026-06-29","day","Ga-68 edotreotide (LNTH-2501)","Neuroendocrine tumor PET imaging","https://investor.lantheus.com/news-releases/news-release-details/lantheus-announces-fda-grants-pdufa-date-lnth-2501-ga-68",0.9,"PDUFA extended from 3/29 to 6/29/2026"),
 ("MNKD","MannKind","2026-07-26","day","FUROSCIX ReadyFlow Autoinjector","Edema in chronic heart failure / CKD (sNDA)","https://www.globenewswire.com/news-release/2025/12/01/3196982/29517/en/MannKind-Announces-U-S-FDA-Accepts-for-Review-its-Supplemental-New-Drug-Application-sNDA-of-FUROSCIX-ReadyFlow-Autoinjector-for-the-Treatment-of-Edema-in-Adults-with-Chronic-Heart-Failure-or-Chronic-Kidney-Disease.html",0.85,""),
 ("MRNA","Moderna","2026-08-05","day","mRNA-1010","Seasonal influenza (BLA)","https://www.pharmaceutical-technology.com/news/fda-to-review-moderna-seasonal-flu-vaccine-mrna-1010/",0.8,""),
 ("BMY","Bristol Myers Squibb","2026-08-17","day","Iberdomide + daratumumab + dexamethasone","Relapsed/refractory multiple myeloma","https://news.bms.com/news/corporate-financial/2026/U-S--Food-and-Drug-Administration-Accepts-Bristol-Myers-Squibbs-New-Drug-Application-for-Iberdomide-in-Patients-with-Relapsed-or-Refractory-Multiple-Myeloma/default.aspx",0.9,""),
 ("MRK","Merck","2026-08-17","day","KEYTRUDA (pembrolizumab) + Padcev","Perioperative muscle-invasive bladder cancer (sBLA)","https://www.merck.com/news/fda-grants-priority-review-for-keytruda-pembrolizumab-and-keytruda-qlex-pembrolizumab-and-berahyaluronidase-alfa-pmph-each-in-combination-with-padcev-enfortumab-vedotin-ejfv/",0.9,""),
 ("ALPMY","Astellas","2026-08-17","day","Enfortumab vedotin (PADCEV) + pembrolizumab","Muscle-invasive bladder cancer (Priority Review)","https://www.astellas.com/en/news/28736",0.85,"Astellas co-holds PADCEV BLA; pembro is Merck's"),
 ("BIIB","Biogen/Eisai","2026-08-24","day","LEQEMBI IQLIK (lecanemab SC autoinjector)","Early Alzheimer's disease (sBLA)","https://www.prnewswire.com/news-releases/leqembi-iqlik-pdufa-date-updated-to-august-24-in-the-us-302766723.html",0.85,"Eisai is lead BLA holder; BIIB co-commercializes"),
 ("RARE","Ultragenyx","2026-09-19","day","UX111 (ABO-102)","Sanfilippo syndrome type A (BLA resubmission)","https://ir.ultragenyx.com/news-releases/news-release-details/ultragenyx-announces-us-fda-acceptance-bla-resubmission-ux111",0.9,"Ticker corrected ABEO->RARE; Ultragenyx is BLA holder"),
 ("IONS","Ionis","2026-09-22","day","Zilganersen (ION373)","Alexander disease","https://ir.ionis.com/news-releases/news-release-details/ionis-announces-zilganersen-new-drug-application-alexander",0.9,""),
 ("MRK","Merck/Daiichi Sankyo","2026-10-10","day","Ifinatamab deruxtecan (I-DXd)","Extensive-stage small cell lung cancer","https://www.merck.com/news/ifinatamab-deruxtecan-granted-priority-review-in-the-u-s-for-adult-patients-with-previously-treated-extensive-stage-small-cell-lung-cancer-who-experienced-disease-progression-on-or-after-platinum-bas/",0.9,"Daiichi Sankyo is BLA holder; MRK co-develops"),
 ("VTRS","Viatris","2026-10-17","day","MR-141 (phentolamine ophthalmic 0.75%)","Presbyopia (sNDA)","https://newsroom.viatris.com/2026-02-25-FDA-Accepts-Viatris-Supplemental-New-Drug-Application-for-MR-141-Phentolamine-Ophthalmic-Solution-0-75-for-the-Treatment-of-Presbyopia",0.85,"Ticker corrected IRD->VTRS; Viatris is FDA applicant, licensed from Opus Genetics (IRD)"),
 ("VRTX","Vertex","2026-11-30","day","Povetacicept (ALPN-303)","IgA nephropathy","https://news.vrtx.com/news-releases/news-release-details/vertex-announces-us-fda-acceptance-biologics-license-application",0.85,""),
 ("RHHBY","Roche/Genentech","2026-11-30","day","Giredestrant (lidERA)","Adjuvant early breast cancer (ER+/HER2-)","https://www.gene.com/media/press-releases/15115/2026-06-01/fda-accepts-new-drug-application-for-gen",0.8,""),
 # --- real pending PDUFA, date is a quarter-deadline / month estimate (precision=month) ---
 ("BAYRY","Bayer","2026-11-30","month","Sevabertinib (BAY 2927088)","HER2-mutant NSCLC, 1L (sBLA, Priority Review)","https://www.bayer.com/media/en-us/fda-grants-sevabertinib-priority-review-as-a-first-line-treatment-for-patients-with-her2-mutant-non-small-cell-lung-cancer/",0.6,"ESTIMATE ~Nov 2026 (6-mo priority clock from 5/18/2026); exact day not published"),
 ("REGN","Regeneron","2026-08-31","month","Garetosmab","Fibrodysplasia ossificans progressiva","https://investor.regeneron.com/news-releases/news-release-details/garetosmab-biologics-license-application-accepted-fda-priority",0.65,"ESTIMATE 'August 2026' per Regeneron; exact day not published"),
 ("TAK","Takeda","2026-09-30","month","Oveporexton (TAK-861)","Narcolepsy type 1","https://www.takeda.com/newsroom/newsreleases/2026/fda-accepts-nda-priority-review-oveporexton-narcolepsy-type-1/",0.65,"ESTIMATE Q3 2026 (by Sep 30); exact day not published"),
 ("PTGX","Protagonist/Takeda","2026-09-30","month","Rusfertide","Polycythemia vera","https://www.takeda.com/newsroom/newsreleases/2026/nda-rusfertide/",0.65,"ESTIMATE Q3 2026; co-developed with Takeda (TAK). Consolidates REVIVE/VERIFY into one NDA"),
 ("ROIV","Roivant/Priovant","2026-09-30","month","Brepocitinib (VALOR)","Dermatomyositis","https://investor.roivant.com/news-releases/news-release-details/priovant-announces-fda-acceptance-and-priority-review-new-drug",0.65,"ESTIMATE Q3 2026; Priovant is a Roivant company (PFE holds ~25%, not the filer)"),
 ("NVO","Novo Nordisk","2026-12-31","month","CagriSema (AM833)","Obesity / weight management","https://www.prnewswire.com/news-releases/novo-nordisk-files-for-fda-approval-of-cagrisema-the-first-once-weekly-combination-of-glp1-and-amylin-analogues-for-weight-management-302645862.html",0.55,"ESTIMATE 'late 2026'; exact PDUFA not published"),
 ("AZN","AstraZeneca/Alexion","2026-12-31","month","Ultomiris (ravulizumab)","IgA nephropathy (I CAN, sBLA)","https://www.astrazeneca.com/media-centre/press-releases/2026/ultomiris-granted-priority-review-in-the-us-as-treatment-for-adults-with-immunoglobulin-a-nephropathy.html",0.6,"ESTIMATE Q4 2026; exact day not published"),
 ("BAYRY","Bayer","2026-12-31","month","KERENDIA (finerenone)","Type 1 diabetes + CKD (FINE-ONE, sNDA)","https://www.bayer.com/en/us/news-stories/kerendiar-granted-priority-review",0.55,"ESTIMATE H2 2026, Priority Review; exact day not published"),
 # --- real pending PDUFA, date genuinely unknown (precision=year) ---
 ("AZN","AstraZeneca","2026-12-31","year","Camizestrant (SERENA-6)","HR+/HER2- metastatic breast cancer","https://www.astrazeneca.com/media-centre/press-releases/2026/us-fda-decision-date-camizestrant-extended.html",0.45,"PDUFA EXTENDED May 2026 after ODAC; new date not published — year estimate only"),
 ("ABBV","AbbVie","2026-12-31","year","Tavapadon (TEMPO)","Early Parkinson's disease","https://www.managedhealthcareexecutive.com/view/abbvie-submits-nda-for-parkinson-s-disease-drug-tavapadon",0.45,"NDA submitted; PDUFA date not published — year estimate. TEMPO-1/2/3 are one NDA"),
]

# (ticker, drug, reason)
DROP=[
 ("LLY","Tirzepatide (new indication)","NOT A PDUFA: HFpEF application withdrawn May 2025, no resubmission timeline"),
 ("GSK","Tebipenem pivoxil (Utebzi)","GHOST: already APPROVED 2026-06-17 — belongs in historic, not forward calendar"),
 ("REGN","DB-OTO (Otarmeni)","GHOST: already APPROVED ~Apr 2026 (accelerated approval)"),
 ("NVO","Sogroya (somapacitan), Noonan","GHOST: already APPROVED 2026-02-27 (sBLA, 3 pediatric indications)"),
 ("NRXP","KETAFREE","NOT A PDUFA: 2026-07-29 is a GDUFA generic ANDA goal date, not a PDUFA"),
 ("AZN","Enhertu (T-DXd) early BC","GHOST: already APPROVED ~May 2026 (DESTINY-Breast05/11)"),
 ("NVO","Mim8 (denecimig)","UNCONFIRMED: BLA submitted Sep 2025 but no PDUFA date corroborated; 2026-09-30 was imputed"),
 ("ABBV","RINVOQ (upadacitinib) vitiligo","UNCONFIRMED DATE: apps submitted Feb 2026, no PDUFA published; standard review may land 2027"),
 ("GH","Camizestrant (SERENA-6)","WRONG TICKER: Guardant is the companion diagnostic (Guardant360 CDx), not the drug sponsor (AZN)"),
 ("GILD","Trodelvy (sacituzumab govitecan)","GHOST/WRONG INDICATION: urothelial withdrawn Nov 2024; 1L TNBC APPROVED 2026-06-24 — nothing pending"),
 ("MRK","Trodelvy (sacituzumab govitecan)","WRONG TICKER: Trodelvy is Gilead's (GILD); Merck is only the Keytruda combo partner"),
 ("AZN","Gefurulimab (PREVAIL)","UNCONFIRMED: P3 positive Apr 2026 but no FDA filing/PDUFA announced yet"),
 ("NVS","Pluvicto (Lu-177 vipivotide)","UNCONFIRMED: pre-chemo mCRPC already approved Mar 2025; no new-indication US PDUFA confirmed"),
 ("LLY","Tirzepatide CV outcomes","NOT A PDUFA: SURMOUNT-MMO is an ongoing data readout, not an FDA action"),
 ("PFE","TUKYSA + trastuzumab + pertuzumab","UNCONFIRMED: HER2CLIMB-05 topline Mar 2026 but no FDA filing/PDUFA announced yet"),
 ("PFE","Brepocitinib (VALOR)","DUPLICATE + WRONG SPONSOR: same NDA as ROIV/Priovant row; PFE is ~25% holder, not the filer"),
 ("PTGX","Rusfertide (VERIFY)","DUPLICATE: same rusfertide PV NDA already kept as the PTGX/Takeda Q3 row"),
 ("TAK","Rusfertide (VERIFY)","DUPLICATE: same rusfertide PV NDA already kept as the PTGX/Takeda Q3 row"),
 ("ABBV","Tavapadon (TEMPO-2)","DUPLICATE: TEMPO-1/2/3 are one tavapadon NDA, already kept as the single ABBV row"),
]

with open("bigpharma_pdufa_seed.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(COLS)
    for tk,co,date,prec,drug,ind,url,conf,note in KEEP:
        w.writerow([tk,co,"PDUFA",date,prec,drug,ind,"curated_pharma",url,conf,"True"])

with open("seed_rejected_audit.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["ticker","drug","reject_reason"])
    for tk,drug,reason in DROP: w.writerow([tk,drug,reason])

# integrity checks
blank=[k for k in KEEP if not k[6].strip()]
print(f"KEEP rows written: {len(KEEP)}  | DROP logged: {len(DROP)}  | total {len(KEEP)+len(DROP)} (expect 44)")
print(f"rows missing source_url: {len(blank)} (expect 0)")
prec={}
for k in KEEP: prec[k[3]]=prec.get(k[3],0)+1
print("date_precision mix:", prec)
