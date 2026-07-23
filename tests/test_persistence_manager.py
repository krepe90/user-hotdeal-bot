import json
import os
import tempfile

import pytest
import pytest_asyncio

from src import bot, crawler
from src.main import PersistenceManager


def generate_dummy_article(crawler_name: str, id_: int) -> crawler.BaseArticle:
    """테스트를 위한 더미 게시글 생성"""
    return crawler.BaseArticle(
        article_id=id_,
        title=f"Test Article {id_}",
        category="Test Category",
        site_name="Test Site",
        board_name="Test Board",
        writer_name="Test Writer",
        crawler_name=crawler_name,
        url=f"https://example.com/{id_}",
        is_end=False,
        extra={"price": "10000원", "delivery": "무료배송"},
    )


@pytest_asyncio.fixture
async def dummy_crawlers():
    """테스트용 더미 크롤러 딕셔너리"""
    crawlers = {
        "test_crawler_1": crawler.DummyCrawler("test_crawler_1", ["https://example.com"]),
        "test_crawler_2": crawler.DummyCrawler("test_crawler_2", ["https://example.com"]),
    }
    yield crawlers
    for crawler_instance in crawlers.values():
        await crawler_instance.close()


@pytest_asyncio.fixture
async def dummy_bots():
    """테스트용 더미 봇 딕셔너리"""
    bots = {
        "test_bot_1": bot.DummyBot("test_bot_1"),
        "test_bot_2": bot.DummyBot("test_bot_2"),
    }
    yield bots
    # Cleanup: 테스트 종료 시 모든 봇의 consumer task 정리
    for bot_instance in bots.values():
        await bot_instance.close()


@pytest_asyncio.fixture
async def article_cache():
    """테스트용 게시글 캐시"""
    return {
        "test_crawler_1": crawler.ArticleCollection(
            {i: generate_dummy_article("test_crawler_1", i) for i in range(1, 6)}
        ),
        "test_crawler_2": crawler.ArticleCollection(
            {i: generate_dummy_article("test_crawler_2", i) for i in range(10, 15)}
        ),
    }


@pytest_asyncio.fixture
async def persistence_manager():
    """PersistenceManager 인스턴스"""
    return PersistenceManager()


@pytest.mark.asyncio
async def test_dump_and_load_data(persistence_manager, article_cache, dummy_crawlers, dummy_bots):
    """데이터 덤프 및 로드 전체 흐름 테스트"""
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        dump_file_path = f.name

    new_crawlers = None
    new_bots = None
    try:
        # 봇에 테스트 메시지 추가
        test_article = generate_dummy_article("test_crawler_1", 1)
        await dummy_bots["test_bot_1"].set_msg_obj(test_article, "test_message_1")

        # 데이터 덤프
        await persistence_manager.dump_data(article_cache, dummy_bots, dump_file_path)

        # 파일이 생성되었는지 확인
        assert os.path.isfile(dump_file_path)

        # 새로운 봇과 크롤러로 데이터 로드
        new_crawlers = {
            "test_crawler_1": crawler.DummyCrawler("test_crawler_1", ["https://example.com"]),
            "test_crawler_2": crawler.DummyCrawler("test_crawler_2", ["https://example.com"]),
        }
        new_bots = {
            "test_bot_1": bot.DummyBot("test_bot_1"),
            "test_bot_2": bot.DummyBot("test_bot_2"),
        }

        loaded_cache = await persistence_manager.load_data(dump_file_path, new_crawlers, new_bots)

        # 로드된 데이터 검증
        assert len(loaded_cache) == 2
        assert "test_crawler_1" in loaded_cache
        assert "test_crawler_2" in loaded_cache
        assert len(loaded_cache["test_crawler_1"]) == 5
        assert len(loaded_cache["test_crawler_2"]) == 5

        # 게시글 내용 확인
        assert loaded_cache["test_crawler_1"][1]["title"] == "Test Article 1"
        assert loaded_cache["test_crawler_2"][10]["title"] == "Test Article 10"

        # 봇 캐시 확인
        assert "test_crawler_1" in new_bots["test_bot_1"].cache
        assert 1 in new_bots["test_bot_1"].cache["test_crawler_1"]

    finally:
        # 임시 파일 삭제
        if os.path.exists(dump_file_path):
            os.remove(dump_file_path)
        # 새로 생성한 크롤러들 정리
        if new_crawlers:
            for crawler_instance in new_crawlers.values():
                await crawler_instance.close()
        # 새로 생성한 봇들 정리
        if new_bots:
            for bot_instance in new_bots.values():
                await bot_instance.close()


