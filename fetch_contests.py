import os
import sys
import json
import time
import argparse
import requests

# URL Endpoints
AUTH_URL = "https://dbapi.ptit.edu.vn/api/auth/auth/ptit-login"
USER_INFO_URL = "https://dbapi.ptit.edu.vn/api/auth/users/info"
CONTEST_INFO_URL = "https://dbapi.ptit.edu.vn/api/app/contest/{}"
CONTEST_QUESTIONS_URL = "https://dbapi.ptit.edu.vn/api/app/jnp-submission/contest/{}/questions"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PTIT_ENV_FILE = os.path.join(BASE_DIR, "ptit.env")
OUTPUT_DIR = os.path.join(BASE_DIR, "sample_responses", "contest")
MASTER_BANK_FILE = os.path.join(BASE_DIR, "sample_responses", "master_jnp_questions_bank.json")

DEFAULT_CONTESTS = [
    "f66109d7-a13e-4f54-8fdb-d98e6c521617",
    "cd57b1ba-a746-46df-afe6-fd50b8f55267"
]

def load_credentials(env_path):
    """Doc danh sach tai khoan tu file ptit.env"""
    if not os.path.exists(env_path):
        print(f"[-] Khong tim thay file: {env_path}")
        return []
    
    creds = []
    cur_u = None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("QLDT_USERNAME="):
                cur_u = line.split("=", 1)[1].strip()
            elif line.startswith("QLDT_PASSWORD=") and cur_u:
                cur_p = line.split("=", 1)[1].strip()
                creds.append((cur_u, cur_p))
                cur_u = None
    return creds

