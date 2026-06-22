const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function parseJsonResponse(response: Response, message: string) {
  if (!response.ok) {
    throw new Error(`${message}: ${response.status}`);
  }
  return response.json();
}

export async function createWorkspace(name: string) {
  const response = await fetch(`${API_BASE}/api/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return parseJsonResponse(response, "Failed to create workspace");
}

export async function listWorkspaces() {
  const response = await fetch(`${API_BASE}/api/workspaces`);
  return parseJsonResponse(response, "Failed to list workspaces");
}

export async function createProfile(workspaceId: string) {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/profile`, {
    method: "POST",
  });
  return parseJsonResponse(response, "Failed to create profile");
}

export async function createSemanticDraft(workspaceId: string) {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/semantic-layer/draft`, {
    method: "POST",
  });
  return parseJsonResponse(response, "Failed to create semantic draft");
}

export async function runAnalysis(workspaceId: string, userQuestion: string) {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_question: userQuestion }),
  });
  return parseJsonResponse(response, "Failed to run analysis");
}
