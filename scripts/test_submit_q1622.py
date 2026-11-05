import json
import socket
import time
import requests

API_HOST = "https://dbapi.ptit.edu.vn"
AUTH_URL = f"{API_HOST}/api/auth/auth/ptit-login"
CONTEST_ID = "f66109d7-a13e-4f54-8fdb-d98e6c521617"

STUDENTS = [
    ("B23DCDT024", "024205001358"),
    ("B23DCAT144", "001205034592"),
]

def login(username, password):
    res = requests.post(AUTH_URL, json={"username": username, "password": password}, timeout=10)
    if res.status_code == 200:
        return res.json().get("accessToken")
    print(f"Login failed for {username}: {res.status_code} - {res.text}")
    return None

def get_contest_questions(token, contest_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_HOST}/api/app/jnp-submission/contest/{contest_id}/questions"
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        return res.json()
    print(f"Get questions error: {res.status_code} - {res.text}")
    return []

def check_completion_status(token, question_alias, exam_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_HOST}/api/app/jnp-submission/completion-status"
    params = {"questionAlias": question_alias}
    if exam_id:
        params["examId"] = exam_id
    res = requests.get(url, headers=headers, params=params, timeout=10)
    return res.status_code, res.text

def check_contest_completion(token, exam_id):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{API_HOST}/api/app/jnp-submission/check/complete/contest"
    payload = {"contestId": exam_id, "examId": exam_id}
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    return res.status_code, res.text

