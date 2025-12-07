import requests
import time
import os
import glob
import webbrowser
import re
import json
import base64
from datetime import datetime
from dotenv import load_dotenv, set_key, find_dotenv
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Tải biến môi trường từ file .env
load_dotenv()

class Client:
    def __init__(self):
        # Kiểm tra cấu hình bắt buộc
        self.username = os.getenv('QLDT_USERNAME')
        self.password = os.getenv('QLDT_PASSWORD')
        self.login_url = os.getenv('LOGIN_URL')
        self.base_api_url = os.getenv('BASE_API_URL')
        self.auth_base_url = os.getenv('AUTH_API_URL')
        self.user_id = None
        self.refresh_token = None
        
        if not all([self.username, self.password, self.login_url]):
            print(Fore.RED + "[-] Lỗi: Thiếu thông tin đăng nhập trong file .env")
            exit(1)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        })
    
    def login_api(self):
        """Đăng nhập qua API và lưu access token"""
        print(Fore.CYAN + f"[*] Đang đăng nhập user **{self.username}** qua API...")
        url = f'{self.auth_base_url.rstrip("/")}/auth/ptit-login'
        payload = {"username": self.username, "password": self.password}

        try:
            resp = self.session.post(url, json=payload, headers={
                "Content-Type": "application/json", 
                "User-Agent": self.session.headers.get('User-Agent', '')
            })

            if resp.status_code != 200:
                print(Fore.RED + f"[-] Đăng nhập API thất bại: {resp.status_code} {resp.text}")
                return False
            
            data = resp.json()
            access_token = data.get('accessToken') or data.get('access_token')
            if not access_token:
                print(Fore.RED + "[-] API không trả về accessToken.")
                return False
            self._set_tokens(access_token)
            # Lấy user id nếu có trong payload
            possible_keys = ['userId', 'id', 'sub']
            for k in possible_keys:
                if k in data:
                    self._save_user_id(data[k])
                    break
            print(Fore.GREEN + "[+] Đăng nhập API thành công. Đã lưu token.")
            return True
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi đăng nhập API: {e}")
            return False

    def _save_user_id(self, user_id):
        """Lưu User ID vào file .env"""
        env_file = find_dotenv()
        if not env_file:
            with open('.env', 'w') as f:
                pass
            env_file = find_dotenv()
            
        if env_file:
            set_key(env_file, "USER_ID", str(user_id))
            print(Fore.GREEN + f"[+] Đã lưu USER_ID vào {env_file}")
        self.user_id = str(user_id)

    def _set_tokens(self, access_token, refresh_token=None):
        """Lưu access token vào session. refresh_token hiện không dùng."""
        if access_token:
            self.session.headers.update({'Authorization': f"Bearer {access_token}"})
        # Không dùng refresh token nữa
        self.refresh_token = None

    def _relogin(self):
        """Thử đăng nhập lại khi gặp 401. Trả về token mới hoặc None."""
        print(Fore.YELLOW + "[*] Token hết hạn, thử đăng nhập lại...")
        try:
            if self.login_api():
                auth_header = self.session.headers.get('Authorization')
                if auth_header and ' ' in auth_header:
                    return auth_header.split(' ', 1)[1]
                return True
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi đăng nhập lại: {e}")
        return None

    def _request(self, method, url, **kwargs):
        """Gửi request, tự refresh token nếu 401. Trả về resp"""
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code == 401:
            new_token = self._relogin()
            if new_token:
                resp = self.session.request(method, url, **kwargs)
        return resp

    def _get_user_id_from_token(self):
        """Giải mã JWT token để lấy User ID (base64url, không padding thừa)"""
        try:
            auth_header = self.session.headers.get('Authorization')
            if not auth_header or ' ' not in auth_header:
                return None

            token = auth_header.split(' ')[1]
            parts = token.split('.')
            if len(parts) != 3:
                return None

            payload = parts[1]
            padded = payload + '=' * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            data = json.loads(decoded.decode('utf-8'))

            possible_keys = ['id', 'userId', 'sub', 'user_id', 'unique_name']
            for k in possible_keys:
                if k in data:
                    return data[k]

            if isinstance(data.get('user'), dict):
                for k in possible_keys:
                    if k in data['user']:
                        return data['user'][k]

            return None
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi giải mã token: {e}")
            return None

    def get_user_id(self):
        """Lấy User ID từ .env, Token hoặc API; cuối cùng hỏi người dùng"""
        current_id = os.getenv('USER_ID')
        if current_id and current_id.strip():
            self.user_id = current_id.strip()
            return self.user_id

        print(Fore.CYAN + "[*] Đang lấy USER_ID từ token...")
        token_id = self._get_user_id_from_token()
        if token_id:
            print(Fore.GREEN + f"[+] Tìm thấy USER_ID từ token: {token_id}")
            self._save_user_id(token_id)
            return token_id

        print(Fore.CYAN + "[*] Đang lấy USER_ID từ API...")
        try:
            url = "https://dbapi.ptit.edu.vn/api/auth/users/info"
            resp = self._request('get', url)
            if resp.status_code == 200:
                data = resp.json()
                api_id = data.get('id')
                if api_id:
                    print(Fore.GREEN + f"[+] Lấy được USER_ID từ API: {api_id}")
                    self._save_user_id(api_id)
                    return api_id
                print(Fore.YELLOW + "[-] API không trả về USER_ID.")
            else:
                print(Fore.YELLOW + f"[-] Lỗi API khi lấy USER_ID: {resp.status_code}")
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi kết nối API: {e}")

        print(Fore.YELLOW + "\n[!] Không tự động lấy được USER_ID. Hãy nhập thủ công:")
        user_id = input("User UUID: ").strip()
        self._save_user_id(user_id)
        return user_id

    def view_submit_history(self, question_id):
        """Display full submission history for a problem"""
        if not self.user_id:
            print(Fore.RED + "[-] Không có USER_ID.")
            return
        
        url = f"{self.base_api_url}/submit-history/user/{self.user_id}"
        params = {
            "questionId": question_id,
            "page": 0,
            "size": 20  # Get last 20 submissions
        }
        
        print(Fore.CYAN + f"\n[*] Đang lấy lịch sử nộp bài...")
        
        try:
            resp = self._request('get', url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                submissions = data.get('content', [])
                
                if not submissions:
                    print(Fore.YELLOW + "[-] Chưa có lần nộp bài nào.")
                    return
                
                print(Fore.GREEN + f"\n[+] Tìm thấy {len(submissions)} lần nộp bài:\n")
                print(Fore.CYAN + "="*80)
                
                for idx, sub in enumerate(submissions, 1):
                    status = sub.get('status', 'N/A')
                    test_pass = f"{sub.get('testPass', 0)}/{sub.get('totalTest', 0)}"
                    created_at = sub.get('createdAt', 'N/A')
                    if created_at != 'N/A':
                        try:
                            # Parse ISO format: 2025-12-02T17:52:10.098051
                            dt = datetime.fromisoformat(created_at)
                            created_at = dt.strftime("%H:%M:%S %d/%m/%Y")
                        except ValueError:
                            pass  # Keep original string if parsing fails
                    
                    # Color based on status
                    if status == 'AC':
                        status_color = Fore.GREEN + f"✅ {status}"
                    elif status == 'WA':
                        status_color = Fore.RED + f"❌ {status}"
                    elif status == 'TLE':
                        status_color = Fore.MAGENTA + f"⏳ {status}"
                    else:
                        status_color = Fore.YELLOW + f"⚠️  {status}"
                    
                    print(f"{idx}. {status_color} | Test: {test_pass} | Time: {created_at}")
                
                print(Fore.CYAN + "="*80)
            else:
                print(Fore.RED + f"[-] Lỗi API: {resp.status_code}")
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi kết nối: {e}")

    def browse_by_sections(self):
        """Browse problems organized by sections/categories"""
        print(Fore.CYAN + "="*30)
        problems_dir = "problems"
        
        if not os.path.exists(problems_dir):
            print(Fore.RED + f"[-] Thư mục '{problems_dir}' không tồn tại.")
            return None
        
        # Get all subdirectories (sections)
        sections = [d for d in os.listdir(problems_dir) 
                   if os.path.isdir(os.path.join(problems_dir, d)) and not d == 'img']
        
        if not sections:
            print(Fore.YELLOW + "[!] Không tìm thấy sections. Hãy chạy organize_problems.py trước.")
            return None
        
        sections.sort()
        
        print(Fore.GREEN + f"\n[+] Tìm thấy {len(sections)} sections:")
        for idx, section in enumerate(sections, 1):
            # Count problems in this section
            section_path = os.path.join(problems_dir, section)
            # Use recursive glob to count all html files in subfolders if any
            problem_count = len(glob.glob(os.path.join(section_path, "**", "*.html"), recursive=True))
            print(f"{idx}. {section} ({problem_count} bài)")
        
        while True:
            choice = input("\nChọn số thứ tự section (hoặc '0' để quay lại): ").strip()
            if choice == '0':
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(sections):
                selected_section = sections[int(choice) - 1]
                return self._browse_section_problems(selected_section)
            print(Fore.RED + "[-] Lựa chọn không hợp lệ.")

    def _browse_section_problems(self, section):
        """Browse problems within a specific section"""
        print(Fore.CYAN + f"\n{'='*30}")
        print(Fore.CYAN + f"SECTION: {section}")
        print(Fore.CYAN + f"{'='*30}")
        
        section_path = os.path.join("problems", section)
        # Recursive search in case there are nested folders
        all_files = glob.glob(os.path.join(section_path, "**", "*.html"), recursive=True)
        
        if not all_files:
            print(Fore.YELLOW + "[-] Không có bài tập trong section này.")
            return None
        
        all_files.sort()
        
        print(Fore.GREEN + f"\n[+] {len(all_files)} bài tập. Đang kiểm tra trạng thái...")
        
        # Extract IDs and fetch status
        question_ids = []
        file_id_map = {}
        
        for f_path in all_files:
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                match_id = re.search(r'URL API: .*/([a-f0-9\-]+)', content)
                if match_id:
                    qid = match_id.group(1)
                    question_ids.append(qid)
                    file_id_map[f_path] = qid
            except:
                pass
        
        status_map = self.check_complete_status(question_ids)
        
        # Filter loop
        current_filter = 'ALL' # ALL, AC, ATTEMPTED, UNSUBMITTED
        
        while True:
            filtered_files = []
            for f_path in all_files:
                qid = file_id_map.get(f_path)
                status = status_map.get(qid)
                
                if current_filter == 'ALL':
                    filtered_files.append(f_path)
                elif current_filter == 'AC' and status == 'AC':
                    filtered_files.append(f_path)
                elif current_filter == 'ATTEMPTED' and status and status != 'AC':
                    filtered_files.append(f_path)
                elif current_filter == 'UNSUBMITTED' and not status:
                    filtered_files.append(f_path)

            print(Fore.CYAN + f"\n--- DANH SÁCH BÀI TẬP ({current_filter}) ---")
            for idx, f_path in enumerate(filtered_files, 1):
                filename = os.path.basename(f_path)
                qid = file_id_map.get(f_path)
                status = status_map.get(qid)
                
                status_icon = "  "
                color = Fore.WHITE
                
                if status == 'AC':
                    status_icon = "✅"
                    color = Fore.GREEN
                elif status:
                    status_icon = "❌"
                    color = Fore.RED
                
                print(f"{color}{idx}. {status_icon} {filename}{Style.RESET_ALL}")
            
            print(Fore.CYAN + "-"*40)
            print("Filter: [A]ll | [C]ompleted (AC) | [T]ried | [U]nsubmitted")
            choice = input("Chọn bài (số) hoặc Filter (A/C/T/U) hoặc '0' để quay lại: ").strip().upper()
            
            if choice == '0':
                return None
            elif choice == 'A':
                current_filter = 'ALL'
            elif choice == 'C':
                current_filter = 'AC'
            elif choice == 'T':
                current_filter = 'ATTEMPTED'
            elif choice == 'U':
                current_filter = 'UNSUBMITTED'
            elif choice.isdigit() and 1 <= int(choice) <= len(filtered_files):
                return filtered_files[int(choice) - 1]
            else:
                print(Fore.RED + "[-] Lựa chọn không hợp lệ.")

    def search_questions(self):
        """Tìm kiếm câu hỏi trong thư mục local (Recursive)"""
        print(Fore.CYAN + "="*30)
        keyword = input("Nhập từ khóa tìm kiếm (Enter để xem tất cả): ").strip().lower()
        
        problems_dir = "problems"
        if not os.path.exists(problems_dir):
            print(Fore.RED + f"[-] Thư mục '{problems_dir}' không tồn tại.")
            return None

        # Search recursively for all .html files
        all_files = glob.glob(os.path.join(problems_dir, "**", "*.html"), recursive=True)
        matched_files = []

        for f in all_files:
            filename = os.path.basename(f)
            if keyword in filename.lower():
                matched_files.append(f)
        
        if not matched_files:
            print(Fore.YELLOW + "[-] Không tìm thấy bài tập nào.")
            return None
        
        print(Fore.GREEN + f"\n[+] Tìm thấy {len(matched_files)} bài tập. Đang kiểm tra trạng thái...")
        matched_files.sort()

        # Extract IDs and fetch status
        question_ids = []
        file_id_map = {}
        
        for f_path in matched_files:
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                match_id = re.search(r'URL API: .*/([a-f0-9\-]+)', content)
                if match_id:
                    qid = match_id.group(1)
                    question_ids.append(qid)
                    file_id_map[f_path] = qid
            except:
                pass
        
        status_map = self.check_complete_status(question_ids)
        
        # Filter loop
        current_filter = 'ALL' # ALL, AC, ATTEMPTED, UNSUBMITTED
        
        while True:
            filtered_files = []
            for f_path in matched_files:
                qid = file_id_map.get(f_path)
                status = status_map.get(qid)
                
                if current_filter == 'ALL':
                    filtered_files.append(f_path)
                elif current_filter == 'AC' and status == 'AC':
                    filtered_files.append(f_path)
                elif current_filter == 'ATTEMPTED' and status and status != 'AC':
                    filtered_files.append(f_path)
                elif current_filter == 'UNSUBMITTED' and not status:
                    filtered_files.append(f_path)

            print(Fore.CYAN + f"\n--- DANH SÁCH BÀI TẬP ({current_filter}) ---")
            for idx, f_path in enumerate(filtered_files, 1):
                rel_path = os.path.relpath(f_path, problems_dir)
                qid = file_id_map.get(f_path)
                status = status_map.get(qid)
                
                status_icon = "  "
                color = Fore.WHITE
                
                if status == 'AC':
                    status_icon = "✅"
                    color = Fore.GREEN
                elif status:
                    status_icon = "❌"
                    color = Fore.RED
                
                print(f"{color}{idx}. {status_icon} {rel_path}{Style.RESET_ALL}")
            
            print(Fore.CYAN + "-"*40)
            print("Filter: [A]ll | [C]ompleted (AC) | [T]ried | [U]nsubmitted")
            choice = input("Chọn bài (số) hoặc Filter (A/C/T/U) hoặc '0' để quay lại: ").strip().upper()
            
            if choice == '0':
                return None
            elif choice == 'A':
                current_filter = 'ALL'
            elif choice == 'C':
                current_filter = 'AC'
            elif choice == 'T':
                current_filter = 'ATTEMPTED'
            elif choice == 'U':
                current_filter = 'UNSUBMITTED'
            elif choice.isdigit() and 1 <= int(choice) <= len(filtered_files):
                return filtered_files[int(choice) - 1]
            else:
                print(Fore.RED + "[-] Lựa chọn không hợp lệ.")

    def fetch_question(self, file_path):
        """Đọc nội dung bài tập từ file local và lấy thông tin từ API"""
        print(Fore.CYAN + f"\n[*] Đang đọc file: {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = {}
            data['file_path'] = file_path
            
            match_id = re.search(r'URL API: .*/([a-f0-9\-]+)', content)
            if match_id:
                data['id'] = match_id.group(1)
            else:
                print(Fore.RED + "[-] Không tìm thấy ID bài tập trong file.")
                return None

            filename = os.path.basename(file_path)
            name_parts = filename.replace('.html', '').split(' - ', 1)
            if len(name_parts) == 2:
                data['questionCode'] = name_parts[0]
                data['title'] = name_parts[1]
            else:
                data['questionCode'] = "UNKNOWN"
                data['title'] = filename

            data['content'] = content
            
            # Fetch details from API to get DB types
            try:
                api_url = f"{self.base_api_url}/question/{data['id']}"
                resp = self._request('get', api_url)
                if resp.status_code == 200:
                    api_data = resp.json()
                    data['api_data'] = api_data
                    
                    db_types = []
                    if 'questionDetails' in api_data:
                        for qd in api_data['questionDetails']:
                            if 'typeDatabase' in qd:
                                db_types.append(qd['typeDatabase'])
                    data['db_types'] = db_types
                    
                    if db_types:
                        names = [db['name'] for db in db_types]
                        print(Fore.GREEN + f"[+] Đã lấy thông tin DB: {', '.join(names)}")
                    else:
                        print(Fore.YELLOW + "[-] API trả về danh sách DB rỗng.")
                else:
                    print(Fore.YELLOW + f"[-] Không thể lấy thông tin API (Code {resp.status_code}).")
            except Exception as e:
                print(Fore.RED + f"[-] Lỗi khi gọi API chi tiết: {e}")

            return data
            
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi đọc file: {e}")
            return None

    def _get_db_type_id(self, question_data):
        """Lấy ID của loại database phù hợp nhất"""
        selected_id = None
        if question_data and question_data.get('db_types'):
            db_types = question_data['db_types']
            print(Fore.GREEN + f"[+] DB Types: {', '.join([db['name'] for db in db_types])}")
            for db in db_types:
                if 'mysql' in db['name'].lower():
                    selected_id = db['id']
                    break
            if not selected_id and db_types:
                selected_id = db_types[0]['id']
        
        if selected_id:
            return selected_id
            
        default_id = os.getenv('DEFAULT_DB_TYPE', '11111111-1111-1111-1111-111111111111')
        print(Fore.YELLOW + f"[!] Không tìm thấy DB Type phù hợp, dùng mặc định: {default_id}")
        return default_id

    def display_question(self, data):
        print(Fore.CYAN + "\n" + "="*50)
        print(f"MÃ BÀI: {data.get('questionCode')} - {data.get('title')}")
        print(f"ID: {data.get('id')}")
        if data.get('db_types'):
             names = [db['name'] for db in data['db_types']]
             print(f"DB Support: {', '.join(names)}")
        print(Fore.CYAN + "="*50)
        
        try:
            file_path = os.path.abspath(data['file_path'])
            print(Fore.CYAN + f"[*] Đang mở bài tập trong trình duyệt...")
            webbrowser.open(f"file:///{file_path}")
        except Exception as e:
            print(Fore.RED + f"[-] Không thể mở trình duyệt: {e}")

    def generate_sql_file(self, question_data):
        filename = "solution.sql"
        if os.path.exists(filename):
             with open(filename, 'r', encoding='utf-8') as f:
                 content = f.read()
                 if f"-- ID: {question_data['id']}" in content:
                     print(Fore.YELLOW + f"[+] File '{filename}' đã tồn tại cho bài này.")
                     return filename

        header = f"""-- ID: {question_data['id']}
-- Code: {question_data['questionCode']}
-- Title: {question_data['title']}
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(header)
            
        print(Fore.GREEN + f"[+] Đã tạo/reset file '{filename}'. Hãy mở và viết code SQL.")
        return filename

    def clean_sql_content(self, sql):
        """Xóa comment và khoảng trắng thừa từ SQL"""
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith('--'):
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines).strip().rstrip(';')

    def print_table(self, data):
        """In bảng kết quả đẹp hơn"""
        if not data:
            print(Fore.YELLOW + "(Không có dữ liệu)")
            return

        headers = list(data[0].keys())
        col_widths = {h: len(h) for h in headers}
        for row in data:
            for h in headers:
                val = str(row.get(h, ''))
                col_widths[h] = max(col_widths[h], len(val))
        
        header_fmt = " | ".join(f"{{:<{col_widths[h]}}}" for h in headers)
        separator = "-+-".join("-" * col_widths[h] for h in headers)
        
        print(header_fmt.format(*headers))
        print(separator)
        for row in data:
            print(header_fmt.format(*[str(row.get(h, '')) for h in headers]))

    def run_query(self, question_id, sql, question_data=None):
        """Chạy thử query (Dry Run)"""
        print(Fore.CYAN + f"\n[*] Đang chạy thử query cho bài {question_id}...")
        
        sql = self.clean_sql_content(sql)
        if not sql:
            print(Fore.RED + "[-] SQL rỗng.")
            return
        
        payload = {
            "questionId": question_id,
            "sql": sql,
            "typeDatabaseId": self._get_db_type_id(question_data)
        }
        
        try:
            url = f"{self.base_api_url}/executor/user"
            resp = self._request('post', url, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 1:
                    print(Fore.GREEN + "[+] Chạy query thành công!")
                    result = data.get('result', [])
                    self.print_table(result)
                else:
                    print(Fore.RED + f"[-] Lỗi chạy query: {data.get('result')}")
            else:
                print(Fore.RED + f"[-] Lỗi API: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi kết nối: {e}")

    def submit_solution(self, question_id, sql, question_data=None):
        """Nộp bài"""
        print(Fore.CYAN + f"\n[*] Đang nộp bài {question_id}...")
        
        sql = self.clean_sql_content(sql)
        if not sql:
            print(Fore.RED + "[-] SQL rỗng.")
            return False

        payload = {
            "questionId": question_id,
            "sql": sql,
            "typeDatabaseId": self._get_db_type_id(question_data)
        }
        
        try:
            url = f"{self.base_api_url}/executor/submit"
            resp = self._request('post', url, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                print(Fore.GREEN + "[+] Nộp bài thành công! Đang chấm...")
                return True
            else:
                print(Fore.RED + f"[-] Lỗi API: {resp.status_code}")
                return False
        except Exception as e:
            print(Fore.RED + f"[-] Lỗi kết nối: {e}")
            return False

    def check_submission_status(self, user_id, question_id):
        print(Fore.CYAN + "[*] Đang kiểm tra kết quả...")
        url = f"{self.base_api_url}/submit-history/user/{user_id}"
        params = {
            "questionId": question_id,
            "page": 0,
            "size": 1
        }
        
        for i in range(15): # Thử 15 lần
            time.sleep(2)
            try:
                resp = self._request('get', url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('content'):
                        latest_sub = data['content'][0]
                        status = latest_sub['status']
                        
                        if status in ['AC', 'WA', 'TLE', 'RTE', 'CE']:
                            return latest_sub
                        print(Fore.YELLOW + f"    ...lần {i+1}: trạng thái {status}")
                else:
                    print(Fore.RED + f"[-] Lỗi lấy lịch sử: {resp.status_code}")
            except Exception:
                pass
        return None

    def check_complete_status(self, question_ids):
        """Check status for multiple questions"""
        if not self.user_id or not question_ids:
            return {}
            
        url = f"{self.base_api_url}/submit-history/check/complete"
        payload = {
            "questionIds": question_ids,
            "userId": self.user_id
        }
        
        try:
            resp = self._request('post', url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                # Map questionId -> status
                status_map = {}
                for item in data:
                    status_map[item['questionId']] = item['status']
                return status_map
        except Exception:
            pass
        return {}

def main():
    if not os.path.exists('.env'):
        print(Fore.RED + "[-] Lỗi: Không tìm thấy file .env. Hãy tạo file cấu hình trước.")
        return

    client = Client()
    
    # 1. Login
    # client.login_selenium()
    if not client.login_api():
        print(Fore.RED + "[-] Đăng nhập thất bại. Dừng chương trình.")
        return
    
    # 2. Lấy User ID
    user_id = client.get_user_id()
    current_question_id = None
    current_question_data = None
    
    while True:
        print(Fore.CYAN + "\n" + "="*30)
        print("MENU:")
        print("1. Tìm kiếm bài tập (Local)")
        print("2. Duyệt bài tập theo Section")
        if current_question_id:
            print(f"3. Chạy thử code (Bài đang chọn: {current_question_data.get('questionCode')})")
            print(f"4. Nộp bài (Bài đang chọn: {current_question_data.get('questionCode')})")
            print("5. Xem lịch sử nộp bài")
        print("0. Thoát")
        
        choice = input("Lựa chọn: ").strip()
        
        if choice == '0':
            break
            
        elif choice == '1':
            file_path = client.search_questions()
            if file_path:
                current_question_data = client.fetch_question(file_path)
                if current_question_data:
                    current_question_id = current_question_data.get('id')
                    client.display_question(current_question_data)
                    client.generate_sql_file(current_question_data)

        elif choice == '2':
            file_path = client.browse_by_sections()
            if file_path:
                current_question_data = client.fetch_question(file_path)
                if current_question_data:
                    current_question_id = current_question_data.get('id')
                    client.display_question(current_question_data)
                    client.generate_sql_file(current_question_data)
                    
        elif choice == '3' and current_question_id:
            try:
                with open("solution.sql", 'r', encoding='utf-8-sig') as f:
                    sql_content = f.read()
                client.run_query(current_question_id, sql_content, current_question_data)
            except FileNotFoundError:
                print(Fore.RED + "[-] Không tìm thấy file solution.sql")
                
        elif choice == '4' and current_question_id:
            try:
                with open("solution.sql", 'r', encoding='utf-8-sig') as f:
                    sql_content = f.read()
            except FileNotFoundError:
                print(Fore.RED + "[-] Không tìm thấy file solution.sql")
                continue

            if client.submit_solution(current_question_id, sql_content, current_question_data):
                result = client.check_submission_status(user_id, current_question_id)
                
                if result:
                    status = result['status']
                    test_pass = f"{result.get('testPass')}/{result.get('totalTest')}"
                    
                    if status == 'AC':
                        print(Fore.GREEN + f"\n✅ CHẤP NHẬN (ACCEPTED) | Test: {test_pass}")
                    elif status == 'WA':
                        print(Fore.RED + f"\n❌ SAI LÈ (WRONG ANSWER) | Test: {test_pass}")
                    elif status == 'TLE':
                        print(Fore.RED + f"\n⏳ QUÁ THỜI GIAN (TIME LIMIT EXCEEDED) | Test: {test_pass}")
                    else:
                        print(Fore.MAGENTA + f"\n⚠️ KẾT QUẢ: {status} | Test: {test_pass}")
                else:
                    print(Fore.RED + "[-] Timeout: Không lấy được kết quả chấm.")

        elif choice == '5' and current_question_id:
            client.view_submit_history(current_question_id)

if __name__ == "__main__":
    main()