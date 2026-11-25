# Readout mine and currency check, 2026-11-25

David 2026-11-25: "mine for more and linked phase readout dates ... go deep red team everything, check for currency".
Facts only, not investment advice. Dates are calendar dates as the company printed them.

## What was done
- Re-read all 242 company-guided readout rows against each company's newest statement (4 researchers).
  225 unchanged; 9 readouts were reported by the company and now show as Reported on the release day;
  2 windows moved (ALZN to December 2026; ERAS-0015 combination data to 2027); 2 passed with no data
  (INBX ChonDRAgon update, NTLA nex-z ISA presentation) and carry a dated no_topline note.
- Mined 232 companies with no guided row for new readout timing in their own releases and SEC filings
  (3 researchers): 159 candidate dates.
- Every changing record was re-opened by an independent red-team pass (6 checkers): {'FIX': 46, 'CONFIRMED': 107, 'DROP': 19}.
  139 new company-guided readout dates went in; 1 was already on the site.
- Every new row carries a hand therapeutic-area tag from the company's stated indication (_readout_ta_manual.json).
- Readouts link to their drug page and to the company's PDUFA-history page (readout_links.py).

## Curator notes
- BCTX: multi-day meeting window kept as stated (2026-12-08..2026-12-11), not a single day
- BEAM: multi-day meeting window kept as stated (2026-12-12..2026-12-15), not a single day
- CLRB: multi-day meeting window kept as stated (2026-12-12..2026-12-15), not a single day
- NRIX: poster day read only from a reprint; window widened to the company's stated ASH dates Dec 12-15
- SNDX: multi-day meeting window kept as stated (2026-12-12..2026-12-15), not a single day
- XENE: multi-day meeting window kept as stated (2026-12-05..2026-12-07), not a single day
- TECX APEX: "by the end of January 2027" kept as a by-date, not narrowed to January
- ARGX ADVANCE-NEXT: program named Efgartigimod (the record carried a placeholder)
- FTH PIK-101: two records for the same readout; kept one
- AAPG APG-5918: session time as printed in the release
- AAPG Olverembatinib + lisaftoclax: session time as printed in the release
- ACAD ACP-211: quote states the year 2027; the half-year words stay in the label
- ACAD Remlifanserin: quote states the year 2027; the quarter words stay in the label
- AUTL AUTO8: quoted sentence says December 2026; the table day was not quoted, so the row is December 2026
- AUTL Obecabtagene autoleucel (obe-cel) Phase 2 CATULUS: "end of 2027" kept as words at year precision
- BCRX BCX17725: "by the end of 2026" kept as words at year precision
- BIIB litifilimab: "first half of December 2026" kept as the Dec 1-15 window
- BIVI Bezisterim: session day as printed in the release
- CGON Cretostimogene grenadenorepvec + gemcitabine: quote states SUO December 1-4, 2026; session day not quoted
- CGON Cretostimogene grenadenorepvec Phase 3: quote states SUO December 1-4, 2026; session day not quoted
- GMAB Epcoritamab: oral session day as printed in the release
- IRON DISC-3405 DISC-3405-102: at ASH, December 12-15, 2026
- KURA Ziftomenib + quizartinib: at ASH 2026
- KURA Ziftomenib + venetoclax: at ASH 2026
- MRKR MT-601: "later this year" kept as words at year precision
- SNDX axatilimab: meeting dates as printed in the release
- SPTX GlyphAgo: "by year-end 2028" kept as words at year precision
- TECX TX2100: "by year-end 2027" kept as words at year precision
- SLN divesiran: quoted release states ASH December 12-15, 2026; the session day is in a different release
- IONS sefaxersen: dropped, timing only a table cell
- KRYS KB111: "before the end of the year" (Nov 2 2026 release) kept as words at year precision

## Not applied
- Reported readouts with no guided row on the site (ACRS, CGON PIVOT-006, FTH, HELP, IVVD, JANX, MLYS, GMAB, NUVB,
  RYTM, VRDN, WVE, ZURA TibuSHIELD, ZLAB, SLS REGAL, and others): left for the reported-results pipeline.
- AARD and BOLT: kept their earlier resolutions (company stopped / no topline).

## Dropped by the red team
- ANNX vonaprument: 2026-11-09 Annexon release says 'ARCHER II completion, including Month 24 analyses, is expected in the third quarter of 2027' only as the alternative path if the DMC recommends continuing; it is a trial-completion milest
- ANNX vonaprument: 2026-11-09 Annexon release: sub-study 'results anticipated in the first quarter of 2027' only if the Q4 2026 DMC finds the Month 15 endpoint met; conditional and already carried by the existing ARCHER II row ('data Q1 20
- ANVS buntanetap: 2026-11-13 Annovis release: 'plans to present the 6-month data at the AD/PD 2027 conference in Barcelona' with no date; same 6-month DUET-AD data already tracked as the March 2027 topline row, so duplicate.
- ATAI VLS-01 (buccal DMT film): Source quote verified (2026-07-06 release, topline Q4 2026), but Lilly agreed to acquire AtaiBeckley on 2026-07-16 and completed the acquisition 2026-09-11 (search results), so ATAI is no longer public.
- ENGN detalimogene voraplasmid + surfactant bladder rinse: Opened BusinessWire release (Nov 11 2026): 'provide an update on the detalimogene plus surfactant bladder rinse cohort mid- 2027' does not say data, and the page does not place the cohort in LEGEND (sidebar refers to pre
- INTS INT230-6: Opened PR Newswire Intensity Q3 release (Nov 5, 2026): quote present, but the Q1 2027 item is an update on the partner's IDMB safety review of whether the skin-irritation issue is resolved, not a clinical data readout (t
- IONS sefaxersen (partner Roche): Opened BusinessWire Ionis Q3 release (Nov 9, 2026): Key Phase 3 Clinical Events table lists 'IMAgINATION interim data | Achieved' in 2026 and 'IMAgINATION data' marked anticipated in 2027 (footnote: timing subject to cha
- LYEL Ronde-cel: Same 11-04 release says 'Lyell announced today updated clinical data' from the two ASH abstracts, and the separate 11-04 ASH release gives the ORR/CR numbers; the data to be presented were already released, and the recor
- MBRX Annamycin + cytarabine: 11-23 release confirms the ASH poster (Dec 12-15, no session date), but Moleculin's 11-04 ASH-acceptance release already disclosed the abstract results (CR rates 43%/36% vs 12% in first 45 patients) and the 11-23 release
- ONCY pelareorep + bortezomib, dexamethasone, pembrolizumab: Opened the 11-09 Oncolytics release: poster Dec 12 is single-cell translational/correlative analysis (release calls it 'translational data'), not a clinical efficacy readout, and its highlights were already disclosed in 
- VYGR NBIB-'223 (FA gene therapy): Ex. 99.1 attributes the timing to the partner: 'Voyager's partner, Neurocrine Biosciences, said that the program is expected to enter a Phase 1 clinical study in the coming months, with initial patient-level data anticip
- PRTC deupirfenidone (LYT-100), Celea Therapeutics: PureTech Half-Year Report (Sep 22 2026) does say 'Celea expects topline results from the Phase 3 SURPASS-IPF trial in the second half of 2029', but the program belongs to Celea Therapeutics (a privately financed PureTech
- SMMT ivonescimab + chemotherapy: Summit Q3 release (Nov 4 2026) full sentence: 'The number of PFS events needed in the squamous cohort for the primary analysis is expected to be reached in the fourth quarter of 2026, and a planned early interim analysis
- SMMT ivonescimab + chemotherapy: Summit Q3 release (Nov 4 2026): 'For the non-squamous cohort, the number of events needed to conduct the PFS analysis is expected to be reached in the first half of 2027.' Event-accrual timing, not a stated data readout.
- SMMT ivonescimab + chemotherapy: Summit Q3 release (Nov 4 2026): 'An interim analysis for OS independent of PFS is planned for the first half of 2027.' Timing of an internal interim analysis, with no statement that data will be reported; not a stated re
- SMMT ivonescimab + casdatifan (Arcus collaboration): Summit Q3 release (Nov 4 2026): Arcus collaboration (ivonescimab + casdatifan in ccRCC), 'Initial data from the study under this collaboration agreement is expected to be generated by mid-2027.' 'Generated' is not a disc
- FTH PIKTOR (serabelisib + sapanisertib): Opened 8-K Ex 99.1 (Nov 3 2026, CIK 1829802): issuer is 'Faeth Therapeutics, Inc.' '(Nasdaq: FTH)' (formerly Sensei; SNSE ticker no longer used). Quote verbatim: 'reporting initial safety and efficacy data from our PIK-1
- TRVI Haduvio (oral nalbuphine ER): Opened Trevi's Q3 2026 release (8-K Ex 99.1, Nov 9, 2026). Quote verified ('now expects to report the outcome of the SSRE analysis early in the first quarter of 2027'), but this is the outcome of a sample-size re-estimat
- XNCR XmAb942 (anti-TL1A): Opened Xencor's Q3 2026 release (8-K Ex 99.1, Nov 4, 2026). Sentence verified, but it is a BLINDED interim analysis whose purpose is not stated and the release does not say any data will be disclosed; not a data readout.
