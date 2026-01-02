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
    print(f"🔥 [Collector] 인크루트 정밀 수집 시작 (타겟 수정: c_row)...")
    
    candidate_jobs = []
    
    for base_url in TARGET_URLS:
        # 페이지 탐색 (1~3페이지)
        for page in range(1, 4):
            try:
                # 목표량의 3배 이상 모이면 중단 (속도 최적화)
                if len(candidate_jobs) >= FINAL_TARGET_COUNT * 3: break

                target_url = f"{base_url}&page={page}"
                print(f"   📡 접속: {target_url} ... ", end="")
                
                response = requests.get(target_url, headers=HEADERS, timeout=10)
                response.encoding = response.apparent_encoding 
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # ★★★ [수정 핵심 1] 일반 리스트 영역 (ul.c_row) ★★★
                # 소장님이 주신 HTML 파일에 있는 정확한 태그 경로입니다.
                list_area = soup.select('div.cBbslist_contenst ul.c_row')
                
                # ★★★ [수정 핵심 2] 프리미엄 공고 영역 (상단 박스형) ★★★
                # 일반 리스트가 부족할 경우 상단 프리미엄 공고도 긁어옵니다.
                if not list_area:
                    print("   ⚠️ 일반 목록 없음, 상단 프리미엄 공고 확인 중...")
                    list_area = soup.select('div.cPrdlists_rows div.cPrdlists_cols')

                if not list_area:
                    print("❌ 공고 못 찾음 (구조가 다르거나 차단됨)")
                    # 디버깅용: 페이지 제목 출력
                    print(f"      ㄴ 페이지 제목: {soup.title.text.strip() if soup.title else '없음'}")
                    continue # 다음 페이지로 넘어감
                else:
                    print(f"✅ {len(list_area)}개 발견!")

                for item in list_area:
                    try:
                        # 1. 회사명 (class='cpname')
                        comp_tag = item.select_one('.cpname')
                        if not comp_tag: continue
                        company = comp_tag.get_text(strip=True)

                        if any(k in company for k in EXCLUDE_KEYWORDS): continue

                        # 2. 제목 & 링크 
                        # 일반형(.cell_mid)과 박스형(.cTitle) 구조가 다를 수 있어 두 가지 다 체크
                        title_tag = item.select_one('.cell_mid .cl_top a') or item.select_one('.cTitle strong') or item.select_one('.cl_top a')
                        
                        if not title_tag: continue

                        title = title_tag.get_text(strip=True)
                        
                        # 링크 추출 (a 태그가 있는 상위 요소 찾기)
                        link_tag = item.find('a', href=True)
                        # 제목 태그 자체가 a태그인 경우
                        if title_tag.name == 'a': link_tag = title_tag
                        
                        if not link_tag: continue
                        link = link_tag['href']
                        if link.startswith("/"): link = "https://job.incruit.com" + link

                        # 3. 마감일
                        deadline = "채용시"
                        # 일반 리스트 구조: .cell_last 안의 첫번째 span
                        d_tag = item.select_one('.cell_last .cl_btm span:first-child')
                        # 프리미엄 리스트 구조: .cDate
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

    print(f"\n📊 [최종 결과] 수집된 데이터: {len(candidate_jobs)}건")
    
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