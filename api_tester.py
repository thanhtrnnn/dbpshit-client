from client import Client
import json
from colorama import Fore, Style

class APITester(Client):
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

if __name__ == "__main__":
    tester = APITester()
    # Use the robust login from the parent Client class
    tester.login_selenium()
    print(tester.session.headers)
    # Run tests
    tester.test_search()
    # tester.test_executor()
