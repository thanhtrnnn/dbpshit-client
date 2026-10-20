/**
 * Lập Chình Mạng - Frontend Controller
 * Monaco Editor + IntelliJ Theme + Problem Navigator + Java Runner
 */

let editor = null;
let allProblems = [];
let filteredProblems = [];
let currentProblem = null;
let savedCreds = [];

const STORAGE_KEY_PREFIX = "jnp_code_";
const STUDENT_CODE_KEY = "jnp_student_code";
const Q_CODE_KEY = "jnp_q_code";

document.addEventListener("DOMContentLoaded", async () => {
    if (!(await Auth.requireAuth())) return;
    initAuthUI();
    initInputs();
    initResizers();
    initFileUploadDownload();
    initMonaco();
    await loadSystemStatus();
    await loadQuestions();
    await loadCredentials();
    bindEvents();
});

// 0. Logged-in user (DB PTIT) on navbar
function initAuthUI() {
    const nameEl = document.getElementById("nav-user-name");
    const render = (user) => {
        const code = user && (user.userCode || user.username || user.sub);
        const name = user && user.fullName;
        nameEl.innerHTML = code ? `<strong>${escapeHtml(code)}</strong>` : "Đã đăng nhập";
        nameEl.title = name ? `Đang đăng nhập: ${name}` : "Tài khoản DB PTIT đang đăng nhập";
    };

    render(Auth.getUser());
    Auth.fetchProfile().then((user) => user && render(user)).catch(() => {});

    document.getElementById("btn-logout").addEventListener("click", () => {
        if (confirm("Đăng xuất khỏi tài khoản DB PTIT?")) Auth.logout();
    });
}

// 1. Initialize Student & Question Code Inputs
function initInputs() {
    const savedStudent = localStorage.getItem(STUDENT_CODE_KEY);
    const savedQCode = localStorage.getItem(Q_CODE_KEY);
    if (savedStudent) document.getElementById("input-student-code").value = savedStudent;
    if (savedQCode) document.getElementById("input-q-code").value = savedQCode;

    document.getElementById("input-student-code").addEventListener("input", (e) => {
        localStorage.setItem(STUDENT_CODE_KEY, e.target.value.trim());
        updateSocketPayloadPlaceholder();
    });
    document.getElementById("input-q-code").addEventListener("input", (e) => {
        localStorage.setItem(Q_CODE_KEY, e.target.value.trim());
        updateSocketPayloadPlaceholder();
    });
}

function updateSocketPayloadPlaceholder() {
    const sCode = document.getElementById("input-student-code").value.trim() || "B23DCAT144";
    const qCode = document.getElementById("input-q-code").value.trim() || "FF49DC02";
    const payloadInput = document.getElementById("sock-payload");
    if (!payloadInput.value) {
        payloadInput.value = `${sCode};${qCode}`;
    }
}

