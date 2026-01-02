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
# config.env 파일 로드 (로컬 테스트용)
if not load_dotenv('config.env'):
    print("ℹ [알림] config.env 파일을 찾을 수 없습니다. (Render 서버 환경 변수 사용 시 정상)")

HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=HF_TOKEN)
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

app = Flask(__name__)
CORS(app) # 보안 해제 (모든 사이트에서 접속 허용)

# ======================================================
# 2. 기능: DB 로드 & 검색 (일반 상담용)
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
    # 1. 욕설 필터 (최우선)
    bad_words = ['시발', '병신', '개새끼', '꺼져', '죽어', '미친', 'ㅗ', '씨발', '놈', '새끼']
    if any(word in user_input for word in bad_words): return "INSULT"
    
    # 2. 검색 의도 (주식, 날씨, 뉴스 등)
    search_keywords = ['주가', '날씨', '뉴스', '정보', '검색', '전망', '연봉', '이슈', '동향']
    if any(x in user_input for x in search_keywords): return "SEARCH"
    
    # 3. 가벼운 인사 (짧은 말)
    chat_keywords = ['안녕', '하이', 'ㅎㅇ', '반가', '고마', '감사', '시작', '테스트']
    if len(user_input) < 5 or any(x in user_input for x in chat_keywords): return "CHAT"
    
    # 4. 나머지는 모두 자소서 상담으로 간주
    return "CONSULTING"

# ======================================================
# 4. 기능: 답변 생성 (김진호 소장 페르소나 - ★중국어 금지판★)
# ======================================================
def ask_kim_pro(user_input, context=""):
    """
    user_input: 사용자 질문
    context: (선택) 현재 보고 있는 채용공고 내용 (HTML에서 긁어옴)
    """
    intent = classify_intent(user_input)
    
    # [★중요★] 중국어 원천 봉쇄 규칙 (모든 프롬프트에 공통 적용)
    NO_CHINESE_RULE = """
    [치명적 경고: 언어 제한]
    1. 당신은 '한국인'입니다. 무조건 '한국어(Korean)'로만 답변하십시오.
    2. 중국어(한자)가 포함되면 즉시 삭제하거나 한국어로 번역해서 출력하세요.
    3. 절대 중국어 문자를 출력하지 마십시오. (No Chinese characters allowed in output)
    """
    
    # [상황 1] 욕설 차단
    if intent == "INSULT":
        return "🚫 예의를 갖춰 질문해 주세요. 김진호 합격연구소는 비매너 채팅에 응답하지 않습니다."
    
    # [상황 2] 실시간 웹 검색
    elif intent == "SEARCH":
        info = search_web(user_input)
        sys_msg = f"""
        당신은 '김진호 합격연구소'의 AI 비서입니다.
        검색 결과를 요약해서 전달하고, 이 정보를 자소서에 어떻게 녹여낼지 전문가적 관점에서 조언하세요.
        {NO_CHINESE_RULE}
        """
        user_msg = f"[실시간 검색 결과]:\n{info}\n\n[사용자 질문]: {user_input}"
        
    # [상황 3] 자소서/취업 상담 (핵심)
    elif intent == "CONSULTING":
        # 3-1. 사용자가 특정 공고를 보고 있을 때 (Context 있음)
        if context:
            sys_msg = f"""
            당신은 '김진호 합격연구소'의 채용 공고 분석 전문가입니다.
            사용자가 현재 보고 있는 [채용공고] 내용을 바탕으로 질문에 답해 주세요.
            단, 정답을 전부 알려주지 말고, "이 직무의 숨겨진 핵심 역량을 완벽하게 공략하려면 김진호 소장의 VIP 설계가 필요합니다"라고 강력하게 영업하십시오.
            말투는 전문적이고 냉철하게 하십시오.
            {NO_CHINESE_RULE}
            """
            user_msg = f"{context}\n\n[사용자 질문]: {user_input}"
            
        # 3-2. 일반적인 상담 (Context 없음) -> DB 활용
        else:
            evidence = search_db(user_input.split()[0])
            sys_msg = f"""
            당신은 '김진호 합격연구소' 수석 AI 연구원입니다.
            "이 데이터는 AI가 아닌 인간의 치열한 논리로 합격한 기록입니다"라고 권위를 세우십시오.
            정답 대신 '합격 논리'를 가르치고, 'Structure-X' 기술과 'VIP 유료 진단'을 받도록 유도하십시오.
            {NO_CHINESE_RULE}
            """
            user_msg = f"[참고 합격DB]: {evidence}\n\n[사용자 질문]: {user_input}"
        
    # [상황 4] 가벼운 인사
    else: # CHAT
        sys_msg = f"당신은 친절하고 전문적인 한국인 상담사입니다. 인사를 받아주고, '어떤 자소서 고민이 있으신가요?'라고 한국어로 물어보세요.\n{NO_CHINESE_RULE}"
        user_msg = user_input

    # AI 호출 (Qwen 모델)
    try:
        response = client.chat_completion(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠ AI 서버 연결 지연: {e}"

# ======================================================
# 5. 웹 통신 API (HTML과 연결되는 구멍)
# ======================================================
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        user_msg = data.get('message', '')
        
        # [핵심] HTML에서 보내준 '공고 내용'을 받음 (없으면 빈 문자열)
        context_data = data.get('context', '') 

        print(f"📩 [질문 수신]: {user_msg}")
        if context_data:
            print(f"📄 [공고 데이터 감지]: 길이 {len(context_data)}자")

        # 질문과 공고 내용을 같이 넘김
        answer = ask_kim_pro(user_msg, context=context_data)
        
        print(f"📤 [답변 발송]: {answer[:30]}...")
        return jsonify({'response': answer})
        
    except Exception as e:
        print(f"❌ 서버 에러: {e}")
        return jsonify({'response': "서버 처리 중 오류가 발생했습니다."})

# ======================================================
# 6. [NEW] 추가 기능 (서버 유지 & 검색 로봇)
# ======================================================

# [기능 1] 서버 수면 방지 (Self-Ping)
# Render 무료 서버는 15분간 요청이 없으면 잠자기 때문에, 14분마다 스스로를 찌름
def keep_alive():
    while True:
        try:
            time.sleep(840)  # 14분 (15분 되기 전에)
            # 자기 자신(localhost)에게 가벼운 요청을 보냄
            requests.get("http://127.0.0.1:5000/robots.txt")
            print("⏰ [알림] 서버 잠자기 방지(Ping) 완료")
        except:
            pass # 실패해도 서버에 지장 없음

# 백그라운드 스레드로 실행 (메인 서버 방해 X)
threading.Thread(target=keep_alive, daemon=True).start()

# [기능 2] 검색 로봇용 robots.txt 응답
@app.route('/robots.txt')
def robots():
    content = "User-agent: *\nAllow: /"
    return Response(content, mimetype="text/plain")

# [기능 3] 서버 상태 확인용 (Health Check)
@app.route('/')
def home():
    return "🤖 김진호 합격연구소 AI 서버 정상 작동 중 (Status: Online)"

# ======================================================
# 7. 서버 실행
# ======================================================
if __name__ == "__main__":
    load_database()
    print("\n🚀 [김진호 연구소] AI 웹 서버 가동 중 (포트: 5000)")
    print("   - 모드: DB검색 / 웹검색 / 공고분석 / 영업멘트 / 한국어전용")
    print("   - [NEW] 24시간 Keep-alive 자동 실행")
    print("   - 상태: 연결 대기 중... (종료하려면 Ctrl+C)")
    app.run(host='0.0.0.0', port=5000)