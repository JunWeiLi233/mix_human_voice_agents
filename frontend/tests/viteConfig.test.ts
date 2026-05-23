import { describe, expect, it, vi } from "vitest";
import { backendProxyUrl } from "../src/devServerConfig";

describe("vite config", () => {
  it("uses a configurable backend proxy URL for local smoke testing", async () => {
    vi.stubEnv("VITE_BACKEND_URL", "http://127.0.0.1:8001");

    expect(backendProxyUrl()).toBe("http://127.0.0.1:8001");
  });
});
