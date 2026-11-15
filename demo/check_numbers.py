#!/usr/bin/env python3
"""Check every number the demo video says or shows against the page's data files, and stop if one disagrees.

Each check names the caption (or card), the words in it that carry the number, the data file and field the number is
read from, and the rule. Nothing here is typed from memory: the value printed is the one in docs/data.

Standard library only. Usage: python3 demo/check_numbers.py   (exit status 1 when a check fails)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "docs" / "data"
WORDS = {"six": 6, "ten": 10, "thirty-seven": 37, "forty-nine": 49}


def run():
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    cap = script["captions"]
    us = json.loads((DATA / "conus.json").read_text(encoding="utf-8"))
    st = json.loads((DATA / "conus_states.json").read_text(encoding="utf-8"))["states"]
    page = (HERE.parent / "docs" / "index.html").read_text(encoding="utf-8")
    k = us["snpp_to_aqua"]["coefficients"]["annual_k"]
    err = us["snpp_to_aqua"]["leave_one_year_out"]["monthly_k"]["all_years"]["abs_error_pct_of_total"]
    passed = sum(1 for s in st.values() if s["calibration_accepted"])
    first = us["sensors"]["MODIS_TERRA/standard"]["first"]
    state = script["scene_state"]
    checks = [
        ("caption 2", cap[1], "since 2000", "conus.json sensors['MODIS_TERRA/standard'].first", first, first.startswith("2000")),
        ("caption 3", cap[2], "over six times", "conus.json snpp_to_aqua.coefficients.annual_k", k, WORDS["six"] < k < WORDS["six"] + 1),
        ("caption 4", cap[3], "month by month", "conus.json calibration_accepted", us["calibration_accepted"], us["calibration_accepted"] is True),
        ("caption 4", cap[3], "about ten percent", "conus.json snpp_to_aqua.leave_one_year_out.monthly_k.all_years.abs_error_pct_of_total", err, round(err) == WORDS["ten"]),
        ("caption 5", cap[4], "Thirty-seven", "conus_states.json: states with calibration_accepted true", passed, passed == WORDS["thirty-seven"]),
        ("caption 5", cap[4], "forty-nine", "conus_states.json: number of states", len(st), len(st) == WORDS["forty-nine"]),
        ("scene 5", "the state the pointer goes to is not harmonized", "", f"conus_states.json states.{state['not_harmonized']}.calibration_accepted",
         st[state["not_harmonized"]]["calibration_accepted"], st[state["not_harmonized"]]["calibration_accepted"] is False),
        ("card 2", script["notice_sentence"], "late 2026 or early 2027", "docs/index.html: the sentence as the page words it", "present" if script["notice_sentence"] in page else "absent", script["notice_sentence"] in page),
    ]
    rows, bad = [], 0
    for where, text, words, field, value, ok in checks:
        ok = bool(ok) and words in text
        bad += not ok
        rows.append({"where": where, "words": words or text, "field": field, "value": value, "ok": ok})
        print(f"{'ok  ' if ok else 'FAIL'} {where}: \"{words or text}\" <- {field} = {value}")
    (HERE / "build").mkdir(exist_ok=True)
    (HERE / "build" / "numbers.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return bad


if __name__ == "__main__":
    failed = run()
    if failed:
        sys.exit(f"{failed} number(s) in the demo disagree with the data. Nothing was built.")
