import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "chatbook_session";
const API_BASE = process.env.CHATBOOK_API_URL ?? "http://127.0.0.1:8000/api/v1";

type RouteContext = { params: Promise<{ path: string[] }> };
interface TokenPayload {
  access_token?: unknown;
  expires_at?: unknown;
  user?: unknown;
}

function backendUrl(path: string[], request: NextRequest): string {
  const cleanBase = API_BASE.replace(/\/$/, "");
  const cleanPath = path.map(encodeURIComponent).join("/");
  return `${cleanBase}/${cleanPath}${request.nextUrl.search}`;
}

async function proxy(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path } = await context.params;
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const idempotencyKey = request.headers.get("idempotency-key");
  const requestId = request.headers.get("x-request-id");
  if (contentType) headers.set("Content-Type", contentType);
  headers.set("Accept", "application/json");
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  if (requestId) headers.set("X-Request-ID", requestId);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  try {
    const hasBody = request.method !== "GET" && request.method !== "HEAD";
    const upstream = await fetch(backendUrl(path, request), {
      method: request.method,
      headers,
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    const upstreamRequestId = upstream.headers.get("x-request-id");
    if (upstreamContentType) responseHeaders.set("Content-Type", upstreamContentType);
    if (upstreamRequestId) responseHeaders.set("X-Request-ID", upstreamRequestId);
    const bodyText = upstream.status === 204 ? null : await upstream.text();
    const response = new NextResponse(bodyText, {
      status: upstream.status,
      headers: responseHeaders,
    });

    const route = path.join("/");
    if (route === "auth/token" && upstream.ok) {
      let payload: TokenPayload | null = null;
      try {
        payload = bodyText ? (JSON.parse(bodyText) as TokenPayload) : null;
      } catch {
        payload = null;
      }
      if (payload && typeof payload.access_token === "string") {
        const expires =
          typeof payload.expires_at === "string" ? new Date(payload.expires_at) : undefined;
        const safeResponse = NextResponse.json(
          {
            token_type: "bearer",
            expires_at: payload.expires_at,
            user: payload.user,
          },
          { status: upstream.status, headers: responseHeaders },
        );
        safeResponse.cookies.set(COOKIE_NAME, payload.access_token, {
          httpOnly: true,
          sameSite: "lax",
          secure: process.env.NODE_ENV === "production",
          path: "/",
          expires,
        });
        return safeResponse;
      }
    }
    if (route === "auth/logout") response.cookies.delete(COOKIE_NAME);
    if (upstream.status === 401) response.cookies.delete(COOKIE_NAME);
    return response;
  } catch {
    return NextResponse.json(
      {
        error: "backend_unavailable",
        message: "Chatbooks could not reach the financial service. Please try again.",
        request_id: crypto.randomUUID(),
        details: null,
      },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
