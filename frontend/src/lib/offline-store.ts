import { apiRequest } from "./api";

export interface OfflineTransactionPayload {
  customer_name: string;
  customer_mobile: string;
  customer_preferred_language: "en" | "ta";
  consent_granted: boolean;
  item_description: string;
  category: string;
  hallmark_huid?: string | null;
  stone_or_non_gold_description?: string | null;
  gross_weight_g: string;
  non_gold_weight_g: string;
  net_gold_weight_g?: string | null;
  purity_pct: string;
  purity_karat_label: string;
  measurement_source: "instrument" | "manual" | "simulated_demo";
  instrument_name?: string | null;
  test_report_ref?: string | null;
  ocr_extracted?: boolean;
  rate_24k_per_g: string;
  rate_source: string;
  benchmark_reference_rate_per_g?: string | null;
  is_simulated_rate?: boolean;
  deductions: {
    deduction_type: string;
    label: string;
    amount_inr: string;
    reason: string;
    supporting_doc_ref?: string | null;
  }[];
  jeweller_offered_value_inr?: string | null;
  offer_difference_explanation?: string | null;
  notes?: string | null;
  is_demo: boolean;
}

export interface OfflineDraftItem {
  client_draft_id: string;
  client_updated_at: string;
  sync_status: "pending" | "synced" | "conflict";
  sync_message?: string;
  server_transaction_id?: string;
  server_transaction_code?: string;
  payload: OfflineTransactionPayload;
}

const STORAGE_KEY = "goldproof_offline_drafts_v1";

export function loadOfflineDrafts(): OfflineDraftItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveOfflineDrafts(items: OfflineDraftItem[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("goldproof-drafts-changed"));
}

export function enqueueOfflineDraft(payload: OfflineTransactionPayload): OfflineDraftItem {
  const current = loadOfflineDrafts();
  const draft: OfflineDraftItem = {
    client_draft_id: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    client_updated_at: new Date().toISOString(),
    sync_status: "pending",
    sync_message: "Saved offline locally. Not yet server-verified or digitally signed.",
    payload,
  };
  saveOfflineDrafts([draft, ...current]);
  return draft;
}

export function removeOfflineDraft(clientDraftId: string): void {
  const next = loadOfflineDrafts().filter((d) => d.client_draft_id !== clientDraftId);
  saveOfflineDrafts(next);
}

export async function syncPendingDrafts(): Promise<OfflineDraftItem[]> {
  const all = loadOfflineDrafts();
  const pending = all.filter((d) => d.sync_status === "pending");
  if (pending.length === 0) return all;

  const response = await apiRequest<{
    results: {
      client_draft_id: string;
      status: string;
      transaction_id?: string;
      transaction_code?: string;
      message: string;
    }[];
  }>("/api/sync/drafts", {
    method: "POST",
    body: JSON.stringify({
      drafts: pending.map((d) => ({
        client_draft_id: d.client_draft_id,
        client_updated_at: d.client_updated_at,
        payload: d.payload,
      })),
    }),
  });

  const resultMap = new Map(response.results.map((r) => [r.client_draft_id, r]));
  const updated = all.map((item) => {
    const res = resultMap.get(item.client_draft_id);
    if (!res) return item;
    if (res.status === "created" || res.status === "updated" || res.status === "already_synced") {
      return {
        ...item,
        sync_status: "synced" as const,
        sync_message: res.message,
        server_transaction_id: res.transaction_id,
        server_transaction_code: res.transaction_code,
      };
    }
    return {
      ...item,
      sync_status: "conflict" as const,
      sync_message: res.message,
      server_transaction_id: res.transaction_id,
      server_transaction_code: res.transaction_code,
    };
  });

  saveOfflineDrafts(updated);
  return updated;
}
