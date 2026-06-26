
function cycleTheme() {
  const themes = ['dark', 'beige', 'gruvbox'];
  const current = localStorage.getItem('insynbio-console-theme') || 'dark';
  let next = themes[(themes.indexOf(current) + 1) % themes.length];
  setTheme(next);
}

function setTheme(theme) {
  const html = document.documentElement;
  html.classList.remove('theme-beige', 'theme-gruvbox');
  if (theme !== 'dark') {
    html.classList.add('theme-' + theme);
  }
  localStorage.setItem('insynbio-console-theme', theme);
}
// Init theme
(function() {
  const saved = localStorage.getItem('insynbio-console-theme');
  if (saved) setTheme(saved);
})();

/** Deployment: `en`/insynbio = international UI; `zh`/therasik = Chinese-only chrome (e.g. sidebar hints). */
function getPublicLocale() {
  const m = document.querySelector('meta[name="insynbio-public-locale"]');
  const raw = m && m.content ? String(m.content).trim() : "";
  if (!raw || raw === "__INSYNBIO_PUBLIC_LOCALE__") return "en";
  const l = raw.toLowerCase();
  if (l === "zh" || l.startsWith("zh-")) return "zh";
  return "en";
}
function applyPublicLocaleChrome() {
  const hint = document.getElementById("sidebar-locale-hint");
  if (hint) hint.style.display = getPublicLocale() === "zh" ? "" : "none";
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", applyPublicLocaleChrome);
} else {
  applyPublicLocaleChrome();
}

/** Active async job (ImmuneBuilder / VH/VL background); POST /jobs/{id}/cancel + stop polling. */
window.__activeAsyncJobId = null;
window.__activeAsyncAbort = false;

function setAsyncJobCancelButtonsVisible(show) {
  ["vhvl-cancel-btn", "fv-cancel-btn", "vhh-cancel-btn", "vh2vhh-cancel-btn", "vhh-struct-cancel-btn", "rchk-vhvl-cancel-btn", "rchk-vhh-cancel-btn", "cmc-cancel-btn"].forEach((hid) => {
    const b = document.getElementById(hid);
    if (b) b.style.display = show ? "inline-flex" : "none";
  });
}
function _cmcSetCancelVisible(show) {
  const b = document.getElementById("cmc-cancel-btn");
  if (b) b.style.display = show ? "inline-flex" : "none";
}

async function cancelActiveAsyncJob() {
  const id = window.__activeAsyncJobId;
  window.__activeAsyncAbort = true;
  if (id) {
    try {
      await apiFetch(apiJoin(`jobs/${id}/cancel`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
    } catch (e) {}
  }
  setAsyncJobCancelButtonsVisible(false);
}

/** API base: meta `insynbio-api-base`, `window.__INSYNBIO_API_BASE__`, or saved local/tunnel endpoint. */
function apiJoin(path) {
  const raw = (path || "").replace(/^\/+/, "");
  const meta = document.querySelector("meta[name=\"insynbio-api-base\"]");
  let base = "";
  if (meta && meta.content && String(meta.content).trim()) {
    base = String(meta.content).trim().replace(/\/$/, "");
  } else if (typeof window.__INSYNBIO_API_BASE__ === "string" && window.__INSYNBIO_API_BASE__.trim()) {
    base = window.__INSYNBIO_API_BASE__.trim().replace(/\/$/, "");
  } else {
    const saved = _getUserApiEndpoint();
    if (saved) {
      base = saved;
    } else if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      // Default to current port for same-origin API
      base = location.origin;
    }
  }
  if (!base) return "/api/" + raw;
  return base.replace(/\/$/, "") + "/api/" + raw;
}

/** One line when POST /annotate returns 404 — context-specific, no wrong “set meta” advice. */
/** User-configurable API endpoint (ngrok / cloudflared tunnel). Saved to localStorage. */
const LS_API_ENDPOINT = "insynbio_api_endpoint";

function _getUserApiEndpoint() {
  try { return (localStorage.getItem(LS_API_ENDPOINT) || "").trim() || null; }
  catch (e) { return null; }
}

function _setUserApiEndpoint(url) {
  try { localStorage.setItem(LS_API_ENDPOINT, (url || "").trim()); }
  catch (e) {}
}

/**
 * apiFetch — drop-in fetch() wrapper that automatically adds
 * "ngrok-skip-browser-warning" header when the URL is a ngrok endpoint.
 * Without this header, ngrok free tier returns an HTML warning page
 * instead of JSON, causing "Unexpected token '<'" errors.
 */
async function apiFetch(url, opts = {}) {
  const isNgrok = /ngrok/i.test(url);
  if (isNgrok) {
    opts = {
      ...opts,
      headers: { "ngrok-skip-browser-warning": "true", ...(opts.headers || {}) }
    };
  }
  // Send same-origin cookies so reverse-proxy auth (if any) carries through
  if (!opts.credentials) opts.credentials = "same-origin";
  return fetch(url, opts);
}

async function apiFetchWithTimeout(url, opts = {}, timeoutMs = 5000) {
  if (opts.signal || typeof AbortController === "undefined") return apiFetch(url, opts);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await apiFetch(url, { ...opts, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch an /api/files/* artifact via apiFetch (carries credentials/cookies),
 * then either:
 *   - open it in a new tab via blob URL (HTML reports)
 *   - trigger a download via temporary <a download> (FASTA/PDB/ZIP/PDF)
 * This avoids letting a stale Nginx auth/redirect bounce the user to a login page
 * during a direct <a href> navigation.
 */
async function _downloadArtifact(url, label, wantsDownload) {
  try {
    const res = await apiFetch(url);
    if (!res.ok) {
      const status = res.status;
      let hint = "";
      if (status === 401 || status === 403) hint = " — Nginx session may have expired; refresh the page (Ctrl+Shift+R) and retry.";
      else if (status === 404) hint = " — file not found on server (job may have been cleaned up).";
      else if (status >= 500) hint = " — API process error; check uvicorn log.";
      alert(`Failed to download "${label}": ${status}${hint}`);
      return;
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    if (wantsDownload) {
      // Force download
      const filename = (url.split("?")[0].split("/").pop() || "report").replace(/[^A-Za-z0-9._-]/g, "_");
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else {
      // Open in new tab (HTML report)
      window.open(blobUrl, "_blank");
    }
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
  } catch (e) {
    alert(`Failed to download "${label}": ${e.message}`);
  }
}

function openApiSettingsModal() {
  const el = document.getElementById("api-settings-modal");
  if (el) {
    const inp = document.getElementById("api-settings-endpoint");
    if (inp) inp.value = _getUserApiEndpoint() || "";
    const msg = document.getElementById("api-settings-msg");
    if (msg) msg.textContent = "";
    el.style.display = "flex";
  }
}

function closeApiSettingsModal() {
  const el = document.getElementById("api-settings-modal");
  if (el) el.style.display = "none";
}


async function saveApiEndpoint() {
  const inp = document.getElementById("api-settings-endpoint");
  const msg = document.getElementById("api-settings-msg");
  const url = (inp ? inp.value.trim() : "").replace(/\/$/, "");
  if (url && !url.startsWith("http")) {
    if (msg) { msg.style.color = "var(--fail)"; msg.textContent = "URL must start with https://"; }
    return;
  }
  _setUserApiEndpoint(url);
  if (msg) { msg.style.color = "var(--muted)"; msg.textContent = url ? "Saved. Testing connection\u2026" : "Cleared."; }
  await loadHealth();
  updateTopbar();
  reflectApiButtonState();
  if (msg) {
    if (!url) { msg.textContent = "Cleared. Using default."; return; }
    if (state.apiVersion === "offline") {
      msg.style.color = "var(--fail)";
      msg.textContent = "Cannot reach endpoint. Verify the tunnel URL and that uvicorn is running.";
    } else {
      msg.style.color = "var(--pass)";
      msg.textContent = "Connected \u00b7 API " + state.apiVersion;
      const banner = document.getElementById("api-not-configured-banner");
      if (banner) { banner.remove(); document.body.style.paddingTop = ""; }
    }
  }
}

function api404Hint() {
  if (location.protocol === "file:") {
    return "Open http://127.0.0.1:8000/ (uvicorn). Do not use file://."; 
  }
  const port = location.port || "";
  if (["5173", "5174", "3000", "4173"].includes(port)) {
    return "API on :8000 — add meta insynbio-api-base if requests still fail.";
  }
  if (port === "8000") {
    return "Restart uvicorn from suite root; ensure api.main includes annotate router.";
  }
  return "Set meta insynbio-api-base to the API origin.";
}
const VALID_AA = /^[ACDEFGHIKLMNPQRSTVWY]+$/;
/** Legacy demo chip copy only; live balance uses OWNER_DEFAULT_CREDITS + localStorage. */
const DEMO_CREDITS = 120;
/** First visit / reset key missing: owner wallet seeds here (local browser). */
const OWNER_DEFAULT_CREDITS = 1000000;
const LS_CREDITS = "insynbio_credits_balance";
const LS_ACCOUNT = "insynbio_account";
const LS_LEDGER = "insynbio_usage_ledger";
const LS_GUEST_ID = "insynbio_guest_id";
const LEDGER_MAX = 500;

const REGISTRY = {
  modules: [
    {
      id: "regular-antibody-engineering",
      label: "Regular Antibody Engineering",
      subtitle: "mouse / rat / human",
      tier: "online",
      services: [
        "segmentation-vhvl",
        "fv-structural",
        "vhvl-humanization",
        "vhvl-recheck",
        "cdna-optimization-igg",
      ],
    },
    {
      id: "vhh-engineering",
      label: "VHH Engineering",
      subtitle: "humanization / conversion",
      tier: "online",
      services: [
        "vhh-segmentation",
        "vhh-structural",
        "vhh-humanization",
        "vhh-recheck",
        "vh-to-vhh-conversion",
        "cdna-optimization-vhh",
      ],
    },
    {
      id: "bispecific-engineering",
      label: "Bispecific Engineering",
      subtitle: "Format assembly",
      tier: "online",
      services: [
        "bispecific-assembler",
      ],
    },
    {
      id: "cmc",
      label: "CMC / Developability",
      subtitle: "Clinical Reference",
      tier: "online",
      services: [
        "igg-cmc-snapshot",
        "vhh-cmc-snapshot",
        "bispecific-analyzer",
        // "bispecific-vhh-cmc",  // hidden 2026-05-13: pending tandem-construct ESMFold integration; backend & service def preserved
      ],
    },
    {
      id: "offline-services",
      label: "Expert Offline Services",
      subtitle: "AF2 · HADDOCK · custom quote",
      tier: "offline",
      services: [
        "af2-multimer",
        "haddock-peptide",
        "virtual-affinity-maturation",
        "cdr-redesign",
        "cart-vaccine-projects",
      ],
    },
  ],
  services: {
    // ── Pet Antibody Engineering (internal — INSYNBIO_INTERNAL_PET_CONSOLE=1) ──
    "petization": {
      module: "pet-engineering",
      navGroup: "petization",
      label: "Caninization / Felinization",
      subtitle: "dog · cat VH/VL framework conversion",
      computeMode: "Internal",
      credits: 0,
      description: "Engineer therapeutic antibodies for dogs (caninization) or cats (felinization). " +
        "Routes VH/VL chains through graft+Vernier, surface reshaping, or deep-FR anchor strategy. " +
        "Requires INSYNBIO_INTERNAL_PET_CONSOLE=1 on the API server.",
      analysisVersion: "petization_cli_v1.2.0",
      underlyingStandard: "Petization Standard V1.0.2",
      reportVersion: "V1.0.2",
      runner: "petization",
      demos: ["tanezumab-dog", "tanezumab-cat"],
    },
    // ── Regular Antibody Engineering ─────────────────────────────────────
    "vhvl-humanization": {
      module: "regular-antibody-engineering",
      navGroup: "humanization",
      label: "VH/VL Humanization",
      subtitle: "mouse · rat",
      computeMode: "Lite",
      credits: 15000,
      description: "Humanize donor VH/VL pairs (mouse or rat) via the AbEngineCore VH/VL workflow.",
      analysisVersion: "v5.5.1",
      underlyingStandard: "VH/VL Humanization Standard V5.5.1",
      reportVersion: "v1.5",
      /** Backend `service_report_versions` key (api/report_versioning._SERVICE_CATALOG). */
      reportCatalogKey: "vhvl_humanization",
      runner: "vhvl",
      demos: ["mouse-cd20", "rat-campath"],
    },
    "vhvl-recheck": {
      module: "regular-antibody-engineering",
      navGroup: "humanization",
      label: "VH/VL Recheck",
      subtitle: "customer sequence virtual QA",
      computeMode: "Lite",
      credits: 1500,
      description: "Virtual recheck for customer-submitted humanized VH/VL against donor VH/VL. Includes input QC and cleaning audit, optional structure conservation, mini-CMC, HPR, and paired Fv naturalness.",
      analysisVersion: "recheck_v1",
      underlyingStandard: "VH/VL Humanization Standard V5.5.1",
      reportVersion: "v1.0",
      reportCatalogKey: "recheck_vhvl",
      runner: "recheck-vhvl",
      demos: ["mouse-cd20"],
    },
    "segmentation-vhvl": {
      module: "regular-antibody-engineering",
      navGroup: "segmentation",
      label: "Segmentation & Germline",
      subtitle: "CDR / FR · IMGT · Kabat · Chothia",
      computeMode: "Lite",
      credits: 200,
      description: "VH/VL FR–CDR split via server numbering (IMGT/Kabat/Chothia); optional germline species library. IMGT-only heuristic when server is off.",
      analysisVersion: "AbEngineCore Numbering v1.5",
      underlyingStandard: "VH/VL Humanization Standard V5.5.1",
      reportVersion: "1.0",
      runner: "segmentation-vhvl",
      demos: ["mouse-cd20", "rat-campath", "human-toripalimab"],
    },
    "fv-structural": {
      module: "regular-antibody-engineering",
      navGroup: "structure",
      label: "Structure (Fv)",
      subtitle: "ImmuneBuilder ABodyBuilder2 · demo / paste / FASTA",
      computeMode: "Lite",
      credits: 800,
      description: "Predict Fv coordinates from VH+VL sequences using ImmuneBuilder ABodyBuilder2. Load a demo, paste sequences, or upload / paste multi-pair FASTA; results return as downloadable PDBs (async job).",
      analysisVersion: "ImmuneBuilder ABodyBuilder2",
      underlyingStandard: "VH/VL Humanization Standard (structure QC phase)",
      reportVersion: "1.0",
      runner: "structural-vhvl",
      demos: ["mouse-cd20", "rat-campath", "human-toripalimab"],
    },
    "cdna-optimization-igg": {
      module: "regular-antibody-engineering",
      navGroup: "workflow",
      label: "cDNA Optimization",
      subtitle: "SP · Fc · CL · then codons",
      computeMode: "Lite",
      credits: 300,
      description: "Assemble full human IgG heavy/light chains (optional signal peptide + VH/CH1 + hinge/Fc + VL/CL), then codon-optimize expression cDNA for HEK293 / CHO / E. coli.",
      analysisVersion: "AbEngineCore cDNA v1.0",
      underlyingStandard: "Expression Codon Optimization Standard v1.0",
      reportVersion: "1.0",
      runner: "cdna-optimization",
      chainType: "igg",
      demos: ["mouse-cd20", "human-toripalimab"],
    },
    // ── VHH Engineering ──────────────────────────────────────────────────
    "vhh-structural": {
      module: "vhh-engineering",
      navGroup: "structure",
      label: "Structure (VHH)",
      subtitle: "NanoBodyBuilder2 · pLDDT · PDB download",
      computeMode: "Lite",
      credits: 600,
      description: "Predict 3D structure of a VHH nanobody using NanoBodyBuilder2. Returns pLDDT confidence, downloadable PDB, and CDR loop quality. Use after humanization or conversion to verify CDR fold.",
      analysisVersion: "NanoBodyBuilder2 (ImmuneBuilder)",
      underlyingStandard: "VHH Humanization Design Standard V3.2 (Structure QC phase)",
      reportVersion: "1.0",
      runner: "vhh-structural",
      demos: ["alpaca-vhh", "humanized-vhh-fc", "humanized-vhh-hsa", "humanized-hsa-vhh"],
    },
    "vhh-segmentation": {
      module: "vhh-engineering",
      label: "VHH Segmentation & Germline",
      subtitle: "CDR / FR / hallmark check",
      computeMode: "Lite",
      credits: 200,
      description: "Segment a VHH/nanobody with the same ANARCI-class stack as VH/VL: IMGT / Kabat / Chothia, per-residue numbering table, optional closest IGHV vs species library, IMGT hallmark sites.",
      analysisVersion: "AbEngineCore Numbering v1.5",
      underlyingStandard: "VHH Humanization Design Standard v2.0",
      reportVersion: "1.0",
      runner: "vhh-segmentation",
      demos: ["alpaca-vhh"],
    },
    "vhh-humanization": {
      module: "vhh-engineering",
      label: "VHH Humanization",
      subtitle: "camelid · V5.0 structure-guided",
      computeMode: "Lite",
      credits: 30000,
      description: "Humanize camelid VHH nanobody sequence using V5.0 clinical framework library. Outputs a single humanized lead with FR/CDR comparison, mini-CMC, naturalness scoring, and structure QC.",
      analysisVersion: "v5.0",
      underlyingStandard: "VHH Humanization Design Standard V5.0",
      reportVersion: "V5.0",
      reportCatalogKey: "vhh_humanization",
      runner: "vhh-humanization",
      demos: ["alpaca-vhh"],
    },
    "vhh-recheck": {
      module: "vhh-engineering",
      label: "VHH Recheck",
      subtitle: "customer sequence virtual QA",
      computeMode: "Lite",
      credits: 1500,
      description: "Virtual recheck for customer-submitted humanized VHH against donor VHH. Includes input QC and cleaning audit, optional structure conservation, mini-CMC, HPR, and single-domain naturalness.",
      analysisVersion: "recheck_v1",
      underlyingStandard: "VHH Humanization Design Standard V4.0",
      reportVersion: "v1.0",
      reportCatalogKey: "recheck_vhh",
      runner: "recheck-vhh",
      demos: ["alpaca-vhh"],
    },
    "vh-to-vhh-conversion": {
      module: "vhh-engineering",
      label: "VH to VHH Conversion",
      subtitle: "Proprietary Reshaping V1.8.17",
      computeMode: "Server full pipeline (Async)",
      credits: 50000,
      description: "Full VH→VHH conversion: Stage-1 feasibility (AbNatiV Δ Hard Gate) → Stage-2 Hallmark+Stealth engineering → Advanced Structural Modeling → CDR Conformation Analysis → mini-CMC + Clinical Benchmark QA → Professional Report.",
      analysisVersion: "v1.8.17",
      underlyingStandard: "VH to VHH Conversion Standard V1.8.17",
      reportVersion: "V1.8.17",
      reportCatalogKey: "vh_to_vhh",
      runner: "vh-to-vhh",
      demos: ["tislelizumab-vh", "teplizumab-vh"],
    },
    "bispecific-assembler": {
      module: "bispecific-engineering",
      navGroup: "workflow",
      label: "Bispecific Assembler",
      subtitle: "Format & linker assembly",
      computeMode: "Lite",
      credits: 5000,
      description: "Assemble two target binders (VH/VL or VHH) into a single bispecific antibody format (e.g. CrossMab, Tandem scFv, BiTE). Provides FASTA outputs with appropriate linkers and constant region scaffolds.",
      analysisVersion: "v1.0",
      underlyingStandard: "Bispecific Design Framework V1.0",
      reportVersion: "1.0",
      runner: "bispecific-assembler",
      demos: ["teclistamab-bsab", "mosunetuzumab-bsab"]
    },
    "cdna-optimization-vhh": {
      module: "vhh-engineering",
      label: "cDNA Optimization",
      subtitle: "HEK293 / yeast / bacterial",
      computeMode: "Lite",
      credits: 300,
      description: "Generate a host-optimized cDNA for VHH/nanobody with codon usage adapted for HEK293, yeast, or bacterial expression.",
      analysisVersion: "AbEngineCore cDNA v1.0",
      underlyingStandard: "Expression Codon Optimization Standard v1.0",
      reportVersion: "1.0",
      runner: "cdna-optimization",
      chainType: "vhh",
      demos: ["alpaca-vhh"],
    },
    // ── CMC ──────────────────────────────────────────────────────────────
    "igg-cmc-snapshot": {
      module: "cmc",
      label: "IgG CMC Snapshot",
      subtitle: "Clinical reference benchmarked",
      computeMode: "Lite (Sync)",
      credits: 3500,
      description: "Rapid CMC developability screen for conventional IgG/VH+VL. Clinical score, percentile rank, and summary status benchmarked against curated clinical reference cohorts.",
      analysisVersion: "CMC Developability Standard v1.4.0",
      underlyingStandard: "CMC Developability Standard v1.4.0",
      reportVersion: "1.0",
      reportCatalogKey: "cmc_igg",
      runner: "cmc-igg",
      cmcView: "snapshot",
      refDb: "Clinical reference",
      demos: ["toripalimab-igg", "abiprubart-engineered", "briakinumab-phage"],
    },
    "vhh-cmc-snapshot": {
      module: "cmc",
      label: "VHH CMC Snapshot",
      subtitle: "VHH clinical panel benchmarked",
      computeMode: "Lite (Sync)",
      credits: 3500,
      description: "Rapid CMC developability screen for VHH / single-domain antibody (sdAb / HCAb-style) sequences. Demo coverage includes a 7D12 humanized VHH example (anti-EGFR, PDB 4KRL family) and Porustobart (HBM4003) — a Harbour HCAb-platform anti-CTLA-4 single-domain antibody. Gate Score, percentile rank, and liability summary are benchmarked against source-matched VHH/HCAb clinical reference panels.",
      analysisVersion: "CMC Developability Standard v1.4.0",
      underlyingStandard: "CMC Developability Standard v1.4.0",
      reportVersion: "1.0",
      reportCatalogKey: "cmc_vhh",
      runner: "cmc-vhh",
      refDb: "VHH clinical",
      demos: ["humanized-vhh-eval", "nanobody-origin-scab"],
    },
    "bispecific-analyzer": {
      module: "cmc",
      navGroup: "workflow",
      label: "Bispecific Analyzer",
      subtitle: "Pairing QA & CMC",
      computeMode: "Server full pipeline (Async)",
      credits: 15000,
      description: "In-depth QA and CMC evaluation for bispecific formats. For IgG-like bispecifics (e.g., CrossMab), computes Pairing Selectivity Index (PSI) using Fv pairing rules, assembly angles, and electrostatic asymmetry to predict chain mispairing risk.",
      analysisVersion: "v1.0",
      underlyingStandard: "Bispecific Structure & Services Mapping V1.0",
      reportVersion: "1.0",
      runner: "bispecific-analyzer",
      demos: ["teclistamab-bsab", "mosunetuzumab-bsab"]
    },
    "bispecific-vhh-cmc": {
      module: "cmc",
      label: "Bispecific VHH CMC",
      subtitle: "tandem VHH + linker",
      computeMode: "Lite (Sync)",
      credits: 3500,
      description: "Per-arm VHH developability (vs VHH clinical panel) plus fusion pI, arm pI delta, ER expression score, and SmartLink-style linker recommendation for VHH-linker-VHH constructs.",
      analysisVersion: "Bispecific VHH CMC v1.0",
      underlyingStandard: "Bispecific VHH CMC Standard v1.0",
      reportVersion: "1.0",
      reportCatalogKey: "cmc_bispecific",
      runner: "cmc-bispecific",
      bispecificCmc: true,
      demos: ["bispecific-vhh-demo"],
    },
    // ── Offline Services ─────────────────────────────────────────────────
    "af2-multimer": {
      module: "offline-services",
      label: "AF2 Multimer & Complex",
      subtitle: "antigen-antibody structure",
      computeMode: "Offline",
      credits: 0,
      description: "Offline AlphaFold2 Multimer for antibody–antigen complexes. Paste antigen (ECD) plus either VH+VL or VHH, or upload ColabFold-style FASTA. No built-in demo — client sequences only. After humanization, use the option to carry humanized VH/VL or VHH forward with your antigen for modeling.",
      analysisVersion: "AF2 Multimer v2.3 (offline)",
      underlyingStandard: "Structure Prediction Standard v1.0",
      reportVersion: "1.0",
      runner: "offline-request",
      scope: ["Antigen ECD + antibody VH/VL or VHH (required inputs)", "ColabFold-style FASTA assembly / upload", "Post-humanization → complex with antigen (offline handoff)", "Optional: epitope/paratope mapping", "Expert delivery PDF"],
    },
    "haddock-peptide": {
      module: "offline-services",
      label: "HADDOCK Short Peptide",
      subtitle: "docking + epitope mapping",
      computeMode: "Offline",
      credits: 0,
      description: "Antibody / VHH docking with short peptide antigens using HADDOCK3. Includes epitope/paratope mapping and interface residue analysis.",
      analysisVersion: "HADDOCK3 v3.0 (offline)",
      underlyingStandard: "Structure Prediction Standard v1.0",
      reportVersion: "1.0",
      runner: "offline-request",
      scope: ["HADDOCK3 docking run", "Paratope & epitope mapping", "Interface energy analysis", "Expert delivery PDF"],
    },
    "virtual-affinity-maturation": {
      module: "offline-services",
      label: "Virtual Affinity Maturation",
      subtitle: "ΔΔG · 6-tool consensus",
      computeMode: "Offline",
      credits: 0,
      description: "6-tool ΔΔG consensus pipeline (EvoEF2, PRODIGY, MM/GBSA, ThermoMPNN, AntiFold, ESM-IF1) with mutation scanning and ranked candidate delivery.",
      analysisVersion: "Virtual Affinity Maturation Standard v1.2 (offline)",
      underlyingStandard: "Virtual Affinity Maturation Standard v1.2",
      reportVersion: "1.0",
      runner: "offline-request",
      scope: ["Single-point mutation scan (full CDR set)", "ΔΔG consensus across 6 tools", "Ranked mutation candidates", "Expert delivery PDF + FASTA"],
    },
    "cdr-redesign": {
      module: "offline-services",
      label: "CDR Redesign",
      subtitle: "ProteinMPNN · AbLang · filter",
      computeMode: "Offline",
      credits: 0,
      description: "Generative CDR redesign using ProteinMPNN + AbLang scoring, structural filtering, and clinical CMC gate. Delivers ranked redesigned sequences ready for experimental validation.",
      analysisVersion: "De Novo CDR Design Standard v1.0 (offline)",
      underlyingStandard: "De Novo CDR Design Standard v1.0",
      reportVersion: "1.0",
      runner: "offline-request",
      scope: ["ProteinMPNN CDR generation (>500 sequences)", "AbLang naturalness scoring", "ΔΔG structural filter", "Ranked output with CMC gate"],
    },
    "cart-vaccine-projects": {
      module: "offline-services",
      label: "CAR-T / Vaccine Projects",
      subtitle: "expert consulting",
      computeMode: "Offline",
      credits: 0,
      description: "Expert consulting for CAR-T scFv design and mRNA vaccine antigen engineering. Projects are scoped individually with a custom timeline and deliverable agreement.",
      analysisVersion: "ACTES / Vaccine Design Standard v1.0 (offline)",
      underlyingStandard: "ACTES v1.0 / Vaccine Design Standard v1.0",
      reportVersion: "1.0",
      runner: "offline-request",
      scope: ["CAR-T scFv selection and engineering", "mRNA antigen design and optimization", "Expert NDA-covered project delivery"],
    },
  },
};

const DEMOS = {
  "mouse-cd20": {
    label: "Mouse anti-CD20 (rituximab-type pair)",
    summary: "Murine VH/VL benchmark (anti-CD20 IgG-style pair; public rituximab parental reference class).",
    type: "vhvl",
    vh: "QVQLQQSGPELVKPGASLKLSCTASGFNIKDTYIHWVKQRPEQGLEWIGRIYPTNGYTRYDPKFQDKATITADTSSNTAYLQVSRLTSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS",
    vl: "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK",
    sourceSpecies: "mouse",
    humanizedDemoKey: "abiprubart-engineered",
  },
  "rat-campath": {
    label: "Rat Campath-1G (alemtuzumab-type pair)",
    summary: "Rat VH/VL donor pair in the Campath / alemtuzumab lineage — rat-aware humanization routing demo.",
    type: "vhvl",
    vh: "EVKLLESGGGLVQPGGSMRLSCAGSGFTFTDFYMNWIRQPAGKAPEWLGFIRDKAKGYTTEYNPSVKGRFTISRDNTQNMLYLQMNTLRAEDTATYYCAREGHTAAPFDYWGQGVMVTVSS",
    vl: "DIKMTQSPSFLSASVGDRVTLNCKASQNIDKYLNWYQQKLGESPKLLIYNTNNLQTGIPSRFSGSGSGTDFTLTISSLQPEDVATYFCLQHISRPRTFGTGTKLELK",
    sourceSpecies: "rat",
  },
  "human-toripalimab": {
    label: "Human IgG1 Fv (toripalimab / JS001)",
    summary: "Fully human therapeutic anti-PD-1 VH/VL (toripalimab) — published Fv reference for segmentation, cDNA, and CMC-style demos (not a murine→human donor).",
    type: "vhvl",
    vh: "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS",
    vl: "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIK",
    sourceSpecies: "human",
  },
  "toripalimab-igg": {
    label: "Toripalimab (Fully human / regular IgG)",
    summary: "Fully human anti-PD-1 IgG Fv (toripalimab) — clinical reference benchmark demo for IgG CMC.",
    type: "igg",
    antibodyType: "humanized_transgenic",
    vh: "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS",
    vl: "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIK",
  },
  "briakinumab-phage": {
    label: "Briakinumab / ABT-874 (Phage display)",
    summary: "Fully human anti-IL-12/23 IgG Fv (phage display origin) — CMC benchmark demo for fully human phage-selected antibodies.",
    type: "igg",
    antibodyType: "phage_display",
    vh: "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKTHGSHDNWGQGTMVTVSS",
    vl: "QSVLTQPPSVSGAPGQRVTISCSGSRSNIGSNTVKWYQQLPGTAPKLLIYYNDQRPSGVPDRFSGSKSGTSASLAITGLQAEDEADYYCQSYDRYTHPALLFGTGTKVTVL",
  },
  "abiprubart-engineered": {
    label: "Abiprubart (Humanized / engineered)",
    summary: "Humanized engineered anti-CD40 IgG Fv (abiprubart) — CMC benchmark demo for humanized / gene-engineered antibodies.",
    type: "igg",
    antibodyType: "humanized",
    vh: "QVQLVQSGAEVKKPGASVKVSCKASGYTFTNYWMHWVRQAPGQRLEWIGYINPSNDYTKYNQKFKDRATLTADKSANTAYMELSSLRSEDTAVYYCARQGFPYWGQGTLVTVSS",
    vl: "EIVLTQSPATLSLSPGERATLSCSASSSVSYMHWYQQKPGQAPRRWIYDTSKLASGVPARFSGSGSGTDYTLTISSLEPEDFAVYYCHQLSSDPFTFGGGTKVEIK",
  },
  "alpaca-vhh": {
    label: "7D12 anti-EGFR VHH (PDB 4KRL)",
    summary:
      "Wild-type camelid nanobody 7D12 (PDB 4KRL, chain B) — aa sequence as used in projects/EGFR_7D12_VHH; demo for segmentation, humanization, CMC, and recheck.",
    type: "vhh",
    seq: "QVKLEESGGGSVQTGGSLRLTCAASGRTSRSYGMGWFRQAPGKEREFVSGISWRGDSTGYADSVKGRFTISRDNAKNTVDLQMNSLKPEDTAIYYCAAAAGSAWYGTLYEYDYWGQGTQVTVSS",
    sourceSpecies: "alpaca",
    humanizedDemoKey: "humanized-vhh-fc",
  },
  "envafolimab-engvh": {
    label: "Envafolimab / KN035 VHH-Fc reference",
    summary: "Envafolimab (KN035) — approved anti-PD-L1 single-domain antibody Fc fusion (VHH-Fc / human-camelid chimeric sdAb). Used only as an sdAb clinical context reference, not as an engineered-VH example.",
    type: "vhh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGFTFSDNYMSWVRQAPGKGLEWVSYISSSGSTIYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARDRGSNYGDSWGQGTLVTVSS",
    sourceSpecies: "engineered_vh",
    sdab_origin: "camelid_vhh",
  },
  "humanized-vhh-fc": {
    label: "Humanized VHH-Fc preset",
    summary:
      "Humanized 7D12-class VHH (framework-adapted reference from EGFR_7D12_VHH compare script) + VHH-Fc cassette preset.",
    type: "vhh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    sourceSpecies: "human",
    cdnaPreset: {
      assembly: true,
      sp: "tpa_short",
      fusion: "igg1_fch",
      orientation: "vhh_fusion",
      linker: "gs15",
      cleavage: "none",
      tag: "none",
    },
  },
  "humanized-vhh-eval": {
    label: "7D12 (humanized) — camelid VHH, anti-EGFR",
    summary:
      "7D12 humanized VHH (anti-EGFR; PDB 4KRL parent family). Framework-adapted humanized camelid VHH — retains canonical VHH hallmark residues at Kabat 37/44/45/47 while using human FR replacements elsewhere.",
    type: "vhh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    sourceSpecies: "humanized_vhh",
    sdab_origin: "camelid_vhh",
  },
  "nanobody-origin-scab": {
    label: "Porustobart (HBM4003) — Harbour HCAb platform, anti-CTLA-4",
    summary:
      "Porustobart (HBM4003) — transgenic-mouse heavy-chain-only antibody (HCAb) from the Harbour BioMed HCAb platform; anti-CTLA-4. VH-canonical FR2 (W47, V37, no camelid hallmark) with a compact CDR-H3 (~11 aa) enabling monomeric expression. Evaluated as a single-domain HCAb candidate against the transgenic sdAb / HCAb reference context — there is room for improvement by selectively introducing VHH hallmark residues if higher solubility / camelid character is desired.",
    type: "vhh",
    seq: "EVQLVESGGGLIQPGGSLRLSCAVSGFTVSKNYMSWVRQAPGKGLEWVSVVYSGGSKTYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARAVPHSPSSFDIWGQGTMVTVSS",
    sourceSpecies: "transgenic_mouse_sdab",
    sdab_origin: "transgenic_sdab",
  },
  "humanized-vhh-hsa": {
    label: "Humanized VHH-ALB8 preset",
    summary: "Humanized 7D12-class VHH + ALB8 fusion preset (same aa as humanized-vhh-fc).",
    type: "vhh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    sourceSpecies: "human",
    cdnaPreset: {
      assembly: true,
      sp: "tpa_short",
      fusion: "hsa",
      orientation: "vhh_fusion",
      linker: "gs20",
      cleavage: "none",
      tag: "his6",
    },
  },
  "humanized-hsa-vhh": {
    label: "Humanized ALB8-VHH preset",
    summary: "Humanized 7D12-class VHH in ALB8–VHH orientation (same aa as humanized-vhh-fc).",
    type: "vhh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    sourceSpecies: "human",
    cdnaPreset: {
      assembly: true,
      sp: "tpa_short",
      fusion: "hsa",
      orientation: "fusion_vhh",
      linker: "gs20",
      cleavage: "none",
      tag: "his6",
    },
  },
  "mumab4d5-vh": {
    label: "mumab4d5 VH (HER2 binder)",
    summary: "Validated mouse HER2 binder VH — VH→VHH dual-path benchmark.",
    type: "vh",
    seq: "EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQGLEWMGIINPSGGSTSYAQKFQGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARDQGSIRGFDYWGQGTLVTVSS",
  },
  "toripalimab-vh": {
    label: "Toripalimab VH (PD-1, JS001)",
    summary: "Humanized anti-PD-1 VH (IGHV3-66, PDB 6JBT) — pI 4.68 BLOCKER case; illustrates CDR-H3 length / charge gate in VH→VHH.",
    type: "vh",
    seq: "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS",
  },
  "tislelizumab-vh": {
    label: "Tislelizumab VH (PD-1, Tevimbra)",
    summary: "Humanized anti-PD-1 VH (IGHV3-66, PDB 7CGW) — Priority 1 VH→VHH benchmark; CDR-H3 10 aa, CMC-favorable. Externally validated by Mirzaei et al. 2025.",
    type: "vh",
    seq: "QVQLQESGPGLVKPSETLSLTCTVSGFSLTSYGVHWIRQPPGKGLEWIGVIYADGSTNYNPSLKSRVTISKDTSKNQVSLKLSSVTAADTAVYYCARAYGNYWYIDVWGQGTTVTVSS",
  },
  "teplizumab-vh": {
    label: "Teplizumab VH (CD3ε, Tzield)",
    summary: "Humanized anti-CD3ε VH (IGHV3-23, FDA-approved T1D) — CDR3 10 aa with unpaired Cys (Cys-gate demo); pI 8.93; 4-mutation conversion: Cys-gate + pI-correction + Hallmark reshaping. InSynBio CD3 VH→VHH Batch 20260515.",
    type: "vh",
    seq: "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS",
  },
  "pembrolizumab-vh": {
    label: "Pembrolizumab VH (PD-1, Keytruda)",
    summary: "Humanized anti-PD-1 VH (IGHV3-23, PDB 5B8C) — CDR-H2 long (17 aa); GRAVY borderline case. Scaffold-graft strategy recommended.",
    type: "vh",
    seq: "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS",
  },
  "camrelizumab-vh": {
    label: "Camrelizumab VH (PD-1, Hengrui)",
    summary: "Humanized anti-PD-1 VH (IGHV1-46, PDB 7CU5 scFv) — VH HCDR1/HCDR2 contact PD-1 N58 glycan; glycan contact is VH-mediated and retained in VHH format.",
    type: "vh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYMMSWVRQAPGKGLEWVASISSSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARVEGYGNSNGMDVWGQGTMVTVSS",
  },
  "nivolumab-vh": {
    label: "Nivolumab VH (PD-1, Opdivo)",
    summary: "Humanized anti-PD-1 VH (IGHV3-33, PDB 5WT9) — CDR-H3 only 4 aa (TNDD); structural challenge case illustrating CDR-H3 length gate.",
    type: "vh",
    seq: "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS",
  },
  "phage-maturation-vh-ref": {
    label: "Synthetic phage library clone (Acidic FR demo)",
    summary: "A synthetic IGHV3-23 library clone enriched via acidic elution, displaying a net negative charge bias in the framework. This triggers the Path C1 charge compensation advisory.",
    type: "vh",
    seq: "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGEGLEWVSAISGSGGSTYYADSVKGRFTISRDNSENTLYLQMNSLRAEDTAVYYCAKDGDYWGQGTLVTVSS",
  },
  "transgenic-hcab-vh-ref": {
    label: "Transgenic HCAb VH (SHM audit demo)",
    summary: "An IGHV3-23 derived VH from a transgenic mouse (HCAb-like), showcasing somatic hypermutation (SHM) in the framework. Triggers the Path C2b SHM audit to classify mutations as stabilizing or risky.",
    type: "vh",
    seq: "EVQLVQSGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKWGQGTLVTVSS",
  },
  "bispecific-vhh-demo": {
    label: "Dual VHH (demo arms)",
    summary:
      "PDB 4KRL wild-type 7D12 (arm1) vs humanized 7D12-class reference (arm2) — replace with your targets as needed.",
    type: "bispecific",
    arm1: "QVKLEESGGGSVQTGGSLRLTCAASGRTSRSYGMGWFRQAPGKEREFVSGISWRGDSTGYADSVKGRFTISRDNAKNTVDLQMNSLKPEDTAIYYCAAAAGSAWYGTLYEYDYWGQGTQVTVSS",
    arm2: "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    arm1Target: "Target_A",
    arm2Target: "Target_B",
    linker: "(G4S)3",
  },
  "teclistamab-bsab": {
    label: "Teclistamab (BCMAxCD3, DuetMab)",
    summary: "Teclistamab (Janssen) — BCMA x CD3 bispecific using DuetMab format (IgG4). Contains engineered CH1/CL mutations to facilitate correct chain pairing.",
    type: "bispecific_vhvl",
    vh_a: "QVQLVQSGAEVKKPGSSVKVSCKASGGTFSSYAISWVRQAPGQGLEWMGGIIPIFGTANYAQKFQGRVTITADESTSTAYMELSSLRSEDTAVYYCARAPNYLFHSVIGAFDIWGQGTMVTVSS",
    vl_a: "DIQMTQSPSSLSASVGDRVTITCRASQGISSWLAWYQQKPEKAPKSLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQYNSYPYTFGQGTKLEIK",
    vh_b: "QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKVKDRVTITTDTSASTAYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS",
    vl_b: "DIQMTQSPSSLSASVGDRVTITCRASQDIRNYLNWYQQKPGKAPKLLIYYTSKLHSGVPSRFSGSGSGTDYTLTISSLQPEDFATYYCQQGNTLPWTFGQGTKVEIK"
  },
  "mosunetuzumab-bsab": {
    label: "Mosunetuzumab (CD20xCD3, CrossMab)",
    summary: "Mosunetuzumab (Roche) — CD20 x CD3 bispecific using CrossMab format (IgG1 KiH). Relies on CH1-CL domain exchange on one arm to prevent light chain mispairing.",
    type: "bispecific_vhvl",
    vh_a: "EVQLVESGGGLVQPGGSLRLSCAASGYTFTSYNMHWVRQAPGKGLEWIGAIYPGNGDTSYNQKFKGRATISVDKSKNTLYLQMNSLRAEDTAVYYCARSNYYGSSYWFFDVWGQGTLVTVSS",
    vl_a: "DIVMTQTPLSLPVTPGEPASISCRSSKSLLHSNGITYLYWYLQKPGQSPQLLIYQMSNLVSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCAQNLELPYTFGGGTKVEIK",
    vh_b: "EVQLVESGGGLVQPGGSLKLSCAASGFTFNKYAMNWVRQAPGKGLEWVARIRSKYNNYATYYADSVKDRFTISRDDSKNTAYLQMNNLKTEDTAVYYCVRHGNFGNSYISYWAYWGQGTLVTVSS",
    vl_b: "QTVVTQEPSLTVSPGGTVTLTCGSSTGAVTSGNYPNWVQQKPGQAPRGLIGGTKFLAPGTPARFSGSLLGGKAALTLSGVQPEDEAEYYCVLWYSNRWVFGGGTKLTVL"
  },
};

/** Sidebar groups for Regular Antibody Engineering (workflow order). */
const RAE_SERVICE_GROUPS = [
  { id: "segmentation", label: "1 · Segmentation" },
  { id: "structure", label: "2 · Structure" },
  { id: "humanization", label: "3 · Humanization" },
  { id: "workflow", label: "Workflow & reports" },
];

const state = {
  module: "regular-antibody-engineering",
  service: "segmentation-vhvl",
  apiVersion: "—",
  gitSha: null,
  apiBuildId: null,
  apiEnvironment: null,
  apiAnalysisVersion: null,
  apiProtocolVersion: null,
  apiReportFormatVersion: null,
  /** Per-service content report versions from GET /health (keys: vhvl_humanization, …). */
  serviceReportVersions: null,
  credits: OWNER_DEFAULT_CREDITS,
  account: { role: "owner", label: "Owner" },
  /** True after successful GET /auth/me (server wallet). */
  serverMode: false,
  serverUsername: null,
  serverRole: null,
  /** Server-side unlimited credits (owner); no real deduction. */
  serverUnlimited: false,
  currentArtifactUrl: null,
  /** When navigating from legacy mouse/rat humanization service ids, pre-select species. */
  pendingVhvlSpecies: null,
};

const UI_BUILD_VERSION = "console-v676-vhh-r-fix-20260515";

function enUsLocalNow() {
  try {
    return new Date().toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch (e) {
    return new Date().toISOString();
  }
}

function getGuestId() {
  try {
    let id = localStorage.getItem(LS_GUEST_ID);
    if (!id) {
      id = `guest-${Math.random().toString(36).slice(2, 8)}-${Date.now().toString(36).slice(-4)}`;
      localStorage.setItem(LS_GUEST_ID, id);
    }
    return id;
  } catch (e) {
    return "guest-local";
  }
}

function currentBillingIdentity() {
  if (state.serverMode && state.serverUsername) {
    return { id: state.serverUsername, type: state.serverRole || "trial", server: true };
  }
  try {
    const gateUser = (sessionStorage.getItem("insynbio_gate_auth") || "").trim();
    const gateRole = (sessionStorage.getItem("insynbio_gate_role") || "user").trim();
    if (gateUser) return { id: gateUser, type: `gate-${gateRole || "user"}`, server: false, gate: true };
  } catch (e) {}
  return { id: getGuestId(), type: "guest", server: false };
}

function gateAuthHeaders() {
  const ident = currentBillingIdentity();
  if (!ident.gate) return null;
  const role = String(ident.type || "gate-user").replace(/^gate-/, "") || "user";
  return {
    "X-InSynBio-Gate-User": ident.id,
    "X-InSynBio-Gate-Role": role,
  };
}

function walletStorageKey() {
  const ident = currentBillingIdentity();
  if (ident.server) return LS_CREDITS;
  if (ident.gate) return `${LS_CREDITS}_${ident.id}`;
  return LS_CREDITS;
}

/** Server Bearer wallet shows ∞ balance when unlimited flag is set, or forced for role `admin`. */
function serverWalletShowsInfinityBalance() {
  if (!state.serverMode) return false;
  const r = String(state.serverRole || "").toLowerCase();
  if (r === "admin") return true;
  return !!state.serverUnlimited;
}

function creditsInfinityParenLabel() {
  const r = String(state.serverRole || "").toLowerCase();
  if (r === "admin") return "admin";
  if (r === "owner") return "owner";
  return "unlimited";
}

function currentRunLocation() {
  const host = location.host || "local";
  const api = _getUserApiEndpoint ? (_getUserApiEndpoint() || location.origin || "default") : (location.origin || "default");
  return `${host} -> ${api}`;
}

function ensureAccountRecord() {
  try {
    let acc = JSON.parse(localStorage.getItem(LS_ACCOUNT) || "{}");
    if (!acc || typeof acc !== "object" || !acc.role) {
      acc = { role: "owner", label: "Owner", createdAt: new Date().toISOString() };
      localStorage.setItem(LS_ACCOUNT, JSON.stringify(acc));
    }
    return acc;
  } catch (e) {
    return { role: "owner", label: "Owner" };
  }
}

function loadWallet() {
  const account = ensureAccountRecord();
  let balance = OWNER_DEFAULT_CREDITS;
  try {
    const key = walletStorageKey();
    const raw = localStorage.getItem(key);
    if (raw != null && raw !== "") {
      const n = parseInt(raw, 10);
      if (!Number.isNaN(n)) balance = Math.max(0, n);
    } else {
      localStorage.setItem(key, String(OWNER_DEFAULT_CREDITS));
    }
  } catch (e) {
    /* private mode */
  }
  return { balance, account };
}

function syncWalletToState() {
  if (state.serverMode && sessionStorage.getItem("insynbio_access_token")) {
    return;
  }
  if (currentBillingIdentity().gate) {
    return;
  }
  const w = loadWallet();
  state.credits = w.balance;
  state.account = w.account;
}

async function refreshGateWallet() {
  const headers = gateAuthHeaders();
  if (!headers) return false;
  try {
    const r = await apiFetch(apiJoin("auth/gate/me"), { headers });
    if (!r.ok) throw new Error("gate/me");
    const d = await r.json();
    state.serverMode = false;
    state.serverUsername = null;
    state.serverRole = null;
    state.serverUnlimited = false;
    state.credits = Number(d.credits) || 0;
    state.account = { role: d.role || "gate", label: d.username || currentBillingIdentity().id };
    try {
      localStorage.setItem(walletStorageKey(), String(state.credits));
    } catch (e) {}
    await refreshGateLedger(d.credits_unlimited ? "∞" : state.credits);
    updateTopbar();
    return true;
  } catch (e) {
    const w = loadWallet();
    state.credits = w.balance;
    state.account = w.account;
    updateTopbar();
    return false;
  }
}

async function refreshGateLedger(currentBalance) {
  const headers = gateAuthHeaders();
  if (!headers) return;
  try {
    const r = await apiFetch(apiJoin("auth/gate/ledger?limit=200"), { headers });
    if (!r.ok) return;
    const d = await r.json();
    const items = Array.isArray(d.items) ? d.items : [];
    let bal = currentBalance === "∞" ? "∞" : Number(currentBalance);
    const rows = items.map((it) => {
      let extra = {};
      try { extra = JSON.parse(it.extra_json || "{}"); } catch (e) {}
      const svc = REGISTRY.services[it.service_id] || {};
      const rowBalance = bal === "∞" ? "∞" : bal;
      if (bal !== "∞") bal += Number(it.credits || 0);
      return {
        id: it.run_id || `server-${it.at_iso}-${it.service_id}`,
        atIso: it.at_iso,
        atLocal: it.at_iso,
        accountId: currentBillingIdentity().id,
        accountType: currentBillingIdentity().type,
        serviceId: it.service_id,
        serviceLabel: svc.label || it.service_id,
        credits: Number(it.credits || 0),
        balance: rowBalance,
        runLocation: extra.runLocation || currentRunLocation(),
        demoId: extra.demoId || null,
        server: true,
        gateServer: true,
        adminFree: !!extra.waived,
        extra,
      };
    });
    localStorage.setItem(LS_LEDGER, JSON.stringify(rows));
  } catch (e) {}
}

async function refreshServerWallet() {
  const t = sessionStorage.getItem("insynbio_access_token");
  if (!t) {
    state.serverMode = false;
    state.serverUsername = null;
    state.serverRole = null;
    state.serverUnlimited = false;
    if (await refreshGateWallet()) {
      updateAuthUi();
      return;
    }
    syncWalletToState();
    updateAuthUi();
    return;
  }
  try {
    const r = await apiFetchWithTimeout(
      apiJoin("auth/me"),
      { headers: { Authorization: "Bearer " + t } },
      4500
    );
    if (!r.ok) throw new Error("me");
    const d = await r.json();
    state.serverMode = true;
    state.serverUsername = d.username;
    state.serverRole = d.role;
    state.serverUnlimited = !!d.credits_unlimited;
    state.credits = d.credits;
    state.account = { role: d.role, label: d.username };
    updateAuthUi();
    updateTopbar();
  } catch (e) {
    sessionStorage.removeItem("insynbio_access_token");
    state.serverMode = false;
    state.serverUsername = null;
    state.serverRole = null;
    state.serverUnlimited = false;
    syncWalletToState();
    updateAuthUi();
    updateTopbar();
  }
}

function logoutAuth() {
  sessionStorage.removeItem("insynbio_access_token");
  state.serverMode = false;
  state.serverUsername = null;
  state.serverRole = null;
  state.serverUnlimited = false;
  syncWalletToState();
  updateAuthUi();
  updateTopbar();
}

function updateAuthUi() {
  const t = sessionStorage.getItem("insynbio_access_token");
  const isValid = t && t !== "undefined" && t !== "null";
  const openBtn = document.getElementById("auth-open-btn");
  const outBtn = document.getElementById("auth-logout-btn");
  const buyBtn = document.getElementById("buy-credits-btn");
  if (openBtn && outBtn) {
    openBtn.style.display = isValid ? "none" : "inline-block";
    outBtn.style.display = isValid ? "inline-block" : "none";
    if (buyBtn) buyBtn.style.display = isValid ? "inline-block" : "none";
  }
}

function openPaymentModal() {
  const amount = prompt("Enter amount to top up (USD):", "50");
  if (!amount || isNaN(amount)) return;
  
  const token = sessionStorage.getItem("insynbio_access_token");
  apiFetch(apiJoin("payments/create-checkout-session"), {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
    body: JSON.stringify({ amount_usd: parseInt(amount) })
  }).then(r => r.json()).then(d => {
    if (d.url) window.location.href = d.url;
    else alert("Payment error: " + (d.detail || JSON.stringify(d)));
  }).catch(e => alert("Payment failed: " + e));
}

function openAuthModal() {
  const el = document.getElementById("auth-modal");
  const msg = document.getElementById("auth-msg");
  if (msg) msg.textContent = "";
  if (el) {
    el.style.display = "flex";
    el.setAttribute("aria-hidden", "false");
  }
}

function closeAuthModal() {
  const el = document.getElementById("auth-modal");
  if (el) {
    el.style.display = "none";
    el.setAttribute("aria-hidden", "true");
  }
}

function showRegisterFields() {
  document.getElementById("auth-email-field").style.display = "block";
  document.getElementById("auth-login-btn").style.display = "none";
  document.getElementById("auth-register-btn").style.display = "none";
  document.getElementById("auth-submit-register-btn").style.display = "inline-block";
}

async function submitAuthRegister() {
  const msg = document.getElementById("auth-msg");
  const u = (document.getElementById("auth-user") && document.getElementById("auth-user").value) || "";
  const e = (document.getElementById("auth-email") && document.getElementById("auth-email").value) || "";
  const p = (document.getElementById("auth-pin") && document.getElementById("auth-pin").value) || "";
  try {
    const r = await apiFetch(apiJoin("auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u.trim(), email: e.trim(), pin: p }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || JSON.stringify(d));
    
    msg.style.color = "var(--pass)";
    msg.textContent = "Registration successful! Please check your email for the verification code.";
    
    document.getElementById("auth-email-field").style.display = "none";
    document.getElementById("auth-pin-field") ? document.getElementById("auth-pin-field").style.display = "none" : null;
    document.getElementById("auth-submit-register-btn").style.display = "none";
    document.getElementById("auth-verify-field").style.display = "block";
    document.getElementById("auth-submit-verify-btn").style.display = "inline-block";
  } catch (err) {
    msg.style.color = "var(--fail)";
    msg.textContent = String(err.message || err);
  }
}

async function submitAuthVerify() {
  const msg = document.getElementById("auth-msg");
  const u = document.getElementById("auth-user").value || "";
  const c = document.getElementById("auth-code").value || "";
  try {
    const r = await apiFetch(apiJoin("auth/verify-email"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u.trim(), code: c.trim() }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || JSON.stringify(d));
    
    msg.style.color = "var(--pass)";
    msg.textContent = "Email verified! You can now log in.";
    
    // Reset to login view
    document.getElementById("auth-verify-field").style.display = "none";
    document.getElementById("auth-submit-verify-btn").style.display = "none";
    document.getElementById("auth-login-btn").style.display = "inline-block";
    document.getElementById("auth-register-btn").style.display = "inline-block";
  } catch (err) {
    msg.style.color = "var(--fail)";
    msg.textContent = String(err.message || err);
  }
}

async function submitAuthLogin() {
  const msg = document.getElementById("auth-msg");
  const u = (document.getElementById("auth-user") && document.getElementById("auth-user").value) || "";
  const p = (document.getElementById("auth-pin") && document.getElementById("auth-pin").value) || "";
  try {
    const r = await apiFetch(apiJoin("auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u.trim(), pin: p }),
    });
    const d = await r.json();
    if (!r.ok) {
      const det = d.detail != null ? d.detail : d;
      throw new Error(typeof det === "string" ? det : JSON.stringify(det));
    }
    sessionStorage.setItem("insynbio_access_token", d.access_token);
    await refreshServerWallet();
    closeAuthModal();
    if (msg) msg.textContent = "";
  } catch (e) {
    if (msg) msg.textContent = String(e.message || e);
  }
}

async function submitAuthRegister() {
  const msg = document.getElementById("auth-msg");
  const u = (document.getElementById("auth-user") && document.getElementById("auth-user").value) || "";
  const p = (document.getElementById("auth-pin") && document.getElementById("auth-pin").value) || "";
  try {
    const r = await apiFetch(apiJoin("auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u.trim(), pin: p }),
    });
    const d = await r.json();
    if (!r.ok) {
      const det = d.detail != null ? d.detail : d;
      throw new Error(typeof det === "string" ? det : JSON.stringify(det));
    }
    sessionStorage.setItem("insynbio_access_token", d.access_token);
    await refreshServerWallet();
    closeAuthModal();
    if (msg) msg.textContent = "";
  } catch (e) {
    if (msg) msg.textContent = String(e.message || e);
  }
}

function saveCreditsBalance(n) {
  const v = Math.max(0, Math.floor(Number(n) || 0));
  try {
    localStorage.setItem(walletStorageKey(), String(v));
  } catch (e) {}
  state.credits = v;
}

function appendUsageLedger(entry) {
  try {
    let arr = [];
    try {
      arr = JSON.parse(localStorage.getItem(LS_LEDGER) || "[]");
    } catch (e) {}
    if (!Array.isArray(arr)) arr = [];
    const identity = currentBillingIdentity();
    arr.unshift({
      atIso: new Date().toISOString(),
      atLocal: enUsLocalNow(),
      accountId: identity.id,
      accountType: identity.type,
      runLocation: currentRunLocation(),
      ...entry,
    });
    if (arr.length > LEDGER_MAX) arr = arr.slice(0, LEDGER_MAX);
    localStorage.setItem(LS_LEDGER, JSON.stringify(arr));
  } catch (e) {}
}

function serviceCreditCost(serviceId) {
  const s = REGISTRY.services[serviceId];
  let cost = s ? (Number(s.credits) || 0) : 0;
  if (cost > 0) {
    if (serviceId === "vhvl-humanization") {
      const mode = (document.querySelector('input[name="vhvl-run-mode"]:checked') || {}).value || "standard_delivery";
      if (mode === "quick_preview") cost = Math.floor(cost * 0.4);
      else if (mode === "enhanced_rescue") cost = Math.floor(cost * 2.0);
    } else if (serviceId === "vhh-humanization") {
      const mode = (document.querySelector('input[name="vhh-run-mode"]:checked') || {}).value || "standard_delivery";
      if (mode === "quick_preview") cost = Math.floor(cost * 0.4);
      else if (mode === "enhanced_rescue") cost = Math.floor(cost * 2.0);
    }
  }
  return cost;
}

function updateDynamicCost() {
  const el = document.getElementById("service-credit-callout");
  if (!el || !state.service) return;
  const cost = serviceCreditCost(state.service);
  if (cost > 0) {
    el.textContent = `${cost.toLocaleString("en-US")} credits / custom run`;
  }
}

function canAffordRun(serviceId) {
  const cost = serviceCreditCost(serviceId);
  if (cost <= 0) return true;
  syncWalletToState();
  return state.credits >= cost;
}

/**
 * After a successful run: deduct server credits if logged in, else local wallet.
 */
async function recordRunDebit(serviceId, opts) {
  const cost = serviceCreditCost(serviceId);
  const service = REGISTRY.services[serviceId];
  if (!service) return { ok: false, reason: "unknown_service", debited: 0, balance: state.credits };
  if (cost <= 0) {
    syncWalletToState();
    if (sessionStorage.getItem("insynbio_access_token")) await refreshServerWallet();
    return { ok: true, debited: 0, balance: state.credits };
  }

  const token = sessionStorage.getItem("insynbio_access_token");
  if (token) {
    try {
      const r = await apiFetch(apiJoin("auth/debit"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({
          service_id: serviceId,
          amount: cost,
          run_id: (opts && opts.runRecordId) || null,
          extra: {
            demoId: opts && opts.demoId,
            runLocation: currentRunLocation(),
            ...(opts && opts.extra),
          },
        }),
      });
      const d = await r.json();
      if (r.ok && d.ok) {
        state.credits = d.balance;
        state.serverMode = true;
        appendUsageLedger({
          id: (opts && opts.runRecordId) || `ledger-${Date.now()}`,
          atIso: new Date().toISOString(),
          atLocal: enUsLocalNow(),
          serviceId,
          serviceLabel: service.label + " (server)",
          credits: cost,
          balance: d.balance,
          demoId: opts && opts.demoId != null ? opts.demoId : null,
          server: true,
        });
        updateTopbar();
        return { ok: true, debited: cost, balance: d.balance };
      }
      return {
        ok: false,
        reason: d.message || "debit_failed",
        debited: 0,
        balance: d.balance != null ? d.balance : state.credits,
        cost,
      };
    } catch (e) {
      return { ok: false, reason: String(e), debited: 0, balance: state.credits };
    }
  }

  const gateHeaders = gateAuthHeaders();
  if (gateHeaders) {
    try {
      const r = await apiFetch(apiJoin("auth/gate/debit"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...gateHeaders },
        body: JSON.stringify({
          service_id: serviceId,
          amount: cost,
          run_id: (opts && opts.runRecordId) || null,
          extra: {
            demoId: opts && opts.demoId,
            runLocation: currentRunLocation(),
            ...(opts && opts.extra),
          },
        }),
      });
      const d = await r.json();
      if (r.ok && d.ok) {
        state.credits = Number(d.balance) || 0;
        try { localStorage.setItem(walletStorageKey(), String(state.credits)); } catch (e) {}
        const adminFree = d.message === "unlimited";
        appendUsageLedger({
          id: (opts && opts.runRecordId) || `ledger-${Date.now()}`,
          serviceId,
          serviceLabel: adminFree ? `${service.label} (admin free)` : `${service.label} (gate server)`,
          credits: Number(d.debited) || 0,
          balance: adminFree ? "∞" : d.balance,
          demoId: opts && opts.demoId != null ? opts.demoId : null,
          server: true,
          gateServer: true,
          adminFree,
        });
        updateTopbar();
        return { ok: true, debited: Number(d.debited) || 0, balance: adminFree ? "∞" : d.balance, adminFree };
      }
      return {
        ok: false,
        reason: d.message || "gate_debit_failed",
        debited: 0,
        balance: d.balance != null ? d.balance : state.credits,
        cost,
      };
    } catch (e) {
      return { ok: false, reason: String(e), debited: 0, balance: state.credits };
    }
  }

  syncWalletToState();
  if (state.credits < cost) {
    return { ok: false, reason: "insufficient_credits", debited: 0, balance: state.credits, cost };
  }
  const next = state.credits - cost;
  saveCreditsBalance(next);
  appendUsageLedger({
    id: (opts && opts.runRecordId) || `ledger-${Date.now()}`,
    atIso: new Date().toISOString(),
    atLocal: enUsLocalNow(),
    serviceId,
    serviceLabel: service.label,
    credits: cost,
    balance: next,
    demoId: opts && opts.demoId != null ? opts.demoId : null,
    extra: opts && opts.extra ? opts.extra : null,
  });
  updateTopbar();
  return { ok: true, debited: cost, balance: next };
}

/** Persisted layout: sidebar width, rail width, Scope/Service vertical split (ratio 0–1). */
const LS_LAYOUT = {
  sidebarW: "insynbio_console_sidebar_w_px",
  railW: "insynbio_console_rail_w_px",
  scopePct: "insynbio_console_sidebar_scope_pct",
};

function initLayoutResizers() {
  const sw = localStorage.getItem(LS_LAYOUT.sidebarW);
  const rw = localStorage.getItem(LS_LAYOUT.railW);
  if (sw) {
    const n = Math.max(200, Math.min(520, parseInt(sw, 10) || 260));
    document.documentElement.style.setProperty("--sidebar-w", `${n}px`);
  }
  if (rw) {
    const n = Math.max(220, Math.min(520, parseInt(rw, 10) || 300));
    document.documentElement.style.setProperty("--rail-w", `${n}px`);
  }
  const scopePctRaw = localStorage.getItem(LS_LAYOUT.scopePct);
  const scopePct =
    scopePctRaw != null ? parseFloat(scopePctRaw) : NaN;
  initShellHorizontalSplitters();
  requestAnimationFrame(() => {
    initSidebarScopeServiceSplitter(Number.isFinite(scopePct) ? scopePct : 0.38);
  });
}

function initShellHorizontalSplitters() {
  const elSidebar = document.getElementById("split-sidebar");
  const elRail = document.getElementById("split-rail");
  const rail = document.querySelector(".rail");
  const sidebar = document.querySelector(".sidebar");
  if (!elSidebar || !elRail || !rail || !sidebar) return;

  elSidebar.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const w0 = sidebar.getBoundingClientRect().width;
    elSidebar.classList.add("is-dragging");
    function move(ev) {
      const nw = Math.round(Math.max(200, Math.min(520, w0 + (ev.clientX - startX))));
      document.documentElement.style.setProperty("--sidebar-w", `${nw}px`);
      localStorage.setItem(LS_LAYOUT.sidebarW, String(nw));
    }
    function up() {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      elSidebar.classList.remove("is-dragging");
    }
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });

  elRail.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const w0 = rail.getBoundingClientRect().width;
    elRail.classList.add("is-dragging");
    function move(ev) {
      const nw = Math.round(Math.max(220, Math.min(520, w0 - (ev.clientX - startX))));
      document.documentElement.style.setProperty("--rail-w", `${nw}px`);
      localStorage.setItem(LS_LAYOUT.railW, String(nw));
    }
    function up() {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      elRail.classList.remove("is-dragging");
    }
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

function initSidebarScopeServiceSplitter(initialPct) {
  const split = document.getElementById("sidebar-splitter-h");
  const top = document.getElementById("sidebar-pane-top");
  const body = document.querySelector(".sidebar-body");
  if (!split || !top || !body) return;

  function applyScopePct(pct) {
    const p = Math.max(0.18, Math.min(0.72, pct));
    top.style.flex = `0 0 ${(p * 100).toFixed(2)}%`;
    localStorage.setItem(LS_LAYOUT.scopePct, String(p));
  }
  applyScopePct(initialPct);

  split.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const startY = e.clientY;
    const h0 = top.getBoundingClientRect().height;
    const bodyH = body.getBoundingClientRect().height;
    if (bodyH < 160) return;
    split.classList.add("is-dragging");
    function move(ev) {
      const dy = ev.clientY - startY;
      let newH = h0 + dy;
      newH = Math.max(80, Math.min(bodyH - 80, newH));
      applyScopePct(newH / bodyH);
    }
    function up() {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      split.classList.remove("is-dragging");
    }
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bootGateCheck();
  initLayoutResizers();
  bootApiConnectivityCheck();
  renderApp();
  reflectApiButtonState();
  loadHealth()
    .then(() => updateTopbar())
    .catch(() => updateTopbar());
  refreshServerWallet().catch(() => {
    syncWalletToState();
    updateAuthUi();
    updateTopbar();
  });
});

/** When deployed on a public host (e.g. GitHub Pages) and the user has not yet
 *  configured an HTTPS tunnel pointing at their local API, every API call would
 *  hit the static host and return HTML — producing the cryptic
 *  "Unexpected token '<', "<html>...' is not valid JSON" error.
 *  Surface this clearly: red banner + auto-open the API Endpoint modal. */
function isPublicDeployment() {
  const h = location.hostname;
  if (!h) return false;
  if (h === "localhost" || h === "127.0.0.1") return false;
  return true;
}

function isCloudConsoleHost() {
  const h = (location.hostname || "").toLowerCase();
  return h === "console.insynbio.com"
    || h === "insynbio.com"
    || h === "www.insynbio.com"
    || h === "157.180.91.72";
}

function isDevMode() {
  try {
    return localStorage.getItem("insynbio_dev_mode") === "1" || window.location.search.includes("dev=1");
  } catch(e) { return false; }
}

function toggleDevMode() {
  try {
    const current = localStorage.getItem("insynbio_dev_mode") === "1";
    if (current) localStorage.removeItem("insynbio_dev_mode");
    else localStorage.setItem("insynbio_dev_mode", "1");
    window.location.reload();
  } catch(e) {}
}

function requiresExternalApiTunnel() {
  // The production console is served by the same origin as the FastAPI gateway
  // (/api/*). Mobile users should never be asked to configure localhost/ngrok.
  if (isDevMode()) return true;
  return isPublicDeployment() && !isCloudConsoleHost();
}

function showApiNotConfiguredBanner() {
  if (document.getElementById("api-not-configured-banner")) return;
  const bar = document.createElement("div");
  bar.id = "api-not-configured-banner";
  bar.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9000;background:#7a1d1d;color:#ffe9e9;padding:8px 14px;font:12px/1.5 system-ui,sans-serif;display:flex;align-items:center;gap:12px;border-bottom:1px solid #f85149;box-shadow:0 2px 8px rgba(0,0,0,.4)";
  bar.innerHTML = `
    <strong style="color:#ffd1d1">⚠ Not connected to a compute backend.</strong>
    <span>Requests will fail until you configure an HTTPS tunnel pointing at your local API (port 8000).</span>
    <button type="button" onclick="openApiSettingsModal()" style="margin-left:auto;background:#f85149;color:#1a0707;border:none;padding:5px 12px;border-radius:5px;font-weight:600;cursor:pointer">Configure now</button>
    <button type="button" onclick="document.getElementById('api-not-configured-banner').remove()" style="background:transparent;color:#ffe9e9;border:1px solid #ffe9e9;padding:4px 8px;border-radius:5px;cursor:pointer">Dismiss</button>
  `;
  document.body.appendChild(bar);
  document.body.style.paddingTop = "40px";
}

function reflectApiButtonState() {
  const btn = document.getElementById("api-settings-btn");
  if (!btn) return;
  const saved = _getUserApiEndpoint();
  // Keep button text as single ⚙ icon always — use red border to signal config needed
  btn.textContent = "⚙";
  if (requiresExternalApiTunnel() && !saved) {
    btn.style.border = "1px solid #f85149";
    btn.style.color = "#f85149";
    btn.title = "⚠ API endpoint not configured — click to set tunnel URL";
    btn.style.display = "flex";
  } else if (saved || isDevMode() || requiresExternalApiTunnel()) {
    btn.style.border = "";
    btn.style.color = "";
    btn.title = "API Endpoint Settings";
    btn.style.display = "flex";
  } else {
    btn.style.display = "none";
  }
}

/** Gate logout — clears session auth and redirects to /login */
function gateLogout() {
  try {
    sessionStorage.removeItem("insynbio_gate_auth");
    sessionStorage.removeItem("insynbio_gate_role");
  } catch(e) {}
  window.location.href = "/login";
}

/** Gate auth check — if accessed via non-localhost and no session auth, go to /login */
function bootGateCheck() {
  const h = location.hostname;
  if (h === "localhost" || h === "127.0.0.1") return; // local dev: no gate
  if (!sessionStorage.getItem("insynbio_gate_auth")) {
    window.location.replace("/login");
  }
}

function bootApiConnectivityCheck() {
  if (!requiresExternalApiTunnel()) return;
  const saved = _getUserApiEndpoint();
  if (saved) return;
  showApiNotConfiguredBanner();
  setTimeout(() => { try { openApiSettingsModal(); } catch (e) {} }, 250);
}

async function loadHealth() {
  try {
    const res = await apiFetchWithTimeout(apiJoin("health"), {}, 4500);
    const ct = res.headers.get("content-type") || "";
    if (!res.ok || !ct.includes("json")) {
      throw new Error("non-json response");
    }
    const data = await res.json();
    state.apiVersion = data.version || "—";
    state.gitSha = data.git_sha || null;
    state.apiBuildId = data.build_id != null ? String(data.build_id) : null;
    state.apiEnvironment = data.environment != null ? String(data.environment) : null;
    state.apiAnalysisVersion = data.analysis_version != null ? String(data.analysis_version) : null;
    state.apiProtocolVersion = data.protocol_version != null ? String(data.protocol_version) : null;
    state.apiReportFormatVersion =
      data.report_format_version != null ? String(data.report_format_version) : null;
    state.serviceReportVersions =
      data.service_report_versions && typeof data.service_report_versions === "object"
        ? data.service_report_versions
        : null;

    // Header P/F chips removed to reduce crowding; versions still visible in right rail
  } catch (err) {
    state.apiVersion = "offline";
    state.gitSha = null;
    state.apiBuildId = null;
    state.apiEnvironment = null;
    state.apiAnalysisVersion = null;
    state.apiProtocolVersion = null;
    state.apiReportFormatVersion = null;
    state.serviceReportVersions = null;
    if (requiresExternalApiTunnel() && !_getUserApiEndpoint()) {
      showApiNotConfiguredBanner();
    }
  }
}

function renderApp() {
  syncWalletToState();
  renderSidebar();
  renderWorkspace();
  renderEmptyRail();
  updateTopbar();
}

function renderSidebar() {
  const moduleNav = document.getElementById("module-nav");
  const serviceNav = document.getElementById("service-nav");

  const onlineModules = REGISTRY.modules.filter(m => m.tier === "online");
  const offlineModules = REGISTRY.modules.filter(m => m.tier === "offline");

  moduleNav.innerHTML = `
    <div class="module-divider">Online Services</div>
    ${onlineModules.map(m => `
      <button class="module-btn ${m.id === state.module ? "active" : ""}" onclick="activateModule('${m.id}')">
        ${m.label}
        <span class="service-sub">${m.subtitle}</span>
      </button>
    `).join("")}
    <div class="module-divider">Offline Services</div>
    ${offlineModules.map(m => `
      <button class="module-btn offline-module ${m.id === state.module ? "active" : ""}" onclick="activateModule('${m.id}')">
        ${m.label}
        <span class="service-sub">${m.subtitle}</span>
      </button>
    `).join("")}
  `;

  const currentModule = REGISTRY.modules.find(m => m.id === state.module);
  if (currentModule.id === "regular-antibody-engineering") {
    serviceNav.innerHTML = RAE_SERVICE_GROUPS.map((g) => {
      const ids = currentModule.services.filter((sid) => {
        const s = REGISTRY.services[sid];
        return s && s.navGroup === g.id;
      });
      if (!ids.length) return "";
      const buttons = ids.map((serviceId) => {
        const service = REGISTRY.services[serviceId];
        return `
      <button class="service-btn ${serviceId === state.service ? "active" : ""}" onclick="activateService('${serviceId}')">
        ${service.label}
        <span class="service-sub">${service.subtitle}</span>
      </button>`;
      }).join("");
      return `<div class="service-group"><div class="service-group-label">${g.label}</div>${buttons}</div>`;
    }).join("");
  } else {
    serviceNav.innerHTML = currentModule.services.map(serviceId => {
      const service = REGISTRY.services[serviceId];
      return `
      <button class="service-btn ${serviceId === state.service ? "active" : ""}" onclick="activateService('${serviceId}')">
        ${service.label}
        <span class="service-sub">${service.subtitle}</span>
      </button>
    `;
    }).join("");
  }
}

function updateTopbar() {
  const service = REGISTRY.services[state.service];
  syncWalletToState();
  const uiBuildEl = document.getElementById("top-ui-build");
  if (uiBuildEl) uiBuildEl.textContent = `UI · ${UI_BUILD_VERSION}`;
  const relEl = document.getElementById("top-backend-release");
  if (relEl) {
    if (state.apiBuildId && state.apiEnvironment) {
      const ana = state.apiAnalysisVersion || state.apiVersion || "—";
      relEl.textContent = `Release · ${state.apiBuildId} · ${state.apiEnvironment} · ana ${ana}`;
      relEl.title = [
        state.apiProtocolVersion ? `protocol ${state.apiProtocolVersion}` : null,
        state.apiReportFormatVersion ? `report ${state.apiReportFormatVersion}` : null,
        state.gitSha ? `git ${state.gitSha}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
    } else if (state.apiVersion === "offline") {
      relEl.textContent = "Release · offline";
      relEl.title = "Configure API endpoint or start uvicorn";
    } else {
      relEl.textContent = "Release · —";
      relEl.title = "Older API: no build_id in GET /health — upgrade backend";
    }
  }
  let apiLine = `API · ${state.apiVersion}`;
  if (state.gitSha) apiLine += ` · ${state.gitSha}`;
  document.getElementById("top-api-version").textContent = apiLine;
  document.getElementById("top-service-name").textContent = `Service · ${service.label}`;
  const protocolEl = document.getElementById("top-protocol-version");
  if (protocolEl) {
    protocolEl.textContent = `Protocol · ${state.apiProtocolVersion || "—"}`;
  }
  document.getElementById("top-analysis-version").textContent =
    `Analysis · ${state.apiAnalysisVersion || service.analysisVersion || "—"}`;
  const rptFmtEl = document.getElementById("top-report-format-version");
  if (rptFmtEl) {
    rptFmtEl.textContent = `Report format · ${state.apiReportFormatVersion || "—"}`;
  }
  const svcRptEl = document.getElementById("top-service-report-version");
  if (svcRptEl) {
    svcRptEl.textContent = `Service report · ${lookupServiceReportVersion(service)}`;
  }
  const accEl = document.getElementById("top-account");
  const railAccCont = document.getElementById("rail-account-container");
  const railAccEl = document.getElementById("rail-account-id");
  const ident = currentBillingIdentity();
  const label = ident.server ? `👤 ${ident.id}` : ident.gate ? `Gate · ${ident.id}` : `Guest · ${ident.id}`;
  if (accEl) { accEl.textContent = label; accEl.style.display = "inline-block"; }
  if (railAccEl) railAccEl.textContent = label;
  if (railAccCont) railAccCont.style.display = "block";
  const credEl = document.getElementById("top-credits");
  if (credEl) {
    if (serverWalletShowsInfinityBalance()) {
      credEl.textContent = `Credits · ∞ (${creditsInfinityParenLabel()})`;
    } else {
      credEl.textContent = `Credits · ${Number(state.credits || 0).toLocaleString("en-US")}`;
    }
  }
  updateAuthUi();
}

function captureSharedSequences() {
  const getVal = id => { const el = document.getElementById(id); return el ? el.value.trim() : ""; };
  
  const vh = ["vhvl-vh", "fv-vh", "cmc-vh", "seg-vh", "vh2vhh-seq", "rchk-vhvl-donor-vh", "pet-vh"].map(getVal).find(v => v);
  if (vh) state.sharedVh = vh;
  
  const vl = ["vhvl-vl", "fv-vl", "cmc-vl", "seg-vl", "cdna-vl", "rchk-vhvl-donor-vl", "pet-vl"].map(getVal).find(v => v);
  if (vl) state.sharedVl = vl;
  
  // Note: For cDNA form, the primary sequence id is "cdna-seq" and it's used for VH or VHH depending on mode
  const cdnaSeq = getVal("cdna-seq");
  if (cdnaSeq) {
     if (getVal("cdna-vl") || state.module === "regular-antibody-engineering") state.sharedVh = cdnaSeq;
     else state.sharedVhh = cdnaSeq;
  }
  
  const vhh = ["vhh-seq", "vhh-struct-seq", "vhh-cmc-seq", "vhh-seg-seq", "bs-cmc-arm1", "rchk-vhh-donor"].map(getVal).find(v => v);
  if (vhh) state.sharedVhh = vhh;

  const name = ["vhvl-name", "fv-name", "cmc-name", "vhh-name", "vhh-struct-name", "vhh-cmc-name", "vhh-seg-name", "seg-name", "bs-cmc-name", "vh2vhh-name"].map(getVal).find(v => v);
  if (name) state.sharedName = name;
}

function populateSharedSequences() {
  const setVal = (id, val) => { const el = document.getElementById(id); if (el && !el.value) el.value = val; };
  
  let populated = false;

  if (state.sharedVh) {
    ["vhvl-vh", "fv-vh", "cmc-vh", "seg-vh", "vh2vhh-seq", "rchk-vhvl-donor-vh", "pet-vh"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedVh; populated = true; }
    });
  }
  if (state.sharedVl) {
    ["vhvl-vl", "fv-vl", "cmc-vl", "seg-vl", "cdna-vl", "rchk-vhvl-donor-vl", "pet-vl"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedVl; populated = true; }
    });
  }
  if (state.sharedVhh) {
    ["vhh-seq", "vhh-struct-seq", "vhh-cmc-seq", "vhh-seg-seq", "bs-cmc-arm1", "rchk-vhh-donor"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedVhh; populated = true; }
    });
  }
  if (state.sharedName) {
    ["vhvl-name", "fv-name", "cmc-name", "vhh-name", "vhh-struct-name", "vhh-cmc-name", "vhh-seg-name", "seg-name", "bs-cmc-name", "vh2vhh-name"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedName; }
    });
  }
  
  const cdnaSeq = document.getElementById("cdna-seq");
  if (cdnaSeq) {
    const s = REGISTRY.services[state.service];
    const isVhh = s && s.chainType === "vhh";
    if (isVhh && state.sharedVhh) { cdnaSeq.value = state.sharedVhh; populated = true; }
    else if (!isVhh && state.sharedVh) { cdnaSeq.value = state.sharedVh; populated = true; }
  }

  return populated;
}

function clearSharedSequences() {
  state.sharedVh = null;
  state.sharedVl = null;
  state.sharedVhh = null;
  state.sharedName = null;
}

function activateModule(moduleId) {
  captureSharedSequences();
  state.module = moduleId;
  const mod = REGISTRY.modules.find(m => m.id === moduleId);
  state.service = mod.services[0];
  renderSidebar();
  renderWorkspace();
  renderEmptyRail();
  updateTopbar();
}

function activateService(serviceId) {
  captureSharedSequences();
  const legacyVhvl = {
    "mouse-humanization": "mouse",
    "rat-humanization": "rat",
  };
  if (legacyVhvl[serviceId]) {
    state.pendingVhvlSpecies = legacyVhvl[serviceId];
    serviceId = "vhvl-humanization";
  }
  state.service = serviceId;
  state.module = REGISTRY.services[serviceId].module;
  renderSidebar();
  renderWorkspace();
  renderEmptyRail();
  updateTopbar();
}

function creditChip(service) {
  if (service.module === "offline-services") {
    return `<span class="chip offline">Custom Quote</span>`;
  }
  if (service.computeMode === "Info") {
    return `<span class="chip accent">Workflow info</span>`;
  }
  if (service.computeMode === "Demo" || service.credits === 0) {
    return `<span class="chip free">Demo · Free</span>`;
  }
  return `<span class="chip credit" id="service-credit-chip">${service.credits} credits / run</span>`;
}

function creditCallout(service) {
  if (service.module === "offline-services") {
    return `
      <div class="credit-callout quote" aria-label="Credit cost">
        <span class="credit-label">Credit cost</span>
        <span class="credit-value">Custom quote</span>
        <span class="credit-note">expert-scoped offline project</span>
      </div>`;
  }
  if (service.computeMode === "Internal") {
    return `
      <div class="credit-callout quote" aria-label="Credit cost">
        <span class="credit-label">Credit cost</span>
        <span class="credit-value">Internal access</span>
        <span class="credit-note">not publicly billed</span>
      </div>`;
  }
  if (service.computeMode === "Info") {
    return `
      <div class="credit-callout free" aria-label="Credit cost">
        <span class="credit-label">Credit cost</span>
        <span class="credit-value">0 credits · workflow info</span>
      </div>`;
  }
  if (service.computeMode === "Demo" || service.credits === 0) {
    return `
      <div class="credit-callout free" aria-label="Credit cost">
        <span class="credit-label">Credit cost</span>
        <span class="credit-value">0 credits</span>
        <span class="credit-note">free service / demo-only</span>
      </div>`;
  }
  return `
    <div class="credit-callout" aria-label="Credit cost">
      <span class="credit-label">Credit cost</span>
      <span class="credit-value" id="service-credit-callout">${Number(service.credits).toLocaleString("en-US")} credits / custom run</span>
      <span class="credit-note">preset demo sequences are free</span>
    </div>`;
}

/** Dynamic credit update for CMC services with Smart-CMC option */
function updateCmcCredits() {
  const isSmart = !!(
    (document.getElementById("cmc-smart-opt") && document.getElementById("cmc-smart-opt").checked) ||
    (document.getElementById("vhh-cmc-smart-opt") && document.getElementById("vhh-cmc-smart-opt").checked) ||
    (document.getElementById("bs-cmc-smart-opt") && document.getElementById("bs-cmc-smart-opt").checked)
  );
  
  const baseCredits = 3500;
  const smartCredits = 6500;
  const credits = isSmart ? smartCredits : baseCredits;
  
  const chip = document.getElementById("service-credit-chip");
  if (chip) {
    chip.textContent = `${credits} credits / run`;
  }
  const callout = document.getElementById("service-credit-callout");
  if (callout) {
    callout.textContent = `${credits.toLocaleString("en-US")} credits / custom run`;
  }
}

function renderWorkspace() {
  const service = REGISTRY.services[state.service];
  const root = document.getElementById("workspace-root");
  const mod = REGISTRY.modules.find(m => m.id === service.module);
  root.innerHTML = `
    <div class="service-shell">
      <section class="surface service-header">
        <div class="header-row">
          <div>
            <div class="panel-label">${mod.label}</div>
            <h1>${service.label}</h1>
            <p>${service.description}</p>
            ${creditCallout(service)}
            ${service.refDb === "Clinical reference" ? `
              <div class="db-badge">
                <div class="db-badge-title">Benchmarked against clinical reference cohorts</div>
                <div class="db-badge-sub">Curated antibody clinical/developability references</div>
              </div>` : ""}
            ${service.refDb === "VHH clinical" ? `
              <div class="db-badge vhh42">
                <div class="db-badge-title">Benchmarked against VHH clinical reference</div>
                <div class="db-badge-sub">Curated VHH clinical/developability references</div>
              </div>` : ""}
            ${service.bispecificCmc ? `
              <div class="db-badge vhh42">
                <div class="db-badge-title">Bispecific VHH fusion CMC</div>
                <div class="db-badge-sub">Per-arm VHH clinical reference &middot; fusion pI / linker / ER score &middot; Bispecific VHH CMC Standard v1.0</div>
              </div>` : ""}
          </div>
          <div class="chips">
            <span class="chip accent">${service.computeMode}</span>
            <span class="chip">${service.analysisVersion}</span>
            ${creditChip(service)}
          </div>
        </div>
      </section>
      ${renderServicePanel(service)}
    </div>
  `;
  hydrateService(service);
}

function renderServicePanel(service) {
  const methodBlock = `
    <section class="surface panel">
      <div class="panel-label">Method &amp; Version</div>
      <div class="method-grid">
        <div class="method-card"><div class="k">Service</div><div class="v">${service.label}</div></div>
        <div class="method-card"><div class="k">Analysis Version</div><div class="v mono">${service.analysisVersion}</div></div>
        <div class="method-card"><div class="k">Underlying Standard</div><div class="v mono">${service.underlyingStandard}</div></div>
        <div class="method-card"><div class="k">Report Version</div><div class="v mono">${service.reportVersion}</div></div>
      </div>
    </section>
  `;

  let formBlock = "";
  switch (service.runner) {
    case "vhvl":              formBlock = renderVhvlForm(service); break;
    case "recheck-vhvl":      formBlock = renderRecheckVhvlForm(service); break;
    case "structural-vhvl":   formBlock = renderStructuralVhvlForm(service); break;
    case "cmc-igg":           formBlock = renderCmcIggForm(service); break;
    case "vhh-humanization":  formBlock = renderVhhHumanizationForm(service); break;
    case "recheck-vhh":       formBlock = renderRecheckVhhForm(service); break;
    case "vhh-structural":    formBlock = renderVhhStructuralForm(service); break;
    case "cmc-vhh":           formBlock = renderVhhCmcForm(service); break;
    case "bispecific-analyzer": formBlock = renderBispecificAnalyzerForm(service); break;
    case "cmc-bispecific":    formBlock = renderCmcBispecificForm(service); break;
    case "vh-to-vhh":         formBlock = renderVhToVhhForm(service); break;
    case "bispecific-assembler": formBlock = renderBispecificAssemblerForm(service); break;
    case "segmentation-vhvl": formBlock = renderSegmentationVhvlForm(service); break;
    case "vhh-segmentation":  formBlock = renderVhhSegmentationForm(service); break;
    case "cdna-optimization": formBlock = renderCdnaOptimizationForm(service); break;
    case "offline-request":   formBlock = renderOfflineRequestForm(service); break;
    case "petization":        formBlock = renderPetizationForm(service); break;
    default: formBlock = `<section class="surface panel"><div class="muted">No renderer defined.</div></section>`;
  }

  return `${formBlock}${methodBlock}`;
}

// ── Form renderers ────────────────────────────────────────────────────────────

function renderStructuralVhvlForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Fv structure modeling</div>
      <p style="color:var(--muted);font-size:12px;line-height:1.65;margin-bottom:12px">
        Provide one VH/VL pair (demo or text boxes), or <strong>multiple pairs</strong> via FASTA. The server runs in-silico Fv modeling per pair and returns <code>.pdb</code> downloads. Full humanization still bundles Fv modeling in Phase 3; this page is for quick standalone Fv models.
      </p>
      <div class="form-grid">
        <div class="field"><label>Demo</label>
          <select id="fv-demo" onchange="loadServiceDemo()"></select>
        </div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional — appears in report)</span></label><input type="text" id="fv-name" placeholder="e.g. Ab001, clone-12, anti-EGFR-mAb" maxlength="80" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>VH (single pair)</label><textarea id="fv-vh" rows="3" placeholder="Heavy chain Fv amino acid sequence"></textarea></div>
        <div class="field full"><label>VL (single pair)</label><textarea id="fv-vl" rows="3" placeholder="Light chain Fv amino acid sequence"></textarea></div>
        <div class="field full"><label>Multi-pair FASTA (optional)</label>
          <textarea id="fv-fasta-batch" rows="6" placeholder="Format A — one pair per block:&#10;&gt;pair_id&#10;VH_SEQUENCE_LINE&#10;VL_SEQUENCE_LINE&#10;&#10;Format B — paired headers:&#10;&gt;sample1_H&#10;VH…&#10;&gt;sample1_L&#10;VL…"></textarea>
        </div>
        <div class="field">
          <label>Upload FASTA</label>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <label for="fv-fasta-file" class="btn" style="margin:0">Choose FASTA File</label>
            <span id="fv-fasta-file-name" class="muted" style="font-size:12px">No file selected</span>
          </div>
          <input type="file" id="fv-fasta-file" accept=".fa,.fasta,.faa,.txt,.seq" onchange="updateFileNameLabel(this, 'fv-fasta-file-name')" style="position:absolute;left:-9999px;opacity:0;pointer-events:none" />
        </div>
      </div>
      <p style="font-size:11px;color:var(--muted);margin:8px 0 10px">If the multi-FASTA field or file has content, it takes priority over the VH/VL boxes. Max 15 pairs per job.</p>
      <div class="panel-label">Workflow</div>
      <p style="font-size:11px;color:var(--muted);line-height:1.6;margin-bottom:8px">
        <strong>Jump to:</strong> optional routing shortcut. <strong>Session:</strong> last-loaded VH/VL demo stores <strong>donor species</strong> (mouse / rat / human reference) for downstream services. <strong>Next:</strong> opens VH/VL Humanization for mouse/rat donors; fully human references open Segmentation for numbering preview.
      </p>
      <div class="button-row">
        <button type="button" class="btn primary" onclick="activateHumanizationFromLastDonor()">Next: VH/VL Humanization (auto route from last demo species)</button>
      </div>
      <div class="button-row" style="margin-top:8px">
        <button type="button" class="btn" onclick="activateService('segmentation-vhvl')">Segmentation &amp; Germline</button>
        <button type="button" class="btn offline-btn" onclick="activateModule('offline-services')">Offline (AF2 Multimer…)</button>
      </div>
      <div class="helper" id="fv-helper"></div>
      <div class="button-row" style="margin-top:14px;flex-wrap:wrap;align-items:center">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run ImmuneBuilder (async)</button>
        <button type="button" class="btn" id="fv-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderVhvlForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="vhvl-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Donor species</label>
          <select id="vhvl-species">
            <option value="mouse">Mouse</option>
            <option value="rat">Rat</option>
          </select>
        </div>
        <div class="field"><label>Report format</label>
          <select id="vhvl-format">
            <option value="html" selected>HTML only</option>
          </select>
        </div>
        <div class="field full helper" style="margin-top:-4px"><strong>Delivery bundle:</strong> Each job ZIP includes README.txt, FASTA, optional PDBs, and any reports produced for that run (e.g. HTML). <strong>Report format</strong> selects which report variants are generated. <strong>Client-facing reports:</strong> English only. <strong>Donor species</strong> must agree with the pasted VH/VL (mouse or rat).</div>
        <div class="field full">
          <label><input type="checkbox" id="vhvl-async" checked> Background job (poll status — avoids browser timeout on long structure runs)</label>
        </div>
        <div class="field full"><label>Project / sequence name <span class="muted" style="font-weight:400;font-size:11px">(optional — echoed as <code>project_name</code> in job metadata &amp; reports)</span></label><input type="text" id="vhvl-name" placeholder="Your project or sequence identifier" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full helper" style="margin-top:-6px;font-size:11px">If left blank, the server uses the <strong>job ID</strong> as the neutral archive label — no auto-generated project titles.</div>
        <div class="field full"><label>VH sequence</label><textarea id="vhvl-vh"></textarea></div>
        <div class="field full"><label>VL sequence</label><textarea id="vhvl-vl"></textarea></div>
      </div>

      <!-- Customer Run Mode (maps to internal engineering switches) -->
      <div style="margin: 15px 0; padding: 12px; background: rgba(33,199,217,0.08); border: 1px solid rgba(33,199,217,0.3); border-radius: 8px;">
        <div style="color: var(--accent); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Run Mode</div>
        <div class="helper" style="margin-bottom: 8px;">Choose the purpose of the customer run. The console manages structure QC, rescue, and surface reshaping settings automatically.
          <strong>Quick vs Standard/Enhanced:</strong> final VH/VL sequences are <strong>not guaranteed identical</strong> — Standard and Enhanced run structure-informed QC and may apply rescue or surface fallback; Quick skips structure modeling and those post-engine routes (same donor input can still match when no fallback fires).</div>
        <div class="form-grid">
          <div class="field full">
            <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer; color: var(--text);">
              <input type="radio" name="vhvl-run-mode" id="vhvl-run-mode-quick" value="quick_preview" style="width: 16px; height: 16px; margin-top: 2px;" onchange="updateDynamicCost()">
              <span><strong>Quick Preview</strong> <span style="font-size:10px;color:#059669;background:#dcfce7;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #bbf7d0;font-weight:600">6,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top: 4px; font-size: 11px; color: var(--muted);">
              Fast draft run for input checks and workflow preview. Structure QC is skipped; no RMSD/pLDDT/angle evidence. Not for final delivery.
            </p>
          </div>
          <div class="field full">
            <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer; color: var(--text);">
              <input type="radio" name="vhvl-run-mode" id="vhvl-run-mode-standard" value="standard_delivery" checked style="width: 16px; height: 16px; margin-top: 2px;" onchange="updateDynamicCost()">
              <span><strong>Standard Delivery</strong> <span style="font-size:10px;color:#d97706;background:#fef3c7;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #fde68a;font-weight:600">15,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top: 4px; font-size: 11px; color: var(--muted);">
              Recommended customer setting. Runs structure QC and allows the CDR-preserving FR surface route when compatibility is low or QC is advisory.
            </p>
          </div>
          <div class="field full">
            <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer; color: var(--text);">
              <input type="radio" name="vhvl-run-mode" id="vhvl-run-mode-enhanced" value="enhanced_rescue" style="width: 16px; height: 16px; margin-top: 2px;" onchange="updateDynamicCost()">
              <span><strong>Enhanced Rescue Evaluation</strong> <span style="font-size:10px;color:#c026d3;background:#fce7f3;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #fbcfe8;font-weight:600">30,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top: 4px; font-size: 11px; color: var(--muted);">
              Use when the standard route is WARN/FAIL or framework compatibility is low. Evaluates additional rescue routes; not guaranteed to outperform Standard Delivery.
            </p>
          </div>
        </div>
      </div>

      <div class="button-row" style="flex-wrap:wrap;align-items:center">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run</button>
        <button type="button" class="btn" id="vhvl-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="helper" id="vhvl-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderRecheckVhvlForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Donor + Candidate input (VH/VL)</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="rchk-vhvl-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Source species</label>
          <select id="rchk-vhvl-species">
            <option value="mouse">Mouse</option>
            <option value="rabbit">Rabbit (API/offline route)</option>
          </select>
        </div>
        <div class="field"><label>Clean mode</label>
          <select id="rchk-vhvl-clean">
            <option value="detect">Detect only</option>
            <option value="suggest">Suggest cleaning</option>
            <option value="auto" selected>Auto clean before scoring</option>
          </select>
        </div>
        <div class="field"><label><input type="checkbox" id="rchk-vhvl-struct" checked> Run structure QC</label></div>
        <input type="hidden" id="rchk-vhvl-async" value="on">
        <div class="field full"><label>Project / sequence name <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="rchk-vhvl-name" placeholder="e.g. CD20-client-recheck-01" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>Donor VH</label><textarea id="rchk-vhvl-donor-vh"></textarea></div>
        <div class="field full"><label>Donor VL</label><textarea id="rchk-vhvl-donor-vl"></textarea></div>
        <div class="field full"><label>Customer humanized VH (candidate)</label><textarea id="rchk-vhvl-cand-vh"></textarea></div>
        <div class="field full"><label>Customer humanized VL (candidate)</label><textarea id="rchk-vhvl-cand-vl"></textarea></div>
      </div>
      <div class="helper" id="rchk-vhvl-helper">Runs unified virtual recheck: input QC + cleaning audit + optional structure conservation + mini-CMC + HPR + paired naturalness.</div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run VH/VL Recheck</button>
        <button type="button" class="btn" id="rchk-vhvl-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderCmcIggForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="cmc-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Regular antibody origin</label>
          <select id="cmc-antibody-type" onchange="updateCmcOriginNote()">
            <option value="humanized">Humanized / engineered (gene-engineered)</option>
            <option value="humanized_transgenic">Fully human (transgenic mouse platform)</option>
            <option value="phage_display">Fully human (phage display)</option>
            <option value="b_cell_derived">B-cell derived (human B cells)</option>
          </select>
        </div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label>
          <input type="text" id="cmc-sequence-name" placeholder="e.g. Client-AB-001, IL17A-lead-3, Briakinumab comparator" maxlength="100" style="font-family:var(--font-mono,monospace)">
        </div>
        <div class="field full">
          <div class="helper" id="cmc-origin-note" style="margin:0">
            Sequence source is required for customer-submitted VH/VL sequences. Gene-engineered humanization uses the engineered clinical gate set; transgenic-mouse campaigns use the transgenic cohort file when installed.
          </div>
        </div>
        <div class="field full"><label>VH sequence</label><textarea id="cmc-vh"></textarea></div>
        <div class="field full"><label>VL sequence</label><textarea id="cmc-vl"></textarea></div>
        <div class="field full">
          <p class="muted" style="font-size:10px;margin:0">In-silico Fv structure modeling is always applied. Buried residues (SASA &lt; 30%) and Vernier-zone positions are automatically excluded from mutation candidates.</p>
        </div>
        <div class="field full">
          <label class="smart-opt-label">
            <input type="checkbox" id="cmc-smart-opt" onchange="updateCmcCredits()">
            <span style="font-weight:600">Smart-CMC optimization suggestions <span class="muted" style="font-weight:400;font-size:11px">(+3000 credits)</span></span>
          </label>
          <p class="helper" style="margin-top:4px">Enable AI-driven mutation suggestions to improve developability (pI, aggregation, stability). Default is assessment only.</p>
        </div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run ${service.label}</button>
        <button type="button" class="btn" id="cmc-cancel-btn" style="display:none;border-color:#c9a227;color:#c9a227" onclick="cancelCmcRun()">Cancel job</button>
      </div>
      <div class="helper" id="cmc-helper"></div>
      <div id="cmc-status-bar"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

// Called after CMC panel DOM is ready — re-attach to in-flight job if one exists
function cmcCheckResumeJob() {
  const saved = sessionStorage.getItem("cmc_active_job");
  if (!saved) return;
  let info;
  try { info = JSON.parse(saved); } catch { sessionStorage.removeItem("cmc_active_job"); return; }
  const elapsed = (Date.now() - (info.startedAt || 0)) / 1000;
  if (elapsed > 1200) { sessionStorage.removeItem("cmc_active_job"); return; }
  const statusBox = document.getElementById("cmc-status-bar");
  if (!statusBox) return;
  const kindLabel = info.kind === "variant" ? `Variant verification (${info.category || ""})` : "CMC job";
  statusBox.innerHTML = `<div style="margin-top:8px;padding:8px 10px;border-radius:4px;background:rgba(201,162,39,.12);border:1px solid rgba(201,162,39,.35);font-size:11px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
    <span style="color:var(--accent)">⏳ ${kindLabel} in progress (${Math.round(elapsed)}s elapsed) — job id: ${info.jobId}</span>
    <button class="btn" style="font-size:11px;padding:3px 10px" onclick="cmcResumePolling()">Re-attach</button>
    <button class="btn" style="font-size:11px;padding:3px 10px;border-color:#c9a227;color:#c9a227" onclick="cancelCmcRun()">Cancel</button>
  </div>`;
  _cmcSetCancelVisible(true);
}

async function cmcResumePolling() {
  const saved = sessionStorage.getItem("cmc_active_job");
  if (!saved) return;
  let info;
  try { info = JSON.parse(saved); } catch { sessionStorage.removeItem("cmc_active_job"); return; }
  const { jobId, sequenceName, demoId, kind } = info;
  _currentCmcJobId = jobId;
  _cmcAbortCtrl = new AbortController();
  _cmcSetCancelVisible(true);
  const isVariant = (kind === "variant");
  const labelHead = isVariant ? `Variant (${info.category || ""})` : "CMC IgG";
  _cmcShowProgress(10, `${labelHead} — re-attached, polling status…`);
  try {
    let poll, pollCount = 0;
    while (pollCount < 200) {
      if (_cmcAbortCtrl?.signal.aborted) break;
      await new Promise(r => setTimeout(r, 3000));
      pollCount++;
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`), { signal: _cmcAbortCtrl?.signal });
      if (!pr.ok) throw new Error(`Job poll failed: ${pr.status}`);
      poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      _cmcShowProgress(poll.progress || 0, `${labelHead} — ${poll.progress_note || st}`);
      if (st === "done" || st === "failed" || st === "cancelled") break;
    }
    sessionStorage.removeItem("cmc_active_job");
    _cmcSetCancelVisible(false);
    _cmcHideProgress();
    if (!poll || poll.status === "failed") {
      if (isVariant) {
        const resDiv = document.getElementById(`variant-result-${info.parentJobId}`);
        if (resDiv) resDiv.innerHTML = `<div style="color:var(--fail);font-size:11px">Variant job failed: ${poll?.error || "unknown"}</div>`;
      } else {
        setOutput(errorPanel(poll?.error || "Job failed"));
      }
      return;
    }
    if (poll.status === "cancelled") {
      if (isVariant) {
        const resDiv = document.getElementById(`variant-result-${info.parentJobId}`);
        if (resDiv) resDiv.innerHTML = `<div class="muted" style="font-size:11px">Variant verification cancelled.</div>`;
      } else {
        setOutput(`<div class="muted" style="padding:12px">CMC run cancelled.</div>`);
      }
      return;
    }
    if (isVariant) {
      // Re-render variant comparison using cached baseline
      let baseline = null;
      try { baseline = JSON.parse(info.baseline); } catch {}
      if (!baseline && _lastCmcResult?.result) baseline = {r: _lastCmcResult.result, rb: _lastCmcResult.result.regular_ab_developability || {}};
      if (baseline) {
        const resDiv = document.getElementById(`variant-result-${info.parentJobId}`);
        if (resDiv) resDiv.style.display = "block";
        _renderVariantComparison(info.parentJobId, info.category, info.categoriesUsed || [info.category], info.muts || [], poll.result || {}, baseline.r, baseline.rb);
      }
    } else {
      const svc = (window._currentSection && window._cmcLastService) ? window._cmcLastService : {id:"cmc_igg",label:"IgG CMC"};
      renderCmcIggResult(poll, svc, demoId, sequenceName);
    }
  } catch (err) {
    sessionStorage.removeItem("cmc_active_job");
    _cmcSetCancelVisible(false);
    _cmcHideProgress();
    if (err.name !== "AbortError") {
      if (isVariant) {
        const resDiv = document.getElementById(`variant-result-${info.parentJobId}`);
        if (resDiv) resDiv.innerHTML = `<div style="color:var(--fail);font-size:11px">Error: ${err.message}</div>`;
      } else {
        setOutput(errorPanel(err.message));
      }
    }
  }
}

function renderVhhHumanizationForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="vhh-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Source species</label>
          <select id="vhh-species">
            <option value="alpaca">Alpaca</option>
            <option value="camel">Camel</option>
            <option value="llama">Llama</option>
          </select>
        </div>
        <div class="field"><label>Report format</label>
          <select id="vhh-format">
            <option value="html" selected>HTML only</option>
          </select>
        </div>
        <div class="field full helper" style="margin-top:-4px"><strong>Delivery bundle:</strong> Each job ZIP includes README.txt, FASTA, donor and humanized PDB (when structure is computed), and the HTML report. <strong>Source species</strong> must match the donor VHH origin (alpaca / camel / llama).</div>
        <input type="hidden" id="vhh-strategy" value="auto">
        <div class="field full">
          <label><input type="checkbox" id="vhh-async" checked> Background job (poll status — avoids browser timeout on long structure runs)</label>
        </div>
        <div class="field full"><label>Project / sequence name <span class="muted" style="font-weight:400;font-size:11px">(optional — echoed as <code>sequence_name</code> in job metadata &amp; reports)</span></label><input type="text" id="vhh-name" placeholder="Your project or sequence identifier" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full helper" style="margin-top:-6px;font-size:11px">If left blank, the server uses the <strong>job ID</strong> as the neutral archive label — no auto-generated project titles.</div>
        <div class="field full"><label>VHH sequence</label><textarea id="vhh-seq" placeholder="Paste camelid VHH amino acid sequence…"></textarea></div>
      </div>

      <!-- VHH Run Mode — mirrors VH/VL run mode block -->
      <div style="margin:15px 0;padding:12px;background:rgba(33,199,217,0.08);border:1px solid rgba(33,199,217,0.3);border-radius:8px;">
        <div style="color:var(--accent);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Run Mode</div>
        <div class="helper" style="margin-bottom:8px;">Choose the purpose of this run. The console selects humanization depth and structure QC automatically.
          <strong>Quick vs Standard/Enhanced:</strong> final VHH sequences are <strong>not guaranteed identical</strong> — Standard and Enhanced include structure-informed QC and may activate context-guided refinement; Quick skips structure modeling.</div>
        <div class="form-grid">
          <div class="field full">
            <label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;color:var(--text);">
              <input type="radio" name="vhh-run-mode" id="vhh-run-mode-quick" value="quick_preview" style="width:16px;height:16px;margin-top:2px;" onchange="updateDynamicCost()">
              <span><strong>Quick Preview</strong> <span style="font-size:10px;color:#059669;background:#dcfce7;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #bbf7d0;font-weight:600">12,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top:4px;font-size:11px;color:var(--muted);">
              Fast draft run for input checks and workflow preview. Structure QC is skipped; no pLDDT/CDR RMSD/AbNatiV evidence. Not for final delivery.
            </p>
          </div>
          <div class="field full">
            <label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;color:var(--text);">
              <input type="radio" name="vhh-run-mode" id="vhh-run-mode-standard" value="standard_delivery" checked style="width:16px;height:16px;margin-top:2px;" onchange="updateDynamicCost()">
              <span><strong>Standard Delivery</strong> <span style="font-size:10px;color:#d97706;background:#fef3c7;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #fde68a;font-weight:600">30,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top:4px;font-size:11px;color:var(--muted);">
              Recommended setting. Runs V5.0 dynamic Hallmark selection, NanoBodyBuilder2 structure QC, mini-CMC, HPR Index, and AbNatiV VH/VHH naturalness scoring.
            </p>
          </div>
          <div class="field full">
            <label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;color:var(--text);">
              <input type="radio" name="vhh-run-mode" id="vhh-run-mode-enhanced" value="enhanced_rescue" style="width:16px;height:16px;margin-top:2px;" onchange="updateDynamicCost()">
              <span><strong>Enhanced Rescue Evaluation</strong> <span style="font-size:10px;color:#c026d3;background:#fce7f3;padding:1px 6px;border-radius:4px;margin-left:6px;border:1px solid #fbcfe8;font-weight:600">60,000 Credits</span></span>
            </label>
            <p class="helper" style="margin-top:4px;font-size:11px;color:var(--muted);">
              Use when the standard route is WARN/FAIL or framework compatibility is low. Applies full Hallmark preservation and activates advanced surface humanization routing. Not guaranteed to outperform Standard Delivery.
            </p>
          </div>
        </div>
      </div>

      <div class="button-row" style="flex-wrap:wrap;align-items:center">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run</button>
        <button type="button" class="btn" id="vhh-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="helper" id="vhh-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderRecheckVhhForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Donor + Candidate input (VHH)</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="rchk-vhh-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Source species</label>
          <select id="rchk-vhh-species">
            <option value="alpaca" selected>Alpaca</option>
            <option value="camel">Camel</option>
            <option value="llama">Llama</option>
            <option value="dog">Dog</option>
          </select>
        </div>
        <div class="field"><label>Clean mode</label>
          <select id="rchk-vhh-clean">
            <option value="detect">Detect only</option>
            <option value="suggest">Suggest cleaning</option>
            <option value="auto" selected>Auto clean before scoring</option>
          </select>
        </div>
        <div class="field"><label><input type="checkbox" id="rchk-vhh-struct" checked> Run structure QC</label></div>
        <input type="hidden" id="rchk-vhh-async" value="on">
        <div class="field full"><label>Project / sequence name <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="rchk-vhh-name" placeholder="e.g. VHH-client-recheck-01" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>Donor VHH</label><textarea id="rchk-vhh-donor"></textarea></div>
        <div class="field full"><label>Customer humanized VHH (candidate)</label><textarea id="rchk-vhh-cand"></textarea></div>
      </div>
      <div class="helper" id="rchk-vhh-helper">Runs unified virtual recheck: input QC + cleaning audit + optional structure conservation + mini-CMC + HPR + single-domain naturalness.</div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run VHH Recheck</button>
        <button type="button" class="btn" id="rchk-vhh-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderVhhStructuralForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">VHH structure modeling</div>
      <p style="color:var(--muted);font-size:12px;line-height:1.65;margin-bottom:12px">
        Provide one VHH sequence (demo or text box). The server runs in-silico VHH modeling
        and returns downloadable <code>.pdb</code>. Use this page for quick standalone VHH modeling;
        full VHH humanization / VH→VHH conversion also include structure checks in their pipelines.
      </p>
      <div class="form-grid">
        <div class="field"><label>Demo</label><select id="vhh-struct-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field full"><label>VHH sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label>
          <input type="text" id="vhh-struct-name" placeholder="e.g. VHH-7D12-humanized" maxlength="80" style="font-family:var(--font-mono,monospace)">
        </div>
        <div class="field full"><label>VHH sequence</label><textarea id="vhh-struct-seq" placeholder="Paste VHH amino acid sequence…"></textarea></div>
      </div>
      <div class="panel-label">Workflow</div>
      <p style="font-size:11px;color:var(--muted);line-height:1.6;margin-bottom:8px">
        <strong>Jump to:</strong> optional. <strong>Downstream:</strong> VHH Humanization, VHH Segmentation, or offline AF2 Multimer (complex modeling).
      </p>
      <div class="button-row" style="margin-top:8px">
        <button type="button" class="btn" onclick="activateService('vhh-humanization')">Next: VHH Humanization</button>
        <button type="button" class="btn" onclick="activateService('vhh-segmentation')">VHH Segmentation</button>
        <button type="button" class="btn offline-btn" onclick="activateModule('offline-services')">Offline (AF2 Multimer…)</button>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run ImmuneBuilder (async)</button>
        <button type="button" class="btn" id="vhh-struct-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="helper" id="vhh-struct-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderVhhCmcForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid single">
        <div class="field"><label>Demo case</label><select id="vhh-cmc-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional — appears in report)</span></label><input type="text" id="vhh-cmc-name" placeholder="e.g. VHH-7D12, candidate-03" maxlength="80" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>VHH sequence</label><textarea id="vhh-cmc-seq"></textarea></div>
        <div class="field full">
          <label>sdAb origin / format <span class="muted" style="font-weight:400;font-size:11px">— selects the correct clinical reference panel</span></label>
          <select id="vhh-cmc-origin">
            <option value="camelid_vhh" selected>Humanized VHH — VHH clinical panel [default]</option>
            <option value="engineered_vh">Gene-engineered VH sdAb / HCAb — engineered VH reference</option>
            <option value="transgenic_sdab">Transgenic mouse-derived HCAb — transgenic sdAb / HCAb reference</option>
          </select>
        </div>
          <div class="field full">
            <p class="muted" style="font-size:10px;margin:0">In-silico VHH structure modeling (NanoBodyBuilder2) is always applied. Structure-related parameters (pLDDT, SASA SAP, surface patches psh/ppc/pnc, CDR loop exposure, structural integrity) are automatically included.</p>
          </div>
        <div class="field full">
          <label class="smart-opt-label">
            <input type="checkbox" id="vhh-cmc-smart-opt" onchange="updateCmcCredits()">
            <span style="font-weight:600">Smart-CMC optimization suggestions <span class="muted" style="font-weight:400;font-size:11px">(+3000 credits)</span></span>
          </label>
          <p class="helper" style="margin-top:4px">Enable AI-driven mutation suggestions for VHH developability. Default is assessment only.</p>
        </div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run VHH CMC</button>
        <button type="button" class="btn" id="vhh-cmc-cancel-btn" style="display:none;background:var(--fail);color:white;border-color:var(--fail)" onclick="cancelVhhCmc()">Cancel job</button>
      </div>
      <div class="helper" id="vhh-cmc-helper"></div>
      <div id="vhh-cmc-status" style="margin-top:8px"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderCmcBispecificForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="bs-cmc-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field full"><label>Construct / project name <span class="muted" style="font-weight:400;font-size:11px">(optional — <code>project_name</code> in report)</span></label><input type="text" id="bs-cmc-name" placeholder="e.g. BsAb-2026-01" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field"><label>Linker</label><input type="text" id="bs-cmc-linker" placeholder="(G4S)3"></div>
        <div class="field"><label>Arm 1 target label</label><input type="text" id="bs-cmc-t1" placeholder="Target_A"></div>
        <div class="field"><label>Arm 2 target label</label><input type="text" id="bs-cmc-t2" placeholder="Target_B"></div>
        <div class="field full"><label>VHH arm 1 sequence</label><textarea id="bs-cmc-arm1"></textarea></div>
        <div class="field full"><label>VHH arm 2 sequence</label><textarea id="bs-cmc-arm2"></textarea></div>
        <div class="field full">
          <label>sdAb origin / format <span class="muted" style="font-weight:400;font-size:11px">— selects the clinical reference panel for both arms</span></label>
          <select id="bs-cmc-origin">
            <option value="camelid_vhh" selected>Humanized VHH — VHH clinical panel [default]</option>
            <option value="engineered_vh">Gene-engineered VH sdAb / HCAb — engineered VH reference</option>
            <option value="transgenic_sdab">Transgenic mouse-derived HCAb — transgenic sdAb / HCAb reference</option>
          </select>
        </div>
          <div class="field full">
            <p class="muted" style="font-size:10px;margin:0">In-silico VHH structure modeling (NanoBodyBuilder2) is always applied for both arms. Structure-related parameters (pLDDT, SASA SAP, surface patches psh/ppc/pnc, CDR loop exposure, structural integrity) are automatically included.</p>
          </div>
        <div class="field full">
          <label class="smart-opt-label">
            <input type="checkbox" id="bs-cmc-smart-opt" onchange="updateCmcCredits()">
            <span style="font-weight:600">Smart-CMC optimization suggestions <span class="muted" style="font-weight:400;font-size:11px">(+3000 credits)</span></span>
          </label>
          <p class="helper" style="margin-top:4px">Enable AI-driven mutation suggestions for bispecific VHH arms. Default is assessment only.</p>
        </div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run Bispecific CMC</button>
        <button class="btn" id="bs-cmc-cancel-btn" style="display:none;background:rgba(239,68,68,.12);color:var(--fail);border-color:rgba(239,68,68,.3)" onclick="cancelBsCmc()">Cancel</button>
      </div>
      <div id="bs-cmc-status-bar" style="margin-top:8px"></div>
      <div class="helper" id="bs-cmc-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderBispecificAssemblerForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Design &amp; Format Selection</div>
      <p style="color:var(--muted);font-size:12px;line-height:1.65;margin-bottom:12px">
        Select a bispecific antibody format and provide the binder sequences. This tool will assemble the full FASTA sequences for all required chains (e.g. heavy and light chains for both arms) using standard scaffolds and linkers. No structural or CMC evaluation is performed here; use this to quickly generate sequences for downstream analysis.
      </p>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="bs-assembler-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field full"><label>Construct / project name <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="bs-assembler-name" placeholder="e.g. BsAb-2026-01" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full">
          <label>Bispecific Format</label>
          <select id="bs-assembler-format">
            <option value="crossmab">CrossMab (IgG-like, CH1-CL exchange)</option>
            <option value="kih">Knob-in-Hole (IgG-like, Fc modification only)</option>
            <option value="duetmab">DuetMab / Ortho-Fab (IgG-like, CH1-CL engineered)</option>
            <option value="common_lc">Common Light Chain (IgG-like, single VL)</option>
            <option value="tandem_scfv">Tandem scFv (scFv-like)</option>
            <option value="tandem_vhh">Tandem VHH (sdAb format)</option>
          </select>
        </div>
        <div class="field full">
          <label>Fc Scaffold (for IgG-like formats)</label>
          <select id="bs-assembler-fc">
            <option value="igg1_kih">IgG1 Knob-in-Hole (L234A/L235A silenced)</option>
            <option value="igg4_kih">IgG4 Knob-in-Hole (S228P silenced)</option>
            <option value="igg1_wt">IgG1 Wild-Type (ADCC/CDC active)</option>
            <option value="none">None (Fv/Fab assembly only)</option>
          </select>
        </div>
        <div class="field"><label>Binder A (e.g. anti-CD3) VH</label><textarea id="bs-assembler-vh-a" rows="3" placeholder="Target A Heavy Chain V-region"></textarea></div>
        <div class="field"><label>Binder A (e.g. anti-CD3) VL</label><textarea id="bs-assembler-vl-a" rows="3" placeholder="Target A Light Chain V-region"></textarea></div>
        
        <div class="field"><label>Binder B (e.g. anti-TAA) VH / or VHH 2</label><textarea id="bs-assembler-vh-b" rows="3" placeholder="Target B Heavy Chain V-region (or 2nd VHH)"></textarea></div>
        <div class="field"><label>Binder B (e.g. anti-TAA) VL</label><textarea id="bs-assembler-vl-b" rows="3" placeholder="Target B Light Chain V-region (leave blank for Common LC or VHH)"></textarea></div>
        <div class="field full">
          <label>Electrostatic Steering (for IgG-like)</label>
          <select id="bs-assembler-steering">
            <option value="none">None</option>
            <option value="vh_vl_interface">VH/VL Interface Charge Mutations (e.g. Q39E in VH-A, Q38K in VL-B)</option>
          </select>
        </div>
      </div>
      
      <div class="button-row" style="margin-top:14px;flex-wrap:wrap;align-items:center">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Assemble Sequences</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderBispecificAnalyzerForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Pairing QA &amp; CMC Input</div>
      <p style="color:var(--muted);font-size:12px;line-height:1.65;margin-bottom:12px">
        Provide the assembled chains or binders for your bispecific candidate. The system will evaluate the 4 possible Fv pairings (using ImmuneBuilder + p-AbNatiV + Charge Asymmetry) to calculate a Pairing Selectivity Index (PSI) and return a comprehensive CMC report, allowing you to gauge the risk of chain mispairing before costly expression runs.
      </p>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="bs-analyzer-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field full"><label>Construct / project name <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="bs-analyzer-name" placeholder="e.g. BsAb-2026-01" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field"><label>Binder A VH</label><textarea id="bs-analyzer-vh-a" rows="3"></textarea></div>
        <div class="field"><label>Binder A VL</label><textarea id="bs-analyzer-vl-a" rows="3"></textarea></div>
        
        <div class="field"><label>Binder B VH</label><textarea id="bs-analyzer-vh-b" rows="3"></textarea></div>
        <div class="field"><label>Binder B VL</label><textarea id="bs-analyzer-vl-b" rows="3"></textarea></div>
      </div>
      
      <div class="button-row" style="margin-top:14px;flex-wrap:wrap;align-items:center">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run Bispecific Analyzer (Async)</button>
        <button type="button" class="btn" id="bs-analyzer-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderVhToVhhForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div style="background:var(--panel-2); border:1px solid var(--line-2); padding:10px 12px; border-radius:6px; margin-bottom:15px; font-size:11.5px; color:var(--text); line-height:1.5;">
        <strong style="color:var(--warn)">Domain Restriction:</strong> The VH to VHH conversion algorithm is restricted to the <strong>IGHV3 family (Human or Murine)</strong>, as natural VHHs are evolutionarily derived from IGHV3. Sequences from other structural families (e.g., IGHV1, IGHV4) exhibit severe framework mismatch and are rejected by the pre-flight check.
        <div style="margin-top:8px;color:var(--muted);font-size:11px;"><strong>Versioning:</strong> Algorithm standard <strong>V1.8.17</strong>. This Console path runs deployment branch <strong>V1.8.17.IGHV3</strong> — same standard rules plus the IGHV3-family gateway on conversion endpoints.</div>
      </div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="vh2vhh-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Source class</label>
          <select id="vh2vhh-source" onchange="syncVh2VhhSourceToDemo(); updateVh2VhhSourceNote()">
            <option value="human_mab">Humanized / Human mAb VH</option>
            <option value="murine_mab">Murine VH (conventional mouse mAb)</option>
          </select>
        </div>
        <div class="field full" id="vh2vhh-source-note" style="display:none"></div>
        <div class="field full">
          <label><input type="checkbox" id="vh2vhh-async" checked> Background job (poll status — avoids browser timeout on long structure runs)</label>
        </div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional — appears in report)</span></label><input type="text" id="vh2vhh-name" placeholder="e.g. anti-PD-1-VH, clone-A05-VH" maxlength="80" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>VH sequence <span class="muted" style="font-weight:400;font-size:11px">(VH domain — scFv auto-detected if linker present)</span></label><textarea id="vh2vhh-seq" placeholder="Paste VH amino acid sequence here…"></textarea></div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run VH&#8594;VHH Analysis</button>
        <button type="button" class="btn" id="vh2vhh-cancel-btn" style="display:none" onclick="cancelActiveAsyncJob()">Cancel job</button>
      </div>
      <div class="helper" id="vh2vhh-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}


const VH2VHH_SOURCE_NOTES = {
  human_mab: {
    color: "#2563eb", darkColor: "#60a5fa", bg: "rgba(59,130,246,0.06)", border: "rgba(59,130,246,0.25)",
    icon: "🔵",
    title: "Path C1 — Framework-preserving camelization",
    body: "Human / humanized VH with intact IGHV framework. Proprietary framework-zone mutations are applied to convert the VH-VL interface to a single-domain-compatible surface. Lowest risk path — germline similarity is high and immunogenicity baseline is low.",
    vam: "medium", vamColor: "#b56300",
    tip: "Verify CDR conformation (RMSD) post-conversion. VAM recommended if binding Kd > 10 nM."
  },
  murine_mab: {
    color: "#7c3aed", darkColor: "#a78bfa", bg: "rgba(124,58,237,0.06)", border: "rgba(124,58,237,0.25)",
    icon: "🐭",
    title: "Path C2 — Dual engineering: humanization + camelization",
    body: "Murine VH requires two sequential engineering phases: (1) FR humanization by CDR-weighted IGHV graft, then (2) Hallmark/Stealth camelization. CDR-FR junctions and Vernier zones should be validated after grafting.",
    vam: "medium", vamColor: "#b56300",
    tip: "Ensure CDR preservation after FR graft. Run structural QC on both the humanized and camelized intermediates."
  },
};

function updateVh2VhhSourceNote() {
  const sel = document.getElementById("vh2vhh-source");
  const panel = document.getElementById("vh2vhh-source-note");
  if (!sel || !panel) return;
  const note = VH2VHH_SOURCE_NOTES[sel.value];
  if (!note) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  const isDark = document.documentElement.classList.contains("theme-dark");
  const titleColor = isDark ? note.darkColor : note.color;
  panel.innerHTML = `
    <div style="background:${note.bg};border:1px solid ${note.border};border-radius:6px;padding:10px 13px">
      <div style="font-size:12px;font-weight:700;color:${titleColor};margin-bottom:5px">${note.icon} ${note.title}</div>
      <div style="font-size:11px;color:var(--text);opacity:0.85;line-height:1.55;margin-bottom:6px">${note.body}</div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <span style="font-size:10px;font-weight:700;color:var(--muted)">VAM PRIORITY</span>
        <span style="font-size:11px;font-weight:700;color:${note.vamColor}">${note.vam.toUpperCase()}</span>
      </div>
      <div style="font-size:11px;color:var(--muted);line-height:1.4">💡 ${note.tip}</div>
    </div>`;
}

function renderSegmentationVhvlForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="seg-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Numbering scheme</label>
          <select id="seg-scheme">
            <option value="imgt" selected>IMGT — default (interop, databases)</option>
            <option value="kabat">Kabat — literature / legacy (server = real ANARCI)</option>
            <option value="chothia">Chothia — structure / PDB (server = real ANARCI)</option>
          </select>
        </div>
        <div class="field full" id="seg-server-row">
          <label><input type="checkbox" id="seg-use-server" checked> <strong>Server numbering</strong> (IMGT / Kabat / Chothia). Off = IMGT heuristic only.</label>
        </div>
        <div class="field"><label title="Does not change CDR/FR boundaries — only which IMGT V-gene library is used for closest-match">V-gene library species</label>
          <select id="seg-species">
            <option value="mouse" selected>Mouse</option>
            <option value="human">Human</option>
            <option value="rat">Rat</option>
            <option value="rabbit">Rabbit</option>
          </select>
        </div>
        <div class="field full">
          <label><input type="checkbox" id="seg-no-germline"> Skip V-gene lookup (still runs numbering / segmentation)</label>
        </div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="seg-name" placeholder="e.g. Ab001, clone-12" maxlength="80" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>VH sequence</label><textarea id="seg-vh"></textarea></div>
        <div class="field full"><label>VL sequence</label><textarea id="seg-vl"></textarea></div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run Segmentation</button>
      </div>
      <div class="helper" id="seg-helper">CDR/FR boundaries depend on numbering scheme and VH/VL sequence only. V-gene library species sets closest V-gene label and identity %, not CDR/FR borders. <strong>Demo load:</strong> fills sequences and aligns library species with demo metadata.</div>
      <div class="panel-label" style="margin-top:14px">Workflow</div>
      <p style="font-size:11px;color:var(--muted);line-height:1.6;margin-bottom:8px">
        Same shortcuts as Structure (Fv). <strong>Demo load:</strong> stores donor species for <strong>Next: VH/VL Humanization</strong> (mouse / rat). Segmentation does not invoke a humanization program — numbering is sequence-only.
      </p>
      <div class="button-row">
        <button type="button" class="btn primary" onclick="activateHumanizationFromLastDonor()">Next: VH/VL Humanization (auto route)</button>
        <button type="button" class="btn" onclick="activateService('fv-structural')">Structure (Fv)</button>
      </div>
      ${pdbViewerLinksHtml()}
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderVhhSegmentationForm(service) {
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="vhh-seg-demo" onchange="loadServiceDemo()"></select></div>
        <div class="field"><label>Numbering scheme</label>
          <select id="vhh-seg-scheme">
            <option value="imgt" selected>IMGT — default (interop, databases)</option>
            <option value="kabat">Kabat — literature / legacy (server = real ANARCI)</option>
            <option value="chothia">Chothia — structure / PDB (server = real ANARCI)</option>
          </select>
        </div>
        <div class="field full">
          <label><input type="checkbox" id="vhh-seg-use-server" checked> <strong>Server numbering</strong> (IMGT / Kabat / Chothia). Off = IMGT heuristic only (browser).</label>
        </div>
        <div class="field"><label title="Does not change CDR/FR cuts — only which IMGT IGHV aa library is scanned for closest-match. Camelid: one Vicugna library (same backend for alpaca/camel/llama). Human/mouse/rabbit: optional references for humanized or engineered contexts.">V-gene library species</label>
          <select id="vhh-seg-species">
            <optgroup label="Camelid VHH (default)">
              <option value="alpaca" selected>Camelid (Vicugna) — natural nanobody</option>
            </optgroup>
            <optgroup label="Human / rodent / lagomorph (reference)">
              <option value="human">Human (IGHV · humanization / chimeric)</option>
              <option value="mouse">Mouse (murine VH context)</option>
              <option value="rabbit">Rabbit</option>
            </optgroup>
          </select>
        </div>
        <div class="field full">
          <label><input type="checkbox" id="vhh-seg-no-germline"> Skip V-gene lookup (still runs numbering / segmentation)</label>
        </div>
        <div class="field full"><label>Sequence name / ID <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label><input type="text" id="vhh-seg-name" placeholder="e.g. VHH-7D12, candidate-01" maxlength="80" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>VHH sequence</label><textarea id="vhh-seg-seq"></textarea></div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run VHH Segmentation</button>
      </div>
      <div class="helper" id="vhh-seg-helper">CDR/FR boundaries depend on numbering scheme and sequence only. Species selects the IGHV library for closest-match — default <strong>Camelid (Vicugna)</strong> for typical VHH; Human/Mouse/Rabbit are alternate reference libraries. <strong>Demo load:</strong> applies sequence and Camelid default when the demo specifies camelid.</div>
      <div class="panel-label" style="margin-top:14px">Workflow</div>
      <p style="font-size:11px;color:var(--muted);line-height:1.6;margin-bottom:8px">
        Same scope as VH/VL Segmentation (optional server Kabat/Chothia). <strong>Demo load:</strong> sets source species for <strong>Next: VHH Humanization</strong> when present in demo metadata.
      </p>
      <div class="button-row">
        <button type="button" class="btn primary" onclick="activateService('vhh-humanization')">Next: VHH Humanization</button>
      </div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function renderCdnaOptimizationForm(service) {
  const isVhh = service.chainType === "vhh";
  const hostOptions = isVhh
    ? `<option value="hek293">HEK293</option><option value="cho">CHO</option><option value="yeast">Yeast (P. pastoris)</option><option value="ecoli">E. coli (periplasm)</option>`
    : `<option value="cho">CHO (default)</option><option value="hek293">HEK293</option><option value="yeast">Yeast (P. pastoris)</option><option value="ecoli">E. coli (periplasm)</option>`;

  const assemblyBlock = isVhh
    ? `
      <div class="field full">
        <label><input type="checkbox" id="cdna-vhh-assembly" checked onchange="toggleCdnaVhhAssembly()"> Assemble VHH construct (signal peptide + optional fusion / tag), then codon-optimize</label>
      </div>
      <div id="cdna-vhh-opts" class="form-grid" style="margin-top:8px;display:grid">
        <div class="field"><label>Signal peptide (N-term)</label>
          <select id="cdna-vhh-sp" onchange="onVhhSpChange()">
            <option value="none" selected>None (mature VHH only)</option>
            <option value="human_ig">Human Ig signal (22 aa)</option>
            <option value="tpa">Human tPA (23 aa) — PS suffix</option>
            <option value="tpa_short">Human tPA (21 aa) — VS suffix</option>
            <option value="ompa">E. coli OmpA (21 aa) — periplasm</option>
            <option value="pelb">E. coli PelB (22 aa) — periplasm</option>
            <option value="custom">Custom (paste below)</option>
          </select>
        </div>
        <div class="field"><label>C-terminal Fusion</label>
          <select id="cdna-vhh-fusion" onchange="onVhhFusionChange()">
            <option value="none" selected>None (VHH only)</option>
            <option value="igg1_fc">Human IgG1 Fc (CH2-CH3)</option>
            <option value="igg1_fch">Human IgG1 Fc (hinge+CH2-CH3)</option>
            <option value="igg4_fc">Human IgG4 Fc (CH2-CH3)</option>
            <option value="igg4_fch">Human IgG4 Fc (hinge+CH2-CH3)</option>
            <option value="hsa">Anti-HSA VHH (ALB8)</option>
          </select>
        </div>
        <div class="field" id="cdna-vhh-orient-row"><label>VHH/ALB8 orientation</label>
          <select id="cdna-vhh-orient" onchange="onVhhOrientChange()">
            <option value="vhh_fusion" selected>VHH-ALB8 (VHH in front)</option>
            <option value="fusion_vhh">ALB8-VHH (ALB8 in front)</option>
          </select>
        </div>
        <div class="field"><label>C-terminal Tag</label>
          <select id="cdna-vhh-tag" onchange="onVhhTagChange()">
            <option value="none">None</option>
            <option value="his6" selected>6xHis (HHHHHH)</option>
            <option value="his8">8xHis (HHHHHHHH)</option>
            <option value="flag">FLAG (DYKDDDDK)</option>
            <option value="strep2">Strep-II (WSHPQFEK)</option>
            <option value="myc">c-Myc (EQKLISEEDL)</option>
            <option value="epea">C-tag (EPEA)</option>
          </select>
        </div>
        <div class="field full" id="cdna-vhh-sp-custom-row" style="display:none"><label>Custom signal peptide (aa)</label><textarea id="cdna-vhh-sp-custom" rows="2" placeholder="Single-letter amino acids"></textarea></div>
        <div class="field" id="cdna-vhh-cleavage-row" style="display:none"><label>Protease site (before terminal addon)</label>
          <select id="cdna-vhh-cleavage">
            <option value="none" selected>None (direct fusion)</option>
            <option value="tev">TEV site (ENLYFQG)</option>
            <option value="ek">Enterokinase (DDDDK)</option>
            <option value="hrv3c">HRV 3C / PreScission (LEVLFQGP)</option>
          </select>
        </div>
        <div class="field" id="cdna-vhh-linker-row" style="display:none"><label>Linker (between VHH and Site/Fusion)</label>
          <select id="cdna-vhh-linker">
            <option value="gs10">(GGGGS)2 — 10 aa</option>
            <option value="gs15" selected>(GGGGS)3 — 15 aa</option>
            <option value="gs20">(GGGGS)4 — 20 aa</option>
            <option value="none">None</option>
          </select>
        </div>
      </div>
      <p id="cdna-vhh-note" class="helper" style="margin-top:6px;display:block">
        VHH construct order: <strong>SP · (VHH · [Linker] · [Fusion] / [Fusion] · [Linker] · VHH) · [Protease Site] · [Tag]</strong>.
        Fc fusions use human IMGT *01 reference sequences. ALB8 follows the clinical-grade anti-HSA VHH sequence (PDB 8Z8V).
      </p>
    `
    : `
      <div class="field full">
        <label><input type="checkbox" id="cdna-full-igg" checked onchange="toggleCdnaIggAssembly()"> Assemble full IgG (signal peptide + human CH1 / hinge / CH2 / CH3 on HC; κ or λ CL on LC), then codon-optimize</label>
      </div>
      <div id="cdna-igg-opts" class="form-grid" style="margin-top:8px">
        <div class="field"><label>HC signal peptide</label>
          <select id="cdna-sp-hc">
            <option value="hc_md" selected>Human Ig HC (default, 22 aa)</option>
            <option value="hc_mef">Alternative HC signal (18 aa)</option>
            <option value="none">None (mature chain only)</option>
            <option value="custom">Custom (paste below)</option>
          </select>
        </div>
        <div class="field"><label>LC signal peptide</label>
          <select id="cdna-sp-lc">
            <option value="lc_md" selected>Human κ LC (default, 22 aa)</option>
            <option value="lc_met">Alternative LC signal (20 aa)</option>
            <option value="none">None (mature chain only)</option>
            <option value="custom">Custom (paste below)</option>
          </select>
        </div>
        <div class="field full"><label>Custom HC signal (aa)</label><textarea id="cdna-sp-hc-custom" rows="2" placeholder="Only if HC signal = Custom; single-letter amino acids"></textarea></div>
        <div class="field full"><label>Custom LC signal (aa)</label><textarea id="cdna-sp-lc-custom" rows="2" placeholder="Only if LC signal = Custom"></textarea></div>
        <div class="field"><label>Heavy chain: human Fc / hinge</label>
          <select id="cdna-fc">
            <optgroup label="Human wild-type (IMGT *01 reference)">
              <option value="igg1" selected>IgG1 — IGHG1*01 CH1+H+CH2+CH3</option>
              <option value="igg2">IgG2 — IGHG2*01 CH1+H+CH2+CH3</option>
              <option value="igg4">IgG4 — IGHG4*01 CH1+H+CH2+CH3</option>
            </optgroup>
            <optgroup label="Engineered Fc — common, widely published (verify FTO / locked CMC)">
              <option value="igg1_lala">IgG1 LALA-style — FcγR-silencing (CH2: PEVTCAAVDV motif, ref. literature)</option>
              <option value="igg1_yte">IgG1 YTE — half-life (M252Y/S254T/T256E on *01 CH2 spine)</option>
              <option value="igg4_s228p">IgG4 S228P — hinge Ser→Pro (Fab-arm exchange–related context)</option>
            </optgroup>
          </select>
        </div>
        <div class="field"><label>Light chain constant</label>
          <select id="cdna-cl">
            <option value="kappa" selected>κ — IGKC*01 (107 aa)</option>
            <option value="lambda2">λ — IGLC2*01 (106 aa)</option>
          </select>
        </div>
      </div>
      <p id="cdna-igg-note" class="helper" style="margin-top:6px">
        Heavy chain order: <strong>SP · VH · CH1 · hinge · CH2 · CH3</strong>. Light chain: <strong>SP · VL · CL</strong>.
        Wild-type rows follow <strong>human IMGT *01</strong> (repository <code>data/germlines/…/IGHC_aa.fasta</code>).
        <strong>Engineered Fc</strong> rows apply commonly published residue changes on that spine for expression preview;
        patent landscape varies by jurisdiction and year — <strong>confirm FTO and match your locked cell-bank sequence</strong> before synthesis.
      </p>
    `;
  return `
    <section class="surface panel">
      <div class="panel-label">Demo &amp; Input</div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label><select id="cdna-demo"></select></div>
        <div class="field"><label>Expression host</label><select id="cdna-host">${hostOptions}</select></div>
        <div class="field full"><label>Sequence / construct name <span class="muted" style="font-weight:400;font-size:11px">(optional — appears in report)</span></label><input type="text" id="cdna-name" placeholder="e.g. pHC-001, GMP-batch-ref" maxlength="120" style="font-family:var(--font-mono,monospace)"></div>
        <div class="field full"><label>${isVhh ? "VHH" : "VH"} sequence</label><textarea id="cdna-seq"></textarea></div>
        ${isVhh ? "" : `<div class="field full"><label>VL sequence</label><textarea id="cdna-vl"></textarea></div>`}
      </div>
      ${assemblyBlock}
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        ${isVhh
          ? `<button type="button" class="btn" onclick="fillCdnaVhhFromLastHumanization()">Use last humanized VHH</button>`
          : `<button type="button" class="btn" onclick="fillCdnaIggFromLastHumanization()">Use last humanized VH/VL</button>`}
        <button class="btn primary" onclick="runCurrentService()">Optimize cDNA</button>
      </div>
      <p class="helper" style="margin-top:10px;line-height:1.5;border-left:3px solid rgba(148,163,184,.45);padding-left:10px">
        <strong>Restriction enzymes / cloning:</strong> this step does <strong>not</strong> scan for conventional Type&nbsp;II RE sites (e.g. NcoI, NotI), remove sites by synonymous design, or output a vector/MCS cut map — <em>no RE-based pass/fail</em>. Use your cloning software and manufacturing map for subcloning.
      </p>
      <p class="helper" style="margin-top:8px;line-height:1.5;border-left:3px solid rgba(34,197,94,.35);padding-left:10px">
        <strong>Optimization vs what baseline?</strong> There is <strong>no upload of your legacy / unoptimized DNA</strong> here. CAI, rare-codon count, and CpG are computed on the <strong>output sequence only</strong>, relative to the selected host’s Kazusa reference — orientation metrics, not an A/B versus your existing construct. To compare two DNAs (old vs new), run the same metrics offline on both or use your vector-design workflow.
      </p>
      <div class="helper" id="cdna-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

function toggleCdnaIggAssembly() {
  const cb = document.getElementById("cdna-full-igg");
  if (!cb) return;
  const on = cb.checked;
  const row = document.getElementById("cdna-igg-opts");
  const note = document.getElementById("cdna-igg-note");
  if (row) row.style.display = on ? "grid" : "none";
  if (note) note.style.display = on ? "block" : "none";
}

function toggleCdnaVhhAssembly() {
  const cb = document.getElementById("cdna-vhh-assembly");
  if (!cb) return;
  const on = cb.checked;
  const row = document.getElementById("cdna-vhh-opts");
  const note = document.getElementById("cdna-vhh-note");
  if (row) row.style.display = on ? "grid" : "none";
  if (note) note.style.display = on ? "block" : "none";
  if (on) {
    onVhhSpChange();
    updateVhhAddonRows();
  }
}

function onVhhSpChange() {
  const sel = document.getElementById("cdna-vhh-sp");
  const row = document.getElementById("cdna-vhh-sp-custom-row");
  if (sel && row) row.style.display = sel.value === "custom" ? "block" : "none";
}

function onVhhFusionChange() {
  enforceVhhFusionTagExclusion("fusion");
  updateVhhAddonRows();
}

function onVhhTagChange() {
  enforceVhhFusionTagExclusion("tag");
  updateVhhAddonRows();
}

function onVhhOrientChange() {
  updateVhhAddonRows();
}

function isFcFusionKey(v) {
  return v === "igg1_fc" || v === "igg1_fch" || v === "igg4_fc" || v === "igg4_fch";
}

function enforceVhhFusionTagExclusion(changedBy) {
  const fusionSel = document.getElementById("cdna-vhh-fusion");
  const tagSel = document.getElementById("cdna-vhh-tag");
  if (!fusionSel || !tagSel) return;
  const fusionVal = fusionSel.value || "none";
  const tagVal = tagSel.value || "none";
  if (changedBy === "fusion" && isFcFusionKey(fusionVal) && tagVal !== "none") {
    tagSel.value = "none";
  }
  if (changedBy === "tag" && tagVal !== "none" && isFcFusionKey(fusionVal)) {
    fusionSel.value = "none";
  }
}

function updateVhhAddonRows() {
  const rowLinker = document.getElementById("cdna-vhh-linker-row");
  const rowCleavage = document.getElementById("cdna-vhh-cleavage-row");
  const fusionSel = document.getElementById("cdna-vhh-fusion");
  const orientSel = document.getElementById("cdna-vhh-orient");
  const tagSel = document.getElementById("cdna-vhh-tag");
  const hasFusion = fusionSel && fusionSel.value !== "none";
  const isFcFusion = fusionSel && isFcFusionKey(fusionSel.value);
  const isHsaFusion = fusionSel && fusionSel.value === "hsa";
  if (tagSel) {
    if (isFcFusion && tagSel.value !== "none") tagSel.value = "none";
    tagSel.disabled = !!isFcFusion;
  }
  const on = hasFusion || (tagSel && tagSel.value !== "none");
  const cb = document.getElementById("cdna-vhh-assembly");
  if (on && cb && !cb.checked) {
    cb.checked = true;
    toggleCdnaVhhAssembly();
  }
  if (rowLinker) rowLinker.style.display = on ? "block" : "none";
  if (rowCleavage) rowCleavage.style.display = on ? "block" : "none";
  if (orientSel) orientSel.disabled = !isHsaFusion;
}

function renderOfflineRequestForm(service) {
  const scopeItems = (service.scope || []).map(s => `<span class="scope-chip">${s}</span>`).join("");
  const isSequenceService = ["af2-multimer", "haddock-peptide"].includes(state.service);
  const af2SeqBlock = isSequenceService
    ? `
      <div class="panel-label" style="margin-top:14px">${state.service === "af2-multimer" ? "AF2 Multimer" : "HADDOCK Short Peptide"} — sequences (required)</div>
      <p style="font-size:11px;color:var(--muted);line-height:1.65;margin-bottom:10px">
        <strong>Offline submission</strong> — there is no demo sequence; paste your own constructs or upload FASTA. 
        ${state.service === "af2-multimer" 
          ? "For soluble complex modeling, the antigen should be specified as the <strong>extracellular domain (ECD)</strong>. Full-length receptors are usually <strong>trimmed to ECD</strong>."
          : "For short peptides (≤30 aa), HADDOCK3 can perform ab-initio docking. Provide the peptide sequence and antibody Fv/VHH sequences below."}
      </p>
      <div class="form-grid">
        <div class="field full">
          <label>Antigen — ECD amino acid sequence</label>
          <textarea id="af2-antigen-ecd" rows="4" placeholder="Single-letter AA; ECD only (recommended). State domain boundaries in notes below if known."></textarea>
        </div>
        <div class="field full">
          <label>Antibody chain type</label>
          <select id="af2-ab-mode" onchange="onAf2AbModeChange()">
            <option value="vh_vl">Conventional Fv — VH + VL (IgG-style)</option>
            <option value="vhh">Nanobody — VHH (single domain)</option>
          </select>
        </div>
        <div class="field full">
          <label><input type="checkbox" id="af2-post-humanization"> Antibody sequences above are <strong>humanized outputs</strong> intended for <strong>antigen complex modeling</strong> (post-humanization offline step)</label>
        </div>
        <div class="field full">
          <button type="button" class="btn" onclick="fillAf2AntibodyFromLastHumanization()">Fill antibody from last humanization result (VH/VL or VHH, this browser)</button>
        </div>
        <div id="af2-rows-vhvl" class="field-full-group">
          <div class="field full">
            <label>Antibody — VH</label>
            <textarea id="af2-antibody-vh" rows="3" placeholder="Heavy chain variable region (Fv)"></textarea>
          </div>
          <div class="field full">
            <label>Antibody — VL</label>
            <textarea id="af2-antibody-vl" rows="3" placeholder="Light chain variable region (Fv)"></textarea>
          </div>
        </div>
        <div id="af2-rows-vhh" class="field-full-group" style="display:none">
          <div class="field full">
            <label>Antibody — VHH</label>
            <textarea id="af2-antibody-vhh" rows="4" placeholder="Single-domain VHH (camelid / nanobody)"></textarea>
          </div>
        </div>
        <div class="field full">
          <label>Antigen construct / linker / TM handling (optional)</label>
          <textarea id="af2-construct-notes" rows="2" placeholder="e.g. EGFR ECD aa 25-638; TM replaced by (G4S)3 between ECD and stub…"></textarea>
        </div>
        <div class="field full">
          <label>Optional GS linker sequence (if you splice domains)</label>
          <input type="text" id="af2-gs-linker" placeholder="e.g. GGGGSGGGGSGGGGS (or leave empty)">
        </div>
        <div class="field full">
          <label><input type="checkbox" id="af2-gs-replace-tm"> I am replacing / bridging a TM segment with the GS linker above (describe in construct notes)</label>
        </div>
        <div class="field full">
          <label><input type="checkbox" id="af2-use-upload-only"> Submit using <strong>uploaded FASTA only</strong> (ignore pasted antigen / antibody fields)</label>
        </div>
        <div class="field full">
          <label>Upload multi-chain FASTA (ColabFold / AF2 multimer style)</label>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <label for="af2-fasta-file" class="btn" style="margin:0">Choose FASTA File</label>
            <span id="af2-fasta-file-name" class="muted" style="font-size:12px">No file selected</span>
          </div>
          <input type="file" id="af2-fasta-file" accept=".fa,.fasta,.faa,.txt,.seq" onchange="onAf2MultimerFastaFile(event)" style="position:absolute;left:-9999px;opacity:0;pointer-events:none">
        </div>
        <div class="field full">
          <label>ColabFold-style FASTA preview (one <code>&gt;header</code> per chain; VH/VL: antigen_ECD + antibody_VH + antibody_VL; VHH: antigen_ECD + antibody_VHH)</label>
          <textarea id="af2-fasta-preview" rows="12" class="mono" style="font-size:11px" placeholder="Paste or upload multi-chain FASTA, or use Build FASTA from pasted sequences."></textarea>
        </div>
      </div>
      <div class="button-row">
        <button type="button" class="btn" onclick="buildAf2MultimerFastaPreview()">Build FASTA from pasted sequences</button>
      </div>
      <div class="helper" style="margin-top:12px">
        <strong>Format</strong>: standard FASTA — multiple records; each <code>&gt;title</code> followed by one sequence (one letter per AA). This matches typical ColabFold / AlphaFold-Multimer batch input. After upload, preview is normalized to this layout.
      </div>
    `
    : "";
  return `
    <section class="surface panel">
      <div class="panel-label">Project Scope</div>
      <div class="offline-scope-card">
        <h4>${service.label}</h4>
        <p>${service.description}</p>
        <div class="scope-chips">${scopeItems}</div>
      </div>
      ${af2SeqBlock}
      <div style="margin-top:16px">
        <div class="panel-label">Submit Request</div>
        <div class="form-grid">
          <div class="field"><label>Your name</label><input type="text" id="offline-name" placeholder="Dr. Li, etc."></div>
          <div class="field"><label>Organization</label><input type="text" id="offline-org" placeholder="InSynBio / Client org"></div>
          <div class="field full"><label>Email address</label><input type="email" id="offline-email" placeholder="name@example.com"></div>
          <div class="field full"><label>Target / antigen context</label><input type="text" id="offline-target" placeholder="e.g. EGFR ECD, CD20, PD-L1"></div>
          <div class="field full"><label>Project description &amp; deliverables expected</label><textarea id="offline-desc"></textarea></div>
          <div class="field"><label>Estimated timeline</label>
            <select id="offline-timeline">
              <option value="2w">2 weeks</option>
              <option value="1m">1 month</option>
              <option value="flexible">Flexible</option>
            </select>
          </div>
        </div>
        <div class="button-row">
          <button class="btn offline-btn" onclick="submitOfflineRequest('${service.label}')">Submit Offline Request</button>
        </div>
      </div>
      <div class="helper">Offline requests are reviewed within 1 business day. A project scoping call will be scheduled with the InSynBio team.</div>
    </section>
    <section class="surface panel" style="margin-top:0">
      <div class="panel-label">Analysis Version (Offline)</div>
      <div class="method-grid">
        <div class="method-card"><div class="k">Service</div><div class="v">${service.label}</div></div>
        <div class="method-card"><div class="k">Analysis Version</div><div class="v mono">${service.analysisVersion}</div></div>
        <div class="method-card"><div class="k">Underlying Standard</div><div class="v mono">${service.underlyingStandard}</div></div>
        <div class="method-card"><div class="k">Billing</div><div class="v">Custom Quote</div></div>
      </div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

// ── Hydration ─────────────────────────────────────────────────────────────────

function hydrateService(service) {
  const runners = {
    "vhvl": () => {
      fillDemoSelect("vhvl-demo", service.demos);
      if (state.pendingVhvlSpecies) {
        const vd = document.getElementById("vhvl-demo");
        if (vd) vd.value = pickVhvlDemoIdForSpecies(state.pendingVhvlSpecies);
        state.pendingVhvlSpecies = null;
      }
      loadServiceDemo();
    },
    "recheck-vhvl": () => { fillDemoSelect("rchk-vhvl-demo", service.demos); loadServiceDemo(); },
    "structural-vhvl": () => { fillDemoSelect("fv-demo", service.demos); loadServiceDemo(); },
    "cmc-igg": () => {
      fillDemoSelect("cmc-demo", service.demos); loadServiceDemo(); updateCmcCredits();
      // Re-attach if a job was running before navigation
      setTimeout(cmcCheckResumeJob, 100);
    },
    "vhh-humanization": () => { fillDemoSelect("vhh-demo", service.demos); loadServiceDemo(); },
    "recheck-vhh": () => { fillDemoSelect("rchk-vhh-demo", service.demos); loadServiceDemo(); },
    "vhh-structural": () => { fillDemoSelect("vhh-struct-demo", service.demos); loadServiceDemo(); },
    "cmc-vhh": () => { fillDemoSelect("vhh-cmc-demo", service.demos); loadServiceDemo(); updateCmcCredits(); },
    "vh-to-vhh": () => { fillDemoSelect("vh2vhh-demo", service.demos); loadServiceDemo(); updateVh2VhhSourceNote(); },
    "segmentation-vhvl": () => { 
      fillDemoSelect("seg-demo", service.demos); 
      if (state.pendingDemo) {
        const sd = document.getElementById("seg-demo");
        if (sd) sd.value = state.pendingDemo;
        state.pendingDemo = null;
      }
      loadServiceDemo(); 
    },
    "vhh-segmentation": () => { fillDemoSelect("vhh-seg-demo", service.demos); loadServiceDemo(); },
    "cdna-optimization": () => {
      fillDemoSelect("cdna-demo", service.demos);
      loadServiceDemo();
      if (typeof toggleCdnaIggAssembly === "function") toggleCdnaIggAssembly();
    },
    "cmc-bispecific": () => { fillDemoSelect("bs-cmc-demo", service.demos); loadServiceDemo(); updateCmcCredits(); },
    "bispecific-assembler": () => { fillDemoSelect("bs-assembler-demo", service.demos); loadServiceDemo(); },
    "bispecific-analyzer": () => { fillDemoSelect("bs-analyzer-demo", service.demos); loadServiceDemo(); },
  };
  const fn = runners[service.runner];
  if (fn) fn();
  updateDynamicCost();
  
  // Populate immediately
  const didPopulate = populateSharedSequences();
  
  // Defeat browser autofill/BFCache change events that might overwrite our populated text
  setTimeout(() => {
    populateSharedSequences();
    if (didPopulate) clearSharedSequences();
  }, 100);
}

function fillDemoSelect(id, demoIds) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = demoIds.map(demoId => `<option value="${demoId}">${DEMOS[demoId].label}</option>`).join("");
}

function cmcOriginLabel(value) {
  return {
    humanized: "Humanized / engineered (gene-engineered)",
    humanized_transgenic: "Fully human (transgenic mouse platform)",
    fully_human: "Fully human (transgenic mouse platform)",  // legacy alias
    phage_display: "Fully human (phage display)",
    b_cell_derived: "B-cell derived (human B cells)",
  }[value] || "Not specified";
}

function updateCmcOriginNote() {
  const originEl = document.getElementById("cmc-antibody-type");
  const note = document.getElementById("cmc-origin-note");
  if (!originEl || !note) return;
  const origin = originEl.value;
  if (origin === "b_cell_derived") {
    note.innerHTML = `Sequence source selected: <strong>B-cell derived (human B cells)</strong>. CMC developability assessment proceeds normally. <strong>Immunogenicity (ADA) testing is not required</strong> for antibodies derived from human B cells — FDA/EMA guidelines do not mandate ADA monitoring for this origin class.`;
  } else {
    note.innerHTML = `Sequence source selected: <strong>${cmcOriginLabel(origin)}</strong>. Customer-submitted VH/VL sequences must declare this origin before CMC review.`;
  }
}

/** Demo id → canonical VH/VL humanization entry (Regular module). */
const VHVL_DEMO_BY_SPECIES = {
  mouse: "mouse-cd20",
  rat: "rat-campath",
  human: "human-toripalimab",
};

function rememberVhvlDonorSpecies(demoId) {
  const d = DEMOS[demoId];
  if (d && d.sourceSpecies) {
    try {
      sessionStorage.setItem("insynbio_last_vhvl_source_species", d.sourceSpecies);
    } catch (e) {}
  }
}

function syncRememberedDonorFromCurrentForm() {
  const svc = REGISTRY.services[state.service];
  const map = {
    vhvl: "vhvl-demo",
    "structural-vhvl": "fv-demo",
    "segmentation-vhvl": "seg-demo",
  };
  const sel = map[svc.runner];
  if (!sel) return;
  const el = document.getElementById(sel);
  if (el && el.value) rememberVhvlDonorSpecies(el.value);
}

function pickVhvlDemoIdForSpecies(sp) {
  return VHVL_DEMO_BY_SPECIES[sp] || "mouse-cd20";
}

/** Official / common free viewers for downloaded PDB (Fv) models. */
function pdbViewerLinksHtml() {
  return `<p class="muted" style="font-size:11px;line-height:1.65;margin-top:8px">Free PDB viewers: <a href="https://www.cgl.ucsf.edu/chimerax/" target="_blank" rel="noopener">UCSF ChimeraX</a> · <a href="https://www.ks.uiuc.edu/Research/vmd/" target="_blank" rel="noopener">VMD</a> · <a href="https://nglviewer.org/" target="_blank" rel="noopener">NGL Viewer</a> (browser) · <a href="https://jmol.sourceforge.net/" target="_blank" rel="noopener">Jmol</a></p>`;
}

/**
 * One-click continue: open Mouse / Rat humanization from last demo species (session).
 * Fully human IgG demo → Segmentation (reference numbering only).
 */
function activateHumanizationFromLastDonor() {
  let sp = "mouse";
  try {
    sp = sessionStorage.getItem("insynbio_last_vhvl_source_species") || "mouse";
  } catch (e) {}
  /* Legacy sessions may still hold rabbit — console no longer exposes rabbit VH/VL humanization. */
  if (sp === "rabbit") {
    try {
      sessionStorage.setItem("insynbio_last_vhvl_source_species", "mouse");
    } catch (e2) {}
    sp = "mouse";
  }
  if (sp === "human") {
    state.pendingDemo = "human-toripalimab";
    activateService("segmentation-vhvl");
    return;
  }
  state.pendingVhvlSpecies = sp;
  activateService("vhvl-humanization");
}

/** VH→VHH: keep Demo case and Source class in sync (bidirectional). */
function syncVh2VhhSourceToDemo() {
  const service = REGISTRY.services[state.service];
  if (!service || service.runner !== "vh-to-vhh") return;
  const src = document.getElementById("vh2vhh-source").value;
  const sel = document.getElementById("vh2vhh-demo");
  if (!sel) return;
  if (src === "murine_mab") sel.value = "tislelizumab-vh";
  else if (src === "phage_display_vh") sel.value = "tislelizumab-vh";
  else if (src === "transgenic_mouse_vh") sel.value = "tislelizumab-vh";
  else sel.value = "tislelizumab-vh";
  loadServiceDemo();
}

function loadServiceDemo() {
  const service = REGISTRY.services[state.service];
  if (service.runner === "vhvl") {
    const demoId = document.getElementById("vhvl-demo").value;
    const demo = DEMOS[demoId];
    document.getElementById("vhvl-vh").value = demo.vh;
    document.getElementById("vhvl-vl").value = demo.vl;
    const nameEl = document.getElementById("vhvl-name");
    if (nameEl) nameEl.value = demoId || "";
    const vhvlSp = document.getElementById("vhvl-species");
    if (vhvlSp && demo.sourceSpecies && demo.sourceSpecies !== "human") {
      vhvlSp.value = demo.sourceSpecies;
    }
    document.getElementById("vhvl-helper").textContent = demo.summary;
  } else if (service.runner === "recheck-vhvl") {
    const demo = DEMOS[document.getElementById("rchk-vhvl-demo").value];
    document.getElementById("rchk-vhvl-donor-vh").value = demo.vh || "";
    document.getElementById("rchk-vhvl-donor-vl").value = demo.vl || "";
    // Load humanized version as candidate if available, otherwise leave blank for user to fill
    const huKey = demo.humanizedDemoKey || null;
    const huDemo = huKey && DEMOS[huKey] ? DEMOS[huKey] : null;
    document.getElementById("rchk-vhvl-cand-vh").value = huDemo ? (huDemo.vh || "") : "";
    document.getElementById("rchk-vhvl-cand-vl").value = huDemo ? (huDemo.vl || "") : "";
    document.getElementById("rchk-vhvl-species").value = demo.sourceSpecies || "mouse";
    document.getElementById("rchk-vhvl-name").value = `${document.getElementById("rchk-vhvl-demo").value || "vhvl"}-recheck`;
    document.getElementById("rchk-vhvl-helper").textContent = `${demo.summary} (recheck mode: donor vs customer candidate).`;
  } else if (service.runner === "structural-vhvl") {
    const demo = DEMOS[document.getElementById("fv-demo").value];
    document.getElementById("fv-vh").value = demo.vh;
    document.getElementById("fv-vl").value = demo.vl;
    const fb = document.getElementById("fv-fasta-batch");
    if (fb) fb.value = "";
    const ff = document.getElementById("fv-fasta-file");
    if (ff) ff.value = "";
    const h = document.getElementById("fv-helper");
    if (h) {
      h.innerHTML =
        `Antibody–antigen complexes: <strong>Offline Services</strong>. This Fv tool is VH+VL only.<br/><span class="muted">${escapeHtml(demo.summary)}</span>` +
        pdbViewerLinksHtml();
    }
  } else if (service.runner === "cmc-igg") {
    const demo = DEMOS[document.getElementById("cmc-demo").value];
    if (!demo) return; // sentinel value (e.g. custom input from humanization) — do not overwrite fields
    document.getElementById("cmc-vh").value = demo.vh;
    document.getElementById("cmc-vl").value = demo.vl;
    document.getElementById("cmc-sequence-name").value = demo.label || "";
    document.getElementById("cmc-antibody-type").value = demo.antibodyType || "humanized";
    updateCmcOriginNote();
    document.getElementById("cmc-helper").textContent = `${demo.summary} Source: ${cmcOriginLabel(demo.antibodyType || "humanized")}.`;
  } else if (service.runner === "vhh-humanization") {
    const demo = DEMOS[document.getElementById("vhh-demo").value];
    document.getElementById("vhh-seq").value = demo.seq;
    document.getElementById("vhh-species").value = demo.sourceSpecies || "alpaca";
    document.getElementById("vhh-helper").textContent = demo.summary;
  } else if (service.runner === "recheck-vhh") {
    const demo = DEMOS[document.getElementById("rchk-vhh-demo").value];
    document.getElementById("rchk-vhh-donor").value = demo.seq || "";
    // Load humanized version as candidate if available, otherwise leave blank for user to fill
    const humanizedKey = demo.humanizedDemoKey || null;
    const humanizedSeq = humanizedKey && DEMOS[humanizedKey] ? DEMOS[humanizedKey].seq : "";
    document.getElementById("rchk-vhh-cand").value = humanizedSeq;
    document.getElementById("rchk-vhh-species").value = demo.sourceSpecies || "alpaca";
    document.getElementById("rchk-vhh-name").value = `${document.getElementById("rchk-vhh-demo").value || "vhh"}-recheck`;
    document.getElementById("rchk-vhh-helper").textContent = `${demo.summary} (recheck mode: donor vs customer candidate).`;
  } else if (service.runner === "vhh-structural") {
    const demo = DEMOS[document.getElementById("vhh-struct-demo").value];
    document.getElementById("vhh-struct-seq").value = demo.seq || "";
    const h = document.getElementById("vhh-struct-helper");
    if (h) {
      h.innerHTML =
        `Antibody–antigen complexes: <strong>Offline Services</strong>. This page builds single-chain VHH only.<br/><span class="muted">${escapeHtml(demo.summary || "")}</span>` +
        pdbViewerLinksHtml();
    }
  } else if (service.runner === "cmc-vhh") {
    const demo = DEMOS[document.getElementById("vhh-cmc-demo").value];
    if (!demo) return; // sentinel value (custom input from humanization) — do not overwrite fields
    document.getElementById("vhh-cmc-seq").value = demo.seq;
    const nameEl = document.getElementById("vhh-cmc-name");
    if (nameEl) nameEl.value = demo.label || "";
    const helperEl = document.getElementById("vhh-cmc-helper");
    const isEngVHDemo = demo.sdab_origin === "engineered_vh";
    helperEl.innerHTML = isEngVHDemo
      ? `<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:5px;padding:8px 11px;margin-bottom:6px"><strong style="color:#92400e">&#9888; EngVH Mode (Engineered Autonomous VH — NOT Camelid VHH)</strong><br><span style="color:#78350f;font-size:11px">${escapeHtml(demo.summary)}</span></div>`
      : `<div style="font-size:11px;color:var(--muted)">${escapeHtml(demo.summary)}</div>`;
    const originSel = document.getElementById("vhh-cmc-origin");
    if (originSel) originSel.value = demo.sdab_origin || "camelid_vhh";
  } else if (service.runner === "vh-to-vhh") {
    const demoId = document.getElementById("vh2vhh-demo").value;
    const demo = DEMOS[demoId];
    document.getElementById("vh2vhh-seq").value = demo.seq;
    document.getElementById("vh2vhh-helper").textContent = demo.summary;
    const src = document.getElementById("vh2vhh-source");
    if (demoId === "mumab4d5-vh" || (demo.label && demo.label.includes("mumab4d5"))) {
      src.value = "murine_mab";
    } else if (demoId === "phage-maturation-vh-ref") {
      src.value = "phage_display_vh";
    } else if (demoId === "transgenic-hcab-vh-ref") {
      src.value = "transgenic_mouse_vh";
    } else {
      src.value = "human_mab";
    }
  } else if (service.runner === "segmentation-vhvl") {
    const demo = DEMOS[document.getElementById("seg-demo").value];
    document.getElementById("seg-vh").value = demo.vh;
    document.getElementById("seg-vl").value = demo.vl;
    const segSp = document.getElementById("seg-species");
    if (segSp && demo.sourceSpecies) segSp.value = demo.sourceSpecies;
    const segBase =
      "CDR/FR boundaries depend on the numbering scheme and VH/VL sequence only. V-gene library species affects closest V-gene name and identity %, not CDR/FR borders. Loading a demo fills sequences and syncs the library species.";
    document.getElementById("seg-helper").innerHTML = `<span>${segBase}</span><br/><span class="muted">${escapeHtml(demo.summary)}</span>`;
  } else if (service.runner === "vhh-segmentation") {
    const demo = DEMOS[document.getElementById("vhh-seg-demo").value];
    document.getElementById("vhh-seg-seq").value = demo.seq;
    const spEl = document.getElementById("vhh-seg-species");
    if (spEl && demo.sourceSpecies) spEl.value = demo.sourceSpecies;
    document.getElementById("vhh-seg-helper").textContent = demo.summary;
  } else if (service.runner === "cdna-optimization") {
    const demo = DEMOS[document.getElementById("cdna-demo").value];
    document.getElementById("cdna-seq").value = demo.seq || demo.vh || "";
    const vlEl = document.getElementById("cdna-vl");
    if (vlEl && demo.vl) vlEl.value = demo.vl;
    if (service.chainType === "vhh" && demo.cdnaPreset) {
      const p = demo.cdnaPreset;
      const a = document.getElementById("cdna-vhh-assembly");
      if (a) a.checked = !!p.assembly;
      const sp = document.getElementById("cdna-vhh-sp");
      if (sp && p.sp) sp.value = p.sp;
      const fu = document.getElementById("cdna-vhh-fusion");
      if (fu && p.fusion) fu.value = p.fusion;
      const or = document.getElementById("cdna-vhh-orient");
      if (or && p.orientation) or.value = p.orientation;
      const li = document.getElementById("cdna-vhh-linker");
      if (li && p.linker) li.value = p.linker;
      const cl = document.getElementById("cdna-vhh-cleavage");
      if (cl && p.cleavage) cl.value = p.cleavage;
      const tg = document.getElementById("cdna-vhh-tag");
      if (tg && p.tag) tg.value = p.tag;
    }
    document.getElementById("cdna-helper").textContent = demo.summary;
    if (typeof toggleCdnaIggAssembly === "function") toggleCdnaIggAssembly();
    if (typeof toggleCdnaVhhAssembly === "function") toggleCdnaVhhAssembly();
    if (typeof updateVhhAddonRows === "function") updateVhhAddonRows();
  } else if (service.runner === "cmc-bispecific") {
    const demo = DEMOS[document.getElementById("bs-cmc-demo").value];
    document.getElementById("bs-cmc-arm1").value = demo.arm1 || "";
    document.getElementById("bs-cmc-arm2").value = demo.arm2 || "";
    document.getElementById("bs-cmc-t1").value = demo.arm1Target || "Target_A";
    document.getElementById("bs-cmc-t2").value = demo.arm2Target || "Target_B";
    document.getElementById("bs-cmc-linker").value = demo.linker || "(G4S)3";
    document.getElementById("bs-cmc-helper").textContent = demo.summary;
    const originSel = document.getElementById("bs-cmc-origin");
    if (originSel) originSel.value = demo.sdab_origin || "camelid_vhh";
  } else if (service.runner === "bispecific-assembler") {
    const demo = DEMOS[document.getElementById("bs-assembler-demo").value];
    document.getElementById("bs-assembler-vh-a").value = demo.vh_a || "";
    document.getElementById("bs-assembler-vl-a").value = demo.vl_a || "";
    document.getElementById("bs-assembler-vh-b").value = demo.vh_b || "";
    document.getElementById("bs-assembler-vl-b").value = demo.vl_b || "";
    // default to crossmab for these demos
    document.getElementById("bs-assembler-format").value = "crossmab";
  } else if (service.runner === "bispecific-analyzer") {
    const demo = DEMOS[document.getElementById("bs-analyzer-demo").value];
    document.getElementById("bs-analyzer-vh-a").value = demo.vh_a || "";
    document.getElementById("bs-analyzer-vl-a").value = demo.vl_a || "";
    document.getElementById("bs-analyzer-vh-b").value = demo.vh_b || "";
    document.getElementById("bs-analyzer-vl-b").value = demo.vl_b || "";
  }
  syncRememberedDonorFromCurrentForm();
}

function openDemoInService(serviceId, demoId) {
  activateService(serviceId);
  setTimeout(() => {
    const service = REGISTRY.services[serviceId];
    if (service.runner === "vhvl") document.getElementById("vhvl-demo").value = demoId;
    else if (service.runner === "recheck-vhvl") document.getElementById("rchk-vhvl-demo").value = demoId;
    else if (service.runner === "structural-vhvl") document.getElementById("fv-demo").value = demoId;
    else if (service.runner === "cmc-igg") document.getElementById("cmc-demo").value = demoId;
    else if (service.runner === "vhh-humanization") document.getElementById("vhh-demo").value = demoId;
    else if (service.runner === "recheck-vhh") document.getElementById("rchk-vhh-demo").value = demoId;
    else if (service.runner === "cmc-vhh") document.getElementById("vhh-cmc-demo").value = demoId;
    else if (service.runner === "vh-to-vhh") document.getElementById("vh2vhh-demo").value = demoId;
    else if (service.runner === "bispecific-assembler") document.getElementById("bs-assembler-demo").value = demoId;
    else if (service.runner === "bispecific-analyzer") document.getElementById("bs-analyzer-demo").value = demoId;
    else if (service.runner === "segmentation-vhvl") document.getElementById("seg-demo").value = demoId;
    else if (service.runner === "vhh-segmentation") document.getElementById("vhh-seg-demo").value = demoId;
    loadServiceDemo();
  }, 0);
}

function resolveDemoTargetService(demoId) {
  if (demoId === "mouse-cd20" || demoId === "rat-campath") return "vhvl-humanization";
  if (demoId === "human-toripalimab") return "segmentation-vhvl";
  if (demoId === "toripalimab-igg" || demoId === "abiprubart-engineered" || demoId === "briakinumab-phage") return "igg-cmc-snapshot";
  if (demoId === "alpaca-vhh") return "vhh-humanization";
  if (demoId === "mumab4d5-vh" || demoId === "toripalimab-vh"
      || demoId === "tislelizumab-vh" || demoId === "pembrolizumab-vh"
      || demoId === "camrelizumab-vh" || demoId === "nivolumab-vh"
      || demoId === "teplizumab-vh") {
    return "vh-to-vhh-conversion";
  }
  return null;
}

// ── UI helpers ────────────────────────────────────────────────────────────────

/** Second arg: 0–100 from async poll; omit for indeterminate (spinner only). */
function setRunning(message, progressPct) {
  const el = document.getElementById("service-status");
  if (!el) return;
  const safe = escapeHtml(String(message || ""));
  let cls = "status-box running";
  let inner;
  const cancelBtn = window.__activeAsyncJobId
    ? `<button type="button" class="btn" style="margin-left:auto;padding:4px 10px;font-size:11px;background:#fee2e2;border:1px solid #fca5a5;color:#991b1b" onclick="cancelActiveAsyncJob()">Cancel job</button>`
    : "";
  if (progressPct != null && progressPct !== "" && !Number.isNaN(Number(progressPct))) {
    const p = Math.max(0, Math.min(100, Number(progressPct)));
    cls += " has-progress";
    inner =
      `<div class="run-progress-track" aria-hidden="true"><div class="run-progress-fill" style="width:${p}%"></div></div>` +
      `<div class="run-progress-row" style="display:flex;align-items:center;gap:8px"><div class="spinner"></div><span class="run-status-msg">${safe}</span><span style="margin-left:8px;font-size:11px;font-weight:600;color:#1e40af">${p}%</span>${cancelBtn}</div>`;
  } else {
    inner = `<div class="run-progress-row" style="display:flex;align-items:center;gap:8px"><div class="spinner"></div><span class="run-status-msg">${safe}</span>${cancelBtn}</div>`;
  }
  el.className = cls;
  el.innerHTML = inner;
}

function clearRunning() {
  const el = document.getElementById("service-status");
  if (!el) return;
  el.className = "status-box";
  el.innerHTML = "";
}

function setOutput(html) {
  const el = document.getElementById("workspace-output");
  if (el) el.innerHTML = html;
}

function validateSeq(seq, label, minLen, maxLen) {
  if (!seq) return `${label}: sequence is required`;
  if (seq.length < minLen) return `${label}: too short (${seq.length} aa; minimum ${minLen})`;
  if (seq.length > maxLen) return `${label}: too long (${seq.length} aa; maximum ${maxLen})`;
  if (!VALID_AA.test(seq)) return `${label}: non-standard amino-acid characters detected`;
  return null;
}

function normalizeSeq(text) {
  return (text || "").trim().replace(/\s/g, "").toUpperCase();
}

function badgeTone(status) {
  const s = String(status || "").toUpperCase();
  if (s.includes("PASS") || s === "DONE" || s === "OK" || s.startsWith("OK_")) return "pass";
  if (s.includes("FAIL")) return "fail";
  return "warn";
}

function statusLabel(status) {
  const map = {
    "OK": "PASS",
    "OK_SAFE_MODE": "PASS (safe mode)",
    "OK_WITH_QA_WARNINGS": "PASS ⚠",
    "FAILED": "FAIL",
  };
  const s = String(status || "");
  return map[s] || s;
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";
  return typeof value === "number" ? value.toFixed(digits) : String(value);
}

function metricHtml(label, value, tone = "", tooltip = "") {
  if (!tooltip) {
    return `<div class="metric ${tone}"><div class="label">${label}</div><div class="value">${value}</div></div>`;
  }
  const safeTooltip = String(tooltip).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  return `<div class="metric ${tone}" data-tip="${safeTooltip}" onmouseenter="showMetricTip(this)" onmouseleave="hideMetricTip()"><div class="label">${label} <span style="font-size:10px;opacity:.72;cursor:help">?</span></div><div class="value">${value}</div></div>`;
}
function showMetricTip(anchor) {
  let tip = document.getElementById("__metric_tip_float");
  if (!tip) {
    tip = document.createElement("div");
    tip.id = "__metric_tip_float";
    tip.style.cssText = "position:fixed;background:#1a2030;color:#e2e8f0;border-radius:7px;padding:10px 14px;font-size:12px;line-height:1.6;max-width:300px;z-index:99999;pointer-events:none;box-shadow:0 6px 20px rgba(0,0,0,.5);border:1px solid rgba(255,255,255,.1);display:none";
    document.body.appendChild(tip);
  }
  const raw = anchor.getAttribute("data-tip") || "";
  tip.textContent = raw.replace(/&amp;/g,"&").replace(/&quot;/g,'"').replace(/&lt;/g,"<").replace(/&gt;/g,">");
  tip.style.display = "block";
  const rect = anchor.getBoundingClientRect();
  const w = Math.min(300, window.innerWidth - 16);
  tip.style.maxWidth = w + "px";
  requestAnimationFrame(() => {
    const th = tip.offsetHeight;
    let left = rect.left + rect.width / 2 - tip.offsetWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tip.offsetWidth - 8));
    let top = rect.top - th - 8;
    if (top < 8) top = rect.bottom + 8;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  });
}
function hideMetricTip() {
  const tip = document.getElementById("__metric_tip_float");
  if (tip) tip.style.display = "none";
}

function toggleVariantDetails(jobId) {
  const body = document.getElementById(`variant-details-${jobId}`);
  const btn = document.getElementById(`variant-toggle-btn-${jobId}`);
  if (!body || !btn) return;
  const isHidden = body.style.display === "none";
  body.style.display = isHidden ? "block" : "none";
  btn.textContent = isHidden ? "Hide optimization details" : "Show optimization details";
}

function toggleSmartCmcSection(sectionId, btnId) {
  const body = document.getElementById(sectionId);
  const btn = document.getElementById(btnId);
  if (!body || !btn) return;
  const isHidden = body.style.display === "none";
  body.style.display = isHidden ? "block" : "none";
  btn.textContent = isHidden ? "▼ Hide mutation evaluation" : "▶ Show mutation evaluation";
}

function valueOutOfRange(v, low, high) {
  if (v == null) return false;
  return (low != null && v < low) || (high != null && v > high);
}

function adiTone(score) {
  if (score == null) return "";
  if (score >= 80) return "ok";
  if (score >= 60) return "warn";
  return "fail";
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function safeSdabOriginLabel(origin) {
  const o = String(origin || "").toLowerCase().replace(/-/g, "_");
  if (o === "engineered_vh") return "Gene-engineered VH sdAb / HCAb";
  if (o === "transgenic_sdab" || o === "transgenic") return "Transgenic mouse-derived HCAb";
  return "Humanized VHH";
}

function safeSdabReferenceLabel(origin) {
  const o = String(origin || "").toLowerCase().replace(/-/g, "_");
  if (o === "engineered_vh") return "Engineered VH reference";
  if (o === "transgenic_sdab" || o === "transgenic") return "Transgenic mouse sdAb reference";
  return "VHH clinical reference";
}

/** Strip cohort size hints from reference labels (UI only; API JSON unchanged). */
function sanitizeCohortLabelForDisplay(s) {
  if (s == null || s === "") return s;
  let t = String(s);
  t = t.replace(/\bNatural-384\b/gi, "Natural");
  t = t.replace(/\bNat-384\b/gi, "Natural cohort");
  t = t.replace(/\bNatural384\b/gi, "Natural");
  t = t.replace(/\bEng-458\b/gi, "Engineered clinical");
  t = t.replace(/\bAbRef-458\b/gi, "Clinical reference");
  t = t.replace(/\bVHH42\b/gi, "VHH clinical panel");
  t = t.replace(/\bVHH68\b/gi, "VHH reference panel");
  t = t.replace(/\(\s*n\s*=\s*\d+\s*\)/gi, "");
  t = t.replace(/\bengineered458_only\b/gi, "engineered clinical panel");
  t = t.replace(/\bnatural384_only\b/gi, "natural cohort panel");
  t = t.replace(/\bintersection_nat384_eng458\b/gi, "natural engineered intersection");
  t = t.replace(/\bhumanized_transgenic_provisional\b/gi, "transgenic-mouse cohort provisional");
  t = t.replace(/\bhumanized_transgenic_cohort\b/gi, "transgenic-mouse cohort");
  t = t.replace(/\s{2,}/g, " ").trim();
  return t;
}

function _billingLedgerRows() {
  try {
    const arr = JSON.parse(localStorage.getItem(LS_LEDGER) || "[]");
    return Array.isArray(arr) ? arr : [];
  } catch (e) {
    return [];
  }
}

function _csvCell(v) {
  const s = String(v == null ? "" : v);
  return `"${s.replace(/"/g, '""')}"`;
}

function downloadUsageLedgerCsv() {
  const rows = _billingLedgerRows();
  const header = [
    "time_local", "time_iso", "account_id", "account_type", "service_id",
    "service_label", "credits_spent", "balance_after", "run_location", "demo_id", "run_id"
  ];
  const body = rows.map(e => [
    e.atLocal, e.atIso, e.accountId, e.accountType, e.serviceId,
    e.serviceLabel, e.credits, e.balance, e.runLocation, e.demoId, e.id,
  ].map(_csvCell).join(","));
  const csv = [header.join(","), ...body].join("\n");
  const blob = new Blob([csv], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `insynbio_usage_ledger_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function clearUsageLedger() {
  if (!confirm("Clear local usage ledger in this browser? Credits balance is not reset.")) return;
  try { localStorage.setItem(LS_LEDGER, "[]"); } catch (e) {}
  renderEmptyRail();
  updateTopbar();
}

/** Right-rail block: account/billing ledger for this browser plus server-debit mirror rows. */
function buildLedgerRailHtml() {
  try {
    const arr = _billingLedgerRows();
    const ident = currentBillingIdentity();
    const balance = serverWalletShowsInfinityBalance() ? "∞" : Number(state.credits || 0).toLocaleString("en-US");
    const accountKind = ident.server ? "Account" : ident.gate ? "Gate" : "Guest";
    const accountLine = `${accountKind} · ${ident.id}`;
    if (!Array.isArray(arr) || !arr.length) {
      return `<div class="rail-section">
        <div class="rail-title">Account &amp; Billing</div>
        <div class="rail-card" style="font-size:10px">
          <div style="font-weight:700;color:var(--accent);font-size:12px">${escapeHtml(accountLine)}</div>
          <div style="margin-top:4px">Balance · <strong>${escapeHtml(balance)}</strong></div>
          <div style="margin-top:4px">Location · <span class="mono">${escapeHtml(currentRunLocation())}</span></div>
          <div class="muted" style="margin-top:8px">No debited runs recorded in this browser yet.</div>
          <button type="button" class="btn link" style="margin-top:8px;font-size:10px;padding:3px 8px" onclick="downloadUsageLedgerCsv()">Download bill CSV</button>
        </div>
      </div>`;
    }
    const rows = arr.slice(0, 8).map((e) => {
      const balanceText = e.balance != null
        ? ` · bal ${Number.isFinite(Number(e.balance)) ? Number(e.balance).toLocaleString("en-US") : escapeHtml(String(e.balance))}`
        : "";
      const creditText = e.adminFree ? "0 credits (admin free)" : `−${escapeHtml(String(e.credits || 0))} credits`;
      return `<div style="padding:6px 0;border-bottom:1px solid var(--line-2)">
        <div style="font-weight:700">${escapeHtml(e.serviceLabel || e.serviceId || "Run")}</div>
        <div class="muted" style="font-size:10px">${escapeHtml(e.atLocal || e.atIso || "—")}</div>
        <div style="font-size:10px">${creditText}${balanceText}</div>
        <div class="muted mono" style="font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(e.runLocation || "")}">${escapeHtml(e.runLocation || "—")}</div>
      </div>`;
    }).join("");
    return `<div class="rail-section">
      <div class="rail-title">Account &amp; Billing</div>
      <div class="rail-card" style="font-size:10px;line-height:1.35">
        <div style="font-weight:700;color:var(--accent);font-size:12px">${escapeHtml(accountLine)}</div>
        <div style="margin-top:4px">Balance · <strong>${escapeHtml(balance)}</strong></div>
        <div style="margin:6px 0 8px;display:flex;gap:6px;flex-wrap:wrap">
          <button type="button" class="btn link" style="font-size:10px;padding:3px 8px" onclick="downloadUsageLedgerCsv()">Download bill CSV</button>
          <button type="button" class="btn link" style="font-size:10px;padding:3px 8px;color:var(--fail)" onclick="clearUsageLedger()">Clear local log</button>
        </div>
        ${rows}
        <div class="muted" style="margin-top:8px">Showing ${Math.min(8, arr.length)} / ${arr.length} records. Local browser ledger; server account debits are mirrored here after successful runs.</div>
      </div>
    </div>`;
  } catch (e) {
    return "";
  }
}

function railServiceCardHtml() {
  const service = REGISTRY.services[state.service];
  const accountStr = document.getElementById("top-account") ? document.getElementById("top-account").textContent : "Account · —";
  return `
    <div class="rail-section">
      <div class="rail-title">Service &amp; Environment</div>
      <div class="rail-card meta-list">
        <div class="meta-item"><div class="k">Selected</div><div class="v">${service.label}</div></div>
        <div class="meta-item"><div class="k">Analysis</div><div class="v mono" style="font-size:10px">${service.analysisVersion}</div></div>
        <div class="meta-item"><div class="k">Standard</div><div class="v mono" style="font-size:9px;line-height:1.3">${service.underlyingStandard}</div></div>
        <div class="meta-item"><div class="k">Credits</div><div class="v">${service.module === "offline-services" ? "Quote" : service.credits === 0 ? "Free" : `${service.credits}/run`}</div></div>
        <div class="meta-item"><div class="k">Environment</div><div class="v">Demo / Lite</div></div>
        ${service.refDb ? `<div class="meta-item"><div class="k">Ref DB</div><div class="v">${service.refDb}</div></div>` : ""}
      </div>
    </div>
  `;
}

function renderEmptyRail() {
  const service = REGISTRY.services[state.service];
  const isOffline = service.module === "offline-services";
  document.getElementById("result-rail").innerHTML = `
    ${railServiceCardHtml()}
    ${buildLedgerRailHtml()}
    <div class="rail-section">
      <div class="rail-title">Last run</div>
      <div class="rail-card">
        <p class="muted" style="font-size:11px;line-height:1.55;margin:0">Full tables and plots stay in the <strong>center</strong>. This column: status, downloads, and expandable metrics.</p>
        <div class="run-status warn" style="margin-top:10px">${isOffline ? "Offline queue" : "No run yet"}</div>
        <p class="muted" style="font-size:11px;margin-top:8px;margin-bottom:0">${isOffline ? "Submit the offline form when ready." : `Run <span class="mono">${service.label}</span> from the main panel.`}</p>
      </div>
    </div>
  `;
}

function updateResultRail(payload) {
  const clientTimeHtml = payload.clientLocalTime
    ? `<div style="margin-top:10px;font-size:10px;color:var(--muted);line-height:1.45">Client time (local)<br><span class="mono" style="font-size:11px;color:var(--text)">${escapeHtml(payload.clientLocalTime)}</span></div>`
    : "";
  const metricsHtml = (payload.metrics || []).map(m => {
    const vLen = String(m.value).length;
    const vSize = vLen > 12 ? "12px" : vLen > 8 ? "14px" : "18px";
    const subRow = m.sub
      ? `<div class="rail-metric-sub" style="margin-top:4px;font-size:10px;font-weight:600;line-height:1.45;white-space:normal;overflow-wrap:anywhere">${m.sub}</div>`
      : "";
    return `
    <div class="metric ${m.tone || ""}">
      <div class="label">${m.label}</div>
      <div class="value ${m.mono ? "mono" : ""}" style="font-size:${vSize};word-break:break-all">${m.value}</div>
      ${subRow}
    </div>`;
  }).join("");
  const artifactsHtml = (payload.artifacts || []).length
    ? payload.artifacts.map(a => {
        // Use blob-fetch for /api/files/* URLs so credentials (cookies / Auth header) are
        // properly carried, and so a transient nginx auth/redirect cannot bounce the user
        // to a login page mid-download. Direct external URLs still use plain <a>.
        const isApiFile = /\/api\/files\//.test(a.url || "");
        if (isApiFile) {
          const safeUrl = String(a.url).replace(/'/g, "%27");
          const safeLabel = String(a.label).replace(/'/g, "\\'");
          const wantsDownload = !!a.download;
          return `<a class="btn link ${a.primary ? "primary" : ""}" href="javascript:void(0)" onclick="_downloadArtifact('${safeUrl}', '${safeLabel}', ${wantsDownload}); return false;">${a.label}</a>`;
        }
        return `<a class="btn link ${a.primary ? "primary" : ""}" href="${a.url}" ${a.download ? "download" : 'target="_blank"'}>${a.label}</a>`;
      }).join("")
    : `<span class="muted">No artifact generated yet.</span>`;
  const metaHtml = (payload.metadata || []).map(m => `
    <div class="meta-item">
      <div class="k">${m.label}</div>
      <div class="v ${m.mono ? "mono" : ""}">${m.value}</div>
    </div>
  `).join("");
  const refDbBlock = payload.refDb ? `
    <div class="rail-card" style="margin-bottom:10px;border-color: ${payload.refDb === "VHH clinical" ? "rgba(167,139,250,.3)" : "rgba(33,199,217,.25)"}">
      <div style="font-size:11px;font-weight:700;color:${payload.refDb === "VHH clinical" ? "var(--credit)" : "var(--accent)"};">${sanitizeCohortLabelForDisplay(payload.refDb)}</div>
      <div style="font-size:10px;color:var(--muted);margin-top:2px">${payload.refDb === "Clinical reference" ? "Clinical reference" : "VHH clinical"}</div>
      ${payload.clinicalRank ? `<div style="margin-top:6px;font-size:15px;font-weight:800;color:var(--pass)">${payload.clinicalRank}</div>` : ""}
    </div>
  ` : "";
  document.getElementById("result-rail").innerHTML = `
    ${railServiceCardHtml()}
    <div class="rail-section">
      <div class="rail-title">Last run</div>
      ${refDbBlock}
      <div class="rail-card">
        <div class="run-status ${badgeTone(payload.status)}">${payload.status}</div>
        <div style="margin-top:8px;font-weight:600;font-size:13px">${payload.summaryTitle || "Done"}</div>
        <p class="muted" style="margin-top:4px;font-size:11px;line-height:1.45">${payload.summaryText || ""}</p>
        ${clientTimeHtml}
        <div style="margin-top:10px;font-size:10px;color:var(--muted)">Details → center panel</div>
      </div>
    </div>
    <div class="rail-section">
      <div class="rail-title">Downloads</div>
      <div class="rail-card artifact-list">${artifactsHtml}</div>
    </div>
    <details class="rail-details">
      <summary>Metrics · advice · audit</summary>
      <div style="margin-top:8px">
        <div class="rail-title" style="margin-bottom:6px;font-size:10px">Key metrics</div>
        <div class="rail-card" style="padding:8px"><div class="metric-grid" style="gap:6px">${metricsHtml}</div></div>
        <div class="rail-title" style="margin:10px 0 6px;font-size:10px">Recommendation</div>
        <div class="rail-card" style="padding:8px;font-size:11px">${payload.recommendation || "<span class='muted'>—</span>"}</div>
        <div class="rail-title" style="margin:10px 0 6px;font-size:10px">Audit</div>
        <div class="rail-card meta-list" style="padding:8px">${metaHtml || "<span class='muted'>—</span>"}</div>
      </div>
    </details>
    ${buildLedgerRailHtml()}
  `;
}

function errorPanel(message) {
  return `
    <section class="result-panel">
      <div class="result-title"><strong>Error</strong><span class="run-status fail">FAILED</span></div>
      <div class="result-body"><pre class="mono" style="white-space:pre-wrap;color:var(--fail)">${escapeHtml(message)}</pre></div>
    </section>
  `;
}

function lookupServiceReportVersion(service) {
  if (!service) return "—";
  const map = state.serviceReportVersions;
  const key = service.reportCatalogKey;
  if (key && map && typeof map === "object" && map[key]) return String(map[key]);
  return service.serviceReportVersion || service.reportVersion || "—";
}

/** Leading kv-table shown after successful runs (parity across services). */
function formatRunMetadataHtml(service, data, extraRows) {
  const genAt = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";
  const svc = service || {};
  const opt = (extraRows || []).filter(Boolean);
  const suiteRf = state.apiReportFormatVersion || "—";
  const suiteProto = state.apiProtocolVersion || "—";
  const analysisDisp = state.apiAnalysisVersion || svc.analysisVersion || "—";
  const svcRpt = lookupServiceReportVersion(svc);
  const rows = [
    `<tr><th>Report format (suite)</th><td class="mono">${escapeHtml(suiteRf)}</td></tr>`,
    `<tr><th>Service</th><td>${escapeHtml(svc.label || "—")}</td></tr>`,
    `<tr><th>Service report (content)</th><td class="mono">${escapeHtml(svcRpt)}</td></tr>`,
    `<tr><th>Protocol (suite)</th><td class="mono">${escapeHtml(suiteProto)}</td></tr>`,
    `<tr><th>Analysis / engine</th><td>${escapeHtml(analysisDisp)}</td></tr>`,
    ...opt,
    `<tr><th>Job ID</th><td class="mono">${escapeHtml(data.job_id || "—")}</td></tr>`,
    `<tr><th>Elapsed</th><td>${data.elapsed_sec != null ? escapeHtml(String(data.elapsed_sec)) + "s" : "—"}</td></tr>`,
    `<tr><th>Generated (browser)</th><td class="mono">${escapeHtml(genAt)}</td></tr>`,
  ];
  return `
    <section class="result-panel">
      <div class="result-title"><strong>Run metadata</strong></div>
      <div class="result-body">
        <table class="kv-table">${rows.join("")}</table>
      </div>
    </section>
  `;
}

// ── Service runners ───────────────────────────────────────────────────────────

async function runCurrentService() {
  const service = REGISTRY.services[state.service];
  if (service.runner === "vhvl") return runVhvlHumanization(service);
  if (service.runner === "recheck-vhvl") return runRecheckVhvl(service);
  if (service.runner === "structural-vhvl") return runFvImmuneBuilder(service);
  if (service.runner === "cmc-igg") return runCmcIgg(service);
  if (service.runner === "vhh-humanization") return runVhhHumanization(service);
  if (service.runner === "recheck-vhh") return runRecheckVhh(service);
  if (service.runner === "vhh-structural") { void runVhhStructural(service); return; }
  if (service.runner === "cmc-vhh") return runVhhCmc(service);
  if (service.runner === "vh-to-vhh") { void runVhToVhh(service); return; }
  if (service.runner === "segmentation-vhvl") return await runSegmentationVhvl(service);
  if (service.runner === "vhh-segmentation") return await runVhhSegmentation(service);
  if (service.runner === "cdna-optimization") return await runCdnaOptimization(service);
  if (service.runner === "cmc-bispecific") return runCmcBispecific(service);
  if (service.runner === "bispecific-assembler") return runBispecificAssembler(service);
  if (service.runner === "bispecific-analyzer") return runBispecificAnalyzer(service);
  if (service.runner === "petization") return runPetization(service);
}

function _recheckJoinUrl(u) {
  return u ? apiJoin(String(u).replace(/^\/+/, "")) : "";
}

function buildRecheckArtifacts(data) {
  const r = data.result || {};
  const ex = data.extra || {};
  const reportUrl = _recheckJoinUrl(data.report_url || ex.report_url || r.report_url);
  const zipUrl = _recheckJoinUrl(ex.zip_url || r.zip_url || data.zip_url);
  const arts = [];
  if (reportUrl) {
    arts.push({ label: "View Report (HTML)", url: reportUrl, primary: true });
    arts.push({ label: "Save Report (HTML)", url: reportUrl, download: true });
  }
  if (zipUrl) {
    arts.push({ label: "Download delivery bundle (ZIP)", url: zipUrl, download: true });
  }
  return { reportUrl, zipUrl, arts };
}

/* ── Recheck professional result rendering (categorized metric cards) ───── */
function _rchkToneByDelta(delta, ranges) {
  if (delta == null || isNaN(Number(delta))) return "";
  const a = Math.abs(Number(delta));
  if (a <= ranges[0]) return "ok";
  if (a <= ranges[1]) return "warn";
  return "fail";
}
function _rchkToneByThreshold(val, okBelow, warnBelow) {
  if (val == null || isNaN(Number(val))) return "";
  const v = Number(val);
  if (v <= okBelow) return "ok";
  if (v <= warnBelow) return "warn";
  return "fail";
}
function _rchkToneByScore(val, okAbove, warnAbove) {
  if (val == null || isNaN(Number(val))) return "";
  const v = Number(val);
  if (v >= okAbove) return "ok";
  if (v >= warnAbove) return "warn";
  return "fail";
}
function _rchkFmt(v, d) {
  if (v == null || isNaN(Number(v))) return "—";
  return Number(v).toFixed(d == null ? 2 : d);
}
function _rchkPanelHeader(title, status) {
  return `<div class="result-title"><strong>${title}</strong><span class="run-status ${badgeTone(status)}">${escapeHtml(String(status||"—"))}</span></div>`;
}
/** Allow bold from API HTML in recommendation (&lt;strong&gt; only). */
function _rchkRecommendationHtml(raw) {
  let t = String(raw || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  t = t.replace(/&lt;(\/?)strong&gt;/gi, "<$1strong>");
  return t;
}
function _rchkDownloadsBar(data) {
  const { reportUrl, zipUrl } = buildRecheckArtifacts(data);
  const btns = [];
  if (reportUrl) {
    const su = String(reportUrl).replace(/'/g, "%27");
    btns.push(`<a class="btn primary" href="javascript:void(0)" onclick="_downloadArtifact('${su}', 'Recheck HTML', false); return false;">View Report (HTML)</a>`);
    btns.push(`<a class="btn" href="javascript:void(0)" onclick="_downloadArtifact('${su}', 'Recheck HTML', true); return false;">Save Report (HTML)</a>`);
  }
  if (zipUrl) {
    const su = String(zipUrl).replace(/'/g, "%27");
    btns.push(`<a class="btn" href="javascript:void(0)" onclick="_downloadArtifact('${su}', 'ZIP bundle', true); return false;">Download delivery bundle (ZIP)</a>`);
  }
  if (!btns.length) return "";
  return `
    <section class="result-panel" style="margin-top:0;margin-bottom:8px;border-color:rgba(217,119,6,.35)">
      <div class="result-title"><strong>Deliverables</strong></div>
      <div class="result-body"><div style="display:flex;flex-wrap:wrap;gap:10px">${btns.join("")}</div></div>
    </section>`;
}

function renderRecheckVhvlResult(r, data, service, overallStatus) {
  const sq  = r.structure_qc || {};
  const mc  = (r.mini_cmc || {}).candidate || {};
  const cmp = (r.mini_cmc || {}).compare_basic_developability || {};
  const donorDev = cmp.donor || {};
  const delta = cmp.delta || {};
  const nat = r.naturalness || {};
  const hpr = r.hpr_index || {};
  const hprScore = ((hpr.humanized || {}).combined || {}).score;

  // Status verdict block
  const inputQc = (r.input_qc || {}).status || "—";
  const structQc = sq.status || "NOT_RUN";
  const cmcStatus = mc.status || "—";
  const natStatus = nat.status || "—";
  const hprStatus = hprScore != null ? (hprScore > 0.6 ? "PASS" : "WARN") : "—";

  // Structure card grid
  const grmsd  = sq.global_fv_rmsd_ca;
  const adelta = sq.angle_delta_deg;
  const plddtD = (sq.donor || {}).plddt;
  const plddtC = (sq.candidate || {}).plddt;
  const cdrR   = sq.cdr_rmsd || {};
  const cdrRows = ["H1","H2","H3","L1","L2","L3"].map(k => {
    if (cdrR[k] == null) return "";
    const tone = _rchkToneByThreshold(cdrR[k], 1.0, 1.5);
    return `<tr><td class="mono">${k}</td><td class="mono"><span class="badge badge-${tone === "ok" ? "ok" : tone === "warn" ? "warn" : "fail"}" style="padding:1px 8px">${_rchkFmt(cdrR[k], 2)} Å</span></td></tr>`;
  }).filter(Boolean).join("");

  const structMetricsHtml = sq.status === "NOT_RUN"
    ? `<p class="muted" style="margin:6px 0">Structure QC not executed for this run.</p>`
    : `<div class="metric-grid recheck-row-4">
        ${metricHtml("Global Cα RMSD (Å)", _rchkFmt(grmsd, 2), _rchkToneByThreshold(grmsd, 1.0, 2.0), "Backbone Cα RMSD between donor and candidate Fv predicted structures.")}
        ${metricHtml("VH/VL Angle Δ (°)", adelta != null ? _rchkFmt(adelta, 1) : "—", adelta != null ? _rchkToneByThreshold(Math.abs(adelta), 4.0, 6.0) : "", "VH-VL packing angle deviation. >6° suggests interface perturbation.")}
        ${metricHtml("pLDDT — donor", plddtD != null ? _rchkFmt(plddtD, 1) : "—", _rchkToneByScore(plddtD, 75, 65), "Local confidence of donor structure model.")}
        ${metricHtml("pLDDT — candidate", plddtC != null ? _rchkFmt(plddtC, 1) : "—", _rchkToneByScore(plddtC, 75, 65), "Local confidence of candidate structure model.")}
      </div>
      ${cdrRows ? `<table class="kv-table" style="margin-top:10px"><thead><tr><th>CDR loop</th><th>Cα RMSD</th></tr></thead><tbody>${cdrRows}</tbody></table>` : ""}`;

  // Mini-CMC card grid + donor/candidate delta
  const flags = mc.flags || [];
  const flagsHtml = flags.length
    ? `<div role="status" style="margin-top:10px;padding:10px 12px;background:#fff7ed;border:1px solid #fdba74;border-radius:8px;color:#78350f;font-size:12px;line-height:1.5;font-weight:600"><span style="opacity:.95">QC flags:</span><br>${flags.map(f => `<span class="mono" style="display:inline-block;margin-top:4px;padding:2px 8px;background:#fde68a;border-radius:4px;color:#92400e;border:1px solid #fcd34d;margin-right:6px">${escapeHtml(f)}</span>`).join("")}</div>`
    : `<div style="margin-top:8px;font-size:11px;color:var(--ok)">✓ No flags raised</div>`;
  const cmcMetricsHtml = `<div class="metric-grid recheck-row-5">
      ${metricHtml("pI (Fab)", _rchkFmt(mc.pI, 2), mc.pI == null ? "" : (mc.pI < 5.0 || mc.pI > 9.5 ? "fail" : (mc.pI < 6.0 || mc.pI > 9.0 ? "warn" : "ok")), "Theoretical isoelectric point of the assembled Fv.")}
      ${metricHtml("GRAVY", _rchkFmt(mc.gravy, 3), mc.gravy == null ? "" : (mc.gravy > 0.10 ? "fail" : (mc.gravy > 0.05 ? "warn" : "ok")), "Grand average of hydropathy (lower = more soluble).")}
      ${metricHtml("Instability index", _rchkFmt(mc.instability_index, 1), _rchkToneByThreshold(mc.instability_index, 40, 50), "Guruprasad instability index (>40 unstable).")}
      ${metricHtml("Aromaticity", _rchkFmt(mc.aromaticity, 3), "", "Fraction of aromatic residues (Trp/Tyr/Phe).")}
      ${metricHtml("Net charge proxy", _rchkFmt(mc.net_charge_proxy, 1), "", "Approximate net charge at neutral pH.")}
    </div>`;

  // Donor vs Candidate delta table
  let deltaHtml = "";
  if (donorDev.pI != null) {
    const dRows = [
      ["pI", donorDev.pI, mc.pI, delta.pI, 2],
      ["GRAVY", donorDev.gravy, mc.gravy, delta.gravy, 3],
      ["Instability", donorDev.instability_index, mc.instability_index, delta.instability_index, 1],
    ].map(([lbl, d, c, dlt, dp]) => {
      const dltStr = dlt != null ? (dlt >= 0 ? "+" : "") + _rchkFmt(dlt, dp) : "—";
      const tone = dlt == null ? "" : (Math.abs(Number(dlt)) <= (lbl === "pI" ? 0.5 : lbl === "GRAVY" ? 0.05 : 5.0) ? "ok" : "warn");
      return `<tr><td>${lbl}</td><td class="mono">${_rchkFmt(d, dp)}</td><td class="mono">${_rchkFmt(c, dp)}</td><td class="mono"><span class="badge badge-${tone === "ok" ? "ok" : "warn"}" style="padding:1px 8px">${dltStr}</span></td></tr>`;
    }).join("");
    deltaHtml = `<table class="kv-table" style="margin-top:10px"><thead><tr><th>Metric</th><th>Donor</th><th>Candidate</th><th>Δ (Cand − Donor)</th></tr></thead><tbody>${dRows}</tbody></table>`;
  }

  // Humanness card grid
  const hprDelta = (hpr.delta || {}).combined;
  const humanessHtml = `<div class="metric-grid recheck-row-4">
      ${metricHtml("HPR Index", hprScore != null ? _rchkFmt(hprScore, 3) : "—", _rchkToneByScore(hprScore, 0.7, 0.6), "9-mer human peptide repertoire compatibility (>0.6 acceptable).")}
      ${metricHtml("HPR Δ (Cand − Donor)", hprDelta != null ? (hprDelta >= 0 ? "+" : "") + _rchkFmt(hprDelta, 3) : "—", hprDelta == null ? "" : (hprDelta >= 0 ? "ok" : "warn"), "Improvement of HPR vs donor.")}
      ${metricHtml("Paired Humanness", nat.paired_humanness != null ? _rchkFmt(nat.paired_humanness, 3) : "—", _rchkToneByScore(nat.paired_humanness, 0.7, 0.5), "Likelihood of human-like VH/VL pairing context.")}
      ${metricHtml("Pairing Likelihood", nat.pairing_likelihood != null ? _rchkFmt(nat.pairing_likelihood, 3) : "—", _rchkToneByScore(nat.pairing_likelihood, 0.7, 0.5), "Empirical pairing likelihood from human repertoire.")}
    </div>`;

  return `
    ${formatRunMetadataHtml(service, data, [
      r.project_name ? `<tr><th>Project / sequence ID</th><td class="mono">${escapeHtml(String(r.project_name))}</td></tr>` : "",
      `<tr><th>Service</th><td>VH/VL Customer Recheck</td></tr>`,
      `<tr><th>Clean mode</th><td>${escapeHtml(r.clean_mode || "—")}</td></tr>`,
    ].filter(Boolean))}
    ${_rchkDownloadsBar(data)}

    <section class="result-panel">
      ${_rchkPanelHeader("§0 Overall verdict", overallStatus)}
      <div class="result-body">
        <div class="metric-grid recheck-row-5">
          ${metricHtml("Input QC", inputQc, badgeTone(inputQc) === "pass" ? "ok" : (badgeTone(inputQc) === "fail" ? "fail" : "warn"))}
          ${metricHtml("Structure QC", structQc, badgeTone(structQc) === "pass" ? "ok" : (badgeTone(structQc) === "fail" ? "fail" : "warn"))}
          ${metricHtml("Mini-CMC", cmcStatus, badgeTone(cmcStatus) === "pass" ? "ok" : (badgeTone(cmcStatus) === "fail" ? "fail" : "warn"))}
          ${metricHtml("Paired Naturalness", natStatus, badgeTone(natStatus) === "pass" ? "ok" : (badgeTone(natStatus) === "fail" ? "fail" : "warn"))}
          ${metricHtml("HPR Index", hprStatus, badgeTone(hprStatus) === "pass" ? "ok" : "warn")}
        </div>
        <div style="margin-top:10px;padding:10px 12px;background:rgba(217,119,6,.06);border-left:3px solid #d97706;border-radius:0 6px 6px 0;font-size:12px;line-height:1.6"><strong>Recommendation</strong> &mdash; ${_rchkRecommendationHtml(r.recommendation || "")}</div>
      </div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§1 Structure conservation (Donor vs Candidate)", structQc)}
      <div class="result-body">${structMetricsHtml}</div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§2 Developability (Mini-CMC)", cmcStatus)}
      <div class="result-body">
        ${cmcMetricsHtml}
        ${flagsHtml}
        ${deltaHtml}
      </div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§3 Humanization analysis", hprStatus)}
      <div class="result-body">${humanessHtml}</div>
    </section>

    <p class="muted" style="margin-top:14px;font-size:11px">Same files appear under <strong>DOWNLOADS</strong> on the right for convenience.</p>
  `;
}

function renderRecheckVhhResult(r, data, service, overallStatus) {
  const sq  = r.structure_qc || {};
  const mc  = (r.mini_cmc || {}).candidate || {};
  const cmp = (r.mini_cmc || {}).compare_basic_developability || {};
  const donorDev = cmp.donor || {};
  const delta = cmp.delta || {};
  const nat = r.naturalness || {};
  const hpr = r.hpr_index || {};
  const hprScore = ((hpr.humanized || {}).vh || {}).score
                || ((hpr.humanized || {}).combined || {}).score;

  const inputQc = (r.input_qc || {}).status || "—";
  const structQc = sq.status || "NOT_RUN";
  const cmcStatus = mc.status || "—";
  const natStatus = nat.status || "—";
  const hprStatus = hprScore != null ? (hprScore > 0.6 ? "PASS" : "WARN") : "—";

  // Structure card grid
  const grmsd  = sq.global_fv_rmsd_ca || sq.global_rmsd_ca;
  const plddtD = (sq.donor || {}).plddt;
  const plddtC = (sq.candidate || {}).plddt;
  const cdrR   = sq.cdr_rmsd || {};
  const cdrRows = ["H1","H2","H3"].map(k => {
    if (cdrR[k] == null) return "";
    const tone = _rchkToneByThreshold(cdrR[k], 1.0, 1.5);
    return `<tr><td class="mono">${k}</td><td class="mono"><span class="badge badge-${tone === "ok" ? "ok" : tone === "warn" ? "warn" : "fail"}" style="padding:1px 8px">${_rchkFmt(cdrR[k], 2)} Å</span></td></tr>`;
  }).filter(Boolean).join("");

  const structMetricsHtml = sq.status === "NOT_RUN"
    ? `<p class="muted" style="margin:6px 0">Structure QC not executed for this run.</p>`
    : `<div class="metric-grid recheck-row-3">
        ${metricHtml("Global Cα RMSD (Å)", _rchkFmt(grmsd, 2), _rchkToneByThreshold(grmsd, 1.0, 2.0), "Backbone Cα RMSD between donor and candidate VHH predicted structures.")}
        ${metricHtml("pLDDT — donor", plddtD != null ? _rchkFmt(plddtD, 1) : "—", _rchkToneByScore(plddtD, 75, 65), "Local confidence of donor VHH model.")}
        ${metricHtml("pLDDT — candidate", plddtC != null ? _rchkFmt(plddtC, 1) : "—", _rchkToneByScore(plddtC, 75, 65), "Local confidence of candidate VHH model.")}
      </div>
      ${cdrRows ? `<table class="kv-table" style="margin-top:10px"><thead><tr><th>CDR loop</th><th>Cα RMSD</th></tr></thead><tbody>${cdrRows}</tbody></table>` : ""}`;

  // Mini-CMC
  const flags = mc.flags || [];
  const flagsHtml = flags.length
    ? `<div role="status" style="margin-top:10px;padding:10px 12px;background:#fff7ed;border:1px solid #fdba74;border-radius:8px;color:#78350f;font-size:12px;line-height:1.5;font-weight:600"><span style="opacity:.95">QC flags:</span><br>${flags.map(f => `<span class="mono" style="display:inline-block;margin-top:4px;padding:2px 8px;background:#fde68a;border-radius:4px;color:#92400e;border:1px solid #fcd34d;margin-right:6px">${escapeHtml(f)}</span>`).join("")}</div>`
    : `<div style="margin-top:8px;font-size:11px;color:var(--ok)">✓ No flags raised</div>`;
  const cmcMetricsHtml = `<div class="metric-grid recheck-row-5">
      ${metricHtml("pI (VHH)", _rchkFmt(mc.pI, 2), mc.pI == null ? "" : (mc.pI < 5.0 || mc.pI > 9.5 ? "fail" : (mc.pI < 6.0 || mc.pI > 9.0 ? "warn" : "ok")), "Theoretical pI of VHH domain.")}
      ${metricHtml("GRAVY", _rchkFmt(mc.gravy, 3), mc.gravy == null ? "" : (mc.gravy > 0.10 ? "fail" : (mc.gravy > 0.05 ? "warn" : "ok")), "Grand average of hydropathy.")}
      ${metricHtml("Instability index", _rchkFmt(mc.instability_index, 1), _rchkToneByThreshold(mc.instability_index, 40, 50), "Guruprasad instability index.")}
      ${metricHtml("Aromaticity", _rchkFmt(mc.aromaticity, 3), "", "Fraction of aromatic residues.")}
      ${metricHtml("Net charge proxy", _rchkFmt(mc.net_charge_proxy, 1), "", "Approximate net charge at neutral pH.")}
    </div>`;

  let deltaHtml = "";
  if (donorDev.pI != null) {
    const dRows = [
      ["pI", donorDev.pI, mc.pI, delta.pI, 2],
      ["GRAVY", donorDev.gravy, mc.gravy, delta.gravy, 3],
      ["Instability", donorDev.instability_index, mc.instability_index, delta.instability_index, 1],
    ].map(([lbl, d, c, dlt, dp]) => {
      const dltStr = dlt != null ? (dlt >= 0 ? "+" : "") + _rchkFmt(dlt, dp) : "—";
      const tone = dlt == null ? "" : (Math.abs(Number(dlt)) <= (lbl === "pI" ? 0.5 : lbl === "GRAVY" ? 0.05 : 5.0) ? "ok" : "warn");
      return `<tr><td>${lbl}</td><td class="mono">${_rchkFmt(d, dp)}</td><td class="mono">${_rchkFmt(c, dp)}</td><td class="mono"><span class="badge badge-${tone === "ok" ? "ok" : "warn"}" style="padding:1px 8px">${dltStr}</span></td></tr>`;
    }).join("");
    deltaHtml = `<table class="kv-table" style="margin-top:10px"><thead><tr><th>Metric</th><th>Donor</th><th>Candidate</th><th>Δ (Cand − Donor)</th></tr></thead><tbody>${dRows}</tbody></table>`;
  }

  // AbNatiV VHH naturalness
  const dvhh2 = (nat.donor || {}).vhh2;
  const cvhh2 = (nat.humanized || {}).vhh2;
  const dltvhh2 = nat.delta_vhh2;
  const dvh2 = (nat.donor || {}).vh2;
  const cvh2 = (nat.humanized || {}).vh2;
  const dltvh2 = nat.delta_vh2;
  const natMetricsHtml = `<div class="metric-grid recheck-row-5">
      ${metricHtml("VHH2 — donor", dvhh2 != null ? _rchkFmt(dvhh2, 3) : "—", "", "AbNatiV VHH2 likelihood for donor.")}
      ${metricHtml("VHH2 — candidate", cvhh2 != null ? _rchkFmt(cvhh2, 3) : "—", _rchkToneByScore(cvhh2, 0.75, 0.6), "AbNatiV VHH2 likelihood for candidate.")}
      ${metricHtml("Δ VHH2", dltvhh2 != null ? (dltvhh2 >= 0 ? "+" : "") + _rchkFmt(dltvhh2, 3) : "—", dltvhh2 == null ? "" : (dltvhh2 >= -0.05 ? "ok" : dltvhh2 >= -0.15 ? "warn" : "fail"), "Drop tolerated up to −0.15. >−0.15 = ok.")}
      ${metricHtml("Δ VH2 (human VH)", dltvh2 != null ? (dltvh2 >= 0 ? "+" : "") + _rchkFmt(dltvh2, 3) : "—", dltvh2 == null ? "" : (dltvh2 >= 0 ? "ok" : "warn"), "Improvement of human VH2 likelihood.")}
      ${metricHtml("HPR Index", hprScore != null ? _rchkFmt(hprScore, 3) : "—", _rchkToneByScore(hprScore, 0.7, 0.6), "9-mer human peptide repertoire compatibility.")}
    </div>`;

  return `
    ${formatRunMetadataHtml(service, data, [
      r.project_name ? `<tr><th>Project / sequence ID</th><td class="mono">${escapeHtml(String(r.project_name))}</td></tr>` : "",
      `<tr><th>Service</th><td>VHH Customer Recheck</td></tr>`,
      `<tr><th>Clean mode</th><td>${escapeHtml(r.clean_mode || "—")}</td></tr>`,
    ].filter(Boolean))}
    ${_rchkDownloadsBar(data)}

    <section class="result-panel">
      ${_rchkPanelHeader("§0 Overall verdict", overallStatus)}
      <div class="result-body">
        <div class="metric-grid recheck-row-5">
          ${metricHtml("Input QC", inputQc, badgeTone(inputQc) === "pass" ? "ok" : (badgeTone(inputQc) === "fail" ? "fail" : "warn"))}
          ${metricHtml("Structure QC", structQc, badgeTone(structQc) === "pass" ? "ok" : (badgeTone(structQc) === "fail" ? "fail" : "warn"))}
          ${metricHtml("Mini-CMC", cmcStatus, badgeTone(cmcStatus) === "pass" ? "ok" : (badgeTone(cmcStatus) === "fail" ? "fail" : "warn"))}
          ${metricHtml("AbNatiV VHH", natStatus, badgeTone(natStatus) === "pass" ? "ok" : (badgeTone(natStatus) === "fail" ? "fail" : "warn"))}
          ${metricHtml("HPR Index", hprStatus, badgeTone(hprStatus) === "pass" ? "ok" : "warn")}
        </div>
        <div style="margin-top:10px;padding:10px 12px;background:rgba(217,119,6,.06);border-left:3px solid #d97706;border-radius:0 6px 6px 0;font-size:12px;line-height:1.6"><strong>Recommendation</strong> &mdash; ${_rchkRecommendationHtml(r.recommendation || "")}</div>
      </div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§1 Structure conservation (Donor vs Candidate)", structQc)}
      <div class="result-body">${structMetricsHtml}</div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§2 Developability (Mini-CMC)", cmcStatus)}
      <div class="result-body">
        ${cmcMetricsHtml}
        ${flagsHtml}
        ${deltaHtml}
      </div>
    </section>

    <section class="result-panel">
      ${_rchkPanelHeader("§3 Humanization analysis", natStatus)}
      <div class="result-body">${natMetricsHtml}</div>
    </section>

    <p class="muted" style="margin-top:14px;font-size:11px">Same files appear under <strong>DOWNLOADS</strong> on the right for convenience.</p>
  `;
}

async function runRecheckVhvl(service) {
  const donorVh = normalizeSeq(document.getElementById("rchk-vhvl-donor-vh").value);
  const donorVl = normalizeSeq(document.getElementById("rchk-vhvl-donor-vl").value);
  const candVh = normalizeSeq(document.getElementById("rchk-vhvl-cand-vh").value);
  const candVl = normalizeSeq(document.getElementById("rchk-vhvl-cand-vl").value);
  const errors = [
    validateSeq(donorVh, "Donor VH", 80, 170),
    validateSeq(donorVl, "Donor VL", 80, 170),
    validateSeq(candVh, "Candidate VH", 80, 170),
    validateSeq(candVl, "Candidate VL", 80, 170),
  ].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Input validation failed",
      summaryText: errors.join(" · "),
      metrics: [],
      recommendation: "Check donor/candidate VH/VL sequences and rerun.",
      artifacts: [],
      metadata: [],
    });
    return;
  }
  const payload = {
    mouse_vh: donorVh,
    mouse_vl: donorVl,
    candidate_vh: candVh,
    candidate_vl: candVl,
    project_name: (document.getElementById("rchk-vhvl-name").value || "").trim(),
    source_species: document.getElementById("rchk-vhvl-species").value || "mouse",
    clean_mode: document.getElementById("rchk-vhvl-clean").value || "detect",
    run_structure: !!document.getElementById("rchk-vhvl-struct").checked,
    report_format: "html",
  };
  const useAsync = true; // Always async — provides progress bar + cancel button
  setRunning("Submitting VH/VL recheck…", 0);
  setOutput("");
  window.__activeAsyncAbort = false;
  try {
    let data;
    if (useAsync) {
      const startRes = await apiFetch(apiJoin("recheck/vhvl/async"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const start = await startRes.json();
      if (!startRes.ok) throw new Error(start.detail || JSON.stringify(start));
      const jobId = start.job_id;
      window.__activeAsyncJobId = jobId;
      setAsyncJobCancelButtonsVisible(true);
      setRunning(`VH/VL recheck ${jobId} — queued — polling…`, 0);

      let poll;
      for (let i = 0; i < 600; i++) {
        await sleep(2000);
        if (window.__activeAsyncAbort) {
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          clearRunning();
          setOutput(errorPanel("Job cancelled by user."));
          return;
        }
        const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
        if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
        poll = await pr.json();
        const st = (poll.status || "").toLowerCase();
        const pct = poll.progress != null ? Number(poll.progress) : null;
        const note = (poll.progress_note && String(poll.progress_note).trim()) || st;
        setRunning(`VH/VL recheck ${jobId} — ${note}`, Number.isFinite(pct) ? pct : undefined);

        if (st === "done") {
          data = {
            job_id: jobId,
            status: "done",
            result: poll.result,
            report_url: poll.report_url,
            elapsed_sec: poll.elapsed_sec,
            extra: poll.extra,
          };
          break;
        }
        if (st === "failed" || st === "cancelled") {
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          clearRunning();
          const errMsg = poll.error || poll.progress_note || (st === "cancelled" ? "Job cancelled." : "Recheck failed.");
          setOutput(errorPanel(errMsg));
          updateResultRail({
            status: "FAIL",
            summaryTitle: st === "cancelled" ? "Recheck cancelled" : "VH/VL recheck failed",
            summaryText: errMsg,
            metrics: [],
            recommendation: st === "cancelled" ? "Job was aborted. Resubmit when ready." : "Check server logs and rerun.",
            artifacts: [],
            metadata: [{ label: "Job", value: jobId, mono: true }],
          });
          return;
        }
      }
      if (!data) throw new Error("VH/VL recheck timed out after polling limit.");
    } else {
      const res = await apiFetch(apiJoin("recheck/vhvl"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    }

    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    const r = data.result || {};
    const status = String(r.overall_status || data.status || "DONE").toUpperCase();
    const { reportUrl, zipUrl, arts } = buildRecheckArtifacts(data);
    const zipLine = zipUrl
      ? `<p style="margin-top:8px"><a href="${escapeHtml(zipUrl)}" rel="noopener">Download delivery ZIP</a> <span class="muted">(README, FASTA, HTML, JSON; PDBs if structure QC succeeded)</span></p>`
      : `<p class="muted" style="margin-top:8px">No delivery ZIP link returned — check API job storage or server logs.</p>`;
    setOutput(renderRecheckVhvlResult(r, data, service, status));
    updateResultRail({
      status,
      summaryTitle: "VH/VL Recheck",
      summaryText: r.recommendation || "Completed.",
      metrics: [
        { label: "Input QC", value: (r.input_qc || {}).status || "—" },
        {
          label: "Structure QC",
          value: (r.structure_qc || {}).status || "—",
          sub: r.structure_qc && r.structure_qc.global_fv_rmsd_ca != null
            ? `Global RMSD: <b>${r.structure_qc.global_fv_rmsd_ca}Å</b>${r.structure_qc.angle_delta_deg != null ? ` · Angle Δ: <b>${r.structure_qc.angle_delta_deg}°</b>` : ""}${r.structure_qc.cdr_rmsd ? `<br>CDR RMSD: ${Object.entries(r.structure_qc.cdr_rmsd).map(([k,v]) => `${k}=<b>${v}</b>`).join(", ")}` : ""}`
            : "Structure not predicted",
        },
        {
          label: "Mini-CMC",
          value: (((r.mini_cmc || {}).candidate || {}).status) || "—",
          sub: r.mini_cmc && r.mini_cmc.candidate && r.mini_cmc.candidate.pI != null
            ? `pI: <b>${r.mini_cmc.candidate.pI}</b> · GRAVY: <b>${r.mini_cmc.candidate.gravy}</b> · Instab: <b>${r.mini_cmc.candidate.instability_index}</b>`
            : "",
        },
        {
          label: "Paired Naturalness",
          value: (r.naturalness || {}).status || "—",
          sub: r.naturalness && r.naturalness.paired_humanness != null
            ? `Paired humanness: <b>${r.naturalness.paired_humanness}</b>`
            : "",
        },
        {
          label: "HPR Index",
          value: r.hpr_index && r.hpr_index.humanized && r.hpr_index.humanized.combined && r.hpr_index.humanized.combined.score != null
            ? (r.hpr_index.humanized.combined.score > 0.6 ? "PASS" : "WARN")
            : "—",
          sub: r.hpr_index && r.hpr_index.humanized && r.hpr_index.humanized.combined && r.hpr_index.humanized.combined.score != null
            ? `Score: <b>${r.hpr_index.humanized.combined.score}</b>`
            : "",
        },
      ],
      recommendation: "Review report and decide release / optimization route.",
      artifacts: arts,
      metadata: [{ label: "Job", value: data.job_id || "—", mono: true }],
    });
  } catch (err) {
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    setOutput(errorPanel(err.message || String(err)));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "VH/VL recheck failed",
      summaryText: err.message || String(err),
      metrics: [],
      recommendation: "Verify API route /recheck/vhvl and payload fields.",
      artifacts: [],
      metadata: [],
    });
  }
}

async function runRecheckVhh(service) {
  const donor = normalizeSeq(document.getElementById("rchk-vhh-donor").value);
  const cand = normalizeSeq(document.getElementById("rchk-vhh-cand").value);
  const errors = [
    validateSeq(donor, "Donor VHH", 80, 200),
    validateSeq(cand, "Candidate VHH", 80, 200),
  ].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Input validation failed",
      summaryText: errors.join(" · "),
      metrics: [],
      recommendation: "Check donor/candidate VHH sequences and rerun.",
      artifacts: [],
      metadata: [],
    });
    return;
  }
  const payload = {
    donor_vhh: donor,
    candidate_vhh: cand,
    project_name: (document.getElementById("rchk-vhh-name").value || "").trim(),
    source_species: document.getElementById("rchk-vhh-species").value || "alpaca",
    clean_mode: document.getElementById("rchk-vhh-clean").value || "detect",
    run_structure: !!document.getElementById("rchk-vhh-struct").checked,
    report_format: "html",
  };
  const useAsync = true; // Always async — provides progress bar + cancel button
  setRunning("Submitting VHH recheck…", 0);
  setOutput("");
  window.__activeAsyncAbort = false;
  try {
    let data;
    if (useAsync) {
      const startRes = await apiFetch(apiJoin("recheck/vhh/async"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const start = await startRes.json();
      if (!startRes.ok) throw new Error(start.detail || JSON.stringify(start));
      const jobId = start.job_id;
      window.__activeAsyncJobId = jobId;
      setAsyncJobCancelButtonsVisible(true);
      setRunning(`VHH recheck ${jobId} — queued — polling…`, 0);

      let poll;
      for (let i = 0; i < 600; i++) {
        await sleep(2000);
        if (window.__activeAsyncAbort) {
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          clearRunning();
          setOutput(errorPanel("Job cancelled by user."));
          return;
        }
        const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
        if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
        poll = await pr.json();
        const st = (poll.status || "").toLowerCase();
        const pct = poll.progress != null ? Number(poll.progress) : null;
        const note = (poll.progress_note && String(poll.progress_note).trim()) || st;
        setRunning(`VHH recheck ${jobId} — ${note}`, Number.isFinite(pct) ? pct : undefined);

        if (st === "done") {
          data = {
            job_id: jobId,
            status: "done",
            result: poll.result,
            report_url: poll.report_url,
            elapsed_sec: poll.elapsed_sec,
            extra: poll.extra,
          };
          break;
        }
        if (st === "failed" || st === "cancelled") {
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          clearRunning();
          const errMsg = poll.error || poll.progress_note || (st === "cancelled" ? "Job cancelled." : "Recheck failed.");
          setOutput(errorPanel(errMsg));
          updateResultRail({
            status: "FAIL",
            summaryTitle: st === "cancelled" ? "Recheck cancelled" : "VHH recheck failed",
            summaryText: errMsg,
            metrics: [],
            recommendation: st === "cancelled" ? "Job was aborted. Resubmit when ready." : "Check server logs and rerun.",
            artifacts: [],
            metadata: [{ label: "Job", value: jobId, mono: true }],
          });
          return;
        }
      }
      if (!data) throw new Error("VHH recheck timed out after polling limit.");
    } else {
      const res = await apiFetch(apiJoin("recheck/vhh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    }

    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    const r = data.result || {};
    const status = String(r.overall_status || data.status || "DONE").toUpperCase();
    const { reportUrl, zipUrl, arts } = buildRecheckArtifacts(data);
    const zipLine = zipUrl
      ? `<p style="margin-top:8px"><a href="${escapeHtml(zipUrl)}" rel="noopener">Download delivery ZIP</a> <span class="muted">(README, FASTA, HTML, JSON; PDBs if structure QC succeeded)</span></p>`
      : `<p class="muted" style="margin-top:8px">No delivery ZIP link returned — check API job storage or server logs.</p>`;
    setOutput(renderRecheckVhhResult(r, data, service, status));
    updateResultRail({
      status,
      summaryTitle: "VHH Recheck",
      summaryText: r.recommendation || "Completed.",
      metrics: [
        { label: "Input QC", value: (r.input_qc || {}).status || "—" },
        {
          label: "Structure QC",
          value: (r.structure_qc || {}).status || "—",
          sub: r.structure_qc && r.structure_qc.global_fv_rmsd_ca != null
            ? `Global RMSD: <b>${r.structure_qc.global_fv_rmsd_ca}Å</b>${r.structure_qc.cdr_rmsd ? `<br>CDR RMSD: ${Object.entries(r.structure_qc.cdr_rmsd).map(([k,v]) => `${k}=<b>${v}</b>`).join(", ")}` : ""}`
            : "Structure not predicted",
        },
        {
          label: "Mini-CMC",
          value: (((r.mini_cmc || {}).candidate || {}).status) || "—",
          sub: r.mini_cmc && r.mini_cmc.candidate && r.mini_cmc.candidate.pI != null
            ? `pI: <b>${r.mini_cmc.candidate.pI}</b> · GRAVY: <b>${r.mini_cmc.candidate.gravy}</b> · Instab: <b>${r.mini_cmc.candidate.instability_index}</b>`
            : "",
        },
        {
          label: "Naturalness (AbNatiV VHH2)",
          value: (r.naturalness || {}).status || "—",
          sub: r.naturalness && r.naturalness.delta_vhh2 != null
            ? `Δ VHH2: <b>${r.naturalness.delta_vhh2}</b>${r.naturalness.humanized && r.naturalness.humanized.vhh2 != null ? ` · Cand VHH2: <b>${r.naturalness.humanized.vhh2}</b>` : ""}`
            : "",
        },
        {
          label: "HPR Index",
          value: r.hpr_index && r.hpr_index.humanized && r.hpr_index.humanized.combined && r.hpr_index.humanized.combined.score != null
            ? (r.hpr_index.humanized.combined.score > 0.6 ? "PASS" : "WARN")
            : "—",
          sub: r.hpr_index && r.hpr_index.humanized && r.hpr_index.humanized.combined && r.hpr_index.humanized.combined.score != null
            ? `Score: <b>${r.hpr_index.humanized.combined.score}</b>`
            : "",
        },
      ],
      recommendation: "Review report and decide release / optimization route.",
      artifacts: arts,
      metadata: [{ label: "Job", value: data.job_id || "—", mono: true }],
    });
  } catch (err) {
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    setOutput(errorPanel(err.message || String(err)));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "VHH recheck failed",
      summaryText: err.message || String(err),
      metrics: [],
      recommendation: "Verify API route /recheck/vhh and payload fields.",
      artifacts: [],
      metadata: [],
    });
  }
}

// ── Structure (Fv) ImmuneBuilder ─────────────────────────────────────────────

/** Parse standard FASTA into {id, seq} (one sequence per record). */
function parseFvFastaRecords(text) {
  const recs = [];
  if (!text || !String(text).trim()) return recs;
  let cur = null;
  const buf = [];
  function flush() {
    if (!cur) return;
    const seq = buf.join("").replace(/[^A-Za-z]/g, "").toUpperCase();
    if (seq) recs.push({ id: cur, seq });
  }
  for (const line of String(text).split(/\r?\n/)) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith(">")) {
      flush();
      cur = t.slice(1).trim().split(/\s+/)[0];
      buf.length = 0;
    } else buf.push(t);
  }
  flush();
  return recs;
}

/**
 * Multi-pair VH/VL from FASTA:
 * (A) Blocks: >id then VH line, VL line
 * (B) Pairs: >base_H / VH seq, >base_L / VL seq
 */
function parseFvFastaPairs(text) {
  const out = [];
  const s = String(text || "").replace(/\r/g, "");
  const blocks = s.split(/^>/m).filter((b) => b.trim());
  for (const block of blocks) {
    const lines = block
      .trim()
      .split(/\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length >= 3) {
      const id = lines[0].split(/\s+/)[0];
      const vh = lines[1].replace(/[^A-Za-z]/g, "").toUpperCase();
      const vl = lines[2].replace(/[^A-Za-z]/g, "").toUpperCase();
      if (vh.length >= 90 && vl.length >= 85) out.push({ pair_id: id || `pair_${out.length + 1}`, vh, vl });
    }
  }
  if (out.length) return out;
  const recs = parseFvFastaRecords(text);
  const by = {};
  for (const { id, seq } of recs) {
    const m = id.match(/^(.*)_(H|L)$/i);
    if (m) {
      const base = m[1];
      const arm = m[2].toUpperCase();
      if (!by[base]) by[base] = {};
      by[base][arm] = seq;
    }
  }
  for (const [base, o] of Object.entries(by)) {
    if (o.H && o.L && o.H.length >= 90 && o.L.length >= 85) {
      out.push({ pair_id: base, vh: o.H, vl: o.L });
    }
  }
  return out;
}

async function runFvImmuneBuilder(service) {
  const demoId = document.getElementById("fv-demo").value;
  const batchEl = document.getElementById("fv-fasta-batch");
  const fileEl = document.getElementById("fv-fasta-file");
  let pairs = [];
  let batchText = (batchEl && batchEl.value.trim()) || "";
  if (!batchText && fileEl && fileEl.files && fileEl.files[0]) {
    try {
      batchText = await fileEl.files[0].text();
    } catch (e) {
      setOutput(errorPanel("Could not read FASTA file."));
      return;
    }
  }
  if (batchText) {
    pairs = parseFvFastaPairs(batchText);
    if (!pairs.length) {
      setOutput(errorPanel("FASTA: no valid VH/VL pairs. Use: >id + VH line + VL line, or >name_H / VH and >name_L / VL."));
      updateResultRail({
        status: "FAIL",
        summaryTitle: "FASTA parse",
        summaryText: "No pairs parsed.",
        metrics: [],
        recommendation: "Check the format help in the textarea placeholder.",
        artifacts: [],
        metadata: [],
      });
      return;
    }
  } else {
    const vh = normalizeSeq(document.getElementById("fv-vh").value);
    const vl = normalizeSeq(document.getElementById("fv-vl").value);
    const errors = [validateSeq(vh, "VH", 90, 150), validateSeq(vl, "VL", 85, 135)].filter(Boolean);
    if (errors.length) {
      setOutput(errorPanel(errors.join("\n")));
      updateResultRail({
        status: "FAIL",
        summaryTitle: "Input validation failed",
        summaryText: errors.join(" · "),
        metrics: [],
        recommendation: "Paste VH/VL or use FASTA batch.",
        artifacts: [],
        metadata: [],
      });
      return;
    }
    const fvPairName = (document.getElementById("fv-name") && document.getElementById("fv-name").value.trim()) || "";
    const pairId = fvPairName || demoId || "pair1";
    pairs = [{ pair_id: pairId, vh, vl }];
  }
  if (pairs.length > 15) {
    setOutput(errorPanel("Maximum 15 VH/VL pairs per job."));
    return;
  }

  await refreshServerWallet();
  syncWalletToState();
  if (!canAffordRun(state.service)) {
    const cost = serviceCreditCost(state.service);
    setOutput(
      errorPanel(
        `Insufficient credits. This run needs ${cost} per job. Current balance: ${state.credits.toLocaleString("en-US")}.`,
      ),
    );
    return;
  }

  setRunning("Submitting Fv job…");
  setOutput("");
  try {
    const res = await apiFetch(apiJoin("structure/fv_immunebuilder/async"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pairs }),
    });
    const start = await res.json();
    if (!res.ok) throw new Error(typeof start.detail === "string" ? start.detail : JSON.stringify(start.detail || start));
    const jobId = start.job_id;
    window.__activeAsyncJobId = jobId;
    window.__activeAsyncAbort = false;
    setAsyncJobCancelButtonsVisible(true);
    let poll;
    for (let i = 0; i < 480; i++) {
      await sleep(2000);
      if (window.__activeAsyncAbort) {
        clearRunning();
        setAsyncJobCancelButtonsVisible(false);
        window.__activeAsyncJobId = null;
        setOutput(
          errorPanel(
            "Polling stopped after cancel. The server may still run the current ImmuneBuilder step; check GET /jobs/{id} if needed."
          )
        );
        updateResultRail({
          status: "WARN",
          summaryTitle: "Cancelled",
          summaryText: "Client stopped polling.",
          metrics: [],
          recommendation: `Poll ${jobId} on the API or retry.`,
          artifacts: [],
          metadata: [{ label: "Job", value: jobId, mono: true }],
        });
        return;
      }
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
      if (!pr.ok) throw new Error(`Job poll failed: ${pr.status}`);
      poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      const ip = poll.progress != null ? Number(poll.progress) : NaN;
      setRunning(
        `ImmuneBuilder ${jobId} — ${st}${poll.progress != null ? ` (${poll.progress}%)` : ""}`,
        Number.isFinite(ip) ? ip : undefined
      );
      if (st === "done") break;
      if (st === "cancelled") break;
      if (st === "failed") throw new Error(poll.error || "Job failed");
    }
    const pst = poll ? (poll.status || "").toLowerCase() : "";
    if (pst === "cancelled") {
      clearRunning();
      setAsyncJobCancelButtonsVisible(false);
      window.__activeAsyncJobId = null;
      const result = poll.result || {};
      const rows = (result.pairs || []).map((p) => {
        if (p.ok) {
          const u = p.pdb_url ? apiJoin(String(p.pdb_url).replace(/^\/+/, "")) : "";
          return `<tr><td class="mono">${escapeHtml(p.pair_id)}</td><td><span class="run-status pass">OK</span></td><td>${u ? `<a href="${escapeHtml(u)}" download>Download PDB</a>` : "—"}</td></tr>`;
        }
        return `<tr><td class="mono">${escapeHtml(p.pair_id)}</td><td><span class="run-status fail">FAIL</span></td><td><pre class="mono" style="white-space:pre-wrap;font-size:11px">${escapeHtml((p.error || "").slice(0, 800))}</pre></td></tr>`;
      }).join("");
      setOutput(`
      <section class="result-panel">
        <div class="result-title"><strong>Fv models</strong><span class="run-status warn">CANCELLED</span></div>
        <div class="result-body">
          <p class="muted" style="margin-bottom:10px">Job <span class="mono">${escapeHtml(jobId)}</span> — partial results only.</p>
          <table class="kv-table">
            <thead><tr><th>Pair</th><th>Status</th><th>PDB / detail</th></tr></thead>
            <tbody>${rows || "<tr><td colspan=3>No pairs completed</td></tr>"}</tbody>
          </table>
        </div>
      </section>
    `);
      const okN = (result.pairs || []).filter((x) => x.ok).length;
      updateResultRail({
        status: "WARN",
        summaryTitle: "ImmuneBuilder cancelled",
        summaryText: poll.progress_note || `${okN}/${pairs.length} pair(s) completed before cancel.`,
        metrics: [
          { label: "Job", value: jobId, mono: true },
        ],
        recommendation: "Remaining pairs were not run after cancel.",
        artifacts: [],
        metadata: [],
      });
      return;
    }
    if (!poll || pst !== "done") throw new Error("Timed out waiting for Fv job (check server / conda anarcii).");
    clearRunning();
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;

    const runRecordId = `fv-${jobId}`;
    const debit = await recordRunDebit(state.service, { runRecordId, demoId: pairs.length > 1 ? "batch" : demoId, extra: { pairs: pairs.length } });
    const result = poll.result || {};
    const rows = (result.pairs || []).map((p) => {
      if (p.ok) {
        const u = p.pdb_url ? apiJoin(String(p.pdb_url).replace(/^\/+/, "")) : "";
        return `<tr><td class="mono">${escapeHtml(p.pair_id)}</td><td><span class="run-status pass">OK</span></td><td>${u ? `<a href="${escapeHtml(u)}" download>Download PDB</a>` : "—"}</td></tr>`;
      }
      return `<tr><td class="mono">${escapeHtml(p.pair_id)}</td><td><span class="run-status fail">FAIL</span></td><td><pre class="mono" style="white-space:pre-wrap;font-size:11px">${escapeHtml((p.error || "").slice(0, 800))}</pre></td></tr>`;
    }).join("");
    setOutput(`
      <section class="result-panel">
        <div class="result-title"><strong>Fv models</strong><span class="run-status pass">DONE</span></div>
        <div class="result-body">
          <p class="muted" style="margin-bottom:10px">${escapeHtml(result.tool || "ABodyBuilder2")} · Job <span class="mono">${escapeHtml(jobId)}</span> · ${pairs.length} pair(s) · ${debit.debited ? debit.debited + " credits" : ""}</p>
          <table class="kv-table">
            <thead><tr><th>Pair</th><th>Status</th><th>PDB / detail</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          ${pdbViewerLinksHtml()}
        </div>
      </section>
    `);
    const okN = (result.pairs || []).filter((x) => x.ok).length;
    updateResultRail({
      status: okN ? "PASS" : "WARN",
      summaryTitle: "ImmuneBuilder Fv",
      summaryText: `${okN}/${pairs.length} PDB(s) generated.`,
      metrics: [
        { label: "Job", value: jobId, mono: true },
        { label: "Pairs", value: String(pairs.length) },
        { label: "OK", value: String(okN) },
      ],
      recommendation:
        okN < pairs.length
          ? "Some pairs failed — check conda env `anarcii`, ImmuneBuilder install, or INSYNBIO_IMMUNEBUILDER_PYTHON in server env."
          : "Download PDBs above; open in ChimeraX / PyMOL.",
      artifacts: (result.pairs || [])
        .filter((p) => p.ok && p.pdb_url)
        .map((p) => ({
          label: `PDB ${p.pair_id}`,
          url: apiJoin(String(p.pdb_url).replace(/^\/+/, "")),
          download: true,
          primary: false,
        })),
      metadata: [
        { label: "Demo / batch", value: pairs.length > 1 ? "multi-FASTA" : demoId, mono: true },
        { label: "Elapsed", value: poll.elapsed_sec != null ? `${fmt(poll.elapsed_sec, 1)}s` : "—" },
      ],
    });
  } catch (err) {
    clearRunning();
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    setOutput(errorPanel(err.message));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Fv modeling failed",
      summaryText: err.message,
      metrics: [],
      recommendation: "Ensure API is on :8000 and ImmuneBuilder runs under conda env anarcii (see server logs).",
      artifacts: [],
      metadata: [],
    });
  }
}

// ── VH/VL Humanization ────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runVhvlHumanization(service) {
  const vh = normalizeSeq(document.getElementById("vhvl-vh").value);
  const vl = normalizeSeq(document.getElementById("vhvl-vl").value);
  const demoId = document.getElementById("vhvl-demo").value;
  const species = (document.getElementById("vhvl-species") && document.getElementById("vhvl-species").value) || "mouse";
  try {
    sessionStorage.setItem("insynbio_last_vhvl_source_species", species);
  } catch (e) {}
  const errors = [validateSeq(vh, "VH", 100, 145), validateSeq(vl, "VL", 95, 130)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the sequence input before rerunning.", artifacts:[], metadata:[]});
    return;
  }
  const useAsync = document.getElementById("vhvl-async") && document.getElementById("vhvl-async").checked;
  const seqNameRaw = (document.getElementById("vhvl-name") && document.getElementById("vhvl-name").value.trim()) || "";
  
  const selectedRunMode = (document.querySelector('input[name="vhvl-run-mode"]:checked') || {}).value || "standard_delivery";
  const vhvlRunSettings = {
    quick_preview: {label: "Quick Preview", repairMode: "standard", dryRunStructure: true, surfaceFallback: false},
    standard_delivery: {label: "Standard Delivery", repairMode: "standard", dryRunStructure: false, surfaceFallback: true},
    enhanced_rescue: {label: "Enhanced Rescue Evaluation", repairMode: "rescue", dryRunStructure: false, surfaceFallback: true},
  }[selectedRunMode] || {label: "Standard Delivery", repairMode: "standard", dryRunStructure: false, surfaceFallback: true};

    const payload = {
    vh_sequence: vh, vl_sequence: vl,
    project_name: seqNameRaw,
    source_species: species,
    report_format: document.getElementById("vhvl-format").value,
    report_language: "en",
    repair_mode: vhvlRunSettings.repairMode,
    back_mutation_strategy: "auto",
    dry_run_structure: vhvlRunSettings.dryRunStructure,
    skip_iedb: true,
    surface_reshape_on_qc_fail: vhvlRunSettings.surfaceFallback,
  };
  if (useAsync) {
    setRunning(`Submitting ${vhvlRunSettings.label} VH/VL job…`, 0);
  } else {
    setRunning(
      `Running VH/VL in ${vhvlRunSettings.label} mode (single HTTP request — browser shows no step-by-step %; enable “Background job” above for live progress)…`
    );
  }
  window.__vhvlLastVH = vh;   // saved for FR/CDR comparison
  window.__vhvlLastVL = vl;
  setOutput("");
  try {
    let data;
    if (useAsync) {
      const res = await apiFetch(apiJoin("humanize/vh_vl/async"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const start = await res.json();
      if (!res.ok) throw new Error(start.detail || JSON.stringify(start));
      const jobId = start.job_id;
      window.__activeAsyncJobId = jobId;
      window.__activeAsyncAbort = false;
      setAsyncJobCancelButtonsVisible(true);
      setRunning(`Job ${jobId} — queued — polling every 3s for live %…`, 0);
      let poll;
      let consecutivePollErrors = 0;
      for (let i = 0; i < 1200; i++) {
        await sleep(3000);
        if (window.__activeAsyncAbort) {
          clearRunning();
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          setOutput(errorPanel("Polling stopped after cancel. The server may still finish the current pipeline step; check GET /jobs/{id}."));
          updateResultRail({
            status: "WARN",
            summaryTitle: "Cancelled",
            summaryText: "Client stopped polling.",
            metrics: [],
            recommendation: `Poll job ${jobId} on the API or retry.`,
            artifacts: [],
            metadata: [{ label: "Job", value: jobId, mono: true }],
          });
          return;
        }
        try {
          const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
          if (!pr.ok) throw new Error(`HTTP ${pr.status}`);
          poll = await pr.json();
          consecutivePollErrors = 0;
        } catch (pollErr) {
          consecutivePollErrors += 1;
          const pollMsg = pollErr && pollErr.message ? pollErr.message : String(pollErr);
          if (consecutivePollErrors <= 20) {
            setRunning(
              `VH/VL job ${jobId} — temporary polling issue (${consecutivePollErrors}/20): ${pollMsg}. Retrying…`,
              poll && Number.isFinite(Number(poll.progress)) ? Number(poll.progress) : undefined
            );
            continue;
          }
          throw new Error(`Job poll failed after retries: ${pollMsg}. The server may still be running; check /jobs/${jobId}.`);
        }
        const st = (poll.status || "").toLowerCase();
        const pct = poll.progress != null ? `${poll.progress}%` : "";
        const note = (poll.progress_note && String(poll.progress_note).trim()) || "";
        const prNum = poll.progress != null ? Number(poll.progress) : null;
        setRunning(
          `VH/VL job ${jobId} — ${st}${pct ? ` · ${pct}` : ""}` +
            (note ? ` · ${note}` : ""),
          Number.isFinite(prNum) ? prNum : undefined
        );
        if (st === "done") {
          data = { job_id: jobId, status: "done", result: poll.result, report_url: poll.report_url,
            elapsed_sec: poll.elapsed_sec, extra: poll.extra };
          break;
        }
        if (st === "cancelled") {
          data = { job_id: jobId, status: "cancelled", result: poll.result, report_url: poll.report_url,
            elapsed_sec: poll.elapsed_sec, extra: poll.extra };
          break;
        }
        if (st === "failed") throw new Error(poll.error || "Job failed");
      }
      setAsyncJobCancelButtonsVisible(false);
      window.__activeAsyncJobId = null;
      if (data && (data.status || "").toLowerCase() === "cancelled") {
        clearRunning();
        setOutput(errorPanel(poll.progress_note || "VH/VL job was cancelled."));
        updateResultRail({
          status: "WARN",
          summaryTitle: "VH/VL cancelled",
          summaryText: poll.progress_note || "Server reported cancelled status.",
          metrics: [],
          recommendation: "Partial files may exist under the job directory on the server.",
          artifacts: [],
          metadata: [{ label: "Job", value: jobId, mono: true }],
        });
        return;
      }
      if (!data) throw new Error("Timed out waiting for VH/VL job (max ~30 min). Check /docs or server logs.");
    } else {
      const res = await apiFetch(apiJoin("humanize/vh_vl"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    }
    clearRunning();
    const _vhvlRunId = `vhvl-${Date.now()}`;
    await recordRunDebit(state.service, { runRecordId: _vhvlRunId, demoId });
    renderVhvlResult(data, service, demoId);
  } catch (err) {
    clearRunning();
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"VH/VL humanization failed", summaryText:err.message, metrics:[], recommendation:"Inspect the error, then rerun with a validated donor pair.", artifacts:[], metadata:[]});
  }
}

function renderVhvlResult(data, service, demoId) {
  const r = data.result || {};
  const _hprBl = r.hpr_index || {};
  const _hprCombSc = (((_hprBl.humanized || {}).combined) || {}).score;
  const hprCombinedPct = _hprCombSc != null && !Number.isNaN(Number(_hprCombSc))
    ? (Number(_hprCombSc) * 100).toFixed(1) + "%"
    : null;
  const _pab = r.p_abnativ2 || {};
  const _abnativ_not_run_reason = String(r.structure_mode || "").toUpperCase() === "DRY_RUN" 
    ? "not run (structure required)" 
    : "not run";
  const pabLine = _pab.paired_humanness != null
    ? `${fmt(_pab.paired_humanness, 3)} (${_pab.paired_humanness_status || "—"})`
    : (_pab.error ? "error — see report" : _abnativ_not_run_reason);
  const vhCh = r.vh_fr_identity_chothia_cdr_masked != null ? r.vh_fr_identity_chothia_cdr_masked : r.vh_germline_identity;
  const vlCh = r.vl_fr_identity_chothia_cdr_masked != null ? r.vl_fr_identity_chothia_cdr_masked : r.vl_germline_identity;
  const bmVh = r.bm_candidates_vh || [];
  const bmVl = r.bm_candidates_vl || [];
  const bmVhRows = bmVh.map((s) => `<tr><td class="mono">${escapeHtml(String(s))}</td></tr>`).join("");
  const bmVlRows = bmVl.map((s) => `<tr><td class="mono">${escapeHtml(String(s))}</td></tr>`).join("");
  const speciesLabel = (r.source_species || "—").toString();
  try {
    if (r.humanized_vh && r.humanized_vl) {
      sessionStorage.setItem("insynbio_last_humanized_vh", String(r.humanized_vh));
      sessionStorage.setItem("insynbio_last_humanized_vl", String(r.humanized_vl));
      // r.project_name may be empty/null even when the user typed a name; fall back to
      // seqNameRaw which was captured from the form input before the API call.
      sessionStorage.setItem("insynbio_last_humanized_name", String(r.project_name || (document.getElementById("vhvl-name") && document.getElementById("vhvl-name").value.trim()) || ""));
      sessionStorage.setItem("insynbio_last_humanization_kind", "vhvl");
      sessionStorage.removeItem("insynbio_last_humanized_vhh");
    }
  } catch (e) {}
  const candRows = (r.candidates || []).slice(0, 5).map((c, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td class="mono">${c.vh_germline || "—"}</td>
      <td class="mono">${c.vl_germline || "—"}</td>
      <td>${fmt(c.vh_fr_id, 1)}%</td>
      <td>${fmt(c.vl_fr_id, 1)}%</td>
      <td>${fmt(c.score, 1)}%</td>
    </tr>
  `).join("");
  const phase2DegradedNote = r.phase2_degraded
    ? `<div class="helper" style="border-left:3px solid #c9a227;padding-left:10px;margin-bottom:12px;line-height:1.5"><strong>Degraded framework selection</strong> — clinical-anchor ranking did not complete; default human germlines were bound and FR% was computed. ${r.phase2_fallback_reason ? `<span class="mono" style="font-size:10px;display:block;margin-top:4px">${escapeHtml(String(r.phase2_fallback_reason))}</span>` : ""}</div>`
    : "";
  const _cfp = String(r.clinical_framework_policy || "");
  const _dsp = String(r.donor_species || "");
  const clinicalPoolNote =
    (!r.phase2_degraded &&
      (_cfp === "murine_rat_clinical_mandatory_no_extended" ||
        _dsp === "mus_musculus" ||
        _dsp === "rattus_norvegicus"))
      ? `<div class="helper" style="border-left:3px solid rgba(45,108,223,.35);padding-left:10px;margin-bottom:12px;line-height:1.45"><strong>Clinical framework pool</strong> — Mouse/rat donors: human VH/VL templates are restricted to the <strong>clinical-frequency anchor pool</strong> (no full Kabat-cache expansion).</div>`
      : (!r.phase2_degraded &&
          (_cfp === "rabbit_prefer_clinical_allow_extended" || _dsp === "oryctolagus_cuniculus"))
        ? `<div class="helper" style="border-left:3px solid rgba(45,108,223,.35);padding-left:10px;margin-bottom:12px;line-height:1.45"><strong>Clinical-first frameworks</strong> — Rabbit donors: prefer clinical-frequency anchors; a <strong>full Kabat V-gene scan</strong> applies only when the clinical pool does not pass the CDR gate on one or both chains (see “Extended germline search” if shown).</div>`
        : "";
  const phase2ExtNote = (!r.phase2_degraded && (r.phase2_extended_cache_scan_vh || r.phase2_extended_cache_scan_vl))
    ? `<div class="helper" style="border-left:3px solid rgba(33,199,217,.45);padding-left:10px;margin-bottom:12px;line-height:1.45"><strong>Extended germline search</strong> — Clinical-frequency anchors did not pass the CDR gate on one or both chains; the pipeline scanned the <strong>full human IGHV / IG(K/L)V Kabat cache</strong> for compatible alleles (<strong>rabbit</strong> workflow — mouse/rat use clinical anchors only). Mode: <span class="mono">${escapeHtml(String(r.selection_mode || "—"))}</span>.</div>`
    : "";
  const HPR_PRINCIPLE_TOOLTIP =
    "HPR Index (Human Peptide Repertoire Compatibility): VH and VL are scanned with overlapping 9-amino-acid peptides; each peptide is checked against a curated human antibody repertoire reference (human-OAS via local promb DB). The combined score is the fraction of peptides found — higher means better local peptide continuity with human antibody-derived sequences. It is a repertoire-compatibility screen, not binding affinity, structure proof, or clinical immunogenicity.";
  const vhvlProj = (r.project_name || "").toString().trim();
  const vhvlComparisonHtml = (() => {
    const donorVh = window.__vhvlLastVH || "";
    const donorVl = window.__vhvlLastVL || "";
    const humVh = r.humanized_vh || "";
    const humVl = r.humanized_vl || "";
    if (!donorVh || !humVh) return "";

    const scVhApi = r.sequence_comparison_vh || {};
    const scVlApi = r.sequence_comparison_vl || {};
    const useApiVh = Array.isArray(scVhApi.regions) && scVhApi.regions.length;
    const useApiVl = Array.isArray(scVlApi.regions) && scVlApi.regions.length;

    function splitImgtVhFallback(seq) {
      const s = (seq || "").toUpperCase();
      const len = s.length;
      const fr4start = Math.max(107, len - 11);
      const cdr3end = fr4start;
      const cdr3start = Math.min(95, cdr3end - 4);
      return [
        { region: "FR1",  seq: s.slice(0, 26),          is_cdr: false },
        { region: "CDR1", seq: s.slice(26, 35),         is_cdr: true  },
        { region: "FR2",  seq: s.slice(35, 50),         is_cdr: false },
        { region: "CDR2", seq: s.slice(50, 66),         is_cdr: true  },
        { region: "FR3",  seq: s.slice(66, cdr3start),  is_cdr: false },
        { region: "CDR3", seq: s.slice(cdr3start, cdr3end), is_cdr: true },
        { region: "FR4",  seq: s.slice(cdr3end),         is_cdr: false },
      ];
    }
    function splitImgtVlFallback(seq) {
      const s = (seq || "").toUpperCase();
      const len = s.length;
      const fr4start = Math.max(99, len - 10);
      const cdr3end = fr4start;
      const cdr3start = Math.min(89, cdr3end - 4);
      return [
        { region: "FR1",  seq: s.slice(0, 24),          is_cdr: false },
        { region: "CDR1", seq: s.slice(24, 40),         is_cdr: true  },
        { region: "FR2",  seq: s.slice(40, 55),         is_cdr: false },
        { region: "CDR2", seq: s.slice(55, 61),         is_cdr: true  },
        { region: "FR3",  seq: s.slice(61, cdr3start),  is_cdr: false },
        { region: "CDR3", seq: s.slice(cdr3start, cdr3end), is_cdr: true },
        { region: "FR4",  seq: s.slice(cdr3end),        is_cdr: false },
      ];
    }

    function buildRegionsFromApi(sc) {
      return (sc.regions || []).map((rg) => ({
        region: rg.region,
        donor_seq: rg.donor_seq || "",
        humanized_seq: rg.humanized_seq || "",
        is_cdr: !!rg.is_cdr,
        n_mutations: rg.is_cdr ? (rg.n_mutations || 0) : (rg.n_mutations || 0),
      }));
    }

    function buildRegionsFallback(donorSeq, humSeq, splitFn) {
      const dParts = splitFn(donorSeq);
      const hParts = splitFn(humSeq);
      return dParts.map((dp, i) => {
        const ds = dp.seq;
        const hs = hParts[i].seq;
        let nMut = 0;
        const ml = Math.min(ds.length, hs.length);
        for (let j = 0; j < ml; j++) if (ds[j] !== hs[j]) nMut++;
        nMut += Math.abs(ds.length - hs.length);
        return { region: dp.region, donor_seq: ds, humanized_seq: hs,
          is_cdr: dp.is_cdr, n_mutations: nMut };
      });
    }

    function countSeqDiff(ds, hs) {
      let n = 0;
      const ml = Math.min((ds || "").length, (hs || "").length);
      for (let j = 0; j < ml; j++) if (ds[j] !== hs[j]) n++;
      n += Math.abs((ds || "").length - (hs || "").length);
      return n;
    }

    // Only use API data — linear fallback produces wrong CDR boundaries (0-indexed vs Kabat).
    // If server hasn't been updated, hide the table and show a clear prompt instead.
    const vhRegions = useApiVh ? buildRegionsFromApi(scVhApi) : null;
    const vlRegions = (donorVl && humVl && useApiVl) ? buildRegionsFromApi(scVlApi) : null;
    const serverMissing = !useApiVh;

    function renderChainTable(regions, chainLabel) {
      const totalFrMut = regions.filter(rg => !rg.is_cdr).reduce((s, rg) =>
        s + countSeqDiff(rg.donor_seq || "", rg.humanized_seq || ""), 0);
      const rows = regions.map((reg) => {
        const isCdr = reg.is_cdr;
        const ds = reg.donor_seq || "";
        const hs = reg.humanized_seq || "";
        const maxLen = Math.max(ds.length, hs.length);
        // Status must match highlighted columns — always recount from displayed strings
        const nMut = countSeqDiff(ds, hs);
        let donorHtml = "";
        let humHtml = "";
        for (let i = 0; i < maxLen; i++) {
          const da = ds[i] || "";
          const ha = hs[i] || "";
          if (da === ha) {
            donorHtml += escapeHtml(da || ha);
            humHtml += escapeHtml(da || ha);
          } else {
            donorHtml += `<b style="color:#c0392b">${escapeHtml(da || "·")}</b>`;
            humHtml += `<b style="color:#16a34a">${escapeHtml(ha || "·")}</b>`;
          }
        }
        let statusText;
        let statusColor;
        if (isCdr) {
          statusText = nMut === 0 ? "CDR — identical" : `CDR — ${nMut} aa differ`;
          statusColor = nMut === 0 ? "#92400e" : "var(--fail)";
        } else if (nMut === 0) {
          statusText = "—";
          statusColor = "#9ca3af";
        } else {
          statusText = `${nMut} change${nMut > 1 ? "s" : ""}`;
          statusColor = "#15803d";
        }
        return `<tr style="border-bottom:1px solid #e5e7eb;background:${isCdr ? "#fefce8" : "transparent"}">
          <td style="padding:5px 12px;font-size:12px;font-weight:700;color:#1e293b;white-space:nowrap">${reg.region}</td>
          <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">${donorHtml}</td>
          <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">${humHtml}</td>
          <td style="padding:5px 12px;font-size:11px;font-weight:600;color:${statusColor};text-align:center;white-space:nowrap">${statusText}</td>
        </tr>`;
      }).join("");
      return `
        <div style="margin-bottom:16px">
          <div style="font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:0.08em;margin-bottom:4px;padding:0 2px">
            ${chainLabel} — ${totalFrMut} FR position${totalFrMut !== 1 ? "s" : ""} changed
          </div>
          <table style="width:100%;border-collapse:collapse;font-family:sans-serif">
            <thead>
              <tr style="background:#334155">
                <th style="padding:6px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left;width:55px">Region</th>
                <th style="padding:6px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left">Donor</th>
                <th style="padding:6px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left">Humanized</th>
                <th style="padding:6px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:center;width:110px">Status</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }


    const apiScheme = scVhApi.scheme || scVlApi.scheme || "";

    return `
      <section class="result-panel">
        <div class="result-title">
          <strong>Sequence Comparison (FR / CDR)</strong>
          ${apiScheme ? `<span class="run-status ok" style="font-size:10px;margin-left:8px;background:#1e293b;color:#86efac;border:1px solid #15803d">${escapeHtml(apiScheme)}</span>` : ""}
        </div>
        <div class="result-body" style="padding:0">
          <div style="padding:10px 12px 0">
            ${serverMissing
              ? `<div style="padding:12px 14px;background:#fef3c7;border:1px solid #d97706;border-radius:6px;margin-bottom:8px">
                   <strong style="color:#92400e;font-size:12px">Server update required</strong>
                   <p style="margin:4px 0 0;font-size:11px;color:#78350f;line-height:1.5">
                     The API did not return Kabat-numbered CDR boundaries.<br/>
                     Run on server: <code style="background:#fff;padding:1px 5px;border-radius:3px">git pull origin master &amp;&amp; systemctl restart insynbio-api.service</code><br/>
                     The <strong>HTML report</strong> already has the correct CDR analysis.
                   </p>
                 </div>`
              : ""}
            ${r.sequence_comparison_error ? `<p class="muted" style="font-size:11px;margin:0 0 8px 0;color:var(--warn)">Comparison backend: ${escapeHtml(String(r.sequence_comparison_error))}</p>` : ""}
            ${vhRegions ? renderChainTable(vhRegions, "VH") : ""}
            ${vlRegions ? renderChainTable(vlRegions, "VL") : ""}
          </div>
          <p style="font-size:10px;color:#6b7280;padding:5px 12px;margin:0;border-top:1px solid rgba(255,255,255,0.05)">
            CDR boundaries: IMGT (CDR-H1 27–38 / CDR-H2 56–65) — same as HTML report §10. CDR rows should always be identical after successful humanization.<br/>
            <b style="color:#c0392b">Red</b> / <b style="color:#16a34a">Green</b> = framework substitution · Yellow rows = CDR
          </p>
        </div>
      </section>`;
  })();
  setOutput(`
    ${formatRunMetadataHtml(service, data, [
      vhvlProj ? `<tr><th>Project / sequence ID</th><td class="mono">${escapeHtml(vhvlProj)}</td></tr>` : "",
      `<tr><th>Donor species</th><td>${escapeHtml(speciesLabel)}</td></tr>`,
    ].filter(Boolean))}

    <!-- ══ SEQUENCES (FIRST, before QA) ══ -->
    <section class="result-panel">
      <div class="result-title">
        <strong>Humanized sequences</strong>
        <span class="run-status ${badgeTone(r.checklist_status || "DONE")}">${r.checklist_status || "DONE"}</span>
      </div>
      <div class="result-body">
        <div class="seq-box"><div class="label">Humanized VH</div><pre>${escapeHtml(r.humanized_vh || "")}</pre></div>
        <div class="seq-box" style="margin-top:12px"><div class="label">Humanized VL</div><pre>${escapeHtml(r.humanized_vl || "")}</pre></div>
        <p style="font-size:11px;color:var(--muted);margin-top:12px;line-height:1.5">
          <strong>Downstream modules</strong> (humanized VH/VL cached in this session for entry points below).<br/>
          <strong>AF2 Multimer:</strong> VH/VL + antigen ECD for complex modeling.<br/>
          <strong>CMC IgG:</strong> Clinical reference benchmarking, developability, liability scan — separate run; not bundled with humanization.
        </p>
        ${(() => {
          const arts = buildArtifacts(data, { htmlZipOnly: true });
          if (!arts.length) return "";
          const links = arts.map(a =>
            `<a class="btn${a.primary ? " primary" : ""}" href="${escapeHtml(a.url)}" ${a.download ? "download" : 'target="_blank"'}
              style="font-size:12px;padding:6px 14px;text-decoration:none;display:inline-block">${escapeHtml(a.label)}</a>`
          ).join("");
          return `<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center">
            <span class="panel-label" style="margin-right:4px">Downloads:</span>${links}</div>`;
        })()}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px;max-width:920px">
          <button type="button" class="btn offline-btn" onclick="goToAf2MultimerWithLastHumanization(false)">AF2 Multimer &amp; Complex</button>
          <button type="button" class="btn" style="border-color:var(--accent);color:var(--accent)" onclick="goToCmcIggWithLastHumanization()">Go to IgG CMC Snapshot</button>
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaWithLastHumanization(false)">cDNA Optimization (IgG) →</button>
        </div>
      </div>
    </section>

    ${vhvlComparisonHtml}

    <section class="result-panel">
      <div class="result-title"><strong>VH/VL humanization</strong><span class="run-status ${badgeTone(r.checklist_status || "DONE")}">${r.checklist_status || "DONE"}</span></div>
      ${phase2DegradedNote}
      ${clinicalPoolNote}
      ${phase2ExtNote}
      <div class="result-body">
        <table class="kv-table" style="margin-bottom:12px">
          <tr><th>Donor species</th><td>${escapeHtml(speciesLabel)}</td></tr>
          <tr><th>Selected VH germline</th><td class="mono">${escapeHtml(r.vh_germline || "—")}</td></tr>
          <tr><th>Selected VL germline</th><td class="mono">${escapeHtml(r.vl_germline || "—")}</td></tr>
        </table>
        <div class="metric-grid" style="grid-template-columns:repeat(5,minmax(0,1fr))">
          ${metricHtml("VH FR identity (pipeline: Chothia-masked)", `${fmt(vhCh, 1)}%`, vhCh != null && vhCh < 70 ? "warn" : "ok", "Framework region identity between humanized VH and the selected human germline, measured on Chothia-defined framework positions (CDRs masked). ≥70% is the clinical development standard; <70% triggers a warning.")}
          ${metricHtml("VL FR identity (pipeline: Chothia-masked)", `${fmt(vlCh, 1)}%`, vlCh != null && vlCh < 70 ? "warn" : "ok", "Framework region identity between humanized VL and the selected human germline, measured on Chothia-defined framework positions (CDRs masked). ≥70% is the clinical development standard.")}
          ${metricHtml("HPR Index (humanized Fv, combined)", hprCombinedPct || "not computed", hprCombinedPct ? "ok" : "warn", HPR_PRINCIPLE_TOOLTIP)}
          ${metricHtml("Paired Fv naturalness (p-AbNatiV)", pabLine, _pab.paired_humanness_status === "FAIL" ? "fail" : (_pab.paired_humanness_status === "WARN" ? "warn" : "ok"), "Paired Fv humanness score from the p-AbNatiV model. Measures how closely the humanized VH/VL pair matches human antibody repertoire sequences. Requires full structure prediction — reported as 'not run' in dry-run mode.")}
          ${metricHtml("Recommended back-mutations (HC rules)", r.backmutation_count ?? "0", "", "Number of Vernier-zone and buried residue back-mutations recommended by the HC rules engine. These positions are reverted to donor residues to preserve CDR conformation and binding.")}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Recommended back-mutations</strong></div>
      <div class="result-body">
        <p class="muted" style="font-size:11px;margin:0 0 8px 0">HC-rule recommendations applied in the assembled humanized sequence (V4.5.1). Empty lists mean no mandatory reversions under current rules.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div>
            <div class="panel-label" style="margin-bottom:6px">VH</div>
            <table class="cand-table"><tbody>${bmVhRows || "<tr><td class='muted'>None</td></tr>"}</tbody></table>
          </div>
          <div>
            <div class="panel-label" style="margin-bottom:6px">VL</div>
            <table class="cand-table"><tbody>${bmVlRows || "<tr><td class='muted'>None</td></tr>"}</tbody></table>
          </div>
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Top germline framework candidates</strong></div>
      <div class="result-body">
        <table class="cand-table">
          <thead><tr><th>#</th><th>VH germline</th><th>VL germline</th><th>VH FR % (pipeline)</th><th>VL FR % (pipeline)</th><th>Avg FR %</th></tr></thead>
          <tbody>${candRows || "<tr><td colspan='6' class='muted'>No candidate table returned.</td></tr>"}</tbody>
        </table>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Structural conservation</strong></div>
      <div class="result-body">
        <p class="muted" style="font-size:11px;margin:0 0 10px 0">
          Donor vs humanized Fv: per-CDR Cα RMSD, global Fv Cα RMSD (when available), VH/VL angle, pLDDT. Full developability: <strong>CMC IgG</strong> separately.
          ${r.structure_mode === "DRY_RUN" ? ' <span style="color:var(--warn)">[Structure not computed]</span>' : ""}
        </p>
        ${(/rabbit/i.test(String(r.source_species || "")) || String(r.donor_species || "").includes("oryctolagus"))
          ? `<p class="muted" style="font-size:11px;margin:0 0 10px 0;color:var(--warn)"><strong>Rabbit:</strong> CDR3 and L1 RMSD in predicted models often reflect flexible loops; weight <strong>H1 / H2 / L2</strong> deviations more heavily than CDR3/L1 alone.</p>`
          : ""}
        ${(() => {
          const rmsd = r.cdr_rmsd || {};
          const cdrs = ["H1","H2","H3","L1","L2","L3"];
          if (!cdrs.some(k => rmsd[k] != null) && r.rmsd_to_reference == null && r.global_fv_rmsd_ca == null) {
            return `<p class="muted">No structural RMSD data (structure not computed).</p>`;
          }
          const instSeries = [];
          const rows = [];
          if (r.rmsd_to_reference != null) {
            const mv = r.rmsd_to_reference;
            const tone = mv >= 1.5 ? "var(--fail)" : mv >= 1.0 ? "var(--warn)" : "var(--ok)";
            const bar = Math.min(Math.round(mv / 2.0 * 80), 80);
            rows.push(`<tr><th>Mean CDR Cα RMSD</th><td>${Number(mv).toFixed(2)} Å</td><td><div style="background:${tone};height:8px;width:${bar}px;border-radius:3px;display:inline-block"></div></td></tr>`);
          }
          if (r.global_fv_rmsd_ca != null && !Number.isNaN(Number(r.global_fv_rmsd_ca))) {
            const gv = Number(r.global_fv_rmsd_ca);
            const tone = gv >= 1.5 ? "var(--warn)" : "var(--ok)";
            const bar = Math.min(Math.round(gv / 2.0 * 80), 80);
            rows.push(`<tr><th>Global Fv Cα RMSD</th><td>${gv.toFixed(2)} Å</td><td><div style="background:${tone};height:8px;width:${bar}px;border-radius:3px;display:inline-block"></div></td></tr>`);
          }
          cdrs.forEach(k => {
            const v = rmsd[k];
            if (v == null) { rows.push(`<tr><th>CDR ${k}</th><td class="muted">—</td><td></td></tr>`); return; }
            const tone = v >= 1.5 ? "var(--fail)" : v >= 1.0 ? "var(--warn)" : "var(--ok)";
            const bar = Math.min(Math.round(v / 2.0 * 80), 80);
            rows.push(`<tr><th>CDR ${k}</th><td>${v.toFixed(2)} Å</td><td><div style="background:${tone};height:8px;width:${bar}px;border-radius:3px;display:inline-block"></div></td></tr>`);
          });
          return `<table class="kv-table">${rows.join("")}</table>`;
        })()}
        ${(() => {
          const resc = r.rescue || {};
          if (!resc.attempted) return "";
          const notes = resc.notes || [];
          let line = "Post-QC framework refinement applied.";
          if (notes.includes("vernier_round2_rescued")) line = "Output sequences: post-QC framework refinement.";
          else if (notes.includes("fallback_germline_rerun")) line = "Output sequences: alternate germline outcome for this run.";
          return `<p class="muted" style="font-size:11px;margin-top:12px;line-height:1.5;border-top:1px solid var(--border);padding-top:10px"><strong>Refinement:</strong> ${line}</p>`;
        })()}
        ${(() => {
          const plddt  = r.plddt;
          const angle  = r.vh_vl_angle_deg;
          const adelta = r.angle_delta_deg;
          const plddtH = r.humanized_plddt;
          const lines = [];
          const donorLabel = escapeHtml((r.source_species || "donor").toLowerCase());
          if (plddt != null || plddtH != null) {
            lines.push(`pLDDT (${donorLabel} / humanized): <strong>${plddt != null ? plddt : "—"}</strong> / <strong>${plddtH != null ? plddtH : "—"}</strong>`);
          }
          if (angle != null)  lines.push(`VH/VL angle (${donorLabel}): <strong>${angle}°</strong>`);
          if (adelta != null) lines.push(`Δangle (humanized − ${donorLabel}): <strong>${adelta > 0 ? "+" : ""}${adelta}°</strong>`);
          return lines.length ? `<p style="font-size:12px;margin:10px 0 6px 0">${lines.join(" &nbsp;·&nbsp; ")}</p>` : "";
        })()}
        ${(() => {
          const vRisk = r.vernier_risk_positions || [];
          const n = vRisk.length;
          if (!n) return "";
          const applied = [...(r.bm_candidates_vh || []), ...(r.bm_candidates_vl || [])].length;
          return `<p class="muted" style="font-size:11px;margin-top:10px;line-height:1.5">
            <strong>Vernier audit (T1/T2):</strong> ${n} FR position${n>1?"s":""} differ between donor and selected germline at Vernier-tier sites.
            ${applied > 0 ? `${applied} position${applied>1?"s":""} covered by recommended back-mutations above.` : "Positions without listed back-mutations remain on germline; donor reversion may be evaluated if binding loss appears in downstream assays."}
          </p>`;
        })()}
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Essential CMC developability</strong></div>
      <div class="result-body">
        <p class="muted" style="font-size:11px;margin:0 0 10px 0">Sequence-level physicochemical flags for the humanized antibody. Full CMC assessment available via the CMC IgG module.</p>
        ${(() => {
          const cmc   = r.mini_cmc || {};
          const pI    = r.pI_fab;
          const liab  = r.liabilities || [];
          const gates = r.cmc_species_gates || {};
          const instWarn = gates.instability_index_warn ?? 40;
          const piMin    = gates.pi_fab_min ?? 5.5;
          const piMax    = gates.pi_fab_max ?? 9.0;
          const species  = (r.source_species || "mouse").toLowerCase();
          const isNonMouse = species === "rabbit" || species === "rat";
          const piTone   = (pI != null && (pI < piMin || pI > piMax)) ? "warn" : "ok";
          const instTone = (cmc.instability_index != null && cmc.instability_index > instWarn) ? "warn" : "ok";
          const gravTone = (cmc.gravy != null && cmc.gravy > -0.1) ? "warn" : "ok";
          const instLabel = isNonMouse
            ? `Instability index [${species} gate: &lt;${instWarn}]`
            : `Instability index`;
          const piLabel = isNonMouse
            ? `pI (Fab) [${species} gate: ${piMin}–${piMax}]`
            : "pI (Fab)";
          const speciesNote = gates.note
            ? `<p style="font-size:10px;color:var(--warn);background:rgba(201,162,39,.08);border:1px solid rgba(201,162,39,.25);border-radius:4px;padding:5px 8px;margin-top:10px;line-height:1.5"><strong>Species-adjusted gates (${species}):</strong> ${escapeHtml(gates.note)}</p>`
            : "";
          return `
          <div class="metric-grid">
            ${metricHtml(piLabel, pI != null ? pI.toFixed(2) : "—", piTone, "Isoelectric point of the Fv (variable region). Preferred range 6.5–8.5 for optimal solubility and reduced self-association. Values outside 5.0–9.5 require developability justification.")}
            ${metricHtml(instLabel, cmc.instability_index != null ? cmc.instability_index.toFixed(1) : "—", instTone, `Recommend < ${instWarn} (Guruprasad et al. 1990). Values > ${instWarn} indicate elevated in vitro instability risk.`)}
            ${metricHtml("GRAVY", cmc.gravy != null ? cmc.gravy.toFixed(3) : "—", gravTone, "Grand Average of Hydropathicity. Negative values indicate hydrophilic character (preferred for solubility). Values > −0.1 suggest hydrophobic aggregation risk.")}
            ${metricHtml("Aromaticity", cmc.aromaticity != null ? cmc.aromaticity.toFixed(3) : "—", "ok", "Fraction of aromatic residues (Phe, Trp, Tyr) in the Fv. High aromaticity (>0.10) correlates with hydrophobic patch formation and elevated aggregation propensity.")}
            ${metricHtml("Length (VH+VL)", cmc.length != null ? String(cmc.length) : "—", "ok", "Total amino acid count of VH + VL. Standard Fv range: 210–240 aa. Unusually long sequences may indicate CDR insertions or non-standard framework regions.")}
          </div>
          ${speciesNote}
          ${liab.length ? `<div style="margin-top:10px"><div class="panel-label" style="margin-bottom:6px">Sequence liabilities</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px">${liab.map(v => `<span class="mono" style="background:rgba(201,100,39,.12);border:1px solid rgba(201,100,39,.3);border-radius:4px;padding:2px 7px;font-size:11px">${escapeHtml(String(v))}</span>`).join("")}</div></div>` : `<p class="muted" style="font-size:11px;margin-top:8px">No sequence liability flags.</p>`}`;
        })()}
      </div>
    </section>
  `);
  updateResultRail({
    status: r.checklist_status || "DONE",
    summaryTitle: "VH/VL humanization completed",
    summaryText: `Demo ${DEMOS[demoId] ? DEMOS[demoId].label : demoId} · ${service.analysisVersion} · donor ${speciesLabel}.`,
    metrics: [
      {label: "VH FR % (pipeline)", value: `${fmt(vhCh, 1)}%`, tone: vhCh != null && vhCh < 70 ? "warn" : "ok"},
      {label: "VL FR % (pipeline)", value: `${fmt(vlCh, 1)}%`, tone: vlCh != null && vlCh < 70 ? "warn" : "ok"},
      {label: "HPR Index (combined)", value: hprCombinedPct || "—", tone: hprCombinedPct ? "ok" : "warn"},
      {label: "p-AbNatiV paired", value: pabLine, tone: _pab.paired_humanness_status === "FAIL" ? "fail" : (_pab.paired_humanness_status === "WARN" ? "warn" : "ok")},
      {label: "Back mut.", value: String(r.backmutation_count ?? "0")},
    ],
    recommendation: (r.flags || []).length
      ? `Review flagged items before escalation. Key flags: ${(r.flags || []).slice(0, 3).join(" · ")}`
      : "Review the downloadable report and recommended back-mutations.",
    artifacts: buildArtifacts(data, { htmlZipOnly: true }),
    metadata: [
      {label: "Demo ID", value: demoId, mono: true},
      {label: "Job ID", value: data.job_id || "—", mono: true},
      {label: "Elapsed", value: data.elapsed_sec ? `${data.elapsed_sec}s` : "—"},
      {label: "Analysis version", value: service.analysisVersion, mono: true},
      ...(r.clinical_framework_policy
        ? [{label: "Framework policy", value: String(r.clinical_framework_policy), mono: true}]
        : []),
    ],
  });
}

// ── CMC IgG ───────────────────────────────────────────────────────────────────

let _cmcAbortCtrl = null;
let _currentCmcJobId = null;
let _activeJobId = null;

async function runCmcIgg(service) {
  // ── Clean slate: abort any lingering job, reset all shared state ──────────
  if (_cmcAbortCtrl && !_cmcAbortCtrl.signal.aborted) _cmcAbortCtrl.abort();
  _cmcAbortCtrl = null;
  _currentCmcJobId = null;
  _activeJobId = null;
  sessionStorage.removeItem("cmc_active_job");
  _cmcSetCancelVisible(false);
  const statusBox0 = document.getElementById("cmc-status-bar");
  if (statusBox0) statusBox0.innerHTML = "";

  const vh = normalizeSeq(document.getElementById("cmc-vh").value);
  const vl = normalizeSeq(document.getElementById("cmc-vl").value);
  const nameEl = document.getElementById("cmc-sequence-name");
  const sequenceName = (nameEl && nameEl.value.trim()) || "customer-vhvl";
  const demoId = document.getElementById("cmc-demo").value;
  const errors = [validateSeq(vh, "VH", 100, 145), validateSeq(vl, "VL", 95, 130)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the sequence input.", artifacts:[], metadata:[]});
    return;
  }

  // --- progress bar + cancel UI ---
  _cmcAbortCtrl = new AbortController();
  let pct = 0;
  const statusBox = document.getElementById("cmc-status-bar");
  function showProgress(p, label) {
    pct = Math.min(p, 99);
    const bar = `<div style="margin-top:8px">
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:3px">
        <span>${label}</span><span>${Math.round(pct)}%</span>
      </div>
      <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:var(--accent);transition:width .4s ease;border-radius:2px"></div>
      </div>
    </div>`;
    if (statusBox) statusBox.innerHTML = bar;
    else setRunning(label);
  }
  function clearProgress() {
    if (statusBox) statusBox.innerHTML = "";
    clearRunning();
    _cmcSetCancelVisible(false);
    sessionStorage.removeItem("cmc_active_job");
  }

  _cmcSetCancelVisible(true);
  showProgress(5, "Initializing CMC assessment…");
  const phases = [
    {pct:20, label:"Numbering & CMC metrics…"},
    {pct:45, label:"Physicochemical profiling…"},
    {pct:60, label:"FR mutation candidate scan…"},
    {pct:75, label:"In-silico Fv structure modeling…"},
    {pct:88, label:"SASA filter & mutation hints…"},
  ];
  let phaseIdx = 0;
  const progTimer = setInterval(() => {
    if (phaseIdx < phases.length) {
      showProgress(phases[phaseIdx].pct, phases[phaseIdx].label);
      phaseIdx++;
    }
  }, 3500);

  setOutput("");
  try {
    const res = await apiFetch(apiJoin("cmc/igg/async"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        vh_sequence: vh, vl_sequence: vl,
        antibody_type: document.getElementById("cmc-antibody-type").value,
        project_name: sequenceName,
        report_format: "html",
        predict_fv_structure: true,
        smart_cmc: !!(document.getElementById("cmc-smart-opt") && document.getElementById("cmc-smart-opt").checked),
      }),
      signal: _cmcAbortCtrl.signal,
    });
    clearInterval(progTimer);
    if (!res.ok) {
      let errMsg = `Server error ${res.status}`;
      try { const e = await res.json(); errMsg = e.detail || JSON.stringify(e); } catch { errMsg = `Server returned ${res.status} (non-JSON response — check if API is running)`; }
      throw new Error(errMsg);
    }
    const startData = await res.json();
    const jobId = startData.job_id;
    _activeJobId = jobId;
    _currentCmcJobId = jobId;
    // Persist job so navigating away and returning can re-attach
    sessionStorage.setItem("cmc_active_job", JSON.stringify({
      jobId, service: service?.id || "cmc_igg", sequenceName, demoId,
      startedAt: Date.now()
    }));

    // Polling loop
    let poll;
    let pollCount = 0;
    while (pollCount < 200) {
      if (_cmcAbortCtrl && _cmcAbortCtrl.signal.aborted) break;
      await new Promise(r => setTimeout(r, 3000));
      pollCount++;
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`), { signal: _cmcAbortCtrl?.signal });
      if (!pr.ok) throw new Error(`Job poll failed: ${pr.status}`);
      poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      const note = poll.progress_note || st;
      // Distinguish queue-waiting state from normal running for clearer UX
      const isQueueWait = st === "queued" && note.toLowerCase().includes("waiting for structure");
      if (isQueueWait) {
        showProgress(2, `⏳ CMC IgG — ${note}`);
      } else {
        showProgress(poll.progress || 0, `CMC IgG — ${note}`);
      }
      if (st === "done" || st === "failed" || st === "cancelled") break;
    }

    clearProgress();
    _currentCmcJobId = null;
    _activeJobId = null;
    if (!poll || poll.status === "failed") throw new Error(poll?.error || "Job failed");
    if (poll.status === "cancelled") {
      setOutput(`<div class="muted" style="padding:12px">CMC run cancelled.</div>`);
      return;
    }
    renderCmcIggResult(poll, service, demoId, sequenceName);
  } catch (err) {
    clearInterval(progTimer);
    clearProgress();
    _currentCmcJobId = null;
    _activeJobId = null;
    if (err.name === "AbortError") {
      setOutput(`<div class="muted" style="padding:12px">CMC run cancelled.</div>`);
    } else {
      const isNetwork = err.message === "Failed to fetch" || err.message.includes("NetworkError") || err.message.includes("fetch");
      const userMsg = isNetwork
        ? "Cannot reach the API server. Please check that the server is running (SSH → restart uvicorn) and try again."
        : err.message;
      setOutput(errorPanel(userMsg));
      updateResultRail({status:"FAIL", summaryTitle:"CMC run failed", summaryText:userMsg, metrics:[], recommendation: isNetwork ? "Restart uvicorn on the remote server." : "Inspect the returned error and rerun.", artifacts:[], metadata:[]});
    }
  }
}

async function cancelCmcRun() {
  if (_cmcAbortCtrl) { _cmcAbortCtrl.abort(); _cmcAbortCtrl = null; }
  const jobId = _currentCmcJobId || (JSON.parse(sessionStorage.getItem("cmc_active_job") || "{}").jobId);
  if (jobId) {
    try {
      await apiFetch(apiJoin(`jobs/${jobId}/cancel`), { method: "POST" });
    } catch (e) {
      console.warn("Failed to request job cancellation:", e);
    }
  }
  _currentCmcJobId = null;
  sessionStorage.removeItem("cmc_active_job");
  _cmcSetCancelVisible(false);
  const statusBox = document.getElementById("cmc-status-bar");
  if (statusBox) statusBox.innerHTML = "";
  clearRunning();
  setOutput(`<div class="muted" style="padding:12px">CMC run cancelled.</div>`);
}

// ── miniCMC variant verification (category-by-category) ─────────────────────
// Charge and Hydrophobic categories run WITH structure prediction (ABodyBuilder2) because
// their primary target metrics (pnc, ppc, psh, SAP_score) are SASA-dependent.
// Without structure, these metrics cannot be verified after mutation — N/A is not acceptable
// when pnc is the flagged reason for the optimization.
// Stability and Liability categories are sequence-only (~5s); their targets do not need SASA.
const CMC_CATEGORIES = {
  charge: {
    label: "Charge",
    color: "#2e8b57",
    needsStructure: true,   // pnc/ppc/sfvcsp require SASA — must rerun structure to verify patch change
    metricKeys: ["pI","net_charge_pH7","ppc","pnc","fv_charge_asymmetry","sfvcsp"],
    // Matches: "charge balance", "charge patch", "negative/positive charge patch profile", "pI ...", "net charge ...", "Fv charge asymmetry"
    targetMatch: (t) => /charge|\bpi\b|net charge|asymm/i.test(t || ""),
    siteFields: ["fr_negative_charge_sites","fr_positive_charge_sites"],
  },
  hydrophobic: {
    label: "Hydrophobic",
    color: "#b8860b",
    needsStructure: true,   // psh/SAP_score require SASA — must rerun structure to verify patch change
    metricKeys: ["GRAVY","agg_motifs","hydro_cluster_count","psh","SAP_score","hydro_patch_max9"],
    // Matches: "hydrophobic patch", "surface hydrophobicity", "SAP ...", "GRAVY ..." (exclude "charge patch")
    targetMatch: (t) => /hydrophob|sap|gravy|patch/i.test(t || "") && !/charge/i.test(t || ""),
    siteFields: ["fr_hydrophobic_runs"],
  },
  stability: {
    label: "Stability",
    color: "#4169aa",
    needsStructure: false,  // instability_index is sequence-based
    metricKeys: ["instability_index","agg_motifs","hydro_cluster_count"],
    // Matches: "sequence stability", "instability ...", "aggregation motif", "cluster"
    // FIX: backend emits "sequence stability" (no "instab" substring) — must also match "stabil" and "aggreg|motif"
    targetMatch: (t) => /stabil|instab|aggreg|motif|cluster/i.test(t || ""),
    siteFields: ["fr_instability_sites"],
  },
  liability: {
    label: "Chemical Liability",
    color: "#8b5e3c",
    needsStructure: false,  // all liability metrics are sequence-based
    metricKeys: ["deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys"],
    // Matches: "chemical liability", "deamidation", "isomerization", "oxidation", "glycosylation", "cysteine/cys"
    // FIX: backend emits "chemical liability" — must also match "liabil"
    targetMatch: (t) => /liabil|deamid|isomer|oxidat|glycos|cysteine|\bcys\b/i.test(t || ""),
    siteFields: [],
  },
};

// Always-checked guardrail metrics (across every variant; flag any regression)
// Note: total_cdr_length is intentionally excluded — CDR boundaries are fixed and cannot
// change from single-residue FR substitutions. Including it would always show 0 delta (noise).
const CMC_GUARDRAIL_KEYS = ["pI","net_charge_pH7","free_cys","glycosylation_sites"];

function _cmcCollectMutationsByCategory(frSuggestions) {
  const buckets = {charge: [], hydrophobic: [], stability: [], liability: []};
  const seen = {charge: new Set(), hydrophobic: new Set(), stability: new Set(), liability: new Set()};
  function pushUnique(cat, m) {
    const key = `${m.chain}-${m.pos}-${m.from}-${m.to}`;
    if (!m.pos || seen[cat].has(key)) return;
    seen[cat].add(key);
    buckets[cat].push(m);
  }
  // Unified strategy: route every suggestion's mutations to the correct category bucket.
  // 1) First try matching the parent suggestion's target string against category regex.
  // 2) Fallback: route by site-field name (works even when target text is non-standard).
  //    fr_negative_charge_sites / fr_positive_charge_sites → "charge"
  //    fr_instability_sites                                → "stability"
  //    fr_hydrophobic_runs                                  → "hydrophobic"
  // 3) Liability suggestions (chemical liability) carry no FR site lists by design — their
  //    advisories surface via the CDR liability panel, not Verify Variant.
  const SITE_FIELD_FALLBACK = {
    fr_negative_charge_sites: "charge",
    fr_positive_charge_sites: "charge",
    fr_instability_sites:     "stability",
  };
  (frSuggestions || []).forEach(s => {
    const sc = s.sequence_candidates;
    if (!sc) return;
    const target = s.target || "";
    let catFromTarget = null;
    for (const [k, def] of Object.entries(CMC_CATEGORIES)) {
      if (def.targetMatch(target)) { catFromTarget = k; break; }
    }
    // Site-list mutations: prefer site-field semantics; fall back to target-derived category
    Object.entries(SITE_FIELD_FALLBACK).forEach(([f, fallbackCat]) => {
      (sc[f] || []).forEach(p => {
        if (!p.from_aa || !p.to_aa_hint) return;
        const finalCat = catFromTarget || fallbackCat;
        pushUnique(finalCat, {chain: p.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, region: p.region, motif: p.motif, target});
      });
    });
    // Hydrophobic runs always go to the "hydrophobic" bucket regardless of parent target.
    // They should never land in "stability" — reducing a hydrophobic run does not guarantee
    // a lower Biopython instability index and empirically makes it worse (L/A/I → S/S/T).
    (sc.fr_hydrophobic_runs || []).forEach(run => {
      (run.per_residue || []).forEach(p => {
        if (p.from_aa && p.to_aa_hint) pushUnique("hydrophobic", {chain: run.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, region: p.region, target});
      });
    });
  });
  return buckets;
}

function _cmcApplyMutations(vh, vl, muts) {
  let mvh = vh, mvl = vl;
  muts.forEach(m => {
    const idx = m.pos - 1;
    if (m.chain === "VH" || m.chain === "H") {
      if (idx >= 0 && idx < mvh.length) mvh = mvh.substring(0, idx) + m.to + mvh.substring(idx + 1);
    } else if (m.chain === "VL" || m.chain === "L") {
      if (idx >= 0 && idx < mvl.length) mvl = mvl.substring(0, idx) + m.to + mvl.substring(idx + 1);
    } else if (m.chain === "VHH" || m.chain === "" || m.chain == null) {
      if (idx >= 0 && idx < mvh.length) mvh = mvh.substring(0, idx) + m.to + mvh.substring(idx + 1);
    }
  });
  return {vh: mvh, vl: mvl};
}

function _highlightMutations(wt, mut) {
  if (!wt || !mut) return mut || "";
  let out = "";
  for (let i = 0; i < mut.length; i++) {
    const aa = mut[i];
    const isMut = i < wt.length && aa !== wt[i];
    if (isMut) {
      out += `<span style="color:#f85149;font-weight:700;background:rgba(248,81,73,.15);padding:0 1px;border-radius:2px" title="pos ${i+1}: ${wt[i]}→${aa}">${aa}</span>`;
    } else {
      out += aa;
    }
  }
  return out;
}

// ─────────────────────────────────────────────────────────────────────────────
// Client-side miniCMC predictor — fast estimate for live preview only.
// Real ADI/structural metrics still come from server-side Verify call.
// ─────────────────────────────────────────────────────────────────────────────
const _CMC_PKA = {nterm: 9.0, cterm: 2.0, C: 8.3, D: 3.65, E: 4.25, H: 6.0, K: 10.5, R: 12.0, Y: 10.07};
const _CMC_HYDROPATHY = {A:1.8,C:2.5,D:-3.5,E:-3.5,F:2.8,G:-0.4,H:-3.2,I:4.5,K:-3.9,L:3.8,M:1.9,N:-3.5,P:-1.6,Q:-3.5,R:-4.5,S:-0.8,T:-0.7,V:4.2,W:-0.9,Y:-1.3};
const _CMC_HYDRO_SET = new Set("AILMFWV");

function cmcClientCharge(seq, pH) {
  let net = 0;
  if (!seq) return 0;
  // Termini
  net += 1 / (1 + Math.pow(10, pH - _CMC_PKA.nterm));
  net -= 1 / (1 + Math.pow(10, _CMC_PKA.cterm - pH));
  // Side chains
  for (const aa of seq) {
    if (aa === "K" || aa === "R" || aa === "H") {
      net += 1 / (1 + Math.pow(10, pH - _CMC_PKA[aa]));
    } else if (aa === "D" || aa === "E" || aa === "C" || aa === "Y") {
      net -= 1 / (1 + Math.pow(10, _CMC_PKA[aa] - pH));
    }
  }
  return net;
}

function cmcClientPi(seq) {
  if (!seq) return 7.0;
  let lo = 0.0, hi = 14.0;
  for (let i = 0; i < 50; i++) {
    const mid = (lo + hi) / 2;
    if (cmcClientCharge(seq, mid) > 0) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

function cmcClientGravy(seq) {
  if (!seq) return 0;
  let sum = 0, n = 0;
  for (const aa of seq) {
    if (aa in _CMC_HYDROPATHY) { sum += _CMC_HYDROPATHY[aa]; n++; }
  }
  return n > 0 ? sum / n : 0;
}

function cmcClientHydroPatchMax9(seq) {
  if (!seq) return 0;
  const w = 9;
  if (seq.length < w) return seq.split("").filter(a => _CMC_HYDRO_SET.has(a)).length / w;
  let best = 0;
  for (let i = 0; i <= seq.length - w; i++) {
    let c = 0;
    for (let j = i; j < i + w; j++) if (_CMC_HYDRO_SET.has(seq[j])) c++;
    if (c > best) best = c;
  }
  return best / w;
}

function cmcClientAggMotifs(seq) {
  let run = 0, count = 0;
  for (const aa of seq) {
    if (_CMC_HYDRO_SET.has(aa)) { run++; if (run >= 3) count++; } else { run = 0; }
  }
  return count;
}

function cmcClientPredict(vh, vl) {
  const combined = (vh || "") + (vl || "");
  return {
    pI: +cmcClientPi(combined).toFixed(2),
    net_charge_pH7: +cmcClientCharge(combined, 7.0).toFixed(2),
    GRAVY: +cmcClientGravy(combined).toFixed(3),
    hydro_patch_max9: +cmcClientHydroPatchMax9(combined).toFixed(3),
    agg_motifs: cmcClientAggMotifs(combined),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Unified Smart-CMC Selector
// Modal-style panel: lists all mutations grouped by goal, lets the user toggle
// individual sites or whole categories, shows live (client-side) miniCMC delta,
// and triggers full server-side Verify on submit.
// ─────────────────────────────────────────────────────────────────────────────
function openSmartCmcUnifiedSelector(opts) {
  const {kind, vh, vl, seq, buckets, baseMetrics, origin, antibodyType, onVerify} = opts;
  const isVhh = kind === "vhh";
  const lastResult = ((_lastCmcResult && (_lastCmcResult.result || _lastCmcResult)) || {});
  const baseVh = isVhh
    ? (seq || lastResult.vh_sequence || "")
    : (vh || lastResult.vh_sequence || "");
  const baseVl = isVhh ? "" : (vl || lastResult.vl_sequence || "");
  const baseClient = cmcClientPredict(baseVh, baseVl);
  const baseAdi = (baseMetrics && (baseMetrics.ADI ?? baseMetrics.adi_score)) || null;

  // Flatten all mutations with stable IDs
  const allMuts = [];
  const catLabel = {charge: "Charge", hydrophobic: "Hydrophobic", stability: "Stability", liability: "Liability"};
  const catColor = {charge: "#1b66d3", hydrophobic: "#0d8a72", stability: "#b4571f", liability: "#a04598"};
  for (const cat of ["charge", "hydrophobic", "stability", "liability"]) {
    (buckets[cat] || []).forEach((m, idx) => {
      if (m.pos == null || !m.from || !m.to) return; // Skip advisories/dummy entries
      allMuts.push({
        id: `${cat}-${idx}`,
        cat, ...m,
        label: `${m.chain || "VHH"} ${m.kabat_pos != null ? m.kabat_pos : m.pos} ${m.from}→${m.to}`,
      });
    });
  }
  if (!allMuts.length) {
    alert("No FR-modifiable mutations available. See the 'No FR modifications recommended' explanation for the reason.");
    return;
  }

  // Build modal
  const existing = document.getElementById("smartcmc-unified-modal");
  if (existing) existing.remove();
  const modal = document.createElement("div");
  modal.id = "smartcmc-unified-modal";
  modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;overflow:auto";
  modal.innerHTML = `
    <div style="background:var(--bg,#fff);color:var(--text,#111);max-width:900px;width:100%;max-height:90vh;overflow:auto;border-radius:8px;padding:22px;box-shadow:0 8px 32px rgba(0,0,0,.3)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
        <div>
          <h3 style="margin:0 0 4px 0;font-size:18px">Smart-CMC unified selector</h3>
          <div style="font-size:12px;color:var(--muted,#666)">
            ${isVhh ? `VHH/HCAb · origin=${escapeHtml(origin || "—")}` : `IgG VH+VL · ${escapeHtml(antibodyType || "—")}`}
            · ${allMuts.length} candidate mutation${allMuts.length === 1 ? "" : "s"}
          </div>
        </div>
        <button onclick="document.getElementById('smartcmc-unified-modal').remove()"
          style="background:none;border:1px solid var(--muted,#999);padding:4px 12px;border-radius:4px;cursor:pointer">Close</button>
      </div>

      <div style="display:grid;grid-template-columns:1fr 280px;gap:18px">
        <div>
          <div style="margin-bottom:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
            <button onclick="_smartcmcSelectAll(true)" style="padding:5px 12px;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">Select all</button>
            <button onclick="_smartcmcSelectAll(false)" style="padding:5px 12px;background:#6b7280;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">Clear</button>
            <span style="font-size:11px;color:var(--muted,#666)">or check any combination below</span>
          </div>
          <div id="smartcmc-mut-list" style="border:1px solid var(--border,#ddd);border-radius:6px;max-height:40vh;overflow:auto">
            ${["charge","hydrophobic","stability","liability"].map(cat => {
              const muts = allMuts.filter(m => m.cat === cat);
              if (!muts.length) return "";
              return `
                <div style="background:${catColor[cat]}1a;padding:6px 10px;font-size:11px;font-weight:700;color:${catColor[cat]};border-bottom:1px solid ${catColor[cat]}55">
                  <label style="cursor:pointer;display:flex;gap:6px;align-items:center">
                    <input type="checkbox" class="smartcmc-cat-toggle" data-cat="${cat}" onchange="_smartcmcToggleCat('${cat}',this.checked)">
                    ${catLabel[cat]} (${muts.length})
                  </label>
                </div>
                ${muts.map(m => `
                  <label style="display:flex;gap:10px;align-items:center;padding:7px 12px;border-bottom:1px solid var(--border,#eee);font-size:12px;cursor:pointer">
                    <input type="checkbox" class="smartcmc-mut-cb" data-id="${m.id}" onchange="_smartcmcUpdatePreview()">
                    <code style="font-weight:600;min-width:120px">${escapeHtml(m.label)}</code>
                    <span style="font-size:10px;padding:1px 6px;background:${catColor[cat]}1a;color:${catColor[cat]};border-radius:3px;border:1px solid ${catColor[cat]}55">${catLabel[cat]}</span>
                    <span style="font-size:10px;color:var(--muted,#666);flex:1">${escapeHtml(m.region || "")} ${m.target ? "· " + escapeHtml(String(m.target).substring(0,40)) : ""}</span>
                  </label>
                `).join("")}
              `;
            }).join("")}
          </div>

          <div style="margin-top:16px;padding:12px;background:rgba(0,0,0,.03);border-radius:6px;border:1px solid rgba(0,0,0,.05)">
            <div style="font-size:11px;font-weight:700;color:var(--muted,#666);margin-bottom:8px">MANUAL CUSTOM MUTATIONS</div>
            <div style="display:flex;gap:10px;align-items:flex-start">
              <textarea id="smartcmc-manual-input" placeholder="e.g. H44G, L18S, E44G (Kabat) or H:E44G, L:Q18S" 
                style="flex:1;height:60px;padding:8px;font-size:12px;border:1px solid var(--border,#ddd);border-radius:4px;font-family:var(--font-mono,monospace)"
                oninput="_smartcmcUpdatePreview()"></textarea>
              <div style="width:180px;font-size:10px;color:var(--muted,#666);line-height:1.4">
                Enter Kabat mutations. IgG accepts <code>H44G</code>/<code>L18S</code>, 
                <code>E44G</code>, or explicit <code>H:E44G</code>. 
                Separate multiple with commas.
              </div>
            </div>
            <div id="smartcmc-manual-status" style="margin-top:4px;font-size:10px;min-height:14px"></div>
          </div>
        </div>

        <div>
          <div style="background:var(--card,#f9fafb);border:1px solid var(--border,#ddd);border-radius:6px;padding:14px">
            <div style="font-size:11px;font-weight:700;color:var(--muted,#666);margin-bottom:8px;letter-spacing:.5px">LIVE miniCMC PREVIEW</div>
            <div id="smartcmc-preview" style="font-size:12px"></div>
            <div style="margin-top:14px;font-size:10px;color:var(--muted,#666);line-height:1.5">
              Client-side estimate. <strong>ADI, instability index, SAP, AbNatiV2 / HPR</strong> require server-side Verify (full pipeline).
            </div>
          </div>
          <button id="smartcmc-verify-btn" onclick="_smartcmcDoVerify()"
            style="margin-top:12px;width:100%;padding:10px;background:#16a34a;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-size:13px">
            Apply selected & Verify (server-side)
          </button>
          <div id="smartcmc-verify-status" style="margin-top:8px;font-size:11px;color:var(--muted,#666);min-height:14px"></div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  // Wire helpers into window scope (modal only)
  window._smartcmcState = {allMuts, baseVh, baseVl, baseClient, baseAdi, baseMetrics, isVhh, origin, antibodyType, onVerify};

  window._smartcmcSelectAll = (val) => {
    modal.querySelectorAll(".smartcmc-mut-cb").forEach(cb => { cb.checked = val; });
    modal.querySelectorAll(".smartcmc-cat-toggle").forEach(cb => { cb.checked = val; });
    _smartcmcUpdatePreview();
  };
  window._smartcmcToggleCat = (cat, val) => {
    modal.querySelectorAll(`.smartcmc-mut-cb`).forEach(cb => {
      const m = window._smartcmcState.allMuts.find(x => x.id === cb.dataset.id);
      if (m && m.cat === cat) cb.checked = val;
    });
    _smartcmcUpdatePreview();
  };

  window._smartcmcGetSelected = () => {
    const out = [];
    modal.querySelectorAll(".smartcmc-mut-cb:checked").forEach(cb => {
      const m = window._smartcmcState.allMuts.find(x => x.id === cb.dataset.id);
      if (m) out.push(m);
    });
    return out;
  };

  window._smartcmcUpdatePreview = () => {
    const selected = window._smartcmcGetSelected();
    const manualText = document.getElementById("smartcmc-manual-input")?.value || "";
    const st = window._smartcmcState;
    const statusEl = document.getElementById("smartcmc-manual-status");
    
    // Parse manual mutations
    const manualMuts = [];
    const manualErrors = [];
    if (manualText.trim()) {
      const parts = manualText.split(/[,;\n]/).map(p => p.trim()).filter(Boolean);
      parts.forEach(p => {
        // Supported formats:
        //   H44G / L18S              (IgG chain + Kabat pos + toAA)
        //   H:E44G / L:Q18S          (explicit chain + fromAA + pos + toAA)
        //   E44G                     (fromAA + pos + toAA)
        //   44G                      (pos + toAA)
        let chainPrefix = st.isVhh ? "VHH" : null;
        let fromAA = null;
        let kabatPos = null;
        let toAA = null;

        const mChain = p.match(/^([HL])(?::)?([A-Z]?)(\d+)([A-Z])$/i);
        const mFrom = p.match(/^([A-Z])(\d+)([A-Z])$/i);
        const mPos = p.match(/^(\d+)([A-Z])$/i);

        if (mChain) {
          chainPrefix = mChain[1].toUpperCase();
          fromAA = mChain[2] ? mChain[2].toUpperCase() : null;
          kabatPos = parseInt(mChain[3], 10);
          toAA = mChain[4].toUpperCase();
        } else if (mFrom) {
          fromAA = mFrom[1].toUpperCase();
          kabatPos = parseInt(mFrom[2], 10);
          toAA = mFrom[3].toUpperCase();
        } else if (mPos) {
          kabatPos = parseInt(mPos[1], 10);
          toAA = mPos[2].toUpperCase();
        }

        if (kabatPos != null && toAA) {
          
          // Try to resolve linear position from suggested list
          const match = st.allMuts.find(x => x.kabat_pos === kabatPos && (chainPrefix ? (x.chain === chainPrefix || x.chain === chainPrefix[0]) : true));
          if (match) {
            manualMuts.push({chain: match.chain, pos: match.pos, from: fromAA || match.from, to: toAA, cat: "manual", label: `${fromAA||match.from}${kabatPos}${toAA} (Manual)`});
          } else {
            // Heuristic fallback for VHH or if not in suggestions
            if (st.isVhh || chainPrefix) {
              const chain = chainPrefix || "VHH";
              const seq = chain === "VH" || chain === "H" || chain === "VHH" ? st.baseVh : st.baseVl;
              // Very rough Kabat->Linear if not found in suggestions
              const lin = kabatPos - 1; 
              if (lin >= 0 && lin < seq.length) {
                const actualFrom = seq[lin];
                if (fromAA && fromAA !== actualFrom) {
                  manualErrors.push(`Mismatch at ${p}: found ${actualFrom} at linear ${lin+1}`);
                } else {
                  manualMuts.push({chain, pos: lin + 1, from: actualFrom, to: toAA, cat: "manual", label: `${actualFrom}${kabatPos}${toAA} (Manual)`});
                }
              } else {
                manualErrors.push(`Position ${kabatPos} out of range for ${chain}`);
              }
            } else {
              // Try to guess chain if missing for IgG
              const vhMatch = st.baseVh && kabatPos <= st.baseVh.length;
              const vlMatch = st.baseVl && kabatPos <= st.baseVl.length;
              if (vhMatch && !vlMatch) {
                 const actualFrom = st.baseVh[kabatPos-1];
                 manualMuts.push({chain: "VH", pos: kabatPos, from: actualFrom, to: toAA, cat: "manual", label: `H:${actualFrom}${kabatPos}${toAA} (Manual)`});
              } else if (vlMatch && !vhMatch) {
                 const actualFrom = st.baseVl[kabatPos-1];
                 manualMuts.push({chain: "VL", pos: kabatPos, from: actualFrom, to: toAA, cat: "manual", label: `L:${actualFrom}${kabatPos}${toAA} (Manual)`});
              } else {
                manualErrors.push(`Specify chain for ${p} (e.g. H:${kabatPos}${toAA})`);
              }
            }
          }
        } else {
          manualErrors.push(`Invalid format: ${p}`);
        }
      });
    }

    if (statusEl) {
      statusEl.innerHTML = manualErrors.length 
        ? `<span style="color:var(--fail)">${manualErrors.join("; ")}</span>`
        : manualMuts.length ? `<span style="color:var(--pass)">${manualMuts.length} manual mutation(s) parsed</span>` : "";
    }

    const combinedMuts = [...selected, ...manualMuts];
    const mut = _cmcApplyMutations(st.baseVh, st.baseVl, combinedMuts);
    const v = cmcClientPredict(mut.vh, mut.vl);
    const rows = [
      ["pI",                "pI",                v.pI,                st.baseClient.pI,                2, true],
      ["Net charge pH7",    "net_charge_pH7",    v.net_charge_pH7,    st.baseClient.net_charge_pH7,    2, true],
      ["GRAVY",             "GRAVY",             v.GRAVY,             st.baseClient.GRAVY,             3, false],
      ["Hydro patch (max9)","hydro_patch_max9",  v.hydro_patch_max9,  st.baseClient.hydro_patch_max9,  3, false],
      ["Agg motifs",        "agg_motifs",        v.agg_motifs,        st.baseClient.agg_motifs,        0, true],
    ];
    const fmtDelta = (a, b, digits) => {
      const d = a - b;
      if (Math.abs(d) < (digits === 0 ? 0.5 : Math.pow(10, -digits)/2)) return `<span style="color:var(--muted,#888)">→ ±0</span>`;
      const arrow = d > 0 ? "▲" : "▼";
      const color = d > 0 ? "#dc2626" : "#16a34a";
      return `<span style="color:${color};font-weight:600">${arrow} ${d>0?"+":""}${d.toFixed(digits)}</span>`;
    };
    const html = `
      <div style="margin-bottom:6px;font-size:11px;color:var(--muted,#666)">
        <strong style="color:var(--text,#111)">${combinedMuts.length}</strong> mutation${combinedMuts.length===1?"":"s"} selected
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:11px">
        <tr style="border-bottom:1px solid var(--border,#ddd)"><th style="text-align:left;padding:4px 2px;font-weight:600;color:var(--muted,#666)">Metric</th><th style="text-align:right;padding:4px 2px;font-weight:600;color:var(--muted,#666)">Base→After</th></tr>
        ${rows.map(r => `<tr style="border-bottom:1px solid var(--border,#eee)">
          <td style="padding:5px 2px">${escapeHtml(r[0])}</td>
          <td style="padding:5px 2px;text-align:right;font-family:var(--font-mono,monospace)">${r[3].toFixed(r[4])} → ${r[2].toFixed(r[4])} ${fmtDelta(r[2], r[3], r[4])}</td>
        </tr>`).join("")}
        ${st.baseAdi != null ? `<tr style="border-top:2px solid var(--border,#ddd);background:var(--card,#f9fafb)">
          <td style="padding:6px 2px;font-weight:600">ADI (baseline)</td>
          <td style="padding:6px 2px;text-align:right;font-family:var(--font-mono,monospace)">${(+st.baseAdi).toFixed(1)} <span style="color:var(--muted,#888);font-size:10px">(server-side)</span></td>
        </tr>` : ""}
      </table>
    `;
    document.getElementById("smartcmc-preview").innerHTML = html;
    window._smartcmcState.manualMuts = manualMuts; // stash for verify
  };

  window._smartcmcDoVerify = async () => {
    const selected = window._smartcmcGetSelected();
    const manual = window._smartcmcState.manualMuts || [];
    const combined = [...selected, ...manual];
    if (!combined.length) { alert("Select or enter at least one mutation to verify."); return; }
    const statusEl = document.getElementById("smartcmc-verify-status");
    const btn = document.getElementById("smartcmc-verify-btn");
    btn.disabled = true; btn.style.opacity = "0.6";
    statusEl.innerHTML = "Running server-side full re-evaluation…";
    try {
      const st = window._smartcmcState;
      if (typeof st.onVerify === "function") {
        await st.onVerify(combined);
        statusEl.innerHTML = "✓ Verify complete — see results panel below.";
      } else {
        statusEl.innerHTML = "⚠ No verify callback wired.";
      }
    } catch (e) {
      statusEl.innerHTML = "❌ Verify failed: " + escapeHtml(e.message || String(e));
    } finally {
      btn.disabled = false; btn.style.opacity = "1";
    }
  };

  // Initial preview render (zero mutations selected)
  window._smartcmcUpdatePreview();
}

// Reuse the main cmc-status-bar progress bar for variant runs
function _cmcShowProgress(pct, label) {
  const statusBox = document.getElementById("cmc-status-bar");
  if (!statusBox) return;
  pct = Math.min(Math.max(pct || 0, 0), 99);
  statusBox.innerHTML = `<div style="margin-top:8px">
    <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:3px">
      <span>${label}</span><span>${Math.round(pct)}%</span>
    </div>
    <div style="height:4px;background:rgba(0,0,0,.1);border-radius:2px;overflow:hidden">
      <div style="width:${pct}%;height:100%;background:var(--accent);transition:width .4s ease;border-radius:2px"></div>
    </div>
  </div>`;
}
function _cmcHideProgress() {
  const statusBox = document.getElementById("cmc-status-bar");
  if (statusBox) statusBox.innerHTML = "";
  clearRunning();
}

// Open the unified Smart-CMC selector from a previously stashed context.
// Wired to the button rendered inside renderCmcIggResult / renderVhhCmcResult.
function _openCmcUnifiedFromCtx(jobId) {
  const ctx = window[`_cmcUnifiedCtx_${jobId}`];
  if (!ctx) { alert("Unified selector context not found for job " + jobId); return; }
  openSmartCmcUnifiedSelector({
    kind: ctx.kind,
    vh: ctx.vh, vl: ctx.vl, seq: ctx.seq,
    buckets: ctx.buckets,
    baseMetrics: ctx.baseMetrics,
    origin: ctx.origin,
    antibodyType: ctx.antibodyType,
    onVerify: async (selectedMuts) => {
      // Stash and trigger the existing verify pipeline with "__custom__" category
      window._cmcCustomMuts = selectedMuts.map(m => ({
        chain: m.chain, pos: m.pos, from: m.from, to: m.to,
        kabat_pos: m.kabat_pos,
        category: m.cat, region: m.region,
      }));
      // Dismiss the modal so the user can see the verify panel below
      const modal = document.getElementById("smartcmc-unified-modal");
      if (modal) modal.remove();
      if (ctx.kind === "vhh") {
        // For VHH, jobId IS the ctxKey ("vhh" or "bs-arm1"/"bs-arm2")
        await verifyVhhCategoryBatch(jobId, "__custom__");
      } else {
        await verifyVariantMini(jobId, "__custom__");
      }
    },
  });
}

async function verifyVariantMini(jobId, category) {
  // ── Clean slate: abort any lingering verify run, reset all shared state ─
  if (_cmcAbortCtrl && !_cmcAbortCtrl.signal.aborted) _cmcAbortCtrl.abort();
  _cmcAbortCtrl = null;
  _currentCmcJobId = null;
  sessionStorage.removeItem("cmc_active_job");
  _cmcSetCancelVisible(false);

  if (!_lastCmcResult || !_lastCmcResult.result) { alert("No baseline result available."); return; }
  const r = _lastCmcResult.result;
  const rb = r.regular_ab_developability || {};
  const frSuggestions = Array.isArray(rb.fr_modification_suggestions) ? rb.fr_modification_suggestions : [];
  const buckets = _cmcCollectMutationsByCategory(frSuggestions);

  let muts = [];
  let categoriesUsed = [];
  if (category === "__custom__") {
    // Unified Smart-CMC selector: arbitrary user-picked mutations across any categories
    muts = (window._cmcCustomMuts || []).map(m => ({...m}));
    if (!muts.length) { alert("No mutations passed to custom verify."); return; }
    const _seenCats = new Set(muts.map(m => m.cat || m.category).filter(Boolean));
    categoriesUsed = Array.from(_seenCats);
    if (!categoriesUsed.length) categoriesUsed = ["custom"];
  } else if (category === "combined") {
    Object.entries(buckets).forEach(([k, v]) => {
      if (v.length) {
        muts = muts.concat(v.map(m => ({...m, category: k})));
        categoriesUsed.push(k);
      }
    });
  } else {
    muts = (buckets[category] || []).map(m => ({...m, category}));
    categoriesUsed = [category];
  }
  if (!muts.length) { alert(`No FR mutations found for category: ${category}`); return; }

  const needsStructure = categoriesUsed.some(c => CMC_CATEGORIES[c]?.needsStructure);
  const vh = (r.vh_sequence || "").trim();
  const vl = (r.vl_sequence || "").trim();
  const {vh: mutVh, vl: mutVl} = _cmcApplyMutations(vh, vl, muts);
  const labelText = categoriesUsed.map(c => CMC_CATEGORIES[c]?.label || c).join(" + ");

  const resDiv = document.getElementById(`variant-result-${jobId}`);
  const catColor = CMC_CATEGORIES[categoriesUsed[0]]?.color || "#2e8b57";
  function _inlineProgress(pct, label) {
    pct = Math.min(Math.max(pct || 0, 0), 99);
    if (!resDiv) return;
    resDiv.style.display = "block";
    resDiv.innerHTML = `
      <div style="padding:14px 16px;background:rgba(0,0,0,.04);border-radius:6px">
        <div style="font-size:12px;font-weight:600;margin-bottom:10px;color:${catColor}">▶ Verifying ${labelText} variant…</div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px">
          <span>${label}</span><span>${Math.round(pct)}%</span>
        </div>
        <div style="height:5px;background:rgba(0,0,0,.1);border-radius:3px;overflow:hidden">
          <div style="width:${pct}%;height:100%;background:${catColor};border-radius:3px;transition:width .5s ease"></div>
        </div>
        <div style="margin-top:10px;font-size:11px;color:var(--muted)">
          Sequence-only scan (~5–10s). Charge/hydrophobic patch metrics not applicable for this category.
          &nbsp;<button onclick="cancelCmcRun()" style="font-size:11px;padding:2px 10px;border:1px solid var(--muted);border-radius:3px;background:transparent;cursor:pointer;color:var(--muted)">Cancel</button>
        </div>
      </div>`;
  }
  _inlineProgress(5, "Initialising…");
  _cmcAbortCtrl = new AbortController();
  _cmcSetCancelVisible(true);
  _cmcShowProgress(5, `${labelText} variant — initialising…`);
  // Snapshot baseline so Re-attach can render even if _lastCmcResult drifts
  const _baselineSnapshot = JSON.stringify({r, rb});

  try {
    // Avoid rapid repeated POSTs through Nginx after users click several verify
    // buttons in sequence.  The endpoint is now async, but a short client-side
    // spacing still prevents proxy/session throttling on small MVP servers.
    const _sinceLastVariantPost = Date.now() - (window._cmcLastVariantPostAt || 0);
    if (_sinceLastVariantPost < 1500) await new Promise(r => setTimeout(r, 1500 - _sinceLastVariantPost));
    window._cmcLastVariantPostAt = Date.now();

    let pollResult = null;
    if (needsStructure) {
      const res = await apiFetch(apiJoin("cmc/igg/async"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          vh_sequence: mutVh, vl_sequence: mutVl,
          antibody_type: r.antibody_type || "IgG1",
          project_name: (r.project_name || "variant") + `-${category}`,
          report_format: "html",
          predict_fv_structure: true,
          smart_cmc: false,
        }),
        signal: _cmcAbortCtrl.signal,
      });
      if (!res.ok) { let em = `Server error ${res.status}`; try { const e = await res.json(); em = e.detail || em; } catch { em = `Server returned ${res.status} — check if API is running`; } throw new Error(em); }
      const start = await res.json();
      const vJobId = start.job_id;
      _currentCmcJobId = vJobId;
      // Persist with kind=variant so Re-attach uses _renderVariantComparison
      sessionStorage.setItem("cmc_active_job", JSON.stringify({
        jobId: vJobId, kind: "variant", parentJobId: jobId,
        category, categoriesUsed, muts,
        baseline: _baselineSnapshot,
        startedAt: Date.now(),
      }));
      let poll, pollCount = 0;
      const phases = [
        {pct:20, label:"Numbering & CMC metrics…"},
        {pct:50, label:"Fv structure modeling (ABodyBuilder2)…"},
        {pct:75, label:"SASA & charge/hydrophobic patch profiling…"},
        {pct:90, label:"Finalising results…"},
      ];
      let phaseIdx = 0;
      const phaseTimer = setInterval(() => {
        if (phaseIdx < phases.length) {
          _inlineProgress(phases[phaseIdx].pct, phases[phaseIdx].label);
          _cmcShowProgress(phases[phaseIdx].pct, `${labelText} — ${phases[phaseIdx].label}`);
          phaseIdx++;
        }
      }, 5000);
      while (pollCount < 120) {
        if (_cmcAbortCtrl?.signal.aborted) break;
        await new Promise(r => setTimeout(r, 3000));
        pollCount++;
        const pr = await apiFetch(apiJoin(`jobs/${vJobId}`), { signal: _cmcAbortCtrl?.signal });
        if (!pr.ok) throw new Error(`Variant poll failed: ${pr.status}`);
        poll = await pr.json();
        const st = (poll.status || "").toLowerCase();
        if (poll.progress) {
          _inlineProgress(poll.progress, poll.progress_note || st);
          _cmcShowProgress(poll.progress, `${labelText} — ${poll.progress_note || st}`);
        }
        if (st === "done" || st === "failed" || st === "cancelled") break;
      }
      clearInterval(phaseTimer);
      sessionStorage.removeItem("cmc_active_job");
      _cmcHideProgress();
      _cmcSetCancelVisible(false);
      _currentCmcJobId = null;
      if (!poll || poll.status === "cancelled") { if (resDiv) resDiv.innerHTML = `<div class="muted" style="font-size:11px">Variant verification cancelled.</div>`; return; }
      if (poll.status !== "done") throw new Error(poll?.error || `Variant job ${poll?.status}`);
      pollResult = poll.result || {};
    } else {
      // All variant categories use sequence-only mode (predict_fv_structure: false).
      // Structure prediction (ABodyBuilder2 ~4-5 GB) is disabled for variant verify
      // to prevent OOM on the 8 GB server. Charge/patch metrics that require structure
      // (SAP_score, hydro_patch_max9, psh, charge_patch_max7) are omitted from results.
      _inlineProgress(10, "Queued sequence-only scan…");
      _cmcShowProgress(10, `${labelText} variant — queued sequence-only scan…`);
      const response = await apiFetch(apiJoin("cmc/igg/async"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          vh_sequence: mutVh, vl_sequence: mutVl,
          antibody_type: r.antibody_type || "IgG1",
          project_name: (r.project_name || "variant") + `-${category}`,
          report_format: "html",
          predict_fv_structure: false,
          smart_cmc: false,
        }),
        signal: _cmcAbortCtrl.signal,
      });
      if (!response.ok) { let em = `Server error ${response.status}`; try { const e = await response.json(); em = e.detail || em; } catch { em = `Server returned ${response.status} — check if API is running`; } throw new Error(em); }
      const start = await response.json();
      const vJobId = start.job_id;
      _currentCmcJobId = vJobId;
      sessionStorage.setItem("cmc_active_job", JSON.stringify({
        jobId: vJobId, kind: "variant", parentJobId: jobId,
        category, categoriesUsed, muts,
        baseline: _baselineSnapshot,
        startedAt: Date.now(),
      }));

      let poll, pollCount = 0;
      while (pollCount < 120) {
        if (_cmcAbortCtrl?.signal.aborted) break;
        await new Promise(r => setTimeout(r, 2000));
        pollCount++;
        const pr = await apiFetch(apiJoin(`jobs/${vJobId}`), { signal: _cmcAbortCtrl?.signal });
        if (!pr.ok) throw new Error(`Variant poll failed: ${pr.status}`);
        poll = await pr.json();
        const st = (poll.status || "").toLowerCase();
        const pct = poll.progress != null ? Number(poll.progress) : 20;
        const note = poll.progress_note || st || "sequence-only scan";
        _inlineProgress(pct, note);
        _cmcShowProgress(pct, `${labelText} — ${note}`);
        if (st === "done" || st === "failed" || st === "cancelled") break;
      }
      sessionStorage.removeItem("cmc_active_job");
      _cmcHideProgress();
      _cmcSetCancelVisible(false);
      _currentCmcJobId = null;
      if (!poll || poll.status === "cancelled") { if (resDiv) resDiv.innerHTML = `<div class="muted" style="font-size:11px">Variant verification cancelled.</div>`; return; }
      if (poll.status !== "done") throw new Error(poll?.error || `Variant job ${poll?.status}`);
      pollResult = poll.result || {};
    }

    _renderVariantComparison(jobId, category, categoriesUsed, muts, pollResult, r, rb);
  } catch (err) {
    sessionStorage.removeItem("cmc_active_job");
    _cmcHideProgress();
    _cmcSetCancelVisible(false);
    _currentCmcJobId = null;
    if (err.name === "AbortError") {
      if (resDiv) resDiv.innerHTML = `<div class="muted" style="font-size:11px">Variant verification cancelled.</div>`;
    } else {
      const msg = err.message || "";
      const is401 = /\b401\b/.test(msg);
      const is403 = /\b403\b/.test(msg);
      const is429 = /\b429\b/.test(msg);
      const is5xx = /\b50[0-9]\b/.test(msg);
      const isNetwork = msg === "Failed to fetch" || msg.includes("NetworkError") || msg.includes("non-JSON");
      let userMsg;
      if (is401 || is403) {
        userMsg = `Server returned ${is401 ? "401" : "403"} — your reverse-proxy session may have expired. <strong>Refresh the page (Ctrl+Shift+R)</strong> and try again. If the problem persists, the Nginx auth/rate-limit configuration on the server may be blocking repeated POSTs.`;
      } else if (is429) {
        userMsg = "Server returned 429 (rate-limited) — wait a few seconds and try again.";
      } else if (is5xx) {
        userMsg = `Server returned ${msg.match(/\b50[0-9]\b/)[0]} — the API process may have restarted. Try again in 5 seconds.`;
      } else if (isNetwork) {
        userMsg = "Cannot reach the API server — check that uvicorn is running on the remote server.";
      } else {
        userMsg = msg;
      }
      if (resDiv) resDiv.innerHTML = `<div style="color:var(--fail);font-size:11px;padding:10px">⚠ ${userMsg}</div>`;
    }
  }
}

function _renderVariantComparison(jobId, category, categoriesUsed, muts, optResult, baseR, baseRb) {
  const resDiv = document.getElementById(`variant-result-${jobId}`);
  if (!resDiv) return;

  // Metrics where "lower absolute value toward 0" = better, but direction matters
  // sfvcsp: product of VH×VL net charge; more negative = stronger dipole = worse viscosity/aggregation
  //   Reference (AbRef-458): p5=-6.3, p25=0.0, p50=+1.88, p75=+5.9
  // SAP_score, Fv_charge_asymmetry: higher = worse (monotone)
  const _MAGNITUDE_WORSE = new Set(["sfvcsp"]);  // more-negative = worse
  const _HIGHER_WORSE    = new Set(["SAP_score","agg_motifs","hydro_cluster_count",
    "deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys",
    "psh","ppc","pnc","hydro_patch_max9","instability_index","Fv_charge_asymmetry"]);

  // sfvcsp reference thresholds from AbRef-458 (clinical IgG, n=458)
  const _SFVCSP_REF = {p5: -6.3, p25: 0.0, p50: 1.88, p75: 5.9};

  // Reference ranges for IgG metrics (clinical reference p25-p75)
  const _IGG_REF_RANGES = {
    pI: [5.5, 8.5],
    net_charge_pH7: [-2.0, 4.0],
    GRAVY: [-0.6, -0.2],
    instability_index: [0, 40],
    SAP_score: [0, 0.9],
    hydro_patch_max9: [0, 8.0],
    charge_patch_max7: [0, 5.0],
    Fv_charge_asymmetry: [0, 8.0],
    agg_motifs: [0, 1],
  };

  function _isValueWorse(key, before, after) {
    const b = Number(before), a = Number(after);
    if (Number.isNaN(b) || Number.isNaN(a)) return false;
    if (_MAGNITUDE_WORSE.has(key)) return a < b;   // more negative = worse
    if (_HIGHER_WORSE.has(key))    return a > b;   // higher = worse
    return false;
  }

  // Assess if a regression is within clinical safe zone
  function _getTolerance(key, before, after) {
    if (key === "sfvcsp") return _sfvcspTolerance(before, after);
    
    const b = Number(before), a = Number(after);
    const worsened = _isValueWorse(key, before, after);
    if (!worsened) return null;

    const range = _IGG_REF_RANGES[key];
    if (!range) return null;

    const [min, max] = range;
    const isSafe = a >= min && a <= max;

    if (isSafe) {
      return {verdict:"ACCEPTABLE", label:"Regression within clinical reference range", color:"var(--pass)"};
    } else {
      return {verdict:"MONITOR", label:"Regression outside clinical reference range", color:"var(--warn)"};
    }
  }

  // For sfvcsp: assess how bad the regression is vs clinical reference
  function _sfvcspTolerance(before, after) {
    const b = Number(before), a = Number(after);
    if (Number.isNaN(b) || Number.isNaN(a) || a >= b) return null; // not a regression
    const delta = a - b;
    // Still above p5 (-6.3)? Within clinical range.
    const stillInRange = a >= _SFVCSP_REF.p5;
    // How far from p25 (0) is the after value?
    const distFromP25before = Math.abs(b - _SFVCSP_REF.p25);
    const distFromP25after  = Math.abs(a - _SFVCSP_REF.p25);
    const pctWorsen = distFromP25before > 0 ? ((distFromP25after - distFromP25before) / Math.abs(_SFVCSP_REF.p5 - _SFVCSP_REF.p25)) * 100 : 0;
    if (!stillInRange) return {verdict:"REJECT", label:"Outside p5 (clinical floor, <-6.3)", color:"var(--fail)"};
    if (pctWorsen < 10) return {verdict:"ACCEPTABLE", label:"Small regression (<10% toward p5 floor), still within clinical band", color:"var(--pass)"};
    if (pctWorsen < 30) return {verdict:"MONITOR", label:"Moderate regression (10–30% toward p5 floor), within clinical range but trend unfavorable", color:"var(--warn)"};
    return {verdict:"REJECT", label:"Large regression (>30% toward p5 floor), viscosity/aggregation risk elevated", color:"var(--fail)"};
  }

  const targetKeys = new Set();
  categoriesUsed.forEach(c => (CMC_CATEGORIES[c]?.metricKeys || []).forEach(k => targetKeys.add(k)));
  CMC_GUARDRAIL_KEYS.forEach(k => targetKeys.add(k));

  const baseParams = Array.isArray(baseRb.parameters) ? baseRb.parameters : [];
  const optRb = optResult.regular_ab_developability || {};
  const optParams = Array.isArray(optRb.parameters) ? optRb.parameters : [];

  const fmt = (v) => (v === null || v === undefined) ? "—" : (typeof v === "number" ? v.toFixed(2) : String(v));
  const riskColor = (r) => r === "HIGH" ? "var(--fail)" : (r === "MODERATE" ? "var(--warn)" : "var(--pass)");

  // Build the set of keys that are target metrics for the selected categories
  const categoryTargetKeys = new Set();
  categoriesUsed.forEach(c => (CMC_CATEGORIES[c]?.metricKeys || []).forEach(k => categoryTargetKeys.add(k)));

  const rows = [];
  baseParams.forEach(bp => {
    if (!targetKeys.has(bp.key)) return;
    const ap = optParams.find(p => p.key === bp.key);
    if (!ap) return;
    const before = bp.value, after = ap.value;
    if (after === null || after === undefined) return;
    const isGuardrail = CMC_GUARDRAIL_KEYS.includes(bp.key);
    // A metric is a "target" if it belongs to the selected category — even if it's also a guardrail.
    // e.g. pI and net_charge_pH7 are guardrails globally but are primary indicators for "charge" optimizations.
    const isTargetCat = categoryTargetKeys.has(bp.key);
    // Worsened = risk-level step up OR value moving in wrong direction for monotone/magnitude metrics
    const riskStepUp = (bp.risk === "PASS" && (ap.risk === "MODERATE" || ap.risk === "HIGH")) ||
                       (bp.risk === "MODERATE" && ap.risk === "HIGH");
    const valueWorse = _isValueWorse(bp.key, before, after);
    const worsened = riskStepUp || valueWorse;
    // Special tolerance assessment
    const tolerance = _getTolerance(bp.key, before, after);
    rows.push({label: bp.label || bp.key, key: bp.key, before, after,
      beforeRisk: bp.risk, afterRisk: ap.risk, isTargetCat, isGuardrail, worsened, tolerance});
  });

  // For structure-dependent target metrics (pnc, ppc, psh, sfvcsp) that exist in the baseline
  // but were not recomputed — this only happens when structure prediction FAILED for the variant
  // (charge/hydrophobic categories always request structure; stability/liability never need it).
  // In the normal path these metrics will be present in optParams and won't trigger this block.
  const structuralKeys = new Set(["pnc","ppc","psh","sfvcsp","SAP_score","hydro_patch_max9"]);
  const structNotRerun = [];
  baseParams.forEach(bp => {
    if (!categoryTargetKeys.has(bp.key)) return;
    if (!structuralKeys.has(bp.key)) return;
    if (bp.value === null || bp.value === undefined) return;
    const alreadyInRows = rows.some(r => r.key === bp.key);
    if (!alreadyInRows) {
      structNotRerun.push({
        label: bp.label || bp.key, key: bp.key,
        before: bp.value, after: null,
        beforeRisk: bp.risk, afterRisk: null,
        isTargetCat: true, isGuardrail: false, worsened: false,
        structureNotRerun: true,
      });
    }
  });

  const baseAdi = baseRb.developability_index ?? baseR.developability_index ?? baseR.clinical_score;
  const optAdi  = optResult.developability_index ?? optResult.clinical_score;
  const baseAdiNum = Number(baseAdi);
  const optAdiNum = Number(optAdi);
  const adiRegression = !Number.isNaN(baseAdiNum) && !Number.isNaN(optAdiNum) && optAdiNum < baseAdiNum;
  const adiDelta = (!Number.isNaN(baseAdiNum) && !Number.isNaN(optAdiNum)) ? (optAdiNum - baseAdiNum) : null;

  const targetRows = rows.filter(r => r.isTargetCat);
  const guardrailRows = rows.filter(r => r.isGuardrail && !r.isTargetCat);
  const allRows = [...targetRows, ...guardrailRows];

  // Identify which categories have regressions (any metric in that category worsened)
  const catRegressions = new Set();
  rows.filter(r => r.worsened).forEach(r => {
    for (const [cat, def] of Object.entries(CMC_CATEGORIES)) {
      if ((def.metricKeys || []).includes(r.key)) catRegressions.add(cat);
    }
    // Special handling for guardrails: pI/charge regressions flag the "charge" category
    if (["pI", "net_charge_pH7"].includes(r.key)) catRegressions.add("charge");
  });

  const renderRow = (r) => {
    if (r.structureNotRerun) {
      // Structure-dependent metric: show baseline value + explanation; no after value available
      const riskBadge = r.beforeRisk === "HIGH"
        ? `<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:var(--fail);color:white">HIGH</span>`
        : r.beforeRisk === "MODERATE"
          ? `<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:var(--warn);color:white">MODERATE</span>`
          : "";
      return `
      <div style="display:grid;grid-template-columns:170px 1fr;gap:10px;font-size:11px;padding:5px 0;border-bottom:1px solid rgba(0,0,0,.05)">
        <div class="muted">${r.label} <span style="color:var(--accent)">[Target]</span></div>
        <div>
          <span style="color:${riskColor(r.beforeRisk)}">${fmt(r.before)}</span>
          <span class="muted"> → </span>
          <span class="muted">N/A</span>
          ${riskBadge}
          <div style="font-size:10px;color:var(--muted);margin-top:2px;font-style:italic">Structure prediction failed for this variant — rerun manually to confirm</div>
        </div>
      </div>`;
    }
    const tolBadge = r.tolerance
      ? ` <span style="font-size:10px;padding:1px 5px;border-radius:3px;background:${r.tolerance.color};color:white;opacity:.9">${r.tolerance.verdict}</span>`
      : "";
    return `
    <div style="display:grid;grid-template-columns:170px 1fr;gap:10px;font-size:11px;padding:5px 0;border-bottom:1px solid rgba(0,0,0,.05)">
      <div class="muted">${r.label}${r.isTargetCat ? ' <span style="color:var(--accent)">[Target]</span>' : ''}${r.isGuardrail ? ' <span style="color:var(--muted)">[Guardrail]</span>' : ''}</div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <div>
          <span style="color:${riskColor(r.beforeRisk)}">${fmt(r.before)}</span>
          <span class="muted"> → </span>
          <strong style="color:${r.worsened ? 'var(--fail)' : riskColor(r.afterRisk)}">${fmt(r.after)}</strong>
          ${r.worsened ? ' <span style="color:var(--fail)">⚠ Regression</span>' : ''}
          ${tolBadge}
        </div>
        ${r.tolerance ? `<div style="font-size:10px;color:${r.tolerance.color};line-height:1.4">${r.tolerance.label}</div>` : ''}
      </div>
    </div>`;
  };

  const mutSummary = muts.map(m => {
    const hasReg = catRegressions.has(m.category);
    const bgColor = hasReg ? 'rgba(248,81,73,.12)' : 'rgba(98,116,0,.12)';
    const borderColor = hasReg ? 'rgba(248,81,73,.3)' : 'rgba(98,116,0,.3)';
    const textColor = hasReg ? 'var(--fail)' : 'var(--pass)';
    const title = hasReg ? 'This mutation category caused a regression' : 'This mutation category is clean';
    return `<span title="${title}" style="font-family:monospace;font-size:11px;padding:2px 6px;background:${bgColor};border:1px solid ${borderColor};color:${textColor};border-radius:3px">${m.chain} ${m.pos} ${m.from}→${m.to}</span>`;
  }).join(" ");

  // Primary target improvement check
  const keyTargets = {
    charge: ["pnc","ppc","pI","net_charge_pH7","sfvcsp"],
    hydrophobic: ["GRAVY","agg_motifs","hydro_cluster_count"],
    stability: ["instability_index"],
    liability: ["deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites"],
  };
  // Secondary context keys: these track the root cause metric even if not in primary target list
  const contextKeys = {
    charge: ["pnc","ppc"],
    hydrophobic: ["SAP_score","hydro_patch_max9"],
  };
  let bioNote = "";
  for (const c of categoriesUsed) {
    const keys = keyTargets[c] || [];
    const headlineRows = targetRows.filter(r => keys.includes(r.key));
    const noImprovement = headlineRows.length > 0 && headlineRows.every(r => {
      const b = Number(r.before), a = Number(r.after);
      if (Number.isNaN(b) || Number.isNaN(a)) return false;
      return !_isValueWorse(r.key, a, b); // "not better" = a is not better than b
    });
    if (noImprovement) {
      const cLabel = CMC_CATEGORIES[c]?.label || c;
      bioNote += `<div style="padding:8px 10px;background:rgba(201,162,39,.10);border:1px solid rgba(201,162,39,.35);border-radius:4px;font-size:11px;color:var(--accent)">
        <strong>Note (${cLabel}):</strong> Primary target metric did not improve with ${muts.length} mutation${muts.length>1?'s':''}.
        ${c === "charge" ? "A charge patch typically requires <strong>2–3 charge mutations</strong> in the same surface region to break apart. The patch score reflects the maximum over any 7-residue window — a single peripheral mutation reduces overall charge but may not disrupt the highest-density cluster. Consider additional Smart-CMC iterations or the Combined variant." : ""}
        ${c === "hydrophobic" ? "Hydrophobic patches often need <strong>multiple substitutions</strong> across the patch region." : ""}
      </div>`;
    }
  }

  // Overall adoption verdict
  const regressions = rows.filter(r => r.worsened);
  const hardRejects = regressions.filter(r => r.tolerance?.verdict === "REJECT" || r.isGuardrail);
  const monitors    = regressions.filter(r => r.tolerance?.verdict === "MONITOR");
  const acceptable  = regressions.filter(r => r.tolerance?.verdict === "ACCEPTABLE");
  let adoptionBadge = "";
  if (hardRejects.length) {
    adoptionBadge = `<div style="padding:10px 12px;background:rgba(248,81,73,.10);border:1px solid var(--fail);border-radius:5px;font-size:11px">
      <div style="font-weight:600;color:var(--fail);margin-bottom:4px">⛔ ADOPTION VERDICT: REJECT THIS VARIANT</div>
      <div style="color:var(--fail)">${hardRejects.map(r => `${r.label} regression is not within acceptable range`).join(" · ")}</div>
      <div style="color:var(--muted);margin-top:4px">Recommendation: need additional candidate mutations or a different substitution strategy.</div>
    </div>`;
  } else if (adiRegression) {
    adoptionBadge = `<div style="padding:10px 12px;background:rgba(181,137,0,.10);border:1px solid var(--warn);border-radius:5px;font-size:11px">
      <div style="font-weight:600;color:var(--warn);margin-bottom:4px">⚠ ADOPTION VERDICT: TRADE-OFF REVIEW REQUIRED</div>
      <div style="color:var(--warn)">Target metrics may improve, but overall ADI decreased (${fmt(baseAdi)} → ${fmt(optAdi)}; Δ ${fmt(adiDelta)}). Do not label this variant as clean.</div>
      <div style="color:var(--muted);margin-top:4px">Recommendation: compare against Charge and Combined variants; adopt only if the target improvement is worth the ADI loss.</div>
    </div>`;
  } else if (monitors.length) {
    adoptionBadge = `<div style="padding:10px 12px;background:rgba(181,137,0,.10);border:1px solid var(--warn);border-radius:5px;font-size:11px">
      <div style="font-weight:600;color:var(--warn);margin-bottom:4px">⚠ ADOPTION VERDICT: PROCEED WITH MONITORING</div>
      <div style="color:var(--warn)">${monitors.map(r => `${r.label} shows moderate regression — within clinical range but requires wet-lab viscosity/aggregation confirmation`).join(" · ")}</div>
    </div>`;
  } else if (acceptable.length) {
    adoptionBadge = `<div style="padding:10px 12px;background:rgba(98,116,0,.10);border:1px solid var(--pass);border-radius:5px;font-size:11px">
      <div style="font-weight:600;color:var(--pass);margin-bottom:4px">✓ ADOPTION VERDICT: ACCEPTABLE</div>
      <div style="color:var(--muted)">Minor regressions (${acceptable.map(r=>r.label).join(", ")}) are within clinical reference band. Primary target should be re-evaluated with additional mutations.</div>
    </div>`;
  } else if (!regressions.length) {
    adoptionBadge = `<div style="padding:10px 12px;background:rgba(98,116,0,.10);border:1px solid var(--pass);border-radius:5px;font-size:11px">
      <div style="font-weight:600;color:var(--pass)">✓ ADOPTION VERDICT: CLEAN — no regressions detected</div>
    </div>`;
  }

  // ── Verify comparison table: 3-tier logic ───────────────────────────────
  // Tier 1 — miniCMC core (4 items, always sequence-computed, always shown):
  //          pI · GRAVY · Instability index · SAP score
  // Tier 2 — Optimization targets (category-specific, deduplicated with Tier 1):
  //          Charge:     net_charge_pH7, pnc*, ppc*, sfvcsp*
  //          Hydrophobic: hydro_patch_max9, psh*, agg_motifs
  //          Stability:  (fully covered by Tier 1)
  //          Liability:  deamidation, isomerization, oxidation, glycosylation, free_cys
  // Tier 3 — Structure (*): run only when category needsStructure=true (charge/hydrophobic).
  //          For stability/liability (sequence-only): structural items show "struct. failed".
  const MINI_CMC_KEYS = [
    {key:"pI",               label:"pI (Fab)",           group:"core"},
    {key:"GRAVY",            label:"GRAVY",              group:"core"},
    {key:"instability_index",label:"Instability index",  group:"core"},
    {key:"SAP_score",        label:"SAP score",          group:"core"},
  ];
  const CATEGORY_EXTRA = {
    charge: [
      {key:"net_charge_pH7",  label:"Net charge pH 7",        group:"target"},
      {key:"pnc",             label:"Neg charge patch",       group:"target", structural:true},
      {key:"ppc",             label:"Pos charge patch",       group:"target", structural:true},
      {key:"sfvcsp",          label:"Fv charge asymmetry",    group:"target", structural:true},
    ],
    hydrophobic: [
      {key:"hydro_patch_max9",label:"Hydro patch (9-mer)",    group:"target"},
      {key:"psh",             label:"Surface hydrophobicity", group:"target", structural:true},
      {key:"agg_motifs",      label:"Agg motifs",             group:"target"},
    ],
    stability: [],   // instability_index already in miniCMC Tier 1
    liability: [
      {key:"deamidation_sites",   label:"Deamidation",   group:"target"},
      {key:"isomerization_sites", label:"Isomerization", group:"target"},
      {key:"oxidation_sites",     label:"Oxidation",     group:"target"},
      {key:"glycosylation_sites", label:"Glycosylation", group:"target"},
      {key:"free_cys",            label:"Free Cys",      group:"target"},
    ],
  };
  const miniCmcKeySet = new Set(MINI_CMC_KEYS.map(d => d.key));
  const uniqueExtra = categoriesUsed.flatMap(c => CATEGORY_EXTRA[c] || []).filter(d => !miniCmcKeySet.has(d.key));
  const ALL_CORE_KEYS_ORDERED = [...MINI_CMC_KEYS, ...uniqueExtra];
  const groupColors = {core:"rgba(100,140,200,.07)", target:"rgba(98,116,0,.07)"};
  const groupLabels = {core:"miniCMC core (always)", target:`Optimization targets — ${categoriesUsed.map(c=>CMC_CATEGORIES[c]?.label||c).join(" + ")}`};
  const CMC_TERM_TIPS = {
    pI: "Isoelectric point of Fab/Fv. Outside clinical band can increase viscosity or reduce solubility.",
    GRAVY: "Hydropathy index. Higher values indicate higher hydrophobicity and potential aggregation trend.",
    instability_index: "Sequence instability predictor. Higher values suggest lower in vitro stability.",
    SAP_score: "Surface aggregation propensity score (structure-aware). Higher is less favorable.",
    net_charge_pH7: "Net Fv charge at pH 7.",
    pnc: "Negative charge patch intensity (structure-aware).",
    ppc: "Positive charge patch intensity (structure-aware).",
    sfvcsp: "VH/VL charge asymmetry proxy; stronger asymmetry can elevate viscosity risk.",
    hydro_patch_max9: "Maximum 9-aa hydrophobic patch score.",
    psh: "Surface hydrophobicity profile (structure-aware).",
    agg_motifs: "Aggregation-prone sequence motif count.",
    deamidation_sites: "Deamidation liability motif count.",
    isomerization_sites: "Asp isomerization liability motif count.",
    oxidation_sites: "Oxidation-prone motif count.",
    glycosylation_sites: "Potential N-linked glycosylation motif count in Fv.",
    free_cys: "Unpaired cysteine count in variable region.",
  };
  const _termTipBadge = (key) => {
    const txt = CMC_TERM_TIPS[key] || "";
    if (!txt) return "";
    const safe = escapeHtml(txt);
    return ` <span style="font-size:10px;opacity:.72;cursor:help" data-tip="${safe}" onmouseenter="showMetricTip(this)" onmouseleave="hideMetricTip()">?</span>`;
  };
  const _parseRangeFromNormalRange = (raw) => {
    if (raw == null) return null;
    if (Array.isArray(raw) && raw.length >= 2) {
      const a = Number(raw[0]);
      const b = Number(raw[1]);
      if (!Number.isNaN(a) && !Number.isNaN(b)) return [Math.min(a, b), Math.max(a, b)];
      return null;
    }
    const s = String(raw).trim();
    if (!s) return null;
    const m = s.match(/^\s*([+-]?\d+(?:\.\d+)?)\s*(?:to|–|—|-)\s*([+-]?\d+(?:\.\d+)?)\s*$/i);
    if (!m) return null;
    const a = Number(m[1]);
    const b = Number(m[2]);
    if (Number.isNaN(a) || Number.isNaN(b)) return null;
    return [Math.min(a, b), Math.max(a, b)];
  };
  const _resolveRangeForKey = (key, bp, ap) => {
    const fromAp = _parseRangeFromNormalRange(ap?.normal_range);
    if (fromAp) return fromAp;
    const fromBp = _parseRangeFromNormalRange(bp?.normal_range);
    if (fromBp) return fromBp;
    const fallback = _IGG_REF_RANGES[key];
    if (Array.isArray(fallback) && fallback.length >= 2) return [fallback[0], fallback[1]];
    return null;
  };
  const _rangeVerdictForValue = (key, afterValue, bp, ap) => {
    if (afterValue === null || afterValue === undefined) {
      return {verdict: "NO DATA", color: "var(--muted)", label: "No post-optimization value returned."};
    }
    const a = Number(afterValue);
    if (Number.isNaN(a)) {
      return {verdict: "NO DATA", color: "var(--muted)", label: "Post-optimization value is not numeric."};
    }
    const range = _resolveRangeForKey(key, bp, ap);
    if (!range) {
      return {verdict: "NO REF BAND", color: "var(--muted)", label: `No configured acceptance range for ${key}.`};
    }
    const [lo, hi] = range;
    const inRange = a >= lo && a <= hi;
    if (inRange) {
      return {verdict: "WITHIN RANGE", color: "var(--pass)", label: `Within configured range [${fmt(lo)}, ${fmt(hi)}].`};
    }
    return {verdict: "OUTSIDE RANGE", color: "var(--warn)", label: `Outside configured range [${fmt(lo)}, ${fmt(hi)}].`};
  };
  const _rangeVerdictBadge = (rangeVerdict, isStructuralMissing) => {
    if (rangeVerdict && (rangeVerdict.verdict === "WITHIN RANGE" || rangeVerdict.verdict === "OUTSIDE RANGE")) {
      return `<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:${rangeVerdict.color};color:white;opacity:.92" title="${escapeHtml(rangeVerdict.label || rangeVerdict.verdict || "")}">${escapeHtml(rangeVerdict.verdict)}</span>`;
    }
    if (isStructuralMissing) {
      return `<span style="font-size:10px;color:var(--muted)" title="Structure-dependent metric was not recomputed for this variant.">STRUCTURE N/A</span>`;
    }
    if (!rangeVerdict) {
      return `<span style="font-size:10px;color:var(--muted)">NO DATA</span>`;
    }
    return `<span style="font-size:10px;color:var(--muted)" title="${escapeHtml(rangeVerdict.label || rangeVerdict.verdict || "")}">${escapeHtml(rangeVerdict.verdict || "NO DATA")}</span>`;
  };

  const coreTableRows = ALL_CORE_KEYS_ORDERED.map(def => {
    const isTarget = categoryTargetKeys.has(def.key);
    const bp = baseParams.find(p => p.key === def.key);
    if (!bp && !def.structural) return null; // not in baseline at all
    const bVal = bp?.value ?? null;
    if (bVal === null && !def.structural) return null;

    const ap = optParams.find(p => p.key === def.key);
    const aVal = (ap?.value !== null && ap?.value !== undefined) ? ap.value : null;
    const bRisk = bp?.risk || null;
    const aRisk = ap?.risk || null;

    const changed = aVal !== null && String(bVal) !== String(aVal);
    const worsened = aVal !== null && _isValueWorse(def.key, bVal, aVal);
    const improved = aVal !== null && _isValueWorse(def.key, aVal, bVal); // reversed = improved

    const beforeColor = bRisk === "HIGH" ? "var(--fail)" : bRisk === "MODERATE" ? "var(--warn)" : "var(--fg)";
    const afterColor  = worsened ? "var(--fail)" : improved ? "var(--pass)" : (aRisk === "HIGH" ? "var(--fail)" : aRisk === "MODERATE" ? "var(--warn)" : "var(--fg)");
    const rowBg = worsened ? "rgba(248,81,73,.05)" : isTarget && changed ? "rgba(98,116,0,.06)" : "transparent";
    const targetBadge = isTarget ? `<span style="font-size:9px;padding:1px 4px;border-radius:2px;background:var(--accent);color:white;opacity:.85;margin-left:3px">TARGET</span>` : "";
    const changedTag = worsened ? `<span style="color:var(--fail);font-size:10px;margin-left:4px">⚠ worse</span>`
      : improved ? `<span style="color:var(--pass);font-size:10px;margin-left:4px">↑ better</span>`
      : changed ? `<span style="color:var(--muted);font-size:10px;margin-left:4px">changed</span>` : "";

    if (def.structural && aVal === null) {
      return `<tr style="background:${rowBg}">
        <td style="color:var(--muted)">${def.label}${targetBadge}</td>
        <td style="color:${beforeColor};font-weight:bRisk==='HIGH'?'700':'400'">${fmt(bVal)}</td>
        <td style="color:var(--muted);font-style:italic">N/A <span style="font-size:9px">(structure req.)</span></td>
        <td></td>
      </tr>`;
    }
    return `<tr style="background:${rowBg}">
      <td style="color:var(--muted)">${def.label}${targetBadge}</td>
      <td style="color:${beforeColor}">${fmt(bVal)}</td>
      <td style="color:${afterColor};font-weight:${changed?'600':'400'}">${aVal !== null ? fmt(aVal) : '—'}</td>
      <td>${changedTag}</td>
    </tr>`;
  }).filter(Boolean);

  // Group rows by section
  let lastGroup = null;
  const groupedTableRows = ALL_CORE_KEYS_ORDERED.map(def => {
    const isTarget = categoryTargetKeys.has(def.key);
    const bp = baseParams.find(p => p.key === def.key);
    if (!bp && !def.structural) return null;
    const bVal = bp?.value ?? null;
    if (bVal === null && !def.structural) return null;
    const ap = optParams.find(p => p.key === def.key);
    const aVal = (ap?.value !== null && ap?.value !== undefined) ? ap.value : null;
    const bRisk = bp?.risk || null;
    const aRisk = ap?.risk || null;
    const changed = aVal !== null && String(bVal) !== String(aVal);
    const worsened = aVal !== null && _isValueWorse(def.key, bVal, aVal);
    const improved = aVal !== null && _isValueWorse(def.key, aVal, bVal);
    const tolerance = aVal !== null ? _getTolerance(def.key, bVal, aVal) : null;
    const rangeVerdictObj = _rangeVerdictForValue(def.key, aVal, bp, ap);
    const beforeColor = bRisk === "HIGH" ? "var(--fail)" : bRisk === "MODERATE" ? "var(--warn)" : "var(--fg)";
    const afterColor  = worsened ? "var(--fail)" : improved ? "var(--pass)" : (aRisk === "HIGH" ? "var(--fail)" : aRisk === "MODERATE" ? "var(--warn)" : "var(--fg)");
    const rowBg = worsened ? "rgba(248,81,73,.06)" : isTarget && changed ? "rgba(98,116,0,.07)" : "transparent";
    const targetBadge = isTarget ? ` <span style="font-size:9px;padding:0 3px;border-radius:2px;background:var(--accent);color:white;opacity:.8">TARGET</span>` : "";
    const termTip = _termTipBadge(def.key);
    const changedTag = worsened ? `<span style="color:var(--fail);font-size:10px;font-weight:600">⚠ worsened</span>`
      : improved ? `<span style="color:var(--pass);font-size:10px">↑ improved</span>`
      : changed ? `<span style="color:var(--muted);font-size:10px">changed</span>`
      : `<span style="color:var(--muted);font-size:10px;opacity:.5">—</span>`;
    const rangeVerdict = _rangeVerdictBadge(rangeVerdictObj, def.structural && aVal === null);

    let headerRow = "";
    if (def.group !== lastGroup) {
      lastGroup = def.group;
      headerRow = `<tr><td colspan="5" style="padding:6px 0 2px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;border-top:1px solid rgba(0,0,0,.07);background:${groupColors[def.group]||'transparent'}">&nbsp;${groupLabels[def.group]||def.group}</td></tr>`;
    }

    if (def.structural && aVal === null) {
      return headerRow + `<tr style="background:${rowBg}">
        <td style="padding:3px 0;color:var(--muted)">${def.label}${termTip}${targetBadge}</td>
        <td style="padding:3px 6px;font-family:monospace;color:${beforeColor}">${bVal !== null ? fmt(bVal) : '—'}</td>
        <td style="padding:3px 6px;font-family:monospace;color:var(--muted);font-style:italic">N/A</td>
        <td style="padding:3px 0;font-size:10px;color:var(--warn)">struct. failed</td>
        <td style="padding:3px 0"><span style="font-size:10px;color:var(--muted)">N/A</span></td>
      </tr>`;
    }
    return headerRow + `<tr style="background:${rowBg}">
      <td style="padding:3px 0;color:var(--muted)">${def.label}${termTip}${targetBadge}</td>
      <td style="padding:3px 6px;font-family:monospace;color:${beforeColor}">${bVal !== null ? fmt(bVal) : '—'}</td>
      <td style="padding:3px 6px;font-family:monospace;color:${afterColor};font-weight:${changed?'600':'400'}">${aVal !== null ? fmt(aVal) : '—'}</td>
      <td style="padding:3px 0">${changedTag}</td>
      <td style="padding:3px 0">${rangeVerdict}</td>
    </tr>`;
  }).filter(Boolean).join("");

  resDiv.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;font-size:11px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div style="color:var(--pass);font-weight:600;font-size:13px">
          ${categoriesUsed.map(c => CMC_CATEGORIES[c]?.label || c).join(" + ")} Variant — Verification Result
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <div class="muted">ADI: ${fmt(baseAdi)} → <strong style="color:${adiRegression ? 'var(--warn)' : 'var(--accent)'}">${fmt(optAdi)}</strong>${adiRegression ? ` <span style="color:var(--warn)">(Δ ${fmt(adiDelta)})</span>` : (adiDelta !== null ? ` <span style="color:var(--pass)">(+${fmt(adiDelta)})</span>` : "")} &nbsp;|&nbsp; ${muts.length} mutation${muts.length>1?'s':''} applied</div>
          <button type="button" id="variant-toggle-btn-${jobId}" onclick="toggleVariantDetails('${jobId}')" class="btn link" style="padding:3px 9px;font-size:11px">Hide optimization details</button>
        </div>
      </div>
      <div id="variant-details-${jobId}">
      <div style="line-height:1.9">${mutSummary}</div>

      ${bioNote}

      <div style="background:rgba(0,0,0,.03);padding:10px 12px;border-radius:6px">
        <div style="font-weight:600;color:var(--muted);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
          <span>miniCMC + target parameter comparison</span>
          <span style="font-size:10px;font-weight:400;color:var(--muted)">TARGET = optimization goal · RANGE = clinical acceptance verdict · N/A = structure required for recompute</span>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:11px">
          <thead>
            <tr style="border-bottom:1px solid rgba(0,0,0,.1)">
              <th style="text-align:left;padding:2px 0;color:var(--muted);font-weight:600;width:34%">Metric</th>
              <th style="text-align:left;padding:2px 6px;color:var(--muted);font-weight:600;width:16%">Before</th>
              <th style="text-align:left;padding:2px 6px;color:var(--muted);font-weight:600;width:16%">After</th>
              <th style="text-align:left;padding:2px 0;color:var(--muted);font-weight:600;width:16%">Status</th>
              <th style="text-align:left;padding:2px 0;color:var(--muted);font-weight:600">Range verdict</th>
            </tr>
          </thead>
          <tbody>
            ${groupedTableRows || '<tr><td colspan="5" class="muted">No parameters available.</td></tr>'}
          </tbody>
        </table>
        <div style="margin-top:8px;font-size:10px;color:var(--muted)">
          Unchanged metrics confirm optimization did not disturb unrelated properties.
          Structural metrics (N/A) require a full structure-prediction rerun for post-mutation confirmation.
        </div>
      </div>

      ${adoptionBadge}

      <div style="margin-top:10px;padding:12px;background:rgba(0,0,0,.03);border-radius:6px;border:1px solid rgba(0,0,0,.05)">
        <div style="font-weight:600;color:var(--muted);margin-bottom:8px;font-size:11px">Optimized Sequence (mutations highlighted)</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div>
            <div style="font-size:10px;color:var(--muted);margin-bottom:2px;font-weight:600">VH Variant</div>
            <div class="mono" style="word-break:break-all;line-height:1.6;font-size:11px;background:#fff;padding:6px;border-radius:4px;border:1px solid rgba(0,0,0,.05)">
              ${_highlightMutations(baseR.vh_sequence || "", optResult.vh_sequence || "")}
            </div>
          </div>
          <div>
            <div style="font-size:10px;color:var(--muted);margin-bottom:2px;font-weight:600">VL Variant</div>
            <div class="mono" style="word-break:break-all;line-height:1.6;font-size:11px;background:#fff;padding:6px;border-radius:4px;border:1px solid rgba(0,0,0,.05)">
              ${_highlightMutations(baseR.vl_sequence || "", optResult.vl_sequence || "")}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>`;
}

/**
 * @deprecated Replaced by verifyVariantMini. Kept for backwards-compat with old buttons.
 */
async function quickPredictOptimized(jobId) {
  if (!_lastCmcResult || !_lastCmcResult.result) {
    alert("No result available for prediction.");
    return;
  }
  const r = _lastCmcResult.result;
  const rb = r.regular_ab_developability || {};
  const frSuggestions = Array.isArray(rb.fr_modification_suggestions) ? rb.fr_modification_suggestions : [];
  
  if (!frSuggestions.length) {
    alert("No mutation suggestions found to predict.");
    return;
  }

  const vh = (r.vh_sequence || "").trim();
  const vl = (r.vl_sequence || "").trim();
  
  // Aggregate all mutations
  const allMuts = [];
  const seenSites = new Set();
  frSuggestions.forEach(s => {
    const sc = s.sequence_candidates;
    if (!sc) return;
    [sc.fr_positive_charge_sites, sc.fr_negative_charge_sites, sc.fr_instability_sites].forEach(sites => {
      (sites || []).forEach(p => {
        const key = `${p.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
        if (p.index_1 && !seenSites.has(key)) {
          allMuts.push({chain: p.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint});
          seenSites.add(key);
        }
      });
    });
    (sc.fr_hydrophobic_runs || []).forEach(run => {
      (run.per_residue || []).forEach(p => {
        const key = `${run.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
        if (p.index_1 && !seenSites.has(key)) {
          allMuts.push({chain: run.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint});
          seenSites.add(key);
        }
      });
    });
  });

  if (!allMuts.length) {
    alert("No valid mutation sites found.");
    return;
  }

  // Apply mutations
  let mutVh = vh;
  let mutVl = vl;
  allMuts.forEach(m => {
    const idx = m.pos - 1;
    if (m.chain === "VH" || m.chain === "H") {
      if (idx >= 0 && idx < mutVh.length) {
        mutVh = mutVh.substring(0, idx) + m.to + mutVh.substring(idx + 1);
      }
    } else if (m.chain === "VL" || m.chain === "L") {
      if (idx >= 0 && idx < mutVl.length) {
        mutVl = mutVl.substring(0, idx) + m.to + mutVl.substring(idx + 1);
      }
    }
  });

  const resDiv = document.getElementById(`quick-predict-result-${jobId}`);
  if (resDiv) {
    resDiv.style.display = "block";
    resDiv.innerHTML = `<span class="muted">Predicting optimized metrics (sequence-only)…</span>`;
  }

  try {
    const response = await apiFetch(apiJoin("cmc/igg"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        vh_sequence: mutVh,
        vl_sequence: mutVl,
        antibody_type: r.antibody_type || "IgG1",
        project_name: (r.project_name || "optimized") + "-quick",
        report_format: "html",
        predict_fv_structure: false,
        smart_cmc: false
      })
    });
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Prediction failed: ${response.status} ${errText.slice(0, 100)}`);
    }
    const data = await response.json();
    const res = data.result || {};
    
    // Before values
    const clinicalScore = r.clinical_score != null ? r.clinical_score : null;
    const beforeAdi = rb.developability_index ?? r.developability_index ?? clinicalScore;
    const beforePi = r.pI_fab ?? "—";
    const paramRows = Array.isArray(rb.parameters) ? rb.parameters : [];
    const beforePncParam = paramRows.find(p => p.key === "pnc");
    const beforePnc = beforePncParam ? beforePncParam.value : "—";

    // After values
    const optAdi = res.developability_index ?? res.clinical_score ?? "—";
    const optPi = res.pI_fab ?? "—";
    const optRb = res.regular_ab_developability || {};
    const optParamRows = Array.isArray(optRb.parameters) ? optRb.parameters : [];
    
    // Identify target metrics from suggestions
    const targetMetrics = new Set(frSuggestions.map(s => {
      const t = (s.target || "").toLowerCase();
      if (t.includes("negative charge")) return "pnc";
      if (t.includes("positive charge")) return "ppc";
      if (t.includes("hydrophobic patch")) return "psh";
      if (t.includes("instability")) return "instability_index";
      return null;
    }).filter(Boolean));

    // Compare all parameters to find improvements and regressions
    const comparison = [];
    const beforeParams = Array.isArray(rb.parameters) ? rb.parameters : [];
    
    // Structural metrics require Fv structure — cannot be verified in sequence-only mode.
    // These keys are excluded from comparison to avoid showing misleading null values.
    const _structKeys = new Set([
      "psh","ppc","pnc","fv_charge_symmetry","vh_vl_orientation",
      "vh_vl_interface_contacts","mean_interface_distance","min_interface_distance",
      "vernier_exposure","sap_score","surface_hydrophobic_patch",
      "positive_charge_patch","negative_charge_patch","fv_charge_asymmetry"
    ]);
    // Structural target metrics: flag them as "requires structure" instead of hiding silently
    const structTargets = [...targetMetrics].filter(k => _structKeys.has(k));
    const seqTargets    = [...targetMetrics].filter(k => !_structKeys.has(k));

    beforeParams.forEach(bp => {
      const ap = optParamRows.find(p => p.key === bp.key);
      if (!ap) return;
      // Skip structure-dependent metrics entirely (value will be null in sequence-only run)
      if (_structKeys.has(bp.key)) return;
      // Skip if after-value is null (safety net for any other structure-dependent keys)
      if (ap.value === null || ap.value === undefined) return;

      const changed = bp.value !== ap.value;
      const riskWorsened = (bp.risk === "PASS" && (ap.risk === "MODERATE" || ap.risk === "HIGH")) ||
                           (bp.risk === "MODERATE" && ap.risk === "HIGH");
      const isTarget = seqTargets.includes(bp.key);

      if (changed || isTarget || riskWorsened) {
        comparison.push({
          label: bp.label || bp.key,
          key: bp.key,
          before: bp.value,
          after: ap.value,
          beforeRisk: bp.risk,
          afterRisk: ap.risk,
          isTarget,
          worsened: riskWorsened
        });
      }
    });

    const fmt = (v) => (v === null || v === undefined) ? "—" : typeof v === 'number' ? v.toFixed(1) : v;
    const riskColor = (r) => r === "HIGH" ? "var(--fail)" : (r === "MODERATE" ? "var(--warn)" : "var(--pass)");

    // Structural metrics note — always shown in sequence-only mode (structure disabled server-side)
    const structTargetNote = `<div style="padding:7px 10px;background:rgba(201,162,39,.08);border:1px solid rgba(201,162,39,.3);border-radius:4px;font-size:10px;color:var(--accent)">
         ℹ Variant verify runs in sequence-only mode. Metrics shown: pI, net charge, GRAVY, ppc, pnc, instability index, agg motifs, liability sites.
         Structure-dependent metrics (charge_patch_max7, SAP_score, hydro_patch_max9, psh) require Fv structure and are omitted.
       </div>`;

    if (resDiv) {
      let compHtml = comparison.map(c => `
        <div style="display:grid;grid-template-columns:140px 1fr;gap:10px;font-size:11px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
          <div class="muted">${c.label}${c.isTarget ? ' <span style="color:var(--accent);font-size:9px">[Target]</span>' : ''}</div>
          <div>
            <span style="color:${riskColor(c.beforeRisk)}">${fmt(c.before)}</span> 
            <span class="muted">→</span> 
            <strong style="color:${c.worsened ? 'var(--fail)' : riskColor(c.afterRisk)}">${fmt(c.after)}</strong>
            ${c.worsened ? ' <span style="color:var(--fail);font-size:9px">⚠ Regression</span>' : ''}
          </div>
        </div>
      `).join("");

      resDiv.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="color:var(--pass);font-weight:600;font-size:12px">Optimization Impact Analysis <span style="font-size:9px;color:var(--muted);font-weight:400">(sequence metrics only)</span></div>
            <div class="muted" style="font-size:9px">ADI: ${fmt(beforeAdi)} → <strong style="color:var(--accent)">${fmt(optAdi)}</strong></div>
          </div>

          ${structTargetNote}
          
          <div style="background:rgba(255,255,255,0.03);padding:10px;border-radius:6px;border:1px solid rgba(255,255,255,0.05)">
            ${compHtml || '<div class="muted">No sequence-level metric changes detected.</div>'}
          </div>

          ${comparison.some(c => c.worsened) ? `
            <div style="padding:8px;background:rgba(248,81,73,0.1);border:1px solid var(--fail);border-radius:4px;color:var(--fail);font-size:10px">
              <strong>Warning:</strong> Some metrics worsened after optimization. Review trade-offs before proceeding.
            </div>
          ` : `
            <div style="color:var(--pass);font-size:10px">✓ No regressions detected in sequence-level CMC parameters.</div>
          `}
        </div>
      `;
    }
  } catch (err) {
    console.error("Quick Predict Error:", err);
    if (resDiv) resDiv.innerHTML = `<span class="fail">Error: ${err.message}</span>`;
  }
}

let _lastCmcResult = null;
function renderCmcIggResult(data, service, demoId, sequenceName) {
  _lastCmcResult = data;
  const r = (data && data.result) || data || {};
  const displayName = r.project_name || sequenceName || "customer-vhvl";
  const rb = r.regular_ab_developability || {};
  const clinicalScore = r.clinical_score != null ? r.clinical_score : null;
  const devIndex = rb.developability_index ?? r.developability_index ?? clinicalScore;
  const abrefNum =
    r.abref_percentile != null && r.abref_percentile !== ""
      ? Number(r.abref_percentile)
      : clinicalScore != null
        ? Number(clinicalScore)
        : null;
  const isGood = devIndex !== null && !Number.isNaN(devIndex) ? devIndex >= 60 : true;
  
  const refCtxMeta = rb.reference_context || {};
  const obMeta = refCtxMeta.origin_benchmark || {};
  const refPrimary = refCtxMeta.primary || "matched reference";

  const clinicalRankLabel =
    abrefNum != null && !Number.isNaN(abrefNum)
      ? `Top ${100 - Math.round(abrefNum)}% of ${escapeHtml(sanitizeCohortLabelForDisplay(refPrimary.split(":")[0]))}`
      : "—";
  const genAt = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";
  const refPanelMeta = (() => {
    const bits = [];
    if (refCtxMeta.primary) bits.push(String(refCtxMeta.primary));
    if (refCtxMeta.primary_stats_file) bits.push(String(refCtxMeta.primary_stats_file));
    if (obMeta.benchmark_mode) bits.push("benchmark: " + String(obMeta.benchmark_mode));
    return bits.length ? sanitizeCohortLabelForDisplay(bits.join(" · ")) : "Clinical reference";
  })();
  const cmcMetadataPanel = `
    <section class="result-panel">
      <div class="result-title"><strong>Run metadata</strong></div>
      <div class="result-body">
        <table class="kv-table">
          <tr><th>Report format (protocol)</th><td class="mono">${escapeHtml(service.reportVersion || "1.0")}</td></tr>
          <tr><th>Analysis / engine</th><td>${escapeHtml(service.analysisVersion || "—")}</td></tr>
          <tr><th>Reference panel</th><td style="font-size:11px;line-height:1.35">${escapeHtml(refPanelMeta)}</td></tr>
          <tr><th>Sequence / project ID</th><td class="mono">${escapeHtml(displayName)}</td></tr>
          <tr><th>Job ID</th><td class="mono">${escapeHtml(data.job_id || "—")}</td></tr>
          <tr><th>Elapsed</th><td>${data.elapsed_sec != null ? escapeHtml(String(data.elapsed_sec)) + "s" : "—"}</td></tr>
          <tr><th>Generated (browser)</th><td class="mono">${escapeHtml(genAt)}</td></tr>
        </table>
      </div>
    </section>
  `;

  const paramRows = Array.isArray(rb.parameters) ? rb.parameters : [];
  const highCount = paramRows.filter((p) => String(p?.risk || "").toUpperCase() === "HIGH").length;
  const warnCount = paramRows.filter((p) => {
    const risk = String(p?.risk || "").toUpperCase();
    return risk === "MODERATE" || risk === "WARN" || risk === "WARNING";
  }).length;
  
  // Group parameters by domain
  const groups = {
    physicochemical: paramRows.filter(p => p.domain === "physicochemical" || p.domain === "surface_charge" || p.domain === "surface_hydrophobicity" || p.domain === "aggregation" || p.domain === "structural_surface" || p.domain === "structural_geometry"),
    cdr_fingerprint: paramRows.filter(p => p.domain === "cdr_fingerprint" || p.domain === "chemical_liability" || p.domain === "sequence_architecture"),
    humanness: [] // Will be populated from metadata + HPR/AbNatiV2
  };

  const _renderParamGrid = (params, emptyMsg = "No parameters in this category.") => {
    if (!params.length) return `<p class="muted" style="font-size:11px;margin-top:8px">${emptyMsg}</p>`;
    const cells = params.map(p => {
      const risk = (p.risk || "NOT_RUN").toUpperCase();
      const isNotRun = risk === "NOT_RUN";
      const dotColor = isNotRun ? "#555" : (risk === "HIGH" ? "#f44336" : (risk === "MODERATE" ? "#c9a227" : "#00c853"));
      const riskLabel = isNotRun ? "N/A" : risk;
      const valStr = (p.value === null || p.value === undefined || p.value === "") ? "—" : escapeHtml(String(p.value));
      const normalRange = p.normal_range ? `Gate: ${escapeHtml(String(p.normal_range))}` : "";
      const interpShort = (p.interpretation && String(p.interpretation).length) ? escapeHtml(String(p.interpretation).slice(0, 120)) + (String(p.interpretation).length > 120 ? "…" : "") : "";
      const tipTextRaw = [p.label || p.key || "", normalRange || "", interpShort || ""].filter(Boolean).join(" · ");
      const tipText = escapeHtml(tipTextRaw);
      return `<div style="display:flex;align-items:baseline;gap:6px;padding:5px 8px;background:rgba(255,255,255,.03);border-radius:4px;min-width:0">
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${dotColor};flex-shrink:0;margin-top:3px"></span>
        <div style="min-width:0">
          <div style="font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(p.label || p.key || "")}">
            ${escapeHtml((p.label || p.key || "—").replace(" (Fv)", "").replace(" index",""))}
            ${tipText ? `<span style="font-size:10px;opacity:.72;cursor:help" data-tip="${tipText}" onmouseenter="showMetricTip(this)" onmouseleave="hideMetricTip()">?</span>` : ""}
          </div>
          <div style="font-size:11px;font-weight:600;color:${dotColor}">${valStr} <span style="font-size:9px;font-weight:400;color:var(--muted)">${isNotRun ? "N/A" : escapeHtml(riskLabel)}</span></div>
          ${normalRange ? `<div style="font-size:8px;color:var(--muted);white-space:normal;line-height:1.25">${normalRange}</div>` : ""}
        </div>
      </div>`;
    });
    return `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:10px">${cells.join("")}</div>`;
  };

  const frSuggestions = Array.isArray(rb.fr_modification_suggestions) ? rb.fr_modification_suggestions : [];
  const cdrWarnings = Array.isArray(rb.cdr_warnings) ? rb.cdr_warnings : [];
  const adaRefs = rb.ada_context && Array.isArray(rb.ada_context.matched_clinical_entries) ? rb.ada_context.matched_clinical_entries : [];
  const sourceNotes = Array.isArray(rb.source_specific_notes) ? rb.source_specific_notes : [];
  const seqBasis = rb.input_sequence_basis || {};
  const refSeqBasis = rb.reference_context && rb.reference_context.sequence_basis ? rb.reference_context.sequence_basis : {};

  const sourceAwarePanel = rb.parameter_set ? `
    <section class="result-panel">
      <div class="result-title">
        <strong>Physicochemical Profile</strong>
        <span class="run-status ${badgeTone(rb.risk_level || r.overall_status || "DONE")}">${escapeHtml(rb.risk_level || r.overall_status || "DONE")}</span>
      </div>
      <div class="result-body">
        <div class="metric-grid" style="grid-template-columns:repeat(4,minmax(0,1fr))">
          ${metricHtml("Developability Index", devIndex !== null && devIndex !== undefined ? Number(devIndex).toFixed(1) : "—", isGood ? "ok" : "warn", "Composite CMC score (0–100).")}
          ${metricHtml("High-risk", String(highCount), highCount ? "warn" : "ok", "Parameters flagged as HIGH risk.")}
          ${metricHtml("Monitor", String(warnCount), warnCount ? "warn" : "ok", "Parameters in MODERATE zone.")}
        </div>
        ${_renderParamGrid(groups.physicochemical)}
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title"><strong>CDR Fingerprint</strong></div>
      <div class="result-body">
        <div style="font-size:11px;color:var(--muted);margin-bottom:8px">CDR-specific physicochemical features and chemical liabilities.</div>
        ${_renderParamGrid(groups.cdr_fingerprint)}
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title"><strong>Engineering Actions</strong></div>
      <div class="result-body">
        ${(() => {
          const fcf = r.fr_candidate_filter;
          const fvOk = r.fv_structure && r.fv_structure.pdb_url;
          const badges = [];
          badges.push(`<span class="run-status pass" title="CDR positions are never included in mutation candidates">CDR excluded</span>`);
          badges.push(`<span class="run-status pass" title="Structural anchor positions are masked out">Anchors masked</span>`);
          if (fcf && fcf.sasa_filtered) {
            badges.push(`<span class="run-status pass" title="Surface-exposed residues only (filtered by structural accessibility)">Surface-only</span>`);
          } else {
            badges.push(`<span class="run-status warn" title="Structure not available — surface filter not applied.">Standard filter</span>`);
          }
          return `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;align-items:center">
            <span style="font-size:10px;color:var(--muted);margin-right:2px">Engineering filters:</span>
            ${badges.join("")}
          </div>`;
        })()}
        ${(() => {
          // Aggregate all individual mutation hints into a flat summary list
          const allMuts = [];
          const seenSites = new Set();
          const noFrReason = r.no_fr_reason || "";
          const reasonHtml = noFrReason ? `<div style="margin-bottom:12px;padding:10px;background:rgba(255,255,255,0.05);border-radius:6px;color:var(--muted);font-size:12px;font-style:italic;border-left:3px solid var(--accent)"><strong>Smart-CMC Note:</strong> ${escapeHtml(noFrReason)}</div>` : "";

          frSuggestions.forEach(s => {
            const sc = s.sequence_candidates;
            if (!sc) return;
            const sites = sc.fr_positive_charge_sites || [];
            sites.forEach(p => { 
              const key = `${p.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
              if (p.index_1 && !seenSites.has(key)) {
                allMuts.push({chain: p.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, metric: s.target, region: p.region}); 
                seenSites.add(key);
              }
            });
            const negSites = sc.fr_negative_charge_sites || [];
            negSites.forEach(p => {
              const key = `${p.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
              if (p.index_1 && !seenSites.has(key)) {
                allMuts.push({chain: p.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, metric: s.target, region: p.region});
                seenSites.add(key);
              }
            });
            const instSites = sc.fr_instability_sites || [];
            instSites.forEach(p => { 
              const key = `${p.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
              if (p.index_1 && !seenSites.has(key)) {
                allMuts.push({chain: p.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, metric: s.target, region: p.region, motif: p.motif}); 
                seenSites.add(key);
              }
            });
            const runs = sc.fr_hydrophobic_runs || [];
            runs.forEach(run => { (run.per_residue || []).forEach(p => { 
              const key = `${run.chain}-${p.index_1}-${p.from_aa}-${p.to_aa_hint}`;
              if (p.index_1 && !seenSites.has(key)) {
                allMuts.push({chain: run.chain, pos: p.index_1, from: p.from_aa, to: p.to_aa_hint, metric: s.target, region: p.region}); 
                seenSites.add(key);
              }
            }); });
          });
          if (!allMuts.length) return "";
          const cells = allMuts.map(m => `<span style="font-family:monospace;font-size:11px;padding:3px 8px;background:rgba(201,162,39,.12);border-radius:3px;white-space:nowrap">${escapeHtml(m.chain || "")} <strong>${m.pos}</strong> ${escapeHtml(m.from||"")}→<strong style="color:#c9a227">${escapeHtml(m.to||"")}</strong>${m.motif ? ` <span style="color:var(--warn);font-size:11px">[${escapeHtml(m.motif)}]</span>` : ""} <span style="color:var(--muted);font-size:11px">${escapeHtml(m.region||"")}</span></span>`).join(" ");
          // Categorize mutations for unified selector context
          const _catBuckets = _cmcCollectMutationsByCategory(frSuggestions);
          // Stash data needed by the unified selector (callback closure won't see local vars)
          window[`_cmcUnifiedCtx_${data.job_id}`] = {
            kind: "vhvl",
            vh: r.vh_sequence || data.vh_sequence || data.vh || "",
            vl: r.vl_sequence || data.vl_sequence || data.vl || "",
            buckets: _catBuckets,
            baseMetrics: {
              pI: (rb.parameters || []).find(p => p.key === "pI")?.value,
              GRAVY: (rb.parameters || []).find(p => p.key === "GRAVY")?.value,
              instability_index: (rb.parameters || []).find(p => p.key === "instability_index")?.value,
              SAP_score: (rb.parameters || []).find(p => p.key === "SAP_score")?.value,
              ADI: rb.developability_index,
            },
            antibodyType: r.antibody_type || data.antibody_type || "—",
            jobId: data.job_id,
          };
          const _vhvlSectionId = `smartcmc-vhvl-section-${data.job_id}`;
          const _vhvlToggleId = `smartcmc-vhvl-toggle-${data.job_id}`;
          return `<div style="margin-bottom:12px;padding:12px 14px;background:rgba(201,162,39,.07);border:1px solid rgba(201,162,39,.22);border-radius:6px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid rgba(201,162,39,.18)">
              <div style="font-size:13px;font-weight:600;color:var(--warn)">Consolidated mutation suggestions (${allMuts.length} site${allMuts.length > 1 ? "s" : ""})</div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <button type="button" id="${_vhvlToggleId}" onclick="toggleSmartCmcSection('${_vhvlSectionId}','${_vhvlToggleId}')"
                  style="padding:7px 12px;background:#1f3b5b;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:5px;cursor:pointer;font-size:11px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.22)">▼ Hide mutation evaluation</button>
                <button onclick="_openCmcUnifiedFromCtx('${data.job_id}')"
                  style="padding:8px 16px;background:#0d8a72;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.18)">
                  ▶ Open unified Smart-CMC selector (single + multi)
                </button>
              </div>
            </div>
            <div id="${_vhvlSectionId}">
            ${reasonHtml}
            <div>
              <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
                Use the unified selector above to run single-category or combined Smart-CMC verification.
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;line-height:2">${cells}</div>
            </div>
            <div id="variant-result-${data.job_id}" style="margin-top:12px;padding:12px;background:rgba(33,199,217,.08);border:1px solid rgba(33,199,217,.2);border-radius:5px;display:none"></div>
            <div id="quick-predict-result-${data.job_id}" style="display:none"></div>
            </div>
          </div>`;
        })()}
        ${frSuggestions.length ? `
          <table class="kv-table" style="table-layout:fixed;width:100%">
            <colgroup>
              <col style="width:26%" />
              <col style="width:18%" />
              <col style="width:12%" />
              <col style="width:44%" />
            </colgroup>
            <tr><th>Target metric</th><th>Current → Target</th><th>Priority</th><th>Recommended action (FR-only)</th></tr>
            ${frSuggestions.map(s => {
              const prio = (s.priority || "").toUpperCase();
              const badgeCls = prio === "HIGH" ? "fail" : "warn";
              const valCell = s.current_value != null
                ? escapeHtml(String(s.current_value)) + (s.target_range ? ` → <span class="muted">${escapeHtml(s.target_range)}</span>` : "")
                : "—";
              const sc0 = s.sequence_candidates;
              const hasCand = sc0 && typeof sc0 === "object" && (
                (sc0.fr_positive_charge_sites || []).length ||
                (sc0.fr_negative_charge_sites || []).length ||
                (sc0.fr_instability_sites || []).length ||
                (sc0.fr_hydrophobic_runs || []).length ||
                (String(sc0.enumeration_note || "").trim().length > 0) ||
                !!sc0.patch_is_cdr_driven ||
                !!sc0.safe_zone_stop
              );
              const candInner = hasCand ? renderFrSequenceCandidates(sc0, s.mutation_sequences || null) : "";
              const noSitesNote = sc0 && !hasCand
                ? `<p class="muted" style="font-size:10px;margin:0;line-height:1.5">This row has a Smart-CMC target, but <strong>no actionable FR site list was returned</strong> (common reasons: acidic/basic clusters fall in CDRs, candidates fall in Vernier protected zones, or "Structure QC" needs to be enabled for SASA filtering). Rerun with structure prediction enabled, or consider CDR/formulation-level strategies.</p>`
                : "";
              const candRow = (candInner || noSitesNote)
                ? `<tr><td colspan="4" style="padding-top:0;padding-bottom:10px;border-bottom:1px solid rgba(33,199,217,.12);vertical-align:top">${candInner}${noSitesNote}</td></tr>`
                : "";
              const rec = escapeHtml(s.recommendation || "—");
              return `
              <tr>
                <td style="word-break:break-word;vertical-align:top">${escapeHtml(s.target || "—")}</td>
                <td style="font-size:11px;vertical-align:top;word-break:break-word">${valCell}</td>
                <td style="vertical-align:top"><span class="run-status ${badgeCls}">${escapeHtml(prio || "—")}</span></td>
                <td style="vertical-align:top;font-size:11px;line-height:1.45;word-break:break-word">${rec}</td>
              </tr>${candRow}`;
            }).join("")}
          </table>
        ` : (() => {
          // Identify HIGH/MONITOR parameters that have no actionable FR suggestion
          const params = Array.isArray(rb.parameters) ? rb.parameters : [];
          const highRisk = params.filter(p => p.risk === "HIGH" || p.risk === "MODERATE");
          if (highRisk.length) {
            const listed = highRisk.map(p =>
              `<span style="font-family:monospace;font-size:11px;padding:1px 5px;background:rgba(248,81,73,.10);border-radius:3px;color:var(--fail)">${escapeHtml(p.label || p.key)}</span>`
            ).join(" ");
            return `<div style="padding:10px 12px;background:rgba(201,162,39,.07);border:1px solid rgba(201,162,39,.28);border-radius:5px;font-size:11px">
              <div style="font-weight:600;color:var(--warn);margin-bottom:6px">⚠ No actionable FR modification sites identified</div>
              <div style="color:var(--muted);margin-bottom:8px">The flagged metrics below could not be addressed via framework-region mutations. Common reasons:</div>
              <ul style="margin:0 0 8px 16px;color:var(--muted);line-height:1.8">
                <li>The responsible residues are in <strong>CDR loops</strong> — FR-only optimization cannot directly correct CDR-driven charge or hydrophobicity.</li>
                <li>All candidate FR positions failed <strong>Vernier-zone</strong> or <strong>surface-exposure (SASA)</strong> filters — buried residues are excluded to prevent structural destabilization.</li>
                <li>Correction may require <strong>CDR re-engineering</strong>, <strong>charge-balanced linker design</strong>, or a formulation strategy.</li>
              </ul>
              <div style="margin-top:6px">${listed}</div>
            </div>`;
          }
          return `<div class="muted" style="font-size:11px;padding:8px 0">All evaluated framework-region metrics are within the selected reference standard (${escapeHtml(sanitizeCohortLabelForDisplay(refPrimary))}).</div>`;
        })()}
        ${cdrWarnings.length ? `
          <div style="margin-top:12px;padding:8px 12px;background:rgba(201,162,39,.07);border:1px solid rgba(201,162,39,.25);border-radius:5px;font-size:11px">
            <strong style="color:var(--warn)">CDR Advisory Warnings</strong>
            <span class="muted" style="margin-left:6px">(do not modify CDR positions without structural validation)</span>
            <ul style="margin:6px 0 0 16px;line-height:1.9">
              ${cdrWarnings.map(w => `<li>Position <strong>${escapeHtml(String(w.position || "?"))}</strong>: ${escapeHtml(w.finding || "?")} — ${escapeHtml(w.action || "advisory only")}</li>`).join("")}
            </ul>
          </div>
        ` : ""}
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Clinical ADA Context</strong></div>
      <div class="result-body">
        <div class="muted" style="font-size:12px;margin-bottom:10px">
          Historical ADA context is shown only when similar germline records exist; it is not a clinical ADA prediction.
        </div>
        ${adaRefs.length ? `
          <table class="kv-table">
            <tr><th>Clinical entry</th><th>Match</th><th>Reported ADA</th><th>Target</th></tr>
            ${adaRefs.map(a => `
              <tr>
                <td>${escapeHtml(a.name || "—")}</td>
                <td>${escapeHtml(a.match_type || "—")}</td>
                <td>${escapeHtml(a.ada_display || "—")}</td>
                <td>${escapeHtml(a.target || "—")}</td>
              </tr>
            `).join("")}
          </table>
        ` : `<div class="muted">No matched clinical ADA entries were found for the returned germline context.</div>`}
      </div>
    </section>
  ` : "";

  const vhIn = (r.vh_sequence || "").trim();
  const vlIn = (r.vl_sequence || "").trim();
  const fvS = r.fv_structure;
  const fvPanel =
    fvS && (fvS.pdb_url || fvS.error)
      ? `
    <section class="result-panel" style="border-color:rgba(33,199,217,.2)">
      <div class="result-title"><strong>Fv structure modeling</strong></div>
      <div class="result-body" style="font-size:11px">
        ${
          fvS.pdb_url
            ? `<p>Method: <span class="mono">In-silico Fv modeling</span></p>
          <p>Confidence (pLDDT-eq): ${fvS.plddt_eq != null ? escapeHtml(String(fvS.plddt_eq)) : "—"}
            &middot; VH–VL angle proxy: ${fvS.vh_vl_angle_deg != null ? escapeHtml(String(fvS.vh_vl_angle_deg)) + "°" : "—"}</p>
          <p class="muted" style="margin-top:6px">${escapeHtml(fvS.note || "")}</p>`
            : `<p class="warn">${escapeHtml(fvS.error || "Unavailable")}</p>
          <p class="muted">${escapeHtml(fvS.note || "")}</p>`
        }
      </div>
    </section>
  `
      : "";
  const inputSeqPanel = (vhIn || vlIn) ? `
    <section class="result-panel" style="border-color:rgba(33,199,217,.2)">
      <div class="result-title"><strong>Input sequences (VH / VL)</strong></div>
      <div class="result-body" style="font-size:11px">
        <p class="muted" style="margin:0 0 8px 0">1-letter codes as submitted for this CMC run. Candidate mutation positions below refer to these chains (1-based index within each chain).</p>
        ${vhIn ? `<div class="panel-label" style="margin-bottom:4px">VH <span class="muted">(${vhIn.length} aa)</span></div>
          <div class="mono" style="word-break:break-all;line-height:1.5;padding:6px 8px;background:rgba(0,0,0,.2);border-radius:4px">${escapeHtml(vhIn)}</div>` : ""}
        ${vlIn ? `<div class="panel-label" style="margin:10px 0 4px 0">VL <span class="muted">(${vlIn.length} aa)</span></div>
          <div class="mono" style="word-break:break-all;line-height:1.5;padding:6px 8px;background:rgba(0,0,0,.2);border-radius:4px">${escapeHtml(vlIn)}</div>` : ""}
      </div>
    </section>
  ` : "";

  const _refPanelShort = sanitizeCohortLabelForDisplay(refPrimary.split(":")[0].trim());
  const _refPanelNote = refCtxMeta.primary_stats_file || "";
  const abref458Banner = `
    <div class="result-panel" style="border-color:rgba(33,199,217,.28)">
      <div class="result-title" style="background:rgba(33,199,217,.04)">
        <strong style="color:var(--accent)">Reference Benchmark</strong>
        <span class="run-status ${isGood ? "pass" : "warn"}">${isGood ? "PASS" : "REVIEW"}</span>
      </div>
      <div class="result-body">
        <div style="font-size:11px;color:var(--muted);margin-bottom:12px">
          ${escapeHtml(sanitizeCohortLabelForDisplay(refPrimary))}${_refPanelNote ? ` &middot; <span style="opacity:.7">${escapeHtml(sanitizeCohortLabelForDisplay(_refPanelNote))}</span>` : ""}
        </div>
        <div class="clinical-rank ${isGood ? "" : "warn-rank"}">
          <div>
            <div class="clinical-score-val">${devIndex !== null && devIndex !== undefined && !Number.isNaN(devIndex) ? Number(devIndex).toFixed(1) : "—"}</div>
            <div class="clinical-score-label">Developability Index (ADI) / 100</div>
          </div>
          <div>
            <div class="clinical-score-val" style="font-size:1.5rem;color:var(--text)">
              ${abrefNum != null && !Number.isNaN(abrefNum) ? abrefNum.toFixed(1) + " / 100" : "—"}
            </div>
            <div class="clinical-score-label">Reference composite index (0–100)</div>
            <div class="clinical-pct" style="margin-top:10px">${clinicalRankLabel}</div>
            <div style="font-size:11px;color:var(--muted);margin-top:3px">Percentile tier vs ${escapeHtml(_refPanelShort)}</div>
          </div>
        </div>
      </div>
    </div>
  `;

  // HPR Index & p-AbNatiV2 humanness
  // HPR: 9-mer repertoire overlap vs human OAS (independent algorithm from AbNatiV2)
  // ADA-validated thresholds from InSynBio HPR-ADA analysis (n=222 HZ+FH therapeutics):
  //   ≥0.95 Low | 0.85–0.95 Medium | 0.75–0.85 Medium-High | <0.75 High
  //   Immunology indication: each tier carries higher risk than oncology.
  const _hprObj = typeof r.hpr_index === "object" && r.hpr_index ? r.hpr_index : {};
  const _hprComb = (_hprObj.combined || _hprObj.humanized || {});
  const _hprScore = _hprComb.score ?? null;
  const _hprStr = _hprScore !== null ? Number(_hprScore).toFixed(4) : (r.hpr_error ? "Error" : "—");
  // _hprTone is set after origin-aware threshold block below
  const _hprVhScore = (_hprObj.vh || {}).score ?? null;
  const _hprVlScore = (_hprObj.vl || {}).score ?? null;

  // p-AbNatiV2: paired VH+VL humanness (neural network, distinct algorithm)
  // Source: AbNatiV "Heavy-Light Score" — combined VH+VL distribution fit to human antibodies.
  // Internal ref (n=458 engineered therapeutics): p25=78.7%, median=82.6%, p75=85.4%
  // Internal ref (n=382 natural human IgG): median=92.8%
  // Note: pairing_likelihood (AbNatiV "Pairing Score") is a DIFFERENT metric measuring
  //   VH+VL co-occurrence probability (scale 0.000–0.009, not 0–1). Both come from AbNatiV2
  //   but measure different things. For CMC display, paired_humanness is the actionable metric.
  const _pab = typeof r.p_abnativ2 === "object" && r.p_abnativ2 ? r.p_abnativ2 : {};
  const _pabHumanness = _pab.paired_humanness ?? null;
  const _pabVhHumanness = _pab.vh_humanness ?? null;
  const _pabVlHumanness = _pab.vl_humanness ?? null;
  const _fmtPct = (v) => v !== null ? (Number(v) * 100).toFixed(1) + "%" : "—";
  const _pabHumanStr = _fmtPct(_pabHumanness);

  // Origin-aware thresholds (internal reference, InSynBio data):
  // antibody_origin is already read below as _rabOrigin (from r.regular_ab_developability.antibody_origin)
  // We need _rabOrigin early — compute it here:
  const _rabOriginEarly = (typeof r.regular_ab_developability === "object" && r.regular_ab_developability)
    ? (r.regular_ab_developability.antibody_origin || "")
    : (r.antibody_origin || "");
  const _isHumanized = _rabOriginEarly.includes("humanized") || _rabOriginEarly === "engineered";
  const _isFullyHuman = _rabOriginEarly.includes("transgenic") || _rabOriginEarly.includes("phage") || _rabOriginEarly === "fully_human";
  const _isBCell = _rabOriginEarly.includes("b_cell");

  // Thresholds by origin (all based on internal p25 per class):
  // Humanized:    paired≥80.5%, vh≥74.4%, vl≥80.3%, HPR≥0.73
  // Fully Human:  paired≥90.9%, vh≥88.0%, vl≥90.7%, HPR≥0.88
  // B-cell:       no ADA gate — always show ok; reference median≥91.8% HPR, ≥91.8% Paired
  const _threshPaired = _isFullyHuman ? 0.909 : (_isBCell ? 0.0 : 0.805);
  const _threshVh     = _isFullyHuman ? 0.880 : (_isBCell ? 0.0 : 0.744);
  const _threshVl     = _isFullyHuman ? 0.907 : (_isBCell ? 0.0 : 0.803);
  const _threshHpr    = _isFullyHuman ? 0.877 : (_isBCell ? 0.0 : 0.731);
  const _originLabel  = _isFullyHuman ? "Fully Human p25" : (_isBCell ? "B-cell (ref only)" : "Humanized p25");

  // Simplified display — two values only: actual % + gate p25 %.
  // Decimal form (0.826) is redundant with percentage (82.6%); they are the same number.
  // Format: "82.6% · gate ≥80.5%" or "82.6% (ref)" for B-cell.
  const _withRef = (raw, thresh, isBcell) =>
    raw === null ? "—" :
    isBcell ? `${_fmtPct(raw)} (ref)` :
    `${_fmtPct(raw)} · gate ≥${(thresh*100).toFixed(1)}%`;
  const _withRefHpr = _withRef;

  const _pabHumanTone = _pabHumanness !== null ? (_isBCell || _pabHumanness >= _threshPaired ? "ok" : "warn") : "";
  const _pabHumanDisplay = _withRef(_pabHumanness, _threshPaired, _isBCell);
  const _pabVhStr = _pabVhHumanness !== null ? _withRef(_pabVhHumanness, _threshVh, _isBCell) : (_pab.error ? "Error" : "—");
  const _pabVhTone = _pabVhHumanness !== null ? (_isBCell || _pabVhHumanness >= _threshVh ? "ok" : "warn") : "";
  const _pabVlStr = _pabVlHumanness !== null ? _withRef(_pabVlHumanness, _threshVl, _isBCell) : (_pab.error ? "Error" : "—");
  const _pabVlTone = _pabVlHumanness !== null ? (_isBCell || _pabVlHumanness >= _threshVl ? "ok" : "warn") : "";

  const _HPR_TIP = `HPR (Human Peptide Repertoire) Index — measures overlap of antibody 9-mers with human OAS repertoire (0–1). "gate ≥XX%" shown = p25 (25th-percentile floor) of the ${_originLabel} clinical reference panel; scores below this gate are in the bottom quartile of approved antibodies of this class. Active gate: ${_isFullyHuman ? "Fully Human p25 = 87.7%" : _isBCell ? "B-cell derived (reference only, no ADA gate)" : "Humanized p25 = 73.1%"}. ADA risk tiers: ≥0.95 Low | 0.85–0.95 Medium | 0.75–0.85 Med-High | <0.75 High.`;
  const _PAB_PAIRED_TIP = `p-AbNatiV2 Paired Humanness — combined VH+VL sequence similarity to human antibody repertoire (neural network, 0–1). "gate ≥XX%" = p25 of ${_originLabel} reference panel. Active gate: ≥${(_threshPaired*100).toFixed(1)}%. A score below this gate does not mean the antibody is not human — it means it is in the bottom quartile of the reference cohort.`;
  const _PAB_VH_TIP = `p-AbNatiV2 VH Humanness — VH chain humanness score from AbNatiV2. "gate ≥XX%" = p25 of ${_originLabel} reference. Active gate: ≥${(_threshVh*100).toFixed(1)}%.`;
  const _PAB_VL_TIP = `p-AbNatiV2 VL Humanness — VL chain humanness score from AbNatiV2. "gate ≥XX%" = p25 of ${_originLabel} reference. Active gate: ≥${(_threshVl*100).toFixed(1)}%.`;
  const _hprTone = _hprScore !== null ? (_isBCell || _hprScore >= _threshHpr ? "ok" : "warn") : "";

  const _rabOrigin = _rabOriginEarly;
  const _isBCellDerived = _isBCell;
  const specificBody = `
    <section class="result-panel">
      <div class="result-title"><strong>Humanness Indicators (HPR + p-AbNatiV2)</strong></div>
      <div class="result-body">
        <div style="font-size:10px;color:var(--muted);margin-bottom:8px;font-style:italic">Format: actual % · gate ≥p25% — gate is the 25th percentile of the ${escapeHtml(_originLabel)} clinical reference panel</div>
        ${_isBCellDerived ? `<div style="background:#eaf4ea;border-left:3px solid #3a9a3a;padding:6px 10px;border-radius:4px;font-size:11px;margin-bottom:8px;color:#1a5c1a">
          <strong>B-cell derived antibody:</strong> CMC developability assessed normally.
          Immunogenicity (ADA) indicators shown for reference only —
          FDA/EMA do not require ADA monitoring for antibodies derived from human B cells.
          Humanness scores are expected to be high (HPR median ≈ 0.918; Paired Humanness median ≈ 94%).
        </div>` : ""}
        <div class="metric-grid">
          ${metricHtml("HPR Index (VH+VL)", _withRefHpr(_hprScore, _threshHpr, _isBCellDerived), _isBCellDerived ? "ok" : _hprTone, _HPR_TIP)}
          ${metricHtml("Paired Humanness", _pabHumanDisplay, _isBCellDerived ? "ok" : _pabHumanTone, _PAB_PAIRED_TIP)}
          ${metricHtml("VH Humanness", _pabVhStr, _isBCellDerived ? "ok" : _pabVhTone, _PAB_VH_TIP)}
          ${metricHtml("VL Humanness", _pabVlStr, _isBCellDerived ? "ok" : _pabVlTone, _PAB_VL_TIP)}
        </div>
        ${r.hpr_error ? `<div class="muted" style="font-size:10px;margin-top:6px">ⓘ HPR: ${escapeHtml(r.hpr_error)}</div>` : ""}
        ${_pab.error ? `<div class="muted" style="font-size:10px">ⓘ p-AbNatiV2: ${escapeHtml(_pab.error)}</div>` : ""}
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Physicochemical Profile</strong></div>
      <div class="result-body">
        <div class="metric-grid" style="grid-template-columns:repeat(5,1fr)">
          ${metricHtml("pI (Fab)", fmt(r.pI_fab), valueOutOfRange(r.pI_fab, 4.5, 9.5) ? "warn" : "ok", "Isoelectric point of Fv region. Acceptable range 4.5–9.5; preferred 6.5–8.5 for solubility and reduced self-association.")}
          ${metricHtml("GRAVY", fmt(r.GRAVY), (r.GRAVY || 0) > -0.1 ? "warn" : "ok", "Grand Average of Hydropathicity. Negative = hydrophilic (preferred). >−0.1 indicates hydrophobic character associated with aggregation risk.")}
          ${metricHtml("Instability Index", fmt(r.instability_index), (r.instability_index || 0) > 40 ? "warn" : "ok", "In vitro stability predictor (Guruprasad 1990). <40 = stable; ≥40 = elevated instability risk.")}
          ${metricHtml("Hydro Patch", fmt(r.hydro_patch_max9), (r.hydro_patch_max9 || 0) > 0.75 ? "warn" : "ok", "Maximum hydrophobic patch score in a 9-residue window. >0.75 indicates surface hydrophobic exposure — associated with aggregation and reduced solubility.")}
          ${metricHtml("Charge Patch", fmt(r.charge_patch_max7), (r.charge_patch_max7 || 0) > 4 ? "warn" : "ok", "Maximum charge patch in a 7-residue window. >4 indicates concentrated surface charge — may cause non-specific binding or viscosity issues.")}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Sequence Liability Scan</strong><span class="run-status DONE">DONE</span></div>
      <div class="result-body">
        <div class="metric-grid">
          ${metricHtml("Deamidation", r.n_deamidation ?? "0", (r.n_deamidation || 0) > 3 ? "warn" : "ok", "CDR deamidation motifs (NG, NS, NT, NA). Each site increases risk of charge heterogeneity and potency loss over shelf life. Gate: ≤3 sites.")}
          ${metricHtml("Isomerization", r.n_isomerization ?? "0", (r.n_isomerization || 0) > 3 ? "warn" : "ok", "CDR aspartate isomerization motifs (DG, DS, DT). Produces isoAsp; alters CDR conformation and may reduce binding. Gate: ≤3 sites.")}
          ${metricHtml("Oxidation", r.n_oxidation ?? "0", (r.n_oxidation || 0) > 7 ? "warn" : "ok", "Methionine/tryptophan oxidation-susceptible sites (exposed Met, Trp in CDR). Increases during storage. Gate: ≤7 sites.")}
          ${metricHtml("Glycosylation", r.n_glycosylation ?? "0", (r.n_glycosylation || 0) > 1 ? "warn" : "ok", "N-linked glycosylation sequons (NxS/T, x≠P) in Fv region. Variable glycosylation causes batch heterogeneity. Gate: ≤1 in Fv.")}
        </div>
        <table class="kv-table" style="margin-top:10px">
          <tr><th>Flag list</th><td>${(r.liability_flags || []).length ? (r.liability_flags || []).join("<br>") : "No sequence liability flags returned."}</td></tr>
        </table>
      </div>
    </section>
  `;

  const reportErrNote = (data.report_error || (data.result && data.result.report_error))
    ? `<section class="result-panel" style="border-color:rgba(244,67,54,.3)">
        <div class="result-title"><strong style="color:var(--fail)">Report generation error</strong></div>
        <div class="result-body"><pre style="font-size:10px;white-space:pre-wrap;color:var(--fail)">${escapeHtml(data.report_error || data.result.report_error)}</pre></div>
      </section>`
    : "";
  // Stash CMC input sequences so the downstream cDNA routing button can forward them
  window._lastCmcInputVh = (r.vh_sequence || "").trim();
  window._lastCmcInputVl = (r.vl_sequence || "").trim();
  window._lastCmcInputName = (r.project_name || sequenceName || "").trim();
  const cmcDownstreamPanel = `
    <section class="result-panel" style="border-color:rgba(34,211,238,.25)">
      <div class="result-title" style="background:rgba(34,211,238,.05)">
        <strong style="color:#22d3ee">Downstream: cDNA Optimization</strong>
        <span style="font-size:11px;color:var(--muted)">Carry assessed VH/VL directly to IgG cDNA assembly</span>
      </div>
      <div class="result-body">
        <p style="font-size:11px;color:var(--muted);margin:0 0 10px">
          Assemble full human IgG (signal peptide + VH + CH1 + hinge + Fc; VL + CL) and codon-optimize for HEK293 / CHO / E. coli using the sequences evaluated above.
        </p>
        <div class="button-row">
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaFromCmcIgg()">cDNA Optimization (IgG) →</button>
        </div>
      </div>
    </section>`;
  setOutput(cmcMetadataPanel + inputSeqPanel + fvPanel + abref458Banner + reportErrNote + sourceAwarePanel + specificBody + cmcDownstreamPanel);
  updateResultRail({
    status: r.overall_status || "DONE",
    summaryTitle: `${service.label} completed`,
    summaryText: `${(DEMOS[demoId] || {}).label || sequenceName || demoId} assessed against ${_refPanelShort}.`,
    refDb: _refPanelShort,
    clinicalRank: clinicalRankLabel,
    metrics: [
      {label: "pI", value: fmt(r.pI_fab), tone: valueOutOfRange(r.pI_fab, 4.5, 9.5) ? "warn" : "ok"},
      {label: "Instability Index", value: fmt(r.instability_index), tone: (r.instability_index || 0) > 40 ? "warn" : "ok"},
      {label: "ADI", value: devIndex !== null && devIndex !== undefined ? Number(devIndex).toFixed(1) : "—", tone: isGood ? "ok" : "warn"},
      {label: "Ref score (0–100)", value: abrefNum != null && !Number.isNaN(abrefNum) ? abrefNum.toFixed(1) : "—", tone: isGood ? "ok" : "warn"},
      {label: "Flags", value: (r.overall_flags || []).length},
    ],
    recommendation: (r.overall_status || "").toUpperCase() === "PASS"
      ? `CMC profile is acceptable. ${clinicalRankLabel !== "—" ? `Ranked ${clinicalRankLabel}.` : ""} Use the full report for downstream discussion.`
      : `Review flagged CMC issues before escalation. ${r.cmc_n_warn || 0} warnings, ${r.cmc_n_fail || 0} fails returned.`,
    artifacts: buildArtifacts(data),
    metadata: [
      {label: "Report format", value: service.reportVersion || "1.0", mono: true},
      {label: "Sequence ID", value: displayName, mono: true},
      {label: "Demo ID", value: demoId, mono: true},
      {label: "Reference panel", value: _refPanelShort},
      {label: "Job ID", value: data.job_id || "—", mono: true},
      {label: "Elapsed", value: data.elapsed_sec ? `${data.elapsed_sec}s` : "—"},
      {label: "Analysis Version", value: service.analysisVersion, mono: true},
    ],
  });
}

// ── VHH Structure (NanoBodyBuilder2) ─────────────────────────────────────────

async function runVhhStructural(service) {
  const seq = normalizeSeq(document.getElementById("vhh-struct-seq").value);
  const nameEl = document.getElementById("vhh-struct-name");
  const seqName = (nameEl && nameEl.value.trim()) || "vhh";
  const err = validateSeq(seq, "VHH", 90, 200);
  if (err) {
    setOutput(errorPanel(err));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:err, metrics:[], recommendation:"Correct the VHH sequence.", artifacts:[], metadata:[]});
    return;
  }
  const body = JSON.stringify({ vhh_sequence: seq, sequence_name: seqName });
  setRunning("Submitting VHH structure prediction…", 0);
  setOutput("");
  window.__activeAsyncAbort = false;
  try {
    const startRes = await apiFetch(apiJoin("structure/nanobodybuilder2/async"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body,
    });
    const start = await startRes.json();
    if (!startRes.ok) throw new Error(start.detail || JSON.stringify(start));
    const jobId = start.job_id;
    window.__activeAsyncJobId = jobId;
    setAsyncJobCancelButtonsVisible(true);
    setRunning(`VHH structure ${jobId} — queued…`, 0);

    for (let i = 0; i < 600; i++) {
      await sleep(3000);
      if (window.__activeAsyncAbort) {
        setAsyncJobCancelButtonsVisible(false);
        clearRunning();
        setOutput(errorPanel("Job cancelled by user."));
        return;
      }
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
      if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
      const poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      const pct = poll.progress != null ? Number(poll.progress) : null;
      const note = (poll.progress_note && String(poll.progress_note).trim()) || st;
      setRunning(`VHH structure ${jobId} — ${note}`, pct);

      if (st === "done") {
        setAsyncJobCancelButtonsVisible(false);
        window.__activeAsyncJobId = null;
        clearRunning();
        renderVhhStructuralResult(poll, jobId, seqName);
        return;
      }
      if (st === "failed" || st === "cancelled") {
        setAsyncJobCancelButtonsVisible(false);
        window.__activeAsyncJobId = null;
        clearRunning();
        const errMsg = poll.error || poll.progress_note || `Job ${st}.`;
        setOutput(errorPanel(errMsg));
        updateResultRail({status:"FAIL", summaryTitle: st === "cancelled" ? "Cancelled" : "Structure prediction failed", summaryText:errMsg, metrics:[], recommendation:"Check input sequence and rerun.", artifacts:[], metadata:[{label:"Job ID", value:jobId, mono:true}]});
        return;
      }
    }
    throw new Error("VHH structure job timed out.");
  } catch (err) {
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"Structure prediction failed", summaryText:err.message, metrics:[], recommendation:"Inspect error and rerun.", artifacts:[], metadata:[]});
  }
}

function renderVhhStructuralResult(data, jobId, seqName) {
  const r = data.result || {};
  const pdbUrl = r.pdb_url ? apiJoin(r.pdb_url.replace(/^\//, "")) : null;
  const statusOk = !!pdbUrl;
  const detailHtml = statusOk
    ? `<a href="${escapeHtml(pdbUrl)}" download="${escapeHtml(r.pdb_filename || "vhh.pdb")}">Download PDB</a>`
    : `<pre class="mono" style="white-space:pre-wrap;font-size:11px">${escapeHtml((r.error || "No PDB returned by backend.").slice(0, 800))}</pre>`;
  const logHtml = r.log
    ? `<details style="margin-top:10px"><summary class="muted" style="cursor:pointer">Build log</summary><pre class="mono" style="white-space:pre-wrap;font-size:11px;max-height:220px;overflow:auto">${escapeHtml(r.log)}</pre></details>`
    : "";
  setOutput(`
      <section class="result-panel">
        <div class="result-title"><strong>VHH model</strong><span class="run-status ${statusOk ? "pass" : "warn"}">${statusOk ? "DONE" : "WARN"}</span></div>
        <div class="result-body">
          <p class="muted" style="margin-bottom:10px">${escapeHtml(r.tool || "NanoBodyBuilder2")} · Job <span class="mono">${escapeHtml(jobId)}</span> · Sequence <span class="mono">${escapeHtml(seqName)}</span></p>
          <table class="kv-table">
            <thead><tr><th>Pair</th><th>Status</th><th>PDB / detail</th></tr></thead>
            <tbody>
              <tr>
                <td class="mono">${escapeHtml(seqName)}</td>
                <td><span class="run-status ${statusOk ? "pass" : "fail"}">${statusOk ? "OK" : "FAIL"}</span></td>
                <td>${detailHtml}</td>
              </tr>
            </tbody>
          </table>
          ${pdbViewerLinksHtml()}
          ${logHtml}
        </div>
      </section>
    `);
  const arts = pdbUrl ? [{label: r.pdb_filename || "vhh.pdb", url: pdbUrl, download: true, primary: false}] : [];
  updateResultRail({
    status: statusOk ? "PASS" : "WARN",
    summaryTitle:"ImmuneBuilder VHH",
    summaryText: statusOk ? `1/1 PDB generated for ${seqName}.` : `No PDB generated for ${seqName}.`,
    metrics:[
      { label: "Job", value: jobId, mono: true },
      { label: "Pairs", value: "1" },
      { label: "OK", value: statusOk ? "1" : "0" },
    ],
    recommendation: statusOk ? "Download PDB above; open in ChimeraX / PyMOL." : "Check backend error/log and rerun.",
    artifacts: arts,
    metadata:[{label:"Job ID", value:jobId, mono:true}, {label:"Tool", value:"NanoBodyBuilder2 (ImmuneBuilder)"}]
  });
}

// ── VHH Humanization ──────────────────────────────────────────────────────────

async function runVhhHumanization(service) {
  const seq = normalizeSeq(document.getElementById("vhh-seq").value);
  const demoId = document.getElementById("vhh-demo").value;
  const errs = [validateSeq(seq, "VHH", 110, 140)].filter(Boolean);
  if (errs.length) {
    setOutput(errorPanel(errs.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errs.join(" · "), metrics:[], recommendation:"Correct the VHH sequence input.", artifacts:[], metadata:[]});
    return;
  }
  const vhhSeqName = (document.getElementById("vhh-name") && document.getElementById("vhh-name").value.trim()) || "";
  const useAsync = document.getElementById("vhh-async") && document.getElementById("vhh-async").checked;
  // Map Run Mode → strategy
  const selectedRunMode = (document.querySelector('input[name="vhh-run-mode"]:checked') || {}).value || "standard_delivery";
  const vhhStrategy = selectedRunMode === "quick_preview" ? "C"
                    : selectedRunMode === "enhanced_rescue" ? "A"
                    : "auto";  // standard_delivery → V5.0 dynamic
  const body = JSON.stringify({
    vhh_sequence: seq,
    source_species: document.getElementById("vhh-species").value,
    strategy: vhhStrategy,
    top_k: 3,
    report_format: "html",
    ...(vhhSeqName && { sequence_name: vhhSeqName }),
  });
  const modeLabel = selectedRunMode === "quick_preview" ? "Quick Preview"
                  : selectedRunMode === "enhanced_rescue" ? "Enhanced Rescue"
                  : "Standard Delivery";
  if (useAsync) {
    setRunning(`Submitting VHH Humanization — ${modeLabel}…`, 0);
  } else {
    setRunning(`Running VHH Humanization (${modeLabel}) — enable Background job for live progress…`);
  }
  window.__vhhLastInputSeq = seq;   // saved for FR/CDR comparison display
  setOutput("");
  window.__activeAsyncAbort = false;
  try {
    let data;
    if (useAsync) {
      // Submit to async endpoint — get job_id immediately
      const startRes = await apiFetch(apiJoin("humanize/vhh/async"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body,
      });
      const start = await startRes.json();
      if (!startRes.ok) throw new Error(start.detail || JSON.stringify(start));
      const jobId = start.job_id;
      window.__activeAsyncJobId = jobId;
      setAsyncJobCancelButtonsVisible(true);
      setRunning(`VHH job ${jobId} — queued — polling…`, 0);

      // Poll GET /jobs/{job_id}
      let poll;
      for (let i = 0; i < 600; i++) {
        await sleep(2000);
        if (window.__activeAsyncAbort) {
          setAsyncJobCancelButtonsVisible(false);
          clearRunning();
          setOutput(errorPanel("Job cancelled by user."));
          return;
        }
        const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
        if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
        poll = await pr.json();
        const st = (poll.status || "").toLowerCase();
        const pct = poll.progress != null ? Number(poll.progress) : null;
        const note = (poll.progress_note && String(poll.progress_note).trim()) || st;
        setRunning(`VHH ${jobId} — ${note}`, pct);

        if (st === "done") {
          data = poll;
          break;
        }
        if (st === "failed" || st === "cancelled") {
          setAsyncJobCancelButtonsVisible(false);
          window.__activeAsyncJobId = null;
          clearRunning();
          const errMsg = poll.error || poll.progress_note || (st === "cancelled" ? "Job cancelled." : "VHH job failed.");
          setOutput(errorPanel(errMsg));
          updateResultRail({status:"FAIL", summaryTitle: st === "cancelled" ? "Job cancelled" : "VHH humanization failed", summaryText:errMsg, metrics:[], recommendation: st === "cancelled" ? "Job was aborted. Resubmit when ready." : "Check server logs.", artifacts:[], metadata:[{label:"Job ID", value:jobId, mono:true}]});
          return;
        }
      }
      if (!data) throw new Error("VHH job timed out after polling limit.");
    } else {
      // Synchronous run
      const res = await apiFetch(apiJoin("humanize/vhh"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body,
      });
      data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    }
    
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    const _vhhRunId = `vhh-${Date.now()}`;
    await recordRunDebit(state.service, { runRecordId: _vhhRunId, demoId });
    renderVhhHumanizationResult(data, service, demoId);
  } catch (err) {
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"VHH humanization failed", summaryText:err.message, metrics:[], recommendation:"Inspect the returned error and rerun.", artifacts:[], metadata:[]});
  }
}

function renderVhhHumanizationResult(data, service, demoId) {
  const r = data.result || {};
  try {
    if (r.humanized_sequence) {
      sessionStorage.setItem("insynbio_last_humanized_vhh", String(r.humanized_sequence));
      sessionStorage.setItem("insynbio_last_humanized_name", String(r.sequence_name || vhhSeqName || ""));
      sessionStorage.setItem("insynbio_last_humanization_kind", "vhh");
      sessionStorage.removeItem("insynbio_last_humanized_vh");
      sessionStorage.removeItem("insynbio_last_humanized_vl");
    }
  } catch (e) {}

  // ── Strategy path detection ──────────────────────────────────────────────────
  const fpRec = (r.feasibility_prescreen || {}).recommendation || "humanization";
  const isSurfaceReshaping    = fpRec === "surface_reshaping_only";
  const isPlusReshape         = fpRec === "humanization_plus_reshape";
  const isPlusCharge          = fpRec === "humanization_plus_charge";
  const srData = r.surface_reshaping || {};

  // ── V5.0 Three-tier route label (external-friendly naming) ──────────────────
  // Tier 1: Sequence-Based Humanization (template match, no structure needed)
  // Tier 2: Structure-Guided Humanization (IgFold/ABB2 + SASA + dynamic Tier)
  // Tier 3: Repertoire-Guided Refinement (9-aa context voting, no-template fallback)
  const routeTier = (() => {
    if (isSurfaceReshaping) return "tier3";
    if (r.structure_computed) return "tier2";
    return "tier1";
  })();
  const routeLabels = {
    tier1: { name: "Sequence-Based Humanization",    color: "#0891b2", badge: "Framework Graft" },
    tier2: { name: "Structure-Guided Humanization",  color: "#059669", badge: "V5.0 Structure" },
    tier3: { name: "Repertoire-Guided Refinement",   color: "#d97706", badge: "Context Refinement" },
  };
  const routeInfo = routeLabels[routeTier];
  const frIdStr = r.human_vh3_identity != null ? ` · FR identity ${fmt(r.human_vh3_identity, 1)}%` : "";
  const dynamicTierStr = r.dynamic_tier ? ` · Dynamic Tier` : "";
  const routeSubline = isSurfaceReshaping
    ? `No high-identity template (FR < 65%) · Context voting applied`
    : `${r.human_vh3_germline || ""}${frIdStr}${dynamicTierStr}`;
  const routeBadgeHtml = `
    <div style="background:#1a2332;border:1px solid #2d3f55;border-radius:6px;padding:8px 14px;margin-bottom:10px;font-size:12px">
      <span style="color:${routeInfo.color};font-weight:700">${routeInfo.name}</span>
      <span style="margin-left:8px;background:${routeInfo.color};color:#fff;font-size:10px;padding:1px 7px;border-radius:3px">${routeInfo.badge}</span>
      <span style="color:#94a3b8;font-size:11px;margin-left:8px">${escapeHtml(routeSubline)}</span>
    </div>`;

  // ── Sequence cleaning banner ─────────────────────────────────────────────────
  const sc = r.sequence_cleaning;
  const scBanner = sc && sc.was_modified ? (() => {
    const removed = (sc.removed || []).map(x =>
      `<span style="font-family:monospace;font-size:11px;background:#bae6fd;color:#0c4a6e;padding:1px 6px;border-radius:3px;margin-right:4px">${escapeHtml(x.tag)} (${x.position}, ${x.length}aa)</span>`
    ).join("");
    const orig = (sc.original_sequence || "").length;
    const clean = (sc.cleaned_sequence || "").length;
    return `
    <section class="result-panel" style="border-left:4px solid #0ea5e9;padding:6px 14px;margin-bottom:4px">
      <div style="font-size:12px;font-weight:600;color:#38bdf8;margin-bottom:4px">Sequence Auto-Cleaned: ${orig} aa → ${clean} aa</div>
      <div style="font-size:11px;color:#cbd5e1">Removed: ${removed}</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:3px">Humanization performed on cleaned sequence. Original preserved in FASTA output.</div>
    </section>`;
  })() : "";

  // ── AbNatiV naturalness helpers ──────────────────────────────────────────────
  const abn = r.abnativ_naturalness || {};
  const dvh2  = abn.delta_vh2;
  const dvhh2 = abn.delta_vhh2;
  const dvh2Tone  = dvh2  == null ? "" : dvh2  >= 0.05 ? "ok" : dvh2  >= 0.0 ? "warn" : "fail";
  const dvhh2Tone = dvhh2 == null ? "" : dvhh2 >= -0.15 ? "ok" : dvhh2 >= -0.25 ? "warn" : "fail";
  const dvh2Val   = dvh2  != null ? (dvh2  >= 0 ? "+" : "") + fmt(dvh2,  3) : (abn.error ? "—" : "pending");
  const dvhh2Val  = dvhh2 != null ? (dvhh2 >= 0 ? "+" : "") + fmt(dvhh2, 3) : (abn.error ? "—" : "pending");
  const hum_vh2   = (abn.humanized || {}).vh2  != null ? fmt((abn.humanized || {}).vh2,  3) : "—";
  const hum_vhh2  = (abn.humanized || {}).vhh2 != null ? fmt((abn.humanized || {}).vhh2, 3) : "—";

  // ── HPR helpers ──────────────────────────────────────────────────────────────
  const hpr = r.hpr_index || {};
  // VHH HPR: score lives at hpr.humanized.vh.score (single-chain, VH model)
  const _hprHumVh  = (hpr.humanized || {}).vh  || {};
  const _hprDonVh  = (hpr.donor    || {}).vh   || {};
  const hprHumScore = parseFloat(_hprHumVh.score != null ? _hprHumVh.score : 0);
  const hprHum = _hprHumVh.score != null ? fmt(_hprHumVh.score, 3) : "—";
  const hprDon = _hprDonVh.score != null ? fmt(_hprDonVh.score, 3) : "—";
  const hprDelta = (hpr.delta || {}).vhh;
  const hprDeltaVal  = hprDelta != null ? (hprDelta >= 0 ? "+" : "") + fmt(hprDelta, 3) : "—";
  const hprTone      = hprHum === "—" ? "" : hprHumScore >= 0.80 ? "ok" : hprHumScore >= 0.70 ? "warn" : "fail";
  const hprDeltaTone = hprDelta == null ? "" : hprDelta >= 0 ? "ok" : "warn";

  // ── miniCMC helpers ─────────────────────────────────────────────────────────
  const mc = r.mini_cmc || {};
  const mcFlags = mc.flags || [];
  const mcTone = mc.error ? "warn" : (mc.pass_cmc ? "ok" : "warn");
  const mcFlagHtml = mcFlags.length
    ? `<span style="color:var(--warn);font-size:11px">⚠ ${mcFlags.join(" · ")}</span>`
    : `<span style="color:var(--ok);font-size:11px">✓ Pass</span>`;
  const piTone  = mc.pI == null ? "" : mc.pI < 5.5 || mc.pI > 9.5 ? "fail" : mc.pI < 6.0 || mc.pI > 9.0 ? "warn" : "ok";
  const grvTone = mc.GRAVY == null ? "" : mc.GRAVY > 0.10 ? "fail" : mc.GRAVY > 0.05 ? "warn" : "ok";
  const iiTone  = mc.instability_index == null ? "" : mc.instability_index > 50 ? "fail" : mc.instability_index > 40 ? "warn" : "ok";
  const sapTone = mc.SAP_proxy == null ? "" : mc.SAP_proxy > 0.771 ? "fail" : mc.SAP_proxy > 0.714 ? "warn" : "ok";

  // ── PTM hotspots ─────────────────────────────────────────────────────────────
  const ptmCount = mc.hotspot_count || 0;
  const ptmHtml = ptmCount > 0
    ? `<span style="color:var(--warn);font-size:11px">⚠ ${ptmCount} PTM hotspot${ptmCount > 1 ? "s" : ""} (positions: ${(mc.hotspot_positions || []).join(", ")})</span>`
    : `<span style="color:var(--ok);font-size:11px">✓ No PTM hotspots detected</span>`;

  // ── Structure QC helpers ─────────────────────────────────────────────────────
  const plddt_h = r.humanized_plddt;
  const plddt_d = r.donor_plddt;
  const plddtTone = plddt_h == null ? "" : plddt_h < 65 ? "fail" : plddt_h < 75 ? "warn" : "ok";
  const cdrRmsd = r.cdr_rmsd || {};
  const rmsdKeys = Object.keys(cdrRmsd).filter(k => typeof cdrRmsd[k] === "number");
  const maxRmsd = rmsdKeys.length ? Math.max(...rmsdKeys.map(k => cdrRmsd[k])) : null;

  // ── Surface reshaping detail panel ──────────────────────────────────────────
  const srPanel = isSurfaceReshaping ? (() => {
    const fp = r.feasibility_prescreen || {};
    const fpReasons = (fp.reasons || []).map(s => `<li style="margin-bottom:3px">${escapeHtml(s)}</li>`).join("");
    const srMuts = (srData.mutations || []).filter(m => m.applied);
    const mutRows = srMuts.length
      ? srMuts.map(m => `<tr><td class="mono">${m.imgt_label}</td><td class="mono">${m.from_aa}→${m.to_aa}</td><td>${(m.sasa_pct||0).toFixed(0)}%</td></tr>`).join("")
      : `<tr><td colspan="3" class="muted">No framework mutations applied — SAP driven by protected CDR residues.</td></tr>`;
    const sapBefore = srData.sap_before != null ? srData.sap_before.toFixed(3) : "—";
    const sapAfter  = srData.sap_after  != null ? srData.sap_after.toFixed(3)  : "—";
    const sapAchievedBadge = srData.target_achieved
      ? `<span class="run-status ok" style="font-size:10px;margin-left:6px">Target achieved</span>`
      : `<span class="run-status warn" style="font-size:10px;margin-left:6px">CDR-driven SAP</span>`;
    return `
    <section class="result-panel" style="border-left:3px solid #d97706">
      <div class="result-title" style="color:#fbbf24"><strong>Repertoire-Guided Refinement Detail</strong></div>
      <div class="result-body">
        <div style="padding:8px 12px;background:#2a1e0a;border-left:3px solid #d97706;border-radius:0 6px 6px 0;font-size:12px;margin-bottom:10px">
          <b style="color:#fcd34d">Why context-based refinement was applied:</b>
          <ul style="margin:5px 0 0 14px;padding:0;color:#fef3c7">${fpReasons || "<li>No high-identity clinical template found.</li>"}</ul>
        </div>
        <div class="metric-grid">
          ${metricHtml("SAP Before", sapBefore, "warn", "Max-9mer hydrophobic patch score of donor sequence")}
          ${metricHtml("SAP After", `${sapAfter} ${sapAchievedBadge}`, srData.target_achieved ? "ok" : "warn", "SAP after context-guided FR substitutions")}
          ${metricHtml("FR Mutations", `${srData.positions_modified ?? 0}`, "", "Number of framework positions modified by refinement")}
          ${metricHtml("Coverage", srData.imgt_coverage || "—", "", "IMGT numbering coverage of the donor")}
        </div>
        <table class="kv-table" style="margin-top:8px">
          <thead><tr><th>IMGT Pos</th><th>Mutation</th><th>SASA%</th></tr></thead>
          <tbody>${mutRows}</tbody>
        </table>
      </div>
    </section>`;
  })() : "";

  setOutput(`
    ${formatRunMetadataHtml(service, data, [
      r.sequence_name ? `<tr><th>Sequence / project ID</th><td class="mono">${escapeHtml(String(r.sequence_name))}</td></tr>` : "",
      `<tr><th>Standard</th><td>VHH Humanization V5.0</td></tr>`,
    ].filter(Boolean))}
    ${scBanner}

    <!-- ══ SECTION 1: OUTPUT SEQUENCE ══ -->
    <section class="result-panel">
      <div class="result-title">
        <strong>Humanized sequences</strong>
        <span class="run-status ${badgeTone(r.checklist_status || "DONE")}">${statusLabel(r.checklist_status) || "DONE"}</span>
      </div>
      <div class="result-body">
        ${routeBadgeHtml}
        <div class="seq-box" style="margin-top:8px">
          <div class="label">Humanized VHH</div>
          <pre>${escapeHtml(r.humanized_sequence || "")}</pre>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:8px">
          Hallmark (37/44/45/47): <span style="font-family:monospace;color:#e2e8f0">${r.hallmark_37||"?"}/${r.hallmark_44||"?"}/${r.hallmark_45||"?"}/${r.hallmark_47||"?"}</span>
          <span style="margin-left:10px">${r.hallmarks_ok ? '<span style="color:var(--ok)">✓ Hallmark OK</span>' : '<span style="color:var(--warn)">⚠ Review hallmark</span>'}</span>
          <span style="margin-left:12px">CDR3: <b>${r.cdr3_length ?? "—"} aa</b>${(r.cdr3_length || 0) > 16 ? ' <span style="color:var(--warn)">⚠ long</span>' : ""}</span>
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:10px;line-height:1.5">
          <strong>Downstream modules</strong> (humanized VHH cached in this session for entry points below).<br/>
          <strong>AF2 Multimer:</strong> VHH + antigen ECD for complex modeling.<br/>
          <strong>VHH CMC:</strong> Developability, clinical reference benchmarking, liability scan — separate run; not bundled with humanization.
        </p>
        ${(() => {
          const arts = buildArtifacts(data, { htmlZipOnly: true });
          if (!arts.length) return "";
          const links = arts.map(a =>
            `<a class="btn${a.primary ? " primary" : ""}" href="${escapeHtml(a.url)}" ${a.download ? "download" : 'target="_blank"'}
              style="font-size:12px;padding:6px 14px;text-decoration:none;display:inline-block">${escapeHtml(a.label)}</a>`
          ).join("");
          return `<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center">
            <span class="panel-label" style="margin-right:4px">Downloads:</span>${links}</div>`;
        })()}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px;max-width:920px">
          <button type="button" class="btn offline-btn" onclick="goToAf2MultimerWithLastHumanization(true)">AF2 Multimer &amp; Complex</button>
          <button type="button" class="btn" style="border-color:var(--accent);color:var(--accent)" onclick="goToVhhCmcWithLastHumanization()">Go to VHH CMC Snapshot</button>
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaWithLastHumanization(true)">cDNA Optimization (VHH) →</button>
        </div>
      </div>
    </section>

    <!-- ══ SECTION 1b: FR/CDR SEQUENCE COMPARISON ══ -->
    ${(() => {
      const sc2 = r.sequence_comparison || {};
      let regions = sc2.regions || [];
      // donor_sequence comes from backend (new builds); fallback to saved input
      const donorSeq = r.donor_sequence || window.__vhhLastInputSeq || "";
      const humanSeq = r.humanized_sequence || "";
      if (!donorSeq || !humanSeq) return "";

      // ── JS-side IMGT boundary split for VHH (approximate, covers 110-130 aa) ──
      // Boundaries based on IMGT linear positions for typical VHH (no gaps assumed):
      // FR1: 1-26 (0-25), CDR1: 27-38 (26-37), FR2: 39-55 (38-54),
      // CDR2: 56-65 (55-64), FR3: 66-104 (65-103), CDR3: 105-117 (104-116), FR4: 118-end
      function splitImgtVhh(seq) {
        const s = (seq || "").toUpperCase();
        const len = s.length;
        // Estimate CDR3 end: FR4 is typically the last 10-12 residues (WGQG...TVSS)
        // Use sequence length to estimate: FR4 ~ last 11 aa
        const fr4start = Math.max(104, len - 11);
        const cdr3end  = fr4start;
        // CDR3 start: position 104 in IMGT or len-adjusted
        const cdr3start = Math.min(104, cdr3end - 4);  // at least 4 aa CDR3
        return [
          { region: "FR1",  seq: s.slice(0, 26),         is_cdr: false },
          { region: "CDR1", seq: s.slice(26, 38),        is_cdr: true  },
          { region: "FR2",  seq: s.slice(38, 55),        is_cdr: false },
          { region: "CDR2", seq: s.slice(55, 65),        is_cdr: true  },
          { region: "FR3",  seq: s.slice(65, cdr3start), is_cdr: false },
          { region: "CDR3", seq: s.slice(cdr3start, cdr3end), is_cdr: true },
          { region: "FR4",  seq: s.slice(cdr3end),       is_cdr: false },
        ];
      }

      // If backend sent regions, use those; otherwise split locally
      if (!regions.length) {
        const dParts = splitImgtVhh(donorSeq);
        const hParts = splitImgtVhh(humanSeq);
        regions = dParts.map((dp, i) => {
          const ds = dp.seq, hs = hParts[i].seq;
          const nMut = Math.min(ds.length, hs.length) - [...ds].filter((c,j) => c === hs[j]).length
                       + Math.abs(ds.length - hs.length);
          return { region: dp.region, donor_seq: ds, humanized_seq: hs,
                   is_cdr: dp.is_cdr, n_mutations: dp.is_cdr ? 0 : nMut,
                   identical: ds === hs };
        });
      }

      const totalFrMut = sc2.total_fr_mutations != null ? sc2.total_fr_mutations
        : regions.filter(r2 => !r2.is_cdr).reduce((s, r2) => s + (r2.n_mutations || 0), 0);

      // Build 4-column rows: Region | Donor | Humanized | Status
      const regionRows = regions.map(reg => {
        const isCdr = reg.is_cdr;
        const ds = reg.donor_seq || "";
        const hs = reg.humanized_seq || "";
        const maxLen = Math.max(ds.length, hs.length);

        let donorHtml = "", humHtml = "";
        for (let i = 0; i < maxLen; i++) {
          const da = ds[i] || "", ha = hs[i] || "";
          if (da === ha) {
            const ch = escapeHtml(da || ha);
            donorHtml += ch;
            humHtml   += ch;
          } else {
            donorHtml += `<b style="color:#c0392b">${escapeHtml(da||"·")}</b>`;
            humHtml   += `<b style="color:#16a34a">${escapeHtml(ha||"·")}</b>`;
          }
        }

        const nMut = reg.n_mutations || 0;
        const statusText = isCdr ? "CDR" : nMut === 0 ? "—" : `${nMut} change${nMut>1?"s":""}`;
        const statusColor = isCdr ? "#92400e" : nMut === 0 ? "#9ca3af" : "#15803d";
        const rowBg = isCdr ? "#fefce8" : "transparent";

        return `<tr style="border-bottom:1px solid #e5e7eb;background:${rowBg}">
          <td style="padding:5px 12px;font-size:12px;font-weight:700;color:#1e293b;white-space:nowrap">${reg.region}</td>
          <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">${donorHtml}</td>
          <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">${humHtml}</td>
          <td style="padding:5px 12px;font-size:11px;font-weight:600;color:${statusColor};text-align:center;white-space:nowrap">${statusText}</td>
        </tr>`;
      }).join("");

      return `
      <section class="result-panel">
        <div class="result-title">
          <strong>Sequence Comparison (FR / CDR)</strong>
          <span style="margin-left:10px;font-size:11px;color:#94a3b8">${totalFrMut} FR position${totalFrMut!==1?"s":""} changed · CDR preserved</span>
        </div>
        <div class="result-body" style="padding:0">
          <table style="width:100%;border-collapse:collapse;font-family:sans-serif">
            <thead>
              <tr style="background:#334155">
                <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left;width:60px">Region</th>
                <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left">Camelid donor</th>
                <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:left">Humanized VHH</th>
                <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#f1f5f9;text-align:center;width:100px">Status</th>
              </tr>
            </thead>
            <tbody>${regionRows}</tbody>
          </table>
          <p style="font-size:10px;color:#6b7280;padding:5px 12px;margin:0">
            <b style="color:#c0392b">Red</b> = donor residue replaced ·
            <b style="color:#16a34a">Green</b> = humanized substitution ·
            Yellow rows = CDR (not modified)
          </p>
        </div>
      </section>`;
    })()}

    <!-- ══ SECTION 2: NATURALNESS & COMPATIBILITY ══ -->
    <section class="result-panel">
      <div class="result-title"><strong>Naturalness &amp; Repertoire Compatibility</strong></div>
      <div class="result-body">
        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:6px">
          ${metricHtml("HPR Index", hprHum, hprTone, "Human Peptide Repertoire Compatibility Index (9-mer match). ≥0.80 = PASS, 0.70–0.80 = WARN, <0.70 = FAIL")}
          ${metricHtml("HPR Δ", hprDeltaVal, hprDeltaTone, "HPR change from donor to humanized. Positive = improved human repertoire compatibility")}
          ${metricHtml("AbNatiV VH Δ", dvh2Val, dvh2Tone, "Change in human VH naturalness score (donor → humanized). Positive = more human-VH-like. ≥+0.05 PASS, 0–+0.05 WARN, <0 FAIL")}
          ${metricHtml("AbNatiV VHH Δ", dvhh2Val, dvhh2Tone, "Change in VHH naturalness score (donor → humanized). Negative expected (acceptable loss of camelid character). ≥−0.15 PASS, −0.15–−0.25 WARN, <−0.25 FAIL")}
          ${metricHtml("VH2 Score (hum.)", hum_vh2, "", "Absolute AbNatiV VH2 score of humanized sequence (0–1, higher = more human-VH-like)")}
        </div>
        ${abn.error ? `<p style="font-size:11px;color:var(--warn);margin-top:4px">⚠ AbNatiV scoring: ${escapeHtml(abn.error)}</p>` : ""}
        ${hpr.error ? `<p style="font-size:11px;color:var(--warn);margin-top:4px">⚠ HPR scoring: ${escapeHtml(hpr.error)}</p>` : ""}
        <p style="font-size:11px;color:#64748b;margin-top:6px">
          HPR Index evaluates 9-mer peptide compatibility with human antibody repertoire.
          AbNatiV VH Δ &gt; 0 confirms framework humanization is effective.
          AbNatiV VHH Δ ≥ −0.15 confirms camelid single-domain character is preserved.
        </p>
      </div>
    </section>

    ${srPanel}
    ${(() => {
      const pgsr = r.post_graft_surface_reshaping;
      if (!pgsr || !pgsr.positions_modified) return "";
      const muts = (pgsr.mutations || []).filter(m => m.applied).map(m =>
        `<span style="font-family:monospace;font-size:11px;background:#1e3a5f;color:#bae6fd;padding:1px 5px;border-radius:3px;margin-right:3px">${escapeHtml(m.imgt_label)} ${m.from_aa}→${m.to_aa}</span>`
      ).join("");
      return `<section class="result-panel" style="border-left:3px solid #0891b2">
        <div class="result-title"><strong>Post-Graft Hydrophobic Patch Reduction</strong>
          <span class="run-status" style="background:#0891b2;font-size:10px">Applied</span></div>
        <div class="result-body">
          <div class="metric-grid">
            ${metricHtml("SAP Before", pgsr.sap_before != null ? pgsr.sap_before.toFixed(3) : "—", "warn", "Hydrophobic patch score before post-graft refinement")}
            ${metricHtml("SAP After", pgsr.sap_after != null ? pgsr.sap_after.toFixed(3) : "—", pgsr.target_achieved ? "ok" : "warn", "Hydrophobic patch score after refinement")}
            ${metricHtml("FR Mutations", pgsr.positions_modified, "", "Framework positions modified to reduce SAP")}
          </div>
          <div style="margin-top:8px;font-size:11px">${muts || "—"}</div>
        </div>
      </section>`;
    })()}

    <!-- ══ SECTION 3: MINI-CMC PHYSICOCHEMICAL ══ -->
    <section class="result-panel">
      <div class="result-title"><strong>Physicochemical Developability (mini-CMC)</strong><span style="margin-left:8px">${mcFlagHtml}</span></div>
      <div class="result-body">
        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:8px">
          ${metricHtml("pI", mc.pI != null ? String(mc.pI) : "—", piTone, "Isoelectric point. PASS: 6.0–9.0 | WARN: 5.5–6.0 or 9.0–9.5 | FAIL: <5.5 or >9.5")}
          ${metricHtml("GRAVY", mc.GRAVY != null ? String(mc.GRAVY) : "—", grvTone, "Grand Average of Hydropathicity. PASS: <−0.05 | WARN: −0.05–0.05 | FAIL: >0.10")}
          ${metricHtml("Instability", mc.instability_index != null ? String(mc.instability_index) : "—", iiTone, "Biopython Instability Index. PASS: <40 | WARN: 40–50 | FAIL: >50")}
          ${metricHtml("SAP Proxy", mc.SAP_proxy != null ? fmt(mc.SAP_proxy, 3) : "—", sapTone, "Max-9mer hydrophobic patch score. PASS: <0.714 | WARN: 0.714–0.771 | FAIL: >0.771")}
          ${metricHtml("Length", mc.length != null ? String(mc.length) + " aa" : "—", "", "Sequence length of humanized VHH")}
        </div>
        <div style="margin-top:4px">${ptmHtml}</div>
        ${mc.hotspot_count > 0 ? `<div style="font-size:11px;color:#94a3b8;margin-top:4px">PTM hotspots: deamidation (NG/NS/QG), oxidation (W/M/C), isomerization (DG/DP) motifs. For full CMC analysis use <strong>VHH CMC Snapshot</strong>.</div>` : ""}
      </div>
    </section>

    <!-- ══ SECTION 4: STRUCTURE QC ══ -->
    <section class="result-panel">
      <div class="result-title">
        <strong>Structure Quality Control</strong>
        ${r.structure_computed ? `<span class="run-status ok" style="font-size:10px;margin-left:8px">NanoBodyBuilder2</span>` : `<span class="run-status warn" style="font-size:10px;margin-left:8px">Not computed</span>`}
      </div>
      <div class="result-body">
        ${r.structure_computed ? `
        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:6px">
          ${metricHtml("pLDDT (donor)", plddt_d != null ? fmt(plddt_d, 1) : "—", "", "Donor VHH predicted LDDT confidence from NanoBodyBuilder2")}
          ${metricHtml("pLDDT (humanized)", plddt_h != null ? fmt(plddt_h, 1) : "—", plddtTone, "Humanized VHH pLDDT. ≥75 PASS | 65–75 WARN | <65 FAIL")}
          ${Object.entries(cdrRmsd).filter(([,v]) => typeof v === "number").map(([k, v]) => {
            const isH3 = k.includes("3") || k.toLowerCase().includes("cdr3");
            const rmTone = v > (isH3 ? 2.5 : 1.5) ? "fail" : v > (isH3 ? 1.5 : 1.0) ? "warn" : "ok";
            return metricHtml(`${k} Cα RMSD`, `${fmt(v, 2)} Å`, rmTone, `${k} backbone RMSD donor vs humanized. CDR3 threshold: ≤1.5 Å PASS, ≤2.5 Å WARN`);
          }).join("")}
        </div>
        <p style="font-size:11px;color:#64748b">CDR Cα RMSD after framework Kabsch alignment. Values &gt;2.0 Å (CDR1/2) or &gt;2.5 Å (CDR3) suggest conformation shift requiring wet-lab validation.</p>
        ` : `<p style="font-size:12px;color:#64748b">Structure not computed — run with Structure mode enabled or use AF2 Multimer for offline verification.</p>`}
      </div>
    </section>

    <!-- ══ METHOD & VERSION ══ -->
    <section class="result-panel">
      <div class="result-title"><strong>Method &amp; Version</strong></div>
      <div class="result-body">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:600px">
          <div>
            <div class="panel-label">Service</div>
            <div style="font-size:13px;font-weight:600;color:var(--text)">VHH Humanization</div>
          </div>
          <div>
            <div class="panel-label">Analysis Version</div>
            <div style="font-size:13px;font-weight:600;color:var(--text);font-family:monospace">${escapeHtml(r.analysis_version || data.analysis_version || "V5.0")}</div>
          </div>
          <div>
            <div class="panel-label">Standard</div>
            <div style="font-size:12px;color:var(--muted);font-family:monospace">VHH Humanization Design Standard V4.0 / V5.0 engine</div>
          </div>
          <div>
            <div class="panel-label">Route</div>
            <div style="font-size:12px;color:var(--muted);font-family:monospace">${escapeHtml(routeInfo.name || "—")}</div>
          </div>
          ${data.elapsed_sec ? `<div><div class="panel-label">Elapsed</div><div style="font-size:12px;color:var(--muted)">${data.elapsed_sec}s</div></div>` : ""}
          ${data.job_id ? `<div><div class="panel-label">Job ID</div><div style="font-size:12px;color:var(--muted);font-family:monospace">${escapeHtml(data.job_id)}</div></div>` : ""}
        </div>
      </div>
    </section>
  `);

  updateResultRail({
    status: r.checklist_status || "DONE",
    summaryTitle: `${service.label} completed`,
    summaryText: `${(DEMOS[demoId] || {}).label || demoId} · VHH Humanization V5.0 · ${routeInfo.name}`,
    metrics: [
      {label: "Route", value: routeInfo.badge, tone: routeTier === "tier3" ? "warn" : "ok"},
      {label: "HPR Index", value: hprHum, tone: hprTone},
      {label: "AbNatiV VH Δ", value: dvh2Val, tone: dvh2Tone},
      {label: "AbNatiV VHH Δ", value: dvhh2Val, tone: dvhh2Tone},
      {label: "mini-CMC", value: mc.pass_cmc ? "PASS" : (mc.error ? "—" : "WARN"), tone: mc.pass_cmc ? "ok" : "warn"},
      {label: "pLDDT", value: plddt_h != null ? fmt(plddt_h, 1) : "—", tone: plddtTone || ""},
      {label: "Hallmark", value: r.hallmarks_ok ? "OK" : "CHECK", tone: r.hallmarks_ok ? "ok" : "warn"},
    ],
    recommendation: isSurfaceReshaping
      ? (srData.target_achieved
          ? "Repertoire-guided refinement achieved SAP target. Proceed to CMC Snapshot for full developability assessment."
          : "SAP remains above target — CDR-driven hydrophobicity. Proceed to VHH CMC Snapshot for optimized FR mutation suggestions.")
      : (dvh2 != null && dvh2 < 0
          ? "AbNatiV VH Δ is negative — framework humanization did not improve VH naturalness. Review template selection."
          : r.hallmarks_ok
            ? "Proceed to VHH CMC Snapshot or AF2 Multimer for structure verification."
            : "Review hallmark positions before downstream development."),
    artifacts: buildArtifacts(data, { htmlZipOnly: true }),
    metadata: [
      {label: "Demo ID", value: demoId, mono: true},
      {label: "Job ID", value: data.job_id || "—", mono: true},
      {label: "Elapsed", value: data.elapsed_sec ? `${data.elapsed_sec}s` : "—"},
      {label: "Standard", value: "VHH Humanization V5.0", mono: true},
      {label: "Route", value: routeTier === "tier3" ? "repertoire_guided" : routeTier === "tier2" ? "structure_guided" : "sequence_based", mono: true},
    ],
  });
}

// ── VHH CMC ───────────────────────────────────────────────────────────────────
// Reuses the same AbortController + cancel mechanism as the IgG CMC runner.

let _vhhCmcAbortCtrl = null;
let _vhhCmcJobId = null;

async function cancelVhhCmc() {
  if (_vhhCmcAbortCtrl) { _vhhCmcAbortCtrl.abort(); _vhhCmcAbortCtrl = null; }
  const jobId = _vhhCmcJobId;
  if (jobId) {
    try { await apiFetch(apiJoin(`jobs/${jobId}/cancel`), { method: "POST" }); } catch (_) {}
    _vhhCmcJobId = null;
  }
  const cancelBtn = document.getElementById("vhh-cmc-cancel-btn");
  if (cancelBtn) cancelBtn.style.display = "none";
  const statusBox = document.getElementById("vhh-cmc-status");
  if (statusBox) statusBox.innerHTML = "";
  clearRunning();
  setOutput(`<div class="muted" style="padding:12px">VHH CMC cancelled.</div>`);
}

async function runVhhCmc(service) {
  // Clean slate
  if (_vhhCmcAbortCtrl && !_vhhCmcAbortCtrl.signal.aborted) _vhhCmcAbortCtrl.abort();
  _vhhCmcAbortCtrl = new AbortController();
  _vhhCmcJobId = null;

  const seq = normalizeSeq(document.getElementById("vhh-cmc-seq").value);
  const demoId = document.getElementById("vhh-cmc-demo").value;
  const errors = [validateSeq(seq, "VHH", 105, 145)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the sdAb sequence input.", artifacts:[], metadata:[]});
    return;
  }

  const cancelBtn = document.getElementById("vhh-cmc-cancel-btn");
  const statusBox = document.getElementById("vhh-cmc-status");

  function _showProgress(pct, label) {
    pct = Math.min(Math.max(pct || 0, 0), 99);
    if (statusBox) statusBox.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:3px">
        <span>${label}</span><span>${Math.round(pct)}%</span>
      </div>
      <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:var(--accent);transition:width .4s ease;border-radius:2px"></div>
      </div>`;
    setRunning(label);
  }
  function _clearProgress() {
    if (statusBox) statusBox.innerHTML = "";
    if (cancelBtn) cancelBtn.style.display = "none";
    clearRunning();
  }

  if (cancelBtn) cancelBtn.style.display = "inline-flex";
  _showProgress(5, "Starting VHH CMC assessment…");
  setOutput("");

  const origin = (document.getElementById("vhh-cmc-origin") || {}).value || "camelid_vhh";
  const phases = [
    {pct:20, label:"Numbering & physicochemical metrics…"},
    {pct:45, label:"VHH hallmark & FR2 hydrophobicity check…"},
    {pct:65, label:"AbNatiV2 naturalness scoring…"},
    {pct:80, label:"Percentile ranks vs VHH clinical panel…"},
    {pct:90, label:origin === "engineered_vh" ? "Comparison vs engineered VH reference…" : "SASA structure metrics (if requested)…"},
  ];
  let phaseIdx = 0;
  const phaseTimer = setInterval(() => {
    if (phaseIdx < phases.length) { _showProgress(phases[phaseIdx].pct, phases[phaseIdx].label); phaseIdx++; }
  }, 5000);

  try {
    const res = await apiFetch(apiJoin("cmc/vhh/async"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        vhh_sequence: seq,
          report_format: "html",
          sdab_origin: origin,
          run_structure: true,
          smart_cmc: !!(document.getElementById("vhh-cmc-smart-opt") && document.getElementById("vhh-cmc-smart-opt").checked),
        ...((document.getElementById("vhh-cmc-name") && document.getElementById("vhh-cmc-name").value.trim()) && {project_name: document.getElementById("vhh-cmc-name").value.trim()})
      }),
      signal: _vhhCmcAbortCtrl.signal,
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `Server error ${res.status}`); }
    const startData = await res.json();
    const jobId = startData.job_id;
    _vhhCmcJobId = jobId;

    let poll, pollCount = 0;
    while (pollCount < 200) {
      if (_vhhCmcAbortCtrl?.signal.aborted) break;
      await new Promise(r => setTimeout(r, 3000));
      pollCount++;
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`), {signal: _vhhCmcAbortCtrl?.signal});
      if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
      poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      const note = poll.progress_note || st;
      if (poll.progress) _showProgress(poll.progress, `VHH CMC — ${note}`);
      if (st === "done" || st === "failed" || st === "cancelled") break;
    }

    clearInterval(phaseTimer);
    _clearProgress();
    _vhhCmcJobId = null;
    if (!poll || poll.status === "failed") throw new Error(poll?.error || "Job failed");
    if (poll.status === "cancelled") { setOutput(`<div class="muted" style="padding:12px">VHH CMC cancelled.</div>`); return; }
    renderVhhCmcResult(poll, service, demoId);
  } catch (err) {
    clearInterval(phaseTimer);
    _clearProgress();
    _vhhCmcJobId = null;
    if (err.name === "AbortError") { setOutput(`<div class="muted" style="padding:12px">VHH CMC cancelled.</div>`); return; }
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"VHH CMC failed", summaryText:err.message, metrics:[], recommendation:"Inspect the returned error and rerun.", artifacts:[], metadata:[]});
  }
}

// Friendly label map for VHH percentile rank table
const _VHH_METRIC_LABELS = {
  pI: "Isoelectric point (pI)", GRAVY: "GRAVY (hydrophobicity)",
  instability_index: "Instability index", net_charge_pH7: "Net charge pH 7",
  hydro_patch_max9: "Hydrophobic patch (9-mer)", charge_patch_max7: "Charge patch (7-mer)",
  SAP_score: "SAP score", agg_motifs: "Aggregation motifs",
  hydro_cluster_count: "Hydrophobic clusters", glycosylation_sites: "Glycosylation sites (NXS/T)",
  deamidation_sites: "Deamidation sites (NG/NS)", isomerization_sites: "Isomerization sites (DG/DS)",
  oxidation_sites: "Oxidation-prone (M/W)", free_cys: "Free Cys (beyond conserved)",
  vhh_all_cdr_gravy: "Total CDR GRAVY",
};

// Reference ranges for VHH metrics (shown in card subtitle line)
const _VHH_REF_RANGES = {
  pI:                 "Isoelectric Point (pI): The pH at which the protein carries no net charge. Values outside the 5.5–8.5 range increase the risk of self-association and poor expression in physiological environments (ER pH 7.2).",
  GRAVY:              "Grand Average of Hydropathy (GRAVY): Measures overall sequence hydrophobicity. Positive values (>0) indicate a hydrophobic character associated with high aggregation risk and low solubility.",
  instability_index:  "Instability Index: A predictor of in vitro protein stability based on dipeptide composition. Values >40 suggest the protein may be unstable during manufacturing and storage.",
  net_charge_pH7:     "Net Charge at pH 7.0: The electrical charge of the molecule at physiological pH. Extreme charges can negatively impact tissue distribution, serum half-life, and formulation viscosity.",
  hydro_patch_max9:   "Hydrophobic Patch: The size of the largest contiguous hydrophobic region on the surface. Patches >8 are critical drivers of non-specific binding and accelerated aggregation.",
  charge_patch_max7:  "Charge Patch: Clusters of like-charged residues on the surface. Excessive patches can lead to high viscosity in formulations and rapid clearance from circulation.",
  SAP_score:          "Spatial Aggregation Propensity (SAP): A structure-based metric identifying exposed hydrophobic atom clusters. High scores (≥0.95) pinpoint hotspots likely to initiate aggregation.",
  SAP_sasa:           "SASA-based SAP: The most accurate assessment of surface hydrophobic exposure, combining sequence propensity with solvent-accessible surface area (requires structure).",
  agg_motifs:         "Aggregation Motifs: Specific sequence patterns known to promote protein association. Presence of multiple motifs increases the risk of irreversible aggregation during storage.",
  vhh_all_cdr_gravy:  "CDR Hydropathicity: Average hydrophobicity of the binding loops. Hydrophobic CDRs are often correlated with non-specific binding and poor developability.",
  hydro_cluster_count:"Hydrophobic Cluster Count: The number of independent hydrophobic regions on the surface. More clusters increase the probability of non-specific interactions.",
  abnativ_delta:      "AbNatiV2 Naturalness Delta (Δ): Measures the preference for the single-domain (VHH) vs. paired (VH) state. A positive delta indicates better suitability for autonomous secretion and stability.",
  cdr3_compactness:   "CDR3 Compactness: The spatial distance between CDR3 anchors. Extended loops (>6.5 Å) may require specific Hallmark mutations to maintain structural integrity.",
  psh:                "Surface Hydrophobic SASA (PSH): Total hydrophobic surface area exposed to solvent. High PSH values correlate with non-specific binding and low solubility.",
  ppc:                "Positive Charge Cluster (PPC): Identifies surface-exposed positive charge patches. May lead to high viscosity or non-specific membrane interactions.",
  pnc:                "Negative Charge Cluster (PNC): Identifies surface-exposed negative charge patches. Influences pI and charge complementarity with targets.",
  deamidation_sites:  "Deamidation (NG/NS/NT/NA): Potential sites for asparagine deamidation. Each site increases risk of charge heterogeneity and potency loss over shelf life.",
  isomerization_sites:"Isomerization (DG/DS/DT): Potential sites for aspartate isomerization. Produces isoAsp, which alters CDR conformation and can reduce binding affinity.",
  oxidation_sites:    "Oxidation (M/W): Methionine or tryptophan residues susceptible to oxidation. Increases during storage and can lead to loss of activity.",
  glycosylation_sites:"Glycosylation (NXS/T): N-linked glycosylation sequons. Variable glycosylation causes batch-to-batch heterogeneity and can impact immunogenicity.",
  free_cys:           "Free Cysteine: Unpaired cysteine residues (excluding conserved Cys21/94). May cause disulfide scrambling or covalent aggregation.",
};

// Rich VHH metric card: name + value + flag badge + percentile band + ref range note
function _vhhMetricCard(name, value, flag, pctBand, refNote) {
  const isNA = flag === "N/A" || flag === "ERROR" || flag === "NOT_RUN";
  const badgeBg = isNA ? "rgba(148,163,184,.45)" : flag === "FAIL" ? "var(--fail)" : flag === "WARN" ? "var(--warn)" : "var(--pass)";
  const valColor = isNA ? "var(--muted)" : flag === "FAIL" ? "var(--fail)" : flag === "WARN" ? "var(--warn)" : "var(--fg)";
  const borderColor = isNA ? "rgba(148,163,184,.18)" : flag === "FAIL" ? "rgba(239,68,68,.45)" : flag === "WARN" ? "rgba(245,158,11,.4)" : "rgba(148,163,184,.18)";
  const badgeLabel = isNA ? "N/A" : flag;
  const pctHtml = pctBand ? `<div style="font-size:9px;color:var(--muted);margin-top:3px;font-style:italic">${escapeHtml(pctBand)}</div>` : "";
  const tipText = [refNote, pctBand].filter(Boolean).join(" | ");
  const hasTip = !!tipText;
  const safeTip = hasTip
    ? String(tipText).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    : "";
  const badgeHtml = isNA
    ? `<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:rgba(148,163,184,.45);color:white;font-weight:700;flex-shrink:0">N/A</span>`
    : (flag && flag !== "PASS")
      ? `<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${badgeBg};color:white;font-weight:700;flex-shrink:0">${escapeHtml(flag)}</span>`
      : `<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:var(--pass);color:white;font-weight:700;flex-shrink:0">PASS</span>`;
  return `<div style="border:1px solid ${borderColor};border-radius:7px;padding:9px 11px;display:flex;flex-direction:column;background:rgba(0,0,0,.02)"
      ${hasTip ? `data-tip="${safeTip}" onmouseenter="showMetricTip(this)" onmouseleave="hideMetricTip()"` : ""}>
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:4px;margin-bottom:3px">
      <div style="font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;line-height:1.25">
        ${escapeHtml(name)}${hasTip ? ` <span style="font-size:10px;opacity:.72;cursor:help">?</span>` : ""}
      </div>
      ${badgeHtml}
    </div>
    <div style="font-size:18px;font-weight:700;color:${valColor};line-height:1">${value}</div>
    ${pctHtml}
  </div>`;
}

// Compact 3-column grid of rich VHH metric cards
function _vhhMetricCardGrid(m, flags, pctRanks, sapLabel, sapMode, resObj) {
  const _v = (key) => m[key] !== undefined && m[key] !== null ? fmt(m[key]) : "—";
  const _f = (key) => flags[key] || "PASS";
  const _p = (key) => pctRanks[key] || null;
  const sapKey = sapMode === "sasa_7mer" ? "SAP_sasa" : "SAP_score";
  
  // Extra metrics from root result
  const abDelta = resObj.abnativ_delta != null ? fmt(resObj.abnativ_delta, 3) : "—";
  const abTier  = resObj.abnativ_tier || "";
  // AbNatiV2 flag: when delta is null (computation error/not run) → show "N/A", not "PASS"
  const abFlag  = (resObj.abnativ_delta == null)
    ? "N/A"
    : (abTier === "FAIL" ? "FAIL" : abTier === "WARN" ? "WARN" : "PASS");
  const compactness = (resObj.structure_metrics && resObj.structure_metrics.cdr3_compactness_ca_dist != null) 
                      ? fmt(resObj.structure_metrics.cdr3_compactness_ca_dist, 2) + " Å" : "—";
  const compFlag = (resObj.structure_metrics && resObj.structure_metrics.cdr3_compactness_ca_dist > 6.5) ? "WARN" : "PASS";

    const sapVal = sapMode === "sasa_7mer" ? (resObj.structure_metrics && resObj.structure_metrics.sap_sasa != null ? resObj.structure_metrics.sap_sasa : m.SAP_score) : m.SAP_score;
    // 6 cards × 3-col = 2 fully-filled rows. SAP moved to Aggregation/Surface block below.
    const cards = [
      _vhhMetricCard("pI",                  _v("pI"),               _f("pI"),               _p("pI"),               _VHH_REF_RANGES.pI),
      _vhhMetricCard("GRAVY",               _v("GRAVY"),            _f("GRAVY"),            _p("GRAVY"),            _VHH_REF_RANGES.GRAVY),
      _vhhMetricCard("Instability Index",   _v("instability_index"),_f("instability_index"),_p("instability_index"),_VHH_REF_RANGES.instability_index),
      _vhhMetricCard("Net Charge pH 7",     _v("net_charge_pH7"),   _f("net_charge_pH7"),   _p("net_charge_pH7"),   _VHH_REF_RANGES.net_charge_pH7),
      _vhhMetricCard("Hydrophobic Patch 9", _v("hydro_patch_max9"), _f("hydro_patch_max9"), _p("hydro_patch_max9"), _VHH_REF_RANGES.hydro_patch_max9),
      _vhhMetricCard("Charge Patch 7",      _v("charge_patch_max7"),_f("charge_patch_max7"),_p("charge_patch_max7"),_VHH_REF_RANGES.charge_patch_max7),
    ];
    // Aggregation & Surface row (SAP always; PSH/PPC/PNC only when structure computed)
    const surfCards = [
      _vhhMetricCard(sapLabel,              fmt(sapVal),            _f("SAP_score"),        _p("SAP_score"),        _VHH_REF_RANGES[sapKey]),
    ];
    if (resObj.structure_metrics && resObj.structure_metrics.structure_computed) {
      const sm = resObj.structure_metrics;
      surfCards.push(
        _vhhMetricCard("PSH (hydrophobic SASA)",  sm.psh !== undefined ? fmt(sm.psh) : "—", flags.psh || "PASS", null, "Surface hydrophobic SASA"),
        _vhhMetricCard("PPC (pos-charge cluster)",sm.ppc !== undefined ? fmt(sm.ppc) : "—", flags.ppc || "PASS", null, "Max consecutive pos-charge"),
        _vhhMetricCard("PNC (neg-charge cluster)",sm.pnc !== undefined ? fmt(sm.pnc) : "—", flags.pnc || "PASS", null, "Max consecutive neg-charge"),
      );
    }
  return `
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;align-items:stretch">${cards.join("")}</div>
    <div style="margin-top:14px">
      <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Aggregation &amp; Surface</div>
      <div style="display:grid;grid-template-columns:repeat(${surfCards.length === 1 ? 3 : 4},minmax(0,1fr));gap:8px;align-items:stretch">${surfCards.join("")}${surfCards.length === 1 ? "<div></div><div></div>" : ""}</div>
    </div>`;
}

function renderVhhCmcResult(data, service, demoId) {
  _vhhOriginalResult = data.result || {};  // store for variant compare
  const resObj = data.result || {};
  const m = resObj.metrics || {};
  const flags = resObj.risk_flags || {};
  const vhhSpec = resObj.vhh_specific || {};
  const structM = resObj.structure_metrics || {};
  const isEngVH = (resObj.sdab_origin || "").toLowerCase().replace(/-/g,"_") === "engineered_vh";
  const engAdapt = resObj.engvh_adaptation || null;      // L18S/F68Y check
  const a24Sim   = resObj.atlas24_similarity   || null;  // engineered VH similarity score
  const frSuggs  = resObj.fr_modification_suggestions || [];
  const smartRun = resObj.smart_cmc_run || false;

  const _flagTone = (f) => f === "FAIL" ? "fail" : f === "WARN" ? "warn" : "ok";
  const _flagBadge = (key) => {
    const f = flags[key];
    if (!f || f === "PASS") return "";
    return ` <span style="font-size:9px;padding:1px 4px;border-radius:3px;background:${f==="FAIL"?"var(--fail)":"var(--warn)"};color:white">${f}</span>`;
  };
  const _naTag = `<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:rgba(148,163,184,.25);color:var(--muted)">N/A</span>`;

  const pctRows = Object.entries(resObj.percentile_ranks || {}).map(([k, v]) =>
    `<tr><th>${_VHH_METRIC_LABELS[k] || k}</th><td>${v}</td></tr>`
  ).join("");
  const scoreDisplayName = resObj.score_display_name || "VHH/sdAb Gate Score";
  const scoreMethod = resObj.score_method || "PASS/WARN/FAIL gate-discrete 4-category weighted score";
  const scoreNote = resObj.score_comparability_note || "Not directly comparable with regular IgG ADI";
  const adiScore = resObj.adi_score ?? null;
  const adiPct = resObj.adi_percentile || null;
  const refPanelLabel = safeSdabReferenceLabel(resObj.sdab_origin || "camelid_vhh");
  const originDisplayLabel = safeSdabOriginLabel(resObj.sdab_origin || "camelid_vhh");
  const adiPctLabel = adiPct !== null ? `Top ${100 - Math.round(adiPct)}% of ${refPanelLabel}` : "—";

  const jobIdStr = (data.job_id || "").toString();
  const nameStr = (resObj.name && String(resObj.name).trim()) || "";
  const vhhCmcSeqRow = nameStr && nameStr !== jobIdStr && nameStr.toLowerCase() !== "demo"
    ? `<tr><th>Sequence / project ID</th><td class="mono">${escapeHtml(nameStr)}</td></tr>` : "";

  // ── Benchmark banner (adapts for engVH vs camelid VHH)
  const bannerColor = isEngVH ? "rgba(251,191,36,.35)" : "rgba(167,139,250,.35)";
  const bannerBg    = isEngVH ? "rgba(251,191,36,.05)"  : "rgba(167,139,250,.05)";
  const bannerLabel = isEngVH
    ? `<strong style="color:#d97706">Engineered VH / HCAb Reference</strong>`
    : `<strong style="color:var(--credit)">VHH Clinical Benchmark</strong>`;
  const bannerSubtitle = isEngVH
    ? "Gene-engineered VH-derived sdAb / HCAb reference context (not labeled as approved engineered-VH therapeutics)"
    : "VHH/sdAb clinical reference context; Gate Score is source-matched and not the regular IgG ADI scale";
  const vhh42Banner = `
    <div class="result-panel" style="border-color:${bannerColor}">
      <div class="result-title" style="background:${bannerBg}">
        ${bannerLabel}
        <span class="run-status ${badgeTone(resObj.overall_status || "DONE")}">${resObj.overall_status || "DONE"}</span>
      </div>
      <div class="result-body">
        <div style="font-size:11px;color:var(--muted);margin-bottom:12px">${bannerSubtitle}</div>
        <div class="clinical-rank ${(adiScore || 0) >= 60 ? "" : "warn-rank"}">
          <div>
            <div class="clinical-score-val" style="color:${(adiScore || 0) >= 60 ? "var(--pass)" : "var(--warn)"}">${adiScore !== null ? adiScore.toFixed(1) : "—"}</div>
            <div class="clinical-score-label">${escapeHtml(scoreDisplayName)} / 100</div>
          </div>
          <div>
            <div class="clinical-pct">${resObj.adi_grade || "—"}</div>
            <div style="font-size:11px;color:var(--muted);margin-top:3px">${adiPctLabel}</div>
          </div>
        </div>
        <div style="font-size:10px;color:var(--muted);margin-top:9px">${escapeHtml(scoreMethod)}. ${escapeHtml(scoreNote)}.</div>
      </div>
    </div>`;

  const sapMode = m.SAP_mode || "sequence_proxy_7mer";
  const sapLabel = sapMode === "sasa_7mer" ? "SAP (SASA)" : "SAP (seq proxy)";
  const sapNote = sapMode === "sasa_7mer"
    ? "SASA-based (NanoBodyBuilder2) — most accurate"
    : "Sequence proxy — enable structure prediction for SASA-based SAP";

  const _abPack = (resObj.abnativ || resObj.abnativ_scores || resObj.naturalness || {});
  const _pickNum = (...vals) => {
    for (const v of vals) {
      if (v !== null && v !== undefined && !Number.isNaN(Number(v))) return Number(v);
    }
    return null;
  };
  const abnativDelta = _pickNum(
    resObj.abnativ_delta,
    _abPack.delta,
    _abPack.abnativ_delta,
    _abPack.vhh_minus_vh,
  );
  const abnativTier  = resObj.abnativ_tier || "";
  const abnativHtml  = abnativDelta !== null && abnativDelta !== undefined
    ? `<strong>${abnativDelta.toFixed(3)}</strong> <span class="muted">(${abnativTier})</span>`
    : `<span class="muted">Not computed — AbNatiV2 warm-up needed (~60s first run).</span>`;
  const hprScore = _pickNum(resObj.hpr_score, ((resObj.hpr_index || {}).combined || {}).score);
  const abnativVh2 = _pickNum(
    resObj.abnativ_vh2_score,
    resObj.abnativ_vh2,
    _abPack.vh2_score,
    _abPack.abnativ_vh2_score,
    _abPack.vh2,
  );
  const abnativVhh2 = _pickNum(
    resObj.abnativ_vhh2_score,
    resObj.abnativ_vhh2,
    _abPack.vhh2_score,
    _abPack.abnativ_vhh2_score,
    _abPack.vhh2,
  );
  const VHH68_VHH2_P25 = 0.6936;
  const VHH68_VHH2_P75 = 0.8009;
  const VHH68_VHH2_P95 = 0.8503;
  const _originNorm = String(resObj.sdab_origin || "").toLowerCase().replace(/-/g, "_");
  const _isVhLikeSdAb = ["engineered_vh", "transgenic_sdab", "transgenic"].includes(_originNorm);
  const _humFmt = (v, d = 3) => (v === null || v === undefined ? "—" : Number(v).toFixed(d));
  const _abDeltaFlag = abnativDelta == null
    ? "N/A"
    : (_isVhLikeSdAb
      ? (abnativDelta > 0.3 ? "WARN" : "PASS")
      : (abnativDelta >= 0 ? "PASS" : (abnativDelta >= -0.05 ? "WARN" : "FAIL")));
  const _abVhh2Flag = abnativVhh2 == null
    ? "N/A"
    : (abnativVhh2 < VHH68_VHH2_P25 ? "WARN" : "PASS");
  const _hprFlag = hprScore == null
    ? "N/A"
    : (hprScore >= 0.80 ? "PASS" : (hprScore >= 0.65 ? "MONITOR" : "WARN"));

  const cdr3Compact = structM.cdr3_compactness_ca_dist ?? null;
  const plddt = structM.plddt ?? null;
  const fr2Tetrad   = vhhSpec.fr2_hallmark_tetrad || "—";
  const fr2Flag     = vhhSpec.fr2_hallmark_flag   || "NOT_RUN";
  const fr2Hydro    = vhhSpec.exposed_fr2_hydrophobicity;
  const fr2HydroFlag= vhhSpec.fr2_hydro_flag      || "NOT_RUN";
  const noncanCys   = vhhSpec.noncanonical_cys    ?? null;
    const nWarn = (resObj.n_warn ?? 0) + (vhhSpec.fr2_hallmark_flag === "WARN" ? 1 : 0) + (vhhSpec.noncanonical_cys_flag === "WARN" ? 1 : 0);
    const nFail = (resObj.n_fail ?? 0) + (vhhSpec.fr2_hallmark_flag === "FAIL" ? 1 : 0) + (vhhSpec.noncanonical_cys_flag === "FAIL" ? 1 : 0);
    const wfBadge = nFail > 0
    ? `<span style="color:var(--fail);font-weight:600">${nFail} FAIL · ${nWarn} WARN</span>`
    : nWarn > 0 ? `<span style="color:var(--warn);font-weight:600">${nWarn} WARN</span>`
    : `<span style="color:var(--pass)">All PASS</span>`;

  // ── Engineered VH Similarity Score section (engVH only)
  let a24Html = "";
  if (isEngVH && a24Sim) {
    const a24Score = a24Sim.score;
    const a24Band  = a24Sim.score_band || "";
    const bandColor = a24Band === "high" ? "var(--pass)" : a24Band === "medium" ? "var(--warn)" : "var(--fail)";
    const ev = a24Sim.evidence || {};
    const comps = a24Sim.components || {};
    const compRows = Object.entries(comps).map(([k, v]) =>
      `<tr><th style="font-weight:400">${k.replace(/_/g," ")}</th><td>${(v*100).toFixed(0)}%</td></tr>`
    ).join("");
    const a24Notes = (a24Sim.notes || []).map(n => `<div style="font-size:10px;color:var(--muted);margin-top:3px">• ${escapeHtml(n)}</div>`).join("");
    const a24Flags = (a24Sim.flags || []).length
      ? `<div style="font-size:10px;color:var(--warn);margin-top:4px">Liability flags: ${a24Sim.flags.join(", ")}</div>` : "";
    a24Html = `
    <section class="result-panel" style="border-color:rgba(251,191,36,.35)">
      <div class="result-title" style="background:rgba(251,191,36,.05)">
        <strong style="color:#d97706">Engineered VH Similarity Score</strong>
        <span style="font-size:11px;padding:2px 7px;border-radius:3px;background:${bandColor};color:white;font-weight:600">${a24Band.toUpperCase()}</span>
      </div>
      <div class="result-body">
        <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
          5-component similarity vs the approved engineered human autonomous VH reference cohort.
          Score ≥0.70 = inside clinical envelope.
        </div>
        <div style="display:flex;align-items:center;gap:20px;margin-bottom:12px">
          <div>
            <div style="font-size:28px;font-weight:700;color:${bandColor}">${(a24Score*100).toFixed(1)}%</div>
            <div style="font-size:11px;color:var(--muted)">Similarity score</div>
          </div>
          <div style="flex:1">
            <table class="kv-table" style="font-size:11px">${compRows}</table>
          </div>
        </div>
        ${ev.hallmark_motif ? `<div style="font-size:11px"><strong>Hallmark motif (37/44/45/47):</strong> <code>${escapeHtml(ev.hallmark_motif)}</code> — ${escapeHtml(ev.hallmark_label || "")}</div>` : ""}
        ${ev.stealth_departures ? `<div style="font-size:11px;margin-top:3px"><strong>Stealth departures:</strong> ${ev.stealth_departures.count} / 4 at positions [${(ev.stealth_departures.positions||[]).join(", ")||"none"}]</div>` : ""}
        ${ev.cdr3_seq ? `<div style="font-size:11px;margin-top:3px"><strong>CDR-H3:</strong> <code>${escapeHtml(ev.cdr3_seq)}</code> len=${ev.cdr3_len}, charge=${ev.cdr3_net_charge}, GRAVY=${ev.cdr3_gravy}</div>` : ""}
        ${a24Notes}${a24Flags}
      </div>
    </section>`;
  } else if (isEngVH) {
    a24Html = `<section class="result-panel"><div class="result-body"><div class="muted" style="font-size:11px">Engineered VH similarity score not computed (numbering failed or timed out).</div></div></section>`;
  }

  // ── sdAb Adaptation Sites section (engVH only)
  let adaptHtml = "";
  if (isEngVH && engAdapt) {
    const siteRows = (engAdapt.sites || []).map(s => {
      const statusColor = s.status === "ADAPTED" ? "var(--pass)" : s.status === "VH_CANONICAL" ? "var(--warn)" : "var(--muted)";
      const statusLabel = s.status === "ADAPTED" ? "✓ Adapted" : s.status === "VH_CANONICAL" ? "⚠ VH-canonical — recommend " + s.sdab_aa : s.found_aa === "?" ? "Unknown" : s.found_aa + " (other)";
      return `<tr>
        <th>${escapeHtml(s.label)}</th>
        <td><code>${escapeHtml(s.found_aa)}</code> <span style="font-size:10px;color:${statusColor}">${escapeHtml(statusLabel)}</span></td>
        <td style="font-size:10px;color:var(--muted)">${escapeHtml(s.function)}</td>
      </tr>`;
    }).join("");
    const adaptSummaryColor = engAdapt.missing === 0 ? "var(--pass)" : engAdapt.missing === 2 ? "var(--fail)" : "var(--warn)";
    adaptHtml = `
    <section class="result-panel" style="border-color:rgba(251,191,36,.35)">
      <div class="result-title" style="background:rgba(251,191,36,.05)"><strong style="color:#d97706">sdAb Adaptation Sites (V1.8 §2 Phase 4.5)</strong></div>
      <div class="result-body">
        <div style="font-size:11px;margin-bottom:8px;color:${adaptSummaryColor}">${escapeHtml(engAdapt.summary || "")}</div>
        <table class="kv-table" style="font-size:11px">
          <tr><th>Site</th><th>Found</th><th>Function</th></tr>
          ${siteRows}
        </table>
        <div style="font-size:10px;color:var(--muted);margin-top:6px">
          ${engAdapt.anarci_ok ? "✓ Kabat numbering via ANARCI" : "⚠ Kabat numbering used sequence-position heuristic (ANARCI unavailable)"}
        </div>
      </div>
    </section>`;
  }

  // ── VHH/EngVH-Specific Parameters section (adapts content for origin)
  const vhhSpecTitle = isEngVH
    ? "Single-Domain Parameters (EngVH / HCAb — no camelid hallmark)"
    : "VHH-Specific Parameters &amp; Naturalness";
  const fr2HallmarkRow = isEngVH
    ? `<tr><th>FR2 residues (37/44/45/47)</th>
        <td><span style="font-family:monospace;font-size:13px">${escapeHtml(fr2Tetrad)}</span>
        &nbsp;${_naTag}&nbsp;<span style="font-size:10px;color:var(--muted)">VH-type FR2 retained — expected for autonomous VH</span></td></tr>`
    : `<tr><th>FR2 Hallmark tetrad (37/44/45/47)</th>
        <td><span style="font-family:monospace;font-size:13px">${escapeHtml(fr2Tetrad)}</span>
        ${fr2Flag !== "NOT_RUN" ? `<span style="margin-left:6px;font-size:10px;padding:1px 4px;border-radius:3px;background:${fr2Flag==="PASS"?"var(--pass)":"var(--warn)"};color:white">${fr2Flag}</span>` : ""}</td></tr>`;
  const fr2HydroRow = isEngVH
    ? `<tr><th>FR2 hydrophobicity (Parker)</th>
        <td>${fr2Hydro !== null && fr2Hydro !== undefined ? fr2Hydro.toFixed(3) : "—"}
        &nbsp;${_naTag}&nbsp;<span style="font-size:10px;color:var(--muted)">Hydrophobic VH-type FR2 interface — not penalized for autonomous VH</span></td></tr>`
    : `<tr><th>Exposed FR2 hydrophobicity (Parker)</th>
        <td>${fr2Hydro !== null && fr2Hydro !== undefined ? fr2Hydro.toFixed(3) : "—"}
        ${fr2HydroFlag !== "NOT_RUN" ? `<span style="margin-left:6px;font-size:10px;padding:1px 4px;border-radius:3px;background:${fr2HydroFlag==="PASS"?"var(--pass)":fr2HydroFlag==="WARN"?"var(--warn)":"var(--fail)"};color:white">${fr2HydroFlag}</span>` : ""}
        <span style="font-size:10px;color:var(--muted)">&nbsp;reference p25–p75: −1.15 to −0.46</span></td></tr>`;

  setOutput(`
    ${formatRunMetadataHtml(service, data, [
      vhhCmcSeqRow,
      `<tr><th>Reference panel</th><td>${escapeHtml(refPanelLabel)}</td></tr>`,
      `<tr><th>Origin</th><td>${escapeHtml(originDisplayLabel)}${isEngVH ? " &nbsp;<span style='font-size:10px;background:#d97706;color:white;padding:1px 4px;border-radius:3px'>EngVH mode</span>" : ""}</td></tr>`,
      `<tr><th>Flag summary</th><td>${wfBadge}</td></tr>`,
    ].filter(Boolean))}
    ${vhh42Banner}
    ${a24Html}
    ${adaptHtml}

    <section class="result-panel">
      <div class="result-title"><strong>Physicochemical Profile</strong>
        <span style="font-size:10px;color:var(--muted)">Value · Flag · Percentile · Reference range</span>
      </div>
      <div class="result-body">
        ${_vhhMetricCardGrid(m, flags, resObj.percentile_ranks || {}, sapLabel, sapMode, resObj)}
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title"><strong>CDR Fingerprint</strong></div>
      <div class="result-body">
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;align-items:stretch">
          ${_vhhMetricCard("CDR3 Length", String(m.vhh_cdr3_len ?? "—"), "PASS", null, "IMGT definition")}
          ${_vhhMetricCard("CDR3 Compactness (Å)", cdr3Compact == null ? "—" : _humFmt(cdr3Compact, 2), cdr3Compact == null ? "N/A" : (cdr3Compact <= 6.5 ? "PASS" : (cdr3Compact <= 7.5 ? "WARN" : "FAIL")), null, "Structure-derived CDR3 compactness. <=6.5 PASS; 6.5-7.5 WARN; >7.5 FAIL.")}
          ${_vhhMetricCard("CDR3 GRAVY", String(m.vhh_cdr3_gravy ?? "—"), "PASS", null, "Hydrophobicity index")}
          ${_vhhMetricCard("CDR3 Net Charge", String(m.vhh_cdr3_net_charge ?? "—"), "PASS", null, "Net charge at pH 7")}
          ${_vhhMetricCard("CDR3 Arom Density", String(m.vhh_cdr3_arom_density ?? "—"), "PASS", null, "W/F/Y fraction")}
          ${_vhhMetricCard("Total CDR GRAVY", String(m.vhh_all_cdr_gravy ?? "—"), "PASS", null, "Combined CDR load")}
        </div>
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title"><strong>Chemical Liabilities (PTM)</strong></div>
      <div class="result-body">
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;align-items:stretch">
          ${_vhhMetricCard("Aggregation Motifs", String(m.agg_motifs ?? "—"), flags.agg_motifs || "PASS", null, "0 preferred")}
          ${_vhhMetricCard("Oxidation (M/W)",    String(m.oxidation_sites ?? "—"), flags.oxidation_sites || "PASS", null, "Exposed Met/Trp")}
          ${_vhhMetricCard("Deamidation (NG/NS)", String(m.deamidation_sites ?? "—"), flags.deamidation_sites || "PASS", null, "NG/NS motif count")}
          ${_vhhMetricCard("Isomerization (DG/DS)", String(m.isomerization_sites ?? "—"), flags.isomerization_sites || "PASS", null, "DG/DS motif count")}
          ${_vhhMetricCard("Glycosylation (NXS/T)", String(m.glycosylation_sites ?? "—"), flags.glycosylation_sites || "PASS", null, "N-glyc sequon count")}
          ${_vhhMetricCard("Free Cys", String(m.free_cys ?? "—"), flags.free_cys || "PASS", null, "Unpaired Cys (excl. conserved 21/94)")}
        </div>
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title"><strong>Humanness (single-domain profile)</strong></div>
      <div class="result-body">
        <div style="font-size:10px;color:var(--muted);margin-bottom:8px;font-style:italic">
          Source-aware interpretation: VHH/camelid prefers positive Δ(VHH2−VH2); autonomous VH/HCAb can be VH-like with negative Δ.
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:10px">
          ${_vhhMetricCard("AbNatiV2 Δ (VHH2−VH2)", _humFmt(abnativDelta, 3), _abDeltaFlag, null,
            _isVhLikeSdAb
              ? "Autonomous VH/HCAb mode: negative Δ is acceptable; WARN only when unexpectedly VHH-biased (>0.30)."
              : "Camelid/VHH mode: Δ>=0 preferred; strongly negative values indicate VH-biased profile.")}
          ${_vhhMetricCard("AbNatiV VH2", _humFmt(abnativVh2, 4), abnativVh2 == null ? "N/A" : "PASS", null,
            "Reference context metric (conventional VH model). Lower values indicate more VHH-like shift.")}
          ${_vhhMetricCard("AbNatiV VHH2", _humFmt(abnativVhh2, 4), _abVhh2Flag, null,
            `Internal VHH benchmark anchor: p25=${VHH68_VHH2_P25}, p75=${VHH68_VHH2_P75}, p95=${VHH68_VHH2_P95}.`)}
          ${_vhhMetricCard("HPR Index", _humFmt(hprScore, 3), _hprFlag, null,
            "Human peptide repertoire compatibility (9-mer, single-chain). VHH single-chain anchor: >=0.80 PASS; 0.65-0.80 MONITOR; <0.65 WARN. Note: single-chain VHH expected lower than VH+VL combined.")}
        </div>
        ${(abnativDelta == null && abnativVh2 == null && abnativVhh2 == null)
          ? `<div style="font-size:10px;color:var(--warn);margin-top:2px">
              AbNatiV metrics were not returned by backend for this run${resObj.abnativ_error ? `: ${escapeHtml(String(resObj.abnativ_error))}` : " (often first-run warm-up or tool timeout)"}.
            </div>`
          : ""}
        <div style="font-size:10px;color:var(--muted);margin-top:2px">
          Origin context: <strong>${escapeHtml(safeSdabOriginLabel(resObj.sdab_origin || "camelid_vhh"))}</strong>
        </div>
      </div>
    </section>

        <details style="margin-top:10px">
          <summary style="font-size:11px;color:var(--muted);cursor:pointer">Full percentile table vs ${escapeHtml(refPanelLabel)}</summary>
          <table class="kv-table" style="font-size:11px;margin-top:6px">
            <tr><th>Metric</th><th>Value</th><th>Percentile Band</th></tr>
            ${Object.entries(resObj.percentile_ranks || {}).map(([k, v]) => {
              const rawVal = m[k] !== undefined && m[k] !== null ? fmt(m[k]) : "—";
              return `<tr><td>${_VHH_METRIC_LABELS[k] || k}</td><td style="font-weight:600;font-family:monospace">${rawVal}</td><td>${v}</td></tr>`;
            }).join("") || "<tr><td colspan='3' class='muted'>No percentile ranks returned.</td></tr>"}
          </table>
        </details>
      </div>
    </section>

    ${_renderVhhFrSuggestions(frSuggs, smartRun, isEngVH, {
      seq: resObj.sequence || "",
      origin: resObj.sdab_origin || "camelid_vhh",
      noFrReason: resObj.no_fr_reason || "",
      baseMetrics: {
        pI: m.pI, GRAVY: m.GRAVY, instability_index: m.instability_index,
        SAP_score: m.SAP_score, ADI: resObj.adi_score, adi_grade: resObj.adi_grade,
      },
    })}

    <section class="result-panel" style="border-color:rgba(34,211,238,.25)">
      <div class="result-title" style="background:rgba(34,211,238,.05)">
        <strong style="color:#22d3ee">Downstream: cDNA Optimization</strong>
        <span style="font-size:11px;color:var(--muted)">Carry assessed VHH directly to cDNA assembly</span>
      </div>
      <div class="result-body">
        <p style="font-size:11px;color:var(--muted);margin:0 0 10px">
          Assemble VHH construct (signal peptide + optional fusion tag) and codon-optimize for HEK293 / CHO / E. coli using the sequence evaluated above.
        </p>
        <div class="button-row">
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaFromCmcVhh()">cDNA Optimization (VHH) →</button>
        </div>
      </div>
    </section>
  `);
  // Stash VHH CMC input sequence for downstream cDNA routing
  window._lastCmcInputVhh  = (resObj.sequence || "").trim();
  window._lastCmcInputName = (nameStr || "").trim();

  const railA24 = (isEngVH && a24Sim)
    ? {label: "EngVH Sim", value: `${(a24Sim.score*100).toFixed(0)}% (${a24Sim.score_band})`, tone: a24Sim.score_band === "high" ? "ok" : a24Sim.score_band === "medium" ? "warn" : "fail"}
    : null;
  const railAdapt = (isEngVH && engAdapt)
    ? {label: "sdAb Adaptation", value: `${engAdapt.adapted}/2 sites`, tone: engAdapt.missing === 0 ? "ok" : "warn"}
    : null;
  const railExtras = [railA24, railAdapt].filter(Boolean);

  updateResultRail({
    status: resObj.overall_status || "DONE",
    summaryTitle: `VHH CMC completed${isEngVH ? " [EngVH mode]" : ""}`,
    summaryText: `${(DEMOS[demoId] || {}).label || demoId} assessed against ${refPanelLabel}.`,
    refDb: refPanelLabel,
    clinicalRank: adiPctLabel,
    metrics: [
      {label: "Gate Score", value: adiScore !== null ? adiScore.toFixed(1) : "—", tone: adiTone(adiScore)},
      {label: "Grade", value: resObj.adi_grade || "—", tone: adiTone(adiScore)},
      {label: "pI", value: m.pI !== undefined ? fmt(m.pI) : "—", tone: _flagTone(flags.pI)},
      {label: "GRAVY", value: m.GRAVY !== undefined ? fmt(m.GRAVY) : "—", tone: _flagTone(flags.GRAVY)},
      {label: "SAP", value: m.SAP_score !== undefined ? fmt(m.SAP_score) : "—", tone: _flagTone(flags.SAP_score)},
      {label: nFail > 0 ? "FAIL flags" : "WARN flags", value: nFail > 0 ? nFail : nWarn, tone: nFail > 0 ? "fail" : nWarn > 0 ? "warn" : "ok"},
      ...railExtras,
    ],
    recommendation: (adiScore || 0) >= 60
      ? `Developability profile acceptable vs ${refPanelLabel}.${isEngVH && engAdapt && engAdapt.missing > 0 ? " sdAb adaptation site(s) absent — FR engineering recommended." : ""}`
      : `Gate Score below preferred range; inspect liabilities and percentile context.${isEngVH && engAdapt && engAdapt.missing > 0 ? " Apply missing sdAb adaptation mutations (see EngVH section)." : ""}`,
    artifacts: buildArtifacts(data),
    metadata: [
      {label: "Reference", value: refPanelLabel},
      {label: "Origin", value: resObj.sdab_origin || "—"},
      {label: "Job ID", value: data.job_id || "—", mono: true},
      {label: "Elapsed", value: data.elapsed_sec ? `${data.elapsed_sec}s` : "—"},
      {label: "Analysis Version", value: service.analysisVersion, mono: true},
    ],
  });
}

// ── VHH Smart-CMC suggestions renderer ───────────────────────────────────────

function _renderVhhFrSuggestions(suggs, smartRun, isEngVH, opts = {}) {
  const isBsArm = !!opts.armLabel;
  if (!isBsArm) _vhhSuggRegistry = [];   // reset registry on each single-VHH render

  // Always render panel so user knows Smart-CMC status
  if (!smartRun) {
    return `<section class="result-panel" style="border-color:rgba(148,163,184,.4)">
      <div class="result-title" style="background:rgba(148,163,184,.05)"><strong style="color:var(--muted)">Smart-CMC: FR Suggestions</strong></div>
      <div class="result-body"><div style="color:var(--muted);font-size:12px">
        Smart-CMC optimization was not enabled for this run. No mutation recommendation or variant re-evaluation is shown.
      </div></div>
    </section>`;
  }

  const _CAT_LABELS = {
    hydrophobic:    "Hydrophobic Patch",
    charge:         "Charge Patch",
    pI:             "pI Tuning",
    stability:      "Stability",
    sdab_adaptation:"sdAb Adaptation",
    engvh_stealth:  "EngVH Stealth",
  };
  const _PRIO_COLORS = {HIGH: "var(--fail)", MEDIUM: "var(--warn)", LOW: "var(--pass)"};
  const _PRIO_BG     = {HIGH: "rgba(239,68,68,.12)", MEDIUM: "rgba(245,158,11,.1)", LOW: "rgba(34,197,94,.08)"};

  const originNote = isEngVH
    ? "EngVH mode: sdAb adaptation sites (L18S/F68Y) are highest priority. Hallmark protection is off."
    : "VHH mode: Hallmark positions (Kabat 37/44/45/47) are protected.";

  if (!suggs || suggs.length === 0) {
    const noFrReason = opts.noFrReason || "";
    const reasonHtml = noFrReason ? `<div style="margin-top:8px;padding:8px;background:rgba(255,255,255,0.05);border-radius:4px;color:var(--muted);font-style:italic">Note: ${escapeHtml(noFrReason)}</div>` : "";
    return `<section class="result-panel" style="border-color:rgba(34,197,94,.4)">
      <div class="result-title" style="background:rgba(34,197,94,.06)"><strong style="color:var(--pass)">Smart-CMC: FR Suggestions</strong></div>
      <div class="result-body"><div style="color:var(--pass);font-size:12px;line-height:1.5">
        <strong>&#10003; No FR modifications recommended.</strong><br>
        Smart-CMC ran successfully — VHH/sdAb CMC gates, sequence liabilities, AbNatiV2/HPR context, and origin-specific FR checks are within the
        <em>${escapeHtml(isEngVH ? "engineered VH / HCAb" : "selected VHH/sdAb")}</em> reference context. No optimization or variant re-evaluation is required.
        ${reasonHtml}
      </div></div>
    </section>`;
  }

  // Group by category
  const byCategory = {};
  for (const s of suggs) {
    const cat = s.category || "other";
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(s);
  }

  const catSections = Object.entries(byCategory).map(([cat, items]) => {
    const catLabel = _CAT_LABELS[cat] || cat;
    const pills = items.map(s => {
      const pColor = _PRIO_COLORS[s.priority] || "var(--muted)";
      const pBg    = _PRIO_BG[s.priority]    || "rgba(148,163,184,.1)";
      const noteHtml = s.note ? `<div style="font-size:10px;color:var(--muted);margin-top:2px">${escapeHtml(s.note)}</div>` : "";
      // Use registry index instead of passing strings via onclick (avoids encoding issues with →, (), etc.)
      const registry = isBsArm ? _bsSuggRegistry : _vhhSuggRegistry;
      const regIdx = registry.length;
      registry.push({
        fromAA: s.found_aa,
        toAA: s.suggested_aa,
        linearPos: s.linear_pos,
        kabatPos: s.kabat_pos,
        catLabel,
        rationale: s.rationale || "",
        armLabel: opts.armLabel || "",
        armSeq: opts.armSeq || "",
      });
      const applyFn = isBsArm ? `applyBsSuggestion(${regIdx})` : `applyVhhSuggestion(${regIdx})`;
      return `<div style="background:${pBg};border:1px solid ${pColor};border-radius:6px;padding:7px 10px;margin-bottom:6px">
        <div style="display:flex;align-items:flex-start;gap:8px">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:7px;margin-bottom:4px">
              <span style="font-size:9px;font-weight:700;color:${pColor};padding:1px 5px;border:1px solid ${pColor};border-radius:3px;flex-shrink:0">${escapeHtml(s.priority)}</span>
              <code style="font-size:13px;font-weight:700">${escapeHtml(s.label || `${s.found_aa}${s.kabat_pos}${s.suggested_aa}`)}</code>
            </div>
            <div style="margin-bottom:4px">
              <span style="display:inline-block;font-size:10px;font-weight:700;background:#fef3c7;color:#92400e;border:1px solid #f59e0b;border-radius:3px;padding:1px 6px">Goal: ${escapeHtml(catLabel)}</span>
            </div>
            <div style="font-size:11px;color:var(--muted)">${s.rationale ? escapeHtml(s.rationale) : "<em>No rationale provided</em>"}</div>
            ${noteHtml}
          </div>
          <button type="button" style="flex-shrink:0;font-size:10px;padding:4px 10px;border-radius:4px;border:1px solid #6366f1;background:rgba(99,102,241,.1);color:#6366f1;cursor:pointer;font-weight:600;margin-top:2px"
            onclick="${applyFn}">Apply &amp; Verify</button>
        </div>
      </div>`;
    }).join("");
    return `<div style="margin-bottom:12px">
      <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">${escapeHtml(catLabel)}</div>
      ${pills}
    </div>`;
  }).join("");

  // ── Consolidated mutation map (chip cells, by category color) ──────────────
  const _CAT_COLORS = {
    hydrophobic:    "#0d9488",
    charge:         "#9333ea",
    pI:             "#9333ea",
    stability:      "#f59e0b",
    sdab_adaptation:"#0ea5e9",
    engvh_stealth:  "#d97706",
  };
  const allChips = suggs.map(s => {
    const cat = s.category || "other";
    const color = _CAT_COLORS[cat] || "#586e75";
    const label = `${s.found_aa}${s.kabat_pos}${s.suggested_aa}`;
    return `<span title="Goal: ${escapeHtml(_CAT_LABELS[cat]||cat)} — ${escapeHtml(s.rationale||'')}"
      style="font-family:monospace;font-size:11px;padding:3px 8px;background:${color}1a;border:1px solid ${color}55;color:${color};border-radius:3px;font-weight:600;white-space:nowrap">${escapeHtml(label)}</span>`;
  }).join(" ");

  // ── Unified selector context ──────────────────────────────────────────────
  const ctxKey = isBsArm ? `bs-${opts.armLabel}` : "vhh";

  // Stash VHH context for unified Smart-CMC selector
  const _vhhUnifiedBuckets = {charge: [], hydrophobic: [], stability: [], liability: []};
  const _vhhCatMap = {charge: "charge", hydrophobic: "hydrophobic", pI: "charge", stability: "stability", sdab_adaptation: "stability", engvh_stealth: "stability"};
  (suggs || []).forEach(s => {
    const tgt = _vhhCatMap[s.category] || "liability";
    _vhhUnifiedBuckets[tgt].push({
      chain: "VHH",
      pos: s.linear_pos != null ? s.linear_pos + 1 : null,  // convert to 1-indexed for _cmcApplyMutations
      kabat_pos: s.kabat_pos,
      from: s.found_aa,
      to: s.suggested_aa,
      region: `Kabat ${s.kabat_pos}`,
      target: s.rationale || s.label,
    });
  });
  window[`_cmcUnifiedCtx_${ctxKey}`] = {
    kind: "vhh",
    seq: opts.seq || "",
    buckets: _vhhUnifiedBuckets,
    baseMetrics: opts.baseMetrics || {},
    origin: opts.origin,
  };

  const _vhhSectionId = `smartcmc-vhh-section-${ctxKey}`;
  const _vhhToggleId = `smartcmc-vhh-toggle-${ctxKey}`;
  const consolidatedPanel = `
    <div style="margin-bottom:14px;padding:12px 14px;background:rgba(217,119,6,.06);border:1px solid rgba(217,119,6,.25);border-radius:6px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid rgba(217,119,6,.2)">
        <div style="font-size:13px;font-weight:600;color:var(--warn)">Consolidated mutation suggestions (${suggs.length} site${suggs.length>1?'s':''})</div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button type="button" id="${_vhhToggleId}" onclick="toggleSmartCmcSection('${_vhhSectionId}','${_vhhToggleId}')"
            style="padding:7px 12px;background:#1f3b5b;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:5px;cursor:pointer;font-size:11px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.22)">▼ Hide mutation evaluation</button>
          <button type="button" onclick="_openCmcUnifiedFromCtx('${ctxKey}')"
            style="padding:8px 16px;background:#0d8a72;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.18)">
            ▶ Open unified Smart-CMC selector (single + multi)
          </button>
        </div>
      </div>
      <div id="${_vhhSectionId}">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
          Use the unified selector above to execute single-category or combined Smart-CMC verification.
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;line-height:2">${allChips}</div>
      </div>
      <div id="vhh-batch-result-${ctxKey}" style="margin-top:12px;display:none"></div>
      </div>
    </div>`;

  return `<section class="result-panel" style="border-color:rgba(245,158,11,.35)">
    <div class="result-title" style="background:rgba(245,158,11,.05)">
      <strong style="color:#d97706">Smart-CMC: FR Optimization Suggestions (${suggs.length})</strong>
      <span style="font-size:10px;color:var(--muted)">${originNote}</span>
    </div>
    <div class="result-body">
      <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
        VHH/sdAb sequence-level advisory. Use <strong>Open unified Smart-CMC selector</strong> to evaluate single or combined mutations.
      </div>
      ${consolidatedPanel}
    </div>
  </section>`;
}

// ── VHH Variant Mini Re-evaluation ───────────────────────────────────────────

let _vhhVariantJobId = null;
let _vhhVariantAbortCtrl = null;
let _vhhOriginalResult = null;

let _vhhSuggestionContext = null;  // {catLabel, rationale, mutation}
let _vhhSuggRegistry = [];         // populated by _renderVhhFrSuggestions; indexed by onclick
let _bsSuggRegistry = [];          // populated by _renderVhhFrSuggestions for bispecific arms

function applyVhhSuggestion(regIdx) {
  const entry = _vhhSuggRegistry[regIdx];
  if (!entry) return;
  const {fromAA, toAA, linearPos, kabatPos, catLabel, rationale} = entry;

  const seqEl  = document.getElementById("vhh-variant-seq");
  const mutEl  = document.getElementById("vhh-variant-mut");
  const origSeq = (document.getElementById("vhh-cmc-seq")?.value || "").replace(/\s/g, "").toUpperCase();
  if (seqEl && origSeq) {
    const arr = origSeq.split("");
    if (arr[linearPos] === fromAA) arr[linearPos] = toAA;
    seqEl.value = arr.join("");
  }
  const mutLabel = `${fromAA}${kabatPos}${toAA}`;
  if (mutEl) mutEl.value = mutLabel;

  _vhhSuggestionContext = {catLabel, rationale, mutation: mutLabel};

  const sec = document.getElementById("vhh-variant-section");
  if (sec) sec.scrollIntoView({behavior:"smooth", block:"start"});
  // small delay so scroll completes before banner renders
  setTimeout(() => {
    const banner = document.getElementById("vhh-variant-purpose");
    if (banner) {
      banner.innerHTML = `<div style="font-size:11px;background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.4);border-radius:5px;padding:8px 11px">
        <div style="font-weight:700;color:#4f46e5;margin-bottom:3px">&#127919; Optimization Goal: ${escapeHtml(catLabel)}</div>
        <div style="color:var(--fg)">${escapeHtml(rationale)}</div>
      </div>`;
    }
  }, 350);
}

async function verifyVhhCategoryBatch(ctxKey, category) {
  // ctxKey = "vhh" or `bs-${armLabel}`
  const isBs = ctxKey.startsWith("bs-");
  const armLabel = isBs ? ctxKey.slice(3) : null;
  const registry = isBs ? _bsSuggRegistry : _vhhSuggRegistry;

  // Filter by category, scope to arm if bispecific
  const scope = registry.filter(e => isBs ? (e.armLabel === armLabel) : (!e.armLabel));
  let muts;
  if (category === "__custom__") {
    // Unified Smart-CMC selector — user picked arbitrary subset. Each item carries
    // {chain,pos,from,to,...} from cmcCollectMutationsByCategory; map to registry shape.
    const custom = window._cmcCustomMuts || [];
    muts = custom.map(c => {
      // Try to match by linearPos/fromAA/toAA against registry to recover catLabel & kabatPos
      const reg = scope.find(e => (e.linearPos === (c.pos - 1) || e.linearPos === c.pos) && e.fromAA === c.from && e.toAA === c.to);
      if (reg) return reg;
      // fallback: use kabat_pos carried through from custom muts
      const kp = c.kabat_pos != null ? c.kabat_pos : "?";
      return {linearPos: (c.pos != null ? c.pos - 1 : null), fromAA: c.from, toAA: c.to, kabatPos: kp, catLabel: c.category || "custom"};
    }).filter(m => m.linearPos != null);
  } else if (category === "combined") {
    muts = scope;
  } else {
    const catMap = {hydrophobic:"Hydrophobic Patch", charge:"Charge Patch", pI:"pI Tuning", stability:"Stability", sdab_adaptation:"sdAb Adaptation", engvh_stealth:"EngVH Stealth"};
    muts = scope.filter(e => e.catLabel === catMap[category]);
  }

  const resultEl = document.getElementById(`vhh-batch-result-${ctxKey}`);
  if (!resultEl) return;
  if (!muts.length) { resultEl.style.display = "block"; resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">No mutations found for category ${category}.</div>`; return; }

  // Resolve original sequence + origin + baseline
  let origSeq, origin, baselineResult;
  if (isBs) {
    const sourceSeq = (muts[0].armSeq || "").replace(/\s/g,"").toUpperCase();
    if (!sourceSeq) { resultEl.style.display = "block"; resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">Arm sequence not available.</div>`; return; }
    origSeq = sourceSeq;
    origin = (document.getElementById("bs-cmc-origin")||{}).value || "camelid_vhh";
    const armKey = armLabel === "arm1" ? "arm1" : "arm2";
    baselineResult = (window._lastBsCmcResult && window._lastBsCmcResult[armKey]) || null;
  } else {
    origSeq = (document.getElementById("vhh-cmc-seq")?.value || "").replace(/\s/g,"").toUpperCase();
    origin = (document.getElementById("vhh-cmc-origin")||{}).value || "camelid_vhh";
    baselineResult = _vhhOriginalResult || null;
  }
  if (!origSeq) { resultEl.style.display = "block"; resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">Original sequence not available.</div>`; return; }

  // Apply mutations
  const arr = origSeq.split("");
  const appliedLabels = [];
  for (const m of muts) {
    if (m.linearPos != null && m.linearPos >= 0 && m.linearPos < arr.length && arr[m.linearPos] === m.fromAA) {
      arr[m.linearPos] = m.toAA;
      appliedLabels.push(`${m.fromAA}${m.kabatPos}${m.toAA}`);
    }
  }
  if (!appliedLabels.length) { resultEl.style.display = "block"; resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">No mutations could be applied — sequence positions did not match.</div>`; return; }
  const variantSeq = arr.join("");

  const catLabel = (category === "combined") ? "Combined" : (muts[0]?.catLabel || category);
  resultEl.style.display = "block";
  resultEl.innerHTML = `<div style="padding:12px;background:rgba(0,0,0,.04);border-radius:6px;font-size:12px">
    <div style="font-weight:600;margin-bottom:6px">▶ Verifying ${escapeHtml(catLabel)} variant — applying ${appliedLabels.length} mutation${appliedLabels.length>1?'s':''}…</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">${appliedLabels.map(l=>`<code style="font-size:11px;padding:2px 6px;background:rgba(99,102,241,.1);border-radius:3px">${escapeHtml(l)}</code>`).join("")}</div>
    <div style="font-size:11px;color:var(--muted)">Sequence-only mini CMC (~10–15s)…</div>
  </div>`;

  try {
    const res = await apiFetch(apiJoin("cmc/vhh/async"), {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({vhh_sequence: variantSeq, report_format:"html", sdab_origin: origin,
        run_structure: false, smart_cmc: false, project_name: `${ctxKey}-${category}`}),
    });
    if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e.detail || `HTTP ${res.status}`); }
    const {job_id} = await res.json();
    let poll, c=0;
    while (c++ < 60) {
      await new Promise(r=>setTimeout(r,3000));
      const pr = await apiFetch(apiJoin(`jobs/${job_id}`));
      if (!pr.ok) throw new Error(`Poll ${pr.status}`);
      poll = await pr.json();
      if ((poll.status||"").match(/done|failed|cancelled/)) break;
    }
    if (!poll || poll.status !== "done") throw new Error(poll?.error || "Verify failed");
    _renderVhhBatchComparison(resultEl, baselineResult, poll.result || {}, catLabel, appliedLabels);
  } catch (err) {
    resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px;padding:8px">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function _renderVhhBatchComparison(host, baseR, varR, catLabel, appliedLabels) {
  const _origM = baseR?.metrics || {};
  const vm = varR.metrics || {};
  const origAdi = baseR?.adi_score ?? null;
  const vAdi = varR.adi_score ?? null;
  const adiDiff = (origAdi !== null && vAdi !== null) ? (vAdi - origAdi) : null;
  const adiColor = adiDiff === null ? "var(--muted)" : adiDiff >= 0 ? "var(--pass)" : "var(--fail)";
  const adiArrow = adiDiff === null ? "—" : adiDiff >= 0 ? `▲ +${adiDiff.toFixed(1)}` : `▼ ${adiDiff.toFixed(1)}`;
  const statusColor = varR.overall_status === "PASS" ? "var(--pass)" : varR.overall_status === "FAIL" ? "var(--fail)" : "var(--warn)";
  const scoreLabel = varR.score_display_name || baseR?.score_display_name || "VHH/sdAb Gate Score";
  const _hpr = (obj) => obj?.hpr_score ?? (((obj?.hpr_index || {}).combined || {}).score ?? null);

  const varFlags = varR.risk_flags || {};
  const _afterFlag = (key, afterVal) => {
    if (afterVal == null) return "N/A";
    if (key === "__abnativ_delta") {
      if (afterVal >= 0) return "PASS";
      if (afterVal > -0.05) return "WARN";
      if (afterVal > -0.074) return "WARN";
      return "FAIL";
    }
    if (key === "__hpr_score") {
      if (afterVal >= 0.80) return "PASS";
      if (afterVal >= 0.65) return "MONITOR";
      return "WARN";
    }
    return varFlags[key] || "PASS";
  };
  const _verdictBadge = (flag) => {
    const isOk = flag === "PASS";
    const isMonitor = flag === "MONITOR";
    const isWarn = flag === "WARN";
    const isFail = flag === "FAIL";
    const bg = isOk ? "var(--pass)" : isFail ? "var(--fail)" : (isMonitor ? "#0ea5b7" : "var(--warn)");
    const lbl = isOk ? "IN RANGE" : isFail ? "OUT OF RANGE" : isMonitor ? "MONITOR" : isWarn ? "BORDERLINE" : "N/A";
    if (flag === "N/A") return `<span style="font-size:9px;color:var(--muted)">—</span>`;
    return `<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${bg};color:white;font-weight:700">${lbl}</span>`;
  };

  const _renderGroup = (title, keys) => {
    const groupRows = keys.map(([lbl,key]) => {
      const before = key === "__abnativ_delta" ? (baseR?.abnativ_delta ?? null) : key === "__hpr_score" ? _hpr(baseR) : (_origM[key] ?? null);
      const after = key === "__abnativ_delta" ? (varR.abnativ_delta ?? null) : key === "__hpr_score" ? _hpr(varR) : (vm[key] ?? null);
      const delta = (before!==null && after!==null) ? (after - before) : null;
      const lowerBetter = ["instability_index","SAP_score","hydro_patch_max9","charge_patch_max7","agg_motifs","deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys"].includes(key);
      const goodDelta = delta===null?false:lowerBetter?delta<0:delta>0;
      const dColor = delta===null||delta===0?"var(--muted)":goodDelta?"var(--pass)":"var(--fail)";
      const dArrow = delta===null?"—":delta>0?`▲ +${delta.toFixed(2)}`:delta<0?`▼ ${delta.toFixed(2)}`:"→ 0";
      const verdictHtml = _verdictBadge(_afterFlag(key, after));
      return `<tr><th>${lbl}</th><td style="font-family:monospace">${before!==null?fmt(before):"—"}</td><td>→</td><td style="font-family:monospace;font-weight:600">${after!==null?fmt(after):"—"}</td><td style="color:${dColor};font-weight:600">${dArrow}</td><td>${verdictHtml}</td></tr>`;
    }).join("");
    return `
      <div style="margin-top:8px">
        <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:4px">${title}</div>
        <table class="kv-table" style="font-size:11px">
          <thead><tr><th></th><th style="text-align:right;font-size:9px;color:var(--muted)">Base</th><th></th><th style="text-align:right;font-size:9px;color:var(--muted)">After</th><th style="text-align:right;font-size:9px;color:var(--muted)">Δ</th><th style="text-align:right;font-size:9px;color:var(--muted)">Range</th></tr></thead>
          ${groupRows}
        </table>
      </div>
    `;
  };

  const physGroup = [
    ["pI","pI"], ["GRAVY","GRAVY"], ["Instability","instability_index"],
    ["SAP","SAP_score"], ["Hydro Patch","hydro_patch_max9"], ["Net Charge","net_charge_pH7"],
    ["Charge Patch","charge_patch_max7"], ["Agg Motifs","agg_motifs"],
  ];
  const cdrGroup = [
    ["Deamidation","deamidation_sites"], ["Isomerization","isomerization_sites"], ["Oxidation","oxidation_sites"], ["Glycosylation","glycosylation_sites"], ["Free Cys","free_cys"],
  ];
  const humanGroup = [
    ["AbNatiV2 Δ","__abnativ_delta"], ["HPR Index","__hpr_score"],
  ];

  const tradeOff = adiDiff !== null && adiDiff < 0
    ? `<div style="margin-top:8px;padding:6px 10px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.4);border-radius:4px;font-size:11px;color:var(--fail);font-weight:600">TRADE-OFF REVIEW REQUIRED — Gate Score regressed; some metrics improved at the cost of others.</div>`
    : (adiDiff !== null && adiDiff >= 1)
      ? `<div style="margin-top:8px;padding:6px 10px;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.4);border-radius:4px;font-size:11px;color:var(--pass);font-weight:600">&#10003; Gate Score improved — variant recommended for further evaluation.</div>` : "";

  host.innerHTML = `
    <div style="border:1px solid rgba(99,102,241,.4);border-radius:8px;padding:14px;background:rgba(99,102,241,.04)">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap">
        <strong style="font-size:14px">${escapeHtml(catLabel)} variant — ${appliedLabels.length} mutation${appliedLabels.length>1?'s':''}</strong>
        <span style="font-size:10px;padding:2px 7px;border-radius:3px;background:${statusColor};color:white;font-weight:700">${varR.overall_status || "?"}</span>
        <span style="font-size:14px;font-weight:700;color:${adiColor}">${adiArrow}</span>
        <span style="font-size:11px;color:var(--muted)">${escapeHtml(scoreLabel)}: ${origAdi!==null?origAdi.toFixed(1):"—"} → ${vAdi!==null?vAdi.toFixed(1):"—"}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">${appliedLabels.map(l=>`<code style="font-size:11px;padding:2px 6px;background:rgba(99,102,241,.12);border-radius:3px;font-weight:600;color:#4f46e5">${escapeHtml(l)}</code>`).join("")}</div>
      
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          ${_renderGroup("Physicochemical Profile", physGroup)}
        </div>
        <div>
          ${_renderGroup("Chemical Liabilities (PTM)", cdrGroup)}
          ${_renderGroup("Humanness & Origin", humanGroup)}
        </div>
      </div>

      ${tradeOff}


      <div style="margin-top:10px;padding:10px;background:rgba(255,255,255,.5);border-radius:6px;border:1px solid rgba(99,102,241,.15)">
        <div style="font-weight:600;color:var(--muted);margin-bottom:6px;font-size:11px">Optimized VHH Sequence (mutations highlighted)</div>
        <div class="mono" style="word-break:break-all;line-height:1.6;font-size:11px;background:#fff;padding:6px;border-radius:4px;border:1px solid rgba(0,0,0,.05)">
          ${_highlightMutations(baseR?.sequence || "", varR.sequence || "")}
        </div>
      </div>

      <div style="font-size:10px;color:var(--muted);margin-top:8px">Sequence-only mode (no structure prediction). Gate grade: ${varR.adi_grade || "—"} · ${varR.n_fail||0} FAIL · ${varR.n_warn||0} WARN</div>
    </div>`;
}

function applyBsSuggestion(regIdx) {
  const entry = _bsSuggRegistry[regIdx];
  if (!entry) return;
  const {fromAA, toAA, linearPos, kabatPos, catLabel, rationale, armLabel, armSeq} = entry;
  const seqEl = document.getElementById(`bs-var-seq-${armLabel}`);
  const mutEl = document.getElementById(`bs-var-mut-${armLabel}`);
  const sourceSeq = (armSeq || seqEl?.value || "").replace(/\s/g, "").toUpperCase();
  if (seqEl && sourceSeq) {
    const arr = sourceSeq.split("");
    if (arr[linearPos] === fromAA) arr[linearPos] = toAA;
    seqEl.value = arr.join("");
  }
  const mutLabel = `${fromAA}${kabatPos}${toAA}`;
  if (mutEl) mutEl.value = mutLabel;
  const banner = document.getElementById(`bs-var-purpose-${armLabel}`);
  if (banner) {
    banner.innerHTML = `<div style="font-size:11px;background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.4);border-radius:5px;padding:8px 11px;margin-bottom:8px">
      <div style="font-weight:700;color:#4f46e5;margin-bottom:3px">&#127919; Optimization Goal: ${escapeHtml(catLabel)}</div>
      <div style="color:var(--fg)">${escapeHtml(rationale)}</div>
    </div>`;
  }
  document.getElementById(`bs-variant-${armLabel}`)?.scrollIntoView({behavior:"smooth", block:"start"});
}

function _renderVhhVariantVerify(origSeq, origin, jobId) {
  return `<section class="result-panel" id="vhh-variant-section" style="border-color:rgba(99,102,241,.35)">
    <div class="result-title" style="background:rgba(99,102,241,.05)">
      <strong style="color:#6366f1">Variant Re-evaluation</strong>
      <span style="font-size:10px;color:var(--muted)">Click "Apply &amp; Verify" on a suggestion above to auto-fill, or manually edit the sequence and label below.</span>
    </div>
    <div class="result-body">
      <div class="form-grid" style="grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
        <div class="field">
          <label style="font-size:11px">Mutation label</label>
          <input type="text" id="vhh-variant-mut" placeholder="Suggested mutation label" maxlength="30"
            style="font-family:monospace;font-size:13px" oninput="document.getElementById('vhh-variant-purpose').innerHTML=''">
          <div id="vhh-variant-purpose" style="margin-top:5px"></div>
        </div>
        <div class="field">
          <label style="font-size:11px">Variant sequence</label>
          <textarea id="vhh-variant-seq" style="height:75px;font-family:monospace;font-size:11px">${escapeHtml(origSeq)}</textarea>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button type="button" class="btn primary" style="font-size:12px;padding:5px 14px"
          onclick="runVhhVariantVerify('${escapeHtml(origin)}')">Verify Variant (~15s)</button>
        <button type="button" class="btn" id="vhh-variant-cancel" style="display:none;font-size:12px;padding:5px 14px;background:var(--fail);color:white;border-color:var(--fail)"
          onclick="cancelVhhVariant()">Cancel</button>
        <span id="vhh-variant-status" style="font-size:11px;color:var(--muted)"></span>
      </div>
      <div id="vhh-variant-result" style="margin-top:10px"></div>
    </div>
  </section>`;
}

async function cancelVhhVariant() {
  if (_vhhVariantAbortCtrl) { _vhhVariantAbortCtrl.abort(); _vhhVariantAbortCtrl = null; }
  if (_vhhVariantJobId) {
    try { await apiFetch(apiJoin(`jobs/${_vhhVariantJobId}/cancel`), {method:"POST"}); } catch(_){}
    _vhhVariantJobId = null;
  }
  document.getElementById("vhh-variant-cancel")?.style.setProperty("display","none");
  document.getElementById("vhh-variant-status").textContent = "Cancelled.";
}

async function runVhhVariantVerify(origin) {
  const seq = (document.getElementById("vhh-variant-seq")?.value || "").replace(/\s/g,"").toUpperCase();
  const mutLabel = (document.getElementById("vhh-variant-mut")?.value || "").trim() || "variant";
  if (seq.length < 100) {
    document.getElementById("vhh-variant-result").innerHTML =
      `<div style="color:var(--fail);font-size:11px">Sequence too short — paste the full variant VHH/sdAb sequence.</div>`;
    return;
  }
  if (_vhhVariantAbortCtrl) { _vhhVariantAbortCtrl.abort(); }
  _vhhVariantAbortCtrl = new AbortController();

  const statusEl  = document.getElementById("vhh-variant-status");
  const resultEl  = document.getElementById("vhh-variant-result");
  const cancelBtn = document.getElementById("vhh-variant-cancel");
  statusEl.textContent = "Starting…";
  resultEl.innerHTML = "";
  if (cancelBtn) cancelBtn.style.display = "inline-flex";

  // Store original gate score for comparison
  const origAdi = _vhhOriginalResult?.adi_score ?? null;

  try {
    const res = await apiFetch(apiJoin("cmc/vhh/async"), {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        vhh_sequence: seq,
        report_format: "html",
        sdab_origin: origin,
        run_structure: false,
        smart_cmc: false,
        project_name: mutLabel,
      }),
      signal: _vhhVariantAbortCtrl.signal,
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
    const startData = await res.json();
    _vhhVariantJobId = startData.job_id;

    let poll, count = 0;
    while (count < 60) {
      if (_vhhVariantAbortCtrl?.signal.aborted) break;
      await new Promise(r => setTimeout(r, 3000));
      count++;
      const pr = await apiFetch(apiJoin(`jobs/${_vhhVariantJobId}`), {signal: _vhhVariantAbortCtrl?.signal});
      if (!pr.ok) throw new Error(`Poll ${pr.status}`);
      poll = await pr.json();
      statusEl.textContent = `${poll.progress_note || poll.status} (${poll.progress||0}%)`;
      if ((poll.status||"").match(/done|failed|cancelled/)) break;
    }
    if (cancelBtn) cancelBtn.style.display = "none";
    _vhhVariantJobId = null;
    if (!poll || poll.status === "failed") throw new Error(poll?.error || "Job failed");
    if (poll.status === "cancelled") { statusEl.textContent = "Cancelled."; return; }

    const vr = poll.result || {};
    const vm = vr.metrics || {};
    const vAdi = vr.adi_score ?? null;
    const adiDiff = (origAdi !== null && vAdi !== null) ? (vAdi - origAdi) : null;
    const adiColor = adiDiff === null ? "var(--muted)" : adiDiff >= 0 ? "var(--pass)" : "var(--fail)";
    const adiArrow = adiDiff === null ? "—" : adiDiff >= 0 ? `▲ +${adiDiff.toFixed(1)}` : `▼ ${adiDiff.toFixed(1)}`;
    const scoreLabel = vr.score_display_name || _vhhOriginalResult?.score_display_name || "VHH/sdAb Gate Score";

    const statusColor = vr.overall_status === "PASS" ? "var(--pass)" : vr.overall_status === "FAIL" ? "var(--fail)" : "var(--warn)";

    const ctx = _vhhSuggestionContext;
    const ctxHtml = (ctx && ctx.catLabel) ? `
      <div style="font-size:11px;background:rgba(99,102,241,.06);border-left:3px solid #6366f1;border-radius:0 4px 4px 0;padding:6px 10px;margin-bottom:8px">
        <strong style="color:#6366f1">Optimization target: ${escapeHtml(ctx.catLabel)}</strong>
        ${ctx.rationale ? `<div style="margin-top:2px;color:var(--muted)">${escapeHtml(ctx.rationale)}</div>` : ""}
      </div>` : "";

    // Per-metric delta rows
    const _origM = _vhhOriginalResult?.metrics || {};
    const _hprScore = (obj) => obj?.hpr_score ?? (((obj?.hpr_index || {}).combined || {}).score ?? null);

    const _varFlags = vr.risk_flags || {};
    const _afterFlag2 = (key, afterVal) => {
      if (afterVal == null) return "N/A";
      if (key === "__abnativ_delta") {
        if (afterVal >= 0) return "PASS";
        if (afterVal > -0.074) return "WARN";
        return "FAIL";
      }
      if (key === "__hpr_score") {
        if (afterVal >= 0.80) return "PASS";
        if (afterVal >= 0.65) return "MONITOR";
        return "WARN";
      }
      return _varFlags[key] || "PASS";
    };
    const _verdictBadge2 = (flag) => {
      if (flag === "N/A") return `<span style="font-size:9px;color:var(--muted)">—</span>`;
      const isOk = flag === "PASS";
      const isFail = flag === "FAIL";
      const isMonitor = flag === "MONITOR";
      const bg = isOk ? "var(--pass)" : isFail ? "var(--fail)" : (isMonitor ? "#0ea5b7" : "var(--warn)");
      const lbl = isOk ? "IN RANGE" : isFail ? "OUT OF RANGE" : isMonitor ? "MONITOR" : "BORDERLINE";
      return `<span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${bg};color:white;font-weight:700">${lbl}</span>`;
    };
    const _renderGroup = (title, keys) => {
      const groupRows = keys.map(([label, key]) => {
        const before = key === "__abnativ_delta" ? (_vhhOriginalResult?.abnativ_delta ?? null) : key === "__hpr_score" ? _hprScore(_vhhOriginalResult) : (_origM[key] ?? null);
        const after = key === "__abnativ_delta" ? (vr.abnativ_delta ?? null) : key === "__hpr_score" ? _hprScore(vr) : (vm[key] ?? null);
        const delta = (before !== null && after !== null) ? (after - before) : null;
        const dc = delta === null ? "" : delta === 0 ? "" : "font-weight:600";
        const lowerBetter = ["instability_index","SAP_score","hydro_patch_max9","charge_patch_max7","agg_motifs","deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys"].includes(key);
        const goodDelta = delta === null ? false : lowerBetter ? delta < 0 : delta > 0;
        const dColor = delta === null || delta === 0 ? "var(--muted)" : goodDelta ? "var(--pass)" : "var(--fail)";
        const dArrow = delta === null ? "—" : delta > 0 ? `▲ +${delta.toFixed(2)}` : delta < 0 ? `▼ ${delta.toFixed(2)}` : "→ 0";
        return `<tr>
          <th>${label}</th>
          <td style="font-family:monospace">${before !== null ? fmt(before) : "—"}</td>
          <td>→</td>
          <td style="font-family:monospace;${dc}">${after !== null ? fmt(after) : "—"}</td>
          <td style="color:${dColor};font-weight:600">${dArrow}</td>
          <td>${_verdictBadge2(_afterFlag2(key, after))}</td>
        </tr>`;
      }).join("");
      return `
        <div style="margin-top:8px">
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:4px">${title}</div>
          <table class="kv-table" style="font-size:11px">
            <thead><tr><th></th><th style="text-align:right;font-size:9px;color:var(--muted)">Base</th><th></th><th style="text-align:right;font-size:9px;color:var(--muted)">After</th><th style="text-align:right;font-size:9px;color:var(--muted)">Δ</th><th style="text-align:right;font-size:9px;color:var(--muted)">Range</th></tr></thead>
            ${groupRows}
          </table>
        </div>
      `;
    };

    const physGroup = [
      ["pI", "pI"], ["GRAVY", "GRAVY"], ["Instability", "instability_index"],
      ["SAP", "SAP_score"], ["Hydro Patch", "hydro_patch_max9"], ["Net Charge", "net_charge_pH7"],
    ];
    const cdrGroup = [
      ["Deamidation", "deamidation_sites"], ["Isomerization", "isomerization_sites"], ["Oxidation", "oxidation_sites"], ["Glycosylation", "glycosylation_sites"], ["Free Cys", "free_cys"],
    ];
    const humanGroup = [
      ["AbNatiV2 Δ", "__abnativ_delta"], ["HPR Index", "__hpr_score"],
    ];

    resultEl.innerHTML = `
      <div style="border:1px solid rgba(99,102,241,.4);border-radius:8px;padding:12px;background:rgba(99,102,241,.04)">
        ${ctxHtml}
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap">
          <strong style="font-size:14px">${escapeHtml(mutLabel)}</strong>
          <span style="font-size:10px;padding:2px 7px;border-radius:3px;background:${statusColor};color:white;font-weight:700">${vr.overall_status || "?"}</span>
          <span style="font-size:14px;font-weight:700;color:${adiColor}">${adiArrow}</span>
          <span style="font-size:11px;color:var(--muted)">${escapeHtml(scoreLabel)}: ${origAdi !== null ? origAdi.toFixed(1) : "—"} → ${vAdi !== null ? vAdi.toFixed(1) : "—"}</span>
          ${adiDiff !== null && adiDiff < 0 ? `<span style="font-size:10px;padding:2px 6px;background:rgba(239,68,68,.15);color:var(--fail);border-radius:3px;font-weight:600">Gate Score regression — trade-off review required</span>` : ""}
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div>
            ${_renderGroup("Physicochemical Profile", physGroup)}
          </div>
          <div>
            ${_renderGroup("Chemical Liabilities (PTM)", cdrGroup)}
            ${_renderGroup("Humanness & Origin", humanGroup)}
          </div>
        </div>

        <div style="font-size:10px;color:var(--muted);margin-top:8px">Sequence-only mode (no structure). Gate grade: ${vr.adi_grade || "—"} · ${vr.n_fail||0} FAIL · ${vr.n_warn||0} WARN</div>
      </div>`;

    statusEl.textContent = "Done.";
  } catch(err) {
    if (cancelBtn) cancelBtn.style.display = "none";
    _vhhVariantJobId = null;
    if (err.name === "AbortError") { statusEl.textContent = "Cancelled."; return; }
    resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">Error: ${escapeHtml(err.message)}</div>`;
    statusEl.textContent = "";
  }
}

// ── Bispecific VHH CMC ────────────────────────────────────────────────────────

let _bsCmcAbortCtrl = null;
let _bsCmcJobId = null;

async function cancelBsCmc() {
  if (_bsCmcAbortCtrl) { _bsCmcAbortCtrl.abort(); _bsCmcAbortCtrl = null; }
  if (_bsCmcJobId) {
    try { await apiFetch(apiJoin(`jobs/${_bsCmcJobId}/cancel`), {method:"POST"}); } catch(_){}
    _bsCmcJobId = null;
  }
  document.getElementById("bs-cmc-cancel-btn")?.style.setProperty("display","none");
  document.getElementById("bs-cmc-status-bar")?.replaceChildren();
  clearRunning();
  setOutput(`<div class="muted" style="padding:12px">Bispecific CMC cancelled.</div>`);
}

async function runBispecificAssembler(service) {
  const vha = (document.getElementById("bs-assembler-vh-a")?.value || "").trim();
  const vla = (document.getElementById("bs-assembler-vl-a")?.value || "").trim();
  const vhb = (document.getElementById("bs-assembler-vh-b")?.value || "").trim();
  const vlb = (document.getElementById("bs-assembler-vl-b")?.value || "").trim();
  const format = document.getElementById("bs-assembler-format")?.value || "";
  const fc = document.getElementById("bs-assembler-fc")?.value || "";
  
  if (!vha || !vhb) {
    setOutput(errorPanel("Please provide at least Binder A VH and Binder B VH."));
    return;
  }

  const status = document.getElementById("service-status");
  status.innerHTML = `<div style="border:1px solid var(--warn);color:var(--warn);background:rgba(212,167,44,0.1);padding:12px;border-radius:8px;font-size:13px;line-height:1.5">
    <strong>Backend Connection Pending</strong><br>
    The Console UI is fully configured, but the corresponding Python endpoint <code>/bispecific/assemble</code> must be registered in <code>api/routers/bispecific.py</code> and <code>api/models.py</code>.<br><br>
    <em>(Write-permission denied for core backend files during this session).</em><br><br>
    <strong>Inputs captured for processing:</strong><br>
    • Format: ${format}<br>
    • Fc Scaffold: ${fc}<br>
    • Binder A: VH (${vha.length} aa), VL (${vla.length} aa)<br>
    • Binder B: VH (${vhb.length} aa), VL (${vlb.length} aa)
  </div>`;
}

async function runBispecificAnalyzer(service) {
  const vha = (document.getElementById("bs-analyzer-vh-a")?.value || "").trim();
  const vhb = (document.getElementById("bs-analyzer-vh-b")?.value || "").trim();

  if (!vha || !vhb) {
    setOutput(errorPanel("Please provide at least Binder A VH and Binder B VH."));
    return;
  }

  const status = document.getElementById("service-status");
  status.innerHTML = `<div style="border:1px solid var(--warn);color:var(--warn);background:rgba(212,167,44,0.1);padding:12px;border-radius:8px;font-size:13px;line-height:1.5">
    <strong>Backend Connection Pending</strong><br>
    The Console UI is ready, but the orchestrating Python endpoint <code>/bispecific/analyze</code> must be registered in <code>api/routers/bispecific.py</code> and <code>api/models.py</code>.<br><br>
    <em>(Write-permission denied for core backend files during this session).</em><br><br>
    <strong>Planned workflow:</strong> The backend will automatically split these inputs into 4 Fv pairing combinations (A_H+A_L, B_H+B_L, A_H+B_L, B_H+A_L), run ImmuneBuilder + p-AbNatiV + Charge Asymmetry, and return the Pairing Selectivity Index (PSI) matrix.
  </div>`;
}

async function runCmcBispecific(service) {
  if (_bsCmcAbortCtrl && !_bsCmcAbortCtrl.signal.aborted) _bsCmcAbortCtrl.abort();
  _bsCmcAbortCtrl = new AbortController();
  _bsCmcJobId = null;

  const a1 = normalizeSeq(document.getElementById("bs-cmc-arm1").value);
  const a2 = normalizeSeq(document.getElementById("bs-cmc-arm2").value);
  const demoId = document.getElementById("bs-cmc-demo").value;
  const bsProjName = (document.getElementById("bs-cmc-name")?.value || "").trim();
  const errors = [
    validateSeq(a1, "Arm1 VHH", 105, 145),
    validateSeq(a2, "Arm2 VHH", 105, 145),
  ].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct both VHH arm sequences.", artifacts:[], metadata:[]});
    return;
  }

  const cancelBtn = document.getElementById("bs-cmc-cancel-btn");
  const statusBar = document.getElementById("bs-cmc-status-bar");
  function _showBsProg(pct, label) {
    pct = Math.min(Math.max(pct||0,0),99);
    if (statusBar) statusBar.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:3px">
        <span>${label}</span><span>${Math.round(pct)}%</span>
      </div>
      <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:var(--accent);transition:width .4s ease;border-radius:2px"></div>
      </div>`;
    setRunning(label);
  }
  function _clearBsProg() {
    if (statusBar) statusBar.innerHTML = "";
    if (cancelBtn) cancelBtn.style.display = "none";
    clearRunning();
  }

  if (cancelBtn) cancelBtn.style.display = "inline-flex";
  _showBsProg(5, "Starting Bispecific VHH CMC…");
  setOutput("");

  const phases = [
    {pct:20, label:"Arm 1 — VHH CMC assessment…"},
    {pct:45, label:"Arm 2 — VHH CMC assessment…"},
    {pct:65, label:"Fusion matrix & linker selection…"},
    {pct:80, label:"AbNatiV2 naturalness scoring…"},
    {pct:90, label:"Smart-CMC FR suggestions…"},
  ];
  let phaseIdx = 0;
  const phaseTimer = setInterval(() => {
    if (phaseIdx < phases.length) { _showBsProg(phases[phaseIdx].pct, phases[phaseIdx].label); phaseIdx++; }
  }, 6000);

  try {
    const res = await apiFetch(apiJoin("cmc/bispecific/async"), {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        arm1_sequence: a1,
        arm2_sequence: a2,
        arm1_target: (document.getElementById("bs-cmc-t1")?.value || "Target_A").trim(),
        arm2_target: (document.getElementById("bs-cmc-t2")?.value || "Target_B").trim(),
        linker: (document.getElementById("bs-cmc-linker")?.value || "(G4S)3").trim(),
        project_name: bsProjName || "demo",
          report_format: "html",
          sdab_origin: (document.getElementById("bs-cmc-origin")||{}).value || "camelid_vhh",
          run_structure: true,
          smart_cmc: !!(document.getElementById("bs-cmc-smart-opt")?.checked),
      }),
      signal: _bsCmcAbortCtrl.signal,
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
    const startData = await res.json();
    _bsCmcJobId = startData.job_id;

    let poll, count = 0;
    while (count < 200) {
      if (_bsCmcAbortCtrl?.signal.aborted) break;
      await new Promise(r => setTimeout(r, 3000));
      count++;
      const pr = await apiFetch(apiJoin(`jobs/${_bsCmcJobId}`), {signal: _bsCmcAbortCtrl?.signal});
      if (!pr.ok) throw new Error(`Poll ${pr.status}`);
      poll = await pr.json();
      if (poll.progress) _showBsProg(poll.progress, `Bispecific CMC — ${poll.progress_note || poll.status}`);
      if ((poll.status||"").match(/done|failed|cancelled/)) break;
    }
    clearInterval(phaseTimer);
    _clearBsProg();
    _bsCmcJobId = null;
    if (!poll || poll.status === "failed") throw new Error(poll?.error || "Job failed");
    if (poll.status === "cancelled") { setOutput(`<div class="muted" style="padding:12px">Bispecific CMC cancelled.</div>`); return; }
    renderCmcBispecificResult(poll, service, demoId);
  } catch(err) {
    clearInterval(phaseTimer);
    _clearBsProg();
    _bsCmcJobId = null;
    if (err.name === "AbortError") { setOutput(`<div class="muted" style="padding:12px">Bispecific CMC cancelled.</div>`); return; }
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"Bispecific CMC failed", summaryText:err.message, metrics:[], recommendation:"Inspect the error and sequence inputs.", artifacts:[], metadata:[]});
  }
}

// ── Bispecific CMC per-arm renderer helper ─────────────────────────────────

function _renderBsArm(arm, armLabel, armTarget, origin, jobId, smartRequested = false) {
  if (!arm || !arm.metrics) return `<div class="muted" style="padding:8px">Arm data not available.</div>`;
  const m = arm.metrics || {};
  const flags = arm.risk_flags || {};
  const vhhSpec = arm.vhh_specific || {};
  const structM = arm.structure_metrics || {};
  const isEngVH = (origin||"").toLowerCase().replace(/-/g,"_") === "engineered_vh";

  const _ft = (f) => f === "FAIL" ? "fail" : f === "WARN" ? "warn" : "ok";
  const adiScore = arm.adi_score ?? null;
    const nWarn = (arm.n_warn ?? 0) + (vhhSpec.fr2_hallmark_flag === "WARN" ? 1 : 0) + (vhhSpec.noncanonical_cys_flag === "WARN" ? 1 : 0);
    const nFail = (arm.n_fail ?? 0) + (vhhSpec.fr2_hallmark_flag === "FAIL" ? 1 : 0) + (vhhSpec.noncanonical_cys_flag === "FAIL" ? 1 : 0);
    const wfBadge = nFail > 0
    ? `<span style="color:var(--fail);font-weight:600">${nFail} FAIL · ${nWarn} WARN</span>`
    : nWarn > 0 ? `<span style="color:var(--warn);font-weight:600">${nWarn} WARN</span>`
    : `<span style="color:var(--pass)">All PASS</span>`;

  const sapMode = m.SAP_mode || "sequence_proxy_7mer";
  const sapLabel = sapMode === "sasa_7mer" ? "SAP (SASA)" : "SAP (seq)";
  const plddt = structM.plddt ?? null;
  const fr2Tetrad = vhhSpec.fr2_hallmark_tetrad || "—";
  const fr2Flag   = vhhSpec.fr2_hallmark_flag   || "NOT_RUN";
  const fr2Hydro  = vhhSpec.exposed_fr2_hydrophobicity;
  const fr2HydroFlag = vhhSpec.fr2_hydro_flag || "NOT_RUN";
  const noncanCys = vhhSpec.noncanonical_cys ?? null;
  const abnativDelta = arm.abnativ_delta;
  const abnativTier  = arm.abnativ_tier || "";
  const abnativHtml  = abnativDelta !== null && abnativDelta !== undefined
    ? `<strong>${abnativDelta.toFixed(3)}</strong> <span class="muted">(${abnativTier})</span>`
    : `<span class="muted">AbNatiV2 not computed (warm-up needed)</span>`;

  const pctRows = Object.entries(arm.percentile_ranks || {}).map(([k,v]) =>
    `<tr><th>${_VHH_METRIC_LABELS[k]||k}</th><td>${v}</td></tr>`).join("");

  // FR suggestions
  const frSuggs  = arm.fr_modification_suggestions || [];
  const smartRun = !!(arm.smart_cmc_run || smartRequested);
  const frHtml   = _renderVhhFrSuggestions(frSuggs, smartRun, isEngVH, {armLabel, armSeq: arm.sequence || ""});

  // Variant verify for this arm
  const armSeq = arm.sequence || "";
  const varHtml = (frSuggs && frSuggs.length > 0) ? `<section class="result-panel" id="bs-variant-${armLabel}" style="border-color:rgba(99,102,241,.35)">
    <div class="result-title" style="background:rgba(99,102,241,.05)">
      <strong style="color:#6366f1">${escapeHtml(armLabel)} Variant Re-evaluation</strong>
    </div>
    <div class="result-body">
      <div class="form-grid" style="grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
        <div class="field"><label style="font-size:11px">Mutation label</label>
          <input type="text" id="bs-var-mut-${armLabel}" placeholder="Suggested mutation label" maxlength="20" style="font-family:monospace;font-size:13px"></div>
        <div class="field"><label style="font-size:11px">Variant sequence</label>
          <textarea id="bs-var-seq-${armLabel}" style="height:55px;font-family:monospace;font-size:11px">${escapeHtml(armSeq)}</textarea></div>
      </div>
      <div id="bs-var-purpose-${armLabel}"></div>
      <div style="display:flex;gap:8px;align-items:center">
        <button type="button" class="btn primary" style="font-size:12px;padding:5px 12px"
          onclick="runBsArmVariant('${armLabel}','${escapeHtml(origin)}',${adiScore ?? null})">Verify Variant</button>
        <span id="bs-var-status-${armLabel}" style="font-size:11px;color:var(--muted)"></span>
      </div>
      <div id="bs-var-result-${armLabel}" style="margin-top:8px"></div>
    </div>
  </section>` : "";

  // Gate Score summary row
  const adiSummaryHtml = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;padding:8px 11px;border-radius:6px;background:rgba(0,0,0,.04);border:1px solid rgba(148,163,184,.18)">
    <div>
      <div style="font-size:18px;font-weight:700;color:${(adiScore||0)>=60?"var(--pass)":"var(--warn)"}">${adiScore !== null ? adiScore.toFixed(1) : "—"}</div>
      <div style="font-size:10px;color:var(--muted)">VHH/sdAb Gate Score / 100</div>
    </div>
    <div style="flex:1">
      <div style="font-size:13px;font-weight:600">${arm.adi_grade || "—"}</div>
      <div style="font-size:11px;margin-top:2px">${wfBadge}</div>
    </div>
  </div>`;

  return `
    ${adiSummaryHtml}
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Physicochemical Profile — Value · Flag · Percentile vs selected VHH/sdAb panel · Range</div>
    ${_vhhMetricCardGrid(m, flags, arm.percentile_ranks || {}, sapLabel, sapMode, arm)}
    <div style="margin-bottom:12px"></div>
    <table class="kv-table" style="font-size:11px;margin-bottom:10px">
      ${isEngVH
        ? `<tr><th>FR2 residues (37/44/45/47)</th><td><code>${escapeHtml(fr2Tetrad)}</code>
           &nbsp;<span style="font-size:10px;padding:1px 4px;border-radius:3px;background:rgba(148,163,184,.2);color:var(--muted)">N/A – EngVH</span></td></tr>`
        : `<tr><th>FR2 Hallmark (37/44/45/47)</th><td><code>${escapeHtml(fr2Tetrad)}</code>
           ${fr2Flag !== "NOT_RUN" ? `<span style="margin-left:5px;font-size:10px;padding:1px 4px;border-radius:3px;background:${fr2Flag==="PASS"?"var(--pass)":"var(--warn)"};color:white">${fr2Flag}</span>` : ""}</td></tr>`}
      <tr><th>FR2 hydrophobicity</th><td>${fr2Hydro !== null && fr2Hydro !== undefined ? fr2Hydro.toFixed(3) : "—"}
        ${!isEngVH && fr2HydroFlag !== "NOT_RUN" ? `<span style="margin-left:5px;font-size:10px;padding:1px 4px;border-radius:3px;background:${fr2HydroFlag==="PASS"?"var(--pass)":fr2HydroFlag==="WARN"?"var(--warn)":"var(--fail)"};color:white">${fr2HydroFlag}</span>` : ""}</td></tr>
      <tr><th>Non-canonical Cys</th><td>${noncanCys !== null ? noncanCys : "—"}</td></tr>
      <tr><th>AbNatiV2 Δ</th><td>${abnativHtml}</td></tr>
      <tr><th>HPR Index</th><td>${arm.hpr_score !== null && arm.hpr_score !== undefined ? arm.hpr_score.toFixed(3) : "—"}</td></tr>
    </table>
    ${structM.structure_computed ? `<div style="margin-bottom:10px"><div class="metric-grid">
      ${metricHtml("pLDDT", plddt !== null ? plddt.toFixed(1):"—", (plddt||0)<70?"warn":"ok")}
      ${metricHtml("PSH", fmt(structM.psh))}
      ${metricHtml("PPC", fmt(structM.ppc))}
      ${metricHtml("PNC", fmt(structM.pnc))}
    </div></div>` : ""}
    <table class="kv-table" style="font-size:11px;margin-bottom:10px">
      <tr><th>Agg motifs</th><td>${m.agg_motifs??'—'}</td><th>Deamidation</th><td>${m.deamidation_sites??'—'}</td></tr>
      <tr><th>Isomerization</th><td>${m.isomerization_sites??'—'}</td><th>Oxidation</th><td>${m.oxidation_sites??'—'}</td></tr>
      <tr><th>Glycosylation</th><td>${m.glycosylation_sites??'—'}</td><th>Free Cys</th><td>${m.free_cys??'—'}</td></tr>
    </table>
    <details style="margin-bottom:8px"><summary style="font-size:11px;color:var(--muted);cursor:pointer">Percentile ranks vs ${isEngVH?"engineered VH":"VHH clinical"} reference</summary>
      <table class="kv-table" style="font-size:11px;margin-top:6px">${pctRows||"<tr><td class='muted'>No percentile data.</td></tr>"}</table>
    </details>
    ${frHtml}
    ${varHtml}`;
}

async function runBsArmVariant(armLabel, origin, origAdi) {
  const seq = (document.getElementById(`bs-var-seq-${armLabel}`)?.value || "").replace(/\s/g,"").toUpperCase();
  const mutLabel = (document.getElementById(`bs-var-mut-${armLabel}`)?.value || "").trim() || "variant";
  const statusEl = document.getElementById(`bs-var-status-${armLabel}`);
  const resultEl = document.getElementById(`bs-var-result-${armLabel}`);
  if (seq.length < 100) { resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">Sequence too short.</div>`; return; }
  statusEl.textContent = "Running…";
  resultEl.innerHTML = "";
  try {
    const res = await apiFetch(apiJoin("cmc/vhh/async"), {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({vhh_sequence:seq, report_format:"html", sdab_origin:origin, run_structure:false, smart_cmc:false, project_name:mutLabel}),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail||`HTTP ${res.status}`); }
    const {job_id} = await res.json();
    let poll, cnt=0;
    while(cnt++ < 60) {
      await new Promise(r=>setTimeout(r,3000));
      const pr = await apiFetch(apiJoin(`jobs/${job_id}`));
      if(!pr.ok) throw new Error(`Poll ${pr.status}`);
      poll = await pr.json();
      statusEl.textContent = `${poll.progress||0}%`;
      if((poll.status||"").match(/done|failed|cancelled/)) break;
    }
    if(!poll || poll.status==="failed") throw new Error(poll?.error||"Failed");
    const vr = poll.result||{}, vm = vr.metrics||{};
    const vAdi = vr.adi_score??null;
    const diff = (origAdi!==null && vAdi!==null) ? (vAdi - origAdi) : null;
    const dc = diff===null?"var(--muted)":diff>=0?"var(--pass)":"var(--fail)";
    const da = diff===null?"—":diff>=0?`▲ +${diff.toFixed(1)}`:`▼ ${diff.toFixed(1)}`;
    resultEl.innerHTML = `<div style="border:1px solid rgba(99,102,241,.4);border-radius:6px;padding:10px;background:rgba(99,102,241,.04)">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <strong>${escapeHtml(mutLabel)}</strong>
        <span style="font-size:10px;padding:2px 6px;border-radius:3px;background:${vr.overall_status==="PASS"?"var(--pass)":vr.overall_status==="FAIL"?"var(--fail)":"var(--warn)"};color:white">${vr.overall_status||"?"}</span>
        <span style="font-size:13px;font-weight:700;color:${dc}">${da}</span>
        <span style="font-size:11px;color:var(--muted)">Gate Score: ${origAdi!==null?origAdi.toFixed(1):"—"} → ${vAdi!==null?vAdi.toFixed(1):"—"}</span>
        ${diff!==null&&diff<0?`<span style="font-size:10px;padding:2px 5px;background:rgba(239,68,68,.12);color:var(--fail);border-radius:3px">Gate Score regression</span>`:""}
      </div>
      <table class="kv-table" style="font-size:11px">
        <tr><th>pI</th><td>${fmt(vm.pI)}</td><th>GRAVY</th><td>${fmt(vm.GRAVY)}</td><th>SAP</th><td>${fmt(vm.SAP_score)}</td></tr>
        <tr><th>Instability</th><td>${fmt(vm.instability_index)}</td><th>Hydro Patch</th><td>${fmt(vm.hydro_patch_max9)}</td><th>Net Charge</th><td>${fmt(vm.net_charge_pH7)}</td></tr>
      </table>
    </div>`;
    statusEl.textContent = "Done.";
  } catch(err) {
    resultEl.innerHTML = `<div style="color:var(--fail);font-size:11px">Error: ${escapeHtml(err.message)}</div>`;
    statusEl.textContent = "";
  }
}

function renderCmcBispecificResult(data, service, demoId) {
  const r = data.result || {};
  const A = r.arm1 || {};
  const B = r.arm2 || {};
  const origin = r.sdab_origin || A.sdab_origin || "camelid_vhh";
  const originDisplayLabel = safeSdabOriginLabel(origin);
  const referenceDisplayLabel = safeSdabReferenceLabel(origin);
  const smartRequested = !!(r.smart_cmc_run || A.smart_cmc_run || B.smart_cmc_run);
  _bsSuggRegistry = [];
  window._lastBsCmcResult = {arm1: A, arm2: B};   // baseline for batch verify
  const fusionStatus = (r.overall_status || "DONE").toUpperCase();
  const flagsHtml = (r.flags || []).length ? (r.flags||[]).map(f=>`<div>• ${escapeHtml(f)}</div>`).join("") : `<span class="muted">None</span>`;
  const jobIdStrBs = (data.job_id || "").toString();
  const bsName = (r.project_name || "").toString().trim();
  const bsProjRow = bsName && bsName !== jobIdStrBs && bsName.toLowerCase() !== "demo"
    ? `<tr><th>Project / construct ID</th><td class="mono">${escapeHtml(bsName)}</td></tr>` : "";

  // Fusion matrix top rows
  const fmRows = (r.fusion_matrix_top || []).slice(0,5).map(row =>
    `<tr><td class="mono">${escapeHtml(row.linker||"")}</td><td>${fmt(row.fusion_pi)}</td>
     <td style="color:${row.pi_flag==="pass"?"var(--pass)":row.pi_flag==="warn"?"var(--warn)":"var(--fail)"}">${row.pi_flag?.toUpperCase()||"—"}</td></tr>`
  ).join("");

  setOutput(`
    ${formatRunMetadataHtml(service, data, [
      bsProjRow,
      `<tr><th>Service</th><td>Bispecific VHH-linker-VHH CMC</td></tr>`,
      `<tr><th>Reference</th><td>${escapeHtml(referenceDisplayLabel)}</td></tr>`,
    ].filter(Boolean))}

    <section class="result-panel" style="border-color:rgba(167,139,250,.35)">
      <div class="result-title" style="background:rgba(167,139,250,.05)">
        <strong style="color:var(--credit)">Fusion Construct Summary</strong>
        <span class="run-status ${badgeTone(fusionStatus)}">${fusionStatus}</span>
      </div>
      <div class="result-body">
        <div class="metric-grid">
          ${metricHtml("Fusion pI", fmt(r.fusion_pI), valueOutOfRange(r.fusion_pI, 4.5, 9.0) ? "warn" : "ok")}
          ${metricHtml("Fusion GRAVY", fmt(r.fusion_GRAVY), (r.fusion_GRAVY||0) > -0.1 ? "warn" : "ok")}
          ${metricHtml("Fusion Instability", fmt(r.fusion_instability), (r.fusion_instability||0) > 50 ? "warn" : "ok")}
          ${metricHtml("Arm pI Δ", fmt(r.pI_delta), (r.pI_delta||0) > 1.5 ? "warn" : "ok")}
          ${metricHtml("ER Expression Score", fmt(r.er_expression_score), (r.er_expression_score||0) < 0.5 ? "warn" : "ok")}
        </div>
        <table class="kv-table" style="margin-top:10px">
          <tr><th>Selected linker</th><td class="mono">${escapeHtml(r.recommended_linker||"—")}</td></tr>
          <tr><th>Linker rationale</th><td style="font-size:11px">${escapeHtml(r.linker_rationale||"—")}</td></tr>
          <tr><th>Flags</th><td>${flagsHtml}</td></tr>
        </table>
        ${fmRows ? `<div style="margin-top:10px">
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:4px">Fusion pI Matrix (top 5 linkers)</div>
          <table class="kv-table" style="font-size:11px">
            <tr><th>Linker</th><th>Fusion pI</th><th>Status</th></tr>${fmRows}
          </table></div>` : ""}
      </div>
    </section>

    <section class="result-panel">
      <div class="result-title">
        <strong>Arm 1 — ${escapeHtml(r.arm1_target || "Target A")}</strong>
        <span class="run-status ${badgeTone(A.overall_status||"DONE")}">${A.overall_status||"—"}</span>
      </div>
      <div class="result-body">${_renderBsArm(A, "arm1", r.arm1_target||"A", origin, data.job_id||"", smartRequested)}</div>
    </section>

    <section class="result-panel">
      <div class="result-title">
        <strong>Arm 2 — ${escapeHtml(r.arm2_target || "Target B")}</strong>
        <span class="run-status ${badgeTone(B.overall_status||"DONE")}">${B.overall_status||"—"}</span>
      </div>
      <div class="result-body">${_renderBsArm(B, "arm2", r.arm2_target||"B", origin, data.job_id||"", smartRequested)}</div>
    </section>
  `);

  const A_m = A.metrics || {};
  const B_m = B.metrics || {};
  updateResultRail({
    status: fusionStatus,
    summaryTitle: "Bispecific VHH CMC completed",
    summaryText: `${(DEMOS[demoId]||{}).label||demoId}: fusion pI ${fmt(r.fusion_pI)} · linker ${r.recommended_linker||"—"}.`,
    metrics: [
      {label:"Fusion pI", value:fmt(r.fusion_pI), tone:valueOutOfRange(r.fusion_pI,4.5,9.0)?"warn":"ok"},
      {label:"pI Δ", value:fmt(r.pI_delta), tone:(r.pI_delta||0)>1.5?"warn":"ok"},
      {label:"Arm1 Gate Score", value:A.adi_score!==null&&A.adi_score!==undefined?A.adi_score.toFixed(1):"—", tone:adiTone(A.adi_score)},
      {label:"Arm2 Gate Score", value:B.adi_score!==null&&B.adi_score!==undefined?B.adi_score.toFixed(1):"—", tone:adiTone(B.adi_score)},
      {label:"Arm1 SAP", value:fmt(A_m.SAP_score), tone:(A.risk_flags||{}).SAP_score==="FAIL"?"fail":(A.risk_flags||{}).SAP_score==="WARN"?"warn":"ok"},
      {label:"Arm2 SAP", value:fmt(B_m.SAP_score), tone:(B.risk_flags||{}).SAP_score==="FAIL"?"fail":(B.risk_flags||{}).SAP_score==="WARN"?"warn":"ok"},
    ],
    recommendation: fusionStatus === "PASS"
      ? "Both arms PASS. Review per-arm WARN flags and fusion pI matrix in the HTML report before final construct selection."
      : "One or both arms have critical flags or fusion pI is out of range. Review §FR suggestions and linker alternatives.",
    artifacts: buildArtifacts(data),
    metadata: [
      {label:"Reference", value:referenceDisplayLabel},
      {label:"Origin", value:originDisplayLabel},
      {label:"Job ID", value:data.job_id||"—", mono:true},
      {label:"Elapsed", value:data.elapsed_sec?`${data.elapsed_sec}s`:"—"},
      {label:"Analysis Version", value:service.analysisVersion, mono:true},
    ],
  });
}

// ── VH to VHH Conversion ──────────────────────────────────────────────────────

async function runVhToVhh(service) {
  const seq = normalizeSeq(document.getElementById("vh2vhh-seq").value);
  const demoId = document.getElementById("vh2vhh-demo").value;
  const source = document.getElementById("vh2vhh-source").value;
  const errors = [validateSeq(seq, "VH", 100, 140)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the VH sequence input.", artifacts:[], metadata:[]});
    return;
  }
  const vh2vhhSeqName = (document.getElementById("vh2vhh-name") && document.getElementById("vh2vhh-name").value.trim()) || "";
  const useAsync = document.getElementById("vh2vhh-async") && document.getElementById("vh2vhh-async").checked;
  const body = JSON.stringify({ vh_sequence: seq, source_class: source, demo_id: demoId, ...(vh2vhhSeqName && { sequence_name: vh2vhhSeqName }) });
  if (useAsync) {
    setRunning("Submitting background VH→VHH conversion job…", 0);
  } else {
    setRunning("Running VH→VHH conversion (single HTTP request style — polling silently)…");
  }
  setOutput("");
  window.__activeAsyncAbort = false;
  try {
    // Submit to async endpoint — returns job_id immediately
    const startRes = await apiFetch(apiJoin("vh_to_vhh/async"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body,
    });
    const start = await startRes.json();
    if (!startRes.ok) throw new Error(start.detail || JSON.stringify(start));
    const jobId = start.job_id;
    window.__activeAsyncJobId = jobId;
    setAsyncJobCancelButtonsVisible(true);
    if (useAsync) setRunning(`VH→VHH job ${jobId} — queued — polling…`, 0);

    // Poll /jobs/{job_id}
    for (let i = 0; i < 600; i++) {
      await sleep(2000);
      if (window.__activeAsyncAbort) {
        setAsyncJobCancelButtonsVisible(false);
        clearRunning();
        setOutput(errorPanel("Job cancelled by user."));
        return;
      }
      const pr = await apiFetch(apiJoin(`jobs/${jobId}`));
      if (!pr.ok) throw new Error(`Poll failed: ${pr.status}`);
      const poll = await pr.json();
      const st = (poll.status || "").toLowerCase();
      const pct = poll.progress != null ? Number(poll.progress) : null;
      const note = (poll.progress_note && String(poll.progress_note).trim()) || st;
      if (useAsync) {
        setRunning(`VH→VHH ${jobId} — ${note}`, pct);
      }

      if (st === "done") {
        setAsyncJobCancelButtonsVisible(false);
        window.__activeAsyncJobId = null;
        clearRunning();
        renderVhToVhhResult(poll, service, demoId);
        return;
      }
      if (st === "failed" || st === "cancelled") {
        setAsyncJobCancelButtonsVisible(false);
        window.__activeAsyncJobId = null;
        clearRunning();
        const errMsg = poll.error || poll.progress_note || (st === "cancelled" ? "Job cancelled." : "VH→VHH job failed.");
        setOutput(errorPanel(errMsg));
        updateResultRail({status:"FAIL", summaryTitle: st === "cancelled" ? "Job cancelled" : "VH→VHH conversion failed", summaryText:errMsg, metrics:[], recommendation: st === "cancelled" ? "Job aborted. Resubmit when ready." : "Check server logs.", artifacts:[], metadata:[{label:"Job ID", value:jobId, mono:true}]});
        return;
      }
    }
    throw new Error("VH→VHH job timed out after polling limit.");
  } catch (err) {
    setAsyncJobCancelButtonsVisible(false);
    window.__activeAsyncJobId = null;
    clearRunning();
    setOutput(errorPanel(err.message));
    updateResultRail({status:"FAIL", summaryTitle:"VH→VHH conversion failed", summaryText:err.message, metrics:[], recommendation:"Inspect the returned error and rerun.", artifacts:[], metadata:[]});
  }
}

function renderVhToVhhResult(data, service, demoId) {
  const r = data.result || {};

  // ── feasibility verdict ───────────────────────────────────────────────────
  const verdict = r.feasibility_verdict || "UNKNOWN";
  const isBlocker    = verdict === "NOT_FEASIBLE" || (r.feasibility_risk === "HIGH" && r.primary_blocker);
  const isConditional = !isBlocker && (verdict === "CONDITIONAL" || r.feasibility_risk === "MEDIUM");
  const isProceed    = !isBlocker && !isConditional;
  const verdictTone  = isBlocker ? "fail" : isConditional ? "warn" : "ok";

  const verdictBannerColor  = isBlocker ? "var(--fail)" : isConditional ? "var(--warn)" : "var(--pass)";
  const verdictBannerBg     = isBlocker ? "rgba(220,38,38,0.12)" : isConditional ? "rgba(217,119,6,0.12)" : "rgba(133,153,0,0.12)";
  const verdictIcon         = isBlocker ? "❌" : isConditional ? "⚠" : "✅";
  const verdictLabel        = isBlocker ? "NOT RECOMMENDED — Redesign required"
                            : isConditional ? "CONDITIONAL — Modification needed before synthesis"
                            : "PROCEED — Conversion design complete";

  // ── conversion advisory ──────────────────────────────────────────────────
  const adv = r.conversion_advisory || null;
  const primaryBlocker = r.primary_blocker || null;

  // Build advisory block (shown at top for blocker/conditional)
  const advSevClass = adv.severity === "high" ? "severity-high" : "severity-medium";
  const advTopHtml = adv ? `
    <div class="conversion-advisory-card ${advSevClass}" role="status">
      <div class="conversion-advisory-title">${adv.severity === "high" ? "❌" : "⚠"} ${escapeHtml(adv.title || "")}</div>
      <div class="conversion-advisory-detail">${escapeHtml(adv.detail || "")}</div>
      <div class="conversion-advisory-action"><strong>Required action:</strong> ${escapeHtml(adv.path_forward || "")}</div>
      ${adv.offline_service ? `<div class="conversion-advisory-service">Available service: <strong>${escapeHtml(adv.offline_service)}</strong>${adv.estimated_time ? ` · ${escapeHtml(adv.estimated_time)}` : ""}</div>` : ""}
    </div>` : (primaryBlocker ? `
    <div style="background:rgba(220,38,38,0.08);border:1px solid var(--fail);border-radius:8px;padding:12px 14px;margin-top:10px">
      <div style="font-size:12px;font-weight:700;color:var(--fail);margin-bottom:4px">❌ Primary blocker detected</div>
      <div style="font-size:12px;color:var(--text)">${escapeHtml(primaryBlocker)}</div>
    </div>` : "");

  // ── feasibility notes ────────────────────────────────────────────────────
  const notes = (r.feasibility_notes || []).map(n => `<li style="font-size:12px;margin-bottom:3px">${escapeHtml(n)}</li>`).join("");
  const glycan = r.glycan_dependency || null;
  const glycanHtml = glycan ? `
    <section class="result-panel">
      <div class="result-title"><strong>V1.7 Glycan-Dependent Epitope Risk</strong><span class="run-status ${glycan.penalty_factor < 1 ? 'warn' : 'ok'}" style="font-size:10px;margin-left:8px">${escapeHtml(glycan.risk_level || "NONE")}</span></div>
      <div class="result-body">
        <div class="metric-grid">
          ${metricHtml("Penalty factor", fmt(glycan.penalty_factor, 2), glycan.penalty_factor < 1 ? "warn" : "ok")}
          ${metricHtml("Known glycan contact", glycan.known_glycan_contact ? "Yes" : "No", glycan.known_glycan_contact ? "warn" : "ok")}
          ${metricHtml("CDR-H3 motifs", (glycan.glycan_motifs_in_cdr3 || []).join(", ") || "None", (glycan.glycan_motifs_in_cdr3 || []).length ? "warn" : "ok")}
          ${metricHtml("VL decoupling", glycan.vl_decoupling_risk || "—", glycan.vl_decoupling_risk === "HIGH" ? "warn" : "ok")}
        </div>
        <p style="font-size:11px;color:var(--muted);margin-top:8px">This layer is applied after V1.5/V1.6 evidence. Penalty factors below 1.0 are multiplied into the final success probability.</p>
      </div>
    </section>` : "";

  // ── structure helpers ────────────────────────────────────────────────────
  const plddtIn  = r.input_plddt;
  const plddtCv  = r.converted_plddt;
  const plddtTone = plddtCv == null ? "" : plddtCv < 60 ? "fail" : plddtCv < 70 ? "warn" : "ok";
  const cdrRmsd  = r.cdr_rmsd || {};
  const rmsdKeys = Object.keys(cdrRmsd).filter(k => typeof cdrRmsd[k] === "number" && !k.includes("linear"));
  const maxRmsd  = rmsdKeys.length ? Math.max(...rmsdKeys.map(k => cdrRmsd[k])) : null;
  const rmsdRows = rmsdKeys.map(k =>
    `<tr><th>${k} Cα RMSD</th><td class="${cdrRmsd[k] > 2.0 ? 'warn-text' : ''}">${fmt(cdrRmsd[k], 2)} Å</td></tr>`
  ).join("") || "<tr><td colspan='2' class='muted'>Structural conformation not computed.</td></tr>";

  // ── mini-CMC ────────────────────────────────────────────────────────────
  const mc = r.mini_cmc || {};
  const mcFlags = mc.flags || [];
  const mcFlagHtml = mcFlags.length
    ? `<span style="color:var(--warn);font-size:11px">⚠ ${mcFlags.join(" · ")}</span>`
    : `<span style="color:var(--ok);font-size:11px">✓ Pass</span>`;

  // ── mutations ────────────────────────────────────────────────────────────
  const mutApplied = (r.mutations_applied || []);
  const mutCanon   = (r.already_canonical || []);
  const isGraftStrategy = (r.selected_strategy || "").includes("graft");
  const mutRows = mutApplied.length
    ? mutApplied.map(m => `<tr><th>Engineering</th><td class="mono">${escapeHtml(m)}</td></tr>`).join("")
    : isGraftStrategy
      ? "<tr><td colspan='2' class='muted'>Proprietary Scaffold Integration (PSI): Framework derived from clinical-grade VHH library; hallmark positions pre-optimized.</td></tr>"
      : "<tr><td colspan='2' class='muted'>No additional engineering required (positions already match proprietary canonical standards).</td></tr>";
  const canonRows = mutCanon.slice(0, 5).map(a => `<tr><th>Canonical match</th><td class="mono">${escapeHtml(a)}</td></tr>`).join("");

  const seqName = (r.sequence_name && String(r.sequence_name).trim()) || "";

  try {
    if (r.converted_sequence) {
      sessionStorage.setItem("insynbio_last_humanized_vhh", String(r.converted_sequence));
      sessionStorage.setItem("insynbio_last_humanized_name", String(r.sequence_name || vh2vhhSeqName || ""));
      sessionStorage.setItem("insynbio_last_humanization_kind", "vhh");
      sessionStorage.removeItem("insynbio_last_humanized_vh");
      sessionStorage.removeItem("insynbio_last_humanized_vl");
    }
  } catch (e) {}

  // ── sequence section (suppressed for hard BLOCKER) ───────────────────────
  const seqSection = isBlocker ? `
    <section class="result-panel" style="opacity:0.5;pointer-events:none">
      <div class="result-title"><strong>Designed VHH Sequence</strong> <span style="font-size:11px;color:#dc2626;font-weight:700">— Not available (blocker present)</span></div>
      <div class="result-body"><p style="font-size:12px;color:var(--muted)">A VHH design cannot be recommended until the blocker above is resolved. Contact InSynBio for redesign support.</p></div>
    </section>` : `
    <section class="result-panel">
      <div class="result-title"><strong>Designed VHH Sequence</strong></div>
      <div class="result-body">
        <div class="seq-box"><div class="label">Input VH (${(r.input_sequence||"").length} aa)</div><pre>${escapeHtml(r.input_sequence||"")}</pre></div>
        <div class="seq-box" style="margin-top:10px"><div class="label">Converted VHH — best candidate (${(r.converted_sequence||"").length} aa)</div><pre>${_highlightMutations(r.input_sequence||"", r.converted_sequence||"")}</pre></div>
        <p style="font-size:11px;color:var(--muted);margin-top:8px">Mutated positions shown in <span style="color:#c9a227;font-weight:700">amber</span>. Verify activity by SPR/BLI before advancing.</p>
        <div class="button-row" style="margin-top:10px;flex-wrap:wrap">
          <button type="button" class="btn" style="border-color:var(--accent);color:var(--accent)" onclick="goToVhhCmcWithLastHumanization()">Run VHH CMC Snapshot →</button>
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaWithLastHumanization(true)">cDNA Optimization (VHH) →</button>
        </div>
      </div>
    </section>`;

  setOutput(`
    ${formatRunMetadataHtml(service, data, [
      seqName ? `<tr><th>Sequence / project ID</th><td class="mono">${escapeHtml(seqName)}</td></tr>` : "",
      `<tr><th>Standard</th><td class="mono">${escapeHtml(r.vh_to_vhh_standard_version || "V1.8.17")} · Console ${escapeHtml(r.vh_to_vhh_console_deployment_branch || "V1.8.17.IGHV3")}</td></tr>`,
    ].filter(Boolean))}
    <section class="result-panel" style="border-left:4px solid ${verdictBannerColor}">
      <div class="result-title">
        <strong>§0 Feasibility & Mechanism Module</strong>
        <span class="run-status ${verdictTone}" style="font-size:12px">${verdictIcon} ${escapeHtml(verdictLabel)}</span>
      </div>
      <div class="result-body">
        ${seqName ? `<p style="font-size:12px;margin:0 0 8px;color:var(--muted)"><strong>Sequence:</strong> <span class="mono">${escapeHtml(seqName)}</span></p>` : ""}
        <div style="background:${verdictBannerBg};border-radius:6px;padding:10px 13px;margin-bottom:10px">
          <div style="font-size:13px;font-weight:700;color:${verdictBannerColor}">${verdictIcon} ${escapeHtml(verdictLabel)}</div>
          ${primaryBlocker ? `<div style="font-size:12px;color:#94a3b8;margin-top:4px">Primary blocker: ${escapeHtml(primaryBlocker)}</div>` : ""}
        </div>
        ${advTopHtml}
        ${notes ? `<ul style="padding-left:16px;margin:10px 0 0">${notes}</ul>` : ""}
      </div>
    </section>
    ${(() => {
      const ev = r.expressibility_verdict || {};
      const evVerdict = ev.verdict || "INCOMPLETE";
      const evCriteria = ev.criteria || [];
      const evColor = { EXCELLENT:"#22c55e", PASS:"#4ade80", WARN:"#fbbf24", FAIL:"#f87171", INCOMPLETE:"#94a3b8" }[evVerdict] || "#94a3b8";
      const evBg    = { EXCELLENT:"rgba(34,197,94,0.08)", PASS:"rgba(74,222,128,0.06)", WARN:"rgba(251,191,36,0.08)", FAIL:"rgba(248,113,113,0.10)", INCOMPLETE:"rgba(148,163,184,0.06)" }[evVerdict] || "transparent";
      const evIcon  = { EXCELLENT:"✦", PASS:"✓", WARN:"⚠", FAIL:"✗", INCOMPLETE:"–" }[evVerdict] || "–";
      const criteriaHtml = evCriteria.map(c => {
        const tone = { PASS:"#4ade80", WARN:"#fbbf24", FAIL:"#f87171", EXCELLENT:"#22c55e", UNKNOWN:"#94a3b8" }[c.status] || "#94a3b8";
        const icon = { PASS:"✓", WARN:"⚠", FAIL:"✗", EXCELLENT:"✦", UNKNOWN:"–" }[c.status] || "–";
        const valStr = c.value != null ? String(c.value) : "—";
        return `<tr><th style="width:120px">${escapeHtml(c.metric)}</th><td><span style="color:${tone};font-weight:700;margin-right:6px">${icon}</span><span class="mono" style="font-size:12px">${escapeHtml(valStr)}</span> <span style="font-size:11px;color:#94a3b8">${escapeHtml(c.reason||"")}</span></td></tr>`;
      }).join("");
      return `
    <section class="result-panel" style="border-left:4px solid ${evColor}">
      <div class="result-title">
        <strong>§0.1 Expressibility Verdict</strong>
        <span class="run-status ${evVerdict==="FAIL"?"fail":evVerdict==="WARN"?"warn":evVerdict==="INCOMPLETE"?"warn":"ok"}" style="font-size:12px">${evIcon} ${evVerdict}</span>
      </div>
      <div class="result-body">
        <div style="background:${evBg};border-radius:6px;padding:9px 12px;margin-bottom:10px;font-size:12px;font-weight:600;color:${evColor}">${evIcon} ${evVerdict}${evVerdict==="FAIL" ? " — Sequence does not meet expressibility / secretability / stability criteria" : evVerdict==="EXCELLENT" ? " — Meets all three-dimensional expressibility criteria" : ""}</div>
        ${criteriaHtml ? `<table class="kv-table">${criteriaHtml}</table>` : '<p style="font-size:12px;color:var(--muted)">Expressibility gate not computed (structure prediction required for compactness).</p>'}
        <p style="font-size:11px;color:var(--muted);margin-top:8px">Three-dimensional gate: CDR3 length + CDR3 compactness + AbNatiV Δ. FAIL = sequence not publishable as complete deliverable.</p>
      </div>
    </section>`;
    })()}
    <section class="result-panel">
      <div class="result-title"><strong>§1 Local Sequence Comparison (FR / CDR)</strong></div>
      <div class="result-body" style="padding:0">
        ${(() => {
          const sc2 = r.sequence_comparison || {};
          let regions = sc2.regions || [];
          const donorSeq = r.input_sequence || "";
          const humanSeq = r.converted_sequence || "";
          if (!donorSeq || !humanSeq) return "<p style='padding:12px;color:var(--muted);font-size:12px'>Not available.</p>";

          function splitImgtVhh(seq) {
            const s = (seq || "").toUpperCase();
            const len = s.length;
            const fr4start = Math.max(104, len - 11);
            const cdr3end  = fr4start;
            const cdr3start = Math.min(104, cdr3end - 4);
            return [
              { region: "FR1",  seq: s.slice(0, 26),         is_cdr: false },
              { region: "CDR1", seq: s.slice(26, 38),        is_cdr: true  },
              { region: "FR2",  seq: s.slice(38, 55),        is_cdr: false },
              { region: "CDR2", seq: s.slice(55, 65),        is_cdr: true  },
              { region: "FR3",  seq: s.slice(65, cdr3start), is_cdr: false },
              { region: "CDR3", seq: s.slice(cdr3start, cdr3end), is_cdr: true },
              { region: "FR4",  seq: s.slice(cdr3end),       is_cdr: false },
            ];
          }

          if (!regions.length) {
            const dParts = splitImgtVhh(donorSeq);
            const hParts = splitImgtVhh(humanSeq);
            regions = dParts.map((dp, i) => {
              const ds = dp.seq, hs = hParts[i].seq;
              const nMut = Math.min(ds.length, hs.length) - [...ds].filter((c,j) => c === hs[j]).length
                           + Math.abs(ds.length - hs.length);
              return { region: dp.region, donor_seq: ds, humanized_seq: hs,
                       is_cdr: dp.is_cdr, n_mutations: dp.is_cdr ? 0 : nMut,
                       identical: ds === hs };
            });
          }

          const totalFrMut = sc2.total_fr_mutations != null ? sc2.total_fr_mutations
            : regions.filter(r2 => !r2.is_cdr).reduce((s, r2) => s + (r2.n_mutations || 0), 0);

          const regionRows = regions.map(reg => {
            const isCdr = reg.is_cdr;
            const ds = reg.donor_seq || "";
            const hs = reg.humanized_seq || "";
            const maxLen = Math.max(ds.length, hs.length);

            let donorHtml = "", humHtml = "";
            for (let i = 0; i < maxLen; i++) {
              const da = ds[i] || "", ha = hs[i] || "";
              if (da === ha) {
                const ch = escapeHtml(da || ha);
                donorHtml += ch;
                humHtml   += ch;
              } else {
                donorHtml += `<b style="color:#c0392b">${escapeHtml(da||"·")}</b>`;
                humHtml   += `<b style="color:#16a34a">${escapeHtml(ha||"·")}</b>`;
              }
            }

            const nMut = reg.n_mutations || 0;
            const statusText = isCdr ? "CDR" : nMut === 0 ? "—" : `${nMut} change${nMut>1?"s":""}`;
            const statusColor = isCdr ? "#92400e" : nMut === 0 ? "var(--muted)" : "var(--pass)";
            const rowBg = isCdr ? "rgba(254,252,232,0.5)" : "transparent";

            return `<tr style="border-bottom:1px solid var(--line);background:${rowBg}">
              <td style="padding:5px 12px;font-size:12px;font-weight:700;color:var(--text);white-space:nowrap">${reg.region}</td>
              <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:var(--text)">${donorHtml}</td>
              <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:var(--text)">${humHtml}</td>
              <td style="padding:5px 12px;font-size:11px;font-weight:600;color:${statusColor};text-align:center;white-space:nowrap">${statusText}</td>
            </tr>`;
          }).join("");

          return `
            <table style="width:100%;border-collapse:collapse;font-family:sans-serif;margin-bottom:8px">
              <thead>
                <tr style="background:var(--panel-2);border-bottom:1px solid var(--line-2)">
                  <th style="padding:7px 12px;font-size:12px;font-weight:700;color:var(--muted);text-align:left;width:60px">Region</th>
                  <th style="padding:7px 12px;font-size:12px;font-weight:700;color:var(--muted);text-align:left">Donor VH</th>
                  <th style="padding:7px 12px;font-size:12px;font-weight:700;color:var(--muted);text-align:left">Converted VHH</th>
                  <th style="padding:7px 12px;font-size:12px;font-weight:700;color:var(--muted);text-align:center;width:100px">Status</th>
                </tr>
              </thead>
              <tbody>${regionRows}</tbody>
            </table>
            <div style="padding:0 12px 10px">
              <span style="font-size:11px;color:var(--muted);font-weight:700;margin-right:10px">Total FR mutations: ${totalFrMut}</span>
              <span style="font-size:11px;color:var(--muted)">Framework mutations restore VH-VL interface compatibility for single-domain display, alongside proprietary surface-patch modifications governed by structural gating. Specific mutation paths depend on the source VH family and baseline developability profile.</span>
              ${r.conversion_error ? `<div style="color:var(--fail);font-size:11px;margin-top:4px">Mutation engine warning: ${escapeHtml(r.conversion_error)}</div>` : ""}
            </div>
          `;
        })()}
      </div>
    </section>
    ${isBlocker ? `
    <section class="result-panel" style="opacity:0.5;pointer-events:none">
      <div class="result-title"><strong>§2 Global Sequence (Designed VHH)</strong> <span style="font-size:11px;color:#dc2626;font-weight:700">— Not available (blocker present)</span></div>
      <div class="result-body"><p style="font-size:12px;color:var(--muted)">A VHH design cannot be recommended until the blocker above is resolved. Contact InSynBio for redesign support.</p></div>
    </section>` : `
    <section class="result-panel">
      <div class="result-title"><strong>§2 Global Sequence (Designed VHH)</strong></div>
      <div class="result-body">
        <div class="seq-box"><div class="label">Input VH (${(r.input_sequence||"").length} aa)</div><pre>${escapeHtml(r.input_sequence||"")}</pre></div>
        <div class="seq-box" style="margin-top:10px"><div class="label">Converted VHH — best candidate (${(r.converted_sequence||"").length} aa)</div><pre>${_highlightMutations(r.input_sequence||"", r.converted_sequence||"")}</pre></div>
        <p style="font-size:11px;color:var(--muted);margin-top:8px">Mutated positions shown in <span style="color:#c9a227;font-weight:700">amber</span>. Verify activity by SPR/BLI before advancing.</p>
        <div class="button-row" style="margin-top:10px;flex-wrap:wrap">
          <button type="button" class="btn" style="border-color:var(--accent);color:var(--accent)" onclick="goToVhhCmcWithLastHumanization()">Run VHH CMC Snapshot →</button>
          <button type="button" class="btn" style="border-color:#22d3ee;color:#22d3ee" onclick="goToCdnaWithLastHumanization(true)">cDNA Optimization (VHH) →</button>
        </div>
      </div>
    </section>`}
    <section class="result-panel">
      <div class="result-title"><strong>§3 Mini-CMC Index</strong><span style="margin-left:8px">${mcFlagHtml}</span></div>
      <div class="result-body">
        <div class="metric-grid recheck-row-4">
          ${mc.pI != null ? metricHtml("pI", fmt(mc.pI, 2), (mc.pI>8.5||mc.pI<5.5)?"warn":"ok", "Theoretical isoelectric point. Ideal range: 5.5–8.5.") : ""}
          ${mc.GRAVY != null ? metricHtml("GRAVY", fmt(mc.GRAVY, 3), mc.GRAVY < -0.50 ? "warn" : "ok", "Grand average of hydropathy. Lower is more soluble.") : ""}
          ${mc.instability_index != null ? metricHtml("Instability Index", fmt(mc.instability_index, 1), mc.instability_index > 40 ? "warn" : "ok", "Guruprasad instability index. <40 is considered stable.") : ""}
          ${mc.net_charge_pH7 != null ? metricHtml("Net Charge", fmt(mc.net_charge_pH7, 1), "", "Approximate net charge at pH 7.") : ""}
        </div>
        ${(r.cmc_flags||[]).filter(f => f.includes("FAIL") || f.includes("HIGH_RISK") || f.includes("WARN")).length ? `
        <div style="margin-top:10px;padding:10px;background:rgba(230,168,23,0.08);border-radius:6px;border-left:3px solid var(--warn)">
          <div style="font-size:11px;font-weight:600;margin-bottom:5px;color:#cbd5e1">CMC flags:</div>
          ${(r.cmc_flags||[]).filter(f => f.includes("FAIL") || f.includes("HIGH_RISK") || f.includes("WARN")).map(f => {
            const isFail = f.includes("FAIL") || f.includes("HIGH_RISK");
            return `<div style="font-size:11px;color:${isFail ? '#f87171' : '#fbbf24'};margin-bottom:3px;line-height:1.4">${isFail ? '❌' : '⚠'} ${escapeHtml(f)}</div>`;
          }).join("")}
        </div>` : ""}
        <p style="font-size:11px;color:var(--muted);margin-top:8px">VHH clinical QA: <strong>${escapeHtml(r.cmc_status||"—")}</strong>${r.cmc_clinical_score!=null ? " · score " + fmt(r.cmc_clinical_score,3) : ""}.</p>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>§4 CDR Index</strong></div>
      <div class="result-body">
        <div class="metric-grid recheck-row-5">
          ${metricHtml("CDR2 Length", `${r.cdr2_length ?? "—"} aa`, (r.cdr2_length||0) >= 17 ? "warn" : "ok", "CDR-H2 loop length. ≥17aa may require scaffolding optimization.")}
          ${metricHtml("CDR3 Length", `${r.cdr3_length ?? "—"} aa`, (r.cdr3_length||0) <= 4 ? "fail" : (r.cdr3_length||0) >= 17 ? "warn" : "ok", "CDR-H3 loop length. Extreme lengths pose structural or expressibility risks.")}
          ${mc.cdr3_compactness != null ? metricHtml("Compactness", `${fmt(mc.cdr3_compactness, 2)} Å`, mc.cdr3_compactness > 7.5 ? "fail" : mc.cdr3_compactness > 6.5 ? "warn" : "ok", "CDR-H3 compactness. >6.5 Å indicates extended loops prone to aggregation.") : ""}
          ${glycan ? metricHtml("Glycan Contact", glycan.known_glycan_contact ? "Yes" : "No", glycan.known_glycan_contact ? "warn" : "ok", "Known glycan contacts in CDR.") : ""}
          ${glycan ? metricHtml("Glycan Motifs", (glycan.glycan_motifs_in_cdr3 || []).join(", ") || "None", (glycan.glycan_motifs_in_cdr3 || []).length ? "warn" : "ok", "Glycan-dependent motifs in CDR3.") : ""}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>§5 Humanization &amp; Camelization Index</strong></div>
      <div class="result-body">
        <div class="metric-grid recheck-row-4">
          ${mc.hpr_index != null ? metricHtml("HPR Index", fmt(mc.hpr_index, 3), mc.hpr_index < 0.65 ? "warn" : "ok", "Human Peptide Repertoire index. ≥0.65 acceptable. Higher score supports better local humanness.") : ""}
          ${r.best_abnativ_delta != null ? metricHtml("AbNatiV Δ", (r.best_abnativ_delta >= 0 ? "+" : "") + fmt(r.best_abnativ_delta, 3), r.best_abnativ_delta < -0.074 ? "fail" : r.best_abnativ_delta < 0 ? "warn" : "ok", "Change in AbNatiV VHH likelihood score vs donor. Drop tolerated up to −0.074.") : ""}
          ${r.best_abnativ_tier ? metricHtml("AbNatiV VHH Tier", escapeHtml(r.best_abnativ_tier || "—"), "", "Absolute AbNatiV VHH likelihood tier of the converted candidate.") : ""}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>§6 Structure Index (NanoBodyBuilder2)</strong>${r.structure_computed ? "" : '<span class="run-status warn" style="font-size:10px;margin-left:8px">Not computed</span>'}</div>
      <div class="result-body">
        <div class="metric-grid recheck-row-5">
          ${plddtIn != null ? metricHtml("pLDDT (Input)", fmt(plddtIn, 1), plddtIn < 70 ? "warn" : "ok", "Local confidence of input VH model.") : ""}
          ${plddtCv != null ? metricHtml("pLDDT (VHH)", fmt(plddtCv, 1), plddtTone, "Local confidence of converted VHH model.") : ""}
          ${maxRmsd != null ? metricHtml("Global Cα RMSD", `${fmt(maxRmsd, 2)} Å`, maxRmsd > 2.0 ? "warn" : "ok", "Maximum CDR backbone deviation between donor and candidate.") : ""}
        </div>
        <table class="kv-table" style="margin-top:10px">
          ${rmsdRows}
        </table>
        <p style="font-size:11px;color:var(--muted);margin-top:8px">CDR Cα RMSD: input VH vs converted VHH. &gt;2.0 Å indicates CDR conformation shift — SPR/BLI validation recommended. Long CDR-H3 (&gt;14 aa) commonly shows H3 RMSD &gt;3 Å even in successful conversions.</p>
      </div>
    </section>
  `);
  updateResultRail({
    status: isBlocker ? "FAIL" : isConditional ? "WARN" : "PASS",
    summaryTitle: `${service.label} completed`,
    summaryText: `${seqName ? `${seqName} — ` : ""}${verdictIcon} ${verdictLabel}`,
      metrics: [
      ...(seqName ? [{ label: "Name", value: seqName, mono: true }] : []),
      {label:"Feasibility", value: verdict.replace(/_/g," "), tone: verdictTone},
      {label:"Expressibility", value: (r.expressibility_verdict||{}).verdict || "—", tone: {EXCELLENT:"ok",PASS:"ok",WARN:"warn",FAIL:"fail",INCOMPLETE:"warn"}[(r.expressibility_verdict||{}).verdict] || "warn"},
      {label:"AbNatiV Δ", value: r.best_abnativ_delta != null ? fmt(r.best_abnativ_delta, 3) : "—", tone: r.best_abnativ_delta != null && r.best_abnativ_delta < -0.074 ? "fail" : "ok"},
      {label:"CDR3 length", value: r.cdr3_length != null ? `${r.cdr3_length} aa` : "—", tone: (r.cdr3_length||0) < 8 ? "fail" : (r.cdr3_length||0) <= 9 ? "warn" : "ok"},
      {label:"pI", value: mc.pI != null ? fmt(mc.pI, 2) : "—", tone: mc.pI != null && (mc.pI>8.5||mc.pI<5.5) ? "warn" : "ok"},
      {label:"Compactness", value: mc.cdr3_compactness != null ? `${fmt(mc.cdr3_compactness, 2)} Å` : "—", tone: mc.cdr3_compactness > 7.5 ? "fail" : mc.cdr3_compactness > 6.5 ? "warn" : "ok"},
    ],
    recommendation: isBlocker
      ? `${adv ? adv.path_forward : "Redesign required — see advisory above."}`
      : isConditional
        ? "Conditional: resolve flagged issues before synthesis. Review CMC metrics and advisory."
        : "Design complete. Verify activity by SPR/BLI. Run VHH CMC Snapshot for full developability assessment.",
    artifacts: buildArtifacts(data, { htmlZipOnly: true }),
      metadata: [
      ...(demoId ? [{label:"Demo", value: demoId, mono:true}] : []),
      {label:"Job ID", value: data.job_id || "—", mono:true},
      {label:"Elapsed", value: data.elapsed_sec ? `${data.elapsed_sec}s` : "—"},
      {label:"Standard", value: (r.vh_to_vhh_standard_version || "VH→VHH V1.8.17") + (r.vh_to_vhh_console_deployment_branch ? " · Console " + r.vh_to_vhh_console_deployment_branch : ""), mono:true},
    ],
  });
}

// ── Segmentation VH/VL ────────────────────────────────────────────────────────

/** IMGT region keys from server (FR1…FR4) → display labels matching Lite UI */
const IMGT_SERVER_TO_VH = { FR1: "FR-H1", CDR1: "CDR-H1", FR2: "FR-H2", CDR2: "CDR-H2", FR3: "FR-H3", CDR3: "CDR-H3", FR4: "FR-H4" };
const IMGT_SERVER_TO_VL = { FR1: "FR-L1", CDR1: "CDR-L1", FR2: "FR-L2", CDR2: "CDR-L2", FR3: "FR-L3", CDR3: "CDR-L3", FR4: "FR-L4" };

function mapImgtServerRegions(regions, keyMap) {
  const o = {};
  for (const [k, v] of Object.entries(regions || {})) {
    o[keyMap[k] || k] = v;
  }
  return o;
}

/** Client wall-clock for UI + lightweight audit (credits / consent trail). Always English labels. */
function formatClientLocalDateTime() {
  return enUsLocalNow();
}

function newSegmentationRunRecordId() {
  return `run-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Public-facing numbering label. Server path uses ANARCI-class stack; include selected
 * scheme (IMGT / Kabat / Chothia) — do not hard-code IMGT when user chose Chothia/Kabat.
 */
function publicNumberingEngineLabel(engine, scheme) {
  const e = String(engine || "").toLowerCase();
  const sch = String(scheme || "imgt").toLowerCase();
  const schemeLabel = { imgt: "IMGT", kabat: "Kabat", chothia: "Chothia" }[sch] || sch.toUpperCase();
  if (e === "anarci" || e === "anarcii") {
    return `ANARCI-class · server · ${schemeLabel}`;
  }
  return engine || "—";
}

function renderSegGridFromMap(seg) {
  return Object.entries(seg).map(([k, v]) => {
    const isCdr = k.includes("CDR");
    return `<div class="seg-region ${isCdr ? "cdr" : ""}"><div class="rname">${k}</div><div class="rseq">${escapeHtml(v)}</div></div>`;
  }).join("");
}

function formatSchemePosLabel(r) {
  if (!r || r.pos == null) return "—";
  const ins = (r.ins || r.ins_code || "").trim();
  return String(r.pos) + (ins ? ins : "");
}

function renderNumberingTable(rows) {
  if (!rows || !rows.length) {
    return "<p class=\"muted\">Not available (browser Lite).</p>";
  }
  const body = rows.map((r, i) => `<tr><td>${i + 1}</td><td>${escapeHtml(formatSchemePosLabel(r))}</td><td>${escapeHtml(String(r.aa || ""))}</td></tr>`).join("");
  return `<div class="num-wrap"><table class="num-table"><thead><tr><th>i</th><th>Label</th><th>Aa</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function formatSegGermlineHtml(g) {
  if (!g) return "<p class=\"muted\">—</p>";
  if (g.chain === "vhh") return formatSegGermlineVhhHtml(g);
  if (g.error && g.allowed) {
    return `<p class="muted">${escapeHtml(String(g.error))} · ${escapeHtml(g.allowed.join(", "))}</p>`;
  }
  if (g.error) return `<p class="muted">${escapeHtml(String(g.error))}</p>`;
  const vh = g.vh || {};
  const vl = g.vl || {};
  const src = [g.source, g.imgt_species].filter(Boolean).join(" · ") || "—";
  return `
    <table class="kv-table">
      <tr><th>Species / source</th><td>${escapeHtml(src)}</td></tr>
      <tr><th>VH closest IGHV</th><td class="mono">${escapeHtml(vh.closest_vh_germline || "—")}</td></tr>
      <tr><th>VH identity (N-term)</th><td>${escapeHtml(String(vh.vh_germline_identity_pct ?? "—"))}%</td></tr>
      <tr><th>VL closest</th><td class="mono">${escapeHtml(vl.closest_vl_germline || "—")} <span class="muted">(${escapeHtml(vl.vl_germline_locus || "—")})</span></td></tr>
      <tr><th>VL identity</th><td>${escapeHtml(String(vl.vl_germline_identity_pct ?? "—"))}%</td></tr>
    </table>`;
}

/** VHH-only germline block (closest IGHV vs selected species library — same IMGT stack as VH/VL). */
function formatSegGermlineVhhHtml(g) {
  if (!g) return "<p class=\"muted\">—</p>";
  if (g.error && g.allowed) {
    return `<p class="muted">${escapeHtml(String(g.error))} · ${escapeHtml(g.allowed.join(", "))}</p>`;
  }
  if (g.error) return `<p class="muted">${escapeHtml(String(g.error))}</p>`;
  const vh = g.vh || {};
  const src = [g.source, g.imgt_species].filter(Boolean).join(" · ") || "—";
  return `
    <table class="kv-table">
      <tr><th>Species / source</th><td>${escapeHtml(src)}</td></tr>
      <tr><th>Closest IGHV (VHH)</th><td class="mono">${escapeHtml(vh.closest_vh_germline || "—")}</td></tr>
      <tr><th>IGHV identity (N-term)</th><td>${escapeHtml(String(vh.vh_germline_identity_pct ?? "—"))}%</td></tr>
    </table>`;
}

async function runSegmentationVhvl(service) {
  const vh = normalizeSeq(document.getElementById("seg-vh").value);
  const vl = normalizeSeq(document.getElementById("seg-vl").value);
  const demoId = document.getElementById("seg-demo").value;
  const segName = (document.getElementById("seg-name") && document.getElementById("seg-name").value.trim()) || "";
  const scheme = document.getElementById("seg-scheme").value;
  const useServer = document.getElementById("seg-use-server") && document.getElementById("seg-use-server").checked;
  const errors = [validateSeq(vh, "VH", 90, 150), validateSeq(vl, "VL", 85, 135)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the sequence input.", artifacts:[], metadata:[]});
    return;
  }

  await refreshServerWallet();
  syncWalletToState();
  if (!canAffordRun(state.service)) {
    const cost = serviceCreditCost(state.service);
    setOutput(
      errorPanel(
        `Insufficient credits. This run needs ${cost} per service. Current balance: ${state.credits.toLocaleString("en-US")}.` +
          (state.serverMode ? "" : " Sign in for a server trial wallet, or use local demo credits."),
      ),
    );
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Insufficient credits",
      summaryText: `Required ${cost} credits per run.`,
      metrics: [{ label: "Balance", value: state.credits.toLocaleString("en-US"), tone: "fail" }],
      recommendation: "Top up or reset local wallet (see docs).",
      artifacts: [],
      metadata: [{ label: "Credits / run", value: String(cost), mono: true }],
    });
    return;
  }

  let vhSeg;
  let vlSeg;
  let modeNote = "";
  let engineLabel = "browser Lite (heuristic)";
  let elapsedSec = null;
  let germlineData = null;
  let numberingVh = null;
  let numberingVl = null;

  if (!useServer && scheme !== "imgt") {
    setOutput(errorPanel("Kabat/Chothia: enable Server numbering, or use IMGT."));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Server required",
      summaryText: `${scheme.toUpperCase()} requires the API.`,
      metrics: [],
      recommendation: "Enable Server numbering or select IMGT.",
      artifacts: [],
      metadata: [{ label: "Scheme", value: scheme, mono: true }],
    });
    return;
  }

  if (useServer) {
    const schemeRun = { imgt: "IMGT", kabat: "Kabat", chothia: "Chothia" }[scheme] || scheme.toUpperCase();
    setRunning(`${schemeRun} (server)…`);
    setOutput("");
    try {
      const res = await apiFetch(apiJoin("annotate/vh_vl"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vh_sequence: vh,
          vl_sequence: vl,
          scheme,
          species: (document.getElementById("seg-species") && document.getElementById("seg-species").value) || "mouse",
          include_germline: !(document.getElementById("seg-no-germline") && document.getElementById("seg-no-germline").checked),
        }),
      });
      const data = await res.json();
      clearRunning();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
      vhSeg = mapImgtServerRegions(data.vh_regions, IMGT_SERVER_TO_VH);
      vlSeg = mapImgtServerRegions(data.vl_regions, IMGT_SERVER_TO_VL);
      engineLabel = publicNumberingEngineLabel(data.engine, data.scheme || scheme);
      elapsedSec = data.elapsed_sec;
      modeNote = `<p class="muted" style="margin-bottom:12px">${(data.scheme || scheme).toUpperCase()} · ${elapsedSec != null ? `${elapsedSec}s` : "ok"}</p>`;
      germlineData = data.germline != null ? data.germline : null;
      numberingVh = Array.isArray(data.vh_numbering) ? data.vh_numbering : null;
      numberingVl = Array.isArray(data.vl_numbering) ? data.vl_numbering : null;
      const spSel = (document.getElementById("seg-species") && document.getElementById("seg-species").value) || "mouse";
      const skipGl = document.getElementById("seg-no-germline") && document.getElementById("seg-no-germline").checked;
      const dm = DEMOS[demoId];
      modeNote += `<p class="muted" style="margin-bottom:10px;line-height:1.55"><strong>CDR/FR boundaries</strong> follow the numbering scheme and sequences only (ANARCI-class). <strong>V-gene library species</strong> selects the IMGT reference library for closest-V names and identity % — it does <em>not</em> change region cuts.${skipGl ? " V-gene lookup was skipped." : ""}</p>`;
      if (!skipGl && dm && dm.sourceSpecies && dm.sourceSpecies !== spSel) {
        modeNote += `<p class="note" style="margin-bottom:10px;line-height:1.55">Demo <code>${escapeHtml(demoId)}</code> is tagged <strong>${escapeHtml(dm.sourceSpecies)}</strong> for germline context, but the library is <strong>${escapeHtml(spSel)}</strong>. Adjust the library to match your donor species for meaningful closest-V results; segmentation regions are unchanged.</p>`;
      }
    } catch (err) {
      clearRunning();
      if (scheme === "imgt") {
        const is404 = /Not Found|404/i.test(String(err.message));
        const sub = is404
          ? ` <span style="font-size:11px;opacity:.9">${escapeHtml(api404Hint())}</span>`
          : "";
        modeNote = `<p class="muted" style="margin-bottom:12px">${escapeHtml(String(err.message))} · IMGT heuristic.${sub}</p>`;
        vhSeg = segmentVh(vh);
        vlSeg = segmentVl(vl);
        engineLabel = "browser Lite (fallback)";
      } else {
        setOutput(errorPanel(`${scheme}: ${escapeHtml(err.message)}`));
        updateResultRail({
          status: "FAIL",
          summaryTitle: "API error",
          summaryText: err.message || String(err),
          metrics: [],
          recommendation: /Not Found|404/i.test(String(err.message || ""))
            ? api404Hint()
            : "Check conda anarcii and retry.",
          artifacts: [],
          metadata: [{ label: "Scheme", value: scheme, mono: true }],
        });
        return;
      }
    }
  } else {
    modeNote = "<p class=\"muted\" style=\"margin-bottom:12px\">IMGT heuristic (browser).</p>";
    vhSeg = segmentVh(vh);
    vlSeg = segmentVl(vl);
    engineLabel = "browser Lite (IMGT heuristic)";
  }

  const clientLocalTime = formatClientLocalDateTime();
  const runRecordId = newSegmentationRunRecordId();
  const debit = await recordRunDebit(state.service, { runRecordId, demoId });
  try {
    localStorage.setItem(
      "insynbio_last_run_segmentation_vhvl",
      JSON.stringify({
        runRecordId,
        clientLocalTime,
        atIso: new Date().toISOString(),
        demoId,
        scheme,
        engineLabel,
        useServer,
      }),
    );
  } catch (e) {
    /* ignore quota / private mode */
  }

  const segSpeciesRow = (document.getElementById("seg-species") && document.getElementById("seg-species").value) || "mouse";
  const segSkipGl = document.getElementById("seg-no-germline") && document.getElementById("seg-no-germline").checked;
  const reportSections = [
    {
      title: "Run record (client)",
      body: [
        segName ? `Sequence name / ID: ${segName}` : "",
        `Client time (local): ${clientLocalTime}`,
        `Run ID: ${runRecordId}`,
        `Numbering scheme: ${scheme.toUpperCase()}`,
        `Engine line: ${engineLabel}`,
        `Server numbering: ${useServer ? "yes" : "no"}`,
        `V-gene library species: ${segSpeciesRow}${segSkipGl ? " (lookup skipped)" : ""}`,
        `Credits debited: ${debit.debited} (balance ${debit.ok ? debit.balance.toLocaleString("en-US") : "—"})`,
      ]
        .filter(Boolean)
        .join("\n"),
    },
    { title: "VH Segmentation", body: Object.entries(vhSeg).map(([k, v]) => `${k}: ${v}`).join("\n") },
    { title: "VL Segmentation", body: Object.entries(vlSeg).map(([k, v]) => `${k}: ${v}`).join("\n") },
    { title: "Mode", body: `${engineLabel}\n${scheme.toUpperCase()}` },
  ];
  if (germlineData) {
    reportSections.push({
      title: "Germline",
      body: typeof germlineData === "object" ? JSON.stringify(germlineData, null, 2) : String(germlineData),
    });
  }
  if (numberingVh && numberingVh.length) {
    reportSections.push({
      title: `VH numbering (${scheme.toUpperCase()})`,
      body: numberingVh.map((r) => `${formatSchemePosLabel(r)}\t${r.aa || ""}`).join("\n"),
    });
  }
  if (numberingVl && numberingVl.length) {
    reportSections.push({
      title: `VL numbering (${scheme.toUpperCase()})`,
      body: numberingVl.map((r) => `${formatSchemePosLabel(r)}\t${r.aa || ""}`).join("\n"),
    });
  }
  const reportUrl = createClientReport({
    title: "Antibody Segmentation & Germline Report",
    service: service.label,
    analysisVersion: service.analysisVersion,
    sections: reportSections,
    generatedAtLocal: clientLocalTime,
    runRecordId,
    schemeLabel: scheme.toUpperCase(),
  });

  const schemeTitle = useServer ? `${(scheme).toUpperCase()} (ANARCI-class)` : `${scheme.toUpperCase()} (${engineLabel})`;
  setOutput(`
    ${modeNote}
    <section class="result-panel">
      <div class="result-title"><strong>VH · ${schemeTitle}</strong><span class="run-status pass">DONE</span></div>
      <div class="result-body">
        <div class="seg-grid">${renderSegGridFromMap(vhSeg)}</div>
        <div class="num-block">
          <div class="num-block-title">Numbering (${scheme.toUpperCase()} · pos + insertion)</div>
          ${renderNumberingTable(numberingVh)}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>VL · ${schemeTitle}</strong><span class="run-status pass">DONE</span></div>
      <div class="result-body">
        <div class="seg-grid">${renderSegGridFromMap(vlSeg)}</div>
        <div class="num-block">
          <div class="num-block-title">Numbering (${scheme.toUpperCase()} · pos + insertion)</div>
          ${renderNumberingTable(numberingVl)}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Summary</strong></div>
      <div class="result-body">
        <table class="kv-table">
          ${segName ? `<tr><th>Sequence name / ID</th><td class="mono">${escapeHtml(segName)}</td></tr>` : ""}
          <tr><th>VH length</th><td>${vh.length} aa</td></tr>
          <tr><th>VL length</th><td>${vl.length} aa</td></tr>
          <tr><th>CDRH3 length</th><td>${vhSeg["CDR-H3"]?.length ?? "—"} aa</td></tr>
          <tr><th>CDRL3 length</th><td>${vlSeg["CDR-L3"]?.length ?? "—"} aa</td></tr>
          <tr><th>Engine</th><td>${engineLabel}</td></tr>
        </table>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Germline</strong></div>
      <div class="result-body">${formatSegGermlineHtml(germlineData)}</div>
    </section>
  `);
  updateResultRail({
    status: "DONE",
    summaryTitle: "Segmentation completed",
    summaryText: `${(DEMOS[demoId] || {}).label || demoId} — ${scheme.toUpperCase()} · ${engineLabel}.`,
    clientLocalTime,
    metrics: [
      { label: "VH", value: `${vh.length} aa` },
      { label: "VL", value: `${vl.length} aa` },
      { label: "CDRH3", value: `${vhSeg["CDR-H3"]?.length ?? "—"} aa` },
      { label: "CDRL3", value: `${vlSeg["CDR-L3"]?.length ?? "—"} aa` },
      ...(germlineData && germlineData.vh && germlineData.vh.closest_vh_germline
        ? [{ label: "VH germline", value: String(germlineData.vh.closest_vh_germline), mono: true }]
        : []),
      ...(germlineData && germlineData.vl && germlineData.vl.closest_vl_germline
        ? [{ label: "VL germline", value: String(germlineData.vl.closest_vl_germline), mono: true }]
        : []),
    ],
    recommendation: useServer
      ? `${scheme.toUpperCase()} (server). Downloaded HTML includes client time + Run ID for your records.`
      : "IMGT heuristic. Enable server for full schemes.",
    artifacts: reportUrl ? [{ label: "View Report (HTML)", url: reportUrl, primary: true }] : [],
    metadata: [
      { label: "Demo ID", value: demoId, mono: true },
      ...(segName ? [{ label: "Sequence name", value: segName, mono: true }] : []),
      { label: "Scheme", value: scheme.toUpperCase(), mono: true },
      { label: "Engine", value: engineLabel, mono: true },
      { label: "Client time (local)", value: clientLocalTime, mono: true },
      { label: "Run ID", value: runRecordId, mono: true },
      { label: "Elapsed", value: elapsedSec != null ? `${elapsedSec}s` : "—" },
      { label: "Debited", value: String(debit.debited) },
      { label: "Balance", value: (debit.ok ? debit.balance : state.credits).toLocaleString("en-US"), mono: true },
    ],
  });
}

// ── VHH Segmentation ──────────────────────────────────────────────────────────

async function runVhhSegmentation(service) {
  const seq = normalizeSeq(document.getElementById("vhh-seg-seq").value);
  const demoId = document.getElementById("vhh-seg-demo").value;
  const vhhSegName = (document.getElementById("vhh-seg-name") && document.getElementById("vhh-seg-name").value.trim()) || "";
  const scheme = (document.getElementById("vhh-seg-scheme") && document.getElementById("vhh-seg-scheme").value) || "imgt";
  const useServer = document.getElementById("vhh-seg-use-server") && document.getElementById("vhh-seg-use-server").checked;
  const segSpecies = (document.getElementById("vhh-seg-species") && document.getElementById("vhh-seg-species").value) || "alpaca";
  const skipGermline = document.getElementById("vhh-seg-no-germline") && document.getElementById("vhh-seg-no-germline").checked;

  const errors = [validateSeq(seq, "VHH", 100, 150)].filter(Boolean);
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Input validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the VHH sequence input.", artifacts:[], metadata:[]});
    return;
  }
  await refreshServerWallet();
  syncWalletToState();
  if (!canAffordRun(state.service)) {
    const cost = serviceCreditCost(state.service);
    setOutput(errorPanel(`Insufficient credits. Need ${cost}. Balance ${state.credits.toLocaleString("en-US")}.`));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Insufficient credits",
      summaryText: `Required ${cost} credits.`,
      metrics: [],
      recommendation: "Top up local wallet.",
      artifacts: [],
      metadata: [],
    });
    return;
  }

  if (!useServer && scheme !== "imgt") {
    setOutput(errorPanel("Kabat/Chothia: enable Server numbering, or use IMGT."));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Server required",
      summaryText: `${scheme.toUpperCase()} requires the API.`,
      metrics: [],
      recommendation: "Enable Server numbering or select IMGT.",
      artifacts: [],
      metadata: [{ label: "Scheme", value: scheme, mono: true }],
    });
    return;
  }

  let vhhSeg;
  let modeNote = "";
  let engineLabel = "browser Lite (heuristic)";
  let elapsedSec = null;
  let germlineData = null;
  let numberingRows = null;
  let hallmarksServer = null;

  if (useServer) {
    const schemeRun = { imgt: "IMGT", kabat: "Kabat", chothia: "Chothia" }[scheme] || scheme.toUpperCase();
    setRunning(`${schemeRun} (server)…`);
    setOutput("");
    try {
      const res = await apiFetch(apiJoin("annotate/vhh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vhh_sequence: seq,
          scheme,
          species: segSpecies,
          include_germline: !skipGermline,
          include_hallmarks: true,
        }),
      });
      const data = await res.json();
      clearRunning();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
      vhhSeg = mapImgtServerRegions(data.regions || {}, IMGT_SERVER_TO_VH);
      engineLabel = publicNumberingEngineLabel(data.engine, data.scheme || scheme);
      elapsedSec = data.elapsed_sec;
      numberingRows = Array.isArray(data.numbering) ? data.numbering : null;
      hallmarksServer = data.hallmarks || null;
      germlineData = data.germline != null ? data.germline : null;
      modeNote = `<p class="muted" style="margin-bottom:12px">${(data.scheme || scheme).toUpperCase()} · ${elapsedSec != null ? `${elapsedSec}s` : "ok"}</p>`;
      modeNote += `<p class="muted" style="margin-bottom:10px;line-height:1.55"><strong>CDR/FR boundaries</strong> follow the numbering scheme and sequence (ANARCI-class). <strong>V-gene library species</strong> selects the IMGT IGHV library for closest-match names and identity % — it does <em>not</em> change region cuts.${skipGermline ? " V-gene lookup was skipped." : ""}</p>`;
    } catch (err) {
      clearRunning();
      if (scheme === "imgt") {
        const is404 = /Not Found|404/i.test(String(err.message));
        const sub = is404 ? ` <span style="font-size:11px;opacity:.9">${escapeHtml(api404Hint())}</span>` : "";
        modeNote = `<p class="muted" style="margin-bottom:12px">${escapeHtml(String(err.message))} · IMGT heuristic.${sub}</p>`;
        const seg = segmentVhh(seq);
        vhhSeg = mapImgtServerRegions(
          { FR1: seg["FR-H1"], CDR1: seg["CDR-H1"], FR2: seg["FR-H2"], CDR2: seg["CDR-H2"], FR3: seg["FR-H3"], CDR3: seg["CDR-H3"], FR4: seg["FR-H4"] },
          IMGT_SERVER_TO_VH,
        );
        engineLabel = "browser Lite (fallback)";
      } else {
        setOutput(errorPanel(`${scheme}: ${escapeHtml(err.message)}`));
        updateResultRail({
          status: "FAIL",
          summaryTitle: "API error",
          summaryText: err.message || String(err),
          metrics: [],
          recommendation: /Not Found|404/i.test(String(err.message || "")) ? api404Hint() : "Check conda anarcii and retry.",
          artifacts: [],
          metadata: [{ label: "Scheme", value: scheme, mono: true }],
        });
        return;
      }
    }
  } else {
    modeNote = "<p class=\"muted\" style=\"margin-bottom:12px\">IMGT heuristic (browser).</p>";
    const seg = segmentVhh(seq);
    vhhSeg = mapImgtServerRegions(
      { FR1: seg["FR-H1"], CDR1: seg["CDR-H1"], FR2: seg["FR-H2"], CDR2: seg["CDR-H2"], FR3: seg["FR-H3"], CDR3: seg["CDR-H3"], FR4: seg["FR-H4"] },
      IMGT_SERVER_TO_VH,
    );
    engineLabel = "browser Lite (IMGT heuristic)";
  }

  const clientLocalTime = formatClientLocalDateTime();
  const runRecordId = newSegmentationRunRecordId();
  const debit = await recordRunDebit(state.service, { runRecordId, demoId });

  const hm37 = hallmarksServer && hallmarksServer["37"] != null ? hallmarksServer["37"] : seq[36] || "?";
  const hm44 = hallmarksServer && hallmarksServer["44"] != null ? hallmarksServer["44"] : seq[43] || "?";
  const hm45 = hallmarksServer && hallmarksServer["45"] != null ? hallmarksServer["45"] : seq[44] || "?";
  const hm47 = hallmarksServer && hallmarksServer["47"] != null ? hallmarksServer["47"] : seq[46] || "?";
  // V2.7 rule: hallmark acceptance is defined on FR2 (IMGT 44/45/47).
  // IMGT 37 is shown as CDR1 context and should not gate hallmark pass/fail.
  const hallmarkOk =
    ["E", "G", "A", "S", "D", "Q"].includes(hm44) &&
    ["A", "R", "L", "K", "Q"].includes(hm45) &&
    ["F", "Y", "L", "W", "G"].includes(hm47);

  const reportSections = [
    {
      title: "Run record (client)",
      body: [
        vhhSegName ? `Sequence name / ID: ${vhhSegName}` : "",
        `Client time (local): ${clientLocalTime}`,
        `Run ID: ${runRecordId}`,
        `Numbering scheme: ${scheme.toUpperCase()}`,
        `Engine line: ${engineLabel}`,
        `Server numbering: ${useServer ? "yes" : "no"}`,
        `V-gene library species: ${segSpecies}${skipGermline ? " (lookup skipped)" : ""}`,
      ]
        .filter(Boolean)
        .join("\n"),
    },
    { title: "VHH Segmentation", body: Object.entries(vhhSeg || {}).map(([k, v]) => `${k}: ${v}`).join("\n") },
    { title: "Four-site display (IMGT 37 + FR2 44/45/47)", body: `37 (CDR1 context): ${hm37}\n44: ${hm44}\n45: ${hm45}\n47: ${hm47}` },
  ];
  if (germlineData) {
    reportSections.push({
      title: "Germline",
      body: typeof germlineData === "object" ? JSON.stringify(germlineData, null, 2) : String(germlineData),
    });
  }
  if (numberingRows && numberingRows.length) {
    reportSections.push({
      title: `VHH numbering (${scheme.toUpperCase()})`,
      body: numberingRows.map((r) => `${formatSchemePosLabel(r)}\t${r.aa || ""}`).join("\n"),
    });
  }

  const reportUrl = createClientReport({
    title: "VHH Segmentation & Germline Report",
    service: service.label,
    analysisVersion: service.analysisVersion,
    sections: reportSections,
    generatedAtLocal: clientLocalTime,
    runRecordId,
    schemeLabel: scheme.toUpperCase(),
  });

  const schemeTitle = useServer ? `${scheme.toUpperCase()} (ANARCI-class)` : `${scheme.toUpperCase()} (${engineLabel})`;
  const dm = DEMOS[demoId];
  if (dm && dm.sourceSpecies && dm.sourceSpecies !== segSpecies && !skipGermline && useServer) {
    modeNote += `<p class="note" style="margin-bottom:10px;line-height:1.55">Demo <code>${escapeHtml(demoId)}</code> is tagged <strong>${escapeHtml(dm.sourceSpecies)}</strong> for germline context, but the library is <strong>${escapeHtml(segSpecies)}</strong>. Adjust the library for meaningful closest-V results; segmentation regions are unchanged.</p>`;
  }

  setOutput(`
    ${modeNote}
    <section class="result-panel">
      <div class="result-title"><strong>VHH · ${schemeTitle}</strong><span class="run-status pass">DONE</span></div>
      <div class="result-body">
        <div class="seg-grid">${renderSegGridFromMap(vhhSeg)}</div>
        <div class="num-block">
          <div class="num-block-title">Numbering (${scheme.toUpperCase()} · pos + insertion)</div>
          ${renderNumberingTable(numberingRows)}
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Summary</strong></div>
      <div class="result-body">
        <table class="kv-table">
          ${vhhSegName ? `<tr><th>Sequence name / ID</th><td class="mono">${escapeHtml(vhhSegName)}</td></tr>` : ""}
          <tr><th>VHH length</th><td>${seq.length} aa</td></tr>
          <tr><th>CDR-H3 length</th><td>${vhhSeg["CDR-H3"]?.length ?? "—"} aa</td></tr>
          <tr><th>Engine</th><td>${engineLabel}</td></tr>
        </table>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Four-site display (IMGT 37 + FR2 44/45/47)</strong><span class="run-status ${hallmarkOk ? "pass" : "warn"}">${hallmarkOk ? "REVIEW OK" : "CHECK"}</span></div>
      <div class="result-body">
        <table class="kv-table">
          <tr><th>IMGT 37</th><td class="mono">${escapeHtml(hm37)}</td></tr>
          <tr><th>IMGT 44</th><td class="mono">${escapeHtml(hm44)}</td></tr>
          <tr><th>IMGT 45</th><td class="mono">${escapeHtml(hm45)}</td></tr>
          <tr><th>IMGT 47</th><td class="mono">${escapeHtml(hm47)}</td></tr>
        </table>
        <p class="muted" style="margin-top:8px;font-size:11px">IMGT 37 is a CDR1 context residue; FR2 hallmark guidance is evaluated on 44/45/47 per V2.7.</p>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Germline</strong></div>
      <div class="result-body">${formatSegGermlineHtml(germlineData)}</div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Method &amp; Version</strong></div>
      <div class="result-body">
        <table class="kv-table">
          <tr><th>Service</th><td>${escapeHtml(service.label)}</td></tr>
          <tr><th>Analysis Version</th><td class="mono">${escapeHtml(service.analysisVersion || "—")}</td></tr>
          <tr><th>Underlying Standard</th><td>${escapeHtml(service.underlyingStandard || "—")}</td></tr>
          <tr><th>Report Version</th><td>${escapeHtml(service.reportVersion || "1.0")}</td></tr>
        </table>
      </div>
    </section>
  `);

  updateResultRail({
    status: hallmarkOk ? "DONE" : "CAUTION",
    summaryTitle: "VHH segmentation completed",
    summaryText: `${dm ? dm.label : demoId} — ${scheme.toUpperCase()} · ${engineLabel}.`,
    clientLocalTime,
    metrics: [
      { label: "Length", value: `${seq.length} aa` },
      { label: "CDR-H3", value: `${vhhSeg["CDR-H3"]?.length ?? "—"} aa` },
      ...(germlineData && germlineData.vh && germlineData.vh.closest_vh_germline
        ? [{ label: "IGHV", value: String(germlineData.vh.closest_vh_germline), mono: true }]
        : []),
    ],
    recommendation: useServer
      ? `${scheme.toUpperCase()} (server). Downloaded HTML includes client time + Run ID.`
      : "IMGT heuristic. Enable server for Kabat/Chothia and full numbering table.",
    artifacts: reportUrl ? [{ label: "View Report (HTML)", url: reportUrl, primary: true }] : [],
    metadata: [
      { label: "Demo ID", value: demoId, mono: true },
      ...(vhhSegName ? [{ label: "Sequence name", value: vhhSegName, mono: true }] : []),
      { label: "Scheme", value: scheme.toUpperCase(), mono: true },
      { label: "Engine", value: engineLabel, mono: true },
      { label: "Client time (local)", value: clientLocalTime, mono: true },
      { label: "Run ID", value: runRecordId, mono: true },
      { label: "Elapsed", value: elapsedSec != null ? `${elapsedSec}s` : "—" },
      { label: "Debited", value: String(debit.debited) },
      { label: "Balance", value: (debit.ok ? debit.balance : state.credits).toLocaleString("en-US"), mono: true },
    ],
  });
}

// ── cDNA Optimization ─────────────────────────────────────────────────────────

function formatCdnaPre(seq) {
  if (!seq) return "—";
  const rows = seq.match(/.{1,60}/g);
  return rows ? rows.join("\n") : seq;
}

function renderAaDomainStrip(plan, aaFull) {
  let pos = 0;
  const blocks = plan.map((p) => {
    const seq = aaFull.slice(pos, pos + p.len);
    pos += p.len;
    const cls = p.cls || "";
    return `<div class="aa-domain-block ${cls}"><div class="dname">${escapeHtml(p.name)} <span class="muted">(${p.len} aa)</span></div><pre class="dseq">${escapeHtml(formatCdnaPre(seq))}</pre></div>`;
  });
  if (pos !== aaFull.length) {
    blocks.push(`<div class="aa-domain-block hinge"><div class="dname">Length check</div><pre class="dseq">expected ${aaFull.length} aa, slices sum to ${pos} — internal error</pre></div>`);
  }
  return `<div class="aa-domain-strip">${blocks.join("")}</div>`;
}

function cdnaHeavyDomainPlan(spHc, vh, fcKey) {
  const p = CDNA_IGG_FC_PARTS[fcKey] || CDNA_IGG_FC_PARTS.igg1;
  const plan = [];
  if (spHc && spHc.length) plan.push({ name: "Signal peptide", len: spHc.length, cls: "sp" });
  plan.push({ name: "VH (V domain)", len: vh.length, cls: "vd" });
  plan.push({ name: "CH1", len: p.ch1.length, cls: "const" });
  plan.push({ name: "Hinge", len: p.hinge.length, cls: "hinge" });
  plan.push({ name: "CH2", len: p.ch2.length, cls: "const" });
  plan.push({ name: "CH3", len: p.ch3.length, cls: "const" });
  return plan;
}

function cdnaLightDomainPlan(spLc, vl, clKey) {
  const cl = CDNA_CL_REGION[clKey] || CDNA_CL_REGION.kappa;
  const plan = [];
  if (spLc && spLc.length) plan.push({ name: "Signal peptide", len: spLc.length, cls: "sp" });
  plan.push({ name: "VL (V domain)", len: vl.length, cls: "vd" });
  plan.push({ name: clKey === "kappa" ? "CL (κ IGKC*01)" : "CL (λ IGLC2*01)", len: cl.length, cls: "const" });
  return plan;
}

/** Downloadable HTML report — domain cards + DNA blocks (light theme, print-friendly). */
function reportHtmlDomainStrip(plan, aaFull, opts) {
  opts = opts || {};
  const showLinear = opts.showLinear !== false;
  let pos = 0;
  const cards = [];
  for (const p of plan) {
    const seq = aaFull.slice(pos, pos + p.len);
    pos += p.len;
    const cls = p.cls ? ` rep-dom-${p.cls}` : "";
    cards.push(
      `<div class="rep-dom${cls}"><header><span class="rep-dom-t">${escapeHtml(p.name)}</span><span class="rep-dom-n">${p.len} aa</span></header><pre class="rep-dom-s">${escapeHtml(formatCdnaPre(seq))}</pre></div>`,
    );
  }
  if (pos !== aaFull.length) {
    cards.push(`<div class="rep-dom rep-dom-warn"><header><span class="rep-dom-t">Length check</span></header><pre class="rep-dom-s">Expected ${aaFull.length} aa, slices sum to ${pos}.</pre></div>`);
  }
  let html = `<div class="rep-domain-row">${cards.join("")}</div>`;
  if (showLinear) {
    html += `<div class="rep-linear"><div class="rep-linear-t">Full chain, one letter (N→C)</div><pre class="rep-seq">${escapeHtml(formatCdnaPre(aaFull))}</pre></div>`;
  }
  return html;
}

function reportHtmlDnaStrip(titleSuffix, seq) {
  const bp = seq.length;
  const cap = titleSuffix ? `${escapeHtml(titleSuffix)} · ${bp} bp` : `${bp} bp`;
  return `<div class="rep-dna-card"><div class="rep-dna-cap">${cap} <span class="rep-dna-h">5′→3′</span> (includes stop)</div><pre class="rep-dna">${escapeHtml(formatCdnaPre(seq))}</pre></div>`;
}

async function runCdnaOptimization(service) {
  const seqEl = document.getElementById("cdna-seq");
  if (!seqEl) return;
  const cdnaName = (document.getElementById("cdna-name") && document.getElementById("cdna-name").value.trim()) || "";
  const vh = normalizeSeq(seqEl.value);
  const demoId = document.getElementById("cdna-demo").value;
  const host = document.getElementById("cdna-host").value;
  const hostLabel = {"cho":"CHO","hek293":"HEK293","ecoli":"E. coli (periplasm)","yeast":"Yeast (P. pastoris)"}[host] || host;
  const isVhh = service.chainType === "vhh";
  const vlEl = document.getElementById("cdna-vl");
  const vl = vlEl ? normalizeSeq(vlEl.value) : "";

  const fullIgg =
    !isVhh &&
    document.getElementById("cdna-full-igg") &&
    document.getElementById("cdna-full-igg").checked;

  let errors = [];
  if (isVhh) {
    errors = [validateSeq(vh, "VHH", 80, 160)].filter(Boolean);
  } else {
    errors = [validateSeq(vh, "VH", 95, 145), validateSeq(vl, "VL", 95, 130)].filter(Boolean);
  }
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Correct the sequence input.", artifacts:[], metadata:[]});
    return;
  }

  let spHc = "";
  let spLc = "";
  let fcKey = "igg1";
  let clKey = "kappa";
  if (!isVhh && fullIgg) {
    spHc = resolveCdnaSignalPeptide("hc", "cdna-sp-hc", "cdna-sp-hc-custom");
    spLc = resolveCdnaSignalPeptide("lc", "cdna-sp-lc", "cdna-sp-lc-custom");
    const fSel = document.getElementById("cdna-fc");
    const cSel = document.getElementById("cdna-cl");
    fcKey = (fSel && fSel.value) || "igg1";
    clKey = (cSel && cSel.value) || "kappa";
    if (document.getElementById("cdna-sp-hc") && document.getElementById("cdna-sp-hc").value === "custom" && !spHc) {
      errors.push("Custom HC signal peptide is empty");
    }
    if (document.getElementById("cdna-sp-lc") && document.getElementById("cdna-sp-lc").value === "custom" && !spLc) {
      errors.push("Custom LC signal peptide is empty");
    }
    if (spHc && !VALID_AA.test(spHc)) errors.push("HC signal peptide: invalid amino-acid characters");
    if (spLc && !VALID_AA.test(spLc)) errors.push("LC signal peptide: invalid amino-acid characters");
  }
  if (errors.length) {
    setOutput(errorPanel(errors.join("\n")));
    updateResultRail({status:"FAIL", summaryTitle:"Validation failed", summaryText:errors.join(" · "), metrics:[], recommendation:"Fix signal peptides or choose a preset.", artifacts:[], metadata:[]});
    return;
  }

  await refreshServerWallet();
  syncWalletToState();
  if (!canAffordRun(state.service)) {
    const cost = serviceCreditCost(state.service);
    setOutput(errorPanel(`Insufficient credits. Need ${cost}. Balance ${state.credits.toLocaleString("en-US")}.`));
    updateResultRail({
      status: "FAIL",
      summaryTitle: "Insufficient credits",
      summaryText: `Required ${cost} credits.`,
      metrics: [],
      recommendation: "Top up local wallet.",
      artifacts: [],
      metadata: [],
    });
    return;
  }

  if (isVhh) {
    let vhhFullAa = vh;
    let vhhPlan = [{ name: "VHH (single domain)", len: vh.length, cls: "vd" }];
    const vhhAssembly = document.getElementById("cdna-vhh-assembly") && document.getElementById("cdna-vhh-assembly").checked;
    
    if (vhhAssembly) {
      const spSel = document.getElementById("cdna-vhh-sp");
      const spVal = spSel ? spSel.value : "none";
      let spAa = "";
      if (spVal === "custom") {
        spAa = normalizeSeq(document.getElementById("cdna-vhh-sp-custom").value);
      } else if (spVal !== "none") {
        spAa = CDNA_SIGNAL_VHH[spVal] || "";
      }
      
      const fusionSel = document.getElementById("cdna-vhh-fusion");
      const fusionVal = fusionSel ? fusionSel.value : "none";
      let fusionAa = "";
      let fusionLabel = "";
      if (fusionVal !== "none") {
        const f = CDNA_VHH_FUSION_PARTS[fusionVal];
        fusionAa = f ? f.seq : "";
        fusionLabel = f ? f.label : "";
      }

      const tagSel = document.getElementById("cdna-vhh-tag");
      const tagVal = tagSel ? tagSel.value : "none";
      const tagAa = tagVal !== "none" ? (CDNA_VHH_TAGS[tagVal] || "") : "";
      const tagLabel = tagSel && tagSel.selectedIndex >= 0 ? tagSel.options[tagSel.selectedIndex].text : "Tag";
      if (!tagAa) {
        errors.push("C-terminal tag is required for VHH expression construct (choose at least His6).");
      }
      
      let linkerAa = "";
      let cleavageAa = "";
      let cleavageLabel = "";
      const orientSel = document.getElementById("cdna-vhh-orient");
      const fusionOrient = orientSel ? orientSel.value : "vhh_fusion";
      if (fusionAa || tagAa) {
        const linkerSel = document.getElementById("cdna-vhh-linker");
        const linkerVal = linkerSel ? linkerSel.value : "none";
        if (linkerVal !== "none") {
          linkerAa = CDNA_VHH_LINKERS[linkerVal] || "";
        }
        const cleavageSel = document.getElementById("cdna-vhh-cleavage");
        const cleavageVal = cleavageSel ? cleavageSel.value : "none";
        if (cleavageVal !== "none") {
          cleavageAa = CDNA_VHH_CLEAVAGE[cleavageVal] || "";
          cleavageLabel = cleavageSel.options[cleavageSel.selectedIndex].text;
        }
      }
      
      if (spAa) {
        vhhFullAa = spAa + vhhFullAa;
        vhhPlan.unshift({ name: "Signal Peptide", len: spAa.length, cls: "sp" });
      }
      if (fusionAa || tagAa) {
        if (fusionAa && fusionOrient === "fusion_vhh") {
          vhhFullAa = spAa ? (spAa + fusionAa) : fusionAa;
          if (spAa) {
            vhhPlan = [{ name: "Signal Peptide", len: spAa.length, cls: "sp" }, { name: fusionLabel, len: fusionAa.length, cls: "constant" }, { name: "VHH (single domain)", len: vh.length, cls: "vd" }];
          } else {
            vhhPlan = [{ name: fusionLabel, len: fusionAa.length, cls: "constant" }, { name: "VHH (single domain)", len: vh.length, cls: "vd" }];
          }
          if (linkerAa) {
            vhhFullAa = vhhFullAa + linkerAa + vh;
            vhhPlan.splice(vhhPlan.length - 1, 0, { name: "Linker", len: linkerAa.length, cls: "linker" });
          } else {
            vhhFullAa = vhhFullAa + vh;
          }
        } else {
          if (linkerAa) {
            vhhFullAa = vhhFullAa + linkerAa;
            vhhPlan.push({ name: "Linker", len: linkerAa.length, cls: "linker" });
          }
          if (fusionAa) {
            vhhFullAa = vhhFullAa + fusionAa;
            vhhPlan.push({ name: fusionLabel, len: fusionAa.length, cls: "constant" });
          }
        }
        if (cleavageAa) {
          vhhFullAa = vhhFullAa + cleavageAa;
          vhhPlan.push({ name: cleavageLabel, len: cleavageAa.length, cls: "linker" });
        }
        if (tagAa) {
          vhhFullAa = vhhFullAa + tagAa;
          vhhPlan.push({ name: tagLabel, len: tagAa.length, cls: "linker" });
        }
      }
    }

    if (errors.length) {
      setOutput(errorPanel(errors.join("\n")));
      updateResultRail({
        status: "FAIL",
        summaryTitle: "Validation failed",
        summaryText: errors.join(" · "),
        metrics: [],
        recommendation: "Set a valid C-terminal tag (recommended: His6) for VHH construct expression.",
        artifacts: [],
        metadata: [],
      });
      return;
    }

    const cdna = generateOptimizedCdna(vhhFullAa, host);
    const cai = cdna.cai;
    const vhhAaNote = vhhAssembly
      ? "Assembled VHH construct. Codon optimization below applies to this full amino-acid sequence (SP · (VHH · [Linker] · [Fusion] / [Fusion] · [Linker] · VHH) · [Protease Site] · [Tag])."
      : "Single-chain VHH — one domain block. Codon optimization below applies to this amino-acid sequence.";
    const nameRowVhh = cdnaName ? [["Sequence / construct name", cdnaName]] : [];
    const reportUrl = createClientReport({
      title: `cDNA Optimization Report — ${hostLabel}`,
      service: service.label, analysisVersion: service.analysisVersion,
      sections: [
        { title: "Input", kind: "kv", rows: [...nameRowVhh, ["VHH length", `${vh.length} aa`], ["Assembled length", `${vhhFullAa.length} aa`], ["Host", hostLabel]] },
        { title: "Assembled protein", kind: "domains", plan: vhhPlan, aa: vhhFullAa, showLinear: true },
        { title: "Optimized cDNA", kind: "dna", seq: cdna.seq, dnaLabel: "Expression ORF" },
        {
          title: "Codon usage (approx.)",
          kind: "kv",
          rows: [
            ["CAI (from output DNA)", cai != null ? String(cai) : "—"],
            ["Informal band (not a gate)", caiBandDescription(cai)],
            ["Rare codons (ref. fraction <10% within AA)", String(cdna.rareCount)],
            ["CpG dinucleotides (CG in ORF)", String(cdna.cpgCount)],
            ["Stop codon", "TAA"],
          ],
        },
        { title: "Rare codon & CpG definitions", body: CDNA_RARE_CPG_NOTE },
        { title: "Restriction sites & subcloning (not provided)", body: CDNA_RE_SITES_NOTE },
        { title: "Metrics vs your own baseline (not in this demo)", body: CDNA_EFFECT_NOTE },
        { title: "About CAI (approx.)", body: CDNA_CAI_NOTE_REPORT },
      ],
    });
    setOutput(`
      <section class="result-panel">
        <div class="result-title"><strong>cDNA Optimization — ${hostLabel}</strong><span class="run-status pass">DONE</span></div>
        <div class="result-body">
          ${cdnaName ? `<p class="muted" style="margin:0 0 10px;font-size:12px"><strong>Sequence / construct name:</strong> <span class="mono">${escapeHtml(cdnaName)}</span></p>` : ""}
          <div class="metric-grid">
            ${metricHtml("VHH length", `${vh.length} aa`)}
            ${metricHtml("DNA length", `${cdna.seq.length} bp`)}
            ${metricHtml("CAI (computed)", cai != null ? String(cai) : "—", "info")}
            ${metricHtml("Host", hostLabel)}
          </div>
          <div class="cdna-cai-note"><strong>CAI (approx.)</strong> — ${escapeHtml(CDNA_CAI_NOTE_SHORT)} <em>Band:</em> ${escapeHtml(caiBandDescription(cai))}</div>
        </div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>Assembled protein (aa)</strong></div>
        <div class="result-body aa-domain-wrap">
          <p class="aa-domain-note">${escapeHtml(vhhAaNote)}</p>
          ${renderAaDomainStrip(vhhPlan, vhhFullAa)}
        </div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>Optimized cDNA (VHH)</strong></div>
        <div class="result-body">
          <div class="seq-box">
            <div class="label">cDNA (${hostLabel}-optimized, TAA stop)</div>
            <pre>${escapeHtml(formatCdnaPre(cdna.seq))}</pre>
          </div>
        </div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>Codon usage notes</strong></div>
        <div class="result-body">
          <table class="kv-table">
            <tr><th>Rare codons (Kazusa ref. &lt;10% within AA)</th><td>${cdna.rareCount}</td></tr>
            <tr><th>CpG dinucleotides (CG, 5′→3′)</th><td>${cdna.cpgCount}</td></tr>
            <tr><th>Stop</th><td class="mono">TAA</td></tr>
          </table>
          <div class="cdna-cai-note" style="margin-top:10px"><strong>Rare / CpG</strong> — ${escapeHtml(CDNA_RARE_CPG_NOTE)}</div>
          <div class="cdna-cai-note" style="margin-top:8px"><strong>RE / cloning</strong> — ${escapeHtml(CDNA_RE_SITES_NOTE)}</div>
        </div>
      </section>
    `);
    const debitCdna = await recordRunDebit(state.service, { demoId, extra: { host: hostLabel } });
    updateResultRail({
      status: "DONE",
      summaryTitle: "cDNA optimization completed",
      summaryText: `${(DEMOS[demoId] || {}).label || demoId} — VHH for ${hostLabel}.`,
      metrics: [
        { label: "CAI", value: cai != null ? String(cai) : "—", tone: "info" },
        { label: "CAI band", value: caiBandDescription(cai), tone: "" },
        { label: "bp", value: `${cdna.seq.length}` },
        { label: "Host", value: hostLabel },
      ],
      recommendation: "CAI is informational — use your program’s own acceptance rules for synthesis and expression. See the note on informal bands in the report.",
      artifacts: [{label: "Download cDNA report", url: reportUrl, download: true, primary: true}],
      metadata: [
        {label: "Demo ID", value: demoId, mono: true},
        ...(cdnaName ? [{ label: "Sequence / construct", value: cdnaName, mono: true }] : []),
        {label: "Host", value: hostLabel},
        {label: "Analysis Version", value: service.analysisVersion, mono: true},
        {label: "Debited", value: String(debitCdna.debited)},
        {label: "Balance", value: (debitCdna.ok ? debitCdna.balance : state.credits).toLocaleString("en-US"), mono: true},
      ],
    });
    return;
  }

  if (!fullIgg) {
    const cdnaH = generateOptimizedCdna(vh, host);
    const cdnaL = generateOptimizedCdna(vl, host);
    const planH = [{ name: "VH (V domain)", len: vh.length, cls: "vd" }];
    const planL = [{ name: "VL (V domain)", len: vl.length, cls: "vd" }];
    const nameRowFv = cdnaName ? [["Sequence / construct name", cdnaName]] : [];
    const reportUrl = createClientReport({
      title: `cDNA Optimization Report — ${hostLabel} (VH + VL Fv)`,
      service: service.label, analysisVersion: service.analysisVersion,
      sections: [
        {
          title: "Input",
          kind: "kv",
          rows: [
            ...nameRowFv,
            ["VH length", `${vh.length} aa`],
            ["VL length", `${vl.length} aa`],
            ["Host", hostLabel],
            ["Mode", "Variable domains only (two ORFs)"],
          ],
        },
        { title: "VH protein", kind: "domains", plan: planH, aa: vh, showLinear: true },
        { title: "VL protein", kind: "domains", plan: planL, aa: vl, showLinear: true },
        { title: "VH cDNA", kind: "dna", seq: cdnaH.seq, dnaLabel: "VH cassette" },
        { title: "VL cDNA", kind: "dna", seq: cdnaL.seq, dnaLabel: "VL cassette" },
        {
          title: "CAI (from output DNA)",
          kind: "kv",
          rows: [
            ["VH CAI", cdnaH.cai != null ? String(cdnaH.cai) : "—"],
            ["VH band (informal)", caiBandDescription(cdnaH.cai)],
            ["VL CAI", cdnaL.cai != null ? String(cdnaL.cai) : "—"],
            ["VL band (informal)", caiBandDescription(cdnaL.cai)],
          ],
        },
        {
          title: "Rare codons & CpG (from output DNA)",
          kind: "kv",
          rows: [
            ["VH rare (ref. <10% within-AA)", String(cdnaH.rareCount)],
            ["VL rare (ref. <10% within-AA)", String(cdnaL.rareCount)],
            ["VH CpG (CG count)", String(cdnaH.cpgCount)],
            ["VL CpG (CG count)", String(cdnaL.cpgCount)],
          ],
        },
        { title: "Rare codon & CpG definitions", body: CDNA_RARE_CPG_NOTE },
        { title: "Restriction sites & subcloning (not provided)", body: CDNA_RE_SITES_NOTE },
        { title: "Metrics vs your own baseline (not in this demo)", body: CDNA_EFFECT_NOTE },
        { title: "About CAI (approx.)", body: CDNA_CAI_NOTE_REPORT },
      ],
    });
    const meanCai = cdnaH.cai != null && cdnaL.cai != null ? (cdnaH.cai + cdnaL.cai) / 2 : null;
    setOutput(`
      <section class="result-panel">
        <div class="result-title"><strong>cDNA Optimization — ${hostLabel} (Fv-only mode)</strong><span class="run-status pass">DONE</span></div>
        <div class="result-body">
          ${cdnaName ? `<p class="muted" style="margin:0 0 10px;font-size:12px"><strong>Sequence / construct name:</strong> <span class="mono">${escapeHtml(cdnaName)}</span></p>` : ""}
          <p class="muted" style="font-size:12px;line-height:1.5">Two separate expression cDNAs (VH and VL). Toggle <strong>Assemble full IgG</strong> to include signal peptides and human constant regions.</p>
          <div class="metric-grid">
            ${metricHtml("VH aa", `${vh.length}`)}
            ${metricHtml("VL aa", `${vl.length}`)}
            ${metricHtml("Mean CAI", meanCai != null ? meanCai.toFixed(4) : "—", "info")}
          </div>
          <div class="cdna-cai-note"><strong>CAI (approx.)</strong> — ${escapeHtml(CDNA_CAI_NOTE_SHORT)} <em>Mean band:</em> ${escapeHtml(caiBandDescription(meanCai))}</div>
        </div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>VH protein (aa) — Fv cassette</strong></div>
        <div class="result-body aa-domain-wrap">${renderAaDomainStrip(planH, vh)}</div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>VL protein (aa) — Fv cassette</strong></div>
        <div class="result-body aa-domain-wrap">${renderAaDomainStrip(planL, vl)}</div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>VH cassette cDNA</strong></div>
        <div class="result-body"><div class="seq-box"><div class="label">VH (${hostLabel})</div><pre>${escapeHtml(formatCdnaPre(cdnaH.seq))}</pre></div></div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>VL cassette cDNA</strong></div>
        <div class="result-body"><div class="seq-box"><div class="label">VL (${hostLabel})</div><pre>${escapeHtml(formatCdnaPre(cdnaL.seq))}</pre></div></div>
      </section>
      <section class="result-panel">
        <div class="result-title"><strong>Rare codons &amp; CpG (VH / VL ORFs)</strong></div>
        <div class="result-body">
          <table class="kv-table">
            <tr><th>VH rare (ref. &lt;10% within-AA)</th><td>${cdnaH.rareCount}</td></tr>
            <tr><th>VL rare (ref. &lt;10% within-AA)</th><td>${cdnaL.rareCount}</td></tr>
            <tr><th>VH CpG (CG)</th><td>${cdnaH.cpgCount}</td></tr>
            <tr><th>VL CpG (CG)</th><td>${cdnaL.cpgCount}</td></tr>
          </table>
          <div class="cdna-cai-note" style="margin-top:10px"><strong>Rare / CpG</strong> — ${escapeHtml(CDNA_RARE_CPG_NOTE)}</div>
          <div class="cdna-cai-note" style="margin-top:8px"><strong>RE / cloning</strong> — ${escapeHtml(CDNA_RE_SITES_NOTE)}</div>
        </div>
      </section>
    `);
    const debitCdna = await recordRunDebit(state.service, { demoId, extra: { host: hostLabel, mode: "fv_only" } });
    updateResultRail({
      status: "DONE",
      summaryTitle: "cDNA optimization completed (VH + VL)",
      summaryText: `${(DEMOS[demoId] || {}).label || demoId} — Fv cDNAs for ${hostLabel}.`,
      metrics: [
        { label: "VH bp", value: `${cdnaH.seq.length}` },
        { label: "VL bp", value: `${cdnaL.seq.length}` },
        { label: "Mean CAI", value: meanCai != null ? meanCai.toFixed(4) : "—", tone: "info" },
      ],
      recommendation: "Clone VH and VL into your expression vectors separately, or switch to full IgG assembly. CAI is informational — not a synthesis gate.",
      artifacts: [{label: "Download cDNA report", url: reportUrl, download: true, primary: true}],
      metadata: [
        {label: "Demo ID", value: demoId, mono: true},
        ...(cdnaName ? [{ label: "Sequence / construct", value: cdnaName, mono: true }] : []),
        {label: "Host", value: hostLabel},
        {label: "Analysis Version", value: service.analysisVersion, mono: true},
        {label: "Debited", value: String(debitCdna.debited)},
        {label: "Balance", value: (debitCdna.ok ? debitCdna.balance : state.credits).toLocaleString("en-US"), mono: true},
      ],
    });
    return;
  }

  const fc = CDNA_IGG_FC_PARTS[fcKey] || CDNA_IGG_FC_PARTS.igg1;
  const clAa = CDNA_CL_REGION[clKey] || CDNA_CL_REGION.kappa;
  const coreHc = assembleIggHeavyChainAa(vh, fcKey);
  const coreLc = assembleIggLightChainAa(vl, clKey);
  const aaHc = spHc + coreHc;
  const aaLc = spLc + coreLc;

  const cdnaHc = generateOptimizedCdna(aaHc, host);
  const cdnaLc = generateOptimizedCdna(aaLc, host);
  const meanCai2 = cdnaHc.cai != null && cdnaLc.cai != null ? (cdnaHc.cai + cdnaLc.cai) / 2 : null;

  const assemblyNote =
    `Heavy: ${spHc ? spHc.length + " aa SP + " : ""}VH (${vh.length}) + CH1/hinge/CH2/CH3 [${fc.label}]\n` +
    `Light: ${spLc ? spLc.length + " aa SP + " : ""}VL (${vl.length}) + CL [${clKey === "kappa" ? "IGKC*01" : "IGLC2*01"}]`;

  const planHc = cdnaHeavyDomainPlan(spHc, vh, fcKey);
  const planLc = cdnaLightDomainPlan(spLc, vl, clKey);

  const nameRowIgg = cdnaName ? [["Sequence / construct name", cdnaName]] : [];
  const reportUrl = createClientReport({
    title: `cDNA Optimization — ${hostLabel} (full IgG assembly)`,
    service: service.label, analysisVersion: service.analysisVersion,
    sections: [
      {
        title: "Assembly summary",
        kind: "kv",
        rows: [
          ...nameRowIgg,
          ["Heavy chain", assemblyNote.split("\n")[0]],
          ["Light chain", assemblyNote.split("\n")[1]],
          ["HC ORF", `${aaHc.length} aa`],
          ["LC ORF", `${aaLc.length} aa`],
          ["Fc preset", fc.label],
          ["CL", clKey === "kappa" ? "κ IGKC*01" : "λ IGLC2*01"],
          ["Mean CAI (from DNA)", meanCai2 != null ? meanCai2.toFixed(4) : "—"],
          ["Mean band (informal)", caiBandDescription(meanCai2)],
        ],
      },
      { title: "Heavy chain — protein (by domain)", kind: "domains", plan: planHc, aa: aaHc, showLinear: true },
      { title: "Light chain — protein (by domain)", kind: "domains", plan: planLc, aa: aaLc, showLinear: true },
      { title: "Heavy chain cDNA", kind: "dna", seq: cdnaHc.seq, dnaLabel: "Secreted HC" },
      { title: "Light chain cDNA", kind: "dna", seq: cdnaLc.seq, dnaLabel: "Secreted LC" },
      {
        title: "CAI (from output DNA)",
        kind: "kv",
        rows: [
          ["Heavy chain CAI", cdnaHc.cai != null ? String(cdnaHc.cai) : "—"],
          ["HC band (informal)", caiBandDescription(cdnaHc.cai)],
          ["Light chain CAI", cdnaLc.cai != null ? String(cdnaLc.cai) : "—"],
          ["LC band (informal)", caiBandDescription(cdnaLc.cai)],
        ],
      },
      {
        title: "Rare codons & CpG (from output DNA)",
        kind: "kv",
        rows: [
          ["HC rare (ref. <10% within-AA)", String(cdnaHc.rareCount)],
          ["LC rare (ref. <10% within-AA)", String(cdnaLc.rareCount)],
          ["HC CpG (CG count)", String(cdnaHc.cpgCount)],
          ["LC CpG (CG count)", String(cdnaLc.cpgCount)],
        ],
      },
      { title: "Rare codon & CpG definitions", body: CDNA_RARE_CPG_NOTE },
      { title: "Restriction sites & subcloning (not provided)", body: CDNA_RE_SITES_NOTE },
      { title: "Metrics vs your own baseline (not in this demo)", body: CDNA_EFFECT_NOTE },
      { title: "About CAI (approx.)", body: CDNA_CAI_NOTE_REPORT },
    ],
  });

  setOutput(`
    <section class="result-panel">
      <div class="result-title"><strong>Full IgG assembly → cDNA — ${hostLabel}</strong><span class="run-status pass">DONE</span></div>
      <div class="result-body">
        ${cdnaName ? `<p class="muted" style="margin:0 0 10px;font-size:12px"><strong>Sequence / construct name:</strong> <span class="mono">${escapeHtml(cdnaName)}</span></p>` : ""}
        <table class="kv-table">
          <tr><th>Fc / hinge</th><td>${escapeHtml(fc.label)}</td></tr>
          <tr><th>CL</th><td>${clKey === "kappa" ? "κ IGKC*01" : "λ IGLC2*01"}</td></tr>
          <tr><th>HC ORF</th><td>${aaHc.length} aa (${spHc ? "with SP" : "no SP"})</td></tr>
          <tr><th>LC ORF</th><td>${aaLc.length} aa (${spLc ? "with SP" : "no SP"})</td></tr>
          <tr><th>Mean CAI (computed)</th><td>${meanCai2 != null ? meanCai2.toFixed(4) : "—"}</td></tr>
        </table>
        <div class="cdna-cai-note"><strong>CAI (approx.)</strong> — ${escapeHtml(CDNA_CAI_NOTE_SHORT)} <em>Mean band:</em> ${escapeHtml(caiBandDescription(meanCai2))}</div>
        <p class="muted" style="font-size:11px;margin-top:10px">Constants are human germline reference segments for <em>design preview</em>. Match to your clinical template and vector strategy before manufacturing.</p>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Heavy chain — assembled protein (aa by domain)</strong></div>
      <div class="result-body aa-domain-wrap">
        <p class="aa-domain-note">N→C order: signal peptide (if any), VH, CH1, hinge, CH2, CH3. cDNA below encodes this exact amino-acid string (plus TAA).</p>
        ${renderAaDomainStrip(planHc, aaHc)}
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Light chain — assembled protein (aa by domain)</strong></div>
      <div class="result-body aa-domain-wrap">
        <p class="aa-domain-note">N→C order: signal peptide (if any), VL, constant light (κ or λ).</p>
        ${renderAaDomainStrip(planLc, aaLc)}
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Secreted heavy chain cDNA</strong> (5'→3', TAA stop)</div>
      <div class="result-body">
        <div class="seq-box"><div class="label">HC · ${cdnaHc.seq.length} bp</div>
          <pre>${escapeHtml(formatCdnaPre(cdnaHc.seq))}</pre>
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Secreted light chain cDNA</strong> (5'→3', TAA stop)</div>
      <div class="result-body">
        <div class="seq-box"><div class="label">LC · ${cdnaLc.seq.length} bp</div>
          <pre>${escapeHtml(formatCdnaPre(cdnaLc.seq))}</pre>
        </div>
      </div>
    </section>
    <section class="result-panel">
      <div class="result-title"><strong>Codon notes (per chain)</strong></div>
      <div class="result-body">
        <table class="kv-table">
          <tr><th>HC rare (Kazusa ref. &lt;10% within-AA)</th><td>${cdnaHc.rareCount}</td></tr>
          <tr><th>LC rare (Kazusa ref. &lt;10% within-AA)</th><td>${cdnaLc.rareCount}</td></tr>
          <tr><th>HC CpG (CG dinucleotides)</th><td>${cdnaHc.cpgCount}</td></tr>
          <tr><th>LC CpG (CG dinucleotides)</th><td>${cdnaLc.cpgCount}</td></tr>
          <tr><th>Stop codon</th><td class="mono">TAA</td></tr>
        </table>
        <div class="cdna-cai-note" style="margin-top:10px"><strong>Rare / CpG</strong> — ${escapeHtml(CDNA_RARE_CPG_NOTE)}</div>
        <div class="cdna-cai-note" style="margin-top:8px"><strong>RE / cloning</strong> — ${escapeHtml(CDNA_RE_SITES_NOTE)}</div>
      </div>
    </section>
  `);

  const debitCdna = await recordRunDebit(state.service, { demoId, extra: { host: hostLabel, mode: "full_igg", fc: fcKey, cl: clKey } });
  updateResultRail({
    status: "DONE",
    summaryTitle: "cDNA optimization (HC + LC assembly)",
    summaryText: `${(DEMOS[demoId] || {}).label || demoId} — ${(fc || {}).label || ""}, ${clKey} CL, ${hostLabel}.`,
    metrics: [
      { label: "HC bp", value: `${cdnaHc.seq.length}` },
      { label: "LC bp", value: `${cdnaLc.seq.length}` },
      { label: "Mean CAI", value: meanCai2 != null ? meanCai2.toFixed(4) : "—", tone: "info" },
    ],
    recommendation: "Review assembled constant regions vs. your locked IgG template. CAI is informational — not a synthesis gate.",
    artifacts: [{label: "Download cDNA report", url: reportUrl, download: true, primary: true}],
    metadata: [
      {label: "Demo ID", value: demoId, mono: true},
      ...(cdnaName ? [{ label: "Sequence / construct", value: cdnaName, mono: true }] : []),
      {label: "Host", value: hostLabel},
      {label: "Fc", value: fcKey, mono: true},
      {label: "Analysis Version", value: service.analysisVersion, mono: true},
      {label: "Debited", value: String(debitCdna.debited)},
      {label: "Balance", value: (debitCdna.ok ? debitCdna.balance : state.credits).toLocaleString("en-US"), mono: true},
    ],
  });
}

// ── Offline Request ───────────────────────────────────────────────────────────

function getAf2AbMode() {
  const el = document.getElementById("af2-ab-mode");
  return el && el.value === "vhh" ? "vhh" : "vh_vl";
}

function onAf2AbModeChange() {
  const vhvl = document.getElementById("af2-rows-vhvl");
  const vhh = document.getElementById("af2-rows-vhh");
  const mode = getAf2AbMode();
  if (vhvl) vhvl.style.display = mode === "vh_vl" ? "block" : "none";
  if (vhh) vhh.style.display = mode === "vhh" ? "block" : "none";
}

function buildAf2MultimerFastaPreview() {
  const ag = normalizeSeq(document.getElementById("af2-antigen-ecd") && document.getElementById("af2-antigen-ecd").value);
  const ta = document.getElementById("af2-fasta-preview");
  if (!ag) {
    window.alert("AF2 Multimer: paste antigen ECD first.");
    return;
  }
  if (getAf2AbMode() === "vhh") {
    const vhh = normalizeSeq(document.getElementById("af2-antibody-vhh") && document.getElementById("af2-antibody-vhh").value);
    if (!vhh) {
      window.alert("AF2 Multimer: paste VHH sequence.");
      return;
    }
    if (ta) ta.value = `>antigen_ECD\n${ag}\n>antibody_VHH\n${vhh}\n`;
    return;
  }
  const vh = normalizeSeq(document.getElementById("af2-antibody-vh") && document.getElementById("af2-antibody-vh").value);
  const vl = normalizeSeq(document.getElementById("af2-antibody-vl") && document.getElementById("af2-antibody-vl").value);
  const miss = [];
  if (!vh) miss.push("VH");
  if (!vl) miss.push("VL");
  if (miss.length) {
    window.alert("AF2 Multimer: paste " + miss.join(", ") + " first.");
    return;
  }
  if (ta) ta.value = `>antigen_ECD\n${ag}\n>antibody_VH\n${vh}\n>antibody_VL\n${vl}\n`;
}

function fillAf2AntibodyFromLastHumanization() {
  let vh = "";
  let vl = "";
  let vhh = "";
  let kind = "";
  try {
    vh = sessionStorage.getItem("insynbio_last_humanized_vh") || "";
    vl = sessionStorage.getItem("insynbio_last_humanized_vl") || "";
    vhh = sessionStorage.getItem("insynbio_last_humanized_vhh") || "";
    kind = sessionStorage.getItem("insynbio_last_humanization_kind") || "";
  } catch (e) {}
  const modeEl = document.getElementById("af2-ab-mode");
  const post = document.getElementById("af2-post-humanization");
  if (kind === "vhh" && vhh) {
    if (modeEl) modeEl.value = "vhh";
    onAf2AbModeChange();
    const el = document.getElementById("af2-antibody-vhh");
    if (el) el.value = vhh;
    if (post) post.checked = true;
    return;
  }
  if (vh && vl) {
    if (modeEl) modeEl.value = "vh_vl";
    onAf2AbModeChange();
    const a = document.getElementById("af2-antibody-vh");
    const b = document.getElementById("af2-antibody-vl");
    if (a) a.value = vh;
    if (b) b.value = vl;
    if (post) post.checked = true;
    return;
  }
  if (vhh && !vh) {
    if (modeEl) modeEl.value = "vhh";
    onAf2AbModeChange();
    const el = document.getElementById("af2-antibody-vhh");
    if (el) el.value = vhh;
    if (post) post.checked = true;
    return;
  }
  window.alert("No humanized VH/VL or VHH found in this browser session. Run humanization first, then use this button.");
}

function fillCdnaVhhFromLastHumanization() {
  let vhh = "";
  try {
    vhh = sessionStorage.getItem("insynbio_last_humanized_vhh") || "";
  } catch (e) {}
  const seqEl = document.getElementById("cdna-seq");
  if (!seqEl) return;
  if (!String(vhh).trim()) {
    window.alert("No humanized VHH found in this browser session. Run VHH Humanization first, then use this button.");
    return;
  }
  seqEl.value = String(vhh).trim();
  const helper = document.getElementById("cdna-helper");
  if (helper) {
    helper.textContent = "Loaded VHH sequence from the latest humanization result in this browser session.";
  }
}

/** Pre-fill IgG cDNA form from last VH/VL humanization stored in sessionStorage. */
function fillCdnaIggFromLastHumanization() {
  let vh = "", vl = "", name = "";
  try {
    vh   = sessionStorage.getItem("insynbio_last_humanized_vh") || "";
    vl   = sessionStorage.getItem("insynbio_last_humanized_vl") || "";
    name = sessionStorage.getItem("insynbio_last_humanized_name") || "";
  } catch (e) {}
  const seqEl  = document.getElementById("cdna-seq");
  const vlEl   = document.getElementById("cdna-vl");
  const nameEl = document.getElementById("cdna-name");
  if (!seqEl) return;
  if (!String(vh).trim()) {
    window.alert("No humanized VH/VL found in this browser session. Run VH/VL Humanization first, then use this button.");
    return;
  }
  seqEl.value = String(vh).trim();
  if (vlEl) vlEl.value = String(vl).trim();
  if (nameEl && name) nameEl.value = name;
  const helper = document.getElementById("cdna-helper");
  if (helper) helper.textContent = "Loaded VH/VL sequences from the latest humanization result in this browser session.";
}

/** Navigate to cDNA optimization and pre-fill the last humanized sequence. */
function goToCdnaWithLastHumanization(isVhh) {
  activateService(isVhh ? "cdna-optimization-vhh" : "cdna-optimization-igg");
  setTimeout(() => {
    if (isVhh) fillCdnaVhhFromLastHumanization();
    else fillCdnaIggFromLastHumanization();
  }, 250);
}

/** Navigate to IgG cDNA optimization and pre-fill from last CMC run. */
function goToCdnaFromCmcIgg() {
  const vh   = (window._lastCmcInputVh   || "").trim();
  const vl   = (window._lastCmcInputVl   || "").trim();
  const name = (window._lastCmcInputName || "").trim();
  if (!vh) {
    window.alert("No IgG CMC sequences cached in this browser session. Run CMC assessment first.");
    return;
  }
  activateService("cdna-optimization-igg");
  setTimeout(() => {
    const seqEl  = document.getElementById("cdna-seq");
    const vlEl   = document.getElementById("cdna-vl");
    const nameEl = document.getElementById("cdna-name");
    if (seqEl) seqEl.value = vh;
    if (vlEl)  vlEl.value  = vl;
    if (nameEl && name) nameEl.value = name;
    const helper = document.getElementById("cdna-helper");
    if (helper) helper.textContent = "Sequences pre-filled from the CMC assessment result in this browser session.";
    const shell = document.querySelector(".service-shell");
    if (shell) shell.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 250);
}

/** Navigate to VHH cDNA optimization and pre-fill from last VHH CMC run. */
function goToCdnaFromCmcVhh() {
  const vhh  = (window._lastCmcInputVhh  || "").trim();
  const name = (window._lastCmcInputName || "").trim();
  if (!vhh) {
    window.alert("No VHH CMC sequence cached in this browser session. Run VHH CMC assessment first.");
    return;
  }
  activateService("cdna-optimization-vhh");
  setTimeout(() => {
    const seqEl  = document.getElementById("cdna-seq");
    const nameEl = document.getElementById("cdna-name");
    if (seqEl) seqEl.value = vhh;
    if (nameEl && name) nameEl.value = name;
    const helper = document.getElementById("cdna-helper");
    if (helper) helper.textContent = "VHH sequence pre-filled from the CMC assessment result in this browser session.";
    const shell = document.querySelector(".service-shell");
    if (shell) shell.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 250);
}

function goToAf2MultimerWithLastHumanization(useVhhMode) {
  activateModule("offline-services");
  activateService("af2-multimer");
  setTimeout(() => {
    const m = document.getElementById("af2-ab-mode");
    if (m) m.value = useVhhMode ? "vhh" : "vh_vl";
    onAf2AbModeChange();
    fillAf2AntibodyFromLastHumanization();
  }, 150);
}

/** Jump to CMC → IgG with last humanized VH/VL (same session as AF2 fill). */
function goToCmcIggWithLastHumanization() {
  const vh = sessionStorage.getItem("insynbio_last_humanized_vh") || "";
  const vl = sessionStorage.getItem("insynbio_last_humanized_vl") || "";
  const name = sessionStorage.getItem("insynbio_last_humanized_name") || "";
  if (!String(vh).trim() || !String(vl).trim()) {
    window.alert("No humanized VH/VL in this browser session. Run humanization first, then use this button.");
    return;
  }
  activateService("igg-cmc-snapshot");
  setTimeout(() => {
    const vhEl = document.getElementById("cmc-vh");
    const vlEl = document.getElementById("cmc-vl");
    const nameEl = document.getElementById("cmc-sequence-name");
    const typeEl = document.getElementById("cmc-antibody-type");
    const demoEl = document.getElementById("cmc-demo");
    const helperEl = document.getElementById("cmc-helper");
    if (vhEl) vhEl.value = vh;
    if (vlEl) vlEl.value = vl;
    // Always set name — fall back to generic label if project_name was empty
    const displayName = name ? `${name} (humanized)` : "Humanized antibody";
    if (nameEl) nameEl.value = displayName;
    // Humanized VH/VL always maps to the "humanized" origin tier, not "fully_human"
    if (typeEl) { typeEl.value = "humanized"; if (typeof updateCmcOriginNote === "function") updateCmcOriginNote(); }
    // Replace demo dropdown label to avoid confusion — insert a "custom input" sentinel option
    if (demoEl) {
      const customOpt = document.createElement("option");
      customOpt.value = "__humanized__";
      customOpt.textContent = `\u2014 ${displayName} (custom input) \u2014`;
      demoEl.insertBefore(customOpt, demoEl.firstChild);
      demoEl.value = "__humanized__";
    }
    if (helperEl) helperEl.textContent = `Custom input from VH/VL humanization: ${displayName}. Sequences pre-filled from this session.`;
    const shell = document.querySelector(".service-shell");
    if (shell) shell.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 300);
}

/** Jump to CMC → VHH with last humanized VHH (same session as AF2 fill). */
function goToVhhCmcWithLastHumanization() {
  const vhh = sessionStorage.getItem("insynbio_last_humanized_vhh") || "";
  const name = sessionStorage.getItem("insynbio_last_humanized_name") || "";
  if (!String(vhh).trim()) {
    window.alert("No humanized VHH in this browser session. Run humanization first, then use this button.");
    return;
  }
  activateService("vhh-cmc-snapshot");
  setTimeout(() => {
    const vhhEl = document.getElementById("vhh-cmc-seq");
    const nameEl = document.getElementById("vhh-cmc-name");
    const demoEl = document.getElementById("vhh-cmc-demo");
    const helperEl = document.getElementById("vhh-cmc-helper");
    if (vhhEl) vhhEl.value = vhh;
    const displayName = name ? `${name} (humanized)` : "Humanized VHH";
    if (nameEl) nameEl.value = displayName;
    if (demoEl) {
      const customOpt = document.createElement("option");
      customOpt.value = "__humanized__";
      customOpt.textContent = `\u2014 ${displayName} (custom input) \u2014`;
      demoEl.insertBefore(customOpt, demoEl.firstChild);
      demoEl.value = "__humanized__";
    }
    if (helperEl) helperEl.innerHTML = `<div style="font-size:11px;color:var(--muted)">Custom input from VHH humanization: ${displayName}. Sequence pre-filled from this session.</div>`;
    const shell = document.querySelector(".service-shell");
    if (shell) shell.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 300);
}

function onAf2MultimerFastaFile(ev) {
  const f = ev.target && ev.target.files && ev.target.files[0];
  updateFileNameLabel(ev.target, "af2-fasta-file-name");
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    const recs = parseFvFastaRecords(text);
    const ta = document.getElementById("af2-fasta-preview");
    if (!ta) return;
    if (!recs.length) {
      ta.value = text.trim();
      return;
    }
    ta.value = recs.map((r) => `>${r.id}\n${r.seq}`).join("\n") + "\n";
  };
  reader.readAsText(f);
}

function updateFileNameLabel(inputEl, labelId) {
  const label = document.getElementById(labelId);
  if (!label) return;
  const file = inputEl && inputEl.files && inputEl.files[0];
  label.textContent = file ? file.name : "No file selected";
}

async function submitOfflineRequest(serviceLabel) {
  const name = document.getElementById("offline-name").value || "(not provided)";
  const org = document.getElementById("offline-org").value || "(not provided)";
  const email = document.getElementById("offline-email").value || "(not provided)";
  const target = document.getElementById("offline-target").value || "(not provided)";
  const desc = document.getElementById("offline-desc").value || "(not provided)";
  const timeline = document.getElementById("offline-timeline").value || "flexible";
  let af2Section = "";
  if (state.service === "af2-multimer") {
    const useUploadOnlyEl = document.getElementById("af2-use-upload-only");
    const useUploadOnly = useUploadOnlyEl && useUploadOnlyEl.checked;
    const previewEl = document.getElementById("af2-fasta-preview");
    let preview = (previewEl && previewEl.value.trim()) || "";
    const construct = (document.getElementById("af2-construct-notes") && document.getElementById("af2-construct-notes").value.trim()) || "";
    const gs = (document.getElementById("af2-gs-linker") && document.getElementById("af2-gs-linker").value.trim()) || "";
    const gsTm = document.getElementById("af2-gs-replace-tm") && document.getElementById("af2-gs-replace-tm").checked;
    const postHum =
      document.getElementById("af2-post-humanization") && document.getElementById("af2-post-humanization").checked;
    const abMode = getAf2AbMode();
    if (!useUploadOnly) {
      const ag = normalizeSeq(document.getElementById("af2-antigen-ecd") && document.getElementById("af2-antigen-ecd").value);
      if (abMode === "vhh") {
        const vhh = normalizeSeq(document.getElementById("af2-antibody-vhh") && document.getElementById("af2-antibody-vhh").value);
        if (!ag || !vhh) {
          window.alert(
            "AF2 Multimer: provide antigen ECD and VHH, or use \"upload FASTA only\" with a valid preview.",
          );
          return;
        }
      } else {
        const vh = normalizeSeq(document.getElementById("af2-antibody-vh") && document.getElementById("af2-antibody-vh").value);
        const vl = normalizeSeq(document.getElementById("af2-antibody-vl") && document.getElementById("af2-antibody-vl").value);
        if (!ag || !vh || !vl) {
          window.alert(
            "AF2 Multimer: provide antigen ECD, VH, and VL — or switch to VHH — or use upload FASTA only.",
          );
          return;
        }
      }
      if (!preview) buildAf2MultimerFastaPreview();
      preview = (previewEl && previewEl.value.trim()) || "";
    }
    if (!preview) {
      window.alert("FASTA preview is empty. Build from sequences, upload a file, or paste a ColabFold-style FASTA.");
      return;
    }
    af2Section = `\n\n--- AF2 Multimer (ColabFold-style FASTA) ---\nAntibody mode: ${abMode === "vhh" ? "VHH (2 chains with antigen)" : "VH+VL (3 chains with antigen)"}\nPost-humanization complex (checkbox): ${postHum ? "yes" : "no"}\nConstruct / ECD notes: ${construct || "—"}\nOptional GS linker: ${gs || "—"}\nTM segment replaced by GS (checkbox): ${gsTm ? "yes" : "no"}\nUpload-only mode: ${useUploadOnly ? "yes" : "no"}\n\n${preview}\n`;
  }

  // 1. Call backend API for true online submission
  try {
    const response = await fetch(`${getApiBase()}/api/v1/offline/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service: serviceLabel,
        name,
        organization: org,
        email,
        target,
        timeline,
        description: desc,
        af2_section: af2Section || null
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log("Offline request result:", result);
  } catch (err) {
    console.warn("Failed to send online request, falling back to mailto:", err);
    // Fallback to mailto if API fails
    const body = encodeURIComponent(
      `Service: ${serviceLabel}\nName: ${name}\nOrganization: ${org}\nEmail: ${email}\nTarget: ${target}\nTimeline: ${timeline}\n\nDescription:\n${desc}${af2Section}`,
    );
    const mailto = `mailto:contact@insynbio.com?subject=${encodeURIComponent(`Offline Request: ${serviceLabel}`)}&body=${body}`;
    window.open(mailto);
  }

  // 2. Update UI
  setOutput(`
    <section class="result-panel">
      <div class="result-title"><strong>Request Submitted</strong><span class="run-status pass">SENT</span></div>
      <div class="result-body">
        <p style="margin-bottom:12px;color:var(--pass)">✓ Your request has been logged on the server and queued for review.</p>
        <table class="kv-table">
          <tr><th>Service</th><td>${escapeHtml(serviceLabel)}</td></tr>
          <tr><th>Contact</th><td>${escapeHtml(name)} — ${escapeHtml(org)}</td></tr>
          <tr><th>Email</th><td>${escapeHtml(email)}</td></tr>
          <tr><th>Target</th><td>${escapeHtml(target)}</td></tr>
          <tr><th>Timeline</th><td>${escapeHtml(timeline)}</td></tr>
          <tr><th>Next step</th><td>InSynBio team will review within 1 business day and schedule a scoping call via <strong>contact@insynbio.com</strong>.</td></tr>
        </table>
      </div>
    </section>
  `);
  updateResultRail({
    status: "PASS",
    summaryTitle: "Offline request sent",
    summaryText: `Request for ${serviceLabel} submitted to the InSynBio offline queue.`,
    metrics: [
      {label: "Service", value: serviceLabel},
      {label: "Timeline", value: timeline},
      {label: "Billing", value: "Custom Quote"},
    ],
    recommendation: "A scoping call will be scheduled within 1 business day. Please check your email.",
    artifacts: [],
    metadata: [
      {label:"Service", value: serviceLabel},
      {label:"Requester", value: name, mono:false},
      {label:"Email", value: email},
      {label:"Organization", value: org},
    ],
  });
}

// ── Client-side analysis helpers ──────────────────────────────────────────────

function segmentVh(seq) {
  const L = seq.length;
  const fr1End = Math.min(25, L);
  const cdr1End = Math.min(35, L);
  const fr2End = Math.min(49, L);
  const cdr2End = Math.min(58, L);
  const fr3End = Math.min(94, L);
  const cdr3End = Math.min(L - 11, L);
  return {
    "FR-H1": seq.slice(0, fr1End),
    "CDR-H1": seq.slice(fr1End, cdr1End),
    "FR-H2": seq.slice(cdr1End, fr2End),
    "CDR-H2": seq.slice(fr2End, cdr2End),
    "FR-H3": seq.slice(cdr2End, fr3End),
    "CDR-H3": seq.slice(fr3End, cdr3End),
    "FR-H4": seq.slice(cdr3End),
  };
}

function segmentVl(seq) {
  const L = seq.length;
  const fr1End = Math.min(23, L);
  const cdr1End = Math.min(35, L);
  const fr2End = Math.min(49, L);
  const cdr2End = Math.min(57, L);
  // IMGT-lite: CDR-L3 + FR-L4 are taken from the C terminus (like server-side split_regions).
  // Fixed fr3End=88 + cdr3End=L-10 wrongly gave ~3 aa CDR-L3 for ~101 aa chains (no FR4 in the label sense).
  const fr4Len = 10;
  const cdr3Typ = 9;
  const cdr3End = Math.max(cdr2End, L - fr4Len);
  const cdr3Start = Math.min(Math.max(cdr2End, cdr3End - cdr3Typ), cdr3End);
  return {
    "FR-L1": seq.slice(0, fr1End),
    "CDR-L1": seq.slice(fr1End, cdr1End),
    "FR-L2": seq.slice(cdr1End, fr2End),
    "CDR-L2": seq.slice(fr2End, cdr2End),
    "FR-L3": seq.slice(cdr2End, cdr3Start),
    "CDR-L3": seq.slice(cdr3Start, cdr3End),
    "FR-L4": seq.slice(cdr3End),
  };
}

function segmentVhh(seq) {
  const L = seq.length;
  const fr1End = Math.min(25, L);
  const cdr1End = Math.min(35, L);
  const fr2End = Math.min(49, L);
  const cdr2End = Math.min(58, L);
  const fr3End = Math.min(97, L);
  const cdr3End = Math.min(L - 11, L);
  return {
    "FR-H1": seq.slice(0, fr1End),
    "CDR-H1": seq.slice(fr1End, cdr1End),
    "FR-H2": seq.slice(cdr1End, fr2End),
    "CDR-H2": seq.slice(fr2End, cdr2End),
    "FR-H3": seq.slice(cdr2End, fr3End),
    "CDR-H3": seq.slice(fr3End, cdr3End),
    "FR-H4": seq.slice(cdr3End),
  };
}

/** Default / preset secretion signals (aa). Custom overrides via form. */
const CDNA_SIGNAL_HC = {
  hc_md: "MDMRVPAQLLGLLLLWFPGARC",
  hc_mef: "MEFGLSWVFLVAALEGEA",
};
const CDNA_SIGNAL_LC = {
  lc_md: "MDMRVPAQLLGLLLLWLSGARC",
  lc_met: "METPAQLLFLLLLWLPDTTG",
};

/**
 * Human heavy-chain constant domains from IMGT (IGHG1*01 / IGHG2*01 / IGHG4*01) — CH1 + hinge + CH2 + CH3.
 * Engineered entries: widely published motif substitutions on the *01 spine (expression preview — confirm vs. CMC + FTO).
 */
const CDNA_IGG_FC_PARTS = {
  igg1: {
    label: "IGHG1*01",
    ch1:
      "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKV",
    hinge: "EPKSCDKTHTCPPCP",
    ch2:
      "APELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAK",
    ch3:
      "GQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  /** FcγR-silencing variant: CH2 motif PEVTCVVVDV → PEVTCAAVDV (commonly cited L234A/L235A–class interface; verify EU numbering vs. template). */
  igg1_lala: {
    label: "IgG1 LALA-class (FcγR-silence motif)",
    ch1:
      "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKV",
    hinge: "EPKSCDKTHTCPPCP",
    ch2:
      "APELLGGPSVFLFPPKPKDTLMISRTPEVTCAAVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAK",
    ch3:
      "GQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  /** FcRn-recycling / half-life: EU ~M252Y/S254T/T256E on IgG1 CH2 (literature “YTE” class). */
  igg1_yte: {
    label: "IgG1 YTE-class (M252Y/S254T/T256E)",
    ch1:
      "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKV",
    hinge: "EPKSCDKTHTCPPCP",
    ch2:
      "APELLGGPSVFLFPPKPKDTLYITREPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAK",
    ch3:
      "GQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  igg2: {
    label: "IGHG2*01",
    ch1:
      "ASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSNFGTQT" + "YTCNVDHKPSNTKVDKTV",
    hinge: "ERKCCVECPPCP",
    ch2:
      "APPVAGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVQFNWYVDGVEVHNAKTKPREEQFNSTFRVVSVLTVVHQDWLNGKEYKCKVSNKGLPAPIEKTISKTK",
    ch3:
      "GQPREPQVYTLPPSREEMTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPMLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  igg4: {
    label: "IGHG4*01",
    ch1:
      "ASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKT" + "YTCNVDHKPSNTKVDKRV",
    hinge: "ESKYGPPCPSCP",
    ch2:
      "APEFLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSQEDPEVQFNWYVDGVEVHNAKTKPREEQFNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKGLPSSIEKTISKAK",
    ch3:
      "GQPREPQVYTLPPSQEEMTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSRLTVDKSRWQEGNVFSCSVMHEALHNHYTQKSLSLSLGK",
  },
  /** IgG4 hinge S228P (reduced Fab-arm exchange context; widely used in industry). */
  igg4_s228p: {
    label: "IgG4 S228P (hinge)",
    ch1:
      "ASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKT" + "YTCNVDHKPSNTKVDKRV",
    hinge: "ESKYGPPCPPCP",
    ch2:
      "APEFLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSQEDPEVQFNWYVDGVEVHNAKTKPREEQFNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKGLPSSIEKTISKAK",
    ch3:
      "GQPREPQVYTLPPSQEEMTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSRLTVDKSRWQEGNVFSCSVMHEALHNHYTQKSLSLSLGK",
  },
};

/** IGKC*01 / IGLC2*01 light-chain constant regions (aa). */
const CDNA_CL_REGION = {
  kappa:
    "RTVAAPSVFIFPPSDEQLKSGTASVVCLLNNFYPREAKVQWKVDNALQSGNSQESVTEQDSKDSTYSLSSTLTLSKADYEKHKVYACEVTHQGLSSPVTKSFNRGEC",
  lambda2:
    "GQPKAAPSVTLFPPSSEELQANKATLVCLISDFYPGAVTVAWKADSSPVKAGVETTTPSKQSNNKYAASSYLSLTPEQWKSHRSYSCQVTHEGSTVEKTVAPTECS",
};

const CDNA_SIGNAL_VHH = {
  human_ig: "MDMRVPAQLLGLLLLWFPGARC",
  tpa: "MDAMKRGLCCVLLLCGAVFVSPS",
  tpa_short: "MDAMKRGLCCVLLLCGAVFVS",
  ompa: "MKKTAIAIAVALAGFATVAQA",
  pelb: "MKYLLPTAAAGLLLLAAQPAMA",
};

const CDNA_VHH_FUSION_PARTS = {
  igg1_fc: {
    label: "Human IgG1 Fc (CH2-CH3)",
    seq: "APELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAKGQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  igg1_fch: {
    label: "Human IgG1 Fc (hinge+CH2-CH3)",
    seq: "EPKSCDKTHTCPPCPAPELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAKGQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK",
  },
  igg4_fc: {
    label: "Human IgG4 Fc (CH2-CH3)",
    seq: "APEFLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSQEDPEVQFNWYVDGVEVHNAKTKPREEQFNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKGLPSSIEKTISKAKGQPREPQVYTLPPSQEEMTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSRLTVDKSRWQEGNVFSCSVMHEALHNHYTQKSLSLSLGK",
  },
  igg4_fch: {
    label: "Human IgG4 Fc (hinge+CH2-CH3)",
    seq: "ESKYGPPCPSCPAPEFLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSQEDPEVQFNWYVDGVEVHNAKTKPREEQFNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKGLPSSIEKTISKAKGQPREPQVYTLPPSQEEMTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSRLTVDKSRWQEGNVFSCSVMHEALHNHYTQKSLSLSLGK",
  },
  hsa: {
    label: "Anti-HSA VHH (ALB8)",
    seq: "EVQLVESGGGLVQPGNSLRLSCAASGFTFSSFGMSWVRQAPGKGLEWVSSISGSGSDTLYADSVKGRFTISRDNAKTTLYLQMNSLRPEDTAVYYCTIGGSLSRSSQGTLVTVSST",
  },
};

const CDNA_VHH_LINKERS = {
  gs10: "GGGGSGGGGS",
  gs15: "GGGGSGGGGSGGGGS",
  gs20: "GGGGSGGGGSGGGGSGGGGS",
};

const CDNA_VHH_CLEAVAGE = {
  tev: "ENLYFQG",
  ek: "DDDDK",
  hrv3c: "LEVLFQGP",
};

const CDNA_VHH_TAGS = {
  his6: "HHHHHH",
  his8: "HHHHHHHH",
  flag: "DYKDDDDK",
  strep2: "WSHPQFEK",
  myc: "EQKLISEEDL",
  epea: "EPEA",
};

function resolveCdnaSignalPeptide(chain, selectId, customId) {
  const sel = document.getElementById(selectId);
  const cust = document.getElementById(customId);
  if (!sel) return "";
  const v = sel.value;
  if (v === "none") return "";
  if (v === "custom") return cust ? normalizeSeq(cust.value) : "";
  if (chain === "hc") return CDNA_SIGNAL_HC[v] || "";
  return CDNA_SIGNAL_LC[v] || "";
}

function assembleIggHeavyChainAa(vh, fcKey) {
  const p = CDNA_IGG_FC_PARTS[fcKey] || CDNA_IGG_FC_PARTS.igg1;
  return vh + p.ch1 + p.hinge + p.ch2 + p.ch3;
}

function assembleIggLightChainAa(vl, clKey) {
  const cl = CDNA_CL_REGION[clKey] || CDNA_CL_REGION.kappa;
  return vl + cl;
}

/** Standard genetic code, DNA → one-letter aa (stops *). */
const _CODON_TO_AA = {
  TTT: "F", TTC: "F", TTA: "L", TTG: "L",
  TCT: "S", TCC: "S", TCA: "S", TCG: "S",
  TAT: "Y", TAC: "Y", TAA: "*", TAG: "*",
  TGT: "C", TGC: "C", TGA: "*", TGG: "W",
  CTT: "L", CTC: "L", CTA: "L", CTG: "L",
  CCT: "P", CCC: "P", CCA: "P", CCG: "P",
  CAT: "H", CAC: "H", CAA: "Q", CAG: "Q",
  CGT: "R", CGC: "R", CGA: "R", CGG: "R",
  ATT: "I", ATC: "I", ATA: "I", ATG: "M",
  ACT: "T", ACC: "T", ACA: "T", ACG: "T",
  AAT: "N", AAC: "N", AAA: "K", AAG: "K",
  AGT: "S", AGC: "S", AGA: "R", AGG: "R",
  GTT: "V", GTC: "V", GTA: "V", GTG: "V",
  GCT: "A", GCC: "A", GCA: "A", GCG: "A",
  GAT: "D", GAC: "D", GAA: "E", GAG: "E",
  GGT: "G", GGC: "G", GGA: "G", GGG: "G",
};

/** Kazusa fraction (within amino acid) — Homo sapiens [taxid 9606], large CDS set. DNA keys. */
const KAZUSA_FRAC_HS_DNA = {
  TTT: 0.46, TTC: 0.54, TTA: 0.08, TTG: 0.13, CTT: 0.13, CTC: 0.2, CTA: 0.07, CTG: 0.4,
  TCT: 0.19, TCC: 0.22, TCA: 0.15, TCG: 0.05, AGT: 0.15, AGC: 0.24,
  TAT: 0.44, TAC: 0.56, TGT: 0.46, TGC: 0.54, TGG: 1,
  CCT: 0.29, CCC: 0.32, CCA: 0.28, CCG: 0.11,
  CAT: 0.42, CAC: 0.58, CAA: 0.27, CAG: 0.73,
  CGT: 0.08, CGC: 0.18, CGA: 0.11, CGG: 0.2, AGA: 0.21, AGG: 0.21,
  ATT: 0.36, ATC: 0.47, ATA: 0.17, ATG: 1,
  ACT: 0.25, ACC: 0.36, ACA: 0.28, ACG: 0.11,
  AAT: 0.47, AAC: 0.53, AAA: 0.43, AAG: 0.57,
  GTT: 0.18, GTC: 0.24, GTA: 0.12, GTG: 0.46,
  GCT: 0.27, GCC: 0.4, GCA: 0.23, GCG: 0.11,
  GAT: 0.46, GAC: 0.54, GAA: 0.42, GAG: 0.58,
  GGT: 0.16, GGC: 0.34, GGA: 0.25, GGG: 0.25,
};

/** Kazusa raw counts — Escherichia coli W3110 [316407]. DNA keys; stops omitted. */
const KAZUSA_COUNT_ECOLI_DNA = {
  TTT: 30462, TTC: 22705, TTA: 18894, TTG: 18664, TCT: 11512, TCC: 11802, TCA: 9620, TCG: 12210,
  TAT: 22037, TAC: 16795, TGT: 7016, TGC: 8797, TGG: 20889,
  CTT: 15082, CTC: 15272, CTA: 5266, CTG: 72898, CCT: 9540, CCC: 7490, CCA: 11569, CCG: 32080,
  CAT: 17791, CAC: 13399, CAA: 21121, CAG: 39835, CGT: 28866, CGC: 30530, CGA: 4810, CGG: 7401,
  ATT: 41644, ATC: 34568, ATA: 5733, ATG: 38167, ACT: 12119, ACC: 32265, ACA: 9452, ACG: 19820,
  AAT: 24106, AAC: 29581, AAA: 46116, AAG: 14174, AGT: 11924, AGC: 22067, AGA: 2771, AGG: 1496,
  GTT: 24991, GTC: 21050, GTA: 14901, GTG: 36108, GCT: 20813, GCC: 35252, GCA: 27567, GCG: 46524,
  GAT: 44217, GAC: 26270, GAA: 54431, GAG: 24629, GGT: 33875, GGC: 40849, GGA: 10774, GGG: 15115,
};

/** Kazusa raw counts — Saccharomyces cerevisiae [4932]. DNA keys; stops omitted. */
const KAZUSA_COUNT_YEAST_DNA = {
  TTT: 170666, TTC: 120510, TTA: 170884, TTG: 177573, TCT: 153557, TCC: 92923, TCA: 122028, TCG: 55951,
  TAT: 122728, TAC: 96596, TGT: 52903, TGC: 31095, TGG: 67789,
  CTT: 80076, CTC: 35545, CTA: 87619, CTG: 68494, CCT: 88263, CCC: 44309, CCA: 119641, CCG: 34597,
  CAT: 89007, CAC: 50785, CAA: 178251, CAG: 79121, CGT: 41791, CGC: 16993, CGA: 19562, CGG: 11351,
  ATT: 196893, ATC: 112176, ATA: 116254, ATG: 136805, ACT: 132522, ACC: 83207, ACA: 116084, ACG: 52045,
  AAT: 233124, AAC: 162199, AAA: 273618, AAG: 201361, AGT: 92466, AGC: 63726, AGA: 139081, AGG: 60289,
  GTT: 144243, GTC: 76947, GTA: 76927, GTG: 70337, GCT: 138358, GCC: 82357, GCA: 105910, GCG: 40358,
  GAT: 245641, GAC: 132048, GAA: 297944, GAG: 125717, GGT: 156109, GGC: 63903, GGA: 71216, GGG: 39359,
};

/** Per-codon fraction of its amino acid (sums to 1 per AA) from raw Kazusa counts. */
function buildCodonFractionWithinAaFromCounts(countMap) {
  const byAA = {};
  for (const [dna, ct] of Object.entries(countMap)) {
    const aa = _CODON_TO_AA[dna];
    if (!aa || aa === "*") continue;
    if (!byAA[aa]) byAA[aa] = [];
    byAA[aa].push([dna, ct]);
  }
  const out = {};
  for (const aa of Object.keys(byAA)) {
    const list = byAA[aa];
    const sum = list.reduce((s, p) => s + p[1], 0);
    for (const [dna, ct] of list) out[dna] = sum > 0 ? ct / sum : 0;
  }
  return out;
}

/** Within-AA reference fractions for rare-codon rule (same host mapping as CAI). */
const CODON_FRAC_WITHIN_AA = {
  mammal: KAZUSA_FRAC_HS_DNA,
  ecoli: buildCodonFractionWithinAaFromCounts(KAZUSA_COUNT_ECOLI_DNA),
  yeast: buildCodonFractionWithinAaFromCounts(KAZUSA_COUNT_YEAST_DNA),
};

function cdnaFracHostKey(host) {
  if (host === "ecoli") return "ecoli";
  if (host === "yeast") return "yeast";
  return "mammal";
}

/**
 * Count synonymous codons whose within-AA reference usage is strictly below `threshold` (default 10%).
 * Unknown triplets (e.g. NNN) are skipped.
 */
function countRareCodonsInCodingDna(codingDna, host, threshold) {
  const t = threshold != null ? threshold : 0.1;
  const fracMap = CODON_FRAC_WITHIN_AA[cdnaFracHostKey(host)] || CODON_FRAC_WITHIN_AA.mammal;
  const dna = String(codingDna || "")
    .toUpperCase()
    .replace(/\s/g, "");
  let n = 0;
  for (let i = 0; i + 3 <= dna.length; i += 3) {
    const c = dna.slice(i, i + 3);
    if (c.length < 3 || c.indexOf("N") >= 0) continue;
    const f = fracMap[c];
    if (f != null && f + 1e-12 < t) n++;
  }
  return n;
}

/** Overlapping 5′→3′ CG dinucleotides (may span codon junctions; includes sequence through stop). */
function countCpgDinucleotides(dnaStr) {
  const s = String(dnaStr || "").toUpperCase();
  let n = 0;
  for (let i = 0; i + 1 < s.length; i++) {
    if (s.charCodeAt(i) === 67 && s.charCodeAt(i + 1) === 71) n++;
  }
  return n;
}

function _buildRelAdaptFromFractions(fracByDna) {
  const byAA = {};
  for (const [dna, f] of Object.entries(fracByDna)) {
    const aa = _CODON_TO_AA[dna];
    if (!aa || aa === "*") continue;
    if (!byAA[aa]) byAA[aa] = [];
    byAA[aa].push({ dna, f });
  }
  const w = {};
  for (const aa of Object.keys(byAA)) {
    const list = byAA[aa];
    const mx = Math.max(...list.map((x) => x.f));
    for (const { dna, f } of list) w[dna] = mx > 0 ? f / mx : 0;
  }
  return w;
}

function _buildRelAdaptFromCounts(countMap) {
  const byAA = {};
  for (const [dna, ct] of Object.entries(countMap)) {
    const aa = _CODON_TO_AA[dna];
    if (!aa || aa === "*") continue;
    if (!byAA[aa]) byAA[aa] = [];
    byAA[aa].push({ dna, ct });
  }
  const w = {};
  for (const aa of Object.keys(byAA)) {
    const list = byAA[aa];
    const mx = Math.max(...list.map((x) => x.ct));
    for (const { dna, ct } of list) w[dna] = mx > 0 ? ct / mx : 0;
  }
  return w;
}

const CAI_WEIGHT_HEK293 = _buildRelAdaptFromFractions(KAZUSA_FRAC_HS_DNA);
const CAI_WEIGHT_CHO = CAI_WEIGHT_HEK293;
const CAI_WEIGHT_ECOLI = _buildRelAdaptFromCounts(KAZUSA_COUNT_ECOLI_DNA);
const CAI_WEIGHT_YEAST = _buildRelAdaptFromCounts(KAZUSA_COUNT_YEAST_DNA);

function caiWeightMapForHost(host) {
  if (host === "ecoli") return CAI_WEIGHT_ECOLI;
  if (host === "yeast") return CAI_WEIGHT_YEAST;
  return CAI_WEIGHT_HEK293;
}

/** Sharp & Li style: geometric mean of relative adaptiveness over coding triplets (stop excluded). */
function computeCaiFromDna(codingDna, wMap) {
  const dna = String(codingDna || "").toUpperCase().replace(/\s/g, "");
  let logSum = 0;
  let n = 0;
  for (let i = 0; i + 3 <= dna.length; i += 3) {
    const c = dna.slice(i, i + 3);
    if (c.length < 3) break;
    const ww = wMap[c];
    const v = ww != null && ww > 0 ? ww : 0.05;
    logSum += Math.log(v);
    n++;
  }
  if (n === 0) return null;
  return Math.exp(logSum / n);
}

/** Informative band text — not a pass/fail gate. */
function caiBandDescription(cai) {
  if (cai == null || Number.isNaN(cai)) return "—";
  if (cai >= 0.85) return "Strong match to reference synonymous bias (typical comfort zone)";
  if (cai >= 0.7) return "Moderate match — fine for many drafts; optimize further if titer is limiting";
  return "Below common “comfort” band — consider synonymous retuning for the chosen host";
}

const CDNA_CAI_NOTE_SHORT =
  "CAI is Codon Adaptation Index (0–1) from your output DNA vs Kazusa-style reference usage (human for HEK293/CHO; E. coli W3110; S. cerevisiae). It is an orientation metric only — no synthesis pass/fail cutoff in this console.";

const CDNA_RARE_CPG_NOTE =
  "Rare codons: triplets whose within–amino-acid fraction in the Kazusa reference (host-matched) is below 10%. CpG: overlapping 5′→3′ CG dinucleotides counted on the printed ORF (includes junctions and the TAA stop). Not a vendor gate.";

/** No conventional restriction-enzyme / MCS cut design in this demo (explicit non-scope). */
const CDNA_RE_SITES_NOTE =
  "This console does not enumerate or optimize conventional Type II restriction-enzyme recognition sites in the output DNA, does not silently remove sites for a chosen vector/MCS, and does not generate a restriction cut map. Subcloning and compatibility with your expression plasmid are out of scope — use your standard sequence/restriction tools and CRO rules; there is no RE-based cut / not-cut gate here.";

/** No uploaded legacy DNA — CAI/rare/CpG are reference-relative on the printed ORF only; true A/B is offline. */
const CDNA_EFFECT_NOTE =
  "There is no upload field for your previous (unoptimized) ORF or GenBank construct. The reported CAI, rare-codon count, and CpG count therefore apply only to the output DNA shown here, measured against the selected host’s Kazusa-style reference — they are orientation metrics, not a delta versus an existing plasmid. To quantify improvement versus a legacy sequence, compute the same metrics on both DNAs (same amino-acid sequence) in your own tools, or add a future feature that accepts a second FASTA as baseline.";

const CDNA_CAI_NOTE_REPORT = [
  "CAI (Codon Adaptation Index): geometric mean of relative adaptiveness for each codon vs the most-used synonymous codon in the reference table (Kazusa: Homo sapiens for HEK293/CHO, Escherichia coli W3110 for E. coli, Saccharomyces cerevisiae for yeast).",
  "Typical informal bands (literature / practice, not a standard): ≥ ~0.85 strong bias match; ~0.70–0.85 moderate; < ~0.70 often worth review if expression is the bottleneck.",
  "This console does not apply a hard cutoff for ordering DNA; follow your CMC, CRO, and program-specific rules.",
].join("\n");

/** One preferred codon per amino acid per host-like preset (demo simplification). */
const CDNA_CODON_TABLES = {
  cho: { A: "GCC", R: "CGG", N: "AAC", D: "GAC", C: "TGC", E: "GAG", Q: "CAG", G: "GGC", H: "CAC", I: "ATC", L: "CTG", K: "AAG", M: "ATG", F: "TTC", P: "CCC", S: "AGC", T: "ACC", W: "TGG", Y: "TAC", V: "GTG" },
  hek293: { A: "GCC", R: "AGA", N: "AAC", D: "GAC", C: "TGC", E: "GAG", Q: "CAG", G: "GGG", H: "CAC", I: "ATC", L: "CTG", K: "AAG", M: "ATG", F: "TTC", P: "CCC", S: "AGC", T: "ACC", W: "TGG", Y: "TAC", V: "GTG" },
  ecoli: { A: "GCT", R: "CGT", N: "AAT", D: "GAT", C: "TGT", E: "GAA", Q: "CAA", G: "GGT", H: "CAT", I: "ATT", L: "CTG", K: "AAA", M: "ATG", F: "TTT", P: "CCG", S: "AGC", T: "ACC", W: "TGG", Y: "TAT", V: "GTT" },
  yeast: { A: "GCT", R: "AGA", N: "AAT", D: "GAT", C: "TGT", E: "GAA", Q: "CAA", G: "GGT", H: "CAT", I: "ATT", L: "TTG", K: "AAG", M: "ATG", F: "TTT", P: "CCA", S: "TCT", T: "ACT", W: "TGG", Y: "TAT", V: "GTT" },
};

function generateOptimizedCdna(aaSeq, host) {
  const table = CDNA_CODON_TABLES[host] || CDNA_CODON_TABLES.cho;
  let dna = "";
  for (const aa of aaSeq) dna += table[aa] || "NNN";
  dna += "TAA";
  const codingOnly = dna.slice(0, -3);
  const caiRaw = computeCaiFromDna(codingOnly, caiWeightMapForHost(host));
  const cai = caiRaw != null ? Number(caiRaw.toFixed(4)) : null;
  const rareCount = countRareCodonsInCodingDna(codingOnly, host, 0.1);
  const cpgCount = countCpgDinucleotides(dna);
  return { seq: dna, cai, rareCount, cpgCount };
}

function analyzeVhToVhh(seq, demoId, source) {
  const isToripalimab = seq === DEMOS["toripalimab-vh"].seq;
  const isTislelizumab = seq === DEMOS["tislelizumab-vh"].seq;
  const isPembrolizumab = seq === DEMOS["pembrolizumab-vh"].seq;
  const isCamrelizumab = seq === DEMOS["camrelizumab-vh"].seq;
  const isNivolumab = seq === DEMOS["nivolumab-vh"].seq;
  const isMumab = seq === DEMOS["mumab4d5-vh"].seq;
  if (isTislelizumab) {
    return {
      status: "PASS", statusTone: "pass",
      summary: "Tislelizumab VH — Priority 1 VH→VHH candidate. CMC-favorable, CDR-H3 10 aa, externally validated (Mirzaei 2025).",
      germline: "IGHV3-66 — high compatibility with VHH scaffold. Framework-preserving camelization (Path C1).",
      cdrNote: "CDR-H3 (AYGNYWYIDV, 10 aa) within optimal VHH range. CDR-H2 (16 aa) standard. No length gate triggered.",
      route: "Strategy A — Framework-preserving camelization. Apply Kabat 44/45/47 + position-35/50 engineering.",
      routeShort: "Strategy A", routeTone: "ok",
      hallmarkStart: "GVHW", hallmark: "FR2 hallmark context is GVHW. Canonical G44E / L45R / W47F apply directly.",
      stealth: "Position 35 (H→N) and 50 (V→D) recommended per CDR2 gate. CDR-H3 surface favorable.",
      stealthShort: "35N + 50D", stealthTone: "ok",
      recommendationText: "Proceed with synthesis. Strong VAM priority: CDR-H3 Tyr97/Tyr102 → Arg to restore PD-1 affinity (validated by Mirzaei 2025).",
    };
  }
  if (isPembrolizumab) {
    return {
      status: "PASS", statusTone: "pass",
      summary: "Pembrolizumab VH — Scaffold-graft strategy recommended. CDR-H2 long (17 aa); GRAVY borderline.",
      germline: "IGHV3-23 — scaffold graft to IGHV3-23 VHH lineage recommended as primary strategy.",
      cdrNote: "CDR-H2 (17 aa) triggers CDR2 gate; Position-50 interface engineering bypassed. CDR-H3 (RDYRFDMGFDY, 11 aa) acceptable length but Phe cluster raises GRAVY.",
      route: "Strategy B — CDR graft to IGHV3-23 VHH scaffold. Hallmark pre-optimized in scaffold.",
      routeShort: "Strategy B (graft)", routeTone: "warn",
      hallmarkStart: "VGLW", hallmark: "Scaffold hallmark pre-configured. CDR-H1/H2/H3 grafted intact.",
      stealth: "GRAVY borderline (−0.513). CDR-H3 Phe100a/100b hydrophilization recommended pre-VAM.",
      stealthShort: "GRAVY fix needed", stealthTone: "warn",
      recommendationText: "Resolve GRAVY before synthesis — CDR-H3 Phe→Asp/Glu. Then VAM for affinity recovery.",
    };
  }
  if (isCamrelizumab) {
    return {
      status: "PASS", statusTone: "pass",
      summary: "Camrelizumab VH — VH HCDR1/HCDR2 contact PD-1 N58 glycan (PDB 7CU5). Glycan contacts are VH-mediated and retained in VHH.",
      germline: "IGHV1-46 — framework-preserving camelization (Path C1). CMC within window.",
      cdrNote: "CDR-H3 (VEGYGNSNGMDV, 12 aa) acceptable. Glycan contacts: HCDR1 S30/S31 + HCDR2 G53/G54/A56 — all VH-derived, preserved in VHH. VL role was PD-L1 steric competition only.",
      route: "Strategy A — Framework-preserving camelization. Verify PD-L1 blocking efficiency post-conversion by SPR.",
      routeShort: "Strategy A", routeTone: "ok",
      hallmarkStart: "GFTF", hallmark: "FR2 hallmark context: G44E / L45R / W47F. Position-35 (S→N) engineering recommended.",
      stealth: "CDR-H3 N101 deamidation risk — N101→Q protective substitution recommended.",
      stealthShort: "N101Q protect", stealthTone: "warn",
      recommendationText: "Synthesize with N101Q. Verify PD-1 binding and PD-L1 competition vs native and N58A PD-1. VAM if functional validation passes.",
    };
  }
  if (isNivolumab) {
    return {
      status: "CAUTION", statusTone: "warn",
      summary: "Nivolumab VH — CDR-H3 = 4 aa (TNDD). Below minimum functional threshold for VHH standalone binding.",
      germline: "IGHV3-33 — framework convertible, but CDR-H3 length is the fundamental barrier.",
      cdrNote: "CDR-H3 of 4 aa insufficient for independent antigen contact after VL removal. CDR-H1/H2 contacts (Ile32, Trp52) valuable. De-novo CDR-H3 redesign required.",
      route: "De-novo CDR-H3 redesign — preserve CDR-H1/H2; design new 8–12 aa CDR-H3 from PD-1 contact interface (PDB 5WT9).",
      routeShort: "De-novo CDR-H3", routeTone: "warn",
      hallmarkStart: "VGLW", hallmark: "Hallmark engineering applicable at FR2 (44/45/47). Direct conversion not recommended.",
      stealth: "Multiple CMC flags: pI 9.01, SAP 0.857 (RED), instability 40.7. Address in de-novo redesign.",
      stealthShort: "CMC FAIL — redesign", stealthTone: "warn",
      recommendationText: "Not recommended for direct conversion. De-novo CDR-H3 design (8–12 aa) or 4-valent VHH-Fc format to leverage Avidity.",
    };
  }
  if (isToripalimab) {
    return {
      status: "CAUTION", statusTone: "warn",
      summary: "Toripalimab VH — pI = 4.68 is a BLOCKER. Net charge −4.2 at pH 7 prevents direct VHH development.",
      germline: "IGHV3-66 (same as Tislelizumab) — framework convertible but CDR3/charge composition makes direct VHH unfeasible without pI correction.",
      cdrNote: "CDR-H3 (EGITTVATTYYWYFD, 16 aa) — longest in PD-1 panel; Asp/Glu residues are primary cause of low pI. VHH window requires pI 6.5–9.5.",
      route: "FR charge compensation required first: introduce 1–3 Arg/Lys in FR3/FR4 to lift pI above 6.5, then re-evaluate.",
      routeShort: "pI fix first", routeTone: "warn",
      hallmarkStart: "VGLW", hallmark: "FR2 hallmark (VGLW) same as Tislelizumab. Hallmark engineering is not the limiting factor.",
      stealth: "pI 4.68 is the primary blocker — resolve before any interface engineering.",
      stealthShort: "pI BLOCKER", stealthTone: "warn",
      recommendationText: "Resolve pI first via FR charge compensation or CDR-H3 acid residue reduction. Re-evaluate after pI > 6.5.",
    };
  }
  if (isMumab) {
    return {
      status: "PASS", statusTone: "pass",
      summary: "mumab4d5 supports the validated dual-path model: Strategy A primary, scaffold graft secondary.",
      germline: "Validated benchmark shows strongest continuity when Strategy A is prioritized; scaffold grafting as secondary comparison path only.",
      cdrNote: "Long CDR2 context raises risk for aggressive interface rewiring; preserving the native fold core is preferred.",
      route: "Strategy A primary, Strategy B retained only as secondary / comparison branch.",
      routeShort: "A primary", routeTone: "ok",
      hallmarkStart: "VGLW", hallmark: "Hallmark engineering necessary but benchmark favors controlled FR2 edits over full scaffold replacement.",
      stealth: "Interface optimization is case-specific; tied to loop context.",
      stealthShort: "Case-specific", stealthTone: "ok",
      recommendationText: "Use Strategy A first and benchmark scaffold graft only as secondary route.",
    };
  }
  return {
    status: "CAUTION", statusTone: "warn",
    summary: "Generic VH submission — light feasibility read only. Full conversion requires offline workflow.",
    germline: `Source class: ${source}. Full germline and CDR-resolution conversion requires offline converter path.`,
    cdrNote: "Without validated conversion backend, loop-sensitive decisions are advisory only.",
    route: "Default to Strategy A unless validated scaffold-graft benchmark exists for same family and loop context.",
    routeShort: "Advisory A", routeTone: "warn",
    hallmarkStart: "Unknown", hallmark: "FR2 hallmark start not numbered. Treat this as pre-check, not final engineering decision.",
    stealth: "Interface optimization advisory only in web mode.",
    stealthShort: "Advisory", stealthTone: "warn",
    recommendationText: "Use as feasibility screen only. For an actionable conversion package, move to the offline VH→VHH workflow.",
  };
}

function detectVhhRoute(seq, mode) {
  if (mode === "vhh" || mode === "vh") return mode;
  if (/QVQLVESGGG|EVQLVESGGG|QVKLEESGGG|QAPGKEREG/.test(seq)) return "vhh";
  return "vh";
}

function renderFrSequenceCandidates(sc, ms) {
  // sc = sequence_candidates block; ms = mutation_sequences block (optional)
  if (!sc || typeof sc !== "object") return "";
  const parts = [];
  if (sc.enumeration_note) {
    parts.push(`<p class="muted" style="font-size:10px;margin:0 0 6px 0">${escapeHtml(String(sc.enumeration_note))}</p>`);
  }
  const sites = sc.fr_positive_charge_sites;
  if (sites && sites.length) {
    parts.push(`<div style="font-size:10px;font-weight:600;margin:6px 0 4px 0">FR candidate sites (K/R → reduce positive charge / pI drivers)</div>
      <table class="kv-table" style="font-size:10px">
      <tr><th>Chain</th><th>Pos</th><th>IMGT</th><th>Suggested</th><th>Local sequence</th><th>SASA</th></tr>
      ${sites.map(x => `<tr><td>${escapeHtml(x.chain || "—")}</td><td>${x.index_1 != null ? x.index_1 : "—"}</td><td>${x.imgt != null ? x.imgt : "—"}</td><td>${escapeHtml(x.from_aa || "?")}→${escapeHtml(x.to_aa_hint || "?")} <span class="muted">(${escapeHtml(x.region || "")})</span></td><td class="mono" style="max-width:220px;word-break:break-all">${escapeHtml(x.window || "—")}</td><td class="muted">${x.sasa_rel != null ? (x.sasa_rel * 100).toFixed(0) + "%" : "—"}</td></tr>`).join("")}
      </table>`);
    // Mutated sequences for charge sites
    if (ms) {
      for (const key of ["charge_vh", "charge_vl"]) {
        const msBlock = ms[key];
        if (!msBlock) continue;
        const chainLabel = key === "charge_vh" ? "VH" : "VL";
        const muts = (msBlock.mutations || []).map(m => `${m.pos}${m.from}→${m.to}`).join(", ");
        parts.push(`<div style="margin-top:6px;padding:6px 8px;background:rgba(201,162,39,.07);border-radius:4px;font-size:10px">
          <div style="font-weight:600;margin-bottom:3px">${chainLabel} optimized sequence (${muts}):</div>
          <div class="mono" style="word-break:break-all;line-height:1.6;font-size:10px">${_highlightMutations(msBlock.original, msBlock.mutant)}</div>
        </div>`);
      }
    }
  }
  const negSites2 = sc.fr_negative_charge_sites;
  if (negSites2 && negSites2.length) {
    parts.push(`<div style="font-size:10px;font-weight:600;margin:8px 0 4px 0">FR candidate sites (D/E → reduce negative patch)</div>
      <table class="kv-table" style="font-size:10px">
      <tr><th>Chain</th><th>Pos</th><th>IMGT</th><th>Suggested</th><th>Local sequence</th><th>SASA</th></tr>
      ${negSites2.map(x => `<tr><td>${escapeHtml(x.chain || "—")}</td><td>${x.index_1 != null ? x.index_1 : "—"}</td><td>${x.imgt != null ? x.imgt : "—"}</td><td>${escapeHtml(x.from_aa || "?")}→${escapeHtml(x.to_aa_hint || "?")} <span class="muted">(${escapeHtml(x.region || "")})</span></td><td class="mono" style="max-width:220px;word-break:break-all">${escapeHtml(x.window || "—")}</td><td class="muted">${x.sasa_rel != null ? (x.sasa_rel * 100).toFixed(0) + "%" : "—"}</td></tr>`).join("")}
      </table>`);
  }
  // Instability dipeptide motif sites
  const instSites = sc.fr_instability_sites;
  if (instSites && instSites.length) {
    parts.push(`<div style="font-size:11px;font-weight:600;margin:8px 0 5px 0;color:var(--warn)">FR instability motif sites (destabilizing dipeptides)</div>
      <table class="kv-table" style="font-size:11px">
      <tr><th>Chain</th><th>Pos</th><th>IMGT</th><th>Motif</th><th>Suggested</th><th>Local sequence</th><th>SASA</th></tr>
      ${instSites.map(x => `<tr>
        <td>${escapeHtml(x.chain || "—")}</td>
        <td><strong>${x.index_1 != null ? x.index_1 : "—"}</strong></td>
        <td>${x.imgt != null ? x.imgt : "—"}</td>
        <td class="mono" style="color:var(--warn);font-weight:700">${escapeHtml(x.motif || "?")}</td>
        <td>${escapeHtml(x.from_aa || "?")}→<strong style="color:#c9a227">${escapeHtml(x.to_aa_hint || "?")}</strong> <span class="muted">(${escapeHtml(x.region || "")})</span></td>
        <td class="mono" style="max-width:180px;word-break:break-all">${escapeHtml(x.window || "—")}</td>
        <td class="muted">${x.sasa_rel != null ? (x.sasa_rel * 100).toFixed(0) + "%" : "—"}</td>
      </tr>`).join("")}
      </table>`);
  }
  const runs = sc.fr_hydrophobic_runs;
  if (runs && runs.length) {
    const runRows = runs.map(x => {
      const spanLabel = x.start_1 != null && x.end_1 != null ? x.start_1 + "–" + x.end_1 : "—";
      const sasaCell = x.sasa_rel_mean != null ? (x.sasa_rel_mean * 100).toFixed(0) + "%" : "—";
      let html = `<tr style="background:rgba(201,162,39,.05)">
        <td>${escapeHtml(x.chain || "—")}</td>
        <td><strong>${spanLabel}</strong></td>
        <td class="mono" style="font-weight:700;font-size:12px">${escapeHtml(x.segment || "—")}</td>
        <td class="mono" style="max-width:180px;word-break:break-all;font-size:10px">${escapeHtml(x.window || "—")}</td>
        <td class="muted">${sasaCell}</td>
      </tr>`;
      const pr = Array.isArray(x.per_residue) ? x.per_residue : [];
      if (pr.length) {
        const prCells = pr.map(p => {
          const sasa = p.sasa_rel != null ? ` <span class="muted" style="font-size:9px">${(p.sasa_rel*100).toFixed(0)}%</span>` : "";
          const caution = p.caution ? ` <span title="${escapeHtml(p.caution)}" style="color:var(--warn);cursor:help">⚠</span>` : "";
          return `<span class="mono" style="white-space:nowrap;margin-right:12px;font-size:12px"><strong>${escapeHtml(p.index_1 != null ? String(p.index_1) : "?")}</strong><sub style="color:var(--muted);font-size:9px">${escapeHtml(p.region || "")}</sub> ${escapeHtml(p.from_aa || "")}→<strong style="color:#c9a227;font-size:13px">${escapeHtml(p.to_aa_hint || "")}</strong>${sasa}${caution}</span>`;
        }).join("");
        html += `<tr><td colspan="5" style="padding:4px 6px 10px 18px;font-size:11px">
          <span style="color:var(--muted);font-size:10px">Mutation hints: </span>${prCells}
        </td></tr>`;
      }
      return html;
    }).join("");
    parts.push(`<div style="font-size:11px;font-weight:600;margin:8px 0 5px 0">FR hydrophobic runs — specific mutation sites</div>
      <table class="kv-table" style="font-size:11px">
      <tr><th>Chain</th><th>Span</th><th>Segment</th><th>Context</th><th>SASA</th></tr>
      ${runRows}
      </table>`);
    // Mutated sequences for hydrophobic runs
    if (ms && Array.isArray(ms.hydro_runs) && ms.hydro_runs.length) {
      const runSeqs = ms.hydro_runs.map(rr => {
        const muts = (rr.mutations || []).map(m => `${m.pos}${m.from}→${m.to}`).join(", ");
        return `<div style="padding:6px 8px;margin-bottom:4px;background:rgba(201,162,39,.07);border-radius:4px">
          <div style="font-weight:600;font-size:10px;margin-bottom:3px">${escapeHtml(rr.chain || "")} optimized sequence (pos ${escapeHtml(rr.span || "")} — ${muts}):</div>
          <div class="mono" style="word-break:break-all;line-height:1.6;font-size:10px">${_highlightMutations(rr.original_seq, rr.mutant_seq)}</div>
        </div>`;
      }).join("");
      parts.push(`<div style="margin-top:6px">${runSeqs}</div>`);
    }
  }
  if (!parts.length) return "";
  return `<div style="margin-top:6px;padding:8px;background:rgba(33,199,217,.06);border-radius:4px;border:1px solid rgba(33,199,217,.2)">${parts.join("")}</div>`;
}

function formatRefPosition(pos) {
  const MAP = {
    "central_reference_band":  "p25–p75 (core)",
    "outer_reference_band":    "p5–p95 (broad)",
    "outside_reference_band":  "Outside p5–p95",
    "favorable_to_typical":    "≤ p75 (favorable)",
    "upper_reference_band":    "p75–p95 (elevated)",
    "not_available":           "—",
    "no_reference":            "—",
    "incomplete_reference":    "—",
  };
  return MAP[pos] || (pos ? pos.replace(/_/g, " ") : "—");
}

function buildArtifacts(data, opts) {
  opts = opts || {};
  const htmlZipOnly = opts.htmlZipOnly === true;
  const list = [];
  const res = data.result || {};
  const ex = data.extra || {};
  const joinU = (u) => apiJoin(String(u || "").replace(/^\/+/, ""));
  const reportUrl = data.report_url || ex.report_url || res.report_url;
  if (reportUrl) {
    const ru = String(reportUrl || "");
    const isHtml = /\.html?(\?|$)/i.test(ru) || /humanization_report\.html/i.test(ru) || /CMC_Report\.html/i.test(ru) || /VHH_CMC_Report\.html/i.test(ru) || /bispecific_cmc_report\.html/i.test(ru) || /recheck_report\.html/i.test(ru) || /vh2vhh_report\.html/i.test(ru);
    if (isHtml) {
      list.push({ label: "View Report (HTML)", url: joinU(reportUrl), primary: true });
      list.push({ label: "Save Report (HTML)", url: joinU(reportUrl), download: true });
    } else {
      list.push({ label: "Download Generated Report", url: joinU(reportUrl), download: true, primary: true });
    }
  }
  const zipUrl = ex.zip_url || res.zip_url || data.zip_url;
  if (zipUrl) {
    list.push({label: "Download delivery bundle (ZIP)", url: joinU(zipUrl)});
  }
  if (htmlZipOnly) {
    return list;
  }
  const fastaUrl = ex.fasta_url || res.fasta_url;
  if (fastaUrl) {
    list.push({label: "Download sequences (FASTA)", url: joinU(fastaUrl), download: true});
  }
  const pdfUrl = ex.pdf_report_url || res.pdf_report_url;
  if (pdfUrl) {
    list.push({label: "Download PDF Report", url: joinU(pdfUrl)});
  }
  const fvSt = res.fv_structure;
  if (fvSt && fvSt.pdb_url) {
    list.push({
      label: "Download Fv model (PDB)",
      url: joinU(fvSt.pdb_url),
      download: true,
    });
  }
  const pdbUrls = res.pdb_urls || {};
  const pdbLabels = {
    donor_ab: "PDB — donor Fv (donor_ab.pdb)",
    humanized_ab: "PDB — humanized Fv (humanized_ab.pdb)",
  };
  for (const [key, label] of Object.entries(pdbLabels)) {
    const u = pdbUrls[key];
    if (u) list.push({label, url: joinU(u), download: true});
  }
  return list;
}

function sectionToReportHtml(s) {
  const title = escapeHtml(s.title);
  if (s && s.kind === "domains" && s.plan && s.aa != null) {
    const inner = reportHtmlDomainStrip(s.plan, String(s.aa), { showLinear: s.showLinear !== false });
    return `<section class="rep-block"><h2>${title}</h2>${inner}</section>`;
  }
  if (s && s.kind === "dna" && s.seq != null) {
    const inner = reportHtmlDnaStrip(s.dnaLabel || "", String(s.seq));
    return `<section class="rep-block"><h2>${title}</h2>${inner}</section>`;
  }
  if (s && s.kind === "kv" && Array.isArray(s.rows)) {
    const trs = s.rows
      .map(([k, v]) => `<tr><th scope="row">${escapeHtml(String(k))}</th><td>${escapeHtml(String(v))}</td></tr>`)
      .join("");
    return `<section class="rep-block"><h2>${title}</h2><table class="rep-kv"><tbody>${trs}</tbody></table></section>`;
  }
  const raw = s.body == null ? "" : String(s.body);
  const lines = raw.split(/\r?\n/).filter((ln) => ln.length > 0);
  const isNumberingTitle = /numbering/i.test(s.title || "");
  const tsvRows = lines.filter((ln) => ln.includes("\t"));
  if (isNumberingTitle && tsvRows.length) {
    const tbody = tsvRows.map((line) => {
      const tab = line.indexOf("\t");
      const label = tab >= 0 ? line.slice(0, tab) : line;
      const aa = tab >= 0 ? line.slice(tab + 1) : "";
      return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(aa)}</td></tr>`;
    }).join("");
    return `<section class="rep-block"><h2>${title}</h2><table class="rep-table"><thead><tr><th>Position (scheme label)</th><th>Aa</th></tr></thead><tbody>${tbody}</tbody></table></section>`;
  }
  return `<section class="rep-block"><h2>${title}</h2><div class="rep-plain"><pre>${escapeHtml(raw)}</pre></div></section>`;
}

function createClientReport({title, service, analysisVersion, sections, generatedAtLocal, runRecordId, schemeLabel}) {
  if (state.currentArtifactUrl && state.currentArtifactUrl.startsWith("blob:")) {
    URL.revokeObjectURL(state.currentArtifactUrl);
  }
  const body = sections.map(sectionToReportHtml).join("");
  const metaLines = [
    `Service: ${escapeHtml(service)}`,
    `Analysis version: ${escapeHtml(analysisVersion)}`,
  ];
  if (schemeLabel) metaLines.push(`Numbering scheme: ${escapeHtml(schemeLabel)}`);
  if (generatedAtLocal) metaLines.push(`Client time (local): ${escapeHtml(generatedAtLocal)}`);
  if (runRecordId) metaLines.push(`Run ID: ${escapeHtml(runRecordId)}`);
  const metaHtml = metaLines.join("<br>");
  const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${escapeHtml(title)}</title>
<style>
  :root { --rep-bg:#f4f6f9; --rep-card:#fff; --rep-line:#e2e6ee; --rep-muted:#64748b; --rep-text:#0f172a; --rep-accent:#0d9488; --rep-sp:#6366f1; --rep-vd:#059669; --rep-const:#d97706; --rep-hinge:#db2777; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height:1.55; color:var(--rep-text); background: linear-gradient(180deg, #eef2f7 0%, var(--rep-bg) 120px); min-height:100vh; }
  .rep-shell { max-width: 920px; margin: 0 auto; padding: 28px 22px 48px; }
  h1 { font-size: 1.45rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 8px; color: #0c1222; }
  .meta { color: var(--rep-muted); font-size: 13px; margin-bottom: 28px; padding: 12px 16px; background: var(--rep-card); border: 1px solid var(--rep-line); border-radius: 10px; }
  .rep-block { background: var(--rep-card); border: 1px solid var(--rep-line); border-radius: 12px; padding: 18px 20px 22px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(15,23,42,.06); }
  .rep-block h2 { margin: 0 0 14px; font-size: 1.05rem; font-weight: 650; color: #1e293b; padding-bottom: 10px; border-bottom: 1px solid var(--rep-line); }
  .rep-plain pre { margin:0; white-space:pre-wrap; word-break:break-all; font-family: ui-monospace, "Cascadia Mono", "Segoe UI Mono", Consolas, monospace; font-size: 12px; line-height: 1.45; background: #f8fafc; padding: 14px; border-radius: 8px; border: 1px solid var(--rep-line); color: #334155; }
  table.rep-kv { width:100%; border-collapse: collapse; font-size: 14px; }
  table.rep-kv th { text-align:left; width: 34%; color: var(--rep-muted); font-weight: 500; padding: 8px 12px 8px 0; vertical-align: top; border-bottom: 1px solid var(--rep-line); }
  table.rep-kv td { padding: 8px 0; vertical-align: top; border-bottom: 1px solid var(--rep-line); }
  table.rep-kv tr:last-child th, table.rep-kv tr:last-child td { border-bottom: none; }
  .rep-domain-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
  .rep-dom { flex: 1 1 160px; min-width: 0; border: 1px solid var(--rep-line); border-radius: 10px; overflow: hidden; background: #fafbfc; }
  .rep-dom header { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; padding: 8px 10px; font-size: 11px; border-bottom: 1px solid var(--rep-line); background: linear-gradient(180deg, #fff 0%, #f8fafc 100%); }
  .rep-dom-t { font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--rep-accent); font-size: 10px; }
  .rep-dom-n { color: var(--rep-muted); font-size: 11px; font-weight: 500; }
  .rep-dom-s { margin: 0; padding: 10px 10px 12px; white-space: pre-wrap; word-break: break-all; font-family: ui-monospace, Consolas, monospace; font-size: 11px; line-height: 1.4; color: #334155; }
  .rep-dom-sp { border-left: 4px solid var(--rep-sp); }
  .rep-dom-vd { border-left: 4px solid var(--rep-vd); }
  .rep-dom-const { border-left: 4px solid var(--rep-const); }
  .rep-dom-hinge { border-left: 4px solid var(--rep-hinge); }
  .rep-dom-warn { border-left: 4px solid #dc2626; background: #fef2f2; }
  .rep-linear { margin-top: 4px; }
  .rep-linear-t { font-size: 11px; color: var(--rep-muted); margin-bottom: 6px; font-weight: 500; }
  .rep-seq { margin: 0; white-space: pre-wrap; word-break: break-all; font-family: ui-monospace, Consolas, monospace; font-size: 11px; line-height: 1.4; padding: 12px 14px; background: #f1f5f9; border-radius: 8px; border: 1px dashed var(--rep-line); color: #1e293b; }
  .rep-dna-card { margin-top: 4px; border-radius: 10px; overflow: hidden; border: 1px solid #c7d2fe; background: linear-gradient(180deg, #eef2ff 0%, #fff 48px); }
  .rep-dna-cap { padding: 10px 14px; font-size: 12px; font-weight: 600; color: #3730a3; border-bottom: 1px solid #c7d2fe; }
  .rep-dna-h { font-weight: 500; color: var(--rep-muted); margin-left: 6px; }
  pre.rep-dna { margin: 0; padding: 12px 14px 16px; white-space: pre-wrap; word-break: break-all; font-family: ui-monospace, Consolas, monospace; font-size: 11px; line-height: 1.42; color: #1e3a5f; background: #fff; }
  table.rep-table{border-collapse:collapse;width:100%;font-size:14px}
  table.rep-table th,table.rep-table td{border:1px solid var(--rep-line);padding:8px 10px;text-align:left}
  table.rep-table th{background:#f1f5f9;font-weight:600}
  @media print { body { background: #fff; } .rep-block { break-inside: avoid; box-shadow: none; } }
</style></head><body>
<div class="rep-shell">
<h1>${escapeHtml(title)}</h1>
<div class="meta">${metaHtml}</div>
${body}
</div>
</body></html>`;
  const url = URL.createObjectURL(new Blob([html], {type: "text/html"}));
  state.currentArtifactUrl = url;
  return url;
}

// ── Petization (internal) ─────────────────────────────────────────────────────

const PET_DEMOS = {
  "tanezumab-dog": {
    label: "Tanezumab → Dog (caninization)",
    species: "dog",
    vh: "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARDHRDAMDRWGQGTLVTVSS",
    vl: "DIQMTQSPSSLSASVGDRVTITCRASQGIRNDLGWYQQKPGKAPKRLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDVATYYCQQSYSTPYTFGQGTKVEIK",
  },
  "tanezumab-cat": {
    label: "Tanezumab → Cat (felinization)",
    species: "cat",
    vh: "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARDHRDAMDRWGQGTLVTVSS",
    vl: "DIQMTQSPSSLSASVGDRVTITCRASQGIRNDLGWYQQKPGKAPKRLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDVATYYCQQSYSTPYTFGQGTKVEIK",
  },
};

function renderPetizationForm(service) {
  const demoOpts = Object.entries(PET_DEMOS)
    .map(([k, v]) => `<option value="${k}">${escapeHtml(v.label)}</option>`)
    .join("");
  return `
    <section class="surface panel">
      <div class="panel-label">Internal — requires INSYNBIO_INTERNAL_PET_CONSOLE=1</div>
      <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:10px 14px;font-size:11px;color:#f87171;margin-bottom:14px">
        ⚠ This service is for internal engineering use only. Do not share outputs externally without owner approval.
      </div>
      <div class="form-grid">
        <div class="field"><label>Demo case</label>
          <select id="pet-demo" onchange="loadServiceDemo()">${demoOpts}</select>
        </div>
        <div class="field"><label>Target species</label>
          <select id="pet-species">
            <option value="dog">Dog (caninization)</option>
            <option value="cat">Cat (felinization)</option>
          </select>
        </div>
        <div class="field"><label>Strategy</label>
          <select id="pet-strategy">
            <option value="auto">Auto (recommended)</option>
            <option value="graft_vernier">Graft + Vernier</option>
            <option value="surface_reshaping">Surface Reshaping</option>
            <option value="deep_fr_anchor">Deep FR Anchor</option>
          </select>
        </div>
        <div class="field full"><label>Project name <span class="muted" style="font-weight:400;font-size:11px">(optional)</span></label>
          <input type="text" id="pet-name" placeholder="e.g. Tanezumab-dog-v1" maxlength="80" style="font-family:var(--font-mono,monospace)">
        </div>
        <div class="field full"><label>VH sequence</label>
          <textarea id="pet-vh" rows="3" placeholder="Donor VH amino acid sequence (min 100 aa)"></textarea>
        </div>
        <div class="field full"><label>VL sequence</label>
          <textarea id="pet-vl" rows="3" placeholder="Donor VL amino acid sequence (min 100 aa)"></textarea>
        </div>
        <div class="field full">
          <details style="font-size:11px;color:var(--muted)">
            <summary style="cursor:pointer;font-weight:500">Advanced anchor positions (optional)</summary>
            <div class="form-grid" style="margin-top:10px">
              <div class="field"><label style="font-size:11px">VH anchor Kabat positions</label>
                <input type="text" id="pet-vh-anchors" placeholder="e.g. 48,67,71" style="font-size:11px">
              </div>
              <div class="field"><label style="font-size:11px">VL anchor Kabat positions</label>
                <input type="text" id="pet-vl-anchors" placeholder="e.g. 36,46,71" style="font-size:11px">
              </div>
            </div>
          </details>
        </div>
      </div>
      <div class="button-row">
        <button class="btn" onclick="loadServiceDemo()">Load Demo</button>
        <button class="btn primary" onclick="runCurrentService()">Run Petization</button>
      </div>
      <div class="helper" id="pet-helper"></div>
      <div class="status-box" id="service-status"></div>
    </section>
    <section class="workspace-output" id="workspace-output"></section>
  `;
}

async function runPetization(service) {
  const vh = (document.getElementById("pet-vh")?.value || "").trim().replace(/\s/g, "").toUpperCase();
  const vl = (document.getElementById("pet-vl")?.value || "").trim().replace(/\s/g, "").toUpperCase();
  const species = document.getElementById("pet-species")?.value || "dog";
  const strategy = document.getElementById("pet-strategy")?.value || "auto";
  const name = (document.getElementById("pet-name")?.value || "").trim() || `${species}-petization`;
  const vhAnchors = (document.getElementById("pet-vh-anchors")?.value || "").trim();
  const vlAnchors = (document.getElementById("pet-vl-anchors")?.value || "").trim();

  const helper = document.getElementById("pet-helper");
  const statusBox = document.getElementById("service-status");
  const output = document.getElementById("workspace-output");

  const errors = [];
  if (!vh || vh.length < 80) errors.push("VH sequence must be at least 80 amino acids.");
  if (!vl || vl.length < 80) errors.push("VL sequence must be at least 80 amino acids.");
  if (errors.length) { setOutput(errorPanel(errors.join("\n"))); return; }

  if (helper) helper.textContent = "Sending to API…";
  if (statusBox) statusBox.textContent = "";

  const apiBase = (document.getElementById("api-endpoint")?.value || "").trim().replace(/\/$/, "") || "";

  try {
    const resp = await fetch(`${apiBase}/internal/petization/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vh,
        vl,
        species,
        strategy,
        vh_anchor_positions: vhAnchors,
        vl_anchor_positions: vlAnchors,
      }),
    });
    if (helper) helper.textContent = "";
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      setOutput(errorPanel(`API error ${resp.status}: ${err.detail || JSON.stringify(err)}`));
      return;
    }
    const result = await resp.json();
    renderPetizationResult(result, name, service);
  } catch (e) {
    if (helper) helper.textContent = "";
    setOutput(errorPanel(`Network error: ${e.message || e}`));
  }
}

function renderPetizationResult(r, name, service) {
  const status = r.overall_status || "?";
  const statusColor = status === "PASS" ? "var(--pass)" : status === "WARN" ? "var(--warn)" : "var(--fail)";
  const strategy = r.strategy_selected || "?";
  const sel = r.selection || {};
  const seqs = r.sequences || {};
  const mut = r.mutations || {};
  const cmc = r.cmc || {};
  const shm = r.fr_shm_auto_detected || {};
  const sg = r.surface_guidance || {};
  const qa = r._qa_audit || {};
  const sqc = qa.structure_qc || null;

  function badge(v) {
    const c = v === "PASS" ? "var(--pass)" : v === "WARN" ? "var(--warn)" : "var(--fail)";
    const rawC = v === "PASS" ? "#22c55e" : v === "WARN" ? "#f59e0b" : "#ef4444"; // Fallback for color opacity logic if needed, but we'll use a safer approach
    return `<span style="display:inline-block;padding:1px 7px;border-radius:4px;font-size:11px;font-weight:700;background:rgba(128,128,128,0.1);color:${c};border:1px solid ${c}">${v}</span>`;
  }
  function mono(s) { return `<code style="font-size:11px;word-break:break-all;color:#93c5fd">${escapeHtml(s || "")}</code>`; }
  function row(k, v) { return `<tr><td style="color:var(--muted);width:38%;padding:5px 8px;vertical-align:top">${k}</td><td style="padding:5px 8px">${v}</td></tr>`; }

  const mutVh = (mut.vh_backmutations || mut.vh_surface_reshaping || []);
  const mutVl = (mut.vl_backmutations || mut.vl_surface_reshaping || []);
  const mutSummary = (mutVh.length + mutVl.length) === 0
    ? "No mutations (sequences unchanged)"
    : `VH: ${mutVh.length} changes · VL: ${mutVl.length} changes`;

  const flagsHtml = (cmc.vh?.species_flags || []).concat(cmc.vl?.species_flags || [])
    .map(f => `<div style="font-size:11px;padding:4px 8px;margin:3px 0;border-radius:5px;background:${f.severity==="FAIL"?"rgba(239,68,68,.1)":"rgba(245,158,11,.1)"};color:${f.severity==="FAIL"?"#f87171":"#fbbf24"}">${f.flag}: ${f.detail}</div>`)
    .join("") || `<span style="color:var(--muted);font-size:11px">No CMC flags</span>`;

  const shmNote = (shm.vh?.length || shm.vl?.length)
    ? `VH: [${(shm.vh||[]).join(", ")}] · VL: [${(shm.vl||[]).join(", ")}]`
    : "None detected";

  const sqcHtml = sqc
    ? `<tr><td style="color:var(--muted);width:38%;padding:5px 8px">Structure QC</td><td style="padding:5px 8px">${badge(sqc.status)} ${sqc.prediction?.tool || ""} ${sqc.errors?.length ? "· " + sqc.errors[0] : ""}</td></tr>`
    : `<tr><td style="color:var(--muted);width:38%;padding:5px 8px">Structure QC</td><td style="padding:5px 8px;font-size:11px;color:var(--muted)">Not run (use --run-struct-qc CLI flag)</td></tr>`;

  const seqBlock = [
    `>petized_VH_${escapeHtml(name)}\n${seqs.petized_vh || ""}`,
    `>petized_VL_${escapeHtml(name)}\n${seqs.petized_vl || ""}`,
  ].join("\n\n");

  const html = `
    <section class="surface panel" style="margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
        <span style="font-size:18px;font-weight:700;color:${statusColor}">${status}</span>
        <span style="font-size:13px;color:var(--muted)">${escapeHtml(name)} · ${escapeHtml(r.species||"")} · ${escapeHtml(strategy)}</span>
      </div>
      <table style="width:100%;border-collapse:collapse">
        ${row("VH germline", `<b>${escapeHtml(sel.vh?.germline||"?")}</b> (${escapeHtml(sel.vh?.tier||"?")}) · FR id ${((sel.vh?.fr_identity)||0).toFixed(1)}%`)}
        ${row("VL germline", `<b>${escapeHtml(sel.vl?.germline||"?")}</b> (${escapeHtml(sel.vl?.tier||"?")}) · FR id ${((sel.vl?.fr_identity)||0).toFixed(1)}%`)}
        ${row("Strategies", `VH: ${escapeHtml(r.strategies_by_chain?.vh||"?")} · VL: ${escapeHtml(r.strategies_by_chain?.vl||"?")}`)}
        ${row("Mutations", escapeHtml(mutSummary))}
        ${row("FR-SHM auto", escapeHtml(shmNote))}
        ${row("Surface guidance", escapeHtml(sg.enabled ? sg.mode : "disabled"))}
        ${row("CMC VH", `${badge(cmc.vh?.overall||"?")} pI ${cmc.vh?.metrics?.pI||"?"} · Instability ${cmc.vh?.metrics?.instability_index||"?"}`)}
        ${row("CMC VL", `${badge(cmc.vl?.overall||"?")} pI ${cmc.vl?.metrics?.pI||"?"} · Instability ${cmc.vl?.metrics?.instability_index||"?"}`)}
        ${sqcHtml}
      </table>
    </section>
    <section class="surface panel" style="margin-bottom:14px">
      <div class="panel-label">CMC Flags</div>
      ${flagsHtml}
    </section>
    <section class="surface panel" style="margin-bottom:14px">
      <div class="panel-label">Petized Sequences (FASTA)</div>
      <pre style="font-size:11px;word-break:break-all;white-space:pre-wrap;color:#93c5fd;background:#0a121f;padding:12px;border-radius:6px;border:1px solid var(--line)">${escapeHtml(seqBlock)}</pre>
      <button class="btn" style="margin-top:8px" onclick="navigator.clipboard.writeText(${JSON.stringify(seqBlock)}).catch(()=>{})">Copy FASTA</button>
    </section>
    <section class="surface panel">
      <div class="panel-label">Full JSON Result</div>
      <pre style="font-size:10px;max-height:320px;overflow:auto;white-space:pre;color:#94a3b8;background:#0a121f;padding:12px;border-radius:6px;border:1px solid var(--line)">${escapeHtml(JSON.stringify(r, null, 2))}</pre>
    </section>
  `;
  setOutput(html);
  updateResultRail({
    status,
    summaryTitle: `${r.species} petization · ${strategy}`,
    summaryText: `VH: ${sel.vh?.germline||"?"} (${sel.vh?.tier||"?"}) · VL: ${sel.vl?.germline||"?"} (${sel.vl?.tier||"?"}) · ${mutSummary}`,
    metrics: [
      { label: "VH pI", value: String(cmc.vh?.metrics?.pI || "?") },
      { label: "VL pI", value: String(cmc.vl?.metrics?.pI || "?") },
      { label: "VH FR id", value: `${((sel.vh?.fr_identity)||0).toFixed(1)}%` },
      { label: "VL FR id", value: `${((sel.vl?.fr_identity)||0).toFixed(1)}%` },
    ],
    recommendation: status === "PASS"
      ? "CDR preservation verified. Proceed to structure QC (Phase 4.5) before delivery."
      : "CDR preservation failed — review mutations and re-run.",
  });
}

// Populate pet demo selectors
(function() {
  const orig = window.hydrateService || function(){};
  window._origHydrate = orig;
  // Patch loadServiceDemo to handle petization demos
  const origLoad = window.loadServiceDemo;
  window.loadServiceDemo = function() {
    const service = REGISTRY.services[state.service];
    if (service && service.runner === "petization") {
      const sel = document.getElementById("pet-demo");
      if (!sel) return;
      const demo = PET_DEMOS[sel.value];
      if (!demo) return;
      const vhEl = document.getElementById("pet-vh");
      const vlEl = document.getElementById("pet-vl");
      const spEl = document.getElementById("pet-species");
      if (vhEl) vhEl.value = demo.vh;
      if (vlEl) vlEl.value = demo.vl;
      if (spEl) spEl.value = demo.species;
      return;
    }
    if (origLoad) origLoad.apply(this, arguments);
  };
})();
