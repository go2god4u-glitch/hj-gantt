# hj_gantt

**RA plan 엑셀을 올리면 간트 차트 엑셀이 나옵니다.** 기존에 쓰던 양식 그대로.

팀원들은 RA plan에 일정을 적고, 매니저는 간트로 봅니다. 지금까지는 그 사이를
사람 손이 이었습니다 — 날짜가 바뀌면 셀을 다시 칠하고, 새 프로젝트가 생기면
간트에도 옮겨 적고, 개정할 때마다 탭을 복제했습니다. 이 도구가 그 손을 갈음합니다.

- 일정이 바뀌면 → 바가 따라 움직입니다
- 팀원이 새 프로젝트를 추가하면 → 간트에 그 행이 저절로 생깁니다
- RA plan에서 빠지면 → 간트에서도 사라집니다
- **무엇이 달라졌는지** 화면에 표시됩니다 (새 프로젝트 / 일정 변경 / 상태 변경 / 삭제)

LLM·외부 API를 쓰지 않습니다. 전부 코드로 처리하며 파일은 이 컴퓨터를 벗어나지 않습니다.

---

## 실행

```bash
./run.sh
```

브라우저에서 <http://127.0.0.1:5001> 을 열고 **RA plan 엑셀 하나만** 올리면 됩니다.
간트 양식은 프로젝트에 내장돼 있어 매번 올릴 필요가 없습니다.

미리보기에 나오는 바 색상은 **엑셀에 실제로 들어가는 색 그대로**입니다.
파일을 열지 않고도 결과를 확인할 수 있습니다.

### 명령줄로 쓰기

```bash
./venv/bin/python gantt_engine.py generate <RA_plan.xlsx> template/RA_gantt_template.xlsx -o 결과.xlsx
```

```bash
./venv/bin/python gantt_engine.py inspect <RA_plan.xlsx>
```

판독 결과만 확인합니다. 어느 컬럼을 어떻게 읽었는지, Sub/App을 어디서 가져왔는지 보여줍니다.

```bash
./venv/bin/python gantt_engine.py calibrate <RA_plan.xlsx> <실제간트.xlsx>
```

규칙이 실제와 맞는지 **역산**합니다. 자세한 내용은 아래 "규칙이 안 맞을 때".

---

## 어떻게 동작하나

```
RA plan.xlsx                    간트 양식(내장)              결과.xlsx
─────────────                  ──────────────              ──────────
 헤더 자동탐지        ┐                                    ┌ 서식 그대로
 PRA/NDA 그룹 분리    │                                    │ 색상 그대로
 날짜 판독            ├──▶  레코드  ──▶  양식에 채우기 ──▶ │ 날짜 스탬프 시트
 Category 변환        │                  + 바 칠하기       │ (20260802)
 준비/검토 구간 계산  ┘                                    └ 변경 내역
```

1. **판독** — RA plan의 헤더 행과 컬럼 위치를 자동으로 찾습니다. 컬럼 순서가
   바뀌거나 머리글에 개정일자가 붙어 있어도 찾습니다.
2. **정규화** — 제출일/승인일을 정하고, Category를 간트 표기로 바꾸고,
   준비기간(연한 바)의 시작점을 계산합니다.
3. **채우기** — 양식 파일을 복사한 뒤 값만 채웁니다. 색·글꼴·열너비·병합·
   틀고정은 손대지 않습니다.
4. **비교** — 이전 간트와 대조해 무엇이 달라졌는지 알려줍니다.

전량 재생성 방식입니다. 일부만 고쳐 넣지 않고 RA plan을 통째로 다시 읽습니다.
그래야 사람이 동기화를 신경 쓸 여지가 없어집니다.

---

## 규칙은 코드가 아니라 `config.json`에 있습니다

컬럼 이름, 날짜 우선순위, Category 변환, 리드타임, 색상 — 전부 `config.json`에
노출돼 있습니다. **코드를 고치지 마세요.** 예를 들어,

| 바꾸고 싶은 것 | 고칠 곳 |
|---|---|
| 담당자 컬럼이 또 바뀌었다 | `responsible_prefer_marker` |
| Category를 하나 더 살리고 싶다 | `category_passthrough` |
| 준비기간이 실제와 다르다 | `lead_months_by_category` |
| 간트 행 정렬 순서 | `sort_by` |
| `TBD` 말고 다른 미정 표기가 있다 | `unresolved_tokens` |
| 바 색상 | `category_palette` |

각 항목 옆에 `_..._note` 키로 **왜 그 값인지, 무엇으로 확인했는지** 적어 두었습니다.

---

## 규칙이 안 맞을 때

간트가 이상하면 추측하지 말고 **역산**하세요.

```bash
./venv/bin/python gantt_engine.py calibrate <RA_plan.xlsx> <사람이_만든_간트.xlsx>
```

간트의 각 날짜 컬럼이 RA plan의 어느 컬럼에서 왔는지를 값 대조로 측정해
일치율(%)을 보여줍니다. 1위로 나온 것을 `config.json`에 옮기면 됩니다.

증상별 진단은 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)를 보세요.

---

## 양식이 바뀌면

컬럼이 늘거나 기간이 바뀌면 새 양식에서 빈 양식을 다시 뽑습니다.

```bash
./venv/bin/python tools/make_blank_template.py <새간트.xlsx>
```

서식은 전부 남기고 데이터만 비운 파일이 `template/RA_gantt_template.xlsx`로
저장되고, 바 색상 팔레트가 `template/palette.json`으로 함께 나옵니다.
그 팔레트를 `config.json`의 `category_palette`에 넣으면 끝입니다.

웹 화면의 "양식이 바뀌었나요?"에서 직접 올려도 됩니다.

---

## 테스트

```bash
./venv/bin/python make_test_fixtures.py   # 가짜 샘플 파일 생성
./venv/bin/python tests/test_rules.py     # 규칙 회귀 테스트
```

테스트의 기대값은 **실물 간트에서 직접 읽은 값**입니다. `config.json`을 만지다가
테스트가 깨지면 테스트가 틀린 게 아니라 규칙이 실제와 어긋난 것입니다.

브라우저에서 <http://127.0.0.1:5001/?selftest=1> 을 열면 업무 파일 없이
샘플 데이터로 화면이 제대로 그려지는지 확인할 수 있습니다.

---

## 파일 안내

| 파일 | 하는 일 |
|---|---|
| `app.py` | 웹 화면 (업로드 → 미리보기 → 내려받기) |
| `gantt_engine.py` | 판독·변환·채우기 엔진. 여기에 모든 로직이 있습니다 |
| `config.json` | **모든 규칙.** 고칠 일이 있으면 여기부터 |
| `template/RA_gantt_template.xlsx` | 내장 간트 양식 (서식만, 데이터 없음) |
| `tools/make_blank_template.py` | 실물 간트 → 빈 양식 + 팔레트 추출 |
| `tests/test_rules.py` | 규칙 회귀 테스트 |
| `_reference/SOURCE_NOTES.md` | 실물 파일 구조 **실측 기록** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 시스템 해부 — 각 규칙의 근거 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 증상별 진단 |

---

## 데이터 취급

실제 RA plan·간트 파일은 저장소에 올라가지 않습니다 (`.gitignore`).
내장 양식은 실물에서 **서식만 남기고 값을 전부 비운** 파일이라 업무 내용이
들어 있지 않습니다 (헤더·월 이름·Note 문구 90셀뿐).

웹 앱은 `127.0.0.1`에서만 돌고 외부로 아무것도 보내지 않습니다.