@pytest.mark.asyncio
async def test_dump_data_creates_valid_json(persistence_manager, article_cache, dummy_bots):
    """덤프된 데이터가 유효한 JSON인지 확인"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        dump_file_path = f.name

    try:
        await persistence_manager.dump_data(article_cache, dummy_bots, dump_file_path)

        # JSON 파일 직접 읽기
        with open(dump_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 구조 검증
        assert "version" in data
        assert "crawler" in data
        assert "bot" in data
        assert "test_crawler_1" in data["crawler"]
        assert "test_crawler_2" in data["crawler"]
        assert "test_bot_1" in data["bot"]
        assert "test_bot_2" in data["bot"]

    finally:
        if os.path.exists(dump_file_path):
            os.remove(dump_file_path)


@pytest.mark.asyncio
async def test_load_data_with_missing_file(persistence_manager, dummy_crawlers, dummy_bots):
    """존재하지 않는 파일을 로드할 때 빈 캐시 반환 테스트"""
    non_existent_file = "/tmp/this_file_does_not_exist_12345.json"

    # 파일이 없는 상태에서 로드
    loaded_cache = await persistence_manager.load_data(non_existent_file, dummy_crawlers, dummy_bots)

    # 빈 ArticleCollection이 반환되어야 함
    assert len(loaded_cache) == 2
    assert len(loaded_cache["test_crawler_1"]) == 0
    assert len(loaded_cache["test_crawler_2"]) == 0


@pytest.mark.asyncio
async def test_load_data_with_invalid_json(persistence_manager, dummy_crawlers, dummy_bots):
    """잘못된 JSON 파일을 로드할 때 빈 캐시 반환 테스트"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("{ invalid json content }")
        invalid_json_file = f.name

    try:
        loaded_cache = await persistence_manager.load_data(invalid_json_file, dummy_crawlers, dummy_bots)

        # JSON 파싱 실패 시 빈 ArticleCollection 반환
        assert len(loaded_cache) == 2
        assert len(loaded_cache["test_crawler_1"]) == 0
        assert len(loaded_cache["test_crawler_2"]) == 0

    finally:
        if os.path.exists(invalid_json_file):
            os.remove(invalid_json_file)


@pytest.mark.asyncio
async def test_deserialize_articles(persistence_manager, dummy_crawlers):
    """게시글 역직렬화 테스트"""
    # 직렬화된 크롤러 데이터
    crawler_data = {
        "test_crawler_1": {
            "1": generate_dummy_article("test_crawler_1", 1),
            "2": generate_dummy_article("test_crawler_1", 2),
            "3": generate_dummy_article("test_crawler_1", 3),
        },
        "test_crawler_2": {
            "10": generate_dummy_article("test_crawler_2", 10),
            "11": generate_dummy_article("test_crawler_2", 11),
        },
    }

    result = await persistence_manager.deserialize_articles(crawler_data, dummy_crawlers)

    # 결과 검증
    assert len(result) == 2
    assert "test_crawler_1" in result
    assert "test_crawler_2" in result
    assert len(result["test_crawler_1"]) == 3
    assert len(result["test_crawler_2"]) == 2

    # ArticleCollection 타입 확인
    assert isinstance(result["test_crawler_1"], crawler.ArticleCollection)
    assert isinstance(result["test_crawler_2"], crawler.ArticleCollection)

    # 데이터 내용 확인
    assert result["test_crawler_1"][1]["title"] == "Test Article 1"
    assert result["test_crawler_2"][10]["title"] == "Test Article 10"


