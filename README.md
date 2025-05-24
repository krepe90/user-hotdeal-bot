# user-hotdeal-bot

한국 커뮤니티 유저 핫딜 알림 봇

## 주요 기능
한국 커뮤니티들의 유저 핫딜 게시판을 크롤링하여 텔레그램 등의 봇으로 알림

- 핫딜 종료, 제목 수정, 게시글 삭제 등 상태 변화 대응
- 나름 유연한 구조로 만들어 그럭저럭 괜찮은 확장성

### 크롤링 방식 안내
1. 아래 게시판들에 대해 각각 **1분에 한번씩** 크롤링 작업을 실행합니다. [(참조)](main.py#L220) 각 작업마다 게시판 글 목록 1페이지에 한하여 **단 한번** 요청을 합니다. (즉 각 게시판마다 기본적으로 **1분에 1회의 요청**이 가해지게 됩니다.)
2. 작업 간격은 정확히 1분을 목표로 하고 있으나, 현재 구조 한계상 매 작업마다 수 ms정도의 지연이 누적되고 있는 듯 합니다.
3. 현재 본 봇은 오라클 클라우드의 서울 리전 무료 인스턴스에서 가동중입니다.
4. 같은 사이트, 동일한 구조의 게시판인 경우 크롤러 소스코드 수정 없이 URL만 변경하여 사용할 수 있습니다.


- [루리웹 - 유저 예판 핫딜 뽐뿌 게시판](https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=1)
  - 썸네일 모드를 사용합니다.
- [뽐뿌 - 뽐뿌 게시판](https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu)
  - RSS 크롤러가 구현되어 있으나, 사용하지 않습니다.
- [뽐뿌 - 해외뽐뿌](https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu4)
  - RSS 크롤러가 구현되어 있으나, 사용하지 않습니다.
- [클리앙 - 알뜰구매](https://www.clien.net/service/board/jirum)
- [쿨앤조이 - 지름, 알뜰정보](https://coolenjoy.net/bbs/jirum)
  - RSS 사용 [(링크)](https://coolenjoy.net/bbs/rss.php?bo_table=jirum)
- [퀘이사존 - 지름/할인정보](https://quasarzone.com/bbs/qb_saleinfo)
- [아카라이브 - 핫딜 채널](https://arca.live/b/hotdeal)
- [다모앙 - 알뜰구매 게시판](https://damoang.net/economy)
- [에펨코리아 - 핫딜 게시판](https://www.fmkorea.com/hotdeal)


## Links
- [텔레그램 채널 (한국 커뮤니티 핫딜 모아보기)](https://t.me/hotdeal_kr)
- [패치로그](PATCHLOG.md)


## How to use
- Requirements:
  - Python>=3.11
  - aiohttp, beautifulsoup4
  - python-telegram-bot >= 20.1
- Run
  - `uv run -m src.main` (권장)
  - `python -m src.main`
- config
  - config.json
    - 크롤러 및 메시지 전송 봇 목록 저장.
    - [config.json.example](/config.json.example) 파일 참조.
    - `crawler_name`, `bot_name` 에 적는 클래스 이름은 각각 [crawler](/crawler/__init__.py), [bot](/bot.py) 모듈에 임포트되어있어야 함.
  - config_logger.json
    - `logging.config.dictConfig()` 참조 [(로깅 요리책: Logging cookbook)](https://docs.python.org/ko/3/howto/logging-cookbook.html#customizing-handlers-with-dictconfig)
    - logger 종류
      - `root`: 루트 로거
      - `bot.BotClassName`: 크롤러 로거. 각 크롤러 클래스의 이름 사용됨.
      - `crawler.CrawlerClassName`: 봇 로거. 각 봇 클래스의 이름 사용됨.
      - `status`: 로그 레벨과 관계없이 텔레그램 핸들러로 메시지를 보내야 할 때 사용하려고 만든 특수 로거
    - handler
      - [util.TelegramHandler](util.py#L11): `logging.handlers.HTTPHandler`를 상속해 간단히 만든 텔레그램 핸들러


## 구현 방식

### 크롤링
1. 각 크롤러 객체로부터 `ArticleCollection` 객체를 반환받음.
2. 직전 크롤링 작업시 받아왔던 (또는 앱 시작 시 역직렬화 했던) `ArticleCollection` 객체와 비교
3. 이후 `new`, `update`, `delete` 세가지 종류로 변경사항을 분류하여 `CrawlingResult` 객체로 묶음.
4. 만료된 (더이상 추적하지 않는) 게시글들을 메모리에서 제거. 크롤러에서는 `BaseArticle` 객체를, 각 봇에서는 `MessageType` (각 봇 메시지 객체의 제네릭 타입) 제거.
5. `CrawlingResult` 객체를 한데 묶어서 반환.

### 메시지 전송/수정/삭제
1. 새로 올라온 게시글, 수정된 게시글, 삭제된 게시글의 리스트들을 받음. (`list[BaseArticle]`)
2. 봇 객체 `queue` 속성에 `tuple[str, BaseArcile]` 형태로 작업을 등록.
3. 봇 객체 생성시부터 작동을 시작한 `consumer` 메서드에서 큐로부터 작업을 받아 전송/수정/삭제 작업을 수행.
4. 각 작업은 상속받은 각 구현 봇 클래스의 `_send`, `_edit`, `_delete` 메서드를 호출해 수행.

## TODO List
### 중요도 높음
- [ ] docstring 작성
- [ ] 게시글 추천수 보여주기 (진행중)
- [ ] **테스트 코드 작성**
- [ ] 도커 컨테이너화
- [ ] util.TelegramHandler 도 비동기적 / 멀티스레드에서 메시지 보내게 하기
- [ ] Asyncio Lock 또는 유사한 기능 추가
- [ ] disabled: true 상태인 크롤러/봇도 초기화는 하도록 변경
  - [ ] 크롤러/봇에 disabled 상태 추가
  - [ ] disabled 상태인 크롤러 및 봇은 작동하지 않게 변경

### 중요도 낮음
- [ ] SQLite 사용
- [ ] (봇) 필터 기능 추가
- [ ] 일간 통계 기능 제공 등
- [ ] 실시간 봇 정보 모니터링 기능 추가 (텔레그램 메신저) - pid, 활성화된 크롤러 및 봇 목록, 최근 크롤러 상태 등
