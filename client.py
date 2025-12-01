import requests
import time
import os
import glob
import webbrowser
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv, set_key, find_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

class PTITSolver:
    def __init__(self):
        # Kiểm tra cấu hình bắt buộc
        self.username = os.getenv('QLDT_USERNAME')
        self.password = os.getenv('QLDT_PASSWORD')
        self.login_url = os.getenv('LOGIN_URL')
        self.base_api_url = os.getenv('BASE_API_URL')
        self.default_db_type = os.getenv('DEFAULT_DB_TYPE')
        self.user_id = None
        
        if not all([self.username, self.password, self.login_url]):
            print("[-] Lỗi: Thiếu thông tin đăng nhập trong file .env")
            exit(1)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        })

    def login_selenium(self):
        """Đăng nhập qua Selenium và lấy Cookies"""
        print(f"[*] Đang khởi động trình duyệt để đăng nhập user: {self.username}...")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') # Chạy ẩn theo yêu cầu
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(self.login_url)
            wait = WebDriverWait(driver, 15)

            # Click button để mở login window nếu cần
            try:
                print("[*] Tìm nút mở login...")
                login_trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".grid.grid-cols-1.gap-4")))
                login_trigger.click()
                print("[*] Đã click nút mở login.")
            except Exception as e:
                print(f"[!] Không tìm thấy hoặc không click được nút login (có thể đã ở trang login): {e}")

            # Chờ và điền username
            user_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#qldt-username")))
            user_input.send_keys(self.username)
            
            # Điền password
            pass_input = driver.find_element(By.CSS_SELECTOR, "#qldt-password")
            pass_input.send_keys(self.password)
            pass_input.submit()
            
            print("[*] Đang chờ đăng nhập thành công...")
            time.sleep(5) 
            
            # Lấy cookies
            selenium_cookies = driver.get_cookies()
            for cookie in selenium_cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            
            # Extract Token
            try:
                ls_keys = driver.execute_script("return Object.keys(localStorage);")
                ss_keys = driver.execute_script("return Object.keys(sessionStorage);")

                token = None
                # Prioritize access_token
                priority_keys = ['access_token', 'accessToken', 'token']
                
                # Check LocalStorage for priority keys
                for pk in priority_keys:
                    for k in ls_keys:
                        if pk == k or pk == k.lower():
                             val = driver.execute_script(f"return localStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found JWT in LocalStorage key '{k}'")
                                 break
                    if token: break
                
                # Fallback to fuzzy search if not found
                if not token:
                    possible_keys = ['token', 'accessToken', 'auth_token', 'jwt', 'user', 'auth']
                    for k in ls_keys:
                        if any(pk in k.lower() for pk in possible_keys) and 'refresh' not in k.lower():
                             val = driver.execute_script(f"return localStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found potential JWT in LocalStorage key '{k}'")
                                 break
            
                # Check SessionStorage if not found
                if not token:
                    possible_keys = ['token', 'accessToken', 'auth_token', 'jwt', 'user', 'auth']
                    for k in ss_keys:
                        if any(pk in k.lower() for pk in possible_keys):
                             val = driver.execute_script(f"return sessionStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found potential JWT in SessionStorage key '{k}'")
                                 break

                if token:
                    self.session.headers.update({'Authorization': f"Bearer {token}"})
                    print("[+] Added Authorization header.")
                else:
                    print("[-] Could not find any JWT-like token.")
            except Exception as e:
                print(f"[-] Error extracting token: {e}")

            print("[+] Đăng nhập thành công! Đã lấy được Cookies và Token.")
            
        except Exception as e:
            print(f"[-] Lỗi đăng nhập: {e}")
            driver.quit()
            exit(1)
        finally:
            driver.quit()

    def get_user_id(self):
        """Lấy User ID từ .env hoặc hỏi người dùng và lưu lại vào .env"""
        current_id = os.getenv('USER_ID')
        
        if current_id and current_id.strip():
            self.user_id = current_id.strip()
            return self.user_id
        
        print("\n[!] Chưa có USER_ID trong file .env")
        print("Hãy nhập User UUID của bạn (lấy từ URL submit history hoặc F12 Network):")
        user_id = input("User UUID: ").strip()
        
        # Lưu ngược lại vào file .env
        env_file = find_dotenv()
        if env_file:
            set_key(env_file, "USER_ID", user_id)
            print(f"[+] Đã lưu USER_ID vào {env_file}")
            
        self.user_id = user_id
        return user_id

    def search_questions(self):
        """Tìm kiếm câu hỏi trong thư mục local"""
        print("\n" + "="*30)
        keyword = input("Nhập từ khóa tìm kiếm (Enter để xem tất cả): ").strip().lower()
        
        problems_dir = "problems"
        if not os.path.exists(problems_dir):
            print(f"[-] Thư mục '{problems_dir}' không tồn tại.")
            return None

        all_files = glob.glob(os.path.join(problems_dir, "*.html"))
        matched_files = []

        for f in all_files:
            filename = os.path.basename(f)
            if keyword in filename.lower():
                matched_files.append(f)
        
        if not matched_files:
            print("[-] Không tìm thấy bài tập nào.")
            return None
        
        print(f"\n[+] Tìm thấy {len(matched_files)} bài tập:")
        # Sort files for consistent display
        matched_files.sort()
        
        for idx, f_path in enumerate(matched_files):
            print(f"{idx + 1}. {os.path.basename(f_path)}")
        
        while True:
            choice = input("\nChọn số thứ tự bài tập (hoặc '0' để quay lại): ").strip()
            if choice == '0':
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(matched_files):
                return matched_files[int(choice) - 1]
            print("[-] Lựa chọn không hợp lệ.")

    def fetch_question(self, file_path):
        """Đọc nội dung bài tập từ file local"""
        print(f"\n[*] Đang đọc file: {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse content
            data = {}
            data['file_path'] = file_path
            
            # Extract ID/UUID from URL API line
            # Line 4: URL API: https://dbapi.ptit.edu.vn/api/app/question/f7c4953d-554f-4ba8-a99b-d58671879c49
            match_id = re.search(r'URL API: .*/([a-f0-9\-]+)', content)
            if match_id:
                data['id'] = match_id.group(1)
            else:
                print("[-] Không tìm thấy ID bài tập trong file.")
                return None

            # Extract Code and Title from filename or content
            # Filename format: SQL132 - Làm quen với LearnSQL.html
            filename = os.path.basename(file_path)
            name_parts = filename.replace('.html', '').split(' - ', 1)
            if len(name_parts) == 2:
                data['questionCode'] = name_parts[0]
                data['title'] = name_parts[1]
            else:
                data['questionCode'] = "UNKNOWN"
                data['title'] = filename

            data['content'] = content
            return data
            
        except Exception as e:
            print(f"[-] Lỗi đọc file: {e}")
            return None

    def display_question(self, data):
        print("\n" + "="*50)
        print(f"MÃ BÀI: {data.get('questionCode')} - {data.get('title')}")
        print(f"ID: {data.get('id')}")
        print("="*50)
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(self.login_url)
            wait = WebDriverWait(driver, 15)

            # Click button để mở login window nếu cần
            try:
                print("[*] Tìm nút mở login...")
                login_trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".grid.grid-cols-1.gap-4")))
                login_trigger.click()
                print("[*] Đã click nút mở login.")
            except Exception as e:
                print(f"[!] Không tìm thấy hoặc không click được nút login (có thể đã ở trang login): {e}")

            # Chờ và điền username
            user_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#qldt-username")))
            user_input.send_keys(self.username)
            
            # Điền password
            pass_input = driver.find_element(By.CSS_SELECTOR, "#qldt-password")
            pass_input.send_keys(self.password)
            pass_input.submit()
            
            print("[*] Đang chờ đăng nhập thành công...")
            time.sleep(5) 
            
            # Lấy cookies
            selenium_cookies = driver.get_cookies()
            for cookie in selenium_cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            
            # Extract Token
            try:
                ls_keys = driver.execute_script("return Object.keys(localStorage);")
                ss_keys = driver.execute_script("return Object.keys(sessionStorage);")

                token = None
                # Prioritize access_token
                priority_keys = ['access_token', 'accessToken', 'token']
                
                # Check LocalStorage for priority keys
                for pk in priority_keys:
                    for k in ls_keys:
                        if pk == k or pk == k.lower():
                             val = driver.execute_script(f"return localStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found JWT in LocalStorage key '{k}'")
                                 break
                    if token: break
                
                # Fallback to fuzzy search if not found
                if not token:
                    possible_keys = ['token', 'accessToken', 'auth_token', 'jwt', 'user', 'auth']
                    for k in ls_keys:
                        if any(pk in k.lower() for pk in possible_keys) and 'refresh' not in k.lower():
                             val = driver.execute_script(f"return localStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found potential JWT in LocalStorage key '{k}'")
                                 break
            
                # Check SessionStorage if not found
                if not token:
                    possible_keys = ['token', 'accessToken', 'auth_token', 'jwt', 'user', 'auth']
                    for k in ss_keys:
                        if any(pk in k.lower() for pk in possible_keys):
                             val = driver.execute_script(f"return sessionStorage.getItem('{k}');")
                             if val and val.startswith('eyJ'):
                                 token = val
                                 # print(f"[+] Found potential JWT in SessionStorage key '{k}'")
                                 break

                if token:
                    self.session.headers.update({'Authorization': f"Bearer {token}"})
                    print("[+] Added Authorization header.")
                else:
                    print("[-] Could not find any JWT-like token.")
            except Exception as e:
                print(f"[-] Error extracting token: {e}")

            print("[+] Đăng nhập thành công! Đã lấy được Cookies và Token.")
            
        except Exception as e:
            print(f"[-] Lỗi đăng nhập: {e}")
            driver.quit()
            exit(1)
        finally:
            driver.quit()

    def get_user_id(self):
        """Lấy User ID từ .env hoặc hỏi người dùng và lưu lại vào .env"""
        current_id = os.getenv('USER_ID')
        
        if current_id and current_id.strip():
            self.user_id = current_id.strip()
            return self.user_id
        
        print("\n[!] Chưa có USER_ID trong file .env")
        print("Hãy nhập User UUID của bạn (lấy từ URL submit history hoặc F12 Network):")
        user_id = input("User UUID: ").strip()
        
        # Lưu ngược lại vào file .env
        env_file = find_dotenv()
        if env_file:
            set_key(env_file, "USER_ID", user_id)
            print(f"[+] Đã lưu USER_ID vào {env_file}")
            
        self.user_id = user_id
        return user_id

    def search_questions(self):
        """Tìm kiếm câu hỏi trong thư mục local"""
        print("\n" + "="*30)
        keyword = input("Nhập từ khóa tìm kiếm (Enter để xem tất cả): ").strip().lower()
        
        problems_dir = "problems"
        if not os.path.exists(problems_dir):
            print(f"[-] Thư mục '{problems_dir}' không tồn tại.")
            return None

        all_files = glob.glob(os.path.join(problems_dir, "*.html"))
        matched_files = []

        for f in all_files:
            filename = os.path.basename(f)
            if keyword in filename.lower():
                matched_files.append(f)
        
        if not matched_files:
            print("[-] Không tìm thấy bài tập nào.")
            return None
        
        print(f"\n[+] Tìm thấy {len(matched_files)} bài tập:")
        # Sort files for consistent display
        matched_files.sort()
        
        for idx, f_path in enumerate(matched_files):
            print(f"{idx + 1}. {os.path.basename(f_path)}")
        
        while True:
            choice = input("\nChọn số thứ tự bài tập (hoặc '0' để quay lại): ").strip()
            if choice == '0':
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(matched_files):
                return matched_files[int(choice) - 1]
            print("[-] Lựa chọn không hợp lệ.")

    def fetch_question(self, file_path):
        """Đọc nội dung bài tập từ file local"""
        print(f"\n[*] Đang đọc file: {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse content
            data = {}
            data['file_path'] = file_path
            
            # Extract ID/UUID from URL API line
            # Line 4: URL API: https://dbapi.ptit.edu.vn/api/app/question/f7c4953d-554f-4ba8-a99b-d58671879c49
            match_id = re.search(r'URL API: .*/([a-f0-9\-]+)', content)
            if match_id:
                data['id'] = match_id.group(1)
            else:
                print("[-] Không tìm thấy ID bài tập trong file.")
                return None

            # Extract Code and Title from filename or content
            # Filename format: SQL132 - Làm quen với LearnSQL.html
            filename = os.path.basename(file_path)
            name_parts = filename.replace('.html', '').split(' - ', 1)
            if len(name_parts) == 2:
                data['questionCode'] = name_parts[0]
                data['title'] = name_parts[1]
            else:
                data['questionCode'] = "UNKNOWN"
                data['title'] = filename

            data['content'] = content
            return data
            
        except Exception as e:
            print(f"[-] Lỗi đọc file: {e}")
            return None

    def display_question(self, data):
        print("\n" + "="*50)
        print(f"MÃ BÀI: {data.get('questionCode')} - {data.get('title')}")
        print(f"ID: {data.get('id')}")
        print("="*50)
        
        # Render HTML in browser
        try:
            # Create a temp file to open in browser if needed, 
            # but we can just open the original local file
            file_path = os.path.abspath(data['file_path'])
            print(f"[*] Đang mở bài tập trong trình duyệt...")
            webbrowser.open(f"file:///{file_path}")
        except Exception as e:
            print(f"[-] Không thể mở trình duyệt: {e}")

    def generate_sql_file(self, question_data):
        filename = "solution.sql"
        # Kiểm tra nếu file đã tồn tại và có nội dung thì không ghi đè header
        if os.path.exists(filename):
             with open(filename, 'r', encoding='utf-8') as f:
                 content = f.read()
                 if f"-- ID: {question_data['id']}" in content:
                     print(f"[+] File '{filename}' đã tồn tại cho bài này.")
                     return filename

        header = f"""-- ID: {question_data['id']}
-- Code: {question_data['questionCode']}
-- Title: {question_data['title']}
-- Yêu cầu: Viết câu lệnh SQL bên dưới
-- ********************************************

"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(header)
            
        print(f"[+] Đã tạo/reset file '{filename}'. Hãy mở và viết code SQL.")
        return filename

    def clean_sql_content(self, sql):
        """Xóa comment và khoảng trắng thừa từ SQL"""
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            # Bỏ qua các dòng bắt đầu bằng --
            if line.strip().startswith('--'):
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines).strip()

    def print_table(self, data):
        """In bảng kết quả đẹp hơn"""
        if not data:
            print("(Không có dữ liệu)")
            return

        # Lấy headers
        headers = list(data[0].keys())
        
        # Tính độ rộng cột
        col_widths = {h: len(h) for h in headers}
        for row in data:
            for h in headers:
                val = str(row.get(h, ''))
                col_widths[h] = max(col_widths[h], len(val))
        
        # Tạo format string
        header_fmt = " | ".join(f"{{:<{col_widths[h]}}}" for h in headers)
        separator = "-+-".join("-" * col_widths[h] for h in headers)
        
        # In bảng
        print(header_fmt.format(*headers))
            "page": 0, "size": 1, "questionId": question_id, "sort": "created_at,desc"
        }
        
        print("[*] Đang kiểm tra kết quả...")
        for i in range(15): # Thử 15 lần
            time.sleep(2)
            try:
                resp = self.session.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('content'):
                        latest_sub = data['content'][0]
                        status = latest_sub['status']
                        
                        # Chỉ return khi có trạng thái cuối cùng
                        if status in ['AC', 'WA', 'TLE', 'RTE', 'CE']:
                            return latest_sub
                        print(f"    ...lần {i+1}: trạng thái {status}")
                else:
                    print(f"[-] Lỗi lấy lịch sử: {resp.status_code} - {resp.text}")
            except Exception:
                pass
        return None

def main():
    # Kiểm tra file .env có tồn tại không
    if not os.path.exists('.env'):
        print("[-] Lỗi: Không tìm thấy file .env. Hãy tạo file cấu hình trước.")
        return

    solver = PTITSolver()
    
    # 1. Login
    solver.login_selenium()
    
    # 2. Lấy User ID
    user_id = solver.get_user_id()
    
    current_question_id = None
    current_question_data = None
    
    while True:
        print("\n" + "="*30)
        print("MENU:")
        print("1. Tìm kiếm bài tập (Local)")
        print("2. Nhập ID bài tập trực tiếp (Disabled)")
        if current_question_id:
            print(f"3. Chạy thử code (Bài đang chọn: {current_question_data.get('questionCode')})")
            print(f"4. Nộp bài (Bài đang chọn: {current_question_data.get('questionCode')})")
        print("0. Thoát")
        
        choice = input("Lựa chọn: ").strip()
        
        if choice == '0':
            break
            
        elif choice == '1':
            file_path = solver.search_questions()
            if file_path:
                current_question_data = solver.fetch_question(file_path)
                if current_question_data:
                    current_question_id = current_question_data.get('id')
                    solver.display_question(current_question_data)
                    solver.generate_sql_file(current_question_data)
                    
        elif choice == '2':
            print("[-] Tính năng nhập ID trực tiếp tạm thời bị vô hiệu hóa trong chế độ local.")
                
        elif choice == '3' and current_question_id:
            try:
                with open("solution.sql", 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                solver.run_query(current_question_id, sql_content)
            except FileNotFoundError:
                print("[-] Không tìm thấy file solution.sql")
                
        elif choice == '4' and current_question_id:
            try:
                with open("solution.sql", 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            except FileNotFoundError:
                print("[-] Không tìm thấy file solution.sql")
                continue

            if solver.submit_solution(current_question_id, sql_content):
                result = solver.check_submission_status(user_id, current_question_id)
                
                if result:
                    status = result['status']
                    test_pass = f"{result.get('testPass')}/{result.get('totalTest')}"
                    
                    if status == 'AC':
                        print(f"\n✅ CHẤP NHẬN (ACCEPTED) | Test: {test_pass}")
                    elif status == 'WA':
                        print(f"\n❌ SAI LÈ (WRONG ANSWER) | Test: {test_pass}")
                    else:
                        print(f"\n⚠️ KẾT QUẢ: {status} | Test: {test_pass}")
                else:
                    print("[-] Timeout: Không lấy được kết quả chấm.")

if __name__ == "__main__":
    main()