import { createHmac, randomUUID } from "node:crypto";
import { resolvePrincipal } from "@/lib/auth";

export const deviceCookieName = "okno_device_id";
const defaultKey = "pilot-user-data-hmac-change-me";

function parseCookie(header: string | null, name: string) {
  if (!header) return "";
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return "";
}

function hmacIdentity(value: string) {
  const key = process.env.USER_DATA_HMAC_KEY?.trim() || defaultKey;
  return createHmac("sha256", key).update(value).digest("hex");
}

export type UserContext = {
  userKey: string;
  actor: string;
  authenticated: boolean;
  deviceId?: string;
  setCookie?: string;
};

export function resolveUserContext(request: Request): UserContext {
  const principal = resolvePrincipal(request);
  if (principal.authenticated) {
    return {
      userKey: hmacIdentity(`sso:${principal.subject}`),
      actor: principal.subject,
      authenticated: true,
    };
  }
  const existing = parseCookie(request.headers.get("cookie"), deviceCookieName);
  const valid = /^[a-zA-Z0-9_-]{16,128}$/u.test(existing) ? existing : "";
  const deviceId = valid || randomUUID();
  return {
    userKey: hmacIdentity(`device:${deviceId}`),
    actor: "pilot-device",
    authenticated: false,
    deviceId,
    setCookie: valid ? undefined : `${deviceCookieName}=${encodeURIComponent(deviceId)}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly`,
  };
}

export function withUserCookie(context: UserContext, headers: HeadersInit = {}) {
  const result = new Headers(headers);
  if (context.setCookie) result.set("set-cookie", context.setCookie);
  return result;
}

export function userDataKeyIsSafe() {
  const key = process.env.USER_DATA_HMAC_KEY?.trim() || "";
  return key.length >= 32 && key !== defaultKey;
}