// 2. Initialize Resizable Panels
function initResizers() {
    const overlay = document.getElementById("drag-overlay");

    // a. Sidebar Resizer
    const sidebarEl = document.getElementById("sidebar");
    const resizerSidebar = document.getElementById("resizer-sidebar");
    const savedSidebarWidth = localStorage.getItem("jnp_sidebar_width");
    if (savedSidebarWidth && sidebarEl && !sidebarEl.classList.contains("collapsed")) {
        sidebarEl.style.width = savedSidebarWidth + "px";
    }

    if (resizerSidebar && sidebarEl) {
        let isDragging = false;
        let startX = 0;
        let startWidth = 0;

        resizerSidebar.addEventListener("mousedown", (e) => {
            if (sidebarEl.classList.contains("collapsed")) return;
            isDragging = true;
            startX = e.clientX;
            startWidth = sidebarEl.getBoundingClientRect().width;
            resizerSidebar.classList.add("dragging");
            if (overlay) overlay.style.display = "block";
            document.body.style.cursor = "col-resize";
            e.preventDefault();
        });

        window.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const newWidth = Math.max(180, Math.min(600, startWidth + (e.clientX - startX)));
            sidebarEl.style.width = newWidth + "px";
            if (editor) editor.layout();
        });

        window.addEventListener("mouseup", () => {
            if (!isDragging) return;
            isDragging = false;
            resizerSidebar.classList.remove("dragging");
            if (overlay) overlay.style.display = "none";
            document.body.style.cursor = "";
            localStorage.setItem("jnp_sidebar_width", sidebarEl.getBoundingClientRect().width);
            if (editor) editor.layout();
        });
    }

    // b. Editor Split Resizer (Problem Pane vs Editor Pane)
    const problemPane = document.querySelector(".problem-pane");
    const resizerSplit = document.getElementById("resizer-editor-split");
    const editorSplit = document.querySelector(".editor-split");
    const savedProblemWidth = localStorage.getItem("jnp_problem_width");
    if (savedProblemWidth && problemPane) {
        problemPane.style.width = savedProblemWidth + "px";
    }

    if (resizerSplit && problemPane) {
        let isDragging = false;
        let startX = 0;
        let startWidth = 0;

        resizerSplit.addEventListener("mousedown", (e) => {
            isDragging = true;
            startX = e.clientX;
            startWidth = problemPane.getBoundingClientRect().width;
            resizerSplit.classList.add("dragging");
            if (overlay) overlay.style.display = "block";
            document.body.style.cursor = "col-resize";
            e.preventDefault();
        });

        window.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const totalWidth = editorSplit ? editorSplit.getBoundingClientRect().width : window.innerWidth;
            const newWidth = Math.max(220, Math.min(totalWidth - 300, startWidth + (e.clientX - startX)));
            problemPane.style.width = newWidth + "px";
            if (editor) editor.layout();
        });

        window.addEventListener("mouseup", () => {
            if (!isDragging) return;
            isDragging = false;
            resizerSplit.classList.remove("dragging");
            if (overlay) overlay.style.display = "none";
            document.body.style.cursor = "";
            localStorage.setItem("jnp_problem_width", problemPane.getBoundingClientRect().width);
            if (editor) editor.layout();
        });
    }

    // c. Bottom Panel Resizer (Vertical Resize)
    const bottomPanel = document.getElementById("bottom-panel");
    const resizerBottom = document.getElementById("resizer-bottom-panel");
    const savedBottomHeight = localStorage.getItem("jnp_bottom_height");
    if (savedBottomHeight && bottomPanel) {
        bottomPanel.style.height = savedBottomHeight + "px";
    }

    if (resizerBottom && bottomPanel) {
        let isDragging = false;
        let startY = 0;
        let startHeight = 0;

        resizerBottom.addEventListener("mousedown", (e) => {
            isDragging = true;
            startY = e.clientY;
            startHeight = bottomPanel.getBoundingClientRect().height;
            resizerBottom.classList.add("dragging");
            if (overlay) overlay.style.display = "block";
            document.body.style.cursor = "row-resize";
            e.preventDefault();
        });

        window.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const newHeight = Math.max(60, Math.min(window.innerHeight - 120, startHeight - (e.clientY - startY)));
            bottomPanel.style.height = newHeight + "px";
            if (editor) editor.layout();
        });

        window.addEventListener("mouseup", () => {
            if (!isDragging) return;
            isDragging = false;
            resizerBottom.classList.remove("dragging");
            if (overlay) overlay.style.display = "none";
            document.body.style.cursor = "";
            localStorage.setItem("jnp_bottom_height", bottomPanel.getBoundingClientRect().height);
            if (editor) editor.layout();
        });
    }
}

// 3. Initialize File Upload & Download Features
function initFileUploadDownload() {
    const uploadInput = document.getElementById("file-upload-input");
    const uploadBtn = document.getElementById("btn-upload-file");
    const downloadBtn = document.getElementById("btn-download-file");
    const editorPane = document.getElementById("editor-pane");

    // Open file picker
    if (uploadBtn && uploadInput) {
        uploadBtn.addEventListener("click", () => {
            uploadInput.value = "";
            uploadInput.click();
        });

        uploadInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (!file) return;
            readFileIntoEditor(file);
        });
    }

    // Download code as .java file
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            if (!editor) return;
            const code = editor.getValue();
            let fileName = "Main.java";
            const match = code.match(/public\s+class\s+([A-Za-z0-9_]+)/);
            if (match) fileName = match[1] + ".java";

            const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    // Drag & drop file onto code editor
    if (editorPane) {
        editorPane.addEventListener("dragover", (e) => {
            e.preventDefault();
            editorPane.classList.add("drag-over");
        });

        editorPane.addEventListener("dragleave", (e) => {
            e.preventDefault();
            editorPane.classList.remove("drag-over");
        });

        editorPane.addEventListener("drop", (e) => {
            e.preventDefault();
            editorPane.classList.remove("drag-over");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                readFileIntoEditor(file);
            }
        });
    }
}

function readFileIntoEditor(file) {
    if (!editor) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result;
        editor.setValue(content);
        const tabSpan = document.querySelector(".editor-tab-active span");
        if (tabSpan) tabSpan.textContent = file.name;
    };
    reader.readAsText(file);
}

