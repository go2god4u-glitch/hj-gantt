# -*- coding: utf-8 -*-
"""
규칙 회귀 테스트 — 실물 간트에서 확인된 값을 못 박아 둔다.

여기 적힌 기대값은 추측이 아니라 **실물 간트 파일에서 직접 읽은 값**이다.
config.json을 만지다가 이 테스트가 깨지면, 테스트가 틀린 게 아니라 규칙이
실제와 어긋난 것이다.

    python make_test_fixtures.py     # 먼저 샘플 파일 생성
    python tests/test_rules.py
"""
from __future__ import annotations

import sys
import warnings
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gantt_engine import (  # noqa: E402
    add_months, apply_tint, diff_records, generate, load_config,
    parse_cell_date, read_ra_plan, record_key, sort_records,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RA_PLAN = FIXTURES / "sample_ra_plan.xlsx"
BUNDLED = Path(__file__).resolve().parent.parent / "template" / "RA_gantt_template.xlsx"

failures: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}\n       기대: {want}\n       실제: {got}")
        failures.append(label)


def section(n: str) -> None:
    print(f"\n[{n}]")


def test_date_parsing() -> None:
    section("1] 날짜 판독 — 실물의 지저분한 값들")
    t = ["TBD", "N/A", "TBU", "Not required", ""]
    check("'2025-10-03' → 날짜", parse_cell_date("2025-10-03", t).value, date(2025, 10, 3))
    check("'TBD' → 미정", parse_cell_date("TBD", t).value, None)
    check("'N/A' → 미정", parse_cell_date("N/A", t).value, None)
    check("'TBU' → 미정", parse_cell_date("TBU", t).value, None)
    check("'2027/01' → partial 표시", parse_cell_date("2027/01", t).partial, True)
    check("'2026-12' → partial 표시", parse_cell_date("2026-12", t).partial, True)
    check("'2026 3Q' → 3분기 첫달", parse_cell_date("2026 3Q", t).value, date(2026, 7, 1))
    check("'2025 Oct' → 2025-10", parse_cell_date("2025 Oct", t).value, date(2025, 10, 1))
    check("'2026' → 연초, partial", parse_cell_date("2026", t).partial, True)
    check("'2026-12-31\\n(TBD)' → 괄호 제거",
          parse_cell_date("2026-12-31\n(TBD)", t).value, date(2026, 12, 31))
    check("'2022-9(E)' → 괄호 제거 후 연-월",
          parse_cell_date("2022-9(E)", t).value, date(2022, 9, 1))
    check("'2024-11-30 2024-12-13' → 첫 날짜만",
          parse_cell_date("2024-11-30 2024-12-13", t).value, date(2024, 11, 30))
    check("'2025-10-03'은 partial 아님", parse_cell_date("2025-10-03", t).partial, False)


def test_add_months() -> None:
    section("2] 개월 가감 — 말일 넘침")
    check("2025-03-31 -1개월 → 2025-02-28", add_months(date(2025, 3, 31), -1), date(2025, 2, 28))
    check("2024-03-31 -1개월 → 2024-02-29(윤년)", add_months(date(2024, 3, 31), -1), date(2024, 2, 29))
    check("2025-01-15 -2개월 → 2024-11-15", add_months(date(2025, 1, 15), -2), date(2024, 11, 15))
    check("2025-12-01 +1개월 → 2026-01-01", add_months(date(2025, 12, 1), 1), date(2026, 1, 1))


def test_ground_truth() -> None:
    """가장 중요한 테스트 — 실물 간트가 적어둔 값을 재현하는가."""
    section("3] 실물 간트 대조")
    recs, _, _ = read_ra_plan(RA_PLAN, load_config())
    by_product = {r.product: r for r in recs}

    # ── 기준행(충전라인 신설) (Ongoing). 실물 간트: PRA Sub=2025-12-23, PRA App=2026-08-31
    #    App이 Actual(2026-05-06)이 아니라 Planned인 것이 핵심.
    r = by_product["Product-B"]
    check("solvent PRA Sub = Actual", r.pra_sub, date(2025, 12, 23))
    check("solvent PRA App = Planned (Ongoing이므로)", r.pra_app, date(2026, 8, 31))
    check("  → sub 출처", r.origins["pra_sub"], "actual")
    check("  → app 출처", r.origins["pra_app"], "planned")

    # ── STEP11 (Pending). 실물 간트: Sub=2026-09-01, App=2027-07-01
    r = by_product["Product-E"]
    check("STEP11 NDA Sub", r.nda_sub, date(2026, 9, 1))
    check("STEP11 NDA App", r.nda_app, date(2027, 7, 1))

    # ── Orphan drug designation (Completed). 실물 간트: Sub=2024-09-30, App=2025-05-06
    r = by_product["Product-F"]
    check("Orphan NDA Sub", r.nda_sub, date(2024, 9, 30))
    check("Orphan NDA App = Actual (Completed이므로)", r.nda_app, date(2025, 5, 6))


def test_pair_separation() -> None:
    """PRA와 NDA가 섞이지 않는가 — 가장 큰 사고가 날 수 있는 지점."""
    section("4] PRA / NDA 쌍 분리")
    recs, cols, _ = read_ra_plan(RA_PLAN, load_config())
    check("PRA Planned Sub = K열(11)", cols.pra_planned_sub, 11)
    check("PRA Actual Sub = L열(12)", cols.pra_actual_sub, 12)
    check("NDA Planned Sub = O열(15)", cols.nda_planned_sub, 15)
    check("NDA Actual App = R열(18)", cols.nda_actual_app, 18)

    r = next(x for x in recs if x.product == "Product-B")
    check("PRA와 NDA가 서로 다른 값", r.pra_sub != r.nda_sub, True)


