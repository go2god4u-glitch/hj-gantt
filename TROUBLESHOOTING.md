# 증상별 진단

> 대부분은 `config.json` 한 줄로 해결됩니다. **코드를 고치기 전에 이 문서를 보세요.**
> 규칙의 근거는 [ARCHITECTURE.md](ARCHITECTURE.md)와
> [_reference/SOURCE_NOTES.md](_reference/SOURCE_NOTES.md)에 있습니다.

가장 먼저 할 일 — 엔진이 무엇을 어떻게 읽었는지 눈으로 봅니다.

```bash
./venv/bin/python gantt_engine.py inspect <RA_plan.xlsx>
```

---

## 1. "RA plan에서 헤더 행을 찾지 못했습니다"

| 원인 | 확인 | 조치 |
|---|---|---|
| 머리글 이름이 다름 | 헤더 행의 실제 글자 확인 | `config.json` → `column_aliases`에 그 이름 추가 |
| 헤더가 25행보다 아래 | 파일 상단 확인 | `detect_source_columns(..., scan_rows=50)` |
| 시트를 잘못 골랐음 | 시트 목록 확인 | CLI에 `-s "시트명"` |

별칭은 **포함 매칭**입니다. 실물의 `Responsible\n20260608~`처럼 개정일자가
붙어 있어도 `Responsible`만 등록돼 있으면 잡힙니다.

---

## 2. 담당자가 엉뚱하게 나온다

RA plan에는 Responsible 컬럼이 **둘**입니다 (구 담당자 A열 / 현 담당자 B열).

```json
"responsible_prefer_marker": "20260608"
```

이 문자열이 든 헤더를 씁니다. 담당자 개편이 또 일어나면 이 값만 새 날짜로 바꾸세요.
표식이 없으면 **가장 오른쪽** 컬럼을 씁니다(최신이라고 가정).

`inspect`가 이렇게 알려줍니다:

```
· Responsible 컬럼이 2개 → B열 사용 (제외: A)
```

담당자 칸에 `N/A`, `done` 같은 값이 적혀 있으면 빈칸으로 처리합니다
(`unresolved_tokens`).

---

## 3. 사전검토 일정이 본제출 칸에 들어갔다

**가장 흔한 큰 사고입니다.** Sub/App은 한 쌍이 아니라 **두 쌍**입니다.

- RA plan: `Pre-review (사전검토…)` K~N / `NDA or Variation` O~R
- 간트: `PRA` E,F / `NDA or variations` G,H

엔진은 헤더 **위쪽의 병합된 그룹 제목**으로 좌우를 가릅니다. 제목을 못 찾으면
"앞 4개=PRA, 뒤 4개=NDA" 순서로 넘어가고 이렇게 경고합니다:

```
· 그룹 제목을 못 찾아 '앞 4개=PRA, 뒤 4개=NDA'로 배정했습니다.
```

이 경고가 보이면 `config.json` → `group_titles`(RA plan 쪽),
`template_aliases.pra_group` / `nda_group`(간트 쪽)에 실제 제목 문구를 추가하세요.

---

## 4. 날짜가 비어 있다 / 이상한 날짜가 들어갔다

실물 날짜 칸에는 별의별 값이 들어 있습니다.

| 값 | 처리 |
|---|---|
| `N/A`, `TBD`, `TBU`, `Not required`, `done` | 미정 → `unresolved_tokens` |
| `2026-12`, `2027/01`, `2026`, `2026 3Q`, `2025 Oct` | **미확정 표기** — 해당 월/분기 1일로 읽되 `partial` 표시 |
| `2026-12-31\n(TBD)`, `2022-9(E)`, `2022-12-07(W)` | 괄호 주석 제거 후 판독 |
| `2024-11-30\n2024-12-13` | 첫 번째 날짜만 사용 |

`reject_partial_dates: true`면 일(日)이 없는 값은 "아직 확정 안 됨"으로 보고
같은 쌍의 다른 값(Actual↔Planned)을 먼저 씁니다.

> **근거**: 기준행(충전라인 신설)에서 NDA Planned가 `2027/01`인데 실제 간트는 Pre-review
> Planned인 `2026-08-31`을 적어 두었습니다. `2027/01`을 건너뛰어야 재현됩니다.

새로운 미정 표기가 나타나면 `unresolved_tokens`에 추가하세요.

---

## 5. 새 프로젝트가 간트에 안 나온다

| 원인 | 조치 |
|---|---|
| 날짜가 하나도 없음 | 정상입니다 — `records_skipped`에 잡힙니다. 제출일이 하나라도 있어야 그립니다 |
| 시트가 다름 | `-s` 로 시트 지정 |
| 그 행이 헤더보다 위 | 데이터는 헤더 행 아래에 있어야 합니다 |

화면의 **"날짜 없어 제외"** 숫자를 보세요. 실물 기준 549건 중 104건이 여기 해당합니다.

---

## 6. "NEW"가 전부 다 붙는다 / 변경 감지가 이상하다