@pytest.mark.asyncio
async def test_deserialize_articles_with_unknown_crawler(persistence_manager, dummy_crawlers):
    """알 수 없는 크롤러가 포함된 데이터 역직렬화 테스트"""
    crawler_data = {
        "test_crawler_1": {
            "1": generate_dummy_article("test_crawler_1", 1),
        },
        "unknown_crawler": {
            "100": generate_dummy_article("unknown_crawler", 100),
        },
    }

    result = await persistence_manager.deserialize_articles(crawler_data, dummy_crawlers)

    # unknown_crawler도 로드되어야 하지만 경고 로그가 출력됨
    assert "test_crawler_1" in result
    assert "unknown_crawler" in result
    assert len(result["unknown_crawler"]) == 1


@pytest.mark.asyncio
async def test_deserialize_articles_initializes_missing_crawlers(persistence_manager, dummy_crawlers):
    """등록된 크롤러 중 데이터가 없는 경우 빈 ArticleCollection 초기화 테스트"""
    crawler_data = {
        "test_crawler_1": {
            "1": generate_dummy_article("test_crawler_1", 1),
        },
        # test_crawler_2는 데이터가 없음
    }

    result = await persistence_manager.deserialize_articles(crawler_data, dummy_crawlers)

    # test_crawler_2도 빈 ArticleCollection으로 초기화되어야 함
    assert "test_crawler_1" in result
    assert "test_crawler_2" in result
    assert len(result["test_crawler_1"]) == 1
    assert len(result["test_crawler_2"]) == 0


@pytest.mark.asyncio
async def test_deserialize_bots(persistence_manager, dummy_bots):
    """봇 역직렬화 테스트"""
    # 봇 데이터 준비
    test_article_1 = generate_dummy_article("test_crawler_1", 1)
    test_article_2 = generate_dummy_article("test_crawler_1", 2)

    await dummy_bots["test_bot_1"].set_msg_obj(test_article_1, "message_1")
    await dummy_bots["test_bot_1"].set_msg_obj(test_article_2, "message_2")

    # 직렬화
    bot_data = {
        "test_bot_1": await dummy_bots["test_bot_1"].to_dict(),
    }

    # 새 봇 인스턴스 생성
    new_bots = {
        "test_bot_1": bot.DummyBot("test_bot_1"),
        "test_bot_2": bot.DummyBot("test_bot_2"),
    }

    try:
        # 역직렬화
        await persistence_manager.deserialize_bots(bot_data, new_bots)

        # 결과 검증
        assert "test_crawler_1" in new_bots["test_bot_1"].cache
        assert 1 in new_bots["test_bot_1"].cache["test_crawler_1"]
        assert 2 in new_bots["test_bot_1"].cache["test_crawler_1"]
        assert new_bots["test_bot_1"].cache["test_crawler_1"][1] == "message_1"
        assert new_bots["test_bot_1"].cache["test_crawler_1"][2] == "message_2"
    finally:
        # cleanup
        for bot_instance in new_bots.values():
            await bot_instance.close()


@pytest.mark.asyncio
async def test_deserialize_bots_with_queue(persistence_manager, dummy_bots):
    """큐가 있는 봇 역직렬화 테스트"""
    # 봇 큐에 작업 추가
    test_article = generate_dummy_article("test_crawler_1", 1)
    await dummy_bots["test_bot_1"].queue.put(("send", test_article))

    # 직렬화
    bot_data = {
        "test_bot_1": await dummy_bots["test_bot_1"].to_dict(),
    }

    # 새 봇 인스턴스
    new_bots = {
        "test_bot_1": bot.DummyBot("test_bot_1"),
    }

    try:
        # 역직렬화
        await persistence_manager.deserialize_bots(bot_data, new_bots)

        # 큐 확인
        assert new_bots["test_bot_1"].queue.qsize() == 1
        action, article = await new_bots["test_bot_1"].queue.get()
        assert action == "send"
        assert article["article_id"] == 1
    finally:
        # cleanup
        for bot_instance in new_bots.values():
            await bot_instance.close()