def test_responsible_column() -> None:
    section("5] 담당자 컬럼 선택")
    recs, cols, _ = read_ra_plan(RA_PLAN, load_config())
    check("B열(20260608~) 선택", cols.responsible, 2)
    check("A열은 대체로 기록", cols.responsible_alt, 1)
    check("주의 메시지 남김", any("Responsible" in n for n in cols.notes), True)


def test_category_remap() -> None:
    section("6] Category 변환")
    recs, _, _ = read_ra_plan(RA_PLAN, load_config())
    by_product = {r.product: r for r in recs}
    check("Safety/Labelling → Others", by_product["Product-D"].category, "Others")
    check("CMC Must-Win → 유지", by_product["Product-B"].category, "CMC Must-Win")
    check("New indication → 유지", by_product["Product-E"].category, "New indication")
    check("NDA → 유지", by_product["Product-F"].category, "NDA")
    check("Site addition → 유지", by_product["Product-G"].category, "Site addition")
    check("리드타임은 원본 Category 기준 (CMC Must-Win=4개월)",
          by_product["Product-B"].lead_months, 4)


def test_prep_bar() -> None:
    section("7] 준비기간 계산")
    recs, _, _ = read_ra_plan(RA_PLAN, load_config())
    r = next(x for x in recs if x.product == "Product-B")
    # CMC Must-Win = 4개월, PRA Sub = 2025-12-23 → 준비 시작 2025-08-23
    check("Product-B PRA 준비 시작", r.pra_prep, date(2025, 8, 23))


def test_tint() -> None:
    section("8] 테마 색 tint 변환 (미리보기용)")
    check("tint 0 → 그대로", apply_tint("A5A5A5", 0.0), "A5A5A5")
    check("ARGB에서 알파 제거", apply_tint("FFD3D7DC", 0.0), "D3D7DC")
    check("tint>0 이면 밝아짐", apply_tint("4472C4", 0.8) > "4472C4", True)
    check("tint<0 이면 어두워짐", apply_tint("4472C4", -0.5) < "4472C4", True)


def test_generate() -> None:
    section("9] 내장 양식에 채우기 + 변경 감지")
    if not BUNDLED.exists():
        print(f"  ⚠️ 내장 양식이 없어 건너뜀: {BUNDLED}")
        return

    out = FIXTURES / "_out.xlsx"
    res = generate(RA_PLAN, out, BUNDLED)
    check("템플릿 모드", res["mode"], "template")
    check("날짜 있는 행 전부 기록", res["rows_written"], 8)  # 9건 중 Product-G는 날짜 없음
    check("빈 양식이므로 전부 신규", res["changes"]["summary"]["added"], 8)
    check("결과 파일 생성", out.exists(), True)
    check("미리보기 색상표 있음", len(res["palette_css"]) > 0, True)
    check("시트명이 날짜 스탬프", res["sheet"].isdigit(), True)

    # 방금 만든 결과를 이전본으로 주면 변경이 없어야 한다
    out2 = FIXTURES / "_out2.xlsx"
    res2 = generate(RA_PLAN, out2, out)
    check("재실행 시 신규 0건", res2["changes"]["summary"]["added"], 0)
    check("재실행 시 일정변경 0건", res2["changes"]["summary"]["moved"], 0)
    check("재실행 시 삭제 0건", res2["changes"]["summary"]["removed"], 0)

    for f in (out, out2):
        f.unlink(missing_ok=True)


def test_diff_and_sort() -> None:
    section("10] 변경 감지 · 정렬")
    cfg = load_config()
    recs, _, _ = read_ra_plan(RA_PLAN, cfg)
    usable = sort_records([r for r in recs if r.has_dates], cfg)

    previous = [r.to_dict() for r in usable[1:]]
    previous[0] = {**previous[0], "nda_sub": "2020-01-01"}

    d = diff_records(previous, usable)
    check("빠져 있던 1건이 신규", d["summary"]["added"], 1)
    check("날짜 바뀐 1건이 일정변동", d["summary"]["moved"], 1)
    check("행 신원은 제품+과제명",
          record_key(usable[0]),
          f"{usable[0].product.lower()}|{usable[0].project.lower()}")

    resp = [r.responsible for r in usable if r.responsible]
    check("담당자순 정렬됨", resp == sorted(resp), True)


def main() -> int:
    print("=" * 70)
    print(" hj_gantt 규칙 회귀 테스트")
    print("=" * 70)
    if not RA_PLAN.exists():
        print("\n픽스처가 없습니다:  python make_test_fixtures.py")
        return 2

    for fn in (test_date_parsing, test_add_months, test_ground_truth,
               test_pair_separation, test_responsible_column, test_category_remap,
               test_prep_bar, test_tint, test_generate, test_diff_and_sort):
        fn()

    print("\n" + "=" * 70)
    if failures:
        print(f" 실패 {len(failures)}건")
        for f in failures:
            print(f"   · {f}")
        print("\n → 규칙이 실제와 어긋났습니다. config.json을 확인하거나")
        print("   실물 파일로 `calibrate`를 돌려 역산하세요.")
        return 1
    print(" 전부 통과 ✅")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
