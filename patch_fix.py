import os

# ==========================================
# [설정] 소장님 환경 완벽 반영
# ==========================================
# 1. 수정 대상 폴더 (공기업/사기업 폴더명)
TARGET_FOLDERS = ["jobs_html", "jobs_private_html"]

# 2. 소장님 AI 서버 주소 (app.py 기준)
SERVER_URL = "https://jinho-lab-bot.onrender.com/chat"

# 3. 교체 대상 (기존의 문제되는 함수 시작 부분)
OLD_CODE_SIGNATURE = "function askAiAboutNews(title, date) {"

# 4. [교체용] 완벽 보안 함수 (지시사항 노출 차단 + 서버 직송)
NEW_JS_FUNCTION = f"""
        function askAiAboutNews(title, date) {{
            const win = document.getElementById('chatbot-window');
            const bubble = document.getElementById('chatbot-bubble');
            if(win) win.style.display = 'flex'; 
            if(bubble) bubble.style.display = 'none';

            // [보안 1] 사용자에게 보여줄 안내 멘트 (지시사항 노출 X)
            const displayMsg = "📢 [" + title + "] 기사를 토대로 합격 전략을 분석 중입니다...";
            addBubble(displayMsg, 'user');

            // [보안 2] HTML 화면에 적힌 기업명을 자동으로 가져옵니다 (에러 방지)
            let orgName = "이 기업";
            try {{
                // job-card 안의 기관명 텍스트 추출 시도
                const orgText = document.querySelector('.job-card div').innerText;
                if(orgText.includes('기관명')) {{
                    orgName = orgText.split('|')[0].replace('기관명:', '').trim();
                }}
            }} catch(e) {{ console.log('기업명 추출 실패, 기본값 사용'); }}

            // [보안 3] 소장님의 영업비밀 지시사항 (사용자 화면엔 절대 안 나옴)
            const secretMsg = `[뉴스 기반 지원동기 작성 요청] 
            기업명: ${{orgName}}
            뉴스 제목: ${{title}}
            뉴스 날짜: ${{date}}

            [지시사항]
            1. 위 뉴스를 분석하여 기업의 현재 상황과 위기/기회 요인을 정리해줘.
            2. 과거 합격 자소서(DB)의 데이터를 참고하여, 지원자가 어떤 '행동(Action)'을 강조해야 합격할 수 있는지 연결해줘.
            3. 답변 마지막에는 반드시 아래 문구로 마무리해서 첨삭을 유도해줘:
            "AI 채용 시대, 합격의 기준은 화려한 문장이 아니라 '검증 가능한 행동 데이터'입니다. 본인만의 행동 중심 에피소드를 설계하세요. (전문가 첨삭 신청)"`;

            // 로딩 표시
            const loadingId = addBubble("⏳ AI 수석 컨설턴트가 데이터를 분석하고 있습니다...", 'ai');
            const loadingElement = document.getElementById(loadingId); 

            // 공고 본문 요약 (컨텍스트)
            const jobTitle = document.querySelector('.job-title') ? document.querySelector('.job-title').innerText : '공고 분석';
            const jobContent = document.querySelector('.content-body') ? document.querySelector('.content-body').innerText.substring(0, 1000) : ''; 

            // [보안 4] fetch를 통해 뒷단에서 서버로 전송 (채팅창 입력 X)
            fetch('{SERVER_URL}', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ 
                    message: secretMsg,
                    context: `[현재 공고 정보]\\n기업명: ${{orgName}}\\n공고제목: ${{jobTitle}}\\n공고내용요약: ${{jobContent}}...`
                }})
            }})
            .then(res => res.json())
            .then(data => {{
                if (loadingElement) {{ loadingElement.innerHTML = data.response.replace(/\\n/g, '<br>'); }}
            }})
            .catch(err => {{
                if (loadingElement) {{ loadingElement.innerText = "⚠ AI 서버 연결 상태를 확인해주세요."; }}
            }});
        }}
"""

def apply_patch():
    print("🛡️ [보안 패치] 소장님의 지시사항 노출 문제를 수정합니다...")
    
    total_fixed = 0
    for folder in TARGET_FOLDERS:
        if not os.path.exists(folder):
            print(f"⚠ 폴더 없음 (건너뜀): {folder}")
            continue
            
        print(f"\n📂 '{folder}' 폴더 스캔 중...")
        count = 0
        
        for filename in os.listdir(folder):
            if filename.endswith(".html"):
                filepath = os.path.join(folder, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 기존 함수가 있는지 확인
                    if OLD_CODE_SIGNATURE in content:
                        # 함수 시작점 찾기
                        start_idx = content.find(OLD_CODE_SIGNATURE)
                        
                        # 함수 끝점 찾기 (다음 함수인 async function sendMsg() 바로 앞까지)
                        next_func_sig = "async function sendMsg() {"
                        end_idx = content.find(next_func_sig)
                        
                        if start_idx != -1 and end_idx != -1:
                            # 기존 함수 도려내고 새 함수 끼워넣기
                            new_content = content[:start_idx] + NEW_JS_FUNCTION + "\n\n        " + content[end_idx:]
                            
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            count += 1
                except Exception as e:
                    print(f"  ❌ 에러 발생 ({filename}): {e}")

        print(f"✅ {folder}: {count}개 파일 수정 완료.")
        total_fixed += count

    print(f"\n🎉 총 {total_fixed}개 파일의 보안 패치가 완료되었습니다.")
    print("❗ [필수] 브라우저에서 사이트를 열고 'Ctrl + F5'를 눌러 캐시를 삭제해야 적용된 화면이 보입니다.")

if __name__ == "__main__":
    apply_patch()