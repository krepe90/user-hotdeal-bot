# user-hotdeal-bot

한국 커뮤니티 유저 핫딜 알림 봇

## 주요 기능
한국 커뮤니티들의 유저 핫딜 게시판을 크롤링하여 텔레그램 등의 봇으로 알림

- 핫딜 종료, 제목 수정, 게시글 삭제 등 상태 변화 대응
- 나름 유연한 구조로 만들어 그럭저럭 괜찮은 확장성
- 열심히 배워서 그럴듯하게 적용한 로깅
- 기능은 아니지만, 추천인 광고 없을 예정

### 크롤링 대상 게시판
아래 게시판들을 약 1분 주기로 크롤링합니다. 같은 사이트, 동일한 구조의 게시판이라면 크롤러의 소스코드 수정 없이 URL만 바꾸어 사용할 수 있습니다. [(예시)](main.py#L53)

- [루리웹 - 유저 예판 핫딜 뽐뿌 게시판](https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=1): 썸네일 모드 사용
- [뽐뿌 - 뽐뿌 게시판](https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu)
- [뽐뿌 - 해외뽐뿌](https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu4)
- [클리앙 - 알뜰구매](https://www.clien.net/service/board/jirum)
- [쿨앤조이 - 지름, 알뜰정보](https://coolenjoy.net/bbs/jirum): RSS 사용 [(링크)](https://coolenjoy.net/rss?bo_table=jirum)
- [퀘이서존 - 지름/할인정보](https://quasarzone.com/bbs/qb_saleinfo): 모바일 페이지 사용
- [아카라이브 - 핫딜 채널](https://arca.live/b/hotdeal)


## Links
- [텔레그램 채널 (한국 커뮤니티 핫딜 모아보기)](https://t.me/hotdeal_kr)
- [패치로그](PATCHLOG.md)


## How to use
- Requirements:
  - Python>=3.11
  - aiohttp, beautifulsoup4, python-telegram-bot >= 20.1
- config
  - config.json
    - 현재는 텔레그램 봇의 토큰을 저장하는 용도로만 사용
      ```json
      {
        "telegram": {
          "token": "TELEGRAM_API_TOKEN",
          "target": "CHAT_ID_OR_CHANNEL_NAME"
        }
      }
      ```
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
5. (고민중) 메시지 전송이 실패한 경우, 다시 큐에 담는 것을 어떻게 구현할 지 생각해보기.


## TODO List

- [x] 메시지 객체 TypedDict 사용해서 정리
- [x] 전송/수정/삭제할 메시지 보관할때 dict 아닌 list 사용
- [x] 타입 힌팅 좀 더 엄격하게
- [x] 좀 더 비동기적으로 고치기
- [x] 로깅, 디버깅 강화
  - [x] 기본적인 프로그램 로그 (info+) -> 파일, 스트림
  - [x] 경고 이상의 주요 로그 (warning+) -> 텔레그램 메신저
- [x] [퀘이사존 지름/핫딜정보](https://quasarzone.com/bbs/qb_saleinfo) 추가
- [x] 게시글 캐시 덤프/로드 기능
- [x] 카테고리 정보 파싱 추가
- [ ] 크롤러, 봇 목록도 json으로부터 불러오기
- [ ] systemctl reload 시그널(아마도 `signal.SIG_HUP`) 대응
  - [ ] `BotManager.reload` 메소드 작성
- [ ] docstring 작성
- [ ] Telegram bot 메시지 전송도 비동기적인 코드로 전환 (PTB 말고 다른 패키지 사용도 고려)
- [ ] 개별 사이트 점검중일때의 대응 추가 (진행중)
- [ ] 게시글 추천수 보여주기 (진행중)
- [ ] **테스트 코드 작성**
- [ ] 도커 컨테이너화
