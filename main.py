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
# 2. [핵심] DB를 외부 JS 파일로 분리 저장
# ==========================================
def export_db_to_js():
    """db1.json, db2.json을 읽어서 jobs_html/db_data.js 파일로 내보냅니다."""
    data = []
    # 파일 읽기
    for db_file in ['db1.json', 'db2.json']:
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list): data.extend(content)
            except: pass
    
    # 샘플 데이터 (파일 없을 경우)
    if not data:
        data = ["성장과정: 책임감 없는 재능은 낭비라는 가훈 아래...", "지원동기: 귀사의 혁신적인 시스템은..."]
    
    formatted_data = []
    for idx, item in enumerate(data):
        content = item if isinstance(item, str) else str(item)
        title = f"합격 데이터 #{idx+1}"
        if len(content) > 20: title = content[:20] + "..."
        formatted_data.append({"title": title, "content": content})
    
    # 저장 폴더 확인
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    # JS 파일로 저장 (변수명: GLOBAL_DB_DATA)
    js_content = f"const GLOBAL_DB_DATA = {json.dumps(formatted_data, ensure_ascii=False)};"
    with open(f"{SAVE_DIR}/db_data.js", "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"✅ [용량 최적화] 합격 데이터 {len(formatted_data)}건을 'db_data.js'로 분리했습니다.")

def extract_keywords_from_text(text):
    target_keywords = ["소통", "협력", "도전", "책임", "분석", "성실", "윤리", "고객", "안전", "혁신", "창의", "전문성", "리더십", "글로벌", "신뢰", "배려", "팀워크", "문제해결", "계획"]
    found = [word for word in target_keywords if word in text[:3000]]
    return found[:6] if found else ["소통", "책임", "도전"]

# ==========================================
# 3. 템플릿 (데이터 제거 + JS 파일 연결)
# ==========================================
JOB_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{org_name} 합격 가이드 - 김진호 합격연구소</title>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
    
    <script src="db_data.js"></script>

    <style>
        :root {{ --navy: #0f172a; --gold: #d4af37; --bg: #f8fafc; --text: #334155; --sidebar-w: 450px; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }}
        
        .sidebar {{ width: var(--sidebar-w); background: white; border-right: 1px solid #cbd5e1; display: flex; flex-direction: column; height: 100%; padding: 25px; z-index: 100; flex-shrink: 0; }}
        .home-link-btn {{ display: block; text-align: center; background: var(--navy); color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 700; margin-bottom: 20px; transition:0.2s; }}
        .home-link-btn:hover {{ background: #1e293b; transform: translateY(-2px); }}
        .sidebar-header {{ font-weight: 800; font-size: 1.1rem; color: var(--navy); margin-bottom: 15px; border-bottom: 2px solid var(--gold); padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .reset-btn {{ font-size: 0.8rem; background: #e2e8f0; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; color: #64748b; }}
        
        .search-area {{ display: flex; gap: 5px; margin-bottom: 15px; }}
        .search-input {{ flex: 1; padding: 10px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; transition: 0.2s; }}
        .search-input:focus {{ border-color: var(--gold); outline: none; }}
        .search-btn {{ background: var(--navy); color: white; border: none; padding: 0 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }}

        .db-controls {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .nav-btn {{ background: #f1f5f9; color: #475569; border: none; padding: 5px 12px; border-radius: 6px; cursor: pointer; font-weight: 700; font-size:0.85rem; }}
        .db-status {{ font-size: 0.8rem; color: #64748b; font-weight: 600; }}

        .db-container {{ flex: 1; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; background: #fdfdfd; padding: 15px; margin-bottom: 15px; }}
        .db-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; cursor: pointer; transition: 0.2s; }}
        .db-card:hover {{ border-color: var(--gold); transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
        .db-tag {{ font-size: 0.75rem; background: #fffbe6; color: #b45309; padding: 2px 6px; border-radius: 4px; margin-bottom: 6px; display: inline-block; border: 1px solid var(--gold); }}
        .db-text {{ font-size: 0.9rem; line-height: 1.6; color: #334155; }}

        .editor-area {{ height: 25%; display: flex; flex-direction: column; border-top: 1px solid #e2e8f0; padding-top: 15px; }}
        textarea {{ width: 100%; flex: 1; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; font-family: inherit; line-height: 1.6; resize: none; background: #fff; font-size: 0.9rem; }}
        textarea:focus {{ outline: 2px solid var(--gold); }}

        .main-content {{ flex: 1; padding: 40px; overflow-y: auto; position: relative; background: #f8fafc; }}
        .header-nav {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .home-btn {{ text-decoration: none; font-weight: 700; color: #64748b; font-size: 1rem; }}

        .job-card {{ background: white; border-radius: 15px; padding: 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); max-width: 900px; margin: 0 auto; }}
        .status-badge {{ background: var(--navy); color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; }}
        .job-title {{ font-size: 2rem; color: var(--navy); margin: 10px 0 20px 0; font-weight: 800; }}
        
        .keyword-box {{ margin: 30px 0; background: white; padding: 25px; border-radius: 12px; border: 2px solid var(--navy); box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08); }}
        .keyword-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }}
        .keyword-title {{ font-size: 1.1rem; color: var(--navy); font-weight: 800; }}
        .keyword-desc {{ font-size: 0.9rem; color: #64748b; margin-left: auto; }}

        .keyword-interface {{ display: flex; flex-wrap: wrap; gap: 20px; align-items: start; }}
        .chip-container {{ flex: 2; display: flex; flex-wrap: wrap; gap: 8px; align-content: center; }}
        .keyword-chip {{ background: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; padding: 8px 16px; border-radius: 50px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: 0.2s; display: flex; align-items: center; gap: 5px; }}
        .keyword-chip:hover {{ background: var(--navy); color: white; border-color: var(--navy); transform: translateY(-2px); }}
        
        .search-group {{ flex: 1; display: flex; gap: 5px; min-width: 200px; }}
        .main-search-input {{ flex: 1; padding: 10px; border: 2px solid var(--gold); border-radius: 8px; font-size: 0.95rem; }}
        .main-search-input:focus {{ outline: none; box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2); }}
        .main-search-btn {{ background: var(--gold); color: var(--navy); border: none; padding: 0 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }}

        .consult-box {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 40px 0; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.2); }}
        .consult-btn {{ display: inline-block; background: var(--gold); color: var(--navy); padding: 15px 40px; border-radius: 50px; font-weight: 800; font-size: 1.1rem; text-decoration: none; margin-top: 20px; transition: 0.3s; }}
        .consult-btn:hover {{ transform: scale(1.05); background: white; }}

        .origin-link {{ display: block; text-align: center; background: #e2e8f0; color: #475569; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: 700; margin-bottom: 40px; transition:0.2s; }}
        .origin-link:hover {{ background: #cbd5e1; color: var(--navy); }}
        .content-body {{ font-size: 0.95rem; line-height: 1.8; color: #334155; margin-top: 30px; }}

        @media (max-width: 1024px) {{
            body {{ flex-direction: column; overflow: auto; }}
            .sidebar {{ display: none; }} 
            .keyword-interface {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <div class="sidebar" id="mainSidebar">
        <a href="{home_link}" target="_blank" class="home-link-btn">🏠 김진호 합격연구소 공식 홈 (새창)</a>
        <div class="sidebar-header">
            <span>📚 합격 데이터베이스</span>
            <button class="reset-btn" onclick="renderSingle(0)">초기화</button>
        </div>
        <div class="search-area">
            <input type="text" id="dbSearchInput" class="search-input" placeholder="키워드 검색 (예: 소통)" onkeypress="handleEnter(event)">
            <button class="search-btn" onclick="searchFromInput()">🔍</button>
        </div>
        <div class="db-controls">
            <button class="nav-btn" onclick="moveDB(-1)">◀</button>
            <span class="db-status" id="dbStatus">로딩중...</span>
            <button class="nav-btn" onclick="moveDB(1)">▶</button>
        </div>
        <div class="db-container" id="dbContainer"></div>
        <div class="editor-area">
            <div style="font-weight:700; color:var(--navy); margin-bottom:10px;">📝 전문가 따라잡기 (연습장)</div>
            <textarea id="userEditor" placeholder="합격 데이터를 클릭하면 복사됩니다. 본문의 단어를 드래그해도 검색됩니다."></textarea>
        </div>
    </div>

    <div class="main-content" id="mainContentArea">
        <div class="header-nav">
            <a href="../jobs.html" class="home-btn">≡ 전체 채용 목록</a>
            <a href="{consult_link}" target="_blank" style="color:var(--gold); font-weight:bold; text-decoration:none;">1:1 첨삭 문의 (새창)</a>
        </div>
        <div class="job-card">
            <span class="status-badge">접수중</span>
            <h1 class="job-title">{title}</h1>
            <div style="color:#64748b; margin-bottom:20px;">기관명: <strong>{org_name}</strong> | 마감일: {end_date}</div>

            <div class="keyword-box">
                <div class="keyword-header">
                    <span style="font-size:1.5rem;">📊</span>
                    <span class="keyword-title">이 공고의 핵심 역량 키워드</span>
                    <span class="keyword-desc">클릭 또는 검색하여 합격 DB 확인</span>
                </div>
                <div class="keyword-interface">
                    <div class="chip-container">{keyword_chips}</div>
                    <div class="search-group">
                        <input type="text" id="mainSearchInput" class="main-search-input" placeholder="키워드 입력" onkeypress="handleEnter(event)">
                        <button class="main-search-btn" onclick="manualSearch()">검색</button>
                    </div>
                </div>
            </div>

            <div class="content-body">{content}</div>
            <div class="consult-box">
                <h2 style="margin:0 0 10px 0;">"검증된 데이터가 합격을 만듭니다."</h2>
                <p style="opacity:0.9; font-size:1rem;">왼쪽의 합격 사례들처럼, 당신의 경험도 합격의 언어로 바뀔 수 있습니다.<br><strong>김진호 소장</strong>이 직접 당신의 합격 구조를 설계해 드립니다.</p>
                <a href="{consult_link}" target="_blank" class="consult-btn">⚡ 1:1 첨삭 상담 (새창)</a>
            </div>
            <a href="{original_url}" target="_blank" class="origin-link">📄 공식 공고문 및 양식 확인 (잡알리오 이동)</a>
        </div>
    </div>

    <script>
        // [핵심] 이제 무거운 데이터가 아니라, 외부 파일(db_data.js)에서 변수를 가져옵니다.
        // 만약 로드가 안 됐을 경우를 대비해 빈 배열 처리
        const dbData = typeof GLOBAL_DB_DATA !== 'undefined' ? GLOBAL_DB_DATA : [];
        
        const dbContainer = document.getElementById('dbContainer');
        const dbStatus = document.getElementById('dbStatus');
        const editor = document.getElementById('userEditor');
        const mainInput = document.getElementById('mainSearchInput');
        const sideInput = document.getElementById('dbSearchInput');
        let currentIndex = 0;

        function renderSingle(index) {{
            if (!dbData.length) {{
                dbStatus.innerText = "데이터 로드 실패";
                return;
            }}
            if (index < 0) index = dbData.length - 1;
            if (index >= dbData.length) index = 0;
            currentIndex = index;

            const item = dbData[currentIndex];
            dbContainer.innerHTML = `
                <div class="db-card" onclick="copyToEditor(this)">
                    <span class="db-tag">랜덤 추천 DB</span>
                    <div class="db-text" style="font-weight:bold; margin-bottom:5px;">${{item.title}}</div>
                    <div class="db-text db-content-text">${{item.content}}</div>
                </div>
            `;
            dbStatus.innerText = `데이터 ${{currentIndex + 1}} / ${{dbData.length}}`;
            sideInput.value = ''; 
        }}

        function executeSearch(keyword) {{
            if (!keyword) return;
            mainInput.value = keyword;
            sideInput.value = keyword;
            const results = dbData.filter(item => item.content.includes(keyword) || item.title.includes(keyword));
            
            if (results.length > 0) {{
                dbStatus.innerHTML = `<span>'${{keyword}}'</span>: ${{results.length}}건`;
                let html = `<div style="padding:10px; font-weight:bold; color:#0f172a; border-bottom:1px solid #e2e8f0; margin-bottom:10px;">🔍 '${{keyword}}' 검색결과</div>`;
                results.forEach(item => {{
                    let content = item.content.replace(new RegExp(keyword, 'gi'), match => `<span style="background:#fffbe6; font-weight:bold;">${{match}}</span>`);
                    html += `
                        <div class="db-card" onclick="copyToEditor(this)">
                            <span class="db-tag" style="background:#fffbe6; color:#b45309;">${{keyword}} 매칭</span>
                            <div class="db-text db-content-text" style="display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden;">${{content}}</div>
                        </div>
                    `;
                }});
                dbContainer.innerHTML = html;
            }} else {{
                alert(`'${{keyword}}' 관련 데이터가 없습니다.`);
                mainInput.focus();
            }}
        }}

        function manualSearch() {{ executeSearch(mainInput.value); }}
        function searchFromInput() {{ executeSearch(sideInput.value); }}
        function handleEnter(e) {{ if (e.key === 'Enter') e.target === mainInput ? manualSearch() : searchFromInput(); }}
        function moveDB(dir) {{ renderSingle(currentIndex + dir); }}
        
        document.getElementById('mainContentArea').addEventListener('mouseup', function() {{
            const txt = window.getSelection().toString().trim();
            if (txt.length > 1 && txt.length < 10) executeSearch(txt);
        }});

        function copyToEditor(el) {{
            const text = el.querySelector('.db-content-text').innerText;
            editor.value = "[참고 DB]\\n" + text + "\\n\\n------------------\\n" + editor.value;
            el.style.borderColor = '#d4af37';
            setTimeout(() => el.style.borderColor = '#e2e8f0', 300);
        }}

        // 실행 (0.5초 딜레이 - JS 로드 시간 고려)
        setTimeout(() => renderSingle(0), 100);
    </script>
</body>
</html>
"""

# ==========================================
# 4. 실행 로직 (JS 생성 -> 페이지 생성)
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
    
    # 히스토리 체크 (중복 생성 방지)
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
        
        # 파일 존재 시 패스
        if os.path.exists(filename): return False

        try:
            end_date = "별도 확인"
            for td in soup.select('td'):
                if "2025" in td.text or "2026" in td.text:
                    end_date = td.text.strip()
                    break
        except: end_date = "공고문 참조"

        content_html = soup.select_one('#tab-1')
        content_text = content_html.text if content_html else ""
        content = str(content_html) if content_html else "<p>상세 내용은 원문 참조</p>"

        # 키워드 배지 생성
        keywords = extract_keywords_from_text(content_text)
        keyword_chips_html = ""
        for kw in keywords:
            keyword_chips_html += f'<button class="keyword-chip" onclick="executeSearch(\'{kw}\')"><span class="chip-check">✔</span> {kw}</button>'
        
        # [수정] DB 데이터를 직접 넣지 않고 템플릿만 사용
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

# 메인 실행
if __name__ == "__main__":
    print(f"🤖 김진호 합격연구소 로봇 가동 (목표: 신규 {TARGET_NEW_FILES}개)")
    
    # 1. DB 데이터를 별도 JS 파일로 추출 (용량 다이어트 핵심)
    export_db_to_js()
    
    # 2. 크롤링 및 페이지 생성
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
        
    # 3. 목록 페이지 갱신 (jobs.html)
    print("\n📋 jobs.html 목록 갱신 중...")
    if os.path.exists(SAVE_DIR):
        files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".html")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SAVE_DIR, x)), reverse=True)
        
        list_html = """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>채용공고 목록</title><link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet"><style>body{font-family:'Pretendard';padding:20px;background:#f8fafc;max-width:800px;margin:0 auto;} .card{background:white;padding:20px;margin-bottom:15px;border-radius:10px;border:1px solid #e2e8f0;display:block;text-decoration:none;color:#333;box-shadow:0 2px 5px rgba(0,0,0,0.05);} .card:hover{border-color:#d4af37;transform:translateY(-2px);} h3{margin:0 0 5px 0;color:#0f172a;} p{margin:0;color:#64748b;font-size:0.9rem;}</style></head><body><h1 style="text-align:center;color:#0f172a;">실시간 채용공고 & DB</h1>"""
        
        for f in files:
            name = f.replace(".html", "").split("_", 1)[1] if "_" in f else f
            list_html += f'<a href="{SAVE_DIR}/{f}" class="card"><h3>{name}</h3><p>합격 DB 분석 | 전문가 첨삭 가이드</p></a>'
        
        list_html += "</body></html>"
        with open("jobs.html", "w", encoding="utf-8") as f: f.write(list_html)

    print(f"\n🎉 작업 끝! 오늘 새로 만든 파일: {new_files_count}개")