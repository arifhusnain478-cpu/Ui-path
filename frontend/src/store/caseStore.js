import { create } from "zustand";
import { getCase, getCases } from "../api/cases.js";
import { CASE_STATUSES, JURISDICTIONS, RISK_LEVELS } from "../config/constants.js";

const empty_filters = {
  jurisdiction: "",
  status: "",
  risk_level: "",
};

function buildApprovedFilters(filters) {
  const approved_filters = {};

  if (JURISDICTIONS.includes(filters?.jurisdiction)) {
    approved_filters.jurisdiction = filters.jurisdiction;
  }

  if (CASE_STATUSES.includes(filters?.status)) {
    approved_filters.status = filters.status;
  }

  if (RISK_LEVELS.includes(filters?.risk_level)) {
    approved_filters.risk_level = filters.risk_level;
  }

  return approved_filters;
}

export const useCaseStore = create((set) => ({
  cases: [],
  currentCase: null,
  loading: false,
  error: null,
  filters: empty_filters,
  fetchCases: async (filters = {}) => {
    set({ loading: true, error: null });

    try {
      const cases = await getCases(buildApprovedFilters(filters));
      set({ cases, loading: false, error: null });
    } catch (error) {
      set({
        cases: [],
        loading: false,
        error:
          error?.message ||
          "Cases could not be loaded from the documented contract.",
      });
    }
  },
  setFilters: (partial_filters) =>
    set((state) => ({
      filters: {
        ...state.filters,
        jurisdiction: partial_filters.jurisdiction ?? state.filters.jurisdiction,
        status: partial_filters.status ?? state.filters.status,
        risk_level: partial_filters.risk_level ?? state.filters.risk_level,
      },
    })),
  clearFilters: () => set({ filters: empty_filters }),
  fetchCase: async (case_id) => {
    set({ loading: true, error: null, currentCase: null });

    try {
      const currentCase = await getCase(case_id);
      set({ currentCase, loading: false, error: null });
    } catch (error) {
      set({
        currentCase: null,
        loading: false,
        error:
          error?.response?.status === 404
            ? "Case not found."
            : error?.message || "Case could not be loaded.",
      });
    }
  },
  refreshCurrentCase: async () => {
    const case_id = useCaseStore.getState().currentCase?.case_id;

    if (!case_id) {
      return;
    }

    await useCaseStore.getState().fetchCase(case_id);
  },
  clearCurrentCase: () => set({ currentCase: null }),
  clearError: () => set({ error: null }),
}));
