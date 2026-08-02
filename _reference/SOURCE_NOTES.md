# 원본 파일 구조 실측 기록

> 이 문서는 **실물 파일에서 코드로 측정한 결과**다. 추측은 "가정"이라고 명시했다.
> 실물 파일 자체는 Internal Use라 저장소에 없다(`.gitignore`). 이 문서만 남긴다.
>
> 측정 대상: `★RA plan_202607 - 복사본.xlsx`, `RA plan_gantt chart_202607 - 복사본.xlsx`
> 측정일: 2026-08-02

---

## 1. RA plan (입력) — 시트 `RA plan`

| 항목 | 값 |
|---|---|
| 헤더 행 | **4행** |
| 데이터 시작 | 5행 |
| 총 행 | 1159 (실제 데이터 549건) |
| 그룹 제목 행 | 3행 (`K3:N3` = Pre-review, `O3:R3` = NDA or Variation) |

### 컬럼 배치

| 열 | 헤더 | 비고 |
|---|---|---|
| A | `Responsible\n~20260607` | **구(舊) 담당자** — 쓰지 않음 |
| B | `Responsible \n20260608~` | **현 담당자 — 이걸 쓴다** (실측 5/5 일치) |
| C | Product | 사본에서는 `AQ`, `AM`, `L` 등 코드로 익명화됨 |
| D | Category | 20종 (아래 참조) |
| E | Project | ⚠️ **사본에서는 전량 비어 있음** (공유 전 삭제됨) |
| F | Artwork impact | 미사용 |
| G | Status | |
| H | CP delivery | 미사용 |
| I | submission due date for safety update | 미사용 |
| J | implementation date for CMC variation | 미사용 |
| K~N | **Pre-review**: Planned Sub / Actual Sub / Planned App / Actual App | |
| O~R | **NDA or Variation (One step)**: Planned Sub / Actual Sub / Planned App / Actual App | |
| S | Note | 미사용 |
| T | VR link | 미사용 |

### Category 분포 (549건)

```
CMC 162 · Safety/Labelling 136 · Site addition 43 · Other 39
Overseas site registration 35 · Renewal 34 · NDA 26 · New indication 20
De-registration 8 · Device variation 6 · Labelling 6 · New device 5
Launch 5 · DMF 4 · IND 4 · Device GMP 4 · CMC Must-Win 4
ODD 3 · New posology 2 · NDA (Must-Win) 1
```

### 날짜 컬럼의 비(非)날짜 값 — 실측 상위

```
N/A 1508 · TBD 858 · TBU 39 · Not required 8 · done 2
2026-12 22 · 2028-03 18 · 2026 6 · 2026-04 4 · 2027-10 3 · 2027/01 2
2026-12-31\n(TBD) 8 · 2028-03-31\n(TBD) 7 · 2024-11-30\n2024-12-13 2
2022-9(E) 4 · 2023-3(E) 2 · 2024-2(E) 2 · 2022-12-07(W) 2 · 2025 Oct 2
```

→ 2행에 형식 안내가 있다: `TBD, YYYY nQ, YYYY-MM-DD (15)`.
즉 **분기 표기(`2026 3Q`)와 연-월 표기가 공식적으로 허용**된다. 일(day)이 없는
값은 "아직 확정 안 됨"의 의미이므로 확정 날짜와 구별해 다뤄야 한다.

---

## 2. 간트 차트 (출력 양식) — 시트 `20260708`

| 항목 | 값 |
|---|---|
| Note 행 | 1행 |
| 그룹 제목 행 | 2행 (`E2` = PRA, `G2` = NDA or variations, `J2~` = 연도) |
| 헤더 행 | **3행** |
| 데이터 시작 | 4행 |
| 데이터 행 | 219건 (날짜 있는 행) |

### 컬럼 배치

| 열 | 헤더 | 대응 (RA plan) |
|---|---|---|
| A | Responsible | B열 |
| B | Category | D열 (변환 후) |
| C | Product | C열 |
| D | Project | E열 |
| E | **PRA** Sub | K/L |
| F | **PRA** App | M/N |
| G | **NDA or variations** Sub | O/P |
| H | **NDA or variations** App | Q/R |
| I | Status | G열 (그대로) |
| J~BE | 월 그리드 | 48개월 = **2025-01 ~ 2028-12** |

