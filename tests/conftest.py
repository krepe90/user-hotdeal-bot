"""pytest 설정 파일 - 테스트 환경 설정

이 파일은 pytest가 자동으로 로드하여 테스트 환경을 설정합니다.
TESTING 환경변수를 설정하여 src 모듈이 import될 때 logfire를 비활성화합니다.
"""

import logging
import os

import pytest

# IMPORTANT: src 모듈을 import하기 전에 환경변수 설정
# conftest.py는 pytest가 가장 먼저 로드하므로 여기서 설정하면 안전
os.environ["TESTING"] = "1"


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """테스트용 로깅 설정 - 최소한의 로그만 출력"""
    # 기본 로거를 WARNING 레벨로 설정
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(name)s - %(message)s")

    # 특정 로거들을 더 조용하게 설정
    logging.getLogger("bot").setLevel(logging.ERROR)
    logging.getLogger("crawler").setLevel(logging.ERROR)
    logging.getLogger("PersistenceManager").setLevel(logging.ERROR)

    yield
