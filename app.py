import os
import json
import random
import time
import threading
import requests
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from duckduckgo_search import DDGS
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ======================================================
# 1. 설정 및 보안
# ======================================================
if not load_dotenv('config.env'):
    print("ℹ [알림] config.env 파일을 찾을 수 없습니다. (Render 서버 환경 변수 사용 시 정상)")

HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=HF_TOKEN)
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

app = Flask(__name__)
CORS(app) 

# ======================================================
# 2. 기능: DB 로드 & 검색
# ======================================================
ALL_DB_DATA = []

def load_database():
    global ALL_DB_DATA
    try:
        with open('db1.json', 'r', encoding='utf-8') as f1: data1 = json.load(f1)
        with open('db2.json', 'r', encoding='utf-8') as f2: data2 = json.load(f2)
        ALL_DB_DATA = data1 + data2
        print(f"✅ [서버] 합격 데이터 {len(ALL_DB_DATA)}건 장전 완료.")
    except:
        ALL_DB_DATA = ["(데이터 로드 실패) 기본 합격 예시 데이터"]
        print("⚠ [주의] DB 파일을 찾을 수 없어 기본 데이터로 실행합니다.")

def search_db(keyword):
    # 키워드가 포함된 합격 자소서를 찾아서 하나 랜덤 반환
    results = [item for item in ALL_DB_DATA if keyword in item]
    return random.choice(results) if results else ""

# ======================================================
# 3. 기능: 웹 검색 & 의도 분류
# ======================================================
def search_web(query):
    try:
        with DDGS() as ddgs:
            # 검색 결과 2개만 빠르게 요약
            results = list(ddgs.text(query, max_results=2))
            if not results: return "최신 정보를 찾을 수 없습니다."
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"검색 시스템 일시 오류: {e}"

def classify_intent(user_input):
    # 1. 욕설 필터
    bad_words = ['시발', '병신', '개새끼', '꺼져', '죽어', '미친', 'ㅗ', '씨발', '놈', '새끼']
    if any(word in user_input for word in bad_words): return "INSULT"
    
    # 2. 검색 의도
    search_keywords = ['주가', '날씨', '뉴스', '정보', '검색', '전망', '연봉', '이슈', '동향']
    if any(x in user_input for x in search_keywords): return "SEARCH"
    
    # 3. 가벼운 인사
    chat_keywords = ['안녕', '하이', 'ㅎㅇ', '반가', '고마', '감사', '시작', '테스트']
    if len(user_input) < 5 or any(x in user_input for x in chat_keywords): return "CHAT"
    
    return "CONSULTING"

