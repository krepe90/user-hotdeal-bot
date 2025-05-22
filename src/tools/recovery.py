# 일정 시간 이후로 봇이 비정상 중단된 이후, 밀린 핫딜 정보를 처리할 수 있도록 돕는 스크립트
# dump.json 파일을 읽은 다음, 사용자가 입력한 article_id 값보다 큰 핫딜 게시글을 제거하여 dump.json 파일 업데이트
# usage: python ./tools/recovery.py

import json


def recovery(dump_file_path: str = "dump.json"):
    # 1. dump.json 파일 읽기
    with open(dump_file_path, "r") as f:
        dump = json.load(f)

    # 2. 대화형으로 사용자에게 article_id값 입력받기
    crawlers = list(dump["crawler"].keys())
    for crawler_name in crawlers:
        print(f"{crawler_name} 작업 시작 (현재 {len(dump['crawler'][crawler_name])}개의 핫딜 게시글이 있습니다.")
        print("누락되지 않은 가장 마지막 핫딜 게시글의 article_id를 입력해주세요.")
        article_id = int(input("article_id: "))

        # 3. 입력받은 id값보다 큰 핫딜 게시글을 제거
        new_articles = {k: v for k, v in dump["crawler"][crawler_name].items() if v["article_id"] <= article_id}
        # 4. dump.json 파일에 반영
        dump["crawler"][crawler_name] = new_articles
        print(f"{crawler_name} 작업 완료")

    # 5. dump.json 파일에 반영된 내용 저장
    with open(dump_file_path, "w") as f:
        json.dump(dump, f, indent=2, ensure_ascii=False)



if __name__ == "__main__":
    recovery()
