import pytest

from src import crawler


def generate_dummy_article(id_: int) -> crawler.BaseArticle:
    """딕셔너리의 서브클래스인 ArticleCollection 클래스의 테스트를 위해 임의로 BaseArticle 객체(=딕셔너리)를 생성하는 함수"""
    return crawler.BaseArticle(
        article_id=id_,
        title=f"Dummy article {id_}",
        category="Dummy",
        site_name="Dummy Site",
        board_name="Dummy Board",
        writer_name="Dummy Writer",
        crawler_name="Dummy Crawler",
        url="https://example.com",
        is_end=False,
        extra={}
    )


def test_article_collection():
    """ArticleCollection 클래스 생성 테스트"""
    ac = crawler.ArticleCollection({i: generate_dummy_article(i) for i in range(1, 11)})
    assert len(ac) == 10


def test_article_collection_remove_expired():
    """ArticleCollection 클래스의 remove_expired 메서드 테스트"""
    ac = crawler.ArticleCollection({i: generate_dummy_article(i) for i in range(1, 11)})
    ac.remove_expired(5)    # 1,2,3,4 삭제
    assert len(ac) == 6


def test_article_collection_get_new():
    """ArticleCollection 클래스의 get_new 메서드 테스트
    
    get_new 메서드는 ArticleCollection 객체에서 i보다 같거나 큰 article_id를 가진 Article 객체들을 반환해야 함.
    """
    ac = crawler.ArticleCollection({i: generate_dummy_article(i) for i in range(1, 11)})
    new_ac = ac.get_new(5)
    assert len(new_ac) == 5


def test_article_collection_sub():
    """ArticleCollection 클래스의 __sub__ 메서드 테스트
    
    두 ArticleCollection 객체의 차집합을 반환해야 함.
    """
    ac1 = crawler.ArticleCollection({i: generate_dummy_article(i) for i in range(1, 6)})
    ac2 = crawler.ArticleCollection({i: generate_dummy_article(i) for i in range(1, 11)})
    sub_ac = ac2 - ac1  # 1,2,3,4,5 삭제
    assert len(sub_ac) == 5
    assert 5 not in sub_ac