@pytest.mark.asyncio
async def test_deserialize_bots_with_unknown_bot(persistence_manager):
    """알 수 없는 봇이 포함된 데이터 역직렬화 테스트"""
    bot_data = {
        "test_bot_1": {"queue": [], "cache": {}},
        "unknown_bot": {"queue": [], "cache": {}},
    }

    new_bots = {
        "test_bot_1": bot.DummyBot("test_bot_1"),
    }

    try:
        # unknown_bot은 경고 로그를 출력하지만 오류는 발생하지 않아야 함
        await persistence_manager.deserialize_bots(bot_data, new_bots)

        # test_bot_1은 정상적으로 처리되어야 함
        assert len(new_bots["test_bot_1"].cache) == 0
    finally:
        # cleanup
        for bot_instance in new_bots.values():
            await bot_instance.close()


@pytest.mark.asyncio
async def test_dump_data_with_complex_extra_field(persistence_manager, dummy_bots):
    """extra 필드에 복잡한 데이터가 있는 경우 덤프 테스트"""
    article_cache = {
        "test_crawler": crawler.ArticleCollection(
            {
                1: crawler.BaseArticle(
                    article_id=1,
                    title="Test",
                    category="Test",
                    site_name="Test",
                    board_name="Test",
                    writer_name="Test",
                    crawler_name="test_crawler",
                    url="https://example.com",
                    is_end=False,
                    extra={
                        "price": "10000원",
                        "delivery": "무료배송",
                        "direct_delivery": True,
                        "nested": {"key": "value"},
                        "list": [1, 2, 3],
                    },
                )
            }
        )
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        dump_file_path = f.name

    try:
        await persistence_manager.dump_data(article_cache, dummy_bots, dump_file_path)

        # JSON 파일 읽기
        with open(dump_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # extra 필드 검증
        article_data = data["crawler"]["test_crawler"]["1"]
        assert article_data["extra"]["price"] == "10000원"
        assert article_data["extra"]["direct_delivery"] is True
        assert article_data["extra"]["nested"]["key"] == "value"
        assert article_data["extra"]["list"] == [1, 2, 3]

    finally:
        if os.path.exists(dump_file_path):
            os.remove(dump_file_path)


@pytest.mark.asyncio
async def test_persistence_manager_roundtrip_preserves_data(persistence_manager, article_cache, dummy_crawlers):
    """덤프와 로드를 거쳐도 데이터가 보존되는지 테스트"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        dump_file_path = f.name

    # 테스트용 봇 생성
    dummy_bots = {
        "test_bot_1": bot.DummyBot("test_bot_1"),
        "test_bot_2": bot.DummyBot("test_bot_2"),
    }
    new_crawlers = None
    new_bots = None

    try:
        # 원본 데이터 저장
        original_article_1 = article_cache["test_crawler_1"][1]

        # 덤프
        await persistence_manager.dump_data(article_cache, dummy_bots, dump_file_path)

        # 로드
        new_crawlers = {
            "test_crawler_1": crawler.DummyCrawler("test_crawler_1", ["https://example.com"]),
            "test_crawler_2": crawler.DummyCrawler("test_crawler_2", ["https://example.com"]),
        }
        new_bots = {
            "test_bot_1": bot.DummyBot("test_bot_1"),
            "test_bot_2": bot.DummyBot("test_bot_2"),
        }
        loaded_cache = await persistence_manager.load_data(dump_file_path, new_crawlers, new_bots)

        # 데이터 비교
        loaded_article_1 = loaded_cache["test_crawler_1"][1]
        assert loaded_article_1["article_id"] == original_article_1["article_id"]
        assert loaded_article_1["title"] == original_article_1["title"]
        assert loaded_article_1["category"] == original_article_1["category"]
        assert loaded_article_1["url"] == original_article_1["url"]
        assert loaded_article_1["is_end"] == original_article_1["is_end"]
        assert loaded_article_1["extra"] == original_article_1["extra"]

    finally:
        # cleanup
        for bot_instance in dummy_bots.values():
            await bot_instance.close()
        if new_crawlers:
            for crawler_instance in new_crawlers.values():
                await crawler_instance.close()
        if new_bots:
            for bot_instance in new_bots.values():
                await bot_instance.close()
        if os.path.exists(dump_file_path):
            os.remove(dump_file_path)