// 4. Initialize Monaco Editor with IntelliJ Theme
function initMonaco() {
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });

    require(['vs/editor/editor.main'], () => {
        // Define IntelliJ Darcula Theme
        monaco.editor.defineTheme('intellij-darcula', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: '', foreground: 'bcbec4', background: '1e1f22' },
                { token: 'keyword', foreground: 'cf8e6d', fontStyle: 'bold' },
                { token: 'keyword.java', foreground: 'cf8e6d', fontStyle: 'bold' },
                { token: 'string', foreground: '6aab73' },
                { token: 'string.escape', foreground: 'cf8e6d' },
                { token: 'comment', foreground: '7a7e85', fontStyle: 'italic' },
                { token: 'number', foreground: '2aacb8' },
                { token: 'type', foreground: '56a8f5' },
                { token: 'type.identifier', foreground: '56a8f5' },
                { token: 'delimiter', foreground: 'bcbec4' },
                { token: 'annotation', foreground: 'b3ae60' }
            ],
            colors: {
                'editor.background': '#1e1f22',
                'editor.foreground': '#bcbec4',
                'editor.lineHighlightBackground': '#26282d',
                'editorCursor.foreground': '#ffffff',
                'editorWhitespace.foreground': '#3b3e44',
                'editorIndentGuide.background': '#2d3035',
                'editorIndentGuide.activeBackground': '#3f4248',
                'editorLineNumber.foreground': '#4e5157',
                'editorLineNumber.activeForeground': '#a1a3a8',
                'editor.selectionBackground': '#264f78',
                'editor.inactiveSelectionBackground': '#3a3d41'
            }
        });

        // Register IntelliJ-style snippets for Java
        monaco.languages.registerCompletionItemProvider('java', {
            provideCompletionItems: (model, position) => {
                const word = model.getWordUntilPosition(position);
                const range = {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: word.startColumn,
                    endColumn: word.endColumn
                };

                const suggestions = [
                    {
                        label: 'psvm',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'public static void main(String[] args) {\n\t$0\n}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Hàm public static void main',
                        range: range
                    },
                    {
                        label: 'sout',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'System.out.println($0);',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Lệnh in System.out.println()',
                        range: range
                    },
                    {
                        label: 'serr',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'System.err.println($0);',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Lệnh in lỗi System.err.println()',
                        range: range
                    },
                    {
                        label: 'tcpsocket',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'try (Socket socket = new Socket("${1:36.50.135.242}", ${2:2206})) {\n\tsocket.setSoTimeout(5000);\n\t$0\n} catch (Exception e) {\n\te.printStackTrace();\n}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Khối kết nối TCP Client Socket (try-with-resources)',
                        range: range
                    },
                    {
                        label: 'udpsocket',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'try (DatagramSocket socket = new DatagramSocket()) {\n\tsocket.setSoTimeout(5000);\n\tInetAddress serverAddr = InetAddress.getByName("${1:36.50.135.242}");\n\t$0\n} catch (Exception e) {\n\te.printStackTrace();\n}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Khối gửi nhận UDP DatagramSocket',
                        range: range
                    },
                    {
                        label: 'byteframe',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'ByteBuffer header = ByteBuffer.allocate(4);\nwhile (header.hasRemaining()) {\n\tchannel.read(header);\n}\nheader.flip();\nint len = header.getInt();\nByteBuffer payload = ByteBuffer.allocate(len);\nwhile (payload.hasRemaining()) {\n\tchannel.read(payload);\n}\npayload.flip();\n$0',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Đọc Frame NIO (4 byte độ dài + payload)',
                        range: range
                    },
                    {
                        label: 'caesar',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'StringBuilder sb = new StringBuilder();\nfor (char c : ${1:text}.toCharArray()) {\n\tif (Character.isUpperCase(c)) {\n\t\tsb.append((char) (\'A\' + (c - \'A\' - ${2:shift} + 26) % 26));\n\t} else if (Character.isLowerCase(c)) {\n\t\tsb.append((char) (\'a\' + (c - \'a\' - ${2:shift} + 26) % 26));\n\t} else {\n\t\tsb.append(c);\n\t}\n}\nString result = sb.toString();\n$0',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'Hàm giải mã Caesar',
                        range: range
                    }
                ];

                return { suggestions: suggestions };
            }
        });

        // Create editor instance with minimap disabled
        editor = monaco.editor.create(document.getElementById('monaco-container'), {
            value: '// Chọn một bài tập từ danh sách bên trái để bắt đầu lập trình Java...',
            language: 'java',
            theme: 'intellij-darcula',
            fontSize: 13.5,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            lineHeight: 22,
            minimap: { enabled: false }, // Đã tắt minimap theo yêu cầu
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            insertSpaces: true,
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true }
        });

        // Save code on edit
        editor.onDidChangeModelContent(() => {
            if (currentProblem) {
                const key = STORAGE_KEY_PREFIX + (currentProblem.alias || currentProblem.id);
                localStorage.setItem(key, editor.getValue());
            }
        });

        // If problems already loaded, select the first one
        if (filteredProblems.length > 0 && !currentProblem) {
            selectProblem(filteredProblems[0]);
        }
    });
}

// 3. Load System Status
async function loadSystemStatus() {
    try {
        const res = await fetch("/api/status");
        if (res.ok) {
            const data = await res.json();
            const statusEl = document.getElementById("system-status");
            if (data.jdkFound) {
                statusEl.textContent = "OpenJDK 17 Sẵn sàng";
                statusEl.style.color = "var(--accent-green)";
            } else {
                statusEl.textContent = "Không tìm thấy JDK";
                statusEl.style.color = "var(--accent-red)";
            }
        }
    } catch (e) {
        console.error("Status check error:", e);
    }
}