# ======================================================
# 4. 기능: 답변 생성 (여기가 가장 중요한 핵심 파트입니다!)
# ======================================================
def ask_kim_pro(user_input, context=""):
    intent = classify_intent(user_input)
    
    # [언어 통제 규칙]
    NO_CHINESE_RULE = """
    [치명적 경고: 언어 제한]
    1. 당신은 '한국인'입니다. 무조건 '한국어(Korean)'로만 답변하십시오.
    2. 중국어(한자)가 포함되면 즉시 삭제하거나 한국어로 번역해서 출력하세요.
    """
    
    if intent == "INSULT":
        return "🚫 예의를 갖춰 질문해 주세요. 김진호 합격연구소는 비매너 채팅에 응답하지 않습니다."
    
    elif intent == "SEARCH":
        info = search_web(user_input)
        sys_msg = f"당신은 '김진호 합격연구소' AI 비서입니다. 검색 결과를 요약하고 전문가의 도움이 필요하다고 덧붙이세요.\n{NO_CHINESE_RULE}"
        user_msg = f"[검색 결과]:\n{info}\n\n[질문]: {user_input}"
        
    elif intent == "CONSULTING":
        
        # ★★★ [Case A] 사용자가 'AI 분석 버튼'을 눌렀을 때 (가장 긴 로직) ★★★
        if "[데이터 분석 요청]" in user_input:
            sys_msg = f"""
            당신은 '김진호 합격연구소'의 수석 컨설턴트 AI입니다.
            제공된 [합격 데이터]를 분석하여, [현재 공고] 직무에 어떻게 적용할지 **전문가처럼 딱 3가지 포인트**로 답변하십시오.
            
            [필수 답변 형식 - 이 구조를 반드시 따를 것]
            **1. ✅ [핵심 역량 발견]**: (합격 데이터에서 가장 돋보이는 강점 1문장 요약)
            
            **2. 🎯 [공고 적용 전략]**: (이 강점을 현재 공고의 직무에 어떻게 연결할지 구체적 조언 1문장)
            
            **3. ⚠️ [합격의 한 끗 차이]**: (아래 멘트를 그대로 출력)
            "하지만 텍스트 분석만으로는 부족합니다. 면접관은 당신의 **'구체적 행동(Action)'**을 집요하게 파고듭니다. 
            AI가 흉내 낼 수 없는 **김진호 소장의 [Structure-X]**로 면접까지 완벽하게 대비하세요.
            
            👉 1:1 VIP 행동 설계 받기: https://kimjinholab.pages.dev/consult.html"

            {NO_CHINESE_RULE}
            """
            user_msg = f"{context}\n\n[요청사항]: {user_input}"

        # [Case B] 일반 질문 (Context 있음)
        elif context:
            sys_msg = f"""
            당신은 '김진호 합격연구소'의 채용 분석가입니다. 
            질문에 대해 3문장 내외로 명쾌하게 답하고, 
            "이 직무의 숨겨진 의도를 공략하려면 소장님의 VIP 진단이 필요합니다"라고 영업하십시오.
            {NO_CHINESE_RULE}
            """
            user_msg = f"{context}\n\n[질문]: {user_input}"
            
        # [Case C] DB 기반 일반 질문
        else:
            evidence = search_db(user_input.split()[0])
            sys_msg = f"당신은 AI 연구원입니다. 합격 DB를 기반으로 답하되, 김진호 소장의 행동 설계를 강조하세요.\n{NO_CHINESE_RULE}"
            user_msg = f"[참고 DB]: {evidence}\n\n[질문]: {user_input}"
        
    else: 
        sys_msg = f"당신은 친절한 상담사입니다. 한국어로 인사하고 자소서 고민을 물어보세요.\n{NO_CHINESE_RULE}"
        user_msg = user_input

    try:
        response = client.chat_completion(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=800, # 3단 논법 답변이 잘리지 않도록 길이 확보 (중요!)
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠ AI 서버 연결 지연: {e}"

# ======================================================
# 5. 웹 통신 API
# ======================================================
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        user_msg = data.get('message', '')
        context_data = data.get('context', '') 

        print(f"📩 [질문]: {user_msg}")
        if context_data:
            print(f"📄 [데이터 감지]: {len(context_data)}자")

        answer = ask_kim_pro(user_msg, context=context_data)
        
        print(f"📤 [답변]: {answer[:30]}...")
        return jsonify({'response': answer})
        
    except Exception as e:
        print(f"❌ 서버 에러: {e}")
        return jsonify({'response': "서버 오류 발생"})

# ======================================================
# 6. 서버 유지 (Keep-alive)
# ======================================================
def keep_alive():
    while True:
        try:
            time.sleep(840)
            requests.get("http://127.0.0.1:5000/robots.txt")
            print("⏰ [알림] 서버 잠자기 방지(Ping) 완료")
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

@app.route('/robots.txt')
def robots():
    return Response("User-agent: *\nAllow: /", mimetype="text/plain")

@app.route('/')
def home():
    return "🤖 김진호 합격연구소 AI 서버 정상 작동 중"

if __name__ == "__main__":
    load_database()
    print("\n🚀 [김진호 연구소] AI 웹 서버 가동 중 (포트: 5000)")
    print("   - 모드: 3단 논법 영업 / 토큰 최적화 / 24시간 가동")
    app.run(host='0.0.0.0', port=5000)