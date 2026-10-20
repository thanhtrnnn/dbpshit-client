import os
import sys
import json
import time
import socket
import re
import shutil
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

# Base directory
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
QUESTIONS_FILE = PROJECT_ROOT / "sample_responses" / "master_jnp_questions_bank.json"
PTIT_ENV_FILE = PROJECT_ROOT / "ptit.env"
ENV_FILE = PROJECT_ROOT / ".env"

PTIT_API_HOST = "https://dbapi.ptit.edu.vn"
PTIT_AUTH_URL = f"{PTIT_API_HOST}/api/auth"
PTIT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Detect Java/Javac binaries
def find_jdk():
    # 1. Check JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        jh_path = Path(java_home)
        java_exe = jh_path / "bin" / ("java.exe" if sys.platform == "win32" else "java")
        javac_exe = jh_path / "bin" / ("javac.exe" if sys.platform == "win32" else "javac")
        if java_exe.exists() and javac_exe.exists():
            return str(java_exe), str(javac_exe)
    
    # 2. Known common Windows paths
    candidates = [
        r"C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot\bin",
        r"C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot\bin",
        r"C:\Program Files\Java\jdk-17\bin",
        r"C:\Program Files\Java\jdk-21\bin",
    ]
    for c in candidates:
        c_path = Path(c)
        java_exe = c_path / "java.exe"
        javac_exe = c_path / "javac.exe"
        if java_exe.exists() and javac_exe.exists():
            return str(java_exe), str(javac_exe)

    # 3. Fallback to PATH
    java_in_path = shutil.which("java")
    javac_in_path = shutil.which("javac")
    return java_in_path or "java", javac_in_path or "javac"

JAVA_EXEC, JAVAC_EXEC = find_jdk()