// 4. Load Questions from Backend
async function loadQuestions() {
    try {
        const res = await fetch("/api/questions");
        if (!res.ok) throw new Error("Không thể nạp danh sách câu hỏi từ máy chủ");
        allProblems = await res.json();

        // Sort: code asc
        allProblems.sort((a, b) => {
            const codeA = a.code || 0;
            const codeB = b.code || 0;
            return codeA - codeB;
        });

        document.getElementById("app-badge").textContent = `${allProblems.length} Bài Tập`;
        filteredProblems = [...allProblems];
        renderProblemList();

        const p701 = filteredProblems.find(p => p.code === 701 || (p.alias && p.alias.includes("701")));
        if (editor && filteredProblems.length > 0) {
            selectProblem(p701 || filteredProblems[0]);
        }
    } catch (e) {
        console.error("Failed to load questions:", e);
        document.getElementById("problem-list").innerHTML = `<div style="padding:12px;color:var(--accent-red);">Không thể tải danh sách bài tập: ${e.message}</div>`;
    }
}

// 5. Render Problem List Sidebar
function renderProblemList() {
    const listEl = document.getElementById("problem-list");
    listEl.innerHTML = "";

    document.getElementById("filtered-count").textContent = `Hiển thị: ${filteredProblems.length}/${allProblems.length}`;

    if (filteredProblems.length === 0) {
        listEl.innerHTML = `<div style="padding:16px;color:var(--text-muted);text-align:center;">Không tìm thấy bài tập phù hợp</div>`;
        return;
    }

    filteredProblems.forEach((p) => {
        const item = document.createElement("div");
        item.className = `problem-item ${currentProblem && currentProblem.id === p.id ? "active" : ""}`;
        item.id = `prob-item-${p.id}`;

        const levelClass = (p.level || "easy").toLowerCase();
        const protoText = p.protocolType || "TCP";

        item.innerHTML = `
            <div class="problem-item-header">
                <span class="problem-alias">${p.alias || "JNP"}</span>
                <span class="level-badge ${levelClass}">${p.level || "EASY"}</span>
            </div>
            <div class="problem-item-title" title="${p.title || ""}">${p.title || "Bài tập"}</div>
            <div class="problem-item-footer">
                <span class="proto-tag">${protoText}</span>
                ${p.code ? `<span class="proto-tag">Code: ${p.code}</span>` : ""}
            </div>
        `;

        item.addEventListener("click", () => selectProblem(p));
        listEl.appendChild(item);
    });
}

// 6. Select Problem and Update UI
function selectProblem(problem) {
    currentProblem = problem;

    // Update active highlight in list
    document.querySelectorAll(".problem-item").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`prob-item-${problem.id}`);
    if (activeEl) activeEl.classList.add("active");

    // Update Left Pane
    document.getElementById("pane-problem-title").textContent = `[${problem.alias || "JNP"}] ${problem.title || ""}`;
    document.getElementById("view-title").textContent = problem.title || "Chi tiết bài tập";
    document.getElementById("view-alias").textContent = problem.alias || "N/A";
    document.getElementById("view-protocol").textContent = problem.protocolType || "N/A";
    document.getElementById("view-level").textContent = problem.level || "EASY";

    const host = problem.examServerHost || document.getElementById("input-server-host").value.trim() || "36.50.135.242";
    const port = JavaTemplates.extractPort(problem.description) || JavaTemplates.getDefaultPort(problem.protocolType || "");
    document.getElementById("view-server-addr").textContent = `${host}:${port}`;

    // Update Socket Tester inputs
    document.getElementById("sock-host").value = host;
    document.getElementById("sock-port").value = port;
    const isUDP = (problem.protocolType || "").toUpperCase().includes("UDP");
    document.getElementById("sock-proto").value = isUDP ? "UDP" : "TCP";

    // Toggle Quick Mock Test Button
    const quickMockBtn = document.getElementById("btn-quick-mock-test");
    if (quickMockBtn) {
        const is701 = problem.code === 701 || (problem.alias && problem.alias.includes("701"));
        quickMockBtn.textContent = is701 ? "Debug Mock 701" : "Debug Mock Server";
    }

    // Format and render description HTML
    document.getElementById("view-description").innerHTML = problem.description || "Chưa có mô tả chi tiết cho bài tập này.";

    // Load or generate Java code in editor
    if (editor) {
        const key = STORAGE_KEY_PREFIX + (problem.alias || problem.id);
        const savedCode = localStorage.getItem(key);
        if (savedCode) {
            editor.setValue(savedCode);
        } else {
            generateStarterCode();
        }
    }
}