변경 감지는 **제품명 + 과제명**으로 같은 건인지 판단합니다(행 번호가 아님 —
팀원이 중간에 행을 끼워 넣으면 밀리기 때문).

| 증상 | 원인 |
|---|---|
| 전부 NEW | 비교 대상 간트가 비어 있음. 내장 양식은 데이터가 없으니 첫 실행 때는 정상입니다 |
| 전부 NEW + 전부 removed | 과제명이 서로 다름. RA plan의 Project 컬럼이 비어 있는지 확인하세요 |
| 이름만 고쳤는데 NEW로 잡힘 | 의도된 동작입니다. 과제명이 신원이라 이름이 바뀌면 다른 건으로 봅니다 |

이전 간트와 비교하려면 웹의 "양식이 바뀌었나요?"에 **지난번 결과 파일**을
올리면 됩니다.

---

## 7. 바 색이 다르다

색은 **코드가 만들지 않습니다.** 다음 순서로 정해집니다.

1. 양식 파일에 바가 남아 있으면 → 거기서 Category별로 **배웁니다**
2. 없으면 → `config.json`의 `category_palette` (실물에서 추출해 구워둔 값)
3. 그것도 없으면 → `category_colors` → `status_colors` → 회색

색조(hue)는 **Category**가 정하고, 진하기(tint)가 준비/검토를 가릅니다.

| Category | 색조 | 실측 일치율 |
|---|---|---|
| Others | theme9 | 90% |
| NDA / NDA (variant) | theme7 | 95% / 74% |
| Site addition / New indication / CMC Must-Win | theme6 | 100% / 100% / 91% |

새 Category의 색을 넣으려면 `category_palette`에 추가하세요:

```json
"renewal": { "prep": {"theme": 5, "tint": 0.8}, "review": {"theme": 5, "tint": 0.4} }
```

> ⚠️ 상태(Completed/Ongoing…)별로 색이 갈린다고 **오해하기 쉽습니다.** 실측 결과
> 모든 상태에 theme6/7/9이 골고루 섞여 있었습니다. 색조는 Category입니다.

---

## 8. 미리보기 색과 엑셀 색이 다르다

미리보기는 엑셀의 테마 색(theme index + tint)을 RGB로 변환해 보여줍니다.
변환은 `apply_tint()` — HSL 명도에 tint를 적용하는 엑셀 규칙 그대로입니다.

양식의 테마가 Office 기본이 아니면 통합문서의 `theme1.xml`에서 실제 색을 읽습니다.
못 읽으면 Office 기본 테마로 근사하므로 미세한 차이가 날 수 있습니다.
**엑셀 파일 자체의 색은 항상 정확합니다** — 화면 근사값만 다를 수 있습니다.

---

## 9. 준비기간(연한 바) 길이가 실제와 다르다

`lead_months_by_category`는 **실측값이 아니라 규제 관행 기준 초안**입니다.
Category별로 "제출 몇 개월 전부터 준비하는가"를 넣습니다.

```json
"lead_months_by_category": { "NDA": 12, "New indication": 9, "CMC": 4, ... },
"default_lead_months": 3
```

리드타임은 **변환 후가 아니라 원본 Category** 기준으로 적용됩니다
(`CMC`는 간트에서 `Others`로 표시되지만 리드타임은 `CMC`의 4개월).

실제 간트에서 연한 바가 제출일 몇 개월 전에 시작하는지 재서 이 값을 교체하세요.

---

## 10. 양식 서식이 깨졌다

엔진은 원본 양식을 **복사한 뒤** 값만 채웁니다(`shutil.copyfile`). 원본은
절대 건드리지 않습니다. 그래도 깨졌다면:

| 원인 | 조치 |
|---|---|
| 데이터가 양식의 기존 행보다 많음 | 첫 데이터 행의 스타일을 복제해 씁니다. 첫 행 서식을 확인하세요 |
| 조건부 서식이 범위를 벗어남 | 엑셀에서 조건부 서식 적용 범위를 늘려 다시 양식을 뽑으세요 |
| 데이터 유효성 검사 경고 | openpyxl이 일부 확장을 버립니다. 결과에 영향은 없습니다 |

---

## 11. 서버가 안 뜬다 / 포트 충돌

macOS는 **5000번을 AirPlay(ControlCenter)가 씁니다.** 기본 포트를 5001로 뒀습니다.

```bash
PORT=5002 ./venv/bin/python app.py
```

---

## 12. 그래도 모르겠다 — 역산하세요

사람이 만든 실제 간트가 있으면 규칙을 추측할 필요가 없습니다.

```bash
./venv/bin/python gantt_engine.py calibrate <RA_plan.xlsx> <실제간트.xlsx>
```

간트의 각 날짜 컬럼이 RA plan의 어느 컬럼에서 왔는지 값 대조로 측정해
일치율(%)을 보여줍니다. 1위를 `config.json`에 옮기면 됩니다.

> RA plan의 Project 컬럼이 비워진 익명화 사본이면 행 단위 대조는 불가하고
> 값 집합 대조만 유효합니다.