> ⚠️ **가장 중요한 구조**: Sub/App이 **한 쌍이 아니라 두 쌍**이다.
> 스크린샷만 봤을 땐 한 쌍으로 오인했고, 그래서 "여덟 개 날짜 중 하나를 고르는
> 우선순위 규칙"이라는 존재하지도 않는 문제를 풀고 있었다. 실제로는 RA plan의
> 두 그룹이 간트의 두 쌍으로 **그대로 1:1 전달**된다.

### 이번 스냅샷의 특징

- PRA 쌍(E/F)은 **전량 비어 있음**. 219건 모두 NDA 쌍(G/H)만 사용.
- 바는 그리드 시작(2025-01)에서 **잘린다**. 예: r4는 Sub=2024-01-05인데 바가
  2025-01부터 시작 → 창(window) 밖은 그리지 않는다.

### Category 변환 (실측)

| 간트 표시값 | 건수 |
|---|---|
| Others | 135 |
| Site addition | 26 |
| New indication | 17 |
| NDA | 15 |
| NDA (variant) | 13 |
| CMC Must-Win | 11 |
| Device | 2 |

행 매칭 5건에서 확인: `CMC → Others`, `Safety/Labelling → Others`.
→ 지정된 몇 개만 남기고 **나머지는 전부 Others**로 접는다는 가설과 일치.

### Status 변환

`Completed → Completed`, `Planned → Planned` — **그대로 통과**.

---

## 3. 바 색상 규칙 (실측)

색상은 테마 색(theme index + tint)으로 들어 있다. RGB 하드코딩이 아니다.

### 색조(hue)는 **Category**가 정한다 — 상태가 아니다

| Category | 주 색조 | 일치율 |
|---|---|---|
| Others | theme **9** | 90% (759건) |
| NDA | theme **7** | 95% (238건) |
| NDA (variant) | theme **7** | 74% (116건) |
| Site addition | theme **6** | 100% (222건) |
| New indication | theme **6** | 100% (130건) |
| CMC Must-Win | theme **6** | 91% (87건) |

Product별·Responsible별로는 뚜렷한 상관이 없었다(주색 비중 40~50%대).
→ **색조 = Category**로 확정.

### 진하기(tint)가 준비/검토를 가른다

- 준비기간(제출 이전): tint **0.8** 계열 (연함)
- 검토기간(제출~승인): tint **0.4 ~ 0.6** 계열 (진함)

원본 간트 Note의 문구와 일치: *"연한 색은 preparation period, 진한 색은
review period 입니다."*

> ⚠️ 초기에 상태(Completed/Ongoing/…)별로 색이 갈린다고 가정했으나 **틀렸다**.
> 모든 상태에 theme6/7/9이 골고루 섞여 있었다.

---

## 4. 아직 확정되지 않은 것

| 항목 | 현재 처리 | 확정 방법 |
|---|---|---|
| 준비기간 리드타임(개월) | Category별 초안값 | 실제 간트의 연한 바 시작점을 Sub와 비교해 역산 (`calibrate`) |
| Planned vs Actual 선택 | Actual 우선, 없으면 Planned | 행 매칭 5건뿐이라 표본 부족 |
| `Device`, `NDA (variant)` 원본 Category | 미상 | RA plan의 `Device variation`/`New device`/`NDA (Must-Win)`에서 온 것으로 추정 |
| 분기 표기(`2026 3Q`) 해석 | 해당 분기 첫 달 1일 | 팀 확인 필요 |

---

## 5. 원본 스크린샷

`_reference/images/` (gitignore됨) — IMG_6766(RA plan), IMG_6767(간트).
스크린샷만으로 판독했을 때 생긴 오류 두 가지를 기록해 둔다:

1. **Sub/App을 한 쌍으로 오인** — 실제로는 PRA/NDA 두 쌍. 화면이 잘려 있었다.
2. **색상을 상태별로 오인** — 실제로는 Category별. 사진으로는 테마 색을 구분할 수 없다.

→ 교훈: 서식·색상이 규칙인 파일은 스크린샷으로 판독하면 안 된다. 실물 파일을
   받아 `openpyxl`로 직접 읽어야 한다.
