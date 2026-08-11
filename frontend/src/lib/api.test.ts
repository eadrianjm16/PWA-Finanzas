import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, clearToken, getToken, setToken } from "./api";

describe("token storage", () => {
  beforeEach(() => window.localStorage.clear());

  it("returns null when no token is stored", () => {
    expect(getToken()).toBeNull();
  });

  it("round-trips a token through set/get", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("removes the token on clear", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the Authorization header when a token is present", async () => {
    setToken("my-token");
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiFetch("/api/whatever");

    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("does not attach an Authorization header when there is no token", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiFetch("/api/whatever");

    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("returns undefined for a 204 No Content response", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));
    const result = await apiFetch("/api/whatever");
    expect(result).toBeUndefined();
  });

  it("throws ApiError with the server's detail message on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Contraseña incorrecta" }), { status: 401 })
    );

    await expect(apiFetch("/api/auth/login")).rejects.toMatchObject({
      status: 401,
      message: "Contraseña incorrecta",
    });
  });

  it("falls back to the raw body when the error response isn't JSON", async () => {
    vi.mocked(fetch).mockImplementation(async () => new Response("Internal Server Error", { status: 500 }));

    await expect(apiFetch("/api/whatever")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/api/whatever")).rejects.toMatchObject({ status: 500 });
  });
});
