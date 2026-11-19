"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, CloudOff, RefreshCw, Trash2, X } from "lucide-react";
import { formatINR } from "@/lib/i18n";
import { OfflineDraftItem, removeOfflineDraft } from "@/lib/offline-store";
import { Badge, Button } from "@/components/ui/primitives";

export function OfflineDraftsDrawer({
  drafts,
  isOnline,
  syncing,
  onSync,
  onClose,
  onChanged,
}: {
  drafts: OfflineDraftItem[];
  isOnline: boolean;
  syncing: boolean;
  onSync: () => Promise<void>;
  onClose: () => void;
  onChanged: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/75 backdrop-blur-sm p-0 sm:p-4">
      <div className="w-full sm:max-w-lg rounded-t-3xl sm:rounded-2xl border border-white/12 bg-[#141418] p-5 max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <h3 className="text-base font-semibold text-[#F5F5F7]">Offline Draft Queue</h3>
            <p className="text-xs text-[#9A9AA6]">
              Offline drafts are local-only and are NOT signed until synchronized and verified by the server.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-xl text-[#9A9AA6] hover:bg-white/10 hover:text-white cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="my-4 flex-1 space-y-3 overflow-y-auto pr-1">
          {drafts.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#9A9AA6]">No offline drafts stored.</p>
          ) : (
            drafts.map((d) => (
              <div
                key={d.client_draft_id}
                className="rounded-xl border border-white/10 bg-[#0B0B0D]/80 p-3.5 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-[#F5F5F7]">{d.payload.customer_name}</p>
                    <p className="text-xs text-[#9A9AA6]">
                      {d.payload.item_description} · {d.payload.gross_weight_g} g ({d.payload.purity_pct}%)
                    </p>
                  </div>
                  <Badge
                    tone={
                      d.sync_status === "synced"
                        ? "emerald"
                        : d.sync_status === "conflict"
                        ? "rose"
                        : "amber"
                    }
                  >
                    {d.sync_status === "synced" && <CheckCircle2 className="h-3 w-3" />}
                    {d.sync_status === "conflict" && <AlertTriangle className="h-3 w-3" />}
                    {d.sync_status === "pending" && <CloudOff className="h-3 w-3" />}
                    {d.sync_status}
                  </Badge>
                </div>

                {d.payload.jeweller_offered_value_inr && (
                  <p className="text-xs text-[#E8D5B5] tabular-nums">
                    Draft offer: {formatINR(d.payload.jeweller_offered_value_inr)}
                  </p>
                )}

                {d.sync_message && <p className="text-xs text-[#9A9AA6]">{d.sync_message}</p>}

                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-[#6E6E7A] font-mono">{d.client_draft_id}</span>
                  <button
                    type="button"
                    onClick={() => {
                      removeOfflineDraft(d.client_draft_id);
                      onChanged();
                    }}
                    className="inline-flex items-center gap-1 text-xs text-rose-300 hover:text-rose-200 cursor-pointer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remove
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-white/10 pt-3">
          <span className="text-xs text-[#9A9AA6]">
            {isOnline ? "Connection ready" : "Connect to internet to sync"}
          </span>
          <Button onClick={onSync} disabled={!isOnline || syncing || drafts.every((d) => d.sync_status !== "pending")}>
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Synchronizing..." : "Sync Pending Drafts"}
          </Button>
        </div>
      </div>
    </div>
  );
}
