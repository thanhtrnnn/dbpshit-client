from solver import PTITSolver
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class APITester(PTITSolver):
    def login_selenium(self):
        super().login_selenium()
        # Extract token from LocalStorage
        print("[*] Extracting token from LocalStorage...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Re-attach to the session if possible, but selenium doesn't support that easily.
        # We need to do this DURING the main login_selenium call or modify PTITSolver.
        # Since we are inheriting, let's just modify PTITSolver in solver.py directly 
        # as it is the most efficient way and we are confident in the plan.
        # BUT, for this tester, we will just re-implement login here to get the token.
        
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(self.login_url)
            wait = WebDriverWait(driver, 20) # Increased timeout
            
            # Try to handle the login trigger button if it exists
            try:
                print("[*] Looking for login trigger button...")
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".grid.grid-cols-1.gap-4")))
                btn.click()
                print("[*] Clicked login trigger button.")
            except Exception as e:
                print(f"[*] Login trigger button not found or not clickable (might be already on login page): {e}")

            print("[*] Waiting for username field...")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#qldt-username"))).send_keys(self.username)
            driver.find_element(By.CSS_SELECTOR, "#qldt-password").send_keys(self.password)
            
            # Click submit instead of .submit() on element, sometimes safer
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']") 
            # If explicit submit button exists, use it. Otherwise fallback.
            if submit_btn:
                 submit_btn.click()
            else:
                 driver.find_element(By.CSS_SELECTOR, "#qldt-password").submit()
            
            print("[*] Submitted credentials. Waiting for navigation...")
            time.sleep(10) # Increased wait time
            
            # Check if we are still on login page
            if "login" in driver.current_url:
                 print(f"[-] Still on login page: {driver.current_url}")
            
            # Extract Token
            print("[*] Attempting to extract token...")
            token = driver.execute_script("return localStorage.getItem('token') || localStorage.getItem('accessToken') || localStorage.getItem('auth_token');")
            if token:
                print(f"[+] Token found: {token[:20]}...")
                self.session.headers.update({'Authorization': f"Bearer {token}"})
            else:
                print("[-] Token NOT found in LocalStorage")
                # Try looking at cookies just in case
                # print(driver.get_cookies())

            for cookie in driver.get_cookies():
                self.session.cookies.set(cookie['name'], cookie['value'])
                
        except Exception as e:
            print(f"[-] Login failed: {e}")
        finally:
            driver.quit()

    def test_executor(self):
        print("\n=== TESTING EXECUTOR ENDPOINTS ===")
        # We need a valid question ID. Let's use the one found earlier: f7c4953d-554f-4ba8-a99b-d58671879c49 (SQL132)
        question_id = "f7c4953d-554f-4ba8-a99b-d58671879c49"
        sql = "SELECT * FROM LearnSQL;"
        
        url = f"{self.base_api_url}/executor/user"
        payload = {
            "questionId": question_id,
            "sql": sql,
            "typeDatabaseId": "11111111-1111-1111-1111-111111111111"
        }
        
        self._make_request("POST /executor/user (Run Query)", "POST", url, json=payload)

    def _make_request(self, name, method, url, params=None, json=None):
        print(f"\n[*] Testing: {name}")
        try:
            if method == "GET":
                resp = self.session.get(url, params=params)
            else:
                resp = self.session.post(url, json=json, params=params)
            
            print(f"    Status: {resp.status_code}")
            print(f"    Response: {resp.text[:300]}...") # Truncate
        except Exception as e:
            print(f"    Error: {e}")

if __name__ == "__main__":
    tester = APITester()
    tester.login_selenium()
    # tester.test_search()
    tester.test_executor()
