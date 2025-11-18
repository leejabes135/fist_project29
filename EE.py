#제목 : 모닝 브리핑 자동화 알림 비서
#저희가 만든 프로젝트는 하루에 한 번, 4개의 자동화 기능을 순서대로 실행하는 통합 스케줄러 구현입니다.
#Google 캘린더 일정, 오늘 날씨, 보안 뉴스 RSS 요약, GitHub Push/PR 이벤트 4개를 slack으로 메시지가 가도록 기능을 구현
#구글 캘린더, 날씨, 뉴스 RSS, 깃허브 이 4개의 섹션들로 조원들을 나눠 작업했으며 각 파트를 맡은 조원분들이 나와서 발표해주실 겁니다. 첫 파트인 캘린더 파트 발표부터 진행하겠습니다. 

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ===== 환경 변수 =====
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "leejabes135")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "fist_project29")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 마지막으로 처리한 GitHub 이벤트 ID 저장용 파일
LAST_EVENT_FILE = "last_event_id.txt"

# ================== 공통 유틸 ==================
def load_last_event_id():
    """마지막으로 처리한 GitHub 이벤트 ID 읽기 (없으면 None)"""
    if not os.path.exists(LAST_EVENT_FILE):
        return None
    with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None #strip? -> 1234567890\n 처럼 줄바꿈 들어있는 경우 존
    
#👉 즉, “이전 실행에서 어디까지 처리했는지 기준점” 을 가져온뒤 그것을 기준으로 새로운 이벤트들을 추적할 수 있습니다. 

def save_last_event_id(event_id: str):
    """마지막으로 처리한 GitHub 이벤트 ID 저장 -> 다음 작업을 위한 기준점 정의"""
    with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
        f.write(event_id)

#가장 최신 이벤트 ID 하나를 파일에 쓰기 -> 스케줄러 실행 후 , 다음 스케줄러 실행 시 필요한 작업으로 
#다음 실행 때, “이 아이디 이후 것만 새 이벤트로 취급”하게 된다.