def fetch_contests(contest_ids):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    creds = load_credentials(PTIT_ENV_FILE)
    if not creds:
        print("[-] Khong co tai khoan nao de chay.")
        return

    print("==================================================")
    print("   PTIT CONTEST QUESTION FETCHER")
    print("==================================================")
    print(f"[*] Tim thay {len(creds)} tai khoan trong ptit.env.")
    print(f"[*] So luong ky thi can quet: {len(contest_ids)}")
    for i, cid in enumerate(contest_ids, 1):
        print(f"    {i}. {cid}")
    print("--------------------------------------------------")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    })

    # 1. Lay thong tin tung contest
    contest_meta = {}
    # Dung tam tai khoan dau tien dang nhap duoc de lay thong tin contest
    first_token = None
    for u, p in creds:
        try:
            r = session.post(AUTH_URL, json={"username": u, "password": p}, timeout=10)
            if r.status_code == 200:
                first_token = r.json().get("accessToken")
                break
        except Exception:
            pass

    if first_token:
        headers_info = {"Authorization": f"Bearer {first_token}"}
        for cid in contest_ids:
            try:
                r = session.get(CONTEST_INFO_URL.format(cid), headers=headers_info, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    contest_meta[cid] = {
                        "name": d.get("name", cid),
                        "code": d.get("contestCode", ""),
                        "mode": d.get("distributionMode", "RANDOM_BY_GROUP")
                    }
                else:
                    contest_meta[cid] = {"name": cid, "code": "", "mode": "UNKNOWN"}
            except Exception:
                contest_meta[cid] = {"name": cid, "code": "", "mode": "UNKNOWN"}
    else:
        for cid in contest_ids:
            contest_meta[cid] = {"name": cid, "code": "", "mode": "UNKNOWN"}

    # 2. Quet cau hoi theo tung tai khoan
    all_contest_questions = {cid: {} for cid in contest_ids}
    student_mappings = {}

    for idx, (username, password) in enumerate(creds, 1):
        print(f"\n[{idx}/{len(creds)}] Dang dang nhap: {username} ...")
        try:
            login_res = session.post(AUTH_URL, json={"username": username, "password": password}, timeout=10)
            if login_res.status_code != 200:
                print(f"  [-] Dang nhap that bai (HTTP {login_res.status_code})")
                student_mappings[username] = {"status": "login_failed", "error": login_res.text[:80]}
                continue

            token = login_res.json().get("accessToken")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            # Lay ten sinh vien
            u_info = session.get(USER_INFO_URL, headers=headers, timeout=10)
            full_name = username
            user_uuid = None
            if u_info.status_code == 200:
                ud = u_info.json()
                full_name = ud.get("fullName", ud.get("firstName", "") + " " + ud.get("lastName", ""))
                user_uuid = ud.get("id")

            print(f"  [+] Dang nhap thanh cong: {full_name} ({username})")
            student_mappings[username] = {
                "status": "success",
                "fullName": full_name,
                "userUuid": user_uuid,
                "contests": {}
            }

            # Lay de thi cua tung contest
            for cid in contest_ids:
                meta = contest_meta.get(cid, {})
                c_name = meta.get("name", cid)
                short_id = cid[:8]

                q_url = CONTEST_QUESTIONS_URL.format(cid)
                q_res = session.get(q_url, headers=headers, timeout=10)

                if q_res.status_code == 200:
                    raw_items = q_res.json()
                    new_count = 0
                    q_summary = []

                    for item in raw_items:
                        q = item.get("question", {})
                        qid = q.get("id")
                        alias = q.get("alias", "N/A")
                        code = q.get("code", 0)
                        title = q.get("title", "")
                        proto = q.get("protocolType", "")
                        level = q.get("level", "")

                        q_summary.append({
                            "id": qid,
                            "code": code,
                            "alias": alias,
                            "title": title,
                            "protocolType": proto,
                            "level": level
                        })

                        if qid and qid not in all_contest_questions[cid]:
                            all_contest_questions[cid][qid] = item
                            new_count += 1
                            print(f"    [Moi in {short_id}] [{alias}] Code {code}: {title} [{proto}]")
                        else:
                            print(f"    [Da co in {short_id}] [{alias}] Code {code}: {title}")

                    student_mappings[username]["contests"][cid] = {
                        "contestName": c_name,
                        "questionsCount": len(q_summary),
                        "newAdded": new_count,
                        "questions": q_summary
                    }
                else:
                    print(f"    [-] Loi lay de {short_id}: HTTP {q_res.status_code}")
                    student_mappings[username]["contests"][cid] = {
                        "contestName": c_name,
                        "error": f"HTTP {q_res.status_code}"
                    }

        except Exception as e:
            print(f"  [-] Loi ngoai le voi {username}: {e}")
            student_mappings[username] = {"status": "exception", "error": str(e)}

        time.sleep(0.3)

    # 3. Luu ket qua cac file JSON
    print("\n--------------------------------------------------")
    print("   TONG KET & LUU FILE")
    print("--------------------------------------------------")
    for cid in contest_ids:
        short_id = cid[:8]
        qs = list(all_contest_questions[cid].values())
        qs.sort(key=lambda x: x.get("question", {}).get("code", 0))

        file_name = f"jnp_{short_id}_all_questions.json"
        out_path = os.path.join(OUTPUT_DIR, file_name)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(qs, f, ensure_ascii=False, indent=2)

        meta = contest_meta.get(cid, {})
        print(f"[+] Contest [{meta.get('code', short_id)}] {meta.get('name', cid)}:")
        print(f"    Tong cau hoi doc nhat: {len(qs)}")
        print(f"    Da luu vao: {out_path}")

    # Luu mapping sinh vien
    mapping_path = os.path.join(OUTPUT_DIR, "contests_student_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(student_mappings, f, ensure_ascii=False, indent=2)
    print(f"[+] Da luu bang mapping sinh vien vao: {mapping_path}")

    # 4. Dong bo voi master question bank
    master_bank = []
    if os.path.exists(MASTER_BANK_FILE):
        try:
            with open(MASTER_BANK_FILE, "r", encoding="utf-8") as f:
                master_bank = json.load(f)
        except Exception:
            master_bank = []

    old_count = len(master_bank)
    existing_ids = set(q.get("id") for q in master_bank)
    existing_codes = set(q.get("code") for q in master_bank)

    added_count = 0
    for cid, qs in all_contest_questions.items():
        for qid, item in qs.items():
            q = item.get("question", {})
            code = q.get("code")
            if qid not in existing_ids and code not in existing_codes:
                clean_q = {
                    "id": q.get("id"),
                    "code": q.get("code"),
                    "alias": q.get("alias"),
                    "title": q.get("title"),
                    "description": q.get("description"),
                    "protocolType": q.get("protocolType"),
                    "level": q.get("level"),
                    "status": q.get("status"),
                    "isPublic": q.get("isPublic", False),
                    "isShared": q.get("isShared", True),
                    "subjectId": q.get("subjectId"),
                    "userAlias": q.get("userAlias"),
                    "examServerHost": q.get("examServerHost", "36.50.135.242")
                }
                master_bank.append(clean_q)
                existing_ids.add(qid)
                if code:
                    existing_codes.add(code)
                added_count += 1

    master_bank.sort(key=lambda x: x.get("code", 0))

    with open(MASTER_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(master_bank, f, ensure_ascii=False, indent=2)

    print(f"[+] Ngan hang de Master ban dau: {old_count} cau")
    print(f"[+] So cau hoi moi bo sung: {added_count} cau")
    print(f"[+] Tong so cau hoi hien co trong Master: {len(master_bank)} cau")
    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool fetch de thi tu he thong PTIT dbapi")
    parser.add_argument("contests", nargs="*", default=DEFAULT_CONTESTS, help="Danh sach Contest ID can fetch (de trong se dung 2 contest mac dinh)")
    args = parser.parse_args()

    fetch_contests(args.contests)