// 7. Generate Boilerplate Starter Code
function generateStarterCode() {
    if (!currentProblem || !editor) return;
    const studentCode = document.getElementById("input-student-code").value.trim() || "B23DCAT144";
    const qCode = document.getElementById("input-q-code").value.trim() || "FF49DC02";
    const host = document.getElementById("input-server-host").value.trim() || currentProblem.examServerHost || "36.50.135.242";

    const problemWithHost = { ...currentProblem, examServerHost: host };
    const code = JavaTemplates.generateForProblem(problemWithHost, studentCode, qCode);
    editor.setValue(code);
}

// 8. Run Java Code via Backend
async function runJavaCode() {
    if (!editor) return;
    const code = editor.getValue().trim();
    if (!code) {
        alert("Vui lòng nhập mã nguồn Java trước khi chạy.");
        return;
    }

    const runBtn = document.getElementById("btn-run-code");
    const termMeta = document.getElementById("terminal-meta");
    const termContent = document.getElementById("terminal-content");
    const termStatus = document.getElementById("term-status");
    const termCompileTime = document.getElementById("term-compile-time");
    const termExecTime = document.getElementById("term-exec-time");
    const termExitCode = document.getElementById("term-exit-code");

    // Switch to Terminal Tab
    switchTab("tab-terminal");

    runBtn.disabled = true;
    runBtn.textContent = "[...] Đang chạy...";
    termMeta.style.display = "flex";
    termStatus.className = "status-badge";
    termStatus.textContent = "ĐANG CHẠY";
    termContent.textContent = "Đang biên dịch và thực thi mã nguồn Java...";

    const startTime = performance.now();

    try {
        const res = await fetch("/api/run-java", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code, timeoutSeconds: 12 })
        });

        const data = await res.json();
        const clientElapsed = Math.round(performance.now() - startTime);

        termCompileTime.textContent = `${data.compileTimeMs || 0}ms`;
        termExecTime.textContent = `${data.executionTimeMs || 0}ms (tổng: ${clientElapsed}ms)`;
        termExitCode.textContent = data.exitCode;

        if (data.stage === "compile") {
            termStatus.className = "status-badge error";
            termStatus.textContent = "LỖI BIÊN DỊCH";
            termContent.textContent = `[!] BIÊN DỊCH THẤT BẠI:\n\n${data.stderr}\n${data.stdout}`;
        } else if (data.stage === "timeout") {
            termStatus.className = "status-badge timeout";
            termStatus.textContent = "QUÁ THỜI GIAN";
            termContent.textContent = `[!] THỜI GIAN CHẠY VƯỢT QUÁ GIỚI HẠN:\n${data.stderr}`;
        } else if (data.success) {
            termStatus.className = "status-badge success";
            termStatus.textContent = "THÀNH CÔNG";
            let output = data.stdout || "(Chương trình chạy xong nhưng không in ra kết quả)";
            if (data.stderr) output += `\n[Lỗi Stderr]:\n${data.stderr}`;
            termContent.textContent = output;
        } else {
            termStatus.className = "status-badge error";
            termStatus.textContent = "LỖI THỰC THI";
            let output = data.stderr || data.stdout || "Lỗi không xác định";
            termContent.textContent = output;
        }
    } catch (e) {
        termStatus.className = "status-badge error";
        termStatus.textContent = "LỖI KẾT NỐI";
        termContent.textContent = `[-] Không thể kết nối đến Backend: ${e.message}`;
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = "[Chạy] Chạy Code Java";
    }
}

