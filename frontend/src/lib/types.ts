export type UserRole = "jeweller" | "customer" | "admin";
export type Language = "en" | "ta";

export interface JewellerProfile {
  id: string;
  shop_name: string;
  shop_code: string;
  city: string;
  state: string;
  bis_hallmark_license?: string | null;
  policy_max_deduction_pct: string;
  policy_max_wastage_pct: string;
  policy_max_fixed_deduction_inr: string;
  policy_notes?: string | null;
}

export interface User {
  id: string;
  email: string;
  phone?: string | null;
  full_name: string;
  role: UserRole;
  preferred_language: Language;
  is_demo: boolean;
  jeweller_profile?: JewellerProfile | null;
}

export interface DemoAccount {
  label: string;
  email: string;
  password: string;
  role: UserRole;
  preferred_language: Language;
  description: string;
}

export interface DeductionItem {
  id?: string;
  deduction_type: string;
  label: string;
  amount_inr: string;
  percentage_of_gross?: string;
  reason?: string;
  supporting_doc_ref?: string | null;
}

export interface CalculationStep {
  step: number;
  code: string;
  label: string;
  formula: string;
  value: string;
  unit: string;
}

export interface AnomalyFlag {
  id?: string;
  detection_method: "rule_based" | "ml_isolation_forest";
  code: string;
  severity: "info" | "attention" | "review_required";
  title: string;
  message: string;
  evidence: Record<string, unknown>;
  is_resolved?: boolean;
}

export interface TransactionSummary {
  id: string;
  transaction_code: string;
  status: string;
  version_number: number;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  shop_name: string;
  customer_name: string;
  item_description: string;
  net_gold_weight_g: string;
  purity_pct: string;
  purity_karat_label: string;
  measurement_source: string;
  total_deductions_inr: string;
  calculated_net_value_inr: string;
  jeweller_offered_value_inr: string;
  review_flag_count: number;
  has_passport: boolean;
  acknowledgement_roles: string[];
}

export interface TransactionDetail {
  id: string;
  transaction_code: string;
  status: string;
  version_number: number;
  parent_transaction_id?: string | null;
  parent_transaction_code?: string | null;
  amended_by_transaction_code?: string | null;
  amendment_reason?: string | null;
  client_draft_id?: string | null;
  is_demo: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  jeweller: {
    id: string;
    shop_name: string;
    shop_code: string;
    city: string;
    state: string;
    bis_hallmark_license?: string | null;
    policy_max_deduction_pct: string;
    policy_max_fixed_deduction_inr: string;
  };
  customer: {
    id: string;
    full_name: string;
    mobile_number: string;
    preferred_language: Language;
  };
  jewellery_items: {
    id: string;
    item_description: string;
    category: string;
    hallmark_huid?: string | null;
    stone_or_non_gold_description?: string | null;
  }[];
  measurement: {
    gross_weight_g: string;
    non_gold_weight_g: string;
    net_gold_weight_g: string;
    purity_pct: string;
    purity_karat_label: string;
    measurement_source: "instrument" | "manual" | "simulated_demo";
    instrument_name?: string | null;
    test_report_ref?: string | null;
    measured_at: string;
    ocr_extracted: boolean;
  } | null;
  rate: {
    rate_24k_per_g: string;
    rate_source: string;
    rate_timestamp: string;
    benchmark_reference_rate_per_g?: string | null;
    is_simulated_rate: boolean;
  } | null;
  deductions: DeductionItem[];
  valuation: {
    pure_gold_weight_g: string;
    gross_reference_value_inr: string;
    total_deductions_inr: string;
    calculated_net_value_inr: string;
    jeweller_offered_value_inr: string;
    offer_difference_inr: string;
    offer_difference_explanation?: string | null;
    assumptions: Record<string, unknown>;
    calculation_steps: CalculationStep[];
    computed_at: string;
  } | null;
  anomaly_flags: AnomalyFlag[];
  ml_status: {
    enabled: boolean;
    sample_count: number;
    min_samples_required: number;
    trained_on_demo_data: boolean;
    reason?: string;
  };
  acknowledgements: {
    id: string;
    party_role: "jeweller" | "customer";
    acknowledged_by_name: string;
    acknowledged_at: string;
    method: string;
    note?: string | null;
  }[];
  digital_passport: {
    id: string;
    transaction_code: string;
    version_number: number;
    payload_sha256: string;
    previous_passport_hash?: string | null;
    signature_algorithm: string;
    signature_b64: string;
    public_key_fingerprint: string;
    verification_url: string;
    qr_data_uri: string;
    signed_at: string;
    is_revoked_by_amendment: boolean;
  } | null;
  audit_logs: {
    sequence_number: number;
    action: string;
    actor_role: string;
    details: Record<string, unknown>;
    entry_hash: string;
    created_at: string;
  }[];
}

export interface ValuationPreviewResponse {
  gross_weight_g: string;
  non_gold_weight_g: string;
  net_gold_weight_g: string;
  purity_pct: string;
  pure_gold_weight_g: string;
  rate_24k_per_g: string;
  gross_reference_value_inr: string;
  total_deductions_inr: string;
  calculated_net_value_inr: string;
  jeweller_offered_value_inr: string;
  offer_difference_inr: string;
  assumptions: Record<string, unknown>;
  calculation_steps: CalculationStep[];
  flags: AnomalyFlag[];
  ml_status: {
    enabled: boolean;
    sample_count: number;
    min_samples_required: number;
    trained_on_demo_data: boolean;
    reason?: string;
  };
  requires_review: boolean;
}

export interface PassportVerificationResponse {
  transaction_code: string;
  version_number: number;
  transaction_status: string;
  is_demo: boolean;
  integrity_status: "verified" | "tampered" | "superseded_by_amendment";
  integrity_message: string;
  signature_valid: boolean;
  hash_matches_stored_payload: boolean;
  matches_current_db_record: boolean;
  payload_sha256: string;
  current_db_sha256: string;
  previous_passport_hash?: string | null;
  signature_algorithm: string;
  signature_b64: string;
  public_key_b64: string;
  public_key_fingerprint: string;
  signed_at: string;
  verification_url: string;
  qr_data_uri: string;
  verification_scope_notice: string;
  parent_transaction_code?: string | null;
  amended_by_transaction_code?: string | null;
  jeweller: {
    shop_name: string;
    shop_code: string;
    city: string;
    state: string;
    bis_hallmark_license?: string | null;
  };
  customer_display: {
    full_name: string;
    masked_mobile: string;
  };
  jewellery_items: {
    item_description: string;
    category: string;
    hallmark_huid?: string | null;
    stone_or_non_gold_description?: string | null;
  }[];
  measurement: {
    gross_weight_g: string;
    non_gold_weight_g: string;
    net_gold_weight_g: string;
    purity_pct: string;
    purity_karat_label: string;
    measurement_source: string;
    instrument_name?: string | null;
    test_report_ref?: string | null;
    measured_at: string;
  };
  rate: {
    rate_24k_per_g: string;
    rate_source: string;
    rate_timestamp: string;
    is_simulated_rate: boolean;
  };
  deductions: DeductionItem[];
  valuation: {
    pure_gold_weight_g: string;
    gross_reference_value_inr: string;
    total_deductions_inr: string;
    calculated_net_value_inr: string;
    jeweller_offered_value_inr: string;
    offer_difference_inr: string;
    offer_difference_explanation?: string | null;
    calculation_steps: CalculationStep[];
  };
  acknowledgements: {
    party_role: string;
    acknowledged_by_name: string;
    acknowledged_at: string;
    method: string;
  }[];
  anomaly_summary: AnomalyFlag[];
}
