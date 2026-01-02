import os
import requests
from bs4 import BeautifulSoup
import json
import random
import time

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

# ★ 최종적으로 저장할 공고 개수 목표
FINAL_TARGET_COUNT = 30

def collect_private_jobs_by_size():
    print(f"🔥 [인크루트] 광범위 수집 모드 가동 (페이지 넘김 기능 추가됨)...")
    
    candidate_jobs = [] # 후보군을 담을 임시 리스트
    
    # 각 기업 규모별 URL을 순회
    for base_url in TARGET_URLS:
        
        # [수정] 각 카테고리별로 1페이지부터 5페이지까지 탐색 (Pagination)
        for page in range(1, 6):
            try:
                # 목표량의 3배 이상 모였으면 조기 종료 (속도 최적화)
                if len(candidate_jobs) >= FINAL_TARGET_COUNT * 3:
                    break

                # URL에 페이지 번호 추가 (&page=1, &page=2 ...)
                target_url = f"{base_url}&page={page}"
                print(f"   Targeting URL: {target_url} (Page {page})...")
                
                response = requests.get(target_url, headers=HEADERS, timeout=10)
                response.encoding = response.apparent_encoding 
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 인크루트 리스트 아이템 추출
                all_list_items = soup.select('ul.c_list > li')
                
                # 해당 페이지에 공고가 없으면 다음 카테고리로 넘어감
                if not all_list_items:
                    print(f"      ㄴ 공고 없음. 다음 카테고리로 이동.")
                    break

                for item in all_list_items:
                    try:
                        # 1. 회사명 추출 & 필터링
                        comp_tag = item.find(class_='cpname')
                        if not comp_tag: continue
                        company = comp_tag.get_text(strip=True)

                        # 공기업 키워드 필터링
                        if any(k in company for k in EXCLUDE_KEYWORDS):
                            continue

                        # 2. 제목 & 링크 추출
                        title_tag = item.find(class_='cl_top') or item.find(class_='hdit')
                        if not title_tag: continue
                        
                        link_tag = title_tag.find('a')
                        if not link_tag: continue

                        title = link_tag.get_text(strip=True)
                        link = link_tag['href']
                        if link.startswith("/"):
                            link = "https://job.incruit.com" + link

                        # 3. 기업 형태(규모) 태그 추출
                        type_tags = []
                        for icon in item.find_all(class_='icon'):
                            tag_text = icon.get_text(strip=True)
                            if tag_text: type_tags.append(tag_text)
                        
                        if "cd=1" in base_url and "대기업" not in type_tags: type_tags.insert(0, "대기업")
                        elif "cd=2" in base_url and "중견기업" not in type_tags: type_tags.insert(0, "중견기업")
                        elif "cd=3" in base_url and "강소기업" not in type_tags: type_tags.insert(0, "강소기업")
                        
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

                        # 6. 데이터 담기 (ID는 나중에 부여)
                        job_data = {
                            "company": company,
                            "type": type_str,
                            "title": title,
                            "exp": exp,
                            "edu": edu,
                            "deadline": deadline,
                            "link": link
                        }
                        
                        candidate_jobs.append(job_data)

                    except Exception:
                        continue 
                
                # 한 페이지 긁은 후 잠시 대기 (차단 방지)
                time.sleep(1) 

            except Exception as e:
                print(f"   ❌ 페이지 접속 오류: {e}")
                continue

    print(f"\n📊 수집 종료: 총 {len(candidate_jobs)}개의 후보 공고 확보")
    
    # [핵심 로직] 충분히 모은 후 랜덤으로 섞어서 30개만 자름 (다양성 확보)
    if len(candidate_jobs) > FINAL_TARGET_COUNT:
        print(f"✂️ 목표 수량({FINAL_TARGET_COUNT}개)에 맞춰 랜덤 선별 중...")
        random.shuffle(candidate_jobs)
        final_jobs = candidate_jobs[:FINAL_TARGET_COUNT]
    else:
        final_jobs = candidate_jobs

    # ID 재부여
    for idx, job in enumerate(final_jobs):
        job['id'] = idx + 1
        
    return final_jobs

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
        print(f"🎉 최종 선별된 알짜 공고 {len(jobs)}개 저장 완료!")
        print(f"📂 저장 경로: {save_path}")
        print("="*50)
    else:
        print("\n💀 수집된 데이터가 없습니다.")