# -*- coding: utf-8 -*-
"""Add organiser-verified congress dates to conf_registry.json.

David, 2026-09-09: "extend the congress registry to find more presenters."

WHY THIS IS THE LEVER. The presenter miner finds a filing that says a company will present at
a congress, then asks the registry for that congress-year's date. `resolve_date()` returns an
observed DAY only when the registry holds that year; otherwise it projects a month (future
mentions only) or returns nothing and the row is dropped. Before this run the registry held
55 congresses, 34 with an observed 2026 date and **zero with any 2027 date** — so every filing
naming a 2027 meeting was found by the EDGAR walk and then discarded for want of a date.

EVERY DATE BELOW WAS READ ON THE ORGANISER'S OWN PAGE, and each carries that URL. Dates are
the product (house rule 4); a congress whose date I could not verify is simply absent. ASH
2027 is the worked example: the society has published its 2027 regional Highlights meetings
but not the 2027 Annual Meeting, so ASH 2027 is NOT in this file.

Start dates only. The registry's contract is one ISO day per congress-year (the first day of
the meeting), which is what date_basis "observed" means downstream.
"""
import datetime as dt
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "conf_registry.json")

# code -> {year: (start_date, source_url, note)}
VERIFIED = {
    "AAO": {
        "2026": ("2026-10-09", "https://www.aao.org/annual-meeting/past-and-future-meetings",
                 "AAO 2026, Oct. 9-12 - New Orleans, Ernest N. Morial Convention Center"),
        "2027": ("2027-11-12", "https://www.aao.org/annual-meeting/past-and-future-meetings",
                 "AAO 2027, Nov. 12-15 - Las Vegas, Venetian Expo & Hotel"),
    },
    "OBESITYWEEK": {
        "2026": ("2026-11-14", "https://obesityweek.org/attend/future-dates/",
                 "ObesityWeek 2026 Washington DC, live sessions Saturday-Tuesday, November 14-17"),
        "2027": ("2027-11-08", "https://obesityweek.org/attend/future-dates/",
                 "ObesityWeek 2027 Grand Rapids MI, live sessions Monday-Thursday, November 8-11"),
        "2028": ("2028-11-12", "https://obesityweek.org/attend/future-dates/",
                 "ObesityWeek 2028 Cleveland OH, live sessions Sunday-Wednesday, November 12-15"),
    },
    "ACAAI": {
        "2026": ("2026-11-12", "https://annualmeeting.acaai.org/2026/meeting_info.cfm",
                 "ACAAI 2026 Annual Scientific Meeting, Phoenix AZ, November 12-16, 2026"),
        "2027": ("2027-11-11", "https://annualmeeting.acaai.org/2026/future_meeting_dates.cfm",
                 "Future Meeting Dates: November 11-15, 2027, Nashville, Tennessee"),
        "2028": ("2028-11-02", "https://annualmeeting.acaai.org/2026/future_meeting_dates.cfm",
                 "Future Meeting Dates: November 2-6, 2028, Seattle, Washington"),
    },
    "ENA": {
        "2026": ("2026-11-18", "https://event.eortc.org/ena2026/",
                 "38th EORTC-NCI-AACR Symposium on Molecular Targets and Cancer Therapeutics, "
                 "Barcelona, November 18-20, 2026"),
    },
    "ASCO-GU": {
        "2027": ("2027-02-11", "https://www.asco.org/gu/dates-know",
                 "ASCO Genitourinary Cancers Symposium, February 11-13, 2027, "
                 "Moscone West, San Francisco CA"),
    },
    "ACC": {
        "2027": ("2027-04-10", "https://accscientificsession.acc.org/Information-Pages/Future-Meetings",
                 "ACC.27 Together With WCC, April 10-12, 2027, Houston TX"),
    },
    "ADA": {
        "2027": ("2027-06-18", "https://professional.diabetes.org/scientific-sessions",
                 "86th Scientific Sessions, June 18-21, 2027, Washington DC"),
    },
    "ASCO": {
        "2027": ("2027-06-04", "https://www.asco.org/annual-meeting/dates-know",
                 "2027 ASCO Annual Meeting, June 4-8, 2027, McCormick Place, Chicago IL"),
    },
}


def main():
    reg = json.load(io.open(REG, encoding="utf-8"))
    added_years, new_codes = 0, 0
    for code, years in VERIFIED.items():
        rec = reg.get(code)
        if rec is None:
            rec = reg[code] = {"dates": {}}
            new_codes += 1
        rec.setdefault("dates", {})
        rec.setdefault("sources", {})
        for year, (iso, url, note) in sorted(years.items()):
            if rec["dates"].get(year) == iso:
                continue
            rec["dates"][year] = iso
            rec["sources"][year] = {"url": url, "states": note,
                                    "verified_on": "2026-09-09"}
            added_years += 1
            print(f"  {code} {year} -> {iso}   ({url})")
        # doy from the most recent observed date, so a future mention with no observed year
        # still projects to the right MONTH (never a day; resolve_date enforces that).
        newest = max(rec["dates"])
        rec["doy"] = dt.date.fromisoformat(rec["dates"][newest]).timetuple().tm_yday

    io.open(REG, "w", encoding="utf-8").write(
        json.dumps(reg, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    have26 = sum(1 for v in reg.values() if "2026" in (v.get("dates") or {}))
    have27 = sum(1 for v in reg.values() if "2027" in (v.get("dates") or {}))
    print(f"\nregistry: {len(reg)} congresses ({new_codes} new), {added_years} date(s) added")
    print(f"  observed 2026 dates: {have26}")
    print(f"  observed 2027 dates: {have27}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