// 8b. Run Mock Debug (Kiểm thử Mock Server nội bộ cho bài 701)
async function runMockDebug() {
    if (!editor) return;
    const code = editor.getValue().trim();
    if (!code) {
        alert("Vui lòng nhập mã nguồn Java trước khi chạy kiểm thử.");
        return;
    }

    const mockBtn = document.getElementById("btn-mock-debug");
    const quickMockBtn = document.getElementById("btn-quick-mock-test");
    const termMeta = document.getElementById("terminal-meta");
    const termContent = document.getElementById("terminal-content");
    const termStatus = document.getElementById("term-status");
    const termCompileTime = document.getElementById("term-compile-time");
    const termExecTime = document.getElementById("term-exec-time");
    const termExitCode = document.getElementById("term-exit-code");

    switchTab("tab-terminal");

    if (mockBtn) { mockBtn.disabled = true; mockBtn.textContent = "[...] Đang Mock..."; }
    if (quickMockBtn) { quickMockBtn.disabled = true; }
    termMeta.style.display = "flex";
    termStatus.className = "status-badge";
    termStatus.textContent = "DEBUG MOCK";
    termContent.textContent = "Đang khởi tạo máy chủ Mock Server nội bộ (127.0.0.1) và thực thi mã nguồn Java...";

    const qCodeNum = currentProblem ? (currentProblem.code || 701) : 701;

    try {
        const res = await fetch("/api/mock-test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: code,
                questionCode: qCodeNum,
                timeoutSeconds: 8
            })
        });

        const data = await res.json();
        termCompileTime.textContent = `${data.compileTimeMs || 0}ms`;
        termExecTime.textContent = `${data.executionTimeMs || 0}ms`;
        termExitCode.textContent = (data.mockServer && data.mockServer.isCorrect) ? 0 : 1;

        if (data.stage === "compile") {
            termStatus.className = "status-badge error";
            termStatus.textContent = "LỖI BIÊN DỊCH";
            termContent.textContent = `[!] BIÊN DỊCH THẤT BẠI:\n\n${data.stderr}\n${data.stdout}`;
            return;
        }

        const ms = data.mockServer || {};
        let resultReport = "";
        if (ms.connected) {
            resultReport += `[+] KẾT NỐI MOCK SERVER THÀNH CÔNG (127.0.0.1)\n`;
            resultReport += `[*] Gói tin Handshake client gửi: "${ms.handshake}"\n`;
            resultReport += `[*] Dữ liệu test Mock Server gửi: "${ms.sentData}"\n`;
            resultReport += `[*] Kết quả client tính toán & phản hồi: "${ms.receivedAnswer}"\n`;
            if (ms.expectedAnswer) {
                resultReport += `[*] Đáp án chuẩn kỳ vọng: "${ms.expectedAnswer}"\n\n`;
                if (ms.isCorrect) {
                    termStatus.className = "status-badge success";
                    termStatus.textContent = "CHÍNH XÁC (PASS)";
                    resultReport += `========================================\n`;
                    resultReport += `[+] KẾT LUẬN: ĐÁP ÁN CHÍNH XÁC! THUẬT TOÁN ĐÃ ĐẠT YÊU CẦU ĐỀ BÀI.\n`;
                    resultReport += `========================================\n\n`;
                } else {
                    termStatus.className = "status-badge error";
                    termStatus.textContent = "SAI KẾT QUẢ (FAIL)";
                    resultReport += `========================================\n`;
                    resultReport += `[-] KẾT LUẬN: SAI KẾT QUẢ! Client gửi "${ms.receivedAnswer}", nhưng kỳ vọng là "${ms.expectedAnswer}".\n`;
                    resultReport += `========================================\n\n`;
                }
            }
        } else {
            termStatus.className = "status-badge error";
            termStatus.textContent = "KHÔNG KẾT NỐI ĐƯỢC";
            resultReport += `[-] Chương trình không kết nối được tới Mock Server: ${ms.error || 'Timeout hoặc lỗi socket'}\n\n`;
        }

        resultReport += `--- [Chi tiết Console Output] ---\n`;
        resultReport += data.stdout || "(Không có stdout)\n";
        if (data.stderr) {
            resultReport += `\n--- [Chi tiết Stderr] ---\n${data.stderr}\n`;
        }

        termContent.textContent = resultReport;

    } catch (err) {
        termStatus.className = "status-badge error";
        termStatus.textContent = "LỖI HỆ THỐNG";
        termContent.textContent = `[-] Lỗi gọi API Mock: ${err.message}`;
    } finally {
        if (mockBtn) { mockBtn.disabled = false; mockBtn.textContent = "[Debug] Test Mock"; }
        if (quickMockBtn) { quickMockBtn.disabled = false; }
    }
}

// 9. Send Socket Probe (Handshake Tester)
async function sendSocketProbe() {
    const host = document.getElementById("sock-host").value.trim();
    const port = parseInt(document.getElementById("sock-port").value.trim(), 10);
    const protocol = document.getElementById("sock-proto").value;
    const payload = document.getElementById("sock-payload").value;
    const isHex = document.getElementById("sock-is-hex").checked;
    const resBox = document.getElementById("sock-response-area");
    const sendBtn = document.getElementById("btn-send-socket-probe");

    if (!host || isNaN(port)) {
        alert("Vui lòng nhập Máy chủ và Cổng Port hợp lệ.");
        return;
    }

    sendBtn.disabled = true;
    sendBtn.textContent = "[...] Đang gửi...";
    resBox.textContent = `Đang kết nối đến ${host}:${port} (${protocol})...`;

    try {
        const res = await fetch("/api/socket-test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host,
                port,
                protocol,
                payload,
                isHex,
                timeoutSeconds: 5.0
            })
        });

        const data = await res.json();
        if (data.success) {
            resBox.innerHTML = `
                <div style="color:var(--accent-green); margin-bottom: 6px;">[+] Kết nối thành công | Độ trễ: ${data.latencyMs}ms | Nhận: ${data.bytesReceived} bytes</div>
                <div><strong>Văn bản giải mã (UTF-8):</strong> <span style="color:var(--accent-cyan);">${escapeHtml(data.receivedText || '(Trống)')}</span></div>
                <div style="margin-top: 4px;"><strong>Bản kết xuất Hex (Hex Dump):</strong> <span style="color:var(--accent-orange); font-size:11px;">${data.receivedHex || 'N/A'}</span></div>
            `;
        } else {
            resBox.innerHTML = `<div style="color:var(--accent-red);">[-] Lỗi kết nối: ${escapeHtml(data.error || 'Hết thời gian chờ hoặc từ chối kết nối')} (Độ trễ: ${data.latencyMs}ms)</div>`;
        }
    } catch (e) {
        resBox.innerHTML = `<div style="color:var(--accent-red);">[-] Lỗi yêu cầu: ${e.message}</div>`;
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Gửi gói tin Socket";
    }
}

