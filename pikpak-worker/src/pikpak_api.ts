import CryptoJS from 'crypto-js';

// Constants
const CLIENT_ID = "YNxT9w7GMdWvEOKa";
const CLIENT_SECRET = "dbw2OtmVEeuUvIptb1Coyg";
const CLIENT_VERSION = "1.47.1";
const PACKAGE_NAME = "com.pikcloud.pikpak";
const SDK_VERSION = "2.0.4.204000";
const APP_NAME = PACKAGE_NAME;
const PIKPAK_API_HOST = "api-drive.mypikpak.com";
const PIKPAK_USER_HOST = "user.mypikpak.com";

const SALTS = [
    "Gez0T9ijiI9WCeTsKSg3SMlx",
    "zQdbalsolyb1R/",
    "ftOjr52zt51JD68C3s",
    "yeOBMH0JkbQdEFNNwQ0RI9T3wU/v",
    "BRJrQZiTQ65WtMvwO",
    "je8fqxKPdQVJiy1DM6Bc9Nb1",
    "niV",
    "9hFCW2R1",
    "sHKHpe2i96",
    "p7c5E6AcXQ/IJUuAEC9W6",
    "",
    "aRv9hjc9P+Pbn+u3krN6",
    "BzStcgE8qVdqjEH16l4",
    "SqgeZvL5j9zoHP95xWHt",
    "zVof5yaJkPe3VFpadPof",
];

export interface PikPakConfig {
    username?: string;
    password?: string;
    deviceId?: string;
}

export class PikPakApi {
    private username?: string;
    private password?: string;
    private deviceId: string;
    private accessToken?: string;
    private refreshToken?: string;
    private userId?: string;
    private captchaToken?: string;

    // Simple in-memory cache for captcha tokens if needed,
    // though in a Worker environment this might reset per request.
    // For a persistent worker, we'd rely on logins per request or KV storage for tokens.

    constructor(config: PikPakConfig) {
        this.username = config.username;
        this.password = config.password;
        this.deviceId = config.deviceId || this.generateDeviceId();
    }

    private generateDeviceId(): string {
        // Simple random UUID-like string
        return crypto.randomUUID().replace(/-/g, "");
    }

    private getTimestamp(): number {
        return Math.floor(Date.now());
    }

    private captchaSign(timestamp: string): string {
        let sign = `${CLIENT_ID}${CLIENT_VERSION}${PACKAGE_NAME}${this.deviceId}${timestamp}`;
        for (const salt of SALTS) {
            sign = CryptoJS.MD5(sign + salt).toString();
        }
        return `1.${sign}`;
    }

    private generateDeviceSign(): string {
        const signatureBase = `${this.deviceId}${PACKAGE_NAME}1appkey`;
        const sha1Result = CryptoJS.SHA1(signatureBase).toString();
        const md5Result = CryptoJS.MD5(sha1Result).toString();
        return `div101.${this.deviceId}${md5Result}`;
    }

    private buildUserAgent(): string {
        const deviceSign = this.generateDeviceSign();
        const parts = [
            `ANDROID-${APP_NAME}/${CLIENT_VERSION}`,
            "protocolVersion/200",
            "accesstype/",
            `clientid/${CLIENT_ID}`,
            `clientversion/${CLIENT_VERSION}`,
            "action_type/",
            "networktype/WIFI",
            "sessionid/",
            `deviceid/${this.deviceId}`,
            "providername/NONE",
            `devicesign/${deviceSign}`,
            "refresh_token/",
            `sdkversion/${SDK_VERSION}`,
            `datetime/${this.getTimestamp()}`,
            `usrno/${this.userId || ""}`,
            `appname/${APP_NAME}`,
            "session_origin/",
            "grant_type/",
            "appid/",
            "clientip/",
            "devicename/CloudflareWorker",
            "osversion/13",
            "platformversion/10",
            "accessmode/",
            "devicemodel/CFWorker",
        ];
        return parts.join(" ");
    }

    private getHeaders(): Record<string, string> {
        const headers: Record<string, string> = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": this.captchaToken ? this.buildUserAgent() : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        };

        if (this.accessToken) {
            headers["Authorization"] = `Bearer ${this.accessToken}`;
        }
        if (this.captchaToken) {
            headers["X-Captcha-Token"] = this.captchaToken;
        }
        if (this.deviceId) {
            headers["X-Device-Id"] = this.deviceId;
        }

        return headers;
    }

    private async request(method: string, url: string, body?: any, params?: any): Promise<any> {
        let fullUrl = url;
        if (params) {
            const usp = new URLSearchParams();
            for (const k in params) {
                if (params[k] !== undefined) usp.append(k, params[k]);
            }
            fullUrl += (url.includes("?") ? "&" : "?") + usp.toString();
        }

        const headers = this.getHeaders();
        const opts: RequestInit = {
            method,
            headers,
        };

        if (body) {
            if (headers["Content-Type"]?.includes("application/x-www-form-urlencoded")) {
                 const usp = new URLSearchParams();
                 for (const k in body) {
                     usp.append(k, body[k]);
                 }
                 opts.body = usp.toString();
            } else {
                 opts.body = JSON.stringify(body);
            }
        }

        const resp = await fetch(fullUrl, opts);
        const json = await resp.json() as any;

        if (json.error) {
             throw new Error(json.error_description || json.error);
        }
        return json;
    }

    // --- Auth ---

    async captchaInit(action: string, meta?: any): Promise<any> {
        const url = `https://${PIKPAK_USER_HOST}/v1/shield/captcha/init`;
        if (!meta) {
            const t = this.getTimestamp().toString();
            meta = {
                captcha_sign: this.captchaSign(t),
                client_version: CLIENT_VERSION,
                package_name: PACKAGE_NAME,
                user_id: this.userId,
                timestamp: t,
            };
        }
        const data = {
            client_id: CLIENT_ID,
            action,
            device_id: this.deviceId,
            meta,
        };
        return this.request("POST", url, data);
    }

    async login(): Promise<void> {
        if (!this.username || !this.password) throw new Error("Username and password required");

        const loginUrl = `https://${PIKPAK_USER_HOST}/v1/auth/signin`;

        // 1. Get Captcha Token
        const metas: any = {};
        if (this.username.includes("@")) {
            metas.email = this.username;
        } else if (/^\d+$/.test(this.username)) {
            metas.phone_number = this.username;
        } else {
            metas.username = this.username;
        }

        const captchaRes = await this.captchaInit(`POST:${loginUrl}`, metas);
        this.captchaToken = captchaRes.captcha_token;

        // 2. Sign In
        const loginData = {
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            password: this.password,
            username: this.username,
            captcha_token: this.captchaToken,
        };

        const userInfo = await this.request("POST", loginUrl, loginData, undefined);

        this.accessToken = userInfo.access_token;
        this.refreshToken = userInfo.refresh_token;
        this.userId = userInfo.sub;

        // Clear captcha after use? Usually yes, but user agent might need it.
        // For subsequent requests we generally don't need X-Captcha-Token unless it's a specific action.
        // But the python code seems to keep it conditionally.
        // We will keep it for now but maybe null it if it expires.
    }

    // --- Offline Download ---

    async offlineDownload(fileUrl: string, parentId?: string): Promise<any> {
        // Captcha is needed for this action
        const captchaRes = await this.captchaInit("POST:/drive/v1/files");
        this.captchaToken = captchaRes.captcha_token;

        const url = `https://${PIKPAK_API_HOST}/drive/v1/files`;
        const data = {
            kind: "drive#file",
            upload_type: "UPLOAD_TYPE_URL",
            url: { url: fileUrl },
            folder_type: !parentId ? "DOWNLOAD" : "",
            parent_id: parentId,
        };

        const res = await this.request("POST", url, data);
        this.captchaToken = undefined; // clear after use
        return res;
    }

    async offlineList(limit: number = 100): Promise<any> {
        const url = `https://${PIKPAK_API_HOST}/drive/v1/tasks`;
        // default phase: RUNNING, ERROR
        const filters = {
            phase: { in: "PHASE_TYPE_RUNNING,PHASE_TYPE_ERROR,PHASE_TYPE_COMPLETE" }
        };

        const params = {
            type: "offline",
            thumbnail_size: "SIZE_SMALL",
            limit,
            filters: JSON.stringify(filters),
            with: "reference_resource",
        };

        return this.request("GET", url, undefined, params);
    }

    // --- File Ops ---

    async getDownloadUrl(fileId: string): Promise<string> {
        // Needs captcha? Python code says yes: GET:/drive/v1/files/{file_id}
        const captchaRes = await this.captchaInit(`GET:/drive/v1/files/${fileId}`);
        this.captchaToken = captchaRes.captcha_token;

        const url = `https://${PIKPAK_API_HOST}/drive/v1/files/${fileId}`;
        const res = await this.request("GET", url);
        this.captchaToken = undefined;

        return res.web_content_link || res.content_hash_link; // web_content_link is usually the download link
    }

    async getFile(fileId: string): Promise<any> {
        const url = `https://${PIKPAK_API_HOST}/drive/v1/files/${fileId}`;
        return this.request("GET", url, undefined, { thumbnail_size: "SIZE_LARGE" });
    }
}
