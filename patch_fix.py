import os
import re

# ==========================================
# [설정] 수정할 대상 폴더 및 서버 주소
# ==========================================
TARGET_FOLDERS = ["jobs_html", "jobs_private_html"]
SERVER_URL = "https://jinho-lab-bot.onrender.com/chat"

# [교체할 보안 자바스크립트 코드]
# 소장님의 지시사항을 사용자 눈에는 안 보이게 하고, 서버로만 보냅니다.
NEW_JS_CODE = f"""
        function askAiAboutNews(title, date) {{
            const win = document.getElementById('chatbot-window');
            const bubble = document.getElementById('chatbot-bubble');
            if(win) win.style.display = 'flex'; 
            if(bubble) bubble.style.display = 'none';

            // 1. [보안] 사용자에게는 안내 멘트만 보여줌
            const displayMsg = "📢 [" + title + "] 기사를 토대로 합격 전략을 분석 중입니다...";
            addBubble(displayMsg, 'user');

            // 2. [자동 감지] HTML에서 기업명 추출
            let orgName = "이 기업";
            try {{
                const orgText = document.querySelector('.job-card div').innerText;
                if(orgText.includes('기관명')) {{
                    orgName = orgText.split('|')[0].replace('기관명:', '').trim();
                }}
            }} catch(e) {{ console.log('기업명 추출 실패'); }}

            // 3. [비밀] 서버로 보낼 진짜 지시사항 (화면 노출 X)
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

            // 4. [핵심] fetch로 서버 직송 (채팅창 입력 방지)
            fetch('{SERVER_URL}', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ 
                    message: secretMsg,
                    context: `[현재 공고 정보]\\n기업명: ${{orgName}}...`
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

def apply_strong_patch():
    print("🛡️ [강력 패치] 기존 파일들의 보안 구멍을 강제로 막습니다...")
    
    # 정규표현식: function askAiAboutNews 부터 async function sendMsg 바로 앞까지 잡음
    # (띄어쓰기, 줄바꿈 상관없이 잡아냄)
    pattern = re.compile(r'function\s+askAiAboutNews\s*\(.*?\)\s*\{[\s\S]*?(?=\s*async\s+function\s+sendMsg)', re.MULTILINE)

    count = 0
    for folder in TARGET_FOLDERS:
        if not os.path.exists(folder): continue
        
        for filename in os.listdir(folder):
            if filename.endswith(".html"):
                filepath = os.path.join(folder, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 패턴이 발견되면 교체
                    if pattern.search(content):
                        new_content = pattern.sub(NEW_JS_CODE + "\n\n        ", content)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                        print(f"  ✅ 수정됨: {filename}")
                        
                except Exception as e:
                    print(f"  ❌ 에러 ({filename}): {e}")

    print(f"\n🎉 총 {count}개 파일의 보안 패치가 완료되었습니다.")
    print("❗ [필수] 브라우저에서 'Ctrl + F5'를 눌러야 사용자에게 반영됩니다!")

if __name__ == "__main__":
    apply_strong_patch()