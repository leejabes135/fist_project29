사전 작업 : slack의 봇 만들고 web hook url을 받기 / git hub 토큰 생성

# 1. 환경 변수 로드 및 기본 설정을 수행한다.

프로그램 시작 시 `.env` 파일을 읽어서 다음 값을 불러온다.

* `GITHUB_TOKEN`
* `GITHUB_OWNER`
* `GITHUB_REPO`
* `SLACK_WEBHOOK_URL`

이 값들은 GitHub API 인증 및 Slack Webhook 호출에 사용된다.

또한 `last_event_id.txt` 파일을 통해 **이전에 처리한 GitHub 이벤트 ID를 저장 및 로드**하도록 구성되어 있다.

---

# 2. 마지막 이벤트 ID를 파일로부터 읽거나, 파일이 없으면 None을 반환한다.

* 기존에 처리한 이벤트가 있으면 ID를 불러온다.
* 최초 실행 시에는 파일이 없으므로 None을 반환한다.

---

# 3. GitHub Events API를 호출하여 레포의 최근 이벤트 데이터를 가져온다.

요청 주소:

<pre class="overflow-visible!" data-start="655" data-end="713"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>https://api.github.com/repos/{owner}/{repo}/events
</span></span></code></div></div></pre>

헤더에 `Authorization: token {GITHUB_TOKEN}` 을 설정하여 인증을 수행한다.

가져오는 이벤트 개수는 기본 20개로 제한한다.

---

# 4. 기존에 처리한 이벤트 이후의 새로운 이벤트만 선별한다.

GitHub Events API는 **최신 이벤트가 리스트의 첫 번째 요소로 온다.**

따라서:

* 리스트를 앞에서부터 순회하면서
* `last_event_id`와 동일한 ID가 나오기 전까지의 이벤트를 "새로운 이벤트"로 판단한다.
* 동일한 ID가 나오면 루프를 종료한다.

이렇게 해서 중복 알림을 방지한다.

---

# 5. 새로운 이벤트 목록을 시간 순서대로 정렬한다.

새로운 이벤트들은 최신 순으로 수집되므로, 이를 `reverse()`하여

**오래된 이벤트 → 최신 이벤트 순**으로 Slack에 전송되도록 한다.

이로써 알림 순서가 뒤바뀌는 문제를 방지한다.

---

# 6. PushEvent와 PullRequestEvent만 처리한다.

이벤트 타입에 따라 다음 동작을 수행한다.

### ■ PushEvent

* 저장소 이름
* 브랜치 이름
* 푸시한 사용자

  등의 정보를 추출하여 Slack 메시지 텍스트로 구성한다.

### ■ PullRequestEvent

* action(opened/closed/synchronize 등)
* PR 번호
* 제목
* 작성자
* 링크

  등을 한국어 문장으로 구성하여 Slack 메시지를 생성한다.

그 외 이벤트는 모두 무시한다.

---

# 7. Slack Webhook URL로 메시지를 전송한다.

Slack은 다음 형식의 JSON을 수신한다.

<pre class="overflow-visible!" data-start="1555" data-end="1585"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>"text"</span><span>:</span><span></span><span>"메시지 내용"</span><span>}</span><span>
</span></span></code></div></div></pre>

성공 시 ✔ 메시지를 출력하고, 실패 시 경고 메시지를 출력하도록 구성되어 있다.

---

# 8. 처리한 이벤트 중 가장 최신 ID를 파일에 저장한다.

모든 새로운 이벤트를 처리한 후:

* `events[0].id` (가장 최신 이벤트 ID)를
* `last_event_id.txt`에 저장한다.

이를 통해 다음 실행 시 중복 알림이 발생하지 않도록 한다.

---

# 최종 요약

이 스크립트는 다음 흐름을 반복하여 수행한다:

1. 이전에 처리한 이벤트 ID를 로드한다.
2. GitHub Events API로 최근 이벤트 목록을 가져온다.
3. 이전 ID 이후에 발생한 새로운 이벤트만 선별한다.
4. PushEvent / PullRequestEvent만 처리하여 Slack에 통보한다.
5. 가장 최신 이벤트 ID를 저장 파일에 기록한다.
