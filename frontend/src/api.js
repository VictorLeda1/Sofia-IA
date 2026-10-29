const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function detailText(data) {
  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.error === "string") return data.error;
  if (data && typeof data === "object") {
    const first = Object.entries(data).find(([, value]) => value);
    if (first)
      return `${first[0]}: ${Array.isArray(first[1]) ? first[1].join(" ") : String(first[1])}`;
  }
  return "Não foi possível concluir. Tente novamente.";
}

export async function request(path, { method = "GET", body, signal } = {}) {
  const response = await fetch(`${API_BASE}/api${path}`, {
    method,
    credentials: "include",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("A API respondeu em um formato inesperado.");
  }
  if (!response.ok) throw new Error(detailText(data));
  return data;
}