def submit_source(token, question_alias, source_code, exam_id=None, course_id=None, field_mode="both"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = f"{API_HOST}/api/app/jnp-submission/source"
    
    payload = {
        "questionAlias": question_alias,
        "courseId": course_id,
        "examId": exam_id
    }
    if field_mode == "sourceCode":
        payload["sourceCode"] = source_code
    elif field_mode == "source":
        payload["source"] = source_code
    else:
        payload["sourceCode"] = source_code
        payload["source"] = source_code

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    return res.status_code, res.text

JAVA_SOLUTION_Q1622 = """import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

public class Solution {
    public static void main(String[] args) {
        String serverHost = "36.50.135.242";
        int serverPort = 2208;
        String studentCode = "B23DCDT024";
        String qCode = "Stpr1AbW";

        try (DatagramSocket socket = new DatagramSocket()) {
            socket.setSoTimeout(5000);
            InetAddress address = InetAddress.getByName(serverHost);

            // Phase 1: Gui ;studentCode;qCode
            String initialMessage = ";" + studentCode + ";" + qCode;
            byte[] sendData1 = initialMessage.getBytes();
            DatagramPacket sendPacket1 = new DatagramPacket(sendData1, sendData1.length, address, serverPort);
            socket.send(sendPacket1);

            // Phase 2: Nhan requestId;data
            byte[] receiveBuffer = new byte[4096];
            DatagramPacket receivePacket = new DatagramPacket(receiveBuffer, receiveBuffer.length);
            socket.receive(receivePacket);

            String receivedStr = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();
            int firstSemi = receivedStr.indexOf(';');
            if (firstSemi == -1) {
                return;
            }

            String requestId = receivedStr.substring(0, firstSemi);
            String data = receivedStr.substring(firstSemi + 1);

            // Xu ly che du lieu:
            // email: [EMAIL]
            // phone: [PHONE]
            // token: token=[TOKEN]
            String masked = data.replaceAll("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}", "[EMAIL]");
            masked = masked.replaceAll("\\\\b\\\\d{10,11}\\\\b", "[PHONE]");
            masked = masked.replaceAll("token=[a-zA-Z0-9]+", "token=[TOKEN]");

            // Gui dap an: requestId;masked
            String answer = requestId + ";" + masked;
            byte[] sendData2 = answer.getBytes();
            DatagramPacket sendPacket2 = new DatagramPacket(sendData2, sendData2.length, address, serverPort);
            socket.send(sendPacket2);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
"""

def test_udp_socket(host, port, student_code, q_code):
    print(f"[*] Testing UDP Socket {host}:{port} with studentCode={student_code}, qCode={q_code}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)
    msg = f";{student_code};{q_code}"
    try:
        sock.sendto(msg.encode("utf-8"), (host, port))
        data, addr = sock.recvfrom(4096)
        resp = data.decode("utf-8", errors="replace")
        print(f"[+] UDP Server responded: {resp}")
        return True, resp
    except socket.timeout:
        print("[-] UDP Socket timed out (server might not be currently hosting this contest question session).")
        return False, None
    except Exception as e:
        print(f"[-] UDP Socket error: {e}")
        return False, None
    finally:
        sock.close()

def main():
    print("=== TEST SUBMITTING NON-PUBLIC CONTEST QUESTION Q1622 ===")
    
    # Check student accounts
    for username, password in STUDENTS:
        print(f"\n==========================================")
        print(f"Testing with account: {username}")
        token = login(username, password)
        if not token:
            continue
        
        print(f"[+] Login OK for {username}")
        
        # Get questions for contest f66109d7-a13e-4f54-8fdb-d98e6c521617
        questions = get_contest_questions(token, CONTEST_ID)
        print(f"[*] Found {len(questions)} questions in contest {CONTEST_ID}")
        
        q1622_item = None
        for item in questions:
            q = item.get("question", {})
            if str(q.get("code")) == "1622" or q.get("alias") == "Q1622":
                q1622_item = q
                break
        
        if not q1622_item:
            print("[-] Q1622 not found for this user in contest!")
            continue
            
        q_code = q1622_item.get("userAlias")
        q_alias = q1622_item.get("alias")
        q_id = q1622_item.get("id")
        server_host = q1622_item.get("examServerHost", "36.50.135.242")
        print(f"[+] Found Q1622:")
        print(f"    - ID: {q_id}")
        print(f"    - Alias: {q_alias}")
        print(f"    - userAlias (qCode): {q_code}")
        print(f"    - isPublic: {q1622_item.get('isPublic')}")
        print(f"    - Host: {server_host}")

        # 1. Check completion status before submit
        print("\n--- 1. Checking Completion Status Before Submit ---")
        code, text = check_completion_status(token, q_code, CONTEST_ID)
        print(f"GET completion-status (userAlias={q_code}, examId={CONTEST_ID}): HTTP {code} -> {text}")
        
        code, text = check_completion_status(token, q_alias, CONTEST_ID)
        print(f"GET completion-status (alias={q_alias}, examId={CONTEST_ID}): HTTP {code} -> {text}")

        code, text = check_contest_completion(token, CONTEST_ID)
        print(f"POST check/complete/contest: HTTP {code} -> {text}")

        # 2. Test live UDP socket handshake
        print("\n--- 2. Testing Live UDP Socket ---")
        test_udp_socket(server_host, 2208, username, q_code)

        # 3. Test submitting source code to PTIT API
        print("\n--- 3. Testing Submit Source Code to /api/app/jnp-submission/source ---")
        
        # Test 3a: submit with questionAlias = userAlias ("Stpr1AbW")
        print(f"[*] Submitting with questionAlias = userAlias ({q_code})...")
        sc_java = JAVA_SOLUTION_Q1622.replace("B23DCDT024", username).replace("Stpr1AbW", q_code)
        code, text = submit_source(token, q_code, sc_java, exam_id=CONTEST_ID, field_mode="sourceCode")
        print(f"HTTP {code} Response: {text}")

        # Test 3b: submit with questionAlias = alias ("Q1622")
        print(f"[*] Submitting with questionAlias = alias ({q_alias})...")
        code, text = submit_source(token, q_alias, sc_java, exam_id=CONTEST_ID, field_mode="sourceCode")
        print(f"HTTP {code} Response: {text}")

        # Test 3c: submit with both sourceCode and source
        print(f"[*] Submitting with both source and sourceCode fields...")
        code, text = submit_source(token, q_code, sc_java, exam_id=CONTEST_ID, field_mode="both")
        print(f"HTTP {code} Response: {text}")

        # 4. Check completion status after submit
        print("\n--- 4. Checking Completion Status After Submit ---")
        code, text = check_completion_status(token, q_code, CONTEST_ID)
        print(f"GET completion-status (userAlias={q_code}): HTTP {code} -> {text}")

        code, text = check_completion_status(token, q_alias, CONTEST_ID)
        print(f"GET completion-status (alias={q_alias}): HTTP {code} -> {text}")

        code, text = check_contest_completion(token, CONTEST_ID)
        print(f"POST check/complete/contest: HTTP {code} -> {text}")
        
        break # Test one user first

if __name__ == "__main__":
    main()