app = FastAPI(title="Lập Chình Mạng Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class JavaRunRequest(BaseModel):
    code: str
    className: Optional[str] = None
    timeoutSeconds: Optional[int] = 10

class SocketTestRequest(BaseModel):
    host: str
    port: int
    protocol: str  # TCP or UDP
    payload: str
    isHex: Optional[bool] = False
    timeoutSeconds: Optional[float] = 5.0

class PtitSubmitRequest(BaseModel):
    questionAlias: str
    code: str
    token: Optional[str] = None
    courseId: Optional[str] = None
    examId: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refreshToken: str

class MockTestRequest(BaseModel):
    code: str
    questionCode: Optional[int] = 701
    customInput: Optional[str] = None
    timeoutSeconds: Optional[int] = 10

# Routes
@app.get("/api/status")
def get_system_status():
    return {
        "status": "online",
        "javaExec": JAVA_EXEC,
        "javacExec": JAVAC_EXEC,
        "jdkFound": os.path.exists(JAVA_EXEC) if JAVA_EXEC else False
    }

@app.get("/api/questions")
def get_questions():
    if not QUESTIONS_FILE.exists():
        raise HTTPException(status_code=404, detail="Questions database not found")
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.get("/api/creds")
def get_saved_credentials():
    creds = []
    # Read from ptit.env
    if PTIT_ENV_FILE.exists():
        with open(PTIT_ENV_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        cur_u = None
        for l in lines:
            if l.startswith("QLDT_USERNAME="):
                cur_u = l.split("=", 1)[1].strip()
            elif l.startswith("QLDT_PASSWORD=") and cur_u:
                cur_p = l.split("=", 1)[1].strip()
                creds.append({"username": cur_u, "password": cur_p, "source": "ptit.env"})
                cur_u = None
    # Read default .env
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # Chấp nhận cả QLDT_USERNAME=... lẫn USERNAME = ...
        m_u = re.search(r"^\s*(?:QLDT_)?USERNAME\s*=\s*([^\r\n#]+)", content, re.MULTILINE)
        m_p = re.search(r"^\s*(?:QLDT_)?PASSWORD\s*=\s*([^\r\n#]+)", content, re.MULTILINE)
        if m_u and m_p:
            creds.append({
                "username": m_u.group(1).strip(),
                "password": m_p.group(1).strip(),
                "source": ".env (Default)"
            })
    return creds

# --- Auth proxy (dbapi.ptit.edu.vn) ---
# Trình duyệt không gọi thẳng dbapi.ptit.edu.vn được (CORS) nên backend đứng giữa,
# giống api/proxy.js của db-pshit-remastered.
def _ptit_auth_call(method: str, path: str, token: Optional[str] = None, payload: Optional[dict] = None):
    headers = {"Content-Type": "application/json", "User-Agent": PTIT_USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.request(method, f"{PTIT_AUTH_URL}{path}", headers=headers, json=payload, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Không kết nối được dbapi.ptit.edu.vn: {e}")
    try:
        body = r.json()
    except ValueError:
        body = {"message": r.text}
    if not r.ok:
        # dbapi trả lỗi dạng {"status": 0, "description": "..."}
        message = (body.get("description") or body.get("message")) if isinstance(body, dict) else None
        raise HTTPException(status_code=r.status_code, detail=message or f"PTIT API lỗi {r.status_code}")
    return body

def _extract_tokens(data: dict) -> Dict[str, Optional[str]]:
    return {
        "accessToken": data.get("accessToken") or data.get("access_token") or data.get("access"),
        "refreshToken": data.get("refreshToken") or data.get("refresh_token") or data.get("refresh"),
    }

def _bearer(authorization: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip() or None
    return None

@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    if not req.username.strip() or not req.password:
        raise HTTPException(status_code=400, detail="Thiếu tên đăng nhập hoặc mật khẩu")
    data = _ptit_auth_call("POST", "/auth/ptit-login", payload={
        "username": req.username.strip(),
        "password": req.password,
    })
    tokens = _extract_tokens(data)
    if not tokens["accessToken"]:
        raise HTTPException(status_code=502, detail="PTIT API không trả về accessToken")
    return tokens

@app.post("/api/auth/refresh")
def auth_refresh(req: RefreshRequest):
    data = _ptit_auth_call("POST", "/auth/refresh-token", payload={"refreshToken": req.refreshToken})
    tokens = _extract_tokens(data)
    if not tokens["accessToken"]:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ")
    return tokens

@app.get("/api/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    token = _bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Thiếu Bearer token")
    return _ptit_auth_call("GET", "/users/info", token=token)

@app.post("/api/run-java")
def run_java_code(req: JavaRunRequest):
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Empty Java source code")

    # Extract class name or package
    class_name = req.className
    if not class_name:
        match = re.search(r"public\s+class\s+([A-Za-z0-9_]+)", code)
        if match:
            class_name = match.group(1)
        else:
            match = re.search(r"class\s+([A-Za-z0-9_]+)", code)
            class_name = match.group(1) if match else "Main"

    # Extract package if any
    pkg_match = re.search(r"package\s+([A-Za-z0-9_.]+)\s*;", code)
    package_name = pkg_match.group(1) if pkg_match else None

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="jnp_run_")
    try:
        if package_name:
            pkg_rel_dir = os.path.join(*package_name.split("."))
            target_dir = os.path.join(temp_dir, pkg_rel_dir)
            os.makedirs(target_dir, exist_ok=True)
            java_file = os.path.join(target_dir, f"{class_name}.java")
            full_class_name = f"{package_name}.{class_name}"
        else:
            target_dir = temp_dir
            java_file = os.path.join(target_dir, f"{class_name}.java")
            full_class_name = class_name

        with open(java_file, "w", encoding="utf-8") as f:
            f.write(code)

        # 1. Compile
        start_time = time.time()
        compile_cmd = [JAVAC_EXEC, "-encoding", "UTF-8", java_file]
        compile_proc = subprocess.run(
            compile_cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=15
        )

        compile_time = round((time.time() - start_time) * 1000, 2)

        if compile_proc.returncode != 0:
            return {
                "success": False,
                "stage": "compile",
                "compileTimeMs": compile_time,
                "executionTimeMs": 0,
                "stdout": compile_proc.stdout,
                "stderr": compile_proc.stderr or "Compilation failed with errors",
                "exitCode": compile_proc.returncode
            }

        # 2. Run
        run_start = time.time()
        run_cmd = [JAVA_EXEC, "-Dfile.encoding=UTF-8", "-cp", temp_dir, full_class_name]
        try:
            run_proc = subprocess.run(
                run_cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=req.timeoutSeconds or 10
            )
            exec_time = round((time.time() - run_start) * 1000, 2)
            return {
                "success": run_proc.returncode == 0,
                "stage": "execute",
                "compileTimeMs": compile_time,
                "executionTimeMs": exec_time,
                "stdout": run_proc.stdout,
                "stderr": run_proc.stderr,
                "exitCode": run_proc.returncode
            }
        except subprocess.TimeoutExpired:
            exec_time = round((time.time() - run_start) * 1000, 2)
            return {
                "success": False,
                "stage": "timeout",
                "compileTimeMs": compile_time,
                "executionTimeMs": exec_time,
                "stdout": "",
                "stderr": f"Execution timed out after {req.timeoutSeconds}s (socket or program did not terminate)",
                "exitCode": -1
            }

    except Exception as e:
        return {
            "success": False,
            "stage": "internal_error",
            "compileTimeMs": 0,
            "executionTimeMs": 0,
            "stdout": "",
            "stderr": f"Backend Error: {str(e)}",
            "exitCode": -1
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/api/socket-test")
def test_socket_connection(req: SocketTestRequest):
    """Interactive raw socket handshake test (TCP or UDP)"""
    host = req.host.strip()
    port = req.port
    proto = req.protocol.upper()
    payload_str = req.payload
    timeout = req.timeoutSeconds or 5.0

    if req.isHex:
        try:
            payload_bytes = bytes.fromhex(payload_str.replace(" ", "").replace("\n", ""))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid hex string: {e}")
    else:
        payload_bytes = payload_str.encode("utf-8")

    start_time = time.time()
    try:
        if "UDP" in proto:
            # UDP Socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(payload_bytes, (host, port))
            data, server_addr = sock.recvfrom(65535)
            elapsed = round((time.time() - start_time) * 1000, 2)
            sock.close()
            return {
                "success": True,
                "protocol": "UDP",
                "host": host,
                "port": port,
                "latencyMs": elapsed,
                "bytesSent": len(payload_bytes),
                "bytesReceived": len(data),
                "receivedHex": data.hex(),
                "receivedText": data.decode("utf-8", errors="replace"),
                "rawDump": str(data)
            }
        else:
            # TCP Socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.sendall(payload_bytes)
            
            # Read response
            received = b""
            try:
                chunk = sock.recv(4096)
                while chunk:
                    received += chunk
                    if len(chunk) < 4096:
                        break
                    chunk = sock.recv(4096)
            except socket.timeout:
                pass

            elapsed = round((time.time() - start_time) * 1000, 2)
            sock.close()

            return {
                "success": True,
                "protocol": "TCP",
                "host": host,
                "port": port,
                "latencyMs": elapsed,
                "bytesSent": len(payload_bytes),
                "bytesReceived": len(received),
                "receivedHex": received.hex(),
                "receivedText": received.decode("utf-8", errors="replace"),
                "rawDump": str(received)
            }

    except socket.timeout:
        elapsed = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "error": f"Socket timed out after {timeout}s",
            "latencyMs": elapsed,
            "bytesSent": len(payload_bytes),
            "bytesReceived": 0
        }
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "latencyMs": elapsed,
            "bytesSent": 0,
            "bytesReceived": 0
        }

@app.post("/api/submit-ptit")
def submit_to_ptit(req: PtitSubmitRequest, authorization: Optional[str] = Header(None)):
    token = req.token or _bearer(authorization)
    if not token:
        raise HTTPException(status_code=400, detail="Missing PTIT Bearer token")

    url = f"{PTIT_API_HOST}/api/app/jnp-submission/source"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": PTIT_USER_AGENT
    }
    payload = {
        "questionAlias": req.questionAlias,
        "source": req.code,
        "courseId": req.courseId,
        "examId": req.examId
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        return {
            "statusCode": r.status_code,
            "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def solve_701_expected(data_str: str) -> str:
    nums = sorted([int(x.strip()) for x in data_str.strip().split(",") if x.strip()])
    min_diff = float("inf")
    best_a, best_b = None, None
    for i in range(len(nums) - 1):
        diff = nums[i + 1] - nums[i]
        if diff < min_diff:
            min_diff = diff
            best_a, best_b = nums[i], nums[i + 1]
        elif diff == min_diff:
            if nums[i + 1] > best_b or (nums[i + 1] == best_b and nums[i] > best_a):
                best_a, best_b = nums[i], nums[i + 1]
    return f"{min_diff},{best_a},{best_b}"

@app.post("/api/mock-test")
def run_mock_test(req: MockTestRequest):
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Mã nguồn Java trống")
    
    # 1. Bind free local port for mock server
    sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_server.bind(("127.0.0.1", 0))
    mock_port = sock_server.getsockname()[1]
    sock_server.listen(1)
    sock_server.settimeout(req.timeoutSeconds or 8.0)

    test_input = req.customInput.strip() if req.customInput and req.customInput.strip() else "1,3,9,19,33,20"
    expected_ans = solve_701_expected(test_input) if req.questionCode == 701 else ""

    server_result = {
        "connected": False,
        "handshake": "",
        "sentData": test_input,
        "receivedAnswer": "",
        "expectedAnswer": expected_ans,
        "isCorrect": False,
        "error": None
    }

    def mock_server_thread():
        try:
            conn, addr = sock_server.accept()
            conn.settimeout(5.0)
            server_result["connected"] = True

            # a. Read studentCode;qCode
            handshake_raw = conn.recv(1024)
            server_result["handshake"] = handshake_raw.decode("utf-8", errors="replace").strip()

            # b. Send test string
            conn.sendall(test_input.encode("utf-8"))

            # c. Read client answer
            ans_raw = conn.recv(1024)
            ans = ans_raw.decode("utf-8", errors="replace").strip()
            server_result["receivedAnswer"] = ans

            # Verify
            if req.questionCode == 701:
                server_result["isCorrect"] = (ans == expected_ans)
                if server_result["isCorrect"]:
                    conn.sendall(b"ACK_OK: Ket qua hoan toan chinh xac!")
                else:
                    conn.sendall(f"ACK_FAIL: Sai ket qua (Nhan duoc: {ans}, Ky vong: {expected_ans})".encode("utf-8"))
            else:
                conn.sendall(b"ACK_OK")

            conn.close()
        except Exception as err:
            server_result["error"] = str(err)
        finally:
            try:
                sock_server.close()
            except:
                pass

    t = threading.Thread(target=mock_server_thread, daemon=True)
    t.start()

    # 2. Rewrite host and port in Java code to point to 127.0.0.1:mock_port
    code_modified = re.sub(r'SERVER_HOST\s*=\s*"[^"]*"', 'SERVER_HOST = "127.0.0.1"', code)
    code_modified = re.sub(r'SERVER_PORT\s*=\s*[0-9]+', f'SERVER_PORT = {mock_port}', code_modified)
    code_modified = re.sub(r'new\s+Socket\(\s*"[^"]*"\s*,\s*[0-9]+\s*\)', f'new Socket("127.0.0.1", {mock_port})', code_modified)

    # 3. Run Java code
    run_req = JavaRunRequest(code=code_modified, timeoutSeconds=req.timeoutSeconds)
    exec_res = run_java_code(run_req)

    t.join(timeout=2.0)

    return {
        "success": exec_res.get("success", False),
        "stage": exec_res.get("stage"),
        "compileTimeMs": exec_res.get("compileTimeMs", 0),
        "executionTimeMs": exec_res.get("executionTimeMs", 0),
        "stdout": exec_res.get("stdout", ""),
        "stderr": exec_res.get("stderr", ""),
        "mockServer": server_result
    }

# Mount static files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting Lập Chình Mạng on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
