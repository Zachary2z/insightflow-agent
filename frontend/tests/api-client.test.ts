import { describe, expect, it, vi } from "vitest";
import { createWorkspace } from "../lib/api";

describe("api client", () => {
  it("creates a workspace through FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ workspace_id: "ws_1", name: "Demo" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createWorkspace("Demo");

    expect(result.workspace_id).toBe("ws_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/workspaces",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
