import requests
from bs4 import BeautifulSoup
import os
import time
import urllib.parse
from datetime import datetime
import random
import json
import re

# ==========================================
# 1. 설정 영역
# ==========================================
MY_CONSULTING_LINK = "https://kimjinholab.pages.dev/consult.html"
MY_HOME_LINK = "https://kimjinholab.pages.dev"
SAVE_DIR = "jobs_html"
HISTORY_FILE = "saved_history.txt"
TARGET_NEW_FILES = 30 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 2. DB 분할 저장 로직 (용량 최적화)
# ==========================================
def export_db_to_js():
    """db1.json, db2.json을 읽어서 js 파일 2개로 분할 저장"""
    data = []
    for db_file in ['db1.json', 'db2.json']:
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list): data.extend(content)
            except: pass
    
    if not data:
        data = ["(기본 데이터) 성장과정: 책임감...", "(기본 데이터) 지원동기: ..."]
    
    formatted_data = []
    for idx, item in enumerate(data):
        content = item if isinstance(item, str) else str(item)
        title = f"합격 데이터 #{idx+1}"
        if len(content) > 20: title = content[:20] + "..."
        formatted_data.append({"title": title, "content": content})
    
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    half_index = len(formatted_data) // 2
    part1 = formatted_data[:half_index]
    part2 = formatted_data[half_index:]

    with open(f"{SAVE_DIR}/db_data1.js", "w", encoding="utf-8") as f:
        f.write(f"const DB_PART_1 = {json.dumps(part1, ensure_ascii=False)};")
    with open(f"{SAVE_DIR}/db_data2.js", "w", encoding="utf-8") as f:
        f.write(f"const DB_PART_2 = {json.dumps(part2, ensure_ascii=False)};")
    
    print(f"✅ [시스템] DB 분할 완료: 총 {len(formatted_data)}건")

def extract_keywords_from_text(text):
    target_keywords = ["소통", "협력", "도전", "책임", "분석", "성실", "윤리", "고객", "안전", "혁신", "창의", "전문성", "리더십", "글로벌"]
    found = [word for word in target_keywords if word in text[:3000]]
    return found[:6] if found else ["소통", "책임", "도전"]

