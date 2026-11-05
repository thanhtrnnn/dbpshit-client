/**
 * Lập Chình Mạng - Auth helper
 * Port từ db-pshit-remastered (AuthContext.jsx + services/api.js):
 *   - Đăng nhập PTIT: POST /api/auth/login  -> dbapi /api/auth/auth/ptit-login
 *   - Làm mới token:  POST /api/auth/refresh -> dbapi /api/auth/auth/refresh-token
 *   - Access/refresh token lưu ở localStorage, gắn header "Authorization: Bearer <token>"
 *   - Gặp 401 thì refresh 1 lần (single-flight) rồi gửi lại request, thất bại thì về trang login
 */
const Auth = (() => {
    const TOKEN_KEY = "db_ptit_token";
    const REFRESH_KEY = "db_ptit_refresh";
    const USER_KEY = "db_ptit_user";
    const LOGIN_PAGE = "/login.html";

    let refreshPromise = null;

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_KEY);
    }

    function decodeJwt(token) {
        try {
            const payload = token.split(".")[1];
            const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
            const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
            const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
            return JSON.parse(new TextDecoder().decode(bytes));
        } catch (e) {
            return null;
        }
    }

    function isExpired(token) {
        const decoded = token ? decodeJwt(token) : null;
        if (!decoded) return true;
        if (!decoded.exp) return false;
        return decoded.exp * 1000 < Date.now();
    }

    function setTokens(accessToken, refreshToken) {
        if (accessToken) localStorage.setItem(TOKEN_KEY, accessToken);
        if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
    }

    function getUser() {
        try {
            const cached = JSON.parse(localStorage.getItem(USER_KEY) || "null");
            if (cached) return cached;
        } catch (e) { /* ignore */ }
        const token = getToken();
        return token ? decodeJwt(token) : null;
    }

    async function readError(res) {
        try {
            const data = await res.json();
            return data.detail || data.message || `Lỗi ${res.status}`;
        } catch (e) {
            return `Lỗi ${res.status}`;
        }
    }

    async function fetchProfile() {
        const res = await authFetch("/api/auth/me");
        if (!res.ok) return null;
        const user = await res.json();
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return user;
    }

    async function login(username, password) {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) throw new Error(await readError(res));
        const data = await res.json();
        clearSession();
        setTokens(data.accessToken, data.refreshToken);
        try {
            await fetchProfile();
        } catch (e) { /* profile chỉ để hiển thị, không bắt buộc */ }
        return getUser();
    }

    // Single-flight: nhiều request cùng 401 chỉ gọi refresh một lần
    function refresh() {
        if (refreshPromise) return refreshPromise;
        const refreshToken = getRefreshToken();
        if (!refreshToken) return Promise.resolve(null);

        refreshPromise = fetch("/api/auth/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refreshToken }),
        })
            .then(async (res) => {
                if (!res.ok) return null;
                const data = await res.json();
                if (!data.accessToken) return null;
                setTokens(data.accessToken, data.refreshToken);
                return data.accessToken;
            })
            .catch(() => null)
            .finally(() => {
                refreshPromise = null;
            });
        return refreshPromise;
    }

    function redirectToLogin() {
        const next = window.location.pathname + window.location.search;
        window.location.replace(`${LOGIN_PAGE}?next=${encodeURIComponent(next)}`);
    }

    function logout() {
        clearSession();
        window.location.replace(LOGIN_PAGE);
    }

    // Tương đương PrivateRoute: token còn hạn -> OK, hết hạn -> thử refresh, không được -> về login
    async function requireAuth() {
        const token = getToken();
        if (token && !isExpired(token)) return true;
        if (await refresh()) return true;
        clearSession();
        redirectToLogin();
        return false;
    }

    // fetch có gắn Bearer token, tự refresh + gửi lại khi gặp 401
    async function authFetch(url, options = {}) {
        const withAuth = (token) => {
            const headers = new Headers(options.headers || {});
            if (token) headers.set("Authorization", `Bearer ${token}`);
            return fetch(url, { ...options, headers });
        };

        const res = await withAuth(getToken());
        if (res.status !== 401) return res;

        const newToken = await refresh();
        if (!newToken) {
            clearSession();
            redirectToLogin();
            return res;
        }
        return withAuth(newToken);
    }

    return {
        getToken,
        getUser,
        decodeJwt,
        isExpired,
        login,
        logout,
        refresh,
        requireAuth,
        authFetch,
        fetchProfile,
    };
})();
