# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
 hj_gantt 웹 앱 — 주소만 알려주면, 각자 올려서 각자 받아 간다
═══════════════════════════════════════════════════════════════════════════

쓰는 법
─────────────────────────────────────────────────────────────────────────
    ./run.sh                     (또는  python app.py)
    → 브라우저에서 http://127.0.0.1:5001

    ① RA plan 엑셀을 올린다
    ② 미리보기로 확인하고 내려받는다   (양식은 내장돼 있다)

무엇을 하는가
─────────────────────────────────────────────────────────────────────────
RA plan을 통째로 다시 읽어 **사용자 양식 그대로** 간트를 그린다. 색·글꼴·
열너비·병합은 양식에서 가져오고, 바 색상은 양식에 이미 칠해진 색을
Category별로 배워서 재사용한다 (색을 지어내지 않는다).

그리고 지난번 간트와 비교해 무엇이 달라졌는지 함께 보여준다 —
새로 생긴 프로젝트, 일정이 밀린 건, 상태가 바뀐 건, 사라진 건.
매니저가 실제로 알고 싶은 것이 그것이기 때문이다.

아무것도 남기지 않는다  ★ 여러 사람이 같은 주소를 쓰기 때문이다
─────────────────────────────────────────────────────────────────────────
이 앱은 주소를 공유해서 **여러 사람이 각자 쓰는** 물건이다. 그래서 서버에
파일을 일절 저장하지 않는다. 올라온 엑셀은 그 요청이 끝나기 전에 지워지고,
만들어진 간트는 응답에 실려 브라우저에서 곧바로 파일로 저장된다. 서버
디스크에 남는 것이 없으니 남의 결과물이 내게 섞이거나, 내 결과물이 남에게
새어 나갈 자리 자체가 없다.

같은 이유로 양식을 서버에 "기억"시키지 않는다. 양식을 올리면 그 요청
한 번에만 쓰이고 사라진다. 평소에는 내장 양식을 쓴다.

