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
        return f.read().strip() or None


def save_last_event_id(event_id: str):
    """마지막으로 처리한 GitHub 이벤트 ID 저장"""
    with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
        f.write(event_id)


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


# ================== GitHub 이벤트 처리 ==================
def get_recent_repo_events(per_page=20):
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
    params = {"per_page": per_page}

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def format_push_event(event: dict) -> str:
    """PushEvent를 사람이 보기 좋은 텍스트로 변환"""
    repo_full = event.get("repo", {}).get("name", f"{GITHUB_OWNER}/{GITHUB_REPO}")
    actor     = event.get("actor", {}).get("login", "알 수 없음")
    payload   = event.get("payload", {}) or {}

    ref    = payload.get("ref", "")
    branch = ref.split("/")[-1] if ref else "알 수 없음"

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


def format_pr_event(event: dict) -> str:
    """PullRequestEvent를 사람이 보기 좋은 텍스트로 변환"""
    repo_full = event.get("repo", {}).get("name", f"{GITHUB_OWNER}/{GITHUB_REPO}")
    actor     = event.get("actor", {}).get("login", "알 수 없음")
    payload   = event.get("payload", {}) or {}

    action = payload.get("action", "unknown")
    pr     = payload.get("pull_request", {}) or {}

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


def main():
    last_event_id = load_last_event_id()
    print(f"[INFO] 마지막 처리 이벤트 ID: {last_event_id}")

    try:
        events = get_recent_repo_events(per_page=20)
    except Exception as e:
        print("⚠️ GitHub API 호출 실패:", e)
        return

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

    if not new_events:
        print("[INFO] 새로운 이벤트가 없습니다.")
        return

    # 오래된 것부터 순서대로 보내려고 뒤집기
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

    # 이번에 가져온 이벤트 중 가장 최신 ID 저장
    newest_id = events[0].get("id")
    if newest_id:
        save_last_event_id(newest_id)
        print("[INFO] 마지막 이벤트 ID 업데이트:", newest_id)


if __name__ == "__main__":
    main()
