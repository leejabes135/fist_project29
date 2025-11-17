import os
import json
import requests
from dotenv import load_dotenv   # 추가

load_dotenv()

# ===== 1. 설정 =====
GITHUB_OWNER = "leejabes135"          # 깃허브 계정명
GITHUB_REPO = "fist_project29"        # 레포 이름

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # Slack Incoming Webhook URL

# 새 이벤트 체크용 (마지막으로 본 이벤트 ID를 저장할 파일)
LAST_EVENT_FILE = "last_event_id.txt"


def get_recent_events(per_page=20):
    """레포의 최근 이벤트 목록 가져오기"""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/events"
    headers = {
        "Accept": "application/vnd.github+json",
    }
    params = {"per_page": per_page}

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()  # 리스트(이벤트들)


def load_last_event_id():
    """마지막으로 처리한 이벤트 ID 읽기 (없으면 None)"""
    if not os.path.exists(LAST_EVENT_FILE):
        return None
    with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def save_last_event_id(event_id: str):
    """마지막 이벤트 ID 저장"""
    with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
        f.write(event_id)


def send_slack_message(text: str):
    """Slack Webhook으로 메시지 전송"""
    if not SLACK_WEBHOOK_URL:
        print("[경고] SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        return

    payload = {"text": text}
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if resp.status_code != 200:
        print("[슬랙 오류]", resp.status_code, resp.text)


def format_push_event(event: dict) -> str:
    repo = event["repo"]["name"]                     # owner/repo
    actor = event["actor"]["login"]
    payload = event.get("payload", {})
    ref = payload.get("ref", "")
    branch = ref.split("/")[-1] if ref else "알 수 없음"
    commits = payload.get("commits", [])
    commit_count = len(commits)

    text = (
        f"📦 GitHub Push 이벤트\n"
        f"• 저장소: {repo}\n"
        f"• 브랜치: {branch}\n"
        f"• 푸시한 사용자: {actor}\n"
        f"• 커밋 개수: {commit_count}\n"
    )
    return text


def format_pr_event(event: dict) -> str:
    repo = event["repo"]["name"]
    actor = event["actor"]["login"]
    payload = event.get("payload", {})
    action = payload.get("action", "unknown")
    pr = payload.get("pull_request", {})
    number = pr.get("number", "?")
    title = pr.get("title", "(제목 없음)")
    url = pr.get("html_url", "")

    text = (
        f"🔀 Pull Request 이벤트 ({action})\n"
        f"• 저장소: {repo}\n"
        f"• 번호: #{number}\n"
        f"• 제목: {title}\n"
        f"• 사용자: {actor}\n"
        f"• 링크: {url}\n"
    )
    return text


def format_issue_event(event: dict) -> str:
    repo = event["repo"]["name"]
    actor = event["actor"]["login"]
    payload = event.get("payload", {})
    action = payload.get("action", "unknown")
    issue = payload.get("issue", {})
    number = issue.get("number", "?")
    title = issue.get("title", "(제목 없음)")
    url = issue.get("html_url", "")

    text = (
        f"📌 Issue 이벤트 ({action})\n"
        f"• 저장소: {repo}\n"
        f"• 번호: #{number}\n"
        f"• 제목: {title}\n"
        f"• 사용자: {actor}\n"
        f"• 링크: {url}\n"
    )
    return text


def main():
    last_event_id = load_last_event_id()
    print("[INFO] 마지막 이벤트 ID:", last_event_id)

    events = get_recent_events(per_page=20)

    if not events:
        print("[INFO] 이벤트가 없습니다.")
        return

    # GitHub Events API는 "가장 최근 이벤트가 리스트의 첫 번째"에 옴.
    # 마지막으로 본 ID 이후의 새로운 이벤트만 보내고 싶으니까,
    # 먼저 역순으로 돌면서, 나중에 가장 최신 ID를 저장한다.
    new_events = []

    for ev in events:
        ev_id = ev.get("id")
        if last_event_id is not None and ev_id == last_event_id:
            # 여기까지가 이전에 본 이벤트, 그 앞쪽만 new
            break
        new_events.append(ev)

    if not new_events:
        print("[INFO] 새로운 이벤트가 없습니다.")
        return

    # 리스트를 뒤집어서 "오래된 것부터 순서대로" 보내기
    new_events.reverse()

    for ev in new_events:
        ev_type = ev.get("type")
        msg = None

        if ev_type == "PushEvent":
            msg = format_push_event(ev)
        elif ev_type == "PullRequestEvent":
            msg = format_pr_event(ev)
        elif ev_type == "IssuesEvent":
            msg = format_issue_event(ev)

        if msg:
            print("[INFO] Slack 전송:\n", msg)
            send_slack_message(msg)

    # 가장 최근 이벤트 ID 저장 (리스트 제일 앞 요소의 id)
    newest_id = events[0].get("id")
    if newest_id:
        save_last_event_id(newest_id)
        print("[INFO] 마지막 이벤트 ID 업데이트:", newest_id)


if __name__ == "__main__":
    main()