외부 API도 LLM도 호출하지 않는다. 다만 이 앱을 인터넷에 올려 두었다면
업로드 파일은 그 서버를 거쳐 간다 — 사내 자료라면 그 점을 감안할 것.
"""

from __future__ import annotations

import base64
import os
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

import gantt_engine as engine

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

# 4MB. 넉넉해서가 아니라 서버리스 요청 한도(약 4.5MB)보다 낮아야 해서 이 값이다.
# 한도를 넘기면 우리 코드에 닿기도 전에 플랫폼이 잘라 버려 사용자는 영문 모를
# 413만 본다. 우리가 먼저 걸러야 한국어로 이유를 말해 줄 수 있다.
# (참고: 실물 RA plan이 약 400KB이므로 열 배 이상 여유가 있다)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

ALLOWED = {".xlsx", ".xlsm"}
XLSX_MIME = ("application/vnd.openxmlformats-officedocument"
             ".spreadsheetml.sheet")


def bundled_template() -> Path | None:
    """프로젝트에 내장된 기본 간트 양식. 실물에서 서식만 남기고 값을 비운 파일."""
    rel = engine.load_config().get("bundled_template")
    if not rel:
        return None
    path = BASE_DIR / rel
    return path if path.exists() else None


def _stash(file_storage, workdir: Path, prefix: str) -> Path:
    """업로드 파일을 요청 전용 임시 폴더에 푼다. 폴더는 요청이 끝나면 통째로 사라진다."""
    name = secure_filename(file_storage.filename or "upload.xlsx")
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError(f"엑셀 파일(.xlsx/.xlsm)만 올릴 수 있습니다: {name}")
    path = workdir / f"{prefix}{ext}"
    file_storage.save(path)
    return path


def _month_span(span: list[str]) -> list[str]:
    """미리보기 타임라인의 월 목록. 양식의 범위를 그대로 따른다."""
    start = date.fromisoformat(span[0])
    end = date.fromisoformat(span[1])
    out, cur = [], start
    while cur <= end:
        out.append(cur.isoformat())
        cur = engine.add_months(cur, 1)
    return out


def _bars(rec: dict, months: list[str]) -> list[dict]:
    """
    미리보기용 바 좌표. 엑셀 채색과 같은 규칙으로 계산한다.

    반환은 월 인덱스 기준의 구간 목록이라 HTML에서 그리드로 바로 그릴 수 있다.
    """
    idx = {m: i for i, m in enumerate(months)}

    def to_i(iso: str | None) -> int | None:
        if not iso:
            return None
        d = date.fromisoformat(iso)
        return idx.get(date(d.year, d.month, 1).isoformat())

    out = []
    for phase in ("pra", "nda"):
        sub, app_, prep = rec.get(f"{phase}_sub"), rec.get(f"{phase}_app"), rec.get(f"{phase}_prep")
        if prep and sub:
            a, b = to_i(prep), to_i(sub)
            if a is not None or b is not None:
                a = a if a is not None else 0
                b = b if b is not None else len(months) - 1
                if b > a:
                    out.append({"kind": "prep", "phase": phase, "start": a, "len": b - a})
        if sub:
            a = to_i(sub)
            b = to_i(app_) if app_ else a
            if a is None and b is None:
                continue
            a = a if a is not None else 0
            b = b if b is not None else len(months) - 1
            if b >= a:
                out.append({"kind": "review", "phase": phase, "start": a, "len": b - a + 1})
    return out


def _payload(result: dict, out_path: Path, out_name: str,
             template_source: str) -> dict:
    """
    엔진 결과 → 브라우저가 바로 쓸 수 있는 응답.

    엑셀 실물을 base64로 함께 실어 보낸다. 서버에 남겨 두고 나중에 받아 가게
    하면 그 파일에 주소가 생기고, 주소가 생기면 남이 주워 갈 수 있다.
    한 번의 응답으로 끝내는 편이 안전하고 또 빠르다.
    """
    records = result.pop("records", [])
    months = _month_span(result["month_span"])

    added_keys = {f"{r['product'].lower()}|{r['project'].lower()}"
                  for r in result["changes"]["added"]}
    moved_keys = {f"{r['product'].lower()}|{r['project'].lower()}"
                  for r in result["changes"]["moved"]}

    rows = []
    for r in records:
        key = f"{(r['product'] or '').lower()}|{(r['project'] or '').lower()}"
        rows.append({
            **r,
            "bars": _bars(r, months),
            "is_new": key in added_keys,
            "is_moved": key in moved_keys,
        })

    result.update({
        "ok": True,
        "filename": out_name,
        "file_b64": base64.b64encode(out_path.read_bytes()).decode("ascii"),
        "mime": XLSX_MIME,
        "template_source": template_source,
        "months": months,
        "rows": rows,
    })
    return result


@app.errorhandler(413)
def too_large(_e):
    limit = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({
        "ok": False,
        "error": f"파일이 너무 큽니다 ({limit}MB 이하만 올릴 수 있습니다). "
                 "RA plan 시트만 남기고 다른 시트를 덜어내면 대개 줄어듭니다.",
    }), 413


@app.route("/")
def index():
    source = "내장 양식" if bundled_template() else None
    return render_template("index.html", template_source=source)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        ra_file = request.files.get("ra_plan")
        if not ra_file or not ra_file.filename:
            return jsonify({"ok": False, "error": "RA plan 엑셀 파일을 선택하세요."}), 400

        # 이 요청만의 작업대. with 블록을 벗어나는 순간 통째로 지워진다.
        with tempfile.TemporaryDirectory(prefix="hjgantt_") as tmp:
            workdir = Path(tmp)
            ra_path = _stash(ra_file, workdir, "raplan")

            # 양식은 내장돼 있다. 올릴 것은 RA plan 하나뿐.
            # (양식이 바뀌었을 때만 새로 올려 이번 한 번에 한해 갈아 쓴다)
            tpl_file = request.files.get("template")
            if tpl_file and tpl_file.filename:
                tpl_path = _stash(tpl_file, workdir, "template")
                template_source = f"이번에 올린 양식 ({secure_filename(tpl_file.filename)})"
            else:
                tpl_path = bundled_template()
                if tpl_path is None:
                    return jsonify({
                        "ok": False,
                        "error": "간트 양식을 찾을 수 없습니다. "
                                 f"{engine.load_config().get('bundled_template')} 파일이 "
                                 "있는지 확인하거나, 양식 파일을 직접 올려주세요."
                    }), 400
                template_source = "내장 양식"

            out_name = f"RA_gantt_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            out_path = workdir / out_name

            result = engine.generate(ra_path, out_path, tpl_path, engine.load_config())
            return jsonify(_payload(result, out_path, out_name, template_source))

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:                                  # noqa: BLE001
        return jsonify({
            "ok": False,
            "error": f"처리 중 오류: {e}",
            "trace": traceback.format_exc()[-1500:],
        }), 500


@app.route("/_selftest")
def selftest():
    """
    자가검증 — 내장 양식 + tests/fixtures 샘플로 한 바퀴 돌려 본다.

    /?selftest=1 로 열면 실제 업로드 없이 화면이 제대로 그려지는지 확인할 수
    있다. 업무 데이터가 필요 없으므로 처음 온 사람에게 보여주기에도 안전하다.
    """
    fixture = BASE_DIR / "tests" / "fixtures" / "sample_ra_plan.xlsx"
    if not fixture.exists():
        return jsonify({"ok": False,
                        "error": "픽스처가 없습니다. python make_test_fixtures.py 를 먼저 실행하세요."}), 400
    tpl = bundled_template()
    if tpl is None:
        return jsonify({"ok": False, "error": "간트 양식을 찾을 수 없습니다."}), 400

    with tempfile.TemporaryDirectory(prefix="hjgantt_") as tmp:
        out_name = f"selftest_{datetime.now():%H%M%S}.xlsx"
        out_path = Path(tmp) / out_name
        result = engine.generate(fixture, out_path, tpl, engine.load_config())
        payload = _payload(result, out_path, out_name,
                           "자가검증 (내장 양식 + 샘플 데이터)")
    for row in payload["rows"]:
        row["is_new"], row["is_moved"] = True, False
    return jsonify(payload)


@app.route("/config")
def config_endpoint():
    """
    규칙(config.json) 확인 — 읽기 전용.

    예전에는 여기로 규칙을 고쳐 넣을 수 있었다. 주소를 공유하는 순간 그건
    "아무나 모두의 규칙을 바꿀 수 있다"는 뜻이 되므로 쓰기를 닫았다.
    규칙을 고칠 일이 있으면 config.json을 직접 고쳐 다시 올린다.
    """
    return jsonify(engine.load_config())


if __name__ == "__main__":
    # macOS는 5000번을 AirPlay(ControlCenter)가 쓰고 있어 기본값을 5001로 둔다.
    port = int(os.environ.get("PORT", "5001"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"\n  hj_gantt  →  http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False)
