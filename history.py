# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
 이력 저장 — "지난번 이후 무엇이 바뀌었나"를 답하기 위한 최소한의 기억
═══════════════════════════════════════════════════════════════════════════

왜 서버에 두는가
─────────────────────────────────────────────────────────────────────────
이 앱은 파일을 서버에 저장하지 않는다. 그 원칙은 그대로다. 다만 **이력**만은
서버에 둔다. 브라우저에 두면 기기를 바꾸는 순간 이력이 끊기고, 쓰는 사람이
여럿이 되면 각자 다른 기준선을 보게 되기 때문이다.

매니저가 알고 싶은 것은 "**내가** 마지막으로 본 이후"가 아니라 "**지난번
실행 이후**"다. 그래서 이력은 사람별로 나누지 않고 하나로 공유한다.
사용자 이름은 누가 돌렸는지 표시하는 라벨일 뿐, 이력을 가르지 않는다.

무엇을 저장하는가
─────────────────────────────────────────────────────────────────────────
비교에 필요한 것만 — 제품·과제명·날짜 4개·상태. 미리보기 전체(약 600B/건)가
아니라 그 1/5 수준이다. 담당자명은 저장하지 않는다. 최근 KEEP회분만 남기고
오래된 것은 지운다.

저장소가 없으면
─────────────────────────────────────────────────────────────────────────
환경변수가 없으면 모든 함수가 조용히 빈 값을 돌려주고 앱은 이력 기능만 빠진
채 그대로 동작한다. 저장소 연결이 앱의 전제조건이 되면 안 되기 때문이다.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

INDEX_KEY = "hjgantt:index"          # 실행 이력 메타(작다)
SNAP_KEY = "hjgantt:snap:"           # 실행별 행 스냅샷(크다) — 필요할 때만 읽는다
KEEP = 10                            # 보관할 실행 횟수
TIMEOUT = 6                          # 초. 이력 때문에 생성이 느려지면 안 된다

# 비교에 필요한 필드만. 담당자(responsible)는 일부러 뺐다.
# category가 있어야 하는 이유: 행 신원 키가 제품+과제명+유형이라 이게 빠지면
# 다음 실행에서 모든 행이 짝을 못 찾고 전부 '신규'로 잡힌다.
SNAP_FIELDS = ("product", "project", "category", "status",
               "pra_sub", "pra_app", "nda_sub", "nda_app")


def _creds() -> tuple[str, str] | None:
    """Upstash 접속 정보. 마켓플레이스가 넣어 주는 이름이 두 가지라 둘 다 본다."""
    for u, t in (("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),
                 ("KV_REST_API_URL", "KV_REST_API_TOKEN")):
        url, token = os.environ.get(u), os.environ.get(t)
        if url and token:
            return url.rstrip("/"), token
    return None


def enabled() -> bool:
    return _creds() is not None


def _cmd(*args) -> object | None:
    """
    Redis 명령 하나. 실패하면 None을 돌려주고 조용히 넘어간다.

    이력은 부가 기능이다. 저장소가 잠깐 죽었다고 간트 생성까지 실패하면
    본말이 전도된다. 그래서 여기서 나는 오류는 밖으로 던지지 않는다.
    """
    creds = _creds()
    if not creds:
        return None
    url, token = creds
    body = json.dumps([str(a) for a in args]).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return json.loads(res.read()).get("result")
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None


def _thin(rows: list[dict]) -> list[dict]:
    """미리보기 행 → 비교용 최소 행."""
    return [{k: r.get(k) for k in SNAP_FIELDS} for r in rows]


def load_index() -> list[dict]:
    """실행 이력 메타 목록. 최신이 앞."""
    raw = _cmd("GET", INDEX_KEY)
    if not raw:
        return []
    try:
        out = json.loads(raw)
        return out if isinstance(out, list) else []
    except ValueError:
        return []


def previous_rows() -> list[dict] | None:
    """
    가장 최근 실행의 행. 이번 결과와 비교할 기준선이다.

    None을 돌려주면 호출한 쪽은 '기준선 없음'으로 보고 엔진 기본 동작
    (양식에서 읽기)에 맡긴다. 빈 리스트와 구별해야 해서 None이다.
    """
    index = load_index()
    if not index:
        return None
    raw = _cmd("GET", SNAP_KEY + str(index[0].get("id")))
    if not raw:
        return None
    try:
        rows = json.loads(raw)
        return rows if isinstance(rows, list) else None
    except ValueError:
        return None


def record(user: str, filename: str, rows: list[dict],
           summary: dict) -> dict | None:
    """
    이번 실행을 이력에 남긴다. 실패해도 예외를 던지지 않는다.

    스냅샷과 메타를 따로 둔다. 메타만 읽으면 이력 목록을 그릴 수 있고,
    무거운 스냅샷은 비교할 때 한 개만 읽으면 되기 때문이다.
    """
    if not enabled():
        return None
    entry = {
        "id": uuid.uuid4().hex[:12],
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": user or "",
        "filename": filename or "",
        "count": len(rows),
        "summary": summary,
    }
    if _cmd("SET", SNAP_KEY + entry["id"],
            json.dumps(_thin(rows), ensure_ascii=False)) is None:
        return None

    index = [entry] + load_index()
    for old in index[KEEP:]:                       # 넘치는 것은 스냅샷까지 지운다
        _cmd("DEL", SNAP_KEY + str(old.get("id")))
    index = index[:KEEP]
    _cmd("SET", INDEX_KEY, json.dumps(index, ensure_ascii=False))
    return entry


def clear() -> bool:
    """이력 전체 삭제. 기준선을 리셋하고 싶을 때."""
    if not enabled():
        return False
    for e in load_index():
        _cmd("DEL", SNAP_KEY + str(e.get("id")))
    _cmd("DEL", INDEX_KEY)
    return True
