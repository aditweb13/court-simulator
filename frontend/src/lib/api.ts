/**
 * REST API client for Verdict courtroom simulator backend.
 */

export interface CaseSummary {
  id: string;
  slug: string;
  title: string;
  charge: string;
  jurisdiction: string;
  difficulty: string;
  summary: string;
}

export interface GuestAuthResponse {
  token: string;
  user: {
    id: string;
    display_name: string;
    is_guest: boolean;
  };
}

export interface TrialCreateResponse {
  id: string;
  case_id: string;
  mode: string;
  state: string;
}

const API_BASE = "";

/**
 * Obtain a guest JWT bearer token.
 */
export async function getGuestToken(): Promise<string> {
  const storedToken = sessionStorage.getItem("verdict_token");
  if (storedToken) return storedToken;

  const res = await fetch(`${API_BASE}/api/v1/auth/guest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: "Juror Guest" }),
  });

  if (!res.ok) {
    throw new Error(`Failed to obtain guest session: ${res.statusText}`);
  }

  const json = await res.json();
  const token = json.data.token;
  sessionStorage.setItem("verdict_token", token);
  return token;
}

/**
 * Fetch available courtroom cases.
 */
export async function fetchCases(): Promise<CaseSummary[]> {
  const token = await getGuestToken();
  const res = await fetch(`${API_BASE}/api/v1/cases`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    // If backend cases endpoint is not seeded or returns error, provide default fallback
    return [
      {
        id: "case_001",
        slug: "state-v-k-sharma",
        title: "State of Maharashtra v. K. Sharma",
        charge: "Section 103(1) Bharatiya Nyaya Sanhita, 2023 (Murder)",
        jurisdiction: "Sessions Court, Greater Mumbai",
        difficulty: "standard",
        summary:
          "The accused is charged with intentional homicide following a dispute at a commercial godown.",
      },
    ];
  }

  const json = await res.json();
  return json.data || [];
}

/**
 * Create a new trial instance on the backend.
 */
export async function createTrial(
  caseId: string,
  mode: string = "spectator",
): Promise<TrialCreateResponse> {
  const token = await getGuestToken();
  const res = await fetch(`${API_BASE}/api/v1/trials`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      case_id: caseId,
      mode: mode,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to create trial: ${res.statusText}`);
  }

  const json = await res.json();
  return json.data;
}

