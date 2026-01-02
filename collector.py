import os
import requests
from bs4 import BeautifulSoup
import json
import random
import time

# ==========================================
# 1. 설정 (인크루트 최신 HTML 구조 반영)
# ==========================================
TARGET_URLS = [
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=1", # 대기업
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=2", # 중견기업
    "https://job.incruit.com/jobdb_list/searchjob.asp?ct=6&ty=1&cd=3"  # 강소기업
]

# [핵심] 차단 방지용 헤더 (Referer 추가)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://job.incruit.com/",
    "Connection": "keep-alive"
}

EXCLUDE_KEYWORDS = ["공사", "공단", "재단", "협회", "진흥원", "시청", "구청", "센터", "공무원", "보건소"]
FINAL_TARGET_COUNT = 30

def collect_private_jobs_by_size():
    print(f"🔥 [Collector] 중복 제거 및 완전 수집 모드 시작 (목표: {FINAL_TARGET_COUNT}개)...")
    
    candidate_jobs = []
    seen_links = set() # ★ [추가] 중복 공고 방지용 체크리스트
    
    for base_url in TARGET_URLS:
        # 페이지 탐색 (1~3페이지)
        for page in range(1, 4):
            try:
                # 목표량의 4배수 이상 모이면 중단 (필터링 고려 넉넉하게)
                if len(candidate_jobs) >= FINAL_TARGET_COUNT * 4: break

                target_url = f"{base_url}&page={page}"
                print(f"   📡 접속: {target_url} ... ", end="")
                
                response = requests.get(target_url, headers=HEADERS, timeout=10)
                response.encoding = response.apparent_encoding 
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # ★★★ [수정 핵심] 상단(Premium) + 하단(General) 모두 수집 ★★★
                # 기존 코드의 'if not list_area' 로직을 삭제하고 둘 다 가져와서 합칩니다.
                list_premium = soup.select('div.cPrdlists_rows div.cPrdlists_cols') # 상단
                list_general = soup.select('div.cBbslist_contenst ul.c_row')        # 하단
                
                # 두 리스트 합치기 (누락 방지)
                all_items = list_premium + list_general
                
                if not all_items:
                    print("❌ 공고 못 찾음 (구조가 다르거나 차단됨)")
                    # 디버깅용: 페이지 제목 출력
                    print(f"      ㄴ 페이지 제목: {soup.title.text.strip() if soup.title else '없음'}")
                    continue 
                else:
                    print(f"✅ {len(all_items)}개 발견 (상단:{len(list_premium)} + 하단:{len(list_general)})")

                for item in all_items:
                    try:
                        # 1. 회사명 (태그가 다를 수 있어 두 가지 다 확인)
                        comp_tag = item.select_one('.cpname') or item.select_one('.cCpName')
                        if not comp_tag: continue
                        company = comp_tag.get_text(strip=True)

                        if any(k in company for k in EXCLUDE_KEYWORDS): continue

                        # 2. 제목 & 링크 
                        # 상단/하단 구조 차이 대응
                        title_tag = item.select_one('.cell_mid .cl_top a') or item.select_one('.cTitle strong') or item.select_one('.cTitle') or item.select_one('.cl_top a')
                        
                        if not title_tag: continue

                        title = title_tag.get_text(strip=True)
                        
                        # 링크 추출 (a 태그가 있는 상위 요소 찾기)
                        link_tag = item.find('a', href=True)
                        # 제목 태그 자체가 a태그인 경우
                        if title_tag.name == 'a': link_tag = title_tag
                        
                        if not link_tag: continue
                        link = link_tag['href']
                        if link.startswith("/"): link = "https://job.incruit.com" + link

                        # ★ [추가] 중복 방지 로직
                        if link in seen_links:
                            continue # 이미 수집한 링크면 패스
                        seen_links.add(link)

                        # 3. 마감일
                        deadline = "채용시"
                        # 하단형 구조
                        d_tag = item.select_one('.cell_last .cl_btm span:first-child')
                        # 상단형 구조 (.cDate)
                        if not d_tag: d_tag = item.select_one('.cDate')
                        
                        if d_tag: deadline = d_tag.get_text(strip=True)

                        # 4. 저장할 데이터 구성
                        job_data = {
                            "company": company,
                            "title": title,
                            "link": link,
                            "deadline": deadline,
                            "id": 0 # 나중에 일괄 부여
                        }
                        candidate_jobs.append(job_data)

                    except Exception:
                        continue
                
                time.sleep(1) # 차단 방지 대기

            except Exception as e:
                print(f"   ❌ 에러: {e}")
                continue

    print(f"\n📊 [최종 결과] 중복 제거 후 확보된 공고: {len(candidate_jobs)}건")
    
    # 데이터가 없으면 비상 경고
    if not candidate_jobs:
        print("🚨 [비상] 수집된 데이터가 0건입니다. HTML 구조가 예상과 다릅니다.")
        return []

    # 셔플 및 30개 자르기
    random.shuffle(candidate_jobs)
    final_jobs = candidate_jobs[:FINAL_TARGET_COUNT]

    # ID 부여
    for idx, job in enumerate(final_jobs):
        job['id'] = idx + 1
        
    return final_jobs

if __name__ == "__main__":
    jobs = collect_private_jobs_by_size()
    
    # 폴더 생성 (현재 위치 기준)
    save_dir = "JOBS"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 파일 저장
    save_path = os.path.join(save_dir, "recruit_data.json")
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=4)
        
    if jobs:
        print(f"🎉 recruit_data.json 저장 완료! ({len(jobs)}건)")
        print(f"📂 저장 경로: {os.path.abspath(save_path)}")
    else:
        print("💀 빈 파일 저장됨.")