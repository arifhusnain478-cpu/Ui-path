import examples from "../mocks/contract_safe_examples.json";

const now = Date.now();
const mock_state_key = "qualitrace_mock_api_state";

function readMockState() {
  if (typeof window === "undefined") {
    return null;
  }

  const stored_state = window.sessionStorage.getItem(mock_state_key);

  if (!stored_state) {
    return null;
  }

  try {
    return JSON.parse(stored_state);
  } catch {
    window.sessionStorage.removeItem(mock_state_key);
    return null;
  }
}

const stored_mock_state = readMockState();

function isoFromOffset(ms) {
  return new Date(now + ms).toISOString();
}

const cases = stored_mock_state?.cases || [
  {
    ...examples.complaint_create_response,
    product_name: "Metformin 500mg",
    batch_number: "MF-2024-0892",
    complaint_type: "quality",
    source_list: ["manufacturing_sop.pdf#odor-investigation", "batch_record_MF-2024-0892.pdf"],
    updated_at: isoFromOffset(-1000 * 60 * 45),
    current_stage: "Investigation review",
    description: "Tablet has unusual smell",
    patient_impact: false,
    status: "open",
    investigation_output: {
      evidence_summary: "Backend returned an investigation summary for the reported tablet odor.",
      root_cause_hypotheses: [
        {
          rank: 1,
          hypothesis: "Packaging exposure may have contributed to odor variation.",
          confidence: 0.78,
          source_ids: ["manufacturing_sop.pdf#odor-investigation"],
          supporting_evidence: "Returned evidence references packaging and odor handling checks.",
        },
        {
          rank: 2,
          hypothesis: "Batch storage condition deviation requires review.",
          confidence: 0.66,
          source_ids: ["batch_record_MF-2024-0892.pdf"],
          supporting_evidence: "Returned batch record citation indicates storage checkpoints.",
        },
      ],
      overall_confidence: 0.82,
      conflicting_sources: [],
      escalation_required: false,
      escalation_reason: null,
    },
    citations: [
      {
        source: "manufacturing_sop.pdf",
        section: "Odor investigation",
        text: "Returned mock citation text for local frontend testing.",
        relevance_score: 0.88,
      },
    ],
    capa_plan: [
      {
        type: "corrective",
        description: "Review packaging line odor controls.",
        responsible_role: "quality_reviewer",
        due_date: isoFromOffset(1000 * 60 * 60 * 24 * 3),
        status: "pending",
        evidence_required: "Packaging inspection record",
        effectiveness_metric: "No repeat odor complaints for matched product.",
        source_citations: ["manufacturing_sop.pdf#odor-investigation"],
      },
    ],
    sla_deadline: isoFromOffset(1000 * 60 * 60 * 6),
    pending_task_id: "T-001",
  },
  {
    case_id: "C-002",
    product_name: "Amlodipine 10mg",
    batch_number: null,
    complaint_type: "labeling",
    source_list: ["intake_form_C-002.pdf"],
    risk_level: "medium",
    status: "pending_review",
    jurisdiction: "EU",
    confidence_score: 0.62,
    created_at: isoFromOffset(-1000 * 60 * 60 * 12),
    updated_at: isoFromOffset(-1000 * 60 * 30),
    current_stage: "Awaiting information",
    description: "Complaint submitted without batch information.",
    patient_impact: false,
    investigation_output: null,
    capa_plan: null,
    sla_deadline: isoFromOffset(1000 * 60 * 45),
    pending_task_id: "T-002",
  },
  {
    case_id: "C-003",
    product_name: "Sterile Injectable 20ml",
    batch_number: "SI-CRIT-001",
    complaint_type: "contamination",
    source_list: ["sterility_report_SI-CRIT-001.pdf", "critical_escalation_policy.pdf"],
    risk_level: "critical",
    status: "pending_review",
    jurisdiction: "US",
    confidence_score: 0.91,
    created_at: isoFromOffset(-1000 * 60 * 60 * 2),
    updated_at: isoFromOffset(-1000 * 60 * 10),
    current_stage: "Critical review",
    description: "Visible contamination reported in sterile injectable product.",
    patient_impact: true,
    investigation_output: {
      evidence_summary: "Backend returned critical contamination evidence requiring human review.",
      root_cause_hypotheses: [
        {
          rank: 1,
          hypothesis: "Sterility excursion may have occurred during fill-finish.",
          confidence: 0.89,
          source_ids: ["sterility_report_SI-CRIT-001.pdf"],
          supporting_evidence: "Returned sterility report reference indicates contamination concern.",
        },
      ],
      overall_confidence: 0.91,
      conflicting_sources: [],
      escalation_required: true,
      escalation_reason: "Critical complaint returned by backend data.",
    },
    citations: [
      {
        source: "sterility_report_SI-CRIT-001.pdf",
        section: "Observation summary",
        authority: "Backend-provided authority",
        doc_type: "report",
        text: "Returned mock citation for local frontend testing of critical scenario.",
        relevance_score: 0.94,
      },
    ],
    capa_plan: [
      {
        type: "corrective",
        description: "Quarantine impacted lot pending investigation.",
        responsible_role: "quality_lead",
        due_date: isoFromOffset(1000 * 60 * 60 * 12),
        status: "pending",
        evidence_required: "Quarantine record",
      },
      {
        type: "preventive",
        description: "Review aseptic process monitoring trend.",
        responsible_role: "quality_lead",
        due_date: isoFromOffset(1000 * 60 * 60 * 24 * 5),
        status: "pending",
        evidence_required: "Trend review",
      },
    ],
    sla_deadline: isoFromOffset(1000 * 60 * 20),
    pending_task_id: "T-003",
  },
];

const tasks = stored_mock_state?.tasks || [
  {
    task_id: "T-001",
    case_id: "C-001",
    task_type: "risk_review",
    assigned_role: "quality_reviewer",
    sla_deadline: isoFromOffset(1000 * 60 * 60 * 6),
    status: "open",
    decision: null,
    override_reason: null,
    ai_recommendation: "Approve investigation path based on returned evidence.",
    confidence_score: 0.82,
    source_list: ["manufacturing_sop.pdf#odor-investigation"],
  },
  {
    task_id: "T-002",
    case_id: "C-002",
    task_type: "missing_info",
    assigned_role: "quality_reviewer",
    sla_deadline: isoFromOffset(1000 * 60 * 45),
    status: "open",
    decision: null,
    override_reason: null,
    ai_recommendation: "Request missing batch information before downstream review.",
    confidence_score: 0.62,
    source_list: ["intake_form_C-002.pdf"],
  },
  {
    task_id: "T-003",
    case_id: "C-003",
    task_type: "critical_escalation",
    assigned_role: "quality_lead",
    sla_deadline: isoFromOffset(1000 * 60 * 20),
    status: "open",
    decision: null,
    override_reason: null,
    ai_recommendation: "Human review required for critical contamination complaint.",
    confidence_score: 0.91,
    source_list: ["sterility_report_SI-CRIT-001.pdf"],
  },
];

const audits = stored_mock_state?.audits || {
  "C-001": [
    {
      event_id: "A-001",
      case_id: "C-001",
      timestamp: isoFromOffset(-1000 * 60 * 60),
      event_type: "ai_decision",
      actor: "ai",
      summary: "Risk and investigation recommendation returned by backend.",
    },
  ],
  "C-002": [
    {
      event_id: "A-002",
      case_id: "C-002",
      timestamp: isoFromOffset(-1000 * 60 * 30),
      event_type: "stage_transition",
      actor: "system",
      stage: "Awaiting information",
      summary: "Backend returned pending review state for missing batch information.",
    },
  ],
  "C-003": [
    {
      event_id: "A-003",
      case_id: "C-003",
      timestamp: isoFromOffset(-1000 * 60 * 20),
      event_type: "sla_event",
      actor: "system",
      summary: "Critical review SLA started from backend data.",
    },
  ],
};

function saveMockState() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    mock_state_key,
    JSON.stringify({ cases, tasks, audits }),
  );
}

function parseBody(data) {
  if (!data) {
    return {};
  }

  if (typeof data === "string") {
    return JSON.parse(data);
  }

  return data;
}

function response(config, status, data) {
  return Promise.resolve({
    data,
    status,
    statusText: String(status),
    headers: {},
    config,
    request: null,
  });
}

function notFound(config) {
  return Promise.reject({
    message: "Not found",
    response: {
      data: { error: "Not found" },
      status: 404,
      statusText: "404",
      headers: {},
      config,
      request: null,
    },
    config,
  });
}

function filterCases(params = {}) {
  return cases.filter((case_record) => {
    if (params.jurisdiction && case_record.jurisdiction !== params.jurisdiction) {
      return false;
    }

    if (params.status && case_record.status !== params.status) {
      return false;
    }

    if (params.risk_level && case_record.risk_level !== params.risk_level) {
      return false;
    }

    return true;
  });
}

function createCaseFromComplaint(body) {
  const is_critical = body.patient_impact || body.complaint_type === "contamination";
  const is_missing_info = body.batch_number === null;
  const case_id = `C-${String(cases.length + 1).padStart(3, "0")}`;
  const case_record = {
    case_id,
    product_name: body.product_name,
    batch_number: body.batch_number,
    complaint_type: body.complaint_type,
    source_list: [],
    risk_level: is_critical ? "critical" : "medium",
    status: is_missing_info || is_critical ? "pending_review" : "open",
    jurisdiction: body.market_code,
    confidence_score: is_critical ? 0.9 : is_missing_info ? 0.58 : 0.82,
    created_at: new Date().toISOString(),
    current_stage: is_missing_info ? "Awaiting information" : is_critical ? "Critical review" : "Created",
    description: body.description,
    patient_impact: body.patient_impact,
    investigation_output: null,
    capa_plan: null,
    sla_deadline: isoFromOffset(1000 * 60 * 60),
    pending_task_id: `T-${String(tasks.length + 1).padStart(3, "0")}`,
  };
  const task = {
    task_id: case_record.pending_task_id,
    case_id,
    task_type: is_missing_info ? "missing_info" : is_critical ? "critical_escalation" : "risk_review",
    assigned_role: is_critical ? "quality_lead" : "quality_reviewer",
    sla_deadline: case_record.sla_deadline,
    status: "open",
    decision: null,
    override_reason: null,
    ai_recommendation: "Backend mock state created a pending human task.",
    confidence_score: case_record.confidence_score,
    source_list: [],
  };
  cases.push(case_record);
  tasks.push(task);
  audits[case_id] = [
    {
      event_id: `A-${case_id}`,
      case_id,
      timestamp: case_record.created_at,
      event_type: "system_action",
      actor: "system",
      summary: "Mock backend created the complaint case.",
    },
  ];
  saveMockState();
  return case_record;
}

function completeTask(task_id, body) {
  const task = tasks.find((task_record) => task_record.task_id === task_id);

  if (!task) {
    return null;
  }

  task.decision = body.decision;
  task.override_reason = body.override_reason;
  task.status = "closed";

  const case_record = cases.find((item) => item.case_id === task.case_id);

  if (case_record) {
    case_record.status = body.decision === "approve" ? "closed" : "pending_review";
    case_record.updated_at = new Date().toISOString();
  }

  audits[task.case_id] = audits[task.case_id] || [];
  audits[task.case_id].push({
    event_id: `A-${task.task_id}-${audits[task.case_id].length + 1}`,
    case_id: task.case_id,
    timestamp: new Date().toISOString(),
    event_type: body.decision === "override" ? "human_override" : "human_decision",
    actor: "human",
    action: body.decision,
    summary: "Mock backend recorded a human task decision.",
    override_reason: body.override_reason,
  });

  saveMockState();
  return task;
}

export default function mockAdapter(config) {
  const method = (config.method || "get").toLowerCase();
  const path = config.url || "";

  if (method === "post" && path === "/auth/login") {
    return response(config, 200, {
      token: "mock_jwt_for_local_frontend_testing",
      user: {
        user_id: "mock-user-001",
        username: "Mock Reviewer",
        email: "mock.reviewer@example.test",
        role: "quality_reviewer",
      },
    });
  }

  if (method === "get" && path === "/complaints") {
    return response(config, 200, filterCases(config.params));
  }

  if (method === "post" && path === "/complaints") {
    return response(config, 200, createCaseFromComplaint(parseBody(config.data)));
  }

  const case_match = path.match(/^\/complaints\/([^/]+)$/);
  if (method === "get" && case_match) {
    const case_record = cases.find((item) => item.case_id === decodeURIComponent(case_match[1]));
    return case_record ? response(config, 200, case_record) : notFound(config);
  }

  const audit_match = path.match(/^\/cases\/([^/]+)\/audit$/);
  if (method === "get" && audit_match) {
    const case_id = decodeURIComponent(audit_match[1]);
    return response(config, 200, audits[case_id] || []);
  }

  if (method === "get" && path === "/tasks") {
    return response(
      config,
      200,
      tasks.filter((task) => task.case_id === config.params?.case_id),
    );
  }

  const complete_match = path.match(/^\/tasks\/([^/]+)\/complete$/);
  if (method === "put" && complete_match) {
    const task = completeTask(decodeURIComponent(complete_match[1]), parseBody(config.data));
    return task ? response(config, 200, task) : notFound(config);
  }

  return notFound(config);
}