# ==========================================
# 3. [핵심] 챗봇이 탑재된 HTML 템플릿
# ==========================================
JOB_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{org_name} 합격 가이드 - 김진호 합격연구소</title>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
    
    <script src="db_data1.js"></script>
    <script src="db_data2.js"></script>

    <style>
        :root {{ --navy: #0f172a; --gold: #d4af37; --bg: #f8fafc; --text: #334155; --sidebar-w: 450px; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }}
        
        /* 레이아웃 */
        .sidebar {{ width: var(--sidebar-w); background: white; border-right: 1px solid #cbd5e1; display: flex; flex-direction: column; height: 100%; padding: 25px; z-index: 100; flex-shrink: 0; }}
        .main-content {{ flex: 1; padding: 40px; overflow-y: auto; position: relative; background: #f8fafc; }}

        /* 사이드바 스타일 */
        .home-link-btn {{ display: block; text-align: center; background: var(--navy); color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 700; margin-bottom: 20px; }}
        .db-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; cursor: pointer; transition: 0.2s; }}
        .db-card:hover {{ border-color: var(--gold); transform: translateY(-2px); }}
        
        /* 메인 콘텐츠 스타일 */
        .job-card {{ background: white; border-radius: 15px; padding: 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); max-width: 900px; margin: 0 auto; }}
        .job-title {{ font-size: 2rem; color: var(--navy); margin: 10px 0 20px 0; font-weight: 800; }}
        .keyword-chip {{ background: #f1f5f9; border: 1px solid #cbd5e1; padding: 8px 16px; border-radius: 50px; margin: 5px; display: inline-block; font-weight: 600; cursor: pointer; }}
        .keyword-chip:hover {{ background: var(--navy); color: white; }}
        .content-body {{ font-size: 0.95rem; line-height: 1.8; color: #334155; margin-top: 30px; }}

        /* ------------------------------------------------------- */
        /* [AI 챗봇 위젯 스타일] - 움직이는 창 & 호객 말풍선 */
        /* ------------------------------------------------------- */
        #chatbot-bubble {{
            position: fixed; bottom: 95px; right: 30px;
            background: white; padding: 10px 15px; border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #2563eb;
            font-size: 13px; font-weight: bold; color: #1e40af; z-index: 9998;
            animation: float 3s ease-in-out infinite; cursor: pointer;
        }}
        #chatbot-bubble::after {{ content: ''; position: absolute; bottom: -8px; right: 25px; border-width: 8px 8px 0; border-style: solid; border-color: #2563eb transparent transparent transparent; }}
        @keyframes float {{ 0% {{transform: translateY(0);}} 50% {{transform: translateY(-10px);}} 100% {{transform: translateY(0);}} }}

        #chatbot-floater {{
            position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px;
            background: linear-gradient(135deg, #2563eb, #1e40af);
            border-radius: 50%; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
            cursor: pointer; z-index: 9999; display: flex; align-items: center; justify-content: center;
            transition: transform 0.2s;
        }}
        #chatbot-floater:hover {{ transform: scale(1.1); }}
        #chatbot-floater span {{ font-size: 32px; }}

        #chatbot-window {{
            display: none; position: fixed; bottom: 100px; right: 30px;
            width: 360px; height: 520px; background: white;
            border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            z-index: 10000; flex-direction: column; border: 1px solid #e2e8f0;
            overflow: hidden; font-family: 'Pretendard', sans-serif;
        }}

        .chat-header {{
            background: #2563eb; color: white; padding: 15px; font-weight: bold;
            display: flex; justify-content: space-between; align-items: center;
            cursor: move; /* 드래그 커서 */
        }}
        
        #chat-messages {{ flex: 1; padding: 15px; overflow-y: auto; background: #f8fafc; display: flex; flex-direction: column; gap: 10px; }}
        .msg {{ max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; word-break: break-word; }}
        .msg-user {{ align-self: flex-end; background: #2563eb; color: white; border-bottom-right-radius: 2px; }}
        .msg-ai {{ align-self: flex-start; background: white; border: 1px solid #e2e8f0; color: #1e293b; border-bottom-left-radius: 2px; }}

        .chat-input-area {{ padding: 10px; border-top: 1px solid #e2e8f0; background: white; display: flex; gap: 5px; }}
        .chat-input-area input {{ flex: 1; padding: 12px; border: 1px solid #e2e8f0; border-radius: 20px; outline: none; }}
        .chat-input-area button {{ background: #2563eb; color: white; border: none; padding: 0 15px; border-radius: 20px; font-weight: bold; cursor: pointer; }}
        
        @media (max-width: 1024px) {{
            .sidebar {{ display: none; }}
            body {{ flex-direction: column; overflow: auto; }}
        }}
    </style>
</head>
<body>
    <div class="sidebar" id="mainSidebar">
        <a href="{home_link}" target="_blank" class="home-link-btn">🏠 홈으로 이동</a>
        <div style="font-weight:800; margin-bottom:10px;">📚 합격 데이터베이스</div>
        <div id="dbContainer" style="flex:1; overflow-y:auto;"></div>
    </div>

    <div class="main-content">
        <div class="job-card">
            <span style="background:var(--navy); color:white; padding:4px 10px; border-radius:10px; font-size:0.8rem;">채용공고</span>
            <h1 class="job-title">{title}</h1>
            <div style="color:#64748b; margin-bottom:20px;">기관명: <strong>{org_name}</strong> | 마감일: {end_date}</div>

            <div style="margin:20px 0;">
                <strong style="color:var(--navy);">✨ 핵심 키워드:</strong> {keyword_chips}
            </div>

            <div class="content-body">
                {content}
            </div>

            <div style="margin-top:50px; text-align:center; padding:30px; background:#f1f5f9; border-radius:10px;">
                <h3>"이 공고, 어떻게 써야 할지 막막하신가요?"</h3>
                <p>우측 하단 챗봇에게 물어보세요. AI가 이 공고를 분석해 드립니다.</p>
                <a href="{consult_link}" target="_blank" style="display:inline-block; margin-top:10px; background:var(--gold); color:white; padding:12px 25px; border-radius:30px; text-decoration:none; font-weight:bold;">⚡ 1:1 전문가 첨삭 신청</a>
            </div>
            
            <a href="{original_url}" target="_blank" style="display:block; text-align:center; margin-top:20px; color:#64748b; text-decoration:none;">📄 원문 공고 확인하기</a>
        </div>
    </div>

    <div id="chatbot-bubble" onclick="toggleChat()">
        자기소개서 무엇이든 물어보세요!! AI입니다.
    </div>

    <div id="chatbot-floater" onclick="toggleChat()">
        <span>🤖</span>
    </div>

    <div id="chatbot-window">
        <div class="chat-header" id="chatHeader">
            <div style="display:flex; align-items:center; gap:8px;">
                <span>🧠 {org_name} 전담 AI</span>
                <span style="font-size:10px; background:#10b981; padding:2px 6px; border-radius:10px;">ONLINE</span>
            </div>
            <div style="display:flex; gap:10px;">
                <span onclick="toggleChat()" style="cursor:pointer;">_</span>
                <span onclick="toggleChat()" style="cursor:pointer;">✕</span>
            </div>
        </div>
        <div id="chat-messages">
            <div class="msg msg-ai">
                안녕하세요! <strong>[{org_name}]</strong> 분석 AI입니다.<br>
                현재 보고 계신 공고 내용에 대해 무엇이든 물어봐 주세요.<br>
                (예: "이 직무 핵심 역량이 뭐야?")
            </div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="chatInput" placeholder="질문 입력..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">전송</button>
        </div>
    </div>

    <script>
        // DB 로드 및 사이드바 렌더링
        const part1 = typeof DB_PART_1 !== 'undefined' ? DB_PART_1 : [];
        const part2 = typeof DB_PART_2 !== 'undefined' ? DB_PART_2 : [];
        const dbData = part1.concat(part2);
        const dbContainer = document.getElementById('dbContainer');

        if(dbData.length > 0) {{
            dbContainer.innerHTML = dbData.slice(0, 15).map(item => `
                <div class="db-card" onclick="alert('데이터를 참고하여 자소서를 작성해보세요!')">
                    <div style="font-weight:bold; font-size:0.9rem;">${{item.title}}</div>
                    <div style="font-size:0.8rem; color:#666; margin-top:5px;">${{item.content.substring(0, 40)}}...</div>
                </div>
            `).join('');
        }} else {{
            dbContainer.innerHTML = "<div style='padding:10px;'>DB 로딩 중...</div>";
        }}

        // [챗봇 기능]
        function toggleChat() {{
            const win = document.getElementById('chatbot-window');
            const bubble = document.getElementById('chatbot-bubble');
            if (win.style.display === 'none' || win.style.display === '') {{
                win.style.display = 'flex';
                bubble.style.display = 'none';
                document.getElementById('chatInput').focus();
            }} else {{
                win.style.display = 'none';
                bubble.style.display = 'block';
            }}
        }}

        async function sendMsg() {{
            const input = document.getElementById('chatInput');
            const msg = input.value.trim();
            if (!msg) return;

            addBubble(msg, 'user');
            input.value = '';
            const loadingId = addBubble("📄 공고 분석 중...", 'ai');

            // [핵심] 현재 페이지의 제목과 본문을 긁어서 파이썬 서버로 전송
            const jobTitle = document.querySelector('.job-title').innerText;
            const jobContent = document.querySelector('.content-body').innerText.substring(0, 1000); // 길이 제한

            try {{
                const res = await fetch('http://127.0.0.1:5000/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ 
                        message: msg,
                        context: `[현재 공고 정보]\\n기업명: {org_name}\\n공고제목: ${{jobTitle}}\\n공고내용요약: ${{jobContent}}...`
                    }})
                }});
                const data = await res.json();
                document.getElementById(loadingId).remove();
                addBubble(data.response, 'ai');
            }} catch (err) {{
                document.getElementById(loadingId).innerText = "⚠ 서버 연결 실패 (app.py 실행 필요)";
            }}
        }}

        function addBubble(text, type) {{
            const box = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = `msg msg-${{type}}`;
            div.innerHTML = text.replace(/\\n/g, '<br>');
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
            return div.id;
        }}

        // [드래그 기능]
        dragElement(document.getElementById("chatbot-window"));
        function dragElement(elmnt) {{
            var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            if (document.getElementById("chatHeader")) {{
                document.getElementById("chatHeader").onmousedown = dragMouseDown;
            }}
            function dragMouseDown(e) {{
                e = e || window.event;
                e.preventDefault();
                pos3 = e.clientX;
                pos4 = e.clientY;
                document.onmouseup = closeDragElement;
                document.onmousemove = elementDrag;
            }}
            function elementDrag(e) {{
                e = e || window.event;
                e.preventDefault();
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
                elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
            }}
            function closeDragElement() {{
                document.onmouseup = null;
                document.onmousemove = null;
            }}
        }}
    </script>
</body>
</html>
"""

# ==========================================
# 4. 크롤링 및 파일 생성 로직
# ==========================================
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f: return f.read().splitlines()

def save_history(job_id):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f: f.write(job_id + "\n")

def get_job_urls_from_page(page_num):
    urls = []
    try:
        res = requests.get(f"https://job.alio.go.kr/recruit.do?pageNo={page_num}", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            if 'recruitview.do' in link['href'] and 'idx=' in link['href']:
                full_url = link['href'] if link['href'].startswith("http") else "https://job.alio.go.kr" + link['href']
                urls.append(full_url)
    except: pass
    return list(set(urls))

def create_job_page(url):
    try:
        parsed = urllib.parse.urlparse(url)
        job_id = urllib.parse.parse_qs(parsed.query)['idx'][0]
    except: return False
    
    if job_id in load_history(): return False

    print(f"🔄 [수집] ID: {job_id}...")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        try:
            org_name = soup.select_one('.topInfo h2').text.strip()
            title = soup.select_one('.titleH2').text.strip()
        except: return False
        
        safe_name = "".join([c for c in org_name if c.isalnum()])
        filename = f"{SAVE_DIR}/{job_id}_{safe_name}.html"
        
        if os.path.exists(filename): return False

        try:
            end_date = "별도 확인"
            for td in soup.select('td'):
                if "2025" in td.text or "2026" in td.text:
                    end_date = td.text.strip()
                    break
        except: end_date = "공고문 참조"

        content_html = soup.select_one('#tab-1')
        content = str(content_html) if content_html else "<p>상세 내용은 원문 참조</p>"
        content_text = content_html.text if content_html else ""

        keywords = extract_keywords_from_text(content_text)
        keyword_chips_html = ""
        for kw in keywords:
            keyword_chips_html += f'<span class="keyword-chip">#{kw}</span>'
        
        # [핵심] 템플릿에 데이터 주입 (챗봇 포함)
        html = JOB_TEMPLATE.format(
            org_name=org_name, title=title, end_date=end_date, content=content,
            consult_link=MY_CONSULTING_LINK, home_link=MY_HOME_LINK, 
            original_url=url, keyword_chips=keyword_chips_html
        )
        
        with open(filename, 'w', encoding='utf-8') as f: f.write(html)
        save_history(job_id)
        print(f"   ✅ 생성 완료: {filename}")
        return True

    except Exception as e:
        print(f"   ❌ 실패: {e}")
        return False

# ==========================================
# 5. 메인 실행 루프
# ==========================================
if __name__ == "__main__":
    print(f"🤖 김진호 합격연구소 로봇 가동 (목표: 신규 {TARGET_NEW_FILES}개)")
    
    # 1. DB 추출
    export_db_to_js()
    
    # 2. 크롤링
    new_files_count = 0
    page = 1
    
    while new_files_count < TARGET_NEW_FILES and page <= 20:
        print(f"\n📄 잡알리오 {page}페이지 스캔 중... (현재: {new_files_count}/{TARGET_NEW_FILES})")
        urls = get_job_urls_from_page(page)
        if not urls: break
        
        for url in urls:
            if new_files_count >= TARGET_NEW_FILES: break
            if create_job_page(url):
                new_files_count += 1
                time.sleep(1)
        page += 1
        time.sleep(1)
        
    # 3. 목록 페이지 갱신
    print("\n📋 jobs.html 목록 갱신 중...")
    if os.path.exists(SAVE_DIR):
        files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".html")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SAVE_DIR, x)), reverse=True)
        
        list_html = """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>채용공고 목록</title><link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet"><style>body{font-family:'Pretendard';padding:20px;background:#f8fafc;max-width:800px;margin:0 auto;} .card{background:white;padding:20px;margin-bottom:15px;border-radius:10px;border:1px solid #e2e8f0;display:block;text-decoration:none;color:#333;box-shadow:0 2px 5px rgba(0,0,0,0.05);} .card:hover{border-color:#d4af37;transform:translateY(-2px);} h3{margin:0 0 5px 0;color:#0f172a;} p{margin:0;color:#64748b;font-size:0.9rem;}</style></head><body><h1 style="text-align:center;color:#0f172a;">실시간 채용공고 & DB</h1>"""
        
        for f in files:
            name = f.replace(".html", "").split("_", 1)[1] if "_" in f else f
            list_html += f'<a href="{SAVE_DIR}/{f}" class="card" target="_blank"><h3>{name}</h3><p>합격 DB 분석 | 전문가 첨삭 가이드</p></a>'
        
        list_html += "</body></html>"
        with open("jobs.html", "w", encoding="utf-8") as f: f.write(list_html)

    print(f"\n🎉 작업 끝! 오늘 새로 만든 파일: {new_files_count}개")