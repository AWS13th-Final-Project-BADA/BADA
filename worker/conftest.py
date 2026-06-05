"""worker 루트를 import 경로에 추가 — `pytest`만 쳐도 rules/providers/security 임포트되게."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