// 10. Load Credentials from Backend
async function loadCredentials() {
    try {
        const res = await fetch("/api/creds");
        if (res.ok) {
            savedCreds = await res.json();
            const selectEl = document.getElementById("select-saved-creds");
            selectEl.innerHTML = `<option value="">-- Chọn tài khoản (${savedCreds.length} tài khoản) --</option>`;
            savedCreds.forEach((c, idx) => {
                const opt = document.createElement("option");
                opt.value = idx;
                opt.textContent = `${c.username} [${c.source}]`;
                selectEl.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Could not load credentials:", e);
    }
}

// 11. Tab Switching
function switchTab(tabId) {
    document.querySelectorAll(".panel-tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.toggle("active", pane.id === tabId);
    });
}

// 12. Helper: Escape HTML
function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}

// 13. Bind UI Events
function bindEvents() {
    // Sidebar Toggle Button
    const sidebarEl = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("btn-toggle-sidebar");
    if (toggleBtn && sidebarEl) {
        toggleBtn.addEventListener("click", () => {
            const isCollapsed = sidebarEl.classList.toggle("collapsed");
            toggleBtn.classList.toggle("active", isCollapsed);
            toggleBtn.textContent = isCollapsed ? "[Hiện Danh sách]" : "[Ẩn Danh sách]";
            setTimeout(() => {
                if (editor) editor.layout();
            }, 220);
        });
    }

    // Run Code Button
    document.getElementById("btn-run-code").addEventListener("click", runJavaCode);

    // Generate Template Button
    document.getElementById("btn-generate-template").addEventListener("click", generateStarterCode);

    // Format Code Button
    document.getElementById("btn-format-code").addEventListener("click", () => {
        if (editor) editor.getAction('editor.action.formatDocument').run();
    });

    // Reset Code Button
    document.getElementById("btn-reset-code").addEventListener("click", () => {
        if (confirm("Bạn có chắc chắn muốn xóa code hiện tại và khôi phục code mẫu ban đầu?")) {
            generateStarterCode();
        }
    });

    // Mock Debug Buttons
    const mockBtn = document.getElementById("btn-mock-debug");
    if (mockBtn) mockBtn.addEventListener("click", runMockDebug);

    const quickMockBtn = document.getElementById("btn-quick-mock-test");
    if (quickMockBtn) quickMockBtn.addEventListener("click", runMockDebug);

    // Toggle Socket Panel Button in Nav
    document.getElementById("btn-toggle-socket-panel").addEventListener("click", () => {
        switchTab("tab-socket");
    });

    // Quick Socket Test from Problem View
    document.getElementById("btn-quick-socket-test").addEventListener("click", () => {
        switchTab("tab-socket");
        sendSocketProbe();
    });

    // Send Socket Probe Button
    document.getElementById("btn-send-socket-probe").addEventListener("click", sendSocketProbe);

    // Clear Terminal Button
    document.getElementById("btn-clear-terminal").addEventListener("click", () => {
        document.getElementById("terminal-content").textContent = "Cửa sổ Terminal đã được làm sạch.";
        document.getElementById("terminal-meta").style.display = "none";
    });

    // Toggle Panel Size Button
    document.getElementById("btn-toggle-panel-size").addEventListener("click", () => {
        const panel = document.getElementById("bottom-panel");
        panel.style.height = panel.style.height === "450px" ? "240px" : "450px";
        setTimeout(() => {
            if (editor) editor.layout();
        }, 220);
    });

    // Panel Tab click
    document.querySelectorAll(".panel-tab").forEach(tab => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });

    // Search filter
    document.getElementById("search-input").addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        applyFilter(currentProtocolFilter, query);
    });

    // Protocol filter chips
    let currentProtocolFilter = "ALL";
    document.querySelectorAll(".filter-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            currentProtocolFilter = chip.dataset.filter;
            const query = document.getElementById("search-input").value.toLowerCase().trim();
            applyFilter(currentProtocolFilter, query);
        });
    });

    // Copy Problem Info
    document.getElementById("btn-copy-problem-info").addEventListener("click", () => {
        if (!currentProblem) return;
        const text = `[${currentProblem.alias}] ${currentProblem.title}\nGiao thức: ${currentProblem.protocolType}\nMáy chủ: ${currentProblem.examServerHost || '36.50.135.242'}`;
        navigator.clipboard.writeText(text);
        alert("Đã sao chép thông tin bài tập vào bộ nhớ tạm (Clipboard)!");
    });

    // Credential Selection Change
    document.getElementById("select-saved-creds").addEventListener("change", async (e) => {
        const idx = e.target.value;
        if (idx !== "" && savedCreds[idx]) {
            const cred = savedCreds[idx];
            document.getElementById("input-student-code").value = cred.username;
            localStorage.setItem(STUDENT_CODE_KEY, cred.username);

            // Try auto-login to obtain token
            const resBox = document.getElementById("submit-response-area");
            resBox.textContent = `Đang đăng nhập tài khoản ${cred.username} để lấy Bearer token...`;
            try {
                // Qua backend proxy (gọi thẳng dbapi.ptit.edu.vn từ trình duyệt bị chặn CORS).
                // Chỉ lấy token cho lần nộp này, không đổi phiên đăng nhập hiện tại.
                const loginRes = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: cred.username, password: cred.password })
                });
                if (loginRes.ok) {
                    const data = await loginRes.json();
                    document.getElementById("input-ptit-token").value = data.accessToken;
                    resBox.innerHTML = `<span style="color:var(--accent-green);">[+] Đăng nhập thành công! Đã tự động điền Bearer token.</span>`;
                } else {
                    resBox.innerHTML = `<span style="color:var(--accent-red);">[-] Đăng nhập thất bại (Mã lỗi ${loginRes.status}). Vui lòng nhập token thủ công.</span>`;
                }
            } catch (err) {
                resBox.innerHTML = `<span style="color:var(--accent-red);">[-] Lỗi kết nối API: ${err.message}</span>`;
            }
        }
    });

    // Submit Code to PTIT Button
    document.getElementById("btn-submit-code-ptit").addEventListener("click", async () => {
        if (!currentProblem || !editor) return;
        // Token nhập tay (tài khoản khác) được ưu tiên, để trống thì dùng token của phiên đăng nhập
        const manualToken = document.getElementById("input-ptit-token").value.trim();
        const code = editor.getValue();
        const resBox = document.getElementById("submit-response-area");

        resBox.textContent = `Đang nộp mã nguồn cho bài [${currentProblem.alias || "JNP"}] lên hệ thống PTIT...`;

        const submitWith = async (token) => {
            const res = await fetch("/api/submit-ptit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    questionAlias: currentProblem.alias || "",
                    code: code,
                    token: token
                })
            });
            return res.json();
        };

        try {
            let data = await submitWith(manualToken || Auth.getToken());
            // Token phiên hết hạn giữa chừng: refresh một lần rồi nộp lại
            if (!manualToken && data.statusCode === 401) {
                const newToken = await Auth.refresh();
                if (!newToken) {
                    Auth.logout();
                    return;
                }
                data = await submitWith(newToken);
            }
            resBox.innerHTML = `
                <div style="color:var(--accent-green); margin-bottom: 4px;">[+] Kết quả phản hồi (Mã trạng thái: ${data.statusCode})</div>
                <pre style="font-size:11px; color:var(--text-primary);">${escapeHtml(JSON.stringify(data.response, null, 2))}</pre>
            `;
        } catch (e) {
            resBox.innerHTML = `<div style="color:var(--accent-red);">[-] Lỗi khi nộp bài: ${e.message}</div>`;
        }
    });

    // Keyboard Shortcut: Ctrl+Enter to Run Code
    window.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            runJavaCode();
        }
    });

    // Resize event on window
    window.addEventListener("resize", () => {
        if (editor) editor.layout();
    });
}

// 14. Apply Filters to Problem List
function applyFilter(protoFilter, searchQuery) {
    filteredProblems = allProblems.filter(p => {
        // Protocol filter
        if (protoFilter !== "ALL") {
            const pt = (p.protocolType || "").toUpperCase();
            if (protoFilter === "TCP_BYTE" && !pt.includes("BYTE")) return false;
            if (protoFilter === "TCP_DATA" && !pt.includes("DATA")) return false;
            if (protoFilter === "TCP_CHAR" && !pt.includes("CHARACTER")) return false;
            if (protoFilter === "TCP_OBJ" && !pt.includes("OBJECT")) return false;
            if (protoFilter === "TCP_NIO" && !pt.includes("NIO")) return false;
            if (protoFilter === "UDP" && !pt.includes("UDP")) return false;
            if (protoFilter === "RMI" && !pt.includes("RMI")) return false;
        }

        // Search query
        if (searchQuery) {
            const text = `${p.alias || ""} ${p.code || ""} ${p.title || ""} ${p.protocolType || ""} ${p.description || ""}`.toLowerCase();
            if (!text.includes(searchQuery)) return false;
        }

        return true;
    });

    renderProblemList();
}
