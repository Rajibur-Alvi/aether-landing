// ═══════════════════════════════════════════════════════════
// THE ENTROPY AESTHETIC — Frontend API Client
// ═══════════════════════════════════════════════════════════

import { createClient, SupabaseClient } from "@supabase/supabase-js";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "https://entropy-backend.onrender.com";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ── Types ──
export interface ChatSource {
  text: string;
  document_id: string;
  chunk_index: number;
  score: number;
}

export interface ChatMeta {
  entropy_score: number;
  latency_ms: number;
  tokens_per_second: number;
  data_density: number;
  sources: ChatSource[];
}

export interface ChatResponse {
  id: string;
  role: "assistant";
  content: string;
  meta: ChatMeta;
  created_at: string;
}

export interface IngestResponse {
  document_id: string;
  chunk_count: number;
  status: string;
  message: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  filename?: string;
  file_type?: string;
  file_size?: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface UserProfile {
  id: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  entropy_level: number;
  ghost_mode: boolean;
  theme: string;
  created_at: string;
  updated_at: string;
}

export interface CommandCenterSettings {
  inference_speed: "fast" | "balanced" | "thorough";
  model_preference: string;
  retrieval_depth: number;
  temperature: number;
  max_tokens: number;
  system_prompt?: string;
  updated_at: string;
}

export interface DarkDataEvent {
  id: string;
  event_type: string;
  event_data: Record<string, unknown>;
  created_at: string;
}

export interface ConversationItem {
  id: string;
  title: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  meta?: ChatMeta;
  created_at: string;
}

// ── Auth Token Helper ──
async function getAuthToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

// ── Base Fetch with Auth ──
async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAuthToken();
  if (!token) throw new Error("Not authenticated. Please sign in.");

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

// ── Chat ──
export interface ChatRequestPayload {
  message: string;
  conversation_id?: string;
  document_id?: string;
  model?: "fast" | "balanced" | "thorough";
  temperature?: number;
  max_tokens?: number;
}

export async function sendChatMessage(payload: ChatRequestPayload): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/chat/ask", { method: "POST", body: JSON.stringify(payload) });
}

export async function streamChatMessage(
  payload: ChatRequestPayload,
  onToken: (token: string) => void,
  onMeta: (meta: Record<string, unknown>) => void,
  onDone: (data: { content_length: number; entropy_score: number }) => void,
  onError: (err: Error) => void
): Promise<void> {
  const token = await getAuthToken();
  if (!token) { onError(new Error("Not authenticated")); return; }

  const res = await fetch(`${BACKEND_URL}/api/chat/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    onError(new Error(err.detail || "Stream failed"));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const parsed = JSON.parse(line.slice(6));
          if (parsed.content !== undefined) onToken(parsed.content);
          else if (parsed.data_density !== undefined) onMeta(parsed);
          else if (parsed.content_length !== undefined) onDone(parsed);
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function getConversations(): Promise<ConversationItem[]> {
  return apiFetch<ConversationItem[]>("/api/chat/conversations");
}

export async function getConversationMessages(conversationId: string): Promise<MessageItem[]> {
  return apiFetch<MessageItem[]>(`/api/chat/conversations/${conversationId}/messages`);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiFetch(`/api/chat/conversations/${conversationId}`, { method: "DELETE" });
}

// ── Ingest ──
export async function ingestText(title: string, content: string): Promise<IngestResponse> {
  return apiFetch<IngestResponse>("/api/ingest/text", {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export async function ingestFile(file: File, title: string): Promise<IngestResponse> {
  const token = await getAuthToken();
  if (!token) throw new Error("Not authenticated");
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);
  const res = await fetch(`${BACKEND_URL}/api/ingest/file`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

// ── Documents ──
export async function getDocuments(): Promise<{ documents: DocumentItem[]; total: number }> {
  return apiFetch("/api/documents");
}

export async function getDocument(documentId: string): Promise<DocumentItem> {
  return apiFetch(`/api/documents/${documentId}`);
}

export async function deleteDocument(documentId: string): Promise<{ status: string }> {
  return apiFetch(`/api/documents/${documentId}`, { method: "DELETE" });
}

// ── User ──
export async function getUserProfile(): Promise<UserProfile> {
  return apiFetch("/api/user/profile");
}

export async function updateUserProfile(updates: Partial<Pick<UserProfile, "username" | "full_name" | "avatar_url" | "entropy_level" | "ghost_mode" | "theme">>): Promise<UserProfile> {
  return apiFetch("/api/user/profile", { method: "PATCH", body: JSON.stringify(updates) });
}

export async function getCommandCenter(): Promise<CommandCenterSettings> {
  return apiFetch("/api/user/command-center");
}

export async function updateCommandCenter(updates: Partial<Pick<CommandCenterSettings, "inference_speed" | "model_preference" | "retrieval_depth" | "temperature" | "max_tokens" | "system_prompt">>): Promise<CommandCenterSettings> {
  return apiFetch("/api/user/command-center", { method: "PATCH", body: JSON.stringify(updates) });
}

export async function getDarkData(limit: number = 50): Promise<{ events: DarkDataEvent[]; total: number }> {
  return apiFetch(`/api/user/dark-data?limit=${limit}`);
}

// ── Auth ──
export async function signUp(email: string, password: string) { return supabase.auth.signUp({ email, password }); }
export async function signIn(email: string, password: string) { return supabase.auth.signInWithPassword({ email, password }); }
export async function signOut() { return supabase.auth.signOut(); }
export async function getCurrentSession() {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}
export function onAuthStateChange(callback: (event: string, session: unknown) => void) {
  return supabase.auth.onAuthStateChange((event, session) => callback(event, session));
}

// ── Visual Effect Mappers ──
export function mapEntropyToVisualIntensity(entropyScore: number) {
  const e = Math.min(1, Math.max(0, entropyScore));
  return { glitchIntensity: e * 0.8, noiseOpacity: e * 0.3, colorShift: e * 30, pulseSpeed: 3 - e * 2.5 };
}

export function mapLatencyToGhostEffect(latencyMs: number) {
  const normalized = Math.min(1, latencyMs / 3000);
  return { ghostOpacity: 1 - normalized * 0.7, flickerRate: normalized * 0.5, fadeDelay: normalized * 500, blurAmount: normalized * 4 };
}

export function mapDensityToStormEffect(dataDensity: number) {
  return { particleCount: Math.min(200, dataDensity * 30), connectionLines: Math.min(50, dataDensity * 8), scrollSpeed: Math.min(2, 0.3 + dataDensity * 0.2) };
}