def send_slack_message(text: str):
    """슬랙 Webhook으로 메시지 전송"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL 이 없습니다. .env 확인 필요")
        return

    resp = requests.post(SLACK_WEBHOOK_URL, json={"text": text})
    if resp.status_code != 200:
        print("⚠️ 슬랙 전송 실패:", resp.status_code, resp.text)
    else:
        print("✅ 슬랙 전송 성공")
#슬랙으로 메시지 보내는 함수 
# .env에 SLACK_WEBHOOK_URL이 없으면 → 경고 출력 후 종료. 있으면 requests.post로 슬랙으로 {"text": text} JSON 보내기.
# 응답 코드가 200이면 성공, 아니면 실패 메시지 출력.

# ================== GitHub 이벤트 처리 ==================
def get_recent_repo_events(per_page=20): #20개인 이유? -> 몇 백개가 있을 수도 있으면 너무 알람 처리 힘드므로 새 이벤트 확인 목적으로만 20개만 적정히 설정 
    """
    GitHub 레포의 최근 이벤트를 GitHub Events API로 가져온다.
    """
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN 이 없습니다. .env 확인")

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/events"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    params = {"per_page": per_page} # 한 페이지에 20개 항목만

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status() # api 호출 오류 자동 추적 후 
    return resp.json() #성공한 경우에만 데이터 반환

#깃허브 토큰 없으면 에러 -> 깃허브 api의 엔드포인트 설정 (url) -> 헤더에 인증을 위한 것들 -> 한 페이지에 20개 항목만 -> 상태값 200아니면 예외처리 -> 200이면 resp.json()으로 이벤트 목록 반환

def format_push_event(event: dict) -> str: # event가 딕셔너리 형태다 라는 명시 그리고 '->str'은 문자열 반환을 할거다라는 명 -> IDE가 자동완성, 타입 체크할때 도움 
    """PushEvent를 사람이 보기 좋은 텍스트로 변환"""
    repo_full = event.get("repo", {}).get("name", f"{GITHUB_OWNER}/{GITHUB_REPO}")
    actor     = event.get("actor", {}).get("login", "알 수 없음")
    payload   = event.get("payload", {}) or {}
#자 모든 포맷 부분에서 공통적으로 등장하는 섹션들 -> 깃허브 이벤트 불러오면 json으로 나오는데 repo, actor 등의 key에 맞는 value를 가져오도록 하는 의미. 
    ref    = payload.get("ref", "") # PushEvent의 ref 값은 보통 깃허브의 디렉토리 위치 같은 것이며 이걸로 브랜치 명을 뽑는 
    branch = ref.split("/")[-1] if ref else "알 수 없음"
    #값을 / 기준으로 쪼개서 리스트로 만들어준다. refs/heads/main -> ["refs", "heads", "main"] 
    #[-1]은 **“마지막 요소


    # size 에 커밋 개수가 들어 있음. 없으면 commits 길이 사용
    commits      = payload.get("commits") or []
    commit_count = payload.get("size") or len(commits)

    text = (
        f"📦 GitHub Push 이벤트\n"
        f"• 저장소 : {repo_full}\n"
        f"• 브랜치 : {branch}\n"
        f"• 푸시한 사람 : {actor}\n"
    )
    return text
#푸시 이벤트를 위한 텍스트 양식


def format_pr_event(event: dict) -> str:
    """PullRequestEvent를 사람이 보기 좋은 텍스트로 변환"""
    repo_full = event.get("repo", {}).get("name", f"{GITHUB_OWNER}/{GITHUB_REPO}")
    actor     = event.get("actor", {}).get("login", "알 수 없음")
    payload   = event.get("payload", {}) or {}

    action = payload.get("action", "unknown")
    pr     = payload.get("pull_request", {}) or {} 
    #get(..., {}) 는 “키 없을 때”만 커버 #or {} 는 “키는 있는데 값이 None일 때”까지 커버

    number = pr.get("number", "?")
    title  = pr.get("title", "(제목 없음)")
    url    = pr.get("html_url", "")

    text = (
        f"🔀 Pull Request 이벤트 ({action})\n"
        f"• 저장소 : {repo_full}\n"
        f"• 번호   : #{number}\n"
        f"• 제목   : {title}\n"
        f"• 작성자 : {actor}\n"
        f"• 링크   : {url}\n"
    )
    return text

#풀리퀘스트를 위한 텍스트 양식 

def main():
    last_event_id = load_last_event_id()
    print(f"[INFO] 마지막 처리 이벤트 ID: {last_event_id}")
#이전 실행에서 이미 처리했던 마지막 이벤트 ID를 읽어온다. 없으면 None 출력.

    try:
        events = get_recent_repo_events(per_page=20)
    except Exception as e:
        print("⚠️ GitHub API 호출 실패:", e)
        return
#GitHub API에서 최신 이벤트 20개를 불러온다. 실패하면 에러 출력하고 함수 종료. 성공하면 “몇 개 가져왔는지” 출력.

    print(f"[INFO] 가져온 이벤트 개수: {len(events)}")

    if not events:
        print("[INFO] 이벤트가 없습니다.")
        return

    # 새 이벤트만 모으기
    new_events = []
    for ev in events:
        ev_id = ev.get("id")

        if last_event_id is not None and ev_id == last_event_id:
            # 여기까지가 이전에 처리했던 것, 그 앞쪽은 새 이벤트
            break

        new_events.append(ev)
    #여기가 핵심 로직이야. GitHub API는 가장 최신 이벤트가 리스트의 0번 인덱스에 있다. 쌓여있는 events를 앞에서부터 순회하면서 기준점이 되는, 이전 호출시의 아이디값인 last_event_id와 같은 ID를 만나면: break → 거기까지가 “이미 지난번에 처리했던 것”이므로 멈춘다.그 전까지는 모두 new_events에 담는다.

    if not new_events:
        print("[INFO] 새로운 이벤트가 없습니다.")
        return

    # 오래된 것부터 순서대로 보내려고 뒤집기 GitHub이 주는 events 리스트 자체가 “최신 → 오래된” 역순으로 정렬
    new_events.reverse()

    for ev in new_events:
        ev_type = ev.get("type")
        msg = None

        if ev_type == "PushEvent":
            msg = format_push_event(ev)
        elif ev_type == "PullRequestEvent":
            msg = format_pr_event(ev)
        else:
            # Push / PR 말고는 무시
            continue

        if msg:
            print("----- Slack 전송할 메시지 -----")
            print(msg)
            print("--------------------------------")
            send_slack_message(msg)
    #새 이벤트 중 Push/PR만 골라 슬랙 전송하는 명령 . NEWEVENTS에서 이벤트 하나씩 가져와서 종류를 꺼내 PUSH면 PUSH 포맷 함수로 가도록 하고, PR이면 PR 포맷 함수로 가게끔 하고 다른 이벤트는 무시하게 했다. 그렇게 MSG가 만들어지면 SLACK으로 전송되도록 설정 

    # 이번에 가져온 이벤트 중 가장 최신 ID 저장하여 다음 명령 실행을 이ㅜ한 기준점 
    newest_id = events[0].get("id")
    if newest_id:
        save_last_event_id(newest_id)
        print("[INFO] 마지막 이벤트 ID 업데이트:", newest_id)


if __name__ == "__main__": # 이 파일이 실행될 때만 main() 돌리기
    main()
