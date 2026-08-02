# -*- coding: utf-8 -*-
"""
Vercel 진입점.

Vercel의 파이썬 런타임은 이 파일에서 `app`이라는 WSGI 객체를 찾는다.
실제 앱은 저장소 루트의 app.py 하나뿐이고, 여기서는 그것을 그대로 끌어다 쓴다.
로직을 여기 두지 않는 이유는 로컬(`./run.sh`)과 배포본이 **같은 코드**를
돌아야 하기 때문이다. 갈라지는 순간 "로컬에선 되는데"가 시작된다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402,F401
