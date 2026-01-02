import os
import requests
from bs4 import BeautifulSoup
import json
import random

# ==========================================
# 1. 설정 (검색어 없음! 규모별 URL 타겟팅)
# ==========================================
# 인크루트 기업분류별 URL 리스트 (대기업, 중견기업, 강소기업)
TARGET_URLS = [
    # 대기업 (Group & Big)
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=1", 
    # 중견기업 (Mid-sized)
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=2", 
    # 강소기업/히든챔피언 (Hidden Champion)
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=3"
]

# 봇 차단 방지용 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# 혹시 섞여 있을 공기업/공무원 필터링
EXCLUDE_KEYWORDS = ["공사", "공단", "재단", "협회", "진흥원", "시청", "구청", "센터", "공무원", "보건소"]

def collect_private_jobs_by_size():
    print(f"🔥 [인크루트] 기업 규모별(대/중견/강소) 알짜배기 공고 수집 시작...")
    
    total_jobs = []
    
    # 각 기업 규모별 페이지를 돌면서 데이터를 모음
    for url in TARGET_URLS:
        if len(total_jobs) >= 30: break # 30개 차면 중단
        
        try:
            print(f"   Targeting URL: {url}...")
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            # 인코딩 자동 감지 (한글 깨짐 방지)
            response.encoding = response.apparent_encoding 

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 인크루트 리스트 아이템 탐색
            all_list_items = soup.find_all('li')
            
            # 페이지당 최대 10개씩만 뽑아서 섞기 (다양성을 위해)
            count_per_page = 0
            
            for item in all_list_items:
                if len(total_jobs) >= 30: break
                if count_per_page >= 10: break # 한 카테고리당 10개만 (골고루 수집)

                try:
                    # 1. 회사명 추출 & 필터링
                    comp_tag = item.find(class_='cpname')
                    if not comp_tag: continue
                    
                    company = comp_tag.get_text(strip=True)

                    # 공기업 키워드가 포함되어 있으면 건너뜀 (순수 사기업만)
                    if any(k in company for k in EXCLUDE_KEYWORDS):
                        continue

                    # 2. 제목 & 링크 추출
                    title_tag = item.find(class_='cl_top') or item.find(class_='hdit')
                    if not title_tag: continue
                    
                    link_tag = title_tag.find('a')
                    if not link_tag: continue

                    title = link_tag.get_text(strip=True)
                    link = link_tag['href']
                    
                    # 링크 절대경로 변환
                    if link.startswith("/"):
                        link = "https://job.incruit.com" + link

                    # 3. 기업 형태(규모) 태그 추출
                    type_tags = []
                    for icon in item.find_all(class_='icon'):
                        tag_text = icon.get_text(strip=True)
                        if tag_text: type_tags.append(tag_text)
                    
                    # URL에 따라 강제 태그 부여 (데이터가 비어있을 경우 대비)
                    if "cd=1" in url and "대기업" not in type_tags: type_tags.insert(0, "대기업")
                    elif "cd=2" in url and "중견기업" not in type_tags: type_tags.insert(0, "중견기업")
                    elif "cd=3" in url and "강소기업" not in type_tags: type_tags.insert(0, "강소기업")
                    
                    type_str = ", ".join(type_tags)

                    # 4. 세부 정보 (경력, 학력 등)
                    details = item.find_all('span')
                    exp = "무관"
                    edu = "무관"
                    
                    info_texts = [d.get_text(strip=True) for d in details if len(d.get_text(strip=True)) > 1]
                    for text in info_texts:
                        if "경력" in text or "신입" in text: exp = text
                        elif "대졸" in text or "고졸" in text or "학력" in text: edu = text

                    # 5. 마감일 추출
                    deadline_tag = item.find(class_='cl_btm')
                    deadline = "채용시"
                    if deadline_tag:
                        d_span = deadline_tag.find('span')
                        if d_span: deadline = d_span.get_text(strip=True)

                    # 6. 데이터 담기
                    job_data = {
                        "id": len(total_jobs) + 1,
                        "company": company,
                        "type": type_str,
                        "title": title,
                        "exp": exp,
                        "edu": edu,
                        "deadline": deadline,
                        "link": link
                    }
                    
                    total_jobs.append(job_data)
                    count_per_page += 1
                    print(f"      ✅ [{len(total_jobs)}] {company} ({type_str})")

                except Exception:
                    continue 

        except Exception as e:
            print(f"   ❌ URL 접속 오류: {e}")
            continue

    return total_jobs

# --- 실행 및 파일 저장 ---
if __name__ == "__main__":
    jobs = collect_private_jobs_by_size()
    
    if jobs:
        # 1. JOBS 폴더 생성
        save_dir = "JOBS"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 2. 파일 저장
        save_path = os.path.join(save_dir, "recruit_data.json")
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=4)
            
        print("\n" + "="*50)
        print(f"🎉 기업규모별 알짜 공고 {len(jobs)}개 수집 완료!")
        print(f"📂 저장 경로: {save_path}")
        print("="*50)
    else:
        print("\n💀 수집된 데이터가 없습니다.")