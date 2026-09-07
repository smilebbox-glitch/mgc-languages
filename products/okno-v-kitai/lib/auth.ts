import { timingSafeEqual } from "node:crypto";
import { logSecurityEvent } from "@/lib/logger";

export type Role = "none" | "viewer" | "editor" | "admin";
export type Principal = {
  authenticated: boolean;
  subject: string;
  email?: string;
  groups: string[];
  role: Role;
  mode: "disabled" | "proxy";
};

const rank: Record<Role, number> = { none: 0, viewer: 1, editor: 2, admin: 3 };

function safeEqual(left: string, right: string) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function splitGroups(value: string | null) {
  return (value ?? "")
    .split(/[;,]/u)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 100);
}

function roleFromGroups(groups: string[]): Role {
  const normalized = new Set(groups.map((value) => value.toLocaleLowerCase("en-US")));
  const adminGroup = (process.env.AUTH_ADMIN_GROUP || "okno-china-admin").toLocaleLowerCase("en-US");
  const editorGroup = (process.env.AUTH_EDITOR_GROUP || "okno-china-editor").toLocaleLowerCase("en-US");
  if (normalized.has(adminGroup)) return "admin";
  if (normalized.has(editorGroup)) return "editor";
  return "viewer";
}

function tokenPrincipal(request: Request): Principal | null {
  const expected = process.env.ADMIN_API_TOKEN?.trim();
  if (!expected) return null;
  const bearer = request.headers.get("authorization")?.replace(/^Bearer\s+/iu, "").trim();
  const supplied = request.headers.get("x-admin-token")?.trim() || bearer || "";
  if (!supplied || !safeEqual(supplied, expected)) return null;
  return {
    authenticated: true,
    subject: "local-admin-token",
    groups: ["local-admin"],
    role: "admin",
    mode: "disabled",
  };
}

export function resolvePrincipal(request: Request): Principal {
  const mode = process.env.AUTH_MODE?.trim().toLocaleLowerCase("en-US") === "proxy" ? "proxy" : "disabled";
  if (mode === "disabled") {
    return tokenPrincipal(request) ?? {
      authenticated: false,
      subject: "pilot-anonymous",
      groups: [],
      role: "viewer",
      mode,
    };
  }

  const expectedSecret = process.env.AUTH_PROXY_SECRET?.trim() || "";
  const suppliedSecret = request.headers.get("x-okno-proxy-secret")?.trim() || "";
  if (!expectedSecret || !suppliedSecret || !safeEqual(expectedSecret, suppliedSecret)) {
    return { authenticated: false, subject: "untrusted-request", groups: [], role: "none", mode };
  }

  const subject = request.headers.get("x-forwarded-user")?.trim() || request.headers.get("x-forwarded-email")?.trim() || "";
  if (!subject) return { authenticated: false, subject: "missing-identity", groups: [], role: "none", mode };
  const groups = splitGroups(request.headers.get("x-forwarded-groups"));
  return {
    authenticated: true,
    subject: subject.slice(0, 160),
    email: request.headers.get("x-forwarded-email")?.trim().slice(0, 254),
    groups,
    role: roleFromGroups(groups),
    mode,
  };
}

export function hasRole(principal: Principal, minimum: Exclude<Role, "none">) {
  return rank[principal.role] >= rank[minimum];
}

export function authorize(request: Request, minimum: Exclude<Role, "none">, requestId = "") {
  const principal = resolvePrincipal(request);
  if (!hasRole(principal, minimum)) {
    logSecurityEvent("authorization_denied", {
      outcome: "blocked",
      requestId,
      actor: principal.subject,
      requiredRole: minimum,
      actualRole: principal.role,
      authenticated: principal.authenticated,
      path: new URL(request.url).pathname,
    });
    return {
      principal,
      response: Response.json(
        { error: principal.authenticated ? "Недостаточно прав." : "Требуется корпоративная аутентификация." },
        { status: principal.authenticated ? 403 : 401, headers: { "cache-control": "no-store", ...(requestId ? { "x-request-id": requestId } : {}) } },
      ),
    };
  }
  return { principal, response: null };
}
