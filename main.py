#이 main.py 파일은 하루에 한 번, 4개의 자동화 기능을 순서대로 실행하는 통합 스케줄러
#Google 캘린더 일정, 오늘 날씨, 보안 뉴스 RSS 요약, GitHub Push/PR 이벤트 4개를 slack으로 메시지가 가도록 기능을 구현
#각 모듈의 메인 함수를 안전하게 호출하면서, 오류가 발생해도 전체 프로그램이 중단되지 않도록 예외 처리
#이 네 가지 작업을 오전 9시에 호출하도록 설정하였고 schedule 라이브러리를 이용하여 스케줄링 작업을 실시했습니다.

#pip install schedule
import schedule
import time

import google_calendar_to_slack
import slack_weather
import python_rss
import github_evens_to_slack

def print_message():
    print("=== 통합 작업 시작 ===")

    print("\n>> [Step 1] 📅Google Calendar 작업 실행")
    try:
        # google_calendar_to_slack 모듈의 메인 함수를 호출합니다.
        google_calendar_to_slack.fetch_calendar_and_send_to_slack()
        print("   -> 캘린더 작업 완료")
    except Exception as e:
        print(f"   [오류] 캘린더 작업 실패: {e}")

    print("\n>> [Step 2] ⛅Weather 작업 실행")
    try:
        # slack_weather 모듈의 메인 함수(main)를 호출합니다.
        slack_weather.main() 
        print("   -> 날씨 작업 완료")
    except Exception as e:
        print(f"   [오류] 날씨 작업 실패: {e}")

    print("\n>> [Step 3] 📜보안 뉴스 rss 작업 실행")
    try:
        # python_rss 모듈의 rss_boannews 함수를 호출합니다.
        python_rss.rss_boannews()
        print("   -> 뉴스 작업 완료")
    except Exception as e:
        print(f"   [오류] 뉴스 작업 실패: {e}")

    print("\n>> [Step 4] 🐙깃허브 작업 실행")
    try:
        # github_evens_to_slack 모듈의 메인 함수(main)를 호출합니다.
        github_evens_to_slack.main()
        print("   -> 깃허브 작업 완료")
    except Exception as e:
        print(f"   [오류] 깃허브 작업 실패: {e}")

    print("\n=== 모든 작업이 종료되었습니다 ===")


# 매일 오전 8시 50분에 실행
# 실행 시간 런하실 때 1~2분 후로 바꿔주세요 
schedule.every().day.at("09:24").do(print_message)
#스케쥴만들거라객체 선언 / every.day -> 매일 /print_message 객체 do로 main의 함수(프로젝트 전체 모듈) 실행

while True:
    schedule.run_pending()
    time.sleep(1) #1초에 한 번씩 확인 / 지금 시각 기준으로 실행해야할 작업 확인 후 있으면 실행
    