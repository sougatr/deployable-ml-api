// State
let currentPatient = null;
let currentEncounterId = null;
let currentAadhaarTxnId = null;
let currentAbhaTxnId = null;
let pendingDuplicatePayload = null;
let currentAdmissionId = null;
let currentBeds = [];
let selectedBedId = null;
let currentWardFilter = "ALL";
let currentDiagOrders = [];
let currentDiagCatalog = [];
let selectedDiagOrderId = null;
let currentDiagFilter = "ALL";
let currentPharmacyInventory = [];
let currentPharmFilter = "ALL";
let currentEmergencyBays = [];
let currentEmergencyCases = [];
let selectedEmergencyCaseId = null;
let currentPortalMpiId = null;
let currentPortalSummary = null;

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
  initTabNavigation();
  initSubTabs();
  initRegistrationForm();
  initDobPicker();
  initAbhaLinking();
  initClinicianConsultation();
  initIPDModule();
  initDiagnosticsModule();
  initPharmacyModule();
  initEmergencyModule();
  initPatientPortalModule();
  initBillingAndPayment();
  initHospitalStepperAndSerialNav();
  initDepartmentDocumentAI();
  fetchHealthStatus();
});

// Viewport Tab Navigation
function initTabNavigation() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      // Handle legacy or direct hospital sub-tab requests
      if (["reception", "clinician", "ipd", "diagnostics", "pharmacy", "emergency"].includes(target)) {
        tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === "hospital"));
        document.querySelectorAll(".viewport-panel").forEach(panel => panel.classList.remove("active"));
        const hospPanel = document.getElementById("panel-hospital");
        if (hospPanel) hospPanel.classList.add("active");
        switchHospitalTab(target);
        updateBannerNavButtons("hospital");
        return;
      }

      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      
      document.querySelectorAll(".viewport-panel").forEach(panel => {
        panel.classList.remove("active");
      });
      const targetPanel = document.getElementById(`panel-${target}`);
      if (targetPanel) targetPanel.classList.add("active");

      updateBannerNavButtons(target);

      if (target === "hospital") {
        const activeSub = document.querySelector(".hospital-tab-btn.active")?.dataset.htab || "reception";
        switchHospitalTab(activeSub);
      } else if (target === "patient-portal") {
        populatePatientPortalSelect();
        const targetMpi = currentPortalMpiId || (currentPatient ? currentPatient.mpi_id : null);
        if (targetMpi) {
          loadPatientPortal(targetMpi);
        }
      } else if (target === "abdm-events" && currentPatient) {
        refreshAbdmAndOutbox();
      }
    });
  });

  const btnBannerPortal = document.getElementById("btn-banner-open-portal");
  if (btnBannerPortal) {
    btnBannerPortal.addEventListener("click", () => {
      const tabBtn = document.querySelector(`.tab-btn[data-tab="patient-portal"]`);
      if (tabBtn) tabBtn.click();
    });
  }

  const btnBannerHospital = document.getElementById("btn-banner-open-hospital");
  if (btnBannerHospital) {
    btnBannerHospital.addEventListener("click", () => {
      const tabBtn = document.querySelector(`.tab-btn[data-tab="hospital"]`);
      if (tabBtn) tabBtn.click();
    });
  }

  initHospitalSubTabNavigation();
}

function updateBannerNavButtons(activeTarget) {
  const btnPortal = document.getElementById("btn-banner-open-portal");
  const btnHospital = document.getElementById("btn-banner-open-hospital");
  if (btnPortal && btnHospital) {
    if (activeTarget === "patient-portal") {
      btnPortal.style.display = "none";
      btnHospital.style.display = "inline-flex";
    } else {
      btnPortal.style.display = "inline-flex";
      btnHospital.style.display = "none";
    }
  }
}

function initHospitalSubTabNavigation() {
  const hospTabs = document.querySelectorAll(".hospital-tab-btn");
  hospTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.htab;
      switchHospitalTab(target);
    });
  });
}

function switchHospitalTab(target) {
  const hospTabs = document.querySelectorAll(".hospital-tab-btn");
  hospTabs.forEach(b => b.classList.toggle("active", b.dataset.htab === target));

  document.querySelectorAll(".hospital-tab-panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById(`htab-${target}`);
  if (panel) panel.classList.add("active");

  // Update Stepper Bar Steps
  const stepOrder = ["reception", "clinician", "diagnostics", "pharmacy", "ipd", "emergency"];
  const targetIdx = stepOrder.indexOf(target);
  document.querySelectorAll(".stepper-step").forEach(s => {
    const sStep = s.dataset.step;
    const sIdx = stepOrder.indexOf(sStep);
    s.classList.toggle("active", sStep === target);
    s.classList.toggle("completed", sIdx !== -1 && targetIdx !== -1 && sIdx < targetIdx);
  });

  if (target === "ipd") {
    fetchBedMatrix();
  } else if (target === "diagnostics") {
    fetchDiagnosticsCatalog();
    fetchDiagnosticsWorklist();
  } else if (target === "pharmacy") {
    fetchPharmacyInventory();
    populatePrescriptionDispenseQueue();
  } else if (target === "emergency") {
    fetchEmergencyBays();
    fetchActiveEmergencyCases();
    populateEmergencyPatientSelect();
  }
}
window.switchHospitalTab = switchHospitalTab;

// Sub-Tabs in ABHA Linking Card
function initSubTabs() {
  const subTabs = document.querySelectorAll(".sub-tab-btn");
  subTabs.forEach(st => {
    st.addEventListener("click", () => {
      subTabs.forEach(t => t.classList.remove("active"));
      st.classList.add("active");
      const target = st.dataset.subtab;
      document.querySelectorAll(".sub-tab-panel").forEach(p => p.classList.remove("active"));
      document.getElementById(`subtab-${target}`).classList.add("active");
    });
  });
}

// Update Active Patient Banner
function updatePatientBanner(patient) {
  currentPatient = patient;
  document.getElementById("banner-name").textContent = `${patient.first_name} ${patient.last_name}`;
  document.getElementById("banner-uhid").textContent = `UHID: ${patient.uhid}`;
  document.getElementById("banner-gender-age").textContent = `${patient.gender} • DOB: ${patient.dob}`;
  document.getElementById("banner-mpi").textContent = patient.mpi_id;
  document.getElementById("banner-phone").textContent = patient.primary_phone || "--";
  document.getElementById("banner-avatar").textContent = patient.first_name[0].toUpperCase();

  const abhaBadge = document.getElementById("banner-abha-badge");
  if (patient.abha_address || patient.abha_number) {
    abhaBadge.className = "badge badge-abdm";
    abhaBadge.textContent = `ABHA: ${patient.abha_address || patient.abha_number}`;
  } else {
    abhaBadge.className = "badge badge-gray";
    abhaBadge.textContent = "ABHA: Not Linked (Optional)";
  }

  // Update clinician viewport state
  document.getElementById("clinician-no-patient-warning").classList.add("hidden");
  document.getElementById("clinician-encounter-flow").classList.remove("hidden");
}

// 1. Patient Registration & MPI
function initRegistrationForm() {
  const form = document.getElementById("patient-reg-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      first_name: document.getElementById("reg-first-name").value,
      last_name: document.getElementById("reg-last-name").value,
      dob: document.getElementById("reg-dob").value,
      gender: document.getElementById("reg-gender").value,
      primary_phone: document.getElementById("reg-phone").value,
      postal_code: document.getElementById("reg-postal").value,
      identifiers: []
    };
    await resolvePatient(payload, false);
  });

  // Modal actions
  document.getElementById("btn-force-create-dup").addEventListener("click", async () => {
    document.getElementById("duplicate-modal").close();
    if (pendingDuplicatePayload) {
      await resolvePatient(pendingDuplicatePayload, true);
    }
  });

  document.getElementById("btn-use-existing-dup").addEventListener("click", () => {
    document.getElementById("duplicate-modal").close();
  });
}

function initDobPicker() {
  const daySelect = document.getElementById("reg-dob-day");
  const monthSelect = document.getElementById("reg-dob-month");
  const yearSelect = document.getElementById("reg-dob-year");
  const ageInput = document.getElementById("reg-age");
  const calInput = document.getElementById("reg-dob");

  if (!daySelect || !yearSelect || !calInput) return;

  const currentYear = new Date().getFullYear();

  // Populate Days: 01 to 31
  daySelect.innerHTML = "";
  for (let d = 1; d <= 31; d++) {
    const val = String(d).padStart(2, "0");
    const opt = document.createElement("option");
    opt.value = val;
    opt.textContent = val;
    daySelect.appendChild(opt);
  }

  // Populate Years: currentYear down to 1910
  yearSelect.innerHTML = "";
  for (let y = currentYear; y >= 1910; y--) {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    yearSelect.appendChild(opt);
  }

  function syncFromIso(isoString) {
    if (!isoString || !isoString.includes("-")) return;
    const parts = isoString.split("-");
    if (parts.length === 3) {
      const [y, m, d] = parts;
      if (yearSelect.querySelector(`option[value="${y}"]`)) yearSelect.value = y;
      if (monthSelect.querySelector(`option[value="${m}"]`)) monthSelect.value = m;
      if (daySelect.querySelector(`option[value="${d}"]`)) daySelect.value = d;
      const age = currentYear - parseInt(y, 10);
      if (!isNaN(age) && age >= 0) ageInput.value = age;
    }
  }

  function syncToIso() {
    const y = yearSelect.value || "1982";
    const m = monthSelect.value || "05";
    let d = daySelect.value || "14";

    // Validate max days in month
    const maxDays = new Date(parseInt(y, 10), parseInt(m, 10), 0).getDate();
    if (parseInt(d, 10) > maxDays) {
      d = String(maxDays).padStart(2, "0");
      daySelect.value = d;
    }

    const iso = `${y}-${m}-${d}`;
    calInput.value = iso;
    const age = currentYear - parseInt(y, 10);
    if (!isNaN(age) && age >= 0) ageInput.value = age;
  }

  // Initialize with calInput's value
  syncFromIso(calInput.value || "1982-05-14");

  daySelect.addEventListener("change", syncToIso);
  monthSelect.addEventListener("change", syncToIso);
  yearSelect.addEventListener("change", syncToIso);

  ageInput.addEventListener("input", () => {
    const ageVal = parseInt(ageInput.value, 10);
    if (!isNaN(ageVal) && ageVal >= 0 && ageVal <= 120) {
      const computedYear = String(currentYear - ageVal);
      if (yearSelect.querySelector(`option[value="${computedYear}"]`)) {
        yearSelect.value = computedYear;
        syncToIso();
      }
    }
  });

  calInput.addEventListener("change", () => {
    syncFromIso(calInput.value);
  });
}

async function resolvePatient(payload, allowOverride = false) {
  try {
    const res = await fetch(`/api/v1/identity/resolve?allow_duplicate_override=${allowOverride}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.status === 409) {
      const errData = await res.json();
      pendingDuplicatePayload = payload;
      showDuplicateModal(errData.detail.candidate_matches);
      return;
    }

    if (!res.ok) {
      throw new Error((await res.json()).detail || "Failed to resolve patient");
    }

    const data = await res.json();
    updatePatientBanner(data.patient_record || {
      first_name: payload.first_name,
      last_name: payload.last_name,
      dob: payload.dob,
      gender: payload.gender,
      primary_phone: payload.primary_phone,
      mpi_id: data.mpi_id,
      uhid: data.uhid
    });
    alert(`Success: Patient ${data.is_newly_created ? 'Registered' : 'Identified'}! UHID: ${data.uhid}`);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

function showDuplicateModal(candidates) {
  const modal = document.getElementById("duplicate-modal");
  const list = document.getElementById("duplicate-candidates-list");
  list.innerHTML = candidates.map(c => `
    <div class="duplicate-item">
      <strong>${c.first_name} ${c.last_name} (${c.gender})</strong>
      <span>UHID: ${c.uhid} • DOB: ${c.dob}</span>
      <span class="badge badge-info">Matching Confidence Weight: ${c.confidence_score}</span>
    </div>
  `).join("");
  modal.showModal();
}

// 2. ABDM Linking (Optional M1)
function initAbhaLinking() {
  // Method A: Aadhaar OTP
  document.getElementById("btn-send-aadhaar-otp").addEventListener("click", async () => {
    const aadhaar = document.getElementById("aadhaar-input").value;
    try {
      const res = await fetch("/api/v1/interop/abdm/aadhaar/generate-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aadhaar_number: aadhaar })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      currentAadhaarTxnId = data.txn_id;
      document.getElementById("aadhaar-otp-box").classList.remove("hidden");
    } catch (e) {
      alert("Aadhaar OTP Error: " + e.message);
    }
  });

  document.getElementById("btn-verify-aadhaar-otp").addEventListener("click", async () => {
    if (!currentPatient) return alert("Please register or select a patient first.");
    const otp = document.getElementById("aadhaar-otp-val").value;
    try {
      const verifyRes = await fetch("/api/v1/interop/abdm/aadhaar/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ txn_id: currentAadhaarTxnId, otp })
      });
      const profile = await verifyRes.json();
      if (!verifyRes.ok) throw new Error(profile.detail);

      // Link to Patient MPI
      await fetch("/api/v1/interop/abdm/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mpi_id: currentPatient.mpi_id, profile })
      });

      currentPatient.abha_number = profile.abha_number;
      currentPatient.abha_address = profile.abha_address;
      updatePatientBanner(currentPatient);

      document.getElementById("aadhaar-otp-box").classList.add("hidden");
      const sBox = document.getElementById("abha-success-box");
      sBox.classList.remove("hidden");
      document.getElementById("abha-linked-details").textContent = `Linked ABHA Number: ${profile.abha_number} (${profile.abha_address})`;
    } catch (e) {
      alert("Verification Failed: " + e.message);
    }
  });

  // Method B: Existing ABHA Address
  document.getElementById("btn-send-abha-otp").addEventListener("click", async () => {
    const abhaId = document.getElementById("abha-address-input").value;
    try {
      const res = await fetch("/api/v1/interop/abdm/address/search-and-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ abha_identifier: abhaId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      currentAbhaTxnId = data.txn_id;
      document.getElementById("abha-otp-box").classList.remove("hidden");
    } catch (e) {
      alert("ABHA OTP Error: " + e.message);
    }
  });

  document.getElementById("btn-verify-abha-otp").addEventListener("click", async () => {
    if (!currentPatient) return alert("Please register or select a patient first.");
    const otp = document.getElementById("abha-otp-val").value;
    try {
      const verifyRes = await fetch("/api/v1/interop/abdm/address/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ txn_id: currentAbhaTxnId, otp })
      });
      const profile = await verifyRes.json();
      if (!verifyRes.ok) throw new Error(profile.detail);

      await fetch("/api/v1/interop/abdm/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mpi_id: currentPatient.mpi_id, profile })
      });

      currentPatient.abha_number = profile.abha_number;
      currentPatient.abha_address = profile.abha_address;
      updatePatientBanner(currentPatient);

      document.getElementById("abha-otp-box").classList.add("hidden");
      const sBox = document.getElementById("abha-success-box");
      sBox.classList.remove("hidden");
      document.getElementById("abha-linked-details").textContent = `Linked ABHA Address: ${profile.abha_address}`;
    } catch (e) {
      alert("Verification Failed: " + e.message);
    }
  });
}

// 3. Clinician OPD Consultation
function initClinicianConsultation() {
  const btnStart = document.getElementById("btn-start-encounter");
  btnStart.addEventListener("click", async () => {
    if (!currentPatient) return alert("Select patient first.");
    try {
      const res = await fetch("/api/v1/clinical/encounters/start-opd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mpi_id: currentPatient.mpi_id,
          practitioner_id: "00000000-0000-0000-0000-000000000001",
          facility_id: "00000000-0000-0000-0000-000000000002",
          tenant_id: "00000000-0000-0000-0000-000000000003"
        })
      });
      const data = await res.json();
      currentEncounterId = data.encounter_id;
      document.getElementById("encounter-status-label").textContent = `Encounter: IN_PROGRESS (#${currentEncounterId.slice(0, 8)})`;
      btnStart.classList.add("hidden");
      document.getElementById("prescription-upload-card").classList.remove("hidden");
      document.getElementById("consultation-form").classList.remove("hidden");
    } catch (e) {
      alert("Error starting encounter: " + e.message);
    }
  });

  // Upload and parse handwritten document
  const btnUploadParse = document.getElementById("btn-upload-parse");
  const btnLoadSample = document.getElementById("btn-load-sample-prescription");
  const fileInput = document.getElementById("prescription-file-input");
  const statusBox = document.getElementById("parser-status-box");
  const statusMsg = document.getElementById("parser-status-msg");
  const btnToggleOcr = document.getElementById("btn-toggle-ocr-preview");
  const ocrPanel = document.getElementById("ocr-raw-text-panel");

  if (btnToggleOcr && ocrPanel) {
    btnToggleOcr.addEventListener("click", () => {
      ocrPanel.classList.toggle("hidden");
    });
  }

  async function triggerParsing(formData) {
    statusBox.classList.remove("hidden");
    statusBox.className = "alert alert-info";
    statusMsg.innerHTML = "<strong>AI Vision & NLP Ingestion Active:</strong> Extracting handwritten text, normalizing clinical shorthand, and mapping to ICD-10, LOINC, and E-Prescription columns...";

    // 0. Ensure patient & encounter are active so columns are ready for review
    if (!currentPatient) {
      try {
        await resolvePatient({
          first_name: "Ramesh",
          last_name: "Sharma",
          dob: document.getElementById("reg-dob")?.value || "1982-05-14",
          gender: "MALE",
          primary_phone: "+919876543210",
          postal_code: "560038",
          identifiers: []
        }, false);
      } catch (e) {
        console.warn("Auto-patient notice:", e);
      }
    }

    if (!currentEncounterId && currentPatient) {
      try {
        const encRes = await fetch("/api/v1/clinical/encounters/start-opd", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mpi_id: currentPatient.mpi_id,
            practitioner_id: "00000000-0000-0000-0000-000000000001",
            facility_id: "00000000-0000-0000-0000-000000000002",
            tenant_id: "00000000-0000-0000-0000-000000000003"
          })
        });
        const encData = await encRes.json();
        currentEncounterId = encData.encounter_id;
        document.getElementById("encounter-status-label").textContent = `Encounter: IN_PROGRESS (#${currentEncounterId.slice(0, 8)})`;
        document.getElementById("btn-start-encounter").classList.add("hidden");
        document.getElementById("prescription-upload-card").classList.remove("hidden");
        document.getElementById("consultation-form").classList.remove("hidden");
      } catch (e) {
        console.warn("Auto-start encounter notice:", e);
      }
    }

    try {
      const res = await fetch("/api/v1/clinical/consultations/parse-document", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      const parsed = data.parsed_columns;
      const highlightEls = [];

      // Show Parsed Columns Dashboard & OCR Text
      const parsedContainer = document.getElementById("parsed-columns-container");
      if (parsedContainer) parsedContainer.classList.remove("hidden");

      if (ocrPanel && data.raw_extracted_text) {
        ocrPanel.textContent = data.raw_extracted_text;
      }

      // Calculate entity count
      let totalEntities = 0;
      if (parsed.chief_complaint) totalEntities++;
      if (parsed.diagnoses) totalEntities += parsed.diagnoses.length;
      if (parsed.vitals) totalEntities += parsed.vitals.length;
      if (parsed.prescriptions) totalEntities += parsed.prescriptions.length;
      if (parsed.orders) totalEntities += parsed.orders.length;

      const badgeEl = document.getElementById("parsed-entity-count-badge");
      if (badgeEl) badgeEl.textContent = `${totalEntities} Entities Parsed & Populated`;

      // Auto-sync patient details if detected from prescription
      if (data.patient_info) {
        const pInfo = data.patient_info;
        if (currentPatient) {
          currentPatient.first_name = pInfo.first_name;
          currentPatient.last_name = pInfo.last_name;
          currentPatient.gender = pInfo.gender;
          updatePatientBanner(currentPatient);
        }
        const regFirst = document.getElementById("reg-first-name");
        const regLast = document.getElementById("reg-last-name");
        const regGender = document.getElementById("reg-gender");
        const regAge = document.getElementById("reg-age");
        if (regFirst) regFirst.value = pInfo.first_name;
        if (regLast) regLast.value = pInfo.last_name;
        if (regGender) regGender.value = pInfo.gender;
        if (regAge && pInfo.age) {
          regAge.value = pInfo.age;
          const currentYear = new Date().getFullYear();
          const computedYear = String(currentYear - pInfo.age);
          const yearSelect = document.getElementById("reg-dob-year");
          const calInput = document.getElementById("reg-dob");
          if (yearSelect) yearSelect.value = computedYear;
          if (calInput) calInput.value = `${computedYear}-07-28`;
        }
      }

      // 1. Column 1: Clinical Notes (SOAP Narrative & History + Vitals)
      const colNotes = document.getElementById("col-clinical-notes-content");
      if (colNotes) {
        colNotes.innerHTML = "";
        const narrativeDiv = document.createElement("div");
        narrativeDiv.style.fontSize = "0.8125rem";
        narrativeDiv.style.lineHeight = "1.45";
        narrativeDiv.style.whiteSpace = "pre-wrap";
        narrativeDiv.style.color = "#1e293b";
        narrativeDiv.textContent = parsed.clinical_narrative || "Patient presented for clinical consultation. Examination and evaluation completed.";
        colNotes.appendChild(narrativeDiv);

        if (parsed.vitals && parsed.vitals.length > 0) {
          const vitalsStrip = document.createElement("div");
          vitalsStrip.className = "parsed-vitals-strip";
          parsed.vitals.forEach(v => {
            const isNorm = v.interpretation === "NORMAL";
            const pill = document.createElement("span");
            pill.className = `badge ${isNorm ? 'badge-success' : 'badge-warning'}`;
            pill.style.fontSize = "0.71875rem";
            pill.style.padding = "0.15rem 0.4rem";
            pill.innerHTML = `<strong>${v.display}:</strong> ${v.value} ${v.unit}`;
            vitalsStrip.appendChild(pill);

            if (v.code_loinc === "8480-6") {
              const el = document.getElementById("vital-sbp");
              if (el) { el.value = v.value; highlightEls.push(el); }
            } else if (v.code_loinc === "8867-4") {
              const el = document.getElementById("vital-hr");
              if (el) { el.value = v.value; highlightEls.push(el); }
            }
          });
          colNotes.appendChild(vitalsStrip);
        }
      }

      if (parsed.chief_complaint) {
        const el = document.getElementById("consult-complaint");
        if (el) el.value = parsed.chief_complaint;
      }
      if (parsed.clinical_narrative) {
        const el = document.getElementById("consult-narrative");
        if (el) {
          el.value = parsed.clinical_narrative;
          highlightEls.push(el);
        }
      }

      // 2. Column 2: Final Diagnoses (ICD-10 & SNOMED CT)
      const colDiag = document.getElementById("col-diagnoses-content");
      const diagSelect = document.getElementById("consult-icd10");
      if (colDiag) colDiag.innerHTML = "";

      if (parsed.diagnoses && parsed.diagnoses.length > 0) {
        parsed.diagnoses.forEach((d, idx) => {
          if (colDiag) {
            const badge = document.createElement("div");
            badge.className = "parsed-item-badge";
            badge.innerHTML = `<span class="parsed-tag-code">${d.code_icd10}</span> <span>${d.display}</span>`;
            colDiag.appendChild(badge);
          }

          // Ensure option exists in select
          let optExists = false;
          for (let i = 0; i < diagSelect.options.length; i++) {
            if (diagSelect.options[i].value === d.code_icd10) {
              optExists = true;
              if (idx === 0) diagSelect.selectedIndex = i;
              break;
            }
          }
          if (!optExists) {
            const newOpt = document.createElement("option");
            newOpt.value = d.code_icd10;
            newOpt.dataset.snomed = d.code_snomed || "38341003";
            newOpt.dataset.name = d.display;
            newOpt.textContent = `[${d.code_icd10}] ${d.display}`;
            diagSelect.appendChild(newOpt);
            if (idx === 0) diagSelect.value = d.code_icd10;
          }
        });
        highlightEls.push(diagSelect);
      }

      // 4. Column 4: E-Prescriptions
      const colRx = document.getElementById("col-rx-content");
      const rxSelect = document.getElementById("rx-medicine");
      const rxInstInput = document.getElementById("rx-instructions");
      if (colRx) colRx.innerHTML = "";

      if (parsed.prescriptions && parsed.prescriptions.length > 0) {
        let rxHtml = `<table class="parsed-table">
          <thead>
            <tr>
              <th>Brand & Strength</th>
              <th>Generic Composition</th>
              <th>Timing</th>
              <th>Duration</th>
              <th>Instructions</th>
            </tr>
          </thead>
          <tbody>`;

        parsed.prescriptions.forEach((p, idx) => {
          rxHtml += `
            <tr>
              <td><strong>${p.brand_name}</strong></td>
              <td>${p.generic_name}</td>
              <td><span class="badge badge-info" style="font-size:0.6875rem;">${p.timing}</span></td>
              <td>${p.duration_days} Days</td>
              <td>${p.instructions}</td>
            </tr>
          `;

          const optVal = `${p.brand_name}|${p.generic_name}|${p.timing}|${p.duration_days}`;
          let optExists = false;
          for (let i = 0; i < rxSelect.options.length; i++) {
            if (rxSelect.options[i].value.toLowerCase().includes(p.brand_name.toLowerCase())) {
              optExists = true;
              if (idx === 0) rxSelect.selectedIndex = i;
              break;
            }
          }
          if (!optExists) {
            const newOpt = document.createElement("option");
            newOpt.value = optVal;
            newOpt.textContent = `${p.brand_name} (${p.generic_name}) - ${p.timing} (${p.duration_days} Days)`;
            rxSelect.appendChild(newOpt);
            if (idx === 0) rxSelect.value = optVal;
          }
        });

        rxHtml += `</tbody></table>`;
        if (colRx) colRx.innerHTML = rxHtml;

        rxInstInput.value = parsed.prescriptions[0].instructions || "Take as instructed";
        highlightEls.push(rxSelect);
        highlightEls.push(rxInstInput);
      }

      // 5. Column 5: Diagnostic Investigation Orders
      const colOrders = document.getElementById("col-orders-content");
      const orderSelect = document.getElementById("order-test");
      if (colOrders) colOrders.innerHTML = "";

      if (parsed.orders && parsed.orders.length > 0) {
        let orderHtml = `<table class="parsed-table">
          <thead>
            <tr>
              <th>Test Name</th>
              <th>Department</th>
              <th>Tariff Code</th>
              <th>Price</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>`;

        parsed.orders.forEach((o, idx) => {
          orderHtml += `
            <tr>
              <td><strong>${o.display}</strong></td>
              <td>${o.department_code}</td>
              <td><code>${o.tariff_code}</code></td>
              <td>₹${o.unit_price.toFixed(2)}</td>
              <td><span class="badge badge-info" style="font-size:0.6875rem;">${o.priority}</span></td>
            </tr>
          `;

          const orderVal = `${o.code_loinc_or_snomed}|${o.display}|${o.tariff_code}|${o.department_code}|${o.unit_price}`;
          let orderExists = false;
          for (let i = 0; i < orderSelect.options.length; i++) {
            if (orderSelect.options[i].value.includes(o.code_loinc_or_snomed)) {
              orderExists = true;
              if (idx === 0) orderSelect.selectedIndex = i;
              break;
            }
          }
          if (!orderExists) {
            const newOpt = document.createElement("option");
            newOpt.value = orderVal;
            newOpt.textContent = `${o.display} (${o.code_loinc_or_snomed}) - ₹${o.unit_price.toFixed(2)}`;
            orderSelect.appendChild(newOpt);
            if (idx === 0) orderSelect.value = orderVal;
          }
        });

        orderHtml += `</tbody></table>`;
        if (colOrders) colOrders.innerHTML = orderHtml;
        highlightEls.push(orderSelect);
      }

      // Visual pulse on updated columns
      highlightEls.forEach(el => {
        if (el) {
          el.classList.add("highlight-updated");
          setTimeout(() => el.classList.remove("highlight-updated"), 2600);
        }
      });

      statusBox.className = "alert alert-success";
      statusMsg.innerHTML = `<strong>Success:</strong> Prescription document parsed into <strong>${totalEntities} clinical entities</strong>! All requisite columns and form fields below have been populated for physician review.`;
    } catch (err) {
      statusBox.className = "alert alert-warning";
      statusMsg.innerHTML = `<strong>Parsing Error:</strong> ${err.message}`;
    }
  }

  if (btnUploadParse) {
    btnUploadParse.addEventListener("click", () => {
      if (!fileInput.files || fileInput.files.length === 0) {
        return alert("Please select a prescription image or PDF file to upload.");
      }
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      triggerParsing(formData);
    });
  }

  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", () => {
      const formData = new FormData();
      triggerParsing(formData);
    });
  }

  const form = document.getElementById("consultation-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentEncounterId) return alert("No active encounter.");

    const icdOpt = document.getElementById("consult-icd10").selectedOptions[0];
    const rxOpt = document.getElementById("rx-medicine").value.split("|");
    const orderOpt = document.getElementById("order-test").value.split("|");
    const consultFee = parseFloat(document.getElementById("consult-fee").value);

    const payload = {
      encounter_id: currentEncounterId,
      practitioner_id: "00000000-0000-0000-0000-000000000001",
      chief_complaint: document.getElementById("consult-complaint").value,
      clinical_narrative: document.getElementById("consult-narrative").value,
      vitals: [
        {
          code_loinc: "8480-6",
          display: "Systolic Blood Pressure",
          value: parseFloat(document.getElementById("vital-sbp").value),
          unit: "mm[Hg]",
          interpretation: "HIGH"
        }
      ],
      diagnoses: [
        {
          code_icd10: icdOpt.value,
          code_snomed: icdOpt.dataset.snomed,
          display: icdOpt.dataset.name,
          clinical_status: "ACTIVE",
          verification_status: "CONFIRMED"
        }
      ],
      prescriptions: [
        {
          brand_name: rxOpt[0],
          generic_name: rxOpt[1],
          dosage_form: "TABLET",
          timing: rxOpt[2],
          duration_days: parseInt(rxOpt[3]),
          instructions: document.getElementById("rx-instructions").value
        }
      ],
      orders: [
        {
          category: "LABORATORY",
          code_loinc_or_snomed: orderOpt[0],
          display: orderOpt[1],
          tariff_code: orderOpt[2],
          department_code: orderOpt[3],
          unit_price: parseFloat(orderOpt[4]),
          priority: "ROUTINE"
        }
      ],
      consultation_fee: consultFee,
      consultation_tariff_code: "CON-OPD-GEN",
      patient_co_pay_ratio: 0.20, // 20% patient co-pay
      doctor_digital_signature: "SIG-RSA-DR-ANAND-8812"
    };

    try {
      const res = await fetch("/api/v1/clinical/consultations/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail);

      // Render summary
      const sBox = document.getElementById("consult-success-summary");
      sBox.classList.remove("hidden");
      document.getElementById("consult-result-details").innerHTML = `
        <p>• <strong>Charges Captured:</strong> ₹${result.total_charges_posted.toFixed(2)} (Patient: ₹${result.patient_share_payable.toFixed(2)}, Insurer: ₹${result.insurer_share_payable.toFixed(2)})</p>
        <p>• <strong>Trial Balance:</strong> ${result.trial_balance_status} (₹0.00 Discrepancy)</p>
        <p>• <strong>ABDM HIP Status:</strong> ${result.abdm_care_context_linked ? 'Linked (' + result.care_context_id + ')' : 'Skipped (No ABHA)'}</p>
      `;

      // Update Billing View
      updateBillingView(result, orderOpt);
    } catch (e) {
      alert("Consultation Error: " + e.message);
    }
  });
}

// 4. Financial Ledger & Cashier View
function updateBillingView(result, orderOpt) {
  const tbody = document.getElementById("billing-charges-tbody");
  tbody.innerHTML = `
    <tr>
      <td><strong>Doctor Consultation</strong><br><small>Tariff: CON-OPD-GEN</small></td>
      <td><span class="badge badge-info">Consultation Note</span></td>
      <td>₹500.00</td>
      <td>₹100.00</td>
      <td>₹400.00</td>
    </tr>
    <tr>
      <td><strong>${orderOpt[1]}</strong><br><small>Tariff: ${orderOpt[2]}</small></td>
      <td><span class="badge badge-info">ServiceRequest</span></td>
      <td>₹${parseFloat(orderOpt[4]).toFixed(2)}</td>
      <td>₹${(parseFloat(orderOpt[4]) * 0.2).toFixed(2)}</td>
      <td>₹${(parseFloat(orderOpt[4]) * 0.8).toFixed(2)}</td>
    </tr>
  `;

  document.getElementById("billing-gross-total").textContent = `₹${result.total_charges_posted.toFixed(2)}`;
  document.getElementById("billing-insurer-total").textContent = `₹${result.insurer_share_payable.toFixed(2)}`;
  document.getElementById("billing-net-payable").textContent = `₹${result.patient_share_payable.toFixed(2)}`;
  document.getElementById("pay-amount").value = result.patient_share_payable.toFixed(2);
}

function initBillingAndPayment() {
  document.getElementById("btn-collect-payment").addEventListener("click", async () => {
    if (!currentEncounterId) return alert("No active encounter charges.");
    const amt = parseFloat(document.getElementById("pay-amount").value);
    const mode = document.getElementById("pay-mode").value;

    try {
      const res = await fetch("/api/v1/billing/payments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          encounter_id: currentEncounterId,
          mpi_id: currentPatient.mpi_id,
          amount: amt,
          payment_method: mode
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      const rBox = document.getElementById("payment-receipt-box");
      rBox.classList.remove("hidden");
      document.getElementById("receipt-text").textContent = `Collected ₹${amt.toFixed(2)} via ${mode}. Journal ID: ${data.journal_id}. Trial balance discrepancy: ₹0.00.`;
    } catch (e) {
      alert("Payment Error: " + e.message);
    }
  });
}

// 5. ABDM & Outbox Inspector
async function refreshAbdmAndOutbox() {
  if (!currentPatient) return;

  // Fetch Care Contexts
  try {
    const res = await fetch(`/api/v1/interop/abdm/care-contexts/${currentPatient.mpi_id}`);
    const data = await res.json();
    const cList = document.getElementById("abdm-care-contexts-list");
    if (data.care_contexts && data.care_contexts.length > 0) {
      cList.innerHTML = data.care_contexts.map(c => `
        <div class="event-card">
          <div class="event-card-type">${c.display}</div>
          <div class="event-card-key">Context ID: ${c.care_context_id} • Registered: ${c.registered_at.slice(0, 19)}</div>
        </div>
      `).join("");
    } else {
      cList.innerHTML = '<div class="empty-state">No ABDM care contexts linked.</div>';
    }
  } catch (e) {}

  // Fetch Outbox
  try {
    const res = await fetch("/health");
    const data = await res.json();
    document.getElementById("header-trial-balance").textContent = `₹${data.trial_balance_discrepancy.toFixed(2)} Discrepancy`;
  } catch (e) {}
}

async function fetchHealthStatus() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    document.getElementById("header-trial-balance").textContent = `₹${data.trial_balance_discrepancy.toFixed(2)} Discrepancy`;
  } catch (e) {}
}

// ==========================================================================
// 6. INPATIENT (IPD) & BED MANAGEMENT MODULE
// ==========================================================================
function initIPDModule() {
  // Ward filter button event listeners
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentWardFilter = btn.dataset.ward;
      renderBedMatrix();
    });
  });

  // IPD bedside subtab listeners
  const ipdTabs = document.querySelectorAll(".ipd-tab-btn");
  ipdTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      ipdTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.ipdtab;
      document.querySelectorAll(".ipd-tab-content").forEach(c => c.classList.remove("active"));
      document.getElementById(`ipd-tab-${target}`).classList.add("active");
    });
  });

  // Quick Admit Active Patient Button
  document.getElementById("btn-quick-admit-active").addEventListener("click", () => {
    openAdmissionModal();
  });

  // Admission Modal close/cancel
  document.getElementById("btn-close-admit-modal").addEventListener("click", () => {
    document.getElementById("ipd-admission-modal").close();
  });
  document.getElementById("btn-cancel-admit").addEventListener("click", () => {
    document.getElementById("ipd-admission-modal").close();
  });

  // Confirm Admission form submit
  document.getElementById("ipd-admission-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentPatient) {
      alert("Please register or select an active patient from the Front Desk first.");
      return;
    }
    const bedId = document.getElementById("admit-select-bed").value;
    const doc = document.getElementById("admit-doctor-name").value;
    const icd10 = document.getElementById("admit-icd10").value;
    const icdDisplay = document.getElementById("admit-icd-display").value;
    const reason = document.getElementById("admit-reason").value;

    try {
      const res = await fetch("/api/v1/ipd/admit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mpi_id: currentPatient.mpi_id,
          bed_id: bedId,
          admitting_doctor_name: doc,
          admitting_diagnosis_icd10: icd10,
          admitting_diagnosis_display: icdDisplay,
          admission_reason: reason
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Admission failed");

      document.getElementById("ipd-admission-modal").close();
      await fetchBedMatrix();
      selectedBedId = bedId;
      await loadBedsideView(data.admission_id);
    } catch (err) {
      alert("Admission Error: " + err.message);
    }
  });

  // Nurse Charting form submit
  document.getElementById("ipd-nurse-chart-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentAdmissionId) return alert("No active inpatient admission selected.");

    const sys = parseFloat(document.getElementById("nurse-bp-sys").value);
    const dia = parseFloat(document.getElementById("nurse-bp-dia").value);
    const hr = parseFloat(document.getElementById("nurse-hr").value);
    const temp = parseFloat(document.getElementById("nurse-temp").value);
    const spo2 = parseFloat(document.getElementById("nurse-spo2").value);
    const rr = parseFloat(document.getElementById("nurse-rr").value);
    const notes = document.getElementById("nurse-notes").value;

    try {
      const res = await fetch("/api/v1/ipd/nursing/charts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admission_id: currentAdmissionId,
          systolic_bp: sys,
          diastolic_bp: dia,
          heart_rate: hr,
          temperature: temp,
          spo2: spo2,
          respiratory_rate: rr,
          nursing_notes: notes
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to log vitals");

      document.getElementById("nurse-notes").value = "";
      await loadNurseCharts(currentAdmissionId);
    } catch (err) {
      alert("Nurse Charting Error: " + err.message);
    }
  });

  // Doctor Round form submit
  document.getElementById("ipd-doctor-round-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentAdmissionId) return alert("No active inpatient admission selected.");

    const doc = document.getElementById("round-doctor-name").value;
    const assess = document.getElementById("round-assessment").value;
    const plan = document.getElementById("round-plan").value;
    const notes = document.getElementById("round-notes").value;

    try {
      const res = await fetch("/api/v1/ipd/doctor/rounds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admission_id: currentAdmissionId,
          doctor_name: doc,
          clinical_assessment: assess,
          plan_adjustments: plan,
          round_notes: notes
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to log round notes");

      await loadDoctorRounds(currentAdmissionId);
    } catch (err) {
      alert("Doctor Round Error: " + err.message);
    }
  });

  // Discharge form submit
  document.getElementById("ipd-discharge-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentAdmissionId) return alert("No active inpatient admission selected.");

    const condition = document.getElementById("discharge-condition").value;
    const course = document.getElementById("discharge-course").value;
    const icd10 = document.getElementById("discharge-icd10").value;
    const icdDisplay = document.getElementById("discharge-icd-display").value;
    const meds = document.getElementById("discharge-meds").value;
    const advice = document.getElementById("discharge-advice").value;
    const docSig = document.getElementById("discharge-doctor").value;

    try {
      const res = await fetch("/api/v1/ipd/discharge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admission_id: currentAdmissionId,
          condition_at_discharge: condition,
          hospital_course: course,
          final_diagnosis_icd10: icd10,
          final_diagnosis_display: icdDisplay,
          discharge_medications: meds,
          follow_up_advice: advice,
          doctor_signature: docSig
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Discharge failed");

      // Set currentEncounterId to the admission encounter so Cashier billing settles it!
      currentEncounterId = data.encounter_id;

      // Render Discharge Summary Card
      document.getElementById("ipd-discharge-form").classList.add("hidden");
      const summaryCard = document.getElementById("ipd-discharge-summary-card");
      summaryCard.classList.remove("hidden");
      document.getElementById("ipd-discharge-details").innerHTML = `
        <p><strong>Discharge ID:</strong> <code>${data.summary_id}</code></p>
        <p><strong>Encounter ID:</strong> <code>${data.encounter_id}</code></p>
        <p><strong>Final Diagnosis:</strong> ${data.final_diagnosis_display} (ICD-10: ${data.final_diagnosis_icd10})</p>
        <p><strong>Length of Stay:</strong> ${data.days_stayed} Day(s)</p>
        <p><strong>Accrued Room Tariff:</strong> ₹${data.total_room_charges.toFixed(2)} (Posted to Financial Ledger)</p>
        <p><strong>Condition at Discharge:</strong> ${data.condition_at_discharge}</p>
        <p><strong>Discharge Medications:</strong> ${data.discharge_medications}</p>
        <p><strong>Follow-Up Advice:</strong> ${data.follow_up_advice}</p>
        <p><strong>Signed by:</strong> ${data.doctor_signature} at ${data.signed_at.slice(0, 19)}</p>
      `;

      // Store summary for billing jump
      window._lastDischargeSummary = data;

      // Refresh bed matrix and ledger
      await fetchBedMatrix();
      await fetchHealthStatus();
    } catch (err) {
      alert("Discharge Error: " + err.message);
    }
  });

  // Proceed to Cashier Desk button
  document.getElementById("btn-ipd-goto-billing").addEventListener("click", () => {
    const summary = window._lastDischargeSummary;
    if (!summary) return;

    // Switch to billing tab
    document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
    const billingTab = document.querySelector('.tab-btn[data-tab="billing"]');
    if (billingTab) billingTab.classList.add("active");
    document.querySelectorAll(".viewport-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("panel-billing").classList.add("active");

    // Populate billing charges table with the inpatient stay
    const gross = summary.total_room_charges;
    const insurer = gross * 0.2;
    const patientShare = gross * 0.8;

    const tbody = document.getElementById("billing-charges-tbody");
    tbody.innerHTML = `
      <tr>
        <td><strong>Inpatient Bed Accommodation (${summary.days_stayed} Day Stay)</strong><br><small>Tariff: BED-STAY-TARIFF</small></td>
        <td><span class="badge badge-info">BedStay (${summary.released_bed})</span></td>
        <td>₹${gross.toFixed(2)}</td>
        <td>₹${patientShare.toFixed(2)}</td>
        <td>₹${insurer.toFixed(2)}</td>
      </tr>
    `;

    document.getElementById("billing-gross-total").textContent = `₹${gross.toFixed(2)}`;
    document.getElementById("billing-insurer-total").textContent = `₹${insurer.toFixed(2)}`;
    document.getElementById("billing-net-payable").textContent = `₹${patientShare.toFixed(2)}`;
    document.getElementById("pay-amount").value = patientShare.toFixed(2);
  });
}

async function fetchBedMatrix() {
  try {
    const res = await fetch("/api/v1/ipd/beds");
    const data = await res.json();
    currentBeds = data;

    // Update KPI counters
    const total = data.length;
    const available = data.filter(b => b.status === "AVAILABLE").length;
    const occupied = data.filter(b => b.status === "OCCUPIED").length;

    document.getElementById("ipd-kpi-total").textContent = total;
    document.getElementById("ipd-kpi-available").textContent = available;
    document.getElementById("ipd-kpi-occupied").textContent = occupied;

    renderBedMatrix();
  } catch (err) {
    console.error("Failed to fetch bed matrix:", err);
  }
}

function renderBedMatrix() {
  const container = document.getElementById("bed-matrix-container");
  let filtered = currentBeds;
  if (currentWardFilter !== "ALL") {
    filtered = currentBeds.filter(b => b.ward_type === currentWardFilter);
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty-state">No beds in this category.</div>';
    return;
  }

  container.innerHTML = filtered.map(bed => {
    const isAvail = bed.status === "AVAILABLE";
    const isSelected = selectedBedId === bed.bed_id;
    return `
      <div class="bed-card ${isAvail ? 'available' : 'occupied'} ${isSelected ? 'selected' : ''}" data-bedid="${bed.bed_id}">
        <div class="bed-card-header">
          <span class="bed-number-title">${bed.bed_number}</span>
          <span class="bed-ward-pill">${bed.ward_name}</span>
        </div>
        <div class="bed-tariff-tag">₹${bed.daily_rate.toLocaleString("en-IN")}/day</div>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.5rem;">
          ${bed.amenities.slice(0, 2).join(" • ")}
        </div>
        ${!isAvail ? `
          <div class="bed-patient-info">
            <div class="bed-patient-name">👤 ${bed.current_patient_name || 'Occupied'}</div>
            <div style="font-size:0.7rem; color:var(--text-muted);">Adm: ${bed.current_admission_id ? bed.current_admission_id.slice(0, 8) : '--'}</div>
          </div>
        ` : `
          <div style="font-size:0.75rem; color:#15803d; font-weight:600; margin-bottom:0.75rem;">
            🟢 Bed Sanitized & Ready
          </div>
        `}
        <div class="bed-actions">
          ${isAvail ? `
            <button type="button" class="btn btn-outline btn-sm btn-admit-here" data-bedid="${bed.bed_id}">
              ➕ Admit Patient
            </button>
          ` : `
            <button type="button" class="btn btn-primary btn-sm btn-view-bedside" data-admid="${bed.current_admission_id}" data-bedid="${bed.bed_id}">
              🩺 Manage Bedside & MAR
            </button>
          `}
        </div>
      </div>
    `;
  }).join("");

  // Attach card and button click listeners
  container.querySelectorAll(".btn-admit-here").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openAdmissionModal(btn.dataset.bedid);
    });
  });

  container.querySelectorAll(".btn-view-bedside").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedBedId = btn.dataset.bedid;
      loadBedsideView(btn.dataset.admid);
      renderBedMatrix();
    });
  });

  container.querySelectorAll(".bed-card").forEach(card => {
    card.addEventListener("click", () => {
      const bId = card.dataset.bedid;
      const b = currentBeds.find(x => x.bed_id === bId);
      if (b && b.status === "OCCUPIED" && b.current_admission_id) {
        selectedBedId = bId;
        loadBedsideView(b.current_admission_id);
        renderBedMatrix();
      } else if (b && b.status === "AVAILABLE") {
        openAdmissionModal(bId);
      }
    });
  });
}

function openAdmissionModal(preselectedBedId = null) {
  if (!currentPatient) {
    alert("Please register or select an active patient from the Front Desk first.");
    return;
  }

  document.getElementById("admit-modal-patient-name").textContent = `${currentPatient.first_name} ${currentPatient.last_name}`;
  document.getElementById("admit-modal-uhid").textContent = `UHID: ${currentPatient.uhid}`;

  const selectBed = document.getElementById("admit-select-bed");
  const availableBeds = currentBeds.filter(b => b.status === "AVAILABLE");

  if (availableBeds.length === 0) {
    alert("No beds currently available. All beds are occupied.");
    return;
  }

  selectBed.innerHTML = availableBeds.map(b => `
    <option value="${b.bed_id}" ${b.bed_id === preselectedBedId ? 'selected' : ''}>
      ${b.bed_number} (${b.ward_name}) - ₹${b.daily_rate.toLocaleString("en-IN")}/day
    </option>
  `).join("");

  document.getElementById("ipd-admission-modal").showModal();
}

async function loadBedsideView(admissionId) {
  if (!admissionId) return;
  currentAdmissionId = admissionId;

  try {
    const res = await fetch(`/api/v1/ipd/admissions/${admissionId}`);
    const adm = await res.json();
    if (!res.ok) throw new Error(adm.detail || "Failed to load admission");

    const bed = currentBeds.find(b => b.bed_id === adm.bed_id);
    const wardName = bed ? bed.ward_name : "Inpatient Ward";
    const bedNum = bed ? bed.bed_number : "Bed";
    const dailyRate = bed ? bed.daily_rate : 5000.0;

    // Show Bedside Content
    document.getElementById("ipd-bedside-unselected").classList.add("hidden");
    document.getElementById("ipd-bedside-content").classList.remove("hidden");

    // Header info
    document.getElementById("ipd-bedside-ward-bed").textContent = `Ward: ${wardName} | Bed: ${bedNum}`;
    document.getElementById("ipd-bedside-patient-name").textContent = adm.patient_name || (currentPatient ? `${currentPatient.first_name} ${currentPatient.last_name}` : "Patient");
    document.getElementById("ipd-bedside-meta").textContent = `IPD Adm #${adm.admission_id.slice(0, 8)} • ${adm.admitting_doctor_name} • Dx: ${adm.admitting_diagnosis_icd10}`;
    document.getElementById("ipd-bedside-rate").textContent = `₹${dailyRate.toLocaleString("en-IN")}/day`;
    document.getElementById("ipd-bedside-stay-days").textContent = `Admitted ${adm.admitted_at.slice(0, 10)} • Status: ${adm.status}`;

    // Reset discharge form & card
    document.getElementById("ipd-discharge-form").classList.remove("hidden");
    document.getElementById("ipd-discharge-summary-card").classList.add("hidden");
    document.getElementById("discharge-icd10").value = adm.admitting_diagnosis_icd10 || "M23.30";
    document.getElementById("discharge-icd-display").value = adm.admitting_diagnosis_display || "Tear of medial meniscus of knee";

    // Load Charts and Rounds
    await loadNurseCharts(admissionId);
    await loadDoctorRounds(admissionId);
  } catch (err) {
    console.error("Error loading bedside view:", err);
  }
}

async function loadNurseCharts(admissionId) {
  try {
    const res = await fetch(`/api/v1/ipd/admissions/${admissionId}/charts`);
    const charts = await res.json();
    const container = document.getElementById("nurse-charts-timeline");

    if (charts.length === 0) {
      container.innerHTML = '<div class="empty-state">No nurse charts recorded yet.</div>';
      return;
    }

    container.innerHTML = charts.map(c => `
      <div class="ipd-timeline-card">
        <div class="ipd-timeline-time">
          <strong>${c.recorded_by}</strong>
          <span>${c.recorded_at.slice(0, 19).replace('T', ' ')}</span>
        </div>
        <div class="vitals-pill-grid">
          <span class="vitals-pill">BP: ${c.systolic_bp}/${c.diastolic_bp} mmHg</span>
          <span class="vitals-pill">Pulse: ${c.heart_rate} bpm</span>
          <span class="vitals-pill">Temp: ${c.temperature} °F</span>
          <span class="vitals-pill">SpO2: ${c.spo2}%</span>
          <span class="vitals-pill">RR: ${c.respiratory_rate} /min</span>
        </div>
        ${c.nursing_notes ? `<div class="timeline-note">"${c.nursing_notes}"</div>` : ''}
      </div>
    `).join("");
  } catch (err) {
    console.error("Error loading nurse charts:", err);
  }
}

async function loadDoctorRounds(admissionId) {
  try {
    const res = await fetch(`/api/v1/ipd/admissions/${admissionId}/rounds`);
    const rounds = await res.json();
    const container = document.getElementById("doctor-rounds-timeline");

    if (rounds.length === 0) {
      container.innerHTML = '<div class="empty-state">No doctor rounds recorded yet.</div>';
      return;
    }

    container.innerHTML = rounds.map(r => `
      <div class="ipd-timeline-card" style="border-left-color: #059669;">
        <div class="ipd-timeline-time">
          <strong>${r.doctor_name}</strong>
          <span>${r.round_time.slice(0, 19).replace('T', ' ')}</span>
        </div>
        <div style="font-size:0.8rem; margin-top:0.25rem;">
          <div><strong>Assessment:</strong> ${r.clinical_assessment}</div>
          ${r.plan_adjustments ? `<div><strong>Plan Adjustments:</strong> ${r.plan_adjustments}</div>` : ''}
          <div class="timeline-note">"${r.round_notes}"</div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Error loading doctor rounds:", err);
  }
}

// ==========================================================================
// 7. DIAGNOSTIC LABORATORY & RADIOLOGY (LIS/RIS) MODULE
// ==========================================================================
function initDiagnosticsModule() {
  // Filter buttons
  const filterBtns = document.querySelectorAll(".filter-btn[data-diagfilter]");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentDiagFilter = btn.dataset.diagfilter;
      renderDiagnosticsWorklist();
    });
  });

  // Quick Order button
  document.getElementById("btn-quick-diag-order").addEventListener("click", () => {
    openDiagnosticOrderModal();
  });

  // Modal close/cancel
  document.getElementById("btn-close-diag-modal").addEventListener("click", () => {
    document.getElementById("diag-order-modal").close();
  });
  document.getElementById("btn-cancel-diag-order").addEventListener("click", () => {
    document.getElementById("diag-order-modal").close();
  });

  // Confirm Diagnostic Order form submit
  document.getElementById("diag-order-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentPatient) {
      alert("Please register or select an active patient from the Front Desk first.");
      return;
    }

    const itemCode = document.getElementById("diag-select-test").value;
    const docName = document.getElementById("diag-order-doctor").value;
    const history = document.getElementById("diag-order-history").value;
    const isStat = document.getElementById("diag-order-stat").value === "true";
    const fasting = document.getElementById("diag-order-fasting").value;

    const encId = currentEncounterId || "00000000-0000-0000-0000-" + Date.now().toString().slice(-12);

    try {
      const res = await fetch("/api/v1/diagnostics/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mpi_id: currentPatient.mpi_id,
          encounter_id: encId,
          item_code: itemCode,
          ordering_doctor_name: docName,
          clinical_history: history,
          fasting_status: fasting,
          is_stat: isStat
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Order placement failed");

      document.getElementById("diag-order-modal").close();
      await fetchDiagnosticsWorklist();
      selectedDiagOrderId = data.order_id;
      loadDiagnosticWorkstation(data.order_id);
      await fetchHealthStatus();
    } catch (err) {
      alert("Diagnostic Order Error: " + err.message);
    }
  });

  // Specimen Collection button
  document.getElementById("btn-execute-collect").addEventListener("click", async () => {
    if (!selectedDiagOrderId) return;
    const phleb = document.getElementById("ws-phleb-name").value;

    try {
      const res = await fetch("/api/v1/diagnostics/specimens/collect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: selectedDiagOrderId,
          phlebotomist_name: phleb
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Specimen collection failed");

      await fetchDiagnosticsWorklist();
      loadDiagnosticWorkstation(selectedDiagOrderId);
    } catch (err) {
      alert("Collection Error: " + err.message);
    }
  });

  // Lab Results form submit
  document.getElementById("ws-lab-result-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedDiagOrderId) return;

    const paramInputs = document.querySelectorAll(".ws-param-input");
    const results = {};
    paramInputs.forEach(input => {
      results[input.dataset.paramcode] = parseFloat(input.value);
    });

    try {
      const res = await fetch("/api/v1/diagnostics/results/lab", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: selectedDiagOrderId,
          parameter_results: results
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Result entry failed");

      await fetchDiagnosticsWorklist();
      loadDiagnosticWorkstation(selectedDiagOrderId);
    } catch (err) {
      alert("Lab Result Error: " + err.message);
    }
  });

  // Radiology Results form submit
  document.getElementById("ws-rad-result-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedDiagOrderId) return;

    const doc = document.getElementById("ws-rad-doctor").value;
    const tech = document.getElementById("ws-rad-technique").value;
    const findings = document.getElementById("ws-rad-findings").value;
    const imp = document.getElementById("ws-rad-impression").value;

    try {
      const res = await fetch("/api/v1/diagnostics/results/radiology", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: selectedDiagOrderId,
          radiologist_name: doc,
          technique: tech,
          findings: findings,
          impression: imp,
          clinical_indication: "Diagnostic Imaging Evaluation"
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Radiology report entry failed");

      await fetchDiagnosticsWorklist();
      loadDiagnosticWorkstation(selectedDiagOrderId);
    } catch (err) {
      alert("Radiology Report Error: " + err.message);
    }
  });

  // Verification form submit
  document.getElementById("ws-verify-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedDiagOrderId) return;

    const vName = document.getElementById("ws-verifier-name").value;
    const vQual = document.getElementById("ws-verifier-qual").value;
    const vReg = document.getElementById("ws-verifier-reg").value;
    const vNotes = document.getElementById("ws-verifier-notes").value;

    try {
      const res = await fetch("/api/v1/diagnostics/reports/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: selectedDiagOrderId,
          verifier_name: vName,
          verifier_qualification: vQual,
          verifier_registration_no: vReg,
          clinical_comments: vNotes
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");

      await fetchDiagnosticsWorklist();
      loadDiagnosticWorkstation(selectedDiagOrderId);
    } catch (err) {
      alert("Verification Error: " + err.message);
    }
  });
}

async function fetchDiagnosticsCatalog() {
  try {
    const res = await fetch("/api/v1/diagnostics/catalog");
    const data = await res.json();
    currentDiagCatalog = data;

    const select = document.getElementById("diag-select-test");
    if (!select) return;

    select.innerHTML = data.map(item => `
      <option value="${item.item_code}">
        [${item.category === 'LABORATORY' ? 'LAB' : 'RAD'}] ${item.item_name} (${item.standard_coding_system.includes('loinc') ? 'LOINC' : 'SNOMED'}: ${item.standard_code}) - ₹${item.base_tariff.toFixed(2)}
      </option>
    `).join("");
  } catch (err) {
    console.error("Failed to fetch diagnostics catalog:", err);
  }
}

async function fetchDiagnosticsWorklist() {
  try {
    const res = await fetch("/api/v1/diagnostics/worklist");
    const data = await res.json();
    currentDiagOrders = data;

    // KPI Counters
    const total = data.length;
    const pending = data.filter(o => o.status === "ORDERED").length;
    const processing = data.filter(o => o.status === "SAMPLE_COLLECTED" || o.status === "RESULTED").length;
    const verified = data.filter(o => o.status === "VERIFIED").length;

    document.getElementById("diag-kpi-total").textContent = total;
    document.getElementById("diag-kpi-pending").textContent = pending;
    document.getElementById("diag-kpi-processing").textContent = processing;
    document.getElementById("diag-kpi-verified").textContent = verified;

    renderDiagnosticsWorklist();
  } catch (err) {
    console.error("Failed to fetch diagnostics worklist:", err);
  }
}

function renderDiagnosticsWorklist() {
  const container = document.getElementById("diag-worklist-container");
  let filtered = currentDiagOrders;

  if (currentDiagFilter !== "ALL") {
    filtered = currentDiagOrders.filter(o => o.category === currentDiagFilter);
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty-state">No diagnostic orders in queue.</div>';
    return;
  }

  container.innerHTML = filtered.map(order => {
    const isSelected = selectedDiagOrderId === order.order_id;
    return `
      <div class="diag-worklist-card ${isSelected ? 'selected' : ''}" data-orderid="${order.order_id}">
        <div class="diag-card-header">
          <div>
            <div class="diag-card-title">${order.item_name}</div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.15rem;">
              Ref: ${order.ordering_doctor_name} • Tariff: ₹${order.tariff_amount.toFixed(2)}
            </div>
          </div>
          <span class="diag-status-pill diag-status-${order.status}">${order.status.replace('_', ' ')}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
          <span class="diag-specimen-badge">${order.specimen_type}</span>
          <span>${order.accession_number ? `<strong>${order.accession_number}</strong>` : (order.sample_barcode ? `<code>${order.sample_barcode}</code>` : 'Pending Sample')}</span>
        </div>
      </div>
    `;
  }).join("");

  // Attach card click handlers
  container.querySelectorAll(".diag-worklist-card").forEach(card => {
    card.addEventListener("click", () => {
      const oId = card.dataset.orderid;
      selectedDiagOrderId = oId;
      renderDiagnosticsWorklist();
      loadDiagnosticWorkstation(oId);
    });
  });
}

function openDiagnosticOrderModal() {
  if (!currentPatient) {
    alert("Please register or select an active patient from the Front Desk first.");
    return;
  }

  document.getElementById("diag-modal-patient-name").textContent = `${currentPatient.first_name} ${currentPatient.last_name}`;
  document.getElementById("diag-modal-uhid").textContent = `UHID: ${currentPatient.uhid}`;
  document.getElementById("diag-order-modal").showModal();
}

function loadDiagnosticWorkstation(orderId) {
  const order = currentDiagOrders.find(o => o.order_id === orderId);
  if (!order) return;

  // Unhide content
  document.getElementById("diag-workstation-unselected").classList.add("hidden");
  document.getElementById("diag-workstation-content").classList.remove("hidden");

  // Header
  document.getElementById("ws-category-badge").textContent = `${order.category} • ${order.modality}`;
  document.getElementById("ws-test-name").textContent = order.item_name;
  document.getElementById("ws-patient-meta").textContent = `Patient MPI: ${order.mpi_id.slice(0, 8)} • Ref: ${order.ordering_doctor_name} • Indication: ${order.clinical_history}`;
  document.getElementById("ws-tariff-amount").textContent = `₹${order.tariff_amount.toFixed(2)}`;
  document.getElementById("ws-coding-info").textContent = `${order.standard_coding_system.includes('loinc') ? 'LOINC' : 'SNOMED'}: ${order.standard_code}`;

  // Update Workflow Stage Bar
  const stages = ["ordered", "collected", "resulted", "verified"];
  const statusMap = {
    "ORDERED": 0,
    "SAMPLE_COLLECTED": 1,
    "RESULTED": 2,
    "VERIFIED": 3
  };
  const activeIdx = statusMap[order.status] ?? 0;

  stages.forEach((st, idx) => {
    const el = document.getElementById(`stage-${st}`);
    el.classList.remove("active", "done");
    if (idx < activeIdx) {
      el.classList.add("done");
    } else if (idx === activeIdx) {
      el.classList.add("active");
    }
  });

  // Hide all step panels first
  document.querySelectorAll(".ws-step-panel").forEach(p => p.classList.add("hidden"));

  // Stage 1: Ordered -> Show Collection
  if (order.status === "ORDERED") {
    const stepCollect = document.getElementById("ws-step-collect");
    stepCollect.classList.remove("hidden");
    document.getElementById("ws-req-specimen").textContent = order.specimen_type;
  }
  // Stage 2: Sample Collected -> Show Lab Analyzer or Radiology Form
  else if (order.status === "SAMPLE_COLLECTED") {
    if (order.category === "LABORATORY") {
      const stepLab = document.getElementById("ws-step-lab-results");
      stepLab.classList.remove("hidden");
      document.getElementById("ws-sample-tag").textContent = `${order.sample_barcode} (${order.accession_number})`;

      // Render parameter inputs
      const catItem = currentDiagCatalog.find(c => c.item_code === order.item_code);
      const container = document.getElementById("ws-parameter-inputs-container");
      if (catItem && catItem.parameters.length > 0) {
        container.innerHTML = catItem.parameters.map(p => `
          <div class="param-input-card">
            <div>
              <div class="param-title">${p.parameter_name}</div>
              <div class="param-meta">LOINC: ${p.loinc_code} • Unit: ${p.unit}</div>
            </div>
            <div>
              <input type="number" step="0.01" class="ws-param-input" data-paramcode="${p.parameter_code}" 
                     placeholder="e.g. ${(p.reference_low ? (p.reference_low + (p.reference_high - p.reference_low)*0.5).toFixed(1) : '5.0')}" 
                     value="${(p.reference_low ? (p.reference_low + (p.reference_high - p.reference_low)*0.5).toFixed(1) : '5.0')}" required>
            </div>
            <div class="param-ref-range">Ref: ${p.reference_low ?? '--'} - ${p.reference_high ?? '--'} ${p.unit}</div>
          </div>
        `).join("");
      }
    } else {
      const stepRad = document.getElementById("ws-step-rad-results");
      stepRad.classList.remove("hidden");
    }
  }
  // Stage 3: Resulted -> Show Verification
  else if (order.status === "RESULTED") {
    const stepVerify = document.getElementById("ws-step-verify");
    stepVerify.classList.remove("hidden");

    const prevTable = document.getElementById("ws-results-preview-table");
    if (order.category === "LABORATORY") {
      prevTable.innerHTML = `
        <table class="report-table">
          <thead>
            <tr><th>Investigation Parameter</th><th>LOINC</th><th>Measured Value</th><th>Reference Range</th><th>Flag</th></tr>
          </thead>
          <tbody>
            ${order.lab_results.map(r => `
              <tr>
                <td><strong>${r.parameter_name}</strong></td>
                <td><code>${r.loinc_code}</code></td>
                <td><strong>${r.measured_value}</strong> ${r.unit}</td>
                <td>${r.reference_range_display}</td>
                <td><span class="flag-badge ${r.flag}">${r.flag}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    } else {
      prevTable.innerHTML = `
        <div style="background:#f8fafc; border:1px solid var(--border); padding:1rem; border-radius:var(--radius-sm); font-size:0.85rem;">
          <div><strong>Technique:</strong> ${order.radiology_technique || '--'}</div>
          <div style="margin-top:0.5rem;"><strong>Findings:</strong> ${order.radiology_findings || '--'}</div>
          <div style="margin-top:0.5rem; color:#b45309;"><strong>Impression:</strong> ${order.radiology_impression || '--'}</div>
        </div>
      `;
    }
  }
  // Stage 4: Verified -> Show Official Diagnostic Report Card
  else if (order.status === "VERIFIED") {
    const stepRep = document.getElementById("ws-step-report-card");
    stepRep.classList.remove("hidden");

    document.getElementById("rep-patient-name").textContent = currentPatient ? `${currentPatient.first_name} ${currentPatient.last_name}` : "Patient";
    document.getElementById("rep-accession").textContent = order.accession_number || "ACC-2026";
    document.getElementById("rep-uhid").textContent = currentPatient ? currentPatient.uhid : "U-2026";
    document.getElementById("rep-specimen").textContent = order.specimen_type;
    document.getElementById("rep-doctor").textContent = order.ordering_doctor_name;
    document.getElementById("rep-reported-at").textContent = order.verified_at ? order.verified_at.slice(0, 19).replace('T', ' ') : new Date().toISOString().slice(0, 19);
    document.getElementById("rep-barcode-sub").textContent = order.sample_barcode || "SMP-2026";
    document.getElementById("rep-signer-name").textContent = order.verified_by || "Consultant Pathologist";
    document.getElementById("rep-signer-reg").textContent = `Medical Council Reg: ${order.verifier_registration_no || 'MMC-XXXX'}`;

    const bodyContainer = document.getElementById("rep-body-content");
    if (order.category === "LABORATORY") {
      bodyContainer.innerHTML = `
        <table class="report-table">
          <thead>
            <tr>
              <th>Test Parameter</th>
              <th>Standard (LOINC)</th>
              <th>Observed Result</th>
              <th>Biological Reference Interval</th>
              <th>Flag</th>
            </tr>
          </thead>
          <tbody>
            ${order.lab_results.map(r => `
              <tr>
                <td><strong>${r.parameter_name}</strong></td>
                <td><code>${r.loinc_code}</code></td>
                <td><strong>${r.measured_value}</strong> ${r.unit}</td>
                <td>${r.reference_range_display}</td>
                <td><span class="flag-badge ${r.flag}">${r.flag}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
        ${order.verifier_comments ? `<div style="font-size:0.8rem; font-style:italic; margin-top:0.5rem;">Note: ${order.verifier_comments}</div>` : ''}
      `;
    } else {
      bodyContainer.innerHTML = `
        <div style="font-size:0.85rem; line-height:1.6; margin:1rem 0;">
          <div style="margin-bottom:0.75rem;">
            <strong>Modality / Study:</strong> ${order.item_name} (SNOMED CT: <code>${order.standard_code}</code>)
          </div>
          <div style="margin-bottom:0.75rem;">
            <strong>Technique:</strong> ${order.radiology_technique || '--'}
          </div>
          <div style="margin-bottom:0.75rem;">
            <strong>Detailed Radiological Findings:</strong><br>
            ${order.radiology_findings || '--'}
          </div>
          <div style="padding:0.75rem; background:#fffbeb; border-left:4px solid #d97706; border-radius:4px;">
            <strong style="color:#b45309;">IMPRESSION:</strong><br>
            ${order.radiology_impression || '--'}
          </div>
        </div>
      `;
    }
  }
}

// ==========================================================================
// 8. PHARMACY & CLOSED-LOOP DISPENSING MODULE
// ==========================================================================
function initPharmacyModule() {
  // Inventory filter buttons
  const filterBtns = document.querySelectorAll(".filter-btn[data-pharmfilter]");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentPharmFilter = btn.dataset.pharmfilter;
      renderPharmacyInventory();
    });
  });

  // Restock Modal triggers
  const btnOpenRestock = document.getElementById("btn-open-restock-modal");
  if (btnOpenRestock) {
    btnOpenRestock.addEventListener("click", () => {
      document.getElementById("pharm-restock-modal").showModal();
    });
  }
  document.getElementById("btn-close-restock-modal").addEventListener("click", () => {
    document.getElementById("pharm-restock-modal").close();
  });
  document.getElementById("btn-cancel-restock").addEventListener("click", () => {
    document.getElementById("pharm-restock-modal").close();
  });

  // Restock form submit
  document.getElementById("pharm-restock-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const itemCode = document.getElementById("restock-select-item").value;
    const batchNum = document.getElementById("restock-batch-num").value;
    const expDate = document.getElementById("restock-expiry-date").value;
    const qty = parseInt(document.getElementById("restock-qty").value, 10);
    const mrp = parseFloat(document.getElementById("restock-mrp").value);
    const cost = parseFloat(document.getElementById("restock-cost").value);
    const mfr = document.getElementById("restock-mfr").value;

    try {
      const res = await fetch("/api/v1/pharmacy/stock/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_code: itemCode,
          batch_number: batchNum,
          expiry_date: expDate,
          mrp: mrp,
          unit_cost: cost,
          quantity: qty,
          manufacturer: mfr
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Restock failed");

      document.getElementById("pharm-restock-modal").close();
      await fetchPharmacyInventory();
    } catch (err) {
      alert("Restock Error: " + err.message);
    }
  });

  // Add Manual Medicine Row
  document.getElementById("btn-pharm-add-manual-row").addEventListener("click", () => {
    addDispenseLine();
  });

  // Submit Dispense
  document.getElementById("btn-submit-dispense").addEventListener("click", async () => {
    if (!currentPatient) {
      alert("Please register or select an active patient from the Front Desk first.");
      return;
    }

    const lineCards = document.querySelectorAll(".dispense-line-card");
    if (lineCards.length === 0) {
      alert("No medication lines to dispense.");
      return;
    }

    const items = [];
    lineCards.forEach(card => {
      const itemCode = card.querySelector(".disp-item-select").value;
      const batchNum = card.querySelector(".disp-batch-select").value;
      const qty = parseInt(card.querySelector(".disp-qty-input").value, 10);
      if (itemCode && batchNum && qty > 0) {
        items.push({
          item_code: itemCode,
          batch_number: batchNum,
          quantity_to_dispense: qty
        });
      }
    });

    if (items.length === 0) {
      alert("Please specify valid items and quantities to dispense.");
      return;
    }

    const encId = currentEncounterId || "00000000-0000-0000-0000-" + Date.now().toString().slice(-12);
    const pharmName = document.getElementById("pharm-signer-name").value;
    const pharmReg = document.getElementById("pharm-signer-reg").value;

    try {
      const res = await fetch("/api/v1/pharmacy/dispense", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mpi_id: currentPatient.mpi_id,
          encounter_id: encId,
          pharmacist_name: pharmName,
          pharmacist_reg_no: pharmReg,
          items: items,
          patient_co_pay_ratio: 0.8
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Dispense failed");

      // Render Receipt Card
      const receiptCard = document.getElementById("pharm-receipt-card");
      receiptCard.classList.remove("hidden");
      document.getElementById("pharm-receipt-details").innerHTML = `
        <p><strong>Invoice / Dispense No:</strong> <code>${data.dispense_number}</code></p>
        <p><strong>Patient:</strong> ${data.patient_name} (UHID: ${data.patient_uhid})</p>
        <p><strong>Dispensed At:</strong> ${data.dispensed_at.slice(0, 19).replace('T', ' ')}</p>
        <p><strong>Verified by:</strong> ${data.pharmacist_name} (${data.pharmacist_reg_no})</p>
        <div style="margin:0.75rem 0;">
          <table class="report-table">
            <thead>
              <tr><th>Item</th><th>Batch</th><th>Expiry</th><th>Qty</th><th>MRP</th><th>Total</th></tr>
            </thead>
            <tbody>
              ${data.lines.map(l => `
                <tr>
                  <td><strong>${l.brand_name}</strong><br><small>${l.generic_name}</small></td>
                  <td><code>${l.batch_number}</code></td>
                  <td>${l.expiry_date}</td>
                  <td>${l.quantity_dispensed}</td>
                  <td>₹${l.unit_price.toFixed(2)}</td>
                  <td><strong>₹${l.total_price.toFixed(2)}</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
        <div style="display:flex; justify-content:space-between; font-weight:700; border-top:1px solid #cbd5e1; padding-top:0.5rem;">
          <span>Gross Total: ₹${data.gross_total.toFixed(2)}</span>
          <span style="color:#047857;">Patient Share (80%): ₹${data.patient_share.toFixed(2)}</span>
          <span style="color:#b45309;">Insurer / TPA (20%): ₹${data.insurer_share.toFixed(2)}</span>
        </div>
      `;

      window._lastPharmacyDispense = data;
      await fetchPharmacyInventory();
      await fetchHealthStatus();
    } catch (err) {
      alert("Dispense Error: " + err.message);
    }
  });

  // Proceed to Cashier Desk
  document.getElementById("btn-pharm-goto-billing").addEventListener("click", () => {
    const data = window._lastPharmacyDispense;
    if (!data) return;

    // Switch to billing tab
    document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
    const billingTab = document.querySelector('.tab-btn[data-tab="billing"]');
    if (billingTab) billingTab.classList.add("active");
    document.querySelectorAll(".viewport-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("panel-billing").classList.add("active");

    // Populate billing charges table with the pharmacy items
    const tbody = document.getElementById("billing-charges-tbody");
    tbody.innerHTML = data.lines.map(l => `
      <tr>
        <td><strong>${l.brand_name} (${l.quantity_dispensed} units)</strong><br><small>Batch: ${l.batch_number} • Exp: ${l.expiry_date}</small></td>
        <td><span class="badge badge-info">Pharmacy Dispense</span></td>
        <td>₹${l.total_price.toFixed(2)}</td>
        <td>₹${(l.total_price * 0.8).toFixed(2)}</td>
        <td>₹${(l.total_price * 0.2).toFixed(2)}</td>
      </tr>
    `).join("");

    document.getElementById("billing-gross-total").textContent = `₹${data.gross_total.toFixed(2)}`;
    document.getElementById("billing-insurer-total").textContent = `₹${data.insurer_share.toFixed(2)}`;
    document.getElementById("billing-net-payable").textContent = `₹${data.patient_share.toFixed(2)}`;
    document.getElementById("pay-amount").value = data.patient_share.toFixed(2);
  });
}

async function fetchPharmacyInventory() {
  try {
    const res = await fetch("/api/v1/pharmacy/inventory");
    const data = await res.json();
    currentPharmacyInventory = data;

    const alertRes = await fetch("/api/v1/pharmacy/alerts");
    const alerts = await alertRes.json();

    const dispRes = await fetch("/api/v1/pharmacy/dispenses");
    const dispenses = await dispRes.json();

    // KPI Counters
    document.getElementById("pharm-kpi-skus").textContent = data.length;
    const totalUnits = data.reduce((sum, item) => sum + item.batches.reduce((bSum, b) => bSum + b.quantity_available, 0), 0);
    document.getElementById("pharm-kpi-units").textContent = totalUnits.toLocaleString("en-IN");
    document.getElementById("pharm-kpi-alerts").textContent = alerts.near_expiry_count + alerts.expired_count;
    document.getElementById("pharm-kpi-dispenses").textContent = dispenses.length;

    // Populate restock select
    const select = document.getElementById("restock-select-item");
    if (select) {
      select.innerHTML = data.map(i => `
        <option value="${i.item_code}">${i.brand_name} (${i.generic_name}) - Current Stock: ${i.batches.reduce((s,b)=>s+b.quantity_available,0)}</option>
      `).join("");
    }

    renderPharmacyInventory();
  } catch (err) {
    console.error("Failed to fetch pharmacy inventory:", err);
  }
}

function renderPharmacyInventory() {
  const container = document.getElementById("pharm-inventory-container");
  if (!container) return;

  let filtered = currentPharmacyInventory;
  if (currentPharmFilter === "HEALTHY") {
    filtered = currentPharmacyInventory.filter(i => {
      const hasAlert = i.batches.some(b => {
        const exp = new Date(b.expiry_date);
        const today = new Date();
        const diffDays = (exp - today) / (1000 * 60 * 60 * 24);
        return diffDays <= 90;
      });
      return !hasAlert;
    });
  } else if (currentPharmFilter === "ALERTS") {
    filtered = currentPharmacyInventory.filter(i => {
      return i.batches.some(b => {
        const exp = new Date(b.expiry_date);
        const today = new Date();
        const diffDays = (exp - today) / (1000 * 60 * 60 * 24);
        return diffDays <= 90;
      });
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty-state">No pharmacy inventory in this filter.</div>';
    return;
  }

  container.innerHTML = filtered.map(item => {
    const totalStock = item.batches.reduce((sum, b) => sum + b.quantity_available, 0);
    return `
      <div class="pharm-item-card">
        <div class="pharm-item-header">
          <div>
            <div class="pharm-brand-title">${item.brand_name} <small style="color:var(--primary);">${item.strength}</small></div>
            <div class="pharm-generic-sub">${item.generic_name}</div>
          </div>
          <span class="pharm-stock-pill pharm-stock-HEALTHY">${totalStock} Units Available</span>
        </div>

        <table class="pharm-batch-table">
          <thead>
            <tr><th>Batch No.</th><th>Expiry</th><th>MRP</th><th>Stock</th><th>Status</th></tr>
          </thead>
          <tbody>
            ${item.batches.map(b => {
              const exp = new Date(b.expiry_date);
              const today = new Date();
              const diffDays = (exp - today) / (1000 * 60 * 60 * 24);
              let tag = '<span class="batch-tag-healthy">🟢 Good</span>';
              if (diffDays < 0) {
                tag = '<span class="batch-tag-expired">🔴 EXPIRED</span>';
              } else if (diffDays <= 90) {
                tag = `<span class="batch-tag-near">🟡 Exp: ${Math.round(diffDays)}d</span>`;
              }
              return `
                <tr>
                  <td><code>${b.batch_number}</code></td>
                  <td>${b.expiry_date}</td>
                  <td>₹${b.mrp.toFixed(2)}</td>
                  <td><strong>${b.quantity_available}</strong></td>
                  <td>${tag}</td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>
    `;
  }).join("");
}

function populatePrescriptionDispenseQueue() {
  if (currentPatient) {
    document.getElementById("pharm-patient-name").textContent = `Active Patient: ${currentPatient.first_name} ${currentPatient.last_name}`;
    document.getElementById("pharm-patient-meta").textContent = `UHID: ${currentPatient.uhid} • Dr. Anup Khatri (Orthopaedics)`;
  }

  const container = document.getElementById("pharm-dispense-lines-container");
  if (!container) return;
  container.innerHTML = "";

  // Pre-seed with prescription medications: Ezorb Forte & Pan 40
  addDispenseLine("MED-EZORB-FORTE", 30);
  addDispenseLine("MED-PAN-40", 10);
}

function addDispenseLine(defaultItemCode = null, defaultQty = 10) {
  const container = document.getElementById("pharm-dispense-lines-container");
  if (!container) return;

  const itemOptions = currentPharmacyInventory.map(i => `
    <option value="${i.item_code}" ${i.item_code === defaultItemCode ? 'selected' : ''}>
      ${i.brand_name} (${i.strength})
    </option>
  `).join("");

  const lineCard = document.createElement("div");
  lineCard.className = "dispense-line-card";
  lineCard.innerHTML = `
    <div>
      <select class="disp-item-select">
        ${itemOptions}
      </select>
    </div>
    <div>
      <select class="disp-batch-select">
        <!-- Batches populated based on chosen item -->
      </select>
    </div>
    <div>
      <input type="number" class="disp-qty-input" min="1" value="${defaultQty}">
    </div>
    <div style="font-weight:700; text-align:right;">
      <span class="disp-line-total">₹0.00</span>
    </div>
    <div>
      <button type="button" class="btn-remove-line" title="Remove line">&times;</button>
    </div>
  `;

  container.appendChild(lineCard);

  const itemSelect = lineCard.querySelector(".disp-item-select");
  const batchSelect = lineCard.querySelector(".disp-batch-select");
  const qtyInput = lineCard.querySelector(".disp-qty-input");
  const removeBtn = lineCard.querySelector(".btn-remove-line");

  function updateBatches() {
    const itemCode = itemSelect.value;
    const item = currentPharmacyInventory.find(i => i.item_code === itemCode);
    if (!item || item.batches.length === 0) {
      batchSelect.innerHTML = '<option value="">No batches</option>';
      return;
    }
    // FEFO: sort by expiry
    const sorted = [...item.batches].sort((a,b) => new Date(a.expiry_date) - new Date(b.expiry_date));
    batchSelect.innerHTML = sorted.map(b => {
      const exp = new Date(b.expiry_date);
      const isExp = exp < new Date();
      return `
        <option value="${b.batch_number}" data-mrp="${b.mrp}" data-avail="${b.quantity_available}" ${isExp ? 'disabled style="color:red;"' : ''}>
          ${b.batch_number} (Exp: ${b.expiry_date}) [Stock: ${b.quantity_available}] ${isExp ? '(EXPIRED)' : ''}
        </option>
      `;
    }).join("");
    updateLinePrice();
  }

  function updateLinePrice() {
    const opt = batchSelect.selectedOptions[0];
    const mrp = opt ? parseFloat(opt.dataset.mrp || 0) : 0;
    const qty = parseInt(qtyInput.value || 0, 10);
    const lineTotal = mrp * qty;
    lineCard.querySelector(".disp-line-total").textContent = `₹${lineTotal.toFixed(2)}`;
    recalculatePharmacyTotals();
  }

  itemSelect.addEventListener("change", () => {
    updateBatches();
  });
  batchSelect.addEventListener("change", () => {
    updateLinePrice();
  });
  qtyInput.addEventListener("input", () => {
    updateLinePrice();
  });
  removeBtn.addEventListener("click", () => {
    lineCard.remove();
    recalculatePharmacyTotals();
  });

  updateBatches();
}

function recalculatePharmacyTotals() {
  const lineCards = document.querySelectorAll(".dispense-line-card");
  let gross = 0.0;
  lineCards.forEach(c => {
    const opt = c.querySelector(".disp-batch-select").selectedOptions[0];
    const mrp = opt ? parseFloat(opt.dataset.mrp || 0) : 0;
    const qty = parseInt(c.querySelector(".disp-qty-input").value || 0, 10);
    gross += (mrp * qty);
  });

  const patientShare = gross * 0.8;
  const insurerShare = gross * 0.2;

  document.getElementById("pharm-bill-gross").textContent = `₹${gross.toFixed(2)}`;
  document.getElementById("pharm-bill-split").textContent = `Patient: ₹${patientShare.toFixed(2)} • TPA: ₹${insurerShare.toFixed(2)}`;
}

// =============================================================================
// EMERGENCY DEPARTMENT (ED / ER) & ESI TRIAGE MODULE
// =============================================================================

function initEmergencyModule() {
  const formTriage = document.getElementById("form-er-triage");
  const formIntervention = document.getElementById("form-er-intervention");
  const formDisposition = document.getElementById("form-er-disposition");
  const btnRefreshBays = document.getElementById("btn-refresh-er-bays");
  const activeCasesSelect = document.getElementById("er-active-cases-select");
  const dispTypeSelect = document.getElementById("er-disp-type");

  if (btnRefreshBays) {
    btnRefreshBays.addEventListener("click", () => {
      fetchEmergencyBays();
      fetchActiveEmergencyCases();
    });
  }

  if (activeCasesSelect) {
    activeCasesSelect.addEventListener("change", (e) => {
      const caseId = e.target.value;
      if (caseId) {
        selectEmergencyCase(caseId);
      } else {
        selectedEmergencyCaseId = null;
        document.getElementById("er-active-case-banner").style.display = "none";
        document.getElementById("er-resus-console").style.display = "none";
        document.getElementById("er-disposition-console").style.display = "none";
        document.getElementById("er-no-case-placeholder").style.display = "block";
      }
    });
  }

  // Quick intervention button listeners
  const btnDefib = document.getElementById("btn-quick-defib");
  if (btnDefib) {
    btnDefib.addEventListener("click", () => {
      quickFillIntervention("DEFIBRILLATION", "Synchronized biphasic shock 200J delivered for VF/VT", "Inj Adrenaline 1mg IV push stat");
    });
  }
  const btnIntub = document.getElementById("btn-quick-intub");
  if (btnIntub) {
    btnIntub.addEventListener("click", () => {
      quickFillIntervention("INTUBATION", "Video laryngoscopy: ETT 7.5mm cuffed placed at 22cm, bilateral air entry confirmed", "Inj Propofol 100mg + Inj Rocuronium 50mg");
    });
  }
  const btnAmiod = document.getElementById("btn-quick-amiodarone");
  if (btnAmiod) {
    btnAmiod.addEventListener("click", () => {
      quickFillIntervention("EMERGENCY_MEDICATION", "Anti-arrhythmic bolus administered", "Inj Amiodarone 300mg IV over 10 mins");
    });
  }
  const btnPocus = document.getElementById("btn-quick-pocus");
  if (btnPocus) {
    btnPocus.addEventListener("click", () => {
      quickFillIntervention("POCUS_EFAST", "eFAST scan completed: Negative pericardial effusion, no free fluid in Morrison pouch or spleno-renal angle", "None");
    });
  }
  const btnBolus = document.getElementById("btn-quick-bolus");
  if (btnBolus) {
    btnBolus.addEventListener("click", () => {
      quickFillIntervention("IV_FLUID_BOLUS", "1000ml Normal Saline wide open pressure bag infusion for volume resuscitation", "Inj Noradrenaline infusion initiated");
    });
  }

  // Triage Form Submission
  if (formTriage) {
    formTriage.addEventListener("submit", async (e) => {
      e.preventDefault();
      const patientSelect = document.getElementById("er-patient-select");
      const mpiId = patientSelect.value || (currentPatient ? currentPatient.mpi_id : null);
      if (!mpiId) {
        showToast("Please select or register an emergency patient first.", "error");
        return;
      }

      const allocatedBay = document.getElementById("er-allocated-bay").value || null;

      const payload = {
        mpi_id: mpiId,
        chief_complaint: document.getElementById("er-chief-complaint").value.trim(),
        triage_level: document.getElementById("er-triage-level").value,
        gcs_score: parseInt(document.getElementById("er-gcs").value, 10),
        systolic_bp: parseFloat(document.getElementById("er-bp-sys").value) || 120.0,
        diastolic_bp: parseFloat(document.getElementById("er-bp-dia").value) || 80.0,
        heart_rate: parseFloat(document.getElementById("er-hr").value) || 80.0,
        respiratory_rate: parseFloat(document.getElementById("er-rr").value) || 18.0,
        spo2: parseFloat(document.getElementById("er-spo2").value) || 98.0,
        temperature: parseFloat(document.getElementById("er-temp").value) || 98.6,
        pain_score: parseInt(document.getElementById("er-pain").value, 10) || 0,
        mode_of_arrival: document.getElementById("er-mode-arrival").value,
        triage_nurse_name: document.getElementById("er-triage-nurse").value.trim(),
        allocated_bay_id: allocatedBay || null
      };

      try {
        const res = await fetch("/api/v1/emergency/triage", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to complete emergency triage.");
        }
        const caseRecord = await res.json();
        showToast(`🚨 Triaged to ${caseRecord.allocated_bay_number}! Case: ${caseRecord.case_number}`, "success");
        formTriage.reset();
        document.getElementById("er-gcs").value = "15";
        document.getElementById("er-bp-sys").value = "120";
        document.getElementById("er-bp-dia").value = "80";
        document.getElementById("er-hr").value = "82";
        document.getElementById("er-rr").value = "18";
        document.getElementById("er-spo2").value = "98";
        document.getElementById("er-temp").value = "98.6";
        document.getElementById("er-pain").value = "0";

        await fetchEmergencyBays();
        await fetchActiveEmergencyCases();
        selectEmergencyCase(caseRecord.case_id);
        fetchHealthStatus();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // Resuscitation Intervention Form Submission
  if (formIntervention) {
    formIntervention.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!selectedEmergencyCaseId) {
        showToast("No active emergency case selected.", "error");
        return;
      }

      const payload = {
        case_id: selectedEmergencyCaseId,
        intervention_type: document.getElementById("er-interv-type").value.trim(),
        details: document.getElementById("er-interv-details").value.trim(),
        medications_given: document.getElementById("er-interv-meds").value.trim() || null,
        clinician_name: document.getElementById("er-interv-clinician").value.trim(),
        vitals_post: document.getElementById("er-interv-post-vitals").value.trim() || null
      };

      try {
        const res = await fetch("/api/v1/emergency/resuscitation/interventions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to record resuscitation intervention.");
        }
        const interv = await res.json();
        showToast(`⚡ Resuscitation recorded: ${interv.intervention_type} (+₹1,200.00 posted)`, "success");
        document.getElementById("er-interv-type").value = "";
        document.getElementById("er-interv-details").value = "";
        document.getElementById("er-interv-meds").value = "";
        document.getElementById("er-interv-post-vitals").value = "";

        selectEmergencyCase(selectedEmergencyCaseId);
        fetchHealthStatus();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // Disposition Decision Handler
  if (dispTypeSelect) {
    dispTypeSelect.addEventListener("change", (e) => {
      const groupBed = document.getElementById("group-er-target-bed");
      if (e.target.value === "ADMIT_TO_ICU" || e.target.value === "ADMIT_TO_IPD_WARD") {
        groupBed.style.display = "block";
        populateTargetBedOptions(e.target.value);
      } else {
        groupBed.style.display = "none";
      }
    });
  }

  // Disposition Form Submission
  if (formDisposition) {
    formDisposition.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!selectedEmergencyCaseId) {
        showToast("No active emergency case selected.", "error");
        return;
      }

      const dispType = document.getElementById("er-disp-type").value;
      const targetBed = document.getElementById("er-disp-target-bed").value || null;

      const payload = {
        case_id: selectedEmergencyCaseId,
        disposition_type: dispType,
        target_bed_id: targetBed,
        final_er_diagnosis: document.getElementById("er-disp-diagnosis").value.trim(),
        discharge_or_transfer_notes: document.getElementById("er-disp-notes").value.trim(),
        attending_er_physician: document.getElementById("er-disp-physician").value.trim(),
        physician_reg_no: document.getElementById("er-disp-reg").value.trim()
      };

      try {
        const res = await fetch("/api/v1/emergency/disposition", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to finalize disposition.");
        }
        const updatedCase = await res.json();
        showToast(`🏥 ER Disposition finalized: ${updatedCase.disposition}! ER Bay released.`, "success");
        formDisposition.reset();
        selectedEmergencyCaseId = null;

        await fetchEmergencyBays();
        await fetchActiveEmergencyCases();
        document.getElementById("er-active-case-banner").style.display = "none";
        document.getElementById("er-resus-console").style.display = "none";
        document.getElementById("er-disposition-console").style.display = "none";
        document.getElementById("er-no-case-placeholder").style.display = "block";

        fetchBedMatrix();
        fetchHealthStatus();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

function quickFillIntervention(type, details, meds) {
  document.getElementById("er-interv-type").value = type;
  document.getElementById("er-interv-details").value = details;
  document.getElementById("er-interv-meds").value = meds;
}

async function fetchEmergencyBays() {
  try {
    const res = await fetch("/api/v1/emergency/bays");
    if (!res.ok) return;
    currentEmergencyBays = await res.json();
    renderEmergencyBays();
    populateBayOptions();
  } catch (err) {
    console.error("Error fetching ER bays:", err);
  }
}

function renderEmergencyBays() {
  const container = document.getElementById("er-bays-container");
  if (!container) return;
  container.innerHTML = "";

  let availableCount = 0;

  currentEmergencyBays.forEach(bay => {
    const isAvail = bay.status === "AVAILABLE";
    if (isAvail) availableCount++;

    let cardClass = "bay-available";
    if (!isAvail) {
      if (bay.current_triage_level === "LEVEL_1_RED") cardClass = "bay-occupied-red";
      else if (bay.current_triage_level === "LEVEL_2_ORANGE") cardClass = "bay-occupied-orange";
      else if (bay.current_triage_level === "LEVEL_3_YELLOW") cardClass = "bay-occupied-yellow";
      else cardClass = "bay-occupied-green";
    }

    const card = document.createElement("div");
    card.className = `er-bay-card ${cardClass}`;
    if (selectedEmergencyCaseId && bay.current_case_id === selectedEmergencyCaseId) {
      card.classList.add("selected");
    }

    let triageBadgeHtml = "";
    if (bay.current_triage_level) {
      const lvl = bay.current_triage_level;
      if (lvl === "LEVEL_1_RED") triageBadgeHtml = `<span class="triage-badge-red">🔴 Resus (L1)</span>`;
      else if (lvl === "LEVEL_2_ORANGE") triageBadgeHtml = `<span class="triage-badge-orange">🟠 Emergent (L2)</span>`;
      else if (lvl === "LEVEL_3_YELLOW") triageBadgeHtml = `<span class="triage-badge-yellow">🟡 Urgent (L3)</span>`;
      else triageBadgeHtml = `<span class="triage-badge-green">🟢 Routine (L4)</span>`;
    }

    card.innerHTML = `
      <div class="er-bay-header">
        <span class="er-bay-number">${escapeHtml(bay.bay_number)}</span>
        <span class="er-bay-status-badge ${isAvail ? 'badge-success' : 'badge-danger'}">
          ${isAvail ? 'AVAILABLE' : 'OCCUPIED'}
        </span>
      </div>
      <div class="er-bay-type">${bay.bay_type.replace(/_/g, ' ')}</div>
      <div class="er-bay-patient">
        ${isAvail ? '<span style="color:#64748b; font-weight:normal; font-size:0.75rem;">Ready for Intake</span>' : `👤 ${escapeHtml(bay.current_patient_name || 'Emergency Patient')}`}
      </div>
      <div style="margin-top:0.4rem; display:flex; justify-content:space-between; align-items:center;">
        ${triageBadgeHtml}
        ${!isAvail && bay.current_case_id ? `<button class="btn btn-secondary btn-sm" style="font-size:0.7rem; padding:0.15rem 0.4rem;">Open Case →</button>` : ''}
      </div>
    `;

    card.addEventListener("click", () => {
      if (bay.current_case_id) {
        selectEmergencyCase(bay.current_case_id);
      } else {
        const baySelect = document.getElementById("er-allocated-bay");
        if (baySelect) baySelect.value = bay.bay_id;
        showToast(`Selected ${bay.bay_number} for upcoming triage intake.`, "info");
      }
    });

    container.appendChild(card);
  });

  const kpiBays = document.getElementById("er-kpi-available-bays");
  if (kpiBays) {
    kpiBays.textContent = `${availableCount} / ${currentEmergencyBays.length}`;
  }
}

function populateBayOptions() {
  const select = document.getElementById("er-allocated-bay");
  if (!select) return;
  const currentVal = select.value;
  select.innerHTML = `<option value="">Auto-Assign Best Bay</option>`;
  currentEmergencyBays.forEach(b => {
    if (b.status === "AVAILABLE") {
      const opt = document.createElement("option");
      opt.value = b.bay_id;
      opt.textContent = `${b.bay_number} (${b.bay_type.replace(/_/g, ' ')})`;
      select.appendChild(opt);
    }
  });
  if (currentVal) select.value = currentVal;
}

async function fetchActiveEmergencyCases() {
  try {
    const res = await fetch("/api/v1/emergency/cases/active");
    if (!res.ok) return;
    currentEmergencyCases = await res.json();

    const select = document.getElementById("er-active-cases-select");
    if (!select) return;

    select.innerHTML = currentEmergencyCases.length === 0
      ? `<option value="">-- No Active Cases --</option>`
      : `<option value="">-- Select Active ER Case (${currentEmergencyCases.length}) --</option>`;

    let codeRedCount = 0;

    currentEmergencyCases.forEach(c => {
      if (c.triage_level === "LEVEL_1_RED") codeRedCount++;
      const opt = document.createElement("option");
      opt.value = c.case_id;
      opt.textContent = `${c.case_number} - ${c.patient_name} (${c.allocated_bay_number})`;
      select.appendChild(opt);
    });

    if (selectedEmergencyCaseId) {
      select.value = selectedEmergencyCaseId;
    }

    const kpiActive = document.getElementById("er-kpi-active");
    if (kpiActive) kpiActive.textContent = currentEmergencyCases.length;

    const kpiRed = document.getElementById("er-kpi-code-red");
    if (kpiRed) kpiRed.textContent = codeRedCount;
  } catch (err) {
    console.error("Error fetching active ER cases:", err);
  }
}

async function selectEmergencyCase(caseId) {
  selectedEmergencyCaseId = caseId;
  const select = document.getElementById("er-active-cases-select");
  if (select) select.value = caseId;

  try {
    const res = await fetch(`/api/v1/emergency/cases/${caseId}`);
    if (!res.ok) return;
    const c = await res.json();

    document.getElementById("er-no-case-placeholder").style.display = "none";
    const banner = document.getElementById("er-active-case-banner");
    banner.style.display = "block";

    document.getElementById("er-banner-patient-name").textContent = c.patient_name;
    document.getElementById("er-banner-uhid").textContent = `UHID: ${c.patient_uhid}`;
    document.getElementById("er-banner-case-no").textContent = c.case_number;
    document.getElementById("er-banner-complaint").textContent = c.chief_complaint;
    document.getElementById("er-banner-bay").textContent = c.allocated_bay_number;
    document.getElementById("er-banner-vitals").textContent = `BP ${c.systolic_bp}/${c.diastolic_bp}, HR ${c.heart_rate}, SpO2 ${c.spo2}%, GCS ${c.gcs_score}`;
    document.getElementById("er-banner-arrived").textContent = new Date(c.arrived_at).toLocaleTimeString();
    document.getElementById("er-banner-charges").textContent = `₹${(c.total_er_charges || 0).toFixed(2)}`;

    // Triage badge
    const badgeContainer = document.getElementById("er-banner-triage-badge");
    if (c.triage_level === "LEVEL_1_RED") {
      badgeContainer.innerHTML = `<span class="triage-badge-red">🔴 Resuscitation (Level 1)</span>`;
    } else if (c.triage_level === "LEVEL_2_ORANGE") {
      badgeContainer.innerHTML = `<span class="triage-badge-orange">🟠 Emergent (Level 2)</span>`;
    } else if (c.triage_level === "LEVEL_3_YELLOW") {
      badgeContainer.innerHTML = `<span class="triage-badge-yellow">🟡 Urgent (Level 3)</span>`;
    } else {
      badgeContainer.innerHTML = `<span class="triage-badge-green">🟢 Less Urgent (Level 4/5)</span>`;
    }

    // Interventions timeline
    renderInterventionsTimeline(c.interventions || []);

    // Show consoles
    document.getElementById("er-resus-console").style.display = "block";
    document.getElementById("er-disposition-console").style.display = "block";

    populateTargetBedOptions(document.getElementById("er-disp-type").value);
    renderEmergencyBays();
  } catch (err) {
    console.error("Error selecting ER case:", err);
  }
}

function renderInterventionsTimeline(interventions) {
  const container = document.getElementById("er-interventions-timeline");
  if (!container) return;
  if (interventions.length === 0) {
    container.innerHTML = `<div style="font-size:0.8rem; color:#64748b; padding:0.5rem; text-align:center;">No resuscitation interventions logged yet for this case.</div>`;
    return;
  }

  container.innerHTML = "";
  interventions.forEach(item => {
    const el = document.createElement("div");
    el.className = "er-timeline-item";
    const timeStr = new Date(item.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.innerHTML = `
      <div class="timeline-item-header">
        <span class="timeline-item-type">⚡ ${escapeHtml(item.intervention_type)}</span>
        <span class="timeline-item-time">${timeStr} • ${escapeHtml(item.clinician_name)}</span>
      </div>
      <div>${escapeHtml(item.details)}</div>
      ${item.medications_given ? `<div style="color:#b91c1c; font-size:0.75rem; margin-top:0.2rem;"><strong>Meds:</strong> ${escapeHtml(item.medications_given)}</div>` : ''}
      ${item.vitals_post ? `<div style="color:#059669; font-size:0.75rem; margin-top:0.2rem;"><strong>Post-Vitals:</strong> ${escapeHtml(item.vitals_post)}</div>` : ''}
    `;
    container.appendChild(el);
  });
}

function populateTargetBedOptions(dispType) {
  const select = document.getElementById("er-disp-target-bed");
  if (!select) return;
  select.innerHTML = `<option value="">-- Auto-Assign Available Bed --</option>`;

  if (currentBeds && currentBeds.length > 0) {
    currentBeds.forEach(bed => {
      if (bed.status === "AVAILABLE") {
        if (dispType === "ADMIT_TO_ICU" && bed.ward_type === "ICU") {
          const opt = document.createElement("option");
          opt.value = bed.bed_id;
          opt.textContent = `🚨 ${bed.bed_number} (${bed.ward_name}) - ₹${bed.daily_rate}/day`;
          select.appendChild(opt);
        } else if (dispType === "ADMIT_TO_IPD_WARD" && bed.ward_type !== "ICU") {
          const opt = document.createElement("option");
          opt.value = bed.bed_id;
          opt.textContent = `🛏️ ${bed.bed_number} (${bed.ward_name}) - ₹${bed.daily_rate}/day`;
          select.appendChild(opt);
        }
      }
    });
  }
}

function populateEmergencyPatientSelect() {
  const select = document.getElementById("er-patient-select");
  if (!select) return;
  select.innerHTML = `<option value="">-- Select or Walk-in Emergency Patient --</option>`;

  if (currentPatient) {
    const opt = document.createElement("option");
    opt.value = currentPatient.mpi_id;
    opt.textContent = `⭐ ACTIVE: ${currentPatient.first_name} ${currentPatient.last_name} (${currentPatient.uhid})`;
    opt.selected = true;
    select.appendChild(opt);
  }

  fetch("/api/v1/patients/search?q=a")
    .then(r => r.ok ? r.json() : [])
    .then(list => {
      list.forEach(p => {
        if (!currentPatient || p.mpi_id !== currentPatient.mpi_id) {
          const opt = document.createElement("option");
          opt.value = p.mpi_id;
          opt.textContent = `${p.first_name} ${p.last_name} (${p.uhid || p.national_id_number || 'UHID Pending'})`;
          select.appendChild(opt);
        }
      });
    })
    .catch(() => {});
}

// =============================================================================
// PATIENT / CLIENT PORTAL & AI HEALTH COMPANION (Pod 9)
// =============================================================================

function initPatientPortalModule() {
  // Inner Sub-Tab Switching
  const portalTabBtns = document.querySelectorAll(".portal-tab-btn");
  portalTabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      portalTabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.ptab;
      document.querySelectorAll(".portal-tab-panel").forEach(p => p.classList.remove("active"));
      const targetPanel = document.getElementById(`ptab-${targetId}`);
      if (targetPanel) targetPanel.classList.add("active");
    });
  });

  // Patient Selector Switcher
  const patientSelect = document.getElementById("portal-patient-select");
  if (patientSelect) {
    patientSelect.addEventListener("change", (e) => {
      const mpiId = e.target.value;
      if (mpiId) {
        currentPortalMpiId = mpiId;
        loadPatientPortal(mpiId);
      }
    });
  }

  // Refresh Button
  const btnRefresh = document.getElementById("btn-refresh-portal");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      if (currentPortalMpiId) {
        loadPatientPortal(currentPortalMpiId);
      } else if (currentPatient) {
        loadPatientPortal(currentPatient.mpi_id);
      }
    });
  }

  // Print Summary Button
  const btnPrint = document.getElementById("btn-print-patient-summary");
  if (btnPrint) {
    btnPrint.addEventListener("click", () => {
      window.print();
    });
  }

  // AI Query Form Submission
  const formAI = document.getElementById("form-portal-ai-query");
  if (formAI) {
    formAI.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("portal-ai-query-input");
      const q = input.value.trim();
      if (!q) return;
      input.value = "";
      await handlePortalAIQuery(q);
    });
  }

  // Quick Chips
  const chips = document.querySelectorAll(".portal-chip-btn");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      const q = chip.dataset.q;
      if (q) {
        handlePortalAIQuery(q);
      }
    });
  });

  initWearablesModule();
  initClinicalNutritionListeners();
}

function populatePatientPortalSelect() {
  const select = document.getElementById("portal-patient-select");
  if (!select) return;
  select.innerHTML = `<option value="">-- Choose Registered Patient --</option>`;

  if (currentPatient) {
    const opt = document.createElement("option");
    opt.value = currentPatient.mpi_id;
    opt.textContent = `⭐ ACTIVE: ${currentPatient.first_name} ${currentPatient.last_name} (${currentPatient.uhid})`;
    opt.selected = true;
    currentPortalMpiId = currentPatient.mpi_id;
    select.appendChild(opt);
  }

  fetch("/api/v1/patients/search?q=a")
    .then(r => r.ok ? r.json() : [])
    .then(list => {
      list.forEach(p => {
        if (!currentPatient || p.mpi_id !== currentPatient.mpi_id) {
          const opt = document.createElement("option");
          opt.value = p.mpi_id;
          opt.textContent = `${p.first_name} ${p.last_name} (${p.uhid || 'UHID Pending'})`;
          if (!currentPortalMpiId) {
            currentPortalMpiId = p.mpi_id;
            opt.selected = true;
            loadPatientPortal(p.mpi_id);
          }
          select.appendChild(opt);
        }
      });
      if (currentPortalMpiId) {
        select.value = currentPortalMpiId;
      }
    })
    .catch(() => {});
}

async function loadPatientPortal(mpiId) {
  if (!mpiId) return;
  currentPortalMpiId = mpiId;

  try {
    const res = await fetch(`/api/v1/portal/patients/${mpiId}/summary`);
    if (!res.ok) {
      showToast("Unable to load patient portal summary.", "error");
      return;
    }
    const data = await res.json();
    currentPortalSummary = data;
    renderPatientPortal(data);
    loadPatientWearables(mpiId);
  } catch (err) {
    console.error("Error loading patient portal summary:", err);
  }
}

function renderPatientPortal(data) {
  // 1. Header Demographic Data
  const avatar = document.getElementById("portal-avatar");
  if (avatar) {
    const initials = data.full_name.split(" ").map(n => n[0]).slice(0, 2).join("").toUpperCase();
    avatar.textContent = initials || "PT";
  }

  document.getElementById("portal-patient-name").textContent = data.full_name;
  document.getElementById("portal-uhid").textContent = data.uhid;
  document.getElementById("portal-age-gender").textContent = `${data.age} Yrs / ${data.gender}`;
  document.getElementById("portal-phone").textContent = data.phone;
  document.getElementById("portal-last-visit").textContent = new Date(data.last_visit_date).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });

  // Badges
  const settingBadge = document.getElementById("portal-setting-badge");
  settingBadge.textContent = data.current_care_setting;
  if (data.current_care_setting.includes("Emergency")) {
    settingBadge.className = "badge badge-danger";
  } else if (data.current_care_setting.includes("Inpatient")) {
    settingBadge.className = "badge badge-warning";
  } else {
    settingBadge.className = "badge badge-success";
  }

  const abhaBadge = document.getElementById("portal-abha-badge");
  if (data.abha_id) {
    abhaBadge.textContent = `ABHA: ${data.abha_id}`;
    abhaBadge.className = "badge badge-info";
  } else {
    abhaBadge.textContent = "ABHA: Optional / Not Linked";
    abhaBadge.className = "badge badge-gray";
  }

  // 2. Vitals Ribbon
  const vitals = data.vital_trends_summary || {};
  document.getElementById("portal-v-bp").textContent = vitals.blood_pressure || "120/80 mmHg";
  document.getElementById("portal-v-hr").textContent = vitals.heart_rate || "76 bpm";
  document.getElementById("portal-v-spo2").textContent = vitals.oxygen_saturation || "99%";
  document.getElementById("portal-v-temp").textContent = vitals.body_temperature || "98.6 °F";
  document.getElementById("portal-v-status").textContent = vitals.status || "Stable & Monitored";

  // 3. Tab 1: Disease Profiles & AI Interpretations
  renderPortalDiseaseProfiles(data.disease_profiles);

  // 4. Tab 2: Lab & Scan Reports
  renderPortalLabReports(data.lab_and_scan_reports);

  // 5. Tab 3: Prescriptions & Medication Guide
  renderPortalMedications(data.active_prescriptions);

  // 6. Tab 4: Diet, Exercise & Recovery Roadmap
  renderPortalRecovery(data.ai_recommendations);

  // 7. Tab 5: Reset AI Assistant Welcome
  resetPortalAIChat(data);
}

function renderPortalDiseaseProfiles(profiles) {
  const container = document.getElementById("portal-disease-cards-container");
  if (!container) return;
  container.innerHTML = "";

  profiles.forEach(p => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-header">
        <div>
          <h4 style="margin:0; font-size:1.15rem; color:#0f766e;">${escapeHtml(p.condition_name)}</h4>
          <span style="font-size:0.8rem; color:#64748b;">ICD-10: <code>${p.icd10_code}</code> • Source: ${escapeHtml(p.source)}</span>
        </div>
        <div style="display:flex; gap:0.4rem; align-items:center;">
          <span class="badge ${p.severity_level === 'High Acuity' ? 'badge-danger' : 'badge-warning'}">
            ${p.severity_level} Acuity
          </span>
          <span class="badge badge-success">${p.status}</span>
        </div>
      </div>

      <div class="ai-insight-box">
        <div class="ai-insight-box-title">
          <span>💡</span> <strong>AI Clinical Translation for Patients:</strong>
        </div>
        <p>${escapeHtml(p.plain_english_summary)}</p>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:0.85rem; font-size:0.85rem;">
        <div style="background:#f8fafc; padding:0.75rem; border-radius:6px; border:1px solid #e2e8f0;">
          <strong style="color:#334155; display:block; margin-bottom:0.25rem;">🔍 Why this happens:</strong>
          <span style="color:#475569;">${escapeHtml(p.what_causes_it)}</span>
        </div>
        <div style="background:#f8fafc; padding:0.75rem; border-radius:6px; border:1px solid #e2e8f0;">
          <strong style="color:#334155; display:block; margin-bottom:0.25rem;">📈 What to expect next:</strong>
          <span style="color:#475569;">${escapeHtml(p.what_to_expect)}</span>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderPortalLabReports(reports) {
  const container = document.getElementById("portal-lab-reports-container");
  if (!container) return;
  container.innerHTML = "";

  if (reports.length === 0) {
    container.innerHTML = `<div class="card" style="text-align:center; padding:2rem; color:#64748b;">No diagnostic laboratory or imaging reports on file for this patient.</div>`;
    return;
  }

  reports.forEach(r => {
    const card = document.createElement("div");
    card.className = "card";

    let paramsHtml = "";
    if (r.parameters && r.parameters.length > 0) {
      paramsHtml = `
        <div style="margin-top:1rem; overflow-x:auto;">
          <table class="parsed-table">
            <thead>
              <tr>
                <th>Investigation Parameter</th>
                <th>Measured Value</th>
                <th>Reference Interval</th>
                <th>Status</th>
                <th>AI Insight</th>
              </tr>
            </thead>
            <tbody>
              ${r.parameters.map(p => `
                <tr>
                  <td><strong>${escapeHtml(p.parameter_name)}</strong></td>
                  <td style="font-weight:700; color:${p.status === 'CRITICAL' ? '#dc2626' : p.status === 'ELEVATED' ? '#b45309' : '#15803d'};">
                    ${p.measured_value} ${escapeHtml(p.unit)}
                  </td>
                  <td>${escapeHtml(p.reference_interval)}</td>
                  <td>
                    <span class="badge ${p.status === 'NORMAL' ? 'badge-success' : p.status === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}">
                      ${p.status}
                    </span>
                  </td>
                  <td style="font-size:0.75rem; color:#475569;">${escapeHtml(p.interpretation)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    let radiologyHtml = "";
    if (r.radiology_findings || r.radiology_impression) {
      radiologyHtml = `
        <div style="margin-top:1rem; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:0.85rem;">
          ${r.radiology_impression ? `<div><strong style="color:#0f766e;">Impression:</strong> ${escapeHtml(r.radiology_impression)}</div>` : ''}
          ${r.radiology_findings ? `<div style="margin-top:0.4rem; font-size:0.825rem; color:#475569;"><strong>Findings:</strong> ${escapeHtml(r.radiology_findings)}</div>` : ''}
          <div style="margin-top:0.4rem; font-size:0.75rem; color:#64748b;"><strong>Verified by:</strong> ${escapeHtml(r.radiologist_or_pathologist || 'Consultant Specialist')}</div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="card-header">
        <div>
          <h4 style="margin:0; color:#0f766e;">${escapeHtml(r.test_name)}</h4>
          <span style="font-size:0.8rem; color:#64748b;">
            Category: ${r.category} • Date: ${new Date(r.reported_at).toLocaleDateString()}
          </span>
        </div>
        <span class="badge ${r.has_critical_findings ? 'badge-danger' : r.is_abnormal ? 'badge-warning' : 'badge-success'}">
          ${r.status}
        </span>
      </div>

      <div class="ai-insight-box">
        <div class="ai-insight-box-title">
          <span>🧠</span> <strong>AI Clinical Takeaway:</strong>
        </div>
        <p>${escapeHtml(r.ai_clinical_takeaway)}</p>
      </div>

      <div style="font-size:0.85rem; color:#475569; margin-top:0.5rem;">
        <em>${escapeHtml(r.patient_plain_explanation)}</em>
      </div>

      ${paramsHtml}
      ${radiologyHtml}
    `;
    container.appendChild(card);
  });
}

function renderPortalMedications(medications) {
  const container = document.getElementById("portal-medications-container");
  if (!container) return;
  container.innerHTML = "";

  medications.forEach(m => {
    const card = document.createElement("div");
    card.className = "portal-med-card";

    // Interpret frequency pills
    const freq = m.frequency;
    let schedulePills = "";
    if (freq.includes("1-0-1")) {
      schedulePills = `
        <span class="schedule-pill pill-morning">🌅 Morning (8:00 AM)</span>
        <span class="schedule-pill pill-night">🌙 Night (8:00 PM)</span>
      `;
    } else if (freq.includes("1-0-0")) {
      schedulePills = `
        <span class="schedule-pill pill-morning">🌅 Morning (7:00 AM - 30m before breakfast)</span>
      `;
    } else if (freq.includes("0-0-1")) {
      schedulePills = `
        <span class="schedule-pill pill-night">🌙 Night (Bedtime)</span>
      `;
    } else {
      schedulePills = `
        <span class="schedule-pill pill-morning">🕒 Schedule: ${escapeHtml(freq)}</span>
      `;
    }

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem;">
        <div>
          <h4 style="margin:0; font-size:1.15rem; color:#0f766e;">💊 ${escapeHtml(m.drug_name)}</h4>
          <span style="font-size:0.8rem; color:#64748b;">
            Dosage: <strong>${escapeHtml(m.dosage)}</strong> • Duration: <strong>${escapeHtml(m.duration)}</strong> • Route: ${escapeHtml(m.route)}
          </span>
        </div>
        <span class="badge ${m.dispensed ? 'badge-success' : 'badge-warning'}">
          ${m.dispensed ? '✅ Dispensed from Pharmacy' : '⏳ Dispense Pending'}
        </span>
      </div>

      <div class="med-timing-grid">
        ${schedulePills}
      </div>

      <div class="ai-insight-box" style="margin-top:0.75rem;">
        <div class="ai-insight-box-title">
          <span>🎯</span> <strong>Why your doctor prescribed this:</strong>
        </div>
        <p>${escapeHtml(m.purpose_ai)}</p>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.85rem; margin-top:0.85rem; font-size:0.825rem;">
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:0.65rem 0.85rem;">
          <strong style="color:#15803d; display:block; margin-bottom:0.2rem;">🍽️ Food & Water Instructions:</strong>
          <span style="color:#166534;">${escapeHtml(m.food_instructions)}</span>
        </div>
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:0.65rem 0.85rem;">
          <strong style="color:#b45309; display:block; margin-bottom:0.2rem;">⚠️ Safety Precautions:</strong>
          <span style="color:#92400e;">${escapeHtml(m.key_precautions)}</span>
        </div>
      </div>

      ${m.side_effects_to_watch && m.side_effects_to_watch.length > 0 ? `
        <div style="margin-top:0.6rem; font-size:0.75rem; color:#64748b;">
          <strong>Potential mild effects to monitor:</strong> ${m.side_effects_to_watch.map(e => escapeHtml(e)).join(" • ")}
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });
}

function renderPortalRecovery(recs) {
  // Prognosis & Milestones
  document.getElementById("portal-prognosis-text").textContent = recs.prognosis_overview;
  document.getElementById("portal-recovery-timeline-badge").textContent = recs.estimated_recovery_timeline;

  const milestonesContainer = document.getElementById("portal-milestones-container");
  if (milestonesContainer) {
    milestonesContainer.innerHTML = "";
    (recs.prognosis_milestones || []).forEach(m => {
      const item = document.createElement("div");
      item.className = "milestone-item";
      item.innerHTML = `
        <div class="milestone-phase">${escapeHtml(m.phase)}</div>
        <div class="milestone-title">${escapeHtml(m.title)}</div>
        <ul style="margin:0; padding-left:1.15rem; font-size:0.825rem; color:#475569;">
          ${m.focus_points.map(p => `<li>${escapeHtml(p)}</li>`).join("")}
        </ul>
        <div class="milestone-mobility">🚶 Expected Mobility: ${escapeHtml(m.expected_mobility)}</div>
      `;
      milestonesContainer.appendChild(item);
    });
  }

  // Dietary Guidelines & PubMed Clinical Nutrition Engine
  if (recs.hydration_target) {
    const hydBadge = document.getElementById("portal-hydration-badge");
    if (hydBadge) hydBadge.textContent = `💧 Hydration: ${recs.hydration_target}`;
  }

  // Auto-select contextual condition based on patient diagnosis and load guideline
  const condSelect = document.getElementById("nutrition-condition-select");
  if (condSelect) {
    let matchedCond = "POST_OP_ORTHOPEDIC";
    const textToScan = (((recs.active_conditions || []).join(" ")) + " " + (recs.prognosis_overview || "")).toLowerCase();
    if (textToScan.includes("pcod") || textToScan.includes("pcos")) matchedCond = "PCOD_PCOS";
    else if (textToScan.includes("kidney") || textToScan.includes("ckd") || textToScan.includes("renal")) matchedCond = "KIDNEY_DISEASE_CKD";
    else if (textToScan.includes("diabet") || textToScan.includes("sugar")) matchedCond = "DIABETES_T2";
    else if (textToScan.includes("hyperten") || textToScan.includes("bp") || textToScan.includes("blood pressure")) matchedCond = "HYPERTENSION";
    else if (textToScan.includes("heart") || textToScan.includes("cad") || textToScan.includes("coronary")) matchedCond = "HEART_DISEASE_CAD";
    else if (textToScan.includes("weight") || textToScan.includes("obes")) matchedCond = "WEIGHT_REDUCTION";
    else if (textToScan.includes("geriatric") || textToScan.includes("elderly")) matchedCond = "POST_OP_GERIATRIC";
    
    condSelect.value = matchedCond;
    loadClinicalNutritionGuideline(matchedCond);
  }

  // Exercise Routine
  const exContainer = document.getElementById("portal-exercise-container");
  if (exContainer) {
    exContainer.innerHTML = "";
    (recs.exercise_routine || []).forEach(e => {
      const item = document.createElement("div");
      item.className = "exercise-item";
      item.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
          <strong style="color:#1e40af; font-size:0.9rem;">🏋️ ${escapeHtml(e.exercise_name)}</strong>
          <span class="badge badge-info">${escapeHtml(e.repetitions_and_sets)}</span>
        </div>
        <div style="font-size:0.775rem; color:#64748b; margin-bottom:0.35rem;">Target: ${escapeHtml(e.target_muscle_or_joint)}</div>
        <p style="margin:0; color:#334155; font-size:0.825rem;">${escapeHtml(e.instructions)}</p>
        <div style="margin-top:0.35rem; font-size:0.75rem; color:#0369a1;"><strong>Safety Tip:</strong> ${escapeHtml(e.safety_precaution)}</div>
      `;
      exContainer.appendChild(item);
    });
  }

  // Restrictions
  const restList = document.getElementById("portal-restrictions-list");
  if (restList) {
    restList.innerHTML = (recs.strict_activity_restrictions || []).map(r => `<li style="margin-bottom:0.25rem;">${escapeHtml(r)}</li>`).join("");
  }

  // Red Flags
  const redFlagsContainer = document.getElementById("portal-redflags-container");
  if (redFlagsContainer) {
    redFlagsContainer.innerHTML = (recs.red_flag_warning_signs || []).map(r => `
      <div class="red-flag-item">
        <strong>${escapeHtml(r)}</strong>
      </div>
    `).join("");
  }

  // Follow-up
  const followUpEl = document.getElementById("portal-followup-advice");
  if (followUpEl) {
    followUpEl.textContent = recs.next_follow_up_advice || "Follow-up review as recommended by physician.";
  }
}

function resetPortalAIChat(data) {
  const container = document.getElementById("portal-chat-messages");
  if (!container) return;
  const condNames = (data.disease_profiles || []).map(p => p.condition_name).join(", ");
  container.innerHTML = `
    <div class="chat-msg chat-ai">
      <div class="chat-avatar">🤖</div>
      <div class="chat-bubble">
        <p>Hello <strong>${escapeHtml(data.full_name)}</strong>! I am your AI Health Companion. I have active visibility of your health profile${condNames ? ` for <em>${escapeHtml(condNames)}</em>` : ''}, your prescriptions, and your diagnostic scans. Feel free to ask any question about your medications, morning knee stiffness, safe exercises, or diet!</p>
        <small class="text-muted" style="display:block; margin-top:0.35rem; font-size:0.75rem;">
          ℹ️ Grounded in your physician's clinical notes • Educational guidance
        </small>
      </div>
    </div>
  `;
}

async function handlePortalAIQuery(question) {
  if (!currentPortalMpiId) {
    showToast("Please select a patient first.", "error");
    return;
  }

  const container = document.getElementById("portal-chat-messages");

  // User Message
  const userMsg = document.createElement("div");
  userMsg.className = "chat-msg chat-user";
  userMsg.innerHTML = `
    <div class="chat-avatar">👤</div>
    <div class="chat-bubble">
      <p>${escapeHtml(question)}</p>
    </div>
  `;
  container.appendChild(userMsg);
  container.scrollTop = container.scrollHeight;

  // AI Loading Bubble
  const aiLoading = document.createElement("div");
  aiLoading.className = "chat-msg chat-ai";
  aiLoading.id = "ai-loading-bubble";
  aiLoading.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble">
      <p><em>Consulting your longitudinal health record and pharmacological rules...</em></p>
    </div>
  `;
  container.appendChild(aiLoading);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch("/api/v1/portal/ai-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mpi_id: currentPortalMpiId,
        question: question
      })
    });
    aiLoading.remove();
    if (!res.ok) {
      throw new Error("Unable to process query.");
    }
    const data = await res.json();

    const aiMsg = document.createElement("div");
    aiMsg.className = "chat-msg chat-ai";
    aiMsg.innerHTML = `
      <div class="chat-avatar">🤖</div>
      <div class="chat-bubble">
        <p>${escapeHtml(data.answer)}</p>
        <small class="text-muted" style="display:block; margin-top:0.5rem; font-size:0.725rem; border-top:1px solid #e2e8f0; padding-top:0.35rem;">
          ${escapeHtml(data.safety_disclaimer)}
        </small>
      </div>
    `;
    container.appendChild(aiMsg);
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    if (aiLoading) aiLoading.remove();
    const errMsg = document.createElement("div");
    errMsg.className = "chat-msg chat-ai";
    errMsg.innerHTML = `
      <div class="chat-avatar">🤖</div>
      <div class="chat-bubble" style="background:#fef2f2; color:#991b1b;">
        <p>Sorry, I encountered an issue retrieving the clinical answer. Please try again or speak directly with your nursing/medical team.</p>
      </div>
    `;
    container.appendChild(errMsg);
    container.scrollTop = container.scrollHeight;
  }
}

// =============================================================================
// 10. WEARABLES, SLEEP, NEURO-CAP (40HZ) & GYM STRENGTH MODULE (Pod 10)
// =============================================================================
let currentWearablesDashboard = null;
let isDeloadRecoveryTest = false;
let simulatedStepsOverride = null;

function initWearablesModule() {
  // 1. Sync All Wearables Button
  const btnSync = document.getElementById("btn-sync-wearables");
  if (btnSync) {
    btnSync.addEventListener("click", async () => {
      if (!currentPortalMpiId) {
        showToast("Please select a patient first.", "error");
        return;
      }
      simulatedStepsOverride = null;
      isDeloadRecoveryTest = false;
      await loadPatientWearables(currentPortalMpiId);
      showToast("All wearable telemetry synchronized from WHOOP, 40Hz Cap & HealthKit.", "success");
    });
  }

  // 2. Simulate Step Hike Button (+1,000 steps to trigger post-op safety ceiling)
  const btnStepHike = document.getElementById("btn-wearable-step-hike");
  if (btnStepHike) {
    btnStepHike.addEventListener("click", async () => {
      if (!currentPortalMpiId) return;
      simulatedStepsOverride = (simulatedStepsOverride || 2150) + 1000;
      await loadPatientWearables(currentPortalMpiId, simulatedStepsOverride, isDeloadRecoveryTest ? 28 : null);
      if (simulatedStepsOverride > 3000) {
        showToast("🚨 SURGICAL CEILING ALERT: Step volume exceeded 3,000 steps!", "error");
      } else {
        showToast(`Simulated step volume updated to ${simulatedStepsOverride.toLocaleString()} steps.`, "info");
      }
    });
  }

  // 3. Toggle Red Recovery Test (Deload test)
  const btnToggleRecovery = document.getElementById("btn-wearable-toggle-recovery");
  if (btnToggleRecovery) {
    btnToggleRecovery.addEventListener("click", async () => {
      if (!currentPortalMpiId) return;
      isDeloadRecoveryTest = !isDeloadRecoveryTest;
      const recVal = isDeloadRecoveryTest ? 28 : 82;
      btnToggleRecovery.textContent = isDeloadRecoveryTest ? "🟢 Restore Green Recovery (82%)" : "🔴 Toggle Red Recovery (Deload Test)";
      btnToggleRecovery.style.borderColor = isDeloadRecoveryTest ? "#16a34a" : "#ef4444";
      btnToggleRecovery.style.color = isDeloadRecoveryTest ? "#16a34a" : "#dc2626";

      await loadPatientWearables(currentPortalMpiId, simulatedStepsOverride, recVal);
      if (isDeloadRecoveryTest) {
        showToast("WHOOP Recovery set to 28% RED: Gym strength training dynamically withheld!", "error");
      } else {
        showToast("WHOOP Recovery restored to 82% GREEN: Cleared for Phase 2 gym training.", "success");
      }
    });
  }

  // 4. Trigger 40Hz Gamma Session Button
  const btnGamma = document.getElementById("btn-trigger-gamma-session");
  if (btnGamma) {
    btnGamma.addEventListener("click", async () => {
      if (!currentPortalMpiId) return;
      try {
        btnGamma.disabled = true;
        btnGamma.textContent = "🎧 Entraining 40Hz Audio-Visual Stimulation...";
        const res = await fetch("/api/v1/portal/wearables/log-gamma", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mpi_id: currentPortalMpiId,
            duration_minutes: 45,
            protocol: "Post-Op Neuro-Analgesia & Circadian Deep Sleep Alignment"
          })
        });
        if (res.ok) {
          showToast("45-min 40Hz Gamma Neuromodulation completed! Cortical coherence 84%.", "success");
          await loadPatientWearables(currentPortalMpiId, simulatedStepsOverride, isDeloadRecoveryTest ? 28 : null);
        }
      } catch (err) {
        showToast("Gamma session connection error.", "error");
      } finally {
        btnGamma.disabled = false;
        btnGamma.textContent = "🎧 Run 45-min 40Hz Gamma Session";
      }
    });
  }

  // 5. Gym Workout Logger Form Submission
  const formWorkout = document.getElementById("gym-workout-log-form");
  if (formWorkout) {
    formWorkout.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!currentPortalMpiId) {
        showToast("Please select a patient first.", "error");
        return;
      }
      const exName = document.getElementById("log-ex-name").value;
      const sets = parseInt(document.getElementById("log-ex-sets").value, 10);
      const reps = parseInt(document.getElementById("log-ex-reps").value, 10);
      const weight = parseFloat(document.getElementById("log-ex-weight").value);
      const rpe = parseInt(document.getElementById("log-ex-rpe").value, 10);

      const exercises = [{
        name: exName,
        sets: sets,
        reps: reps,
        weight_kg: weight,
        target_rom_degrees: "0° to 70° flexion",
        actual_rom_degrees: "0° to 65°",
        rpe: rpe,
        tempo: "3-1-2-0 (Controlled eccentric)",
        safety_compliance: true
      }];

      try {
        const res = await fetch("/api/v1/portal/wearables/log-workout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mpi_id: currentPortalMpiId,
            workout_name: `Phase 2 Strength - ${exName}`,
            exercises: exercises,
            duration_minutes: 35,
            strain_generated: 8.4
          })
        });
        if (res.ok) {
          showToast(`Recorded strength telemetry: ${sets}x${reps} @ ${weight}kg (ROM within 70°).`, "success");
          await loadPatientWearables(currentPortalMpiId, simulatedStepsOverride, isDeloadRecoveryTest ? 28 : null);
        } else {
          showToast("Failed to record workout.", "error");
        }
      } catch (err) {
        showToast("Error recording workout telemetry.", "error");
      }
    });
  }
}

async function loadPatientWearables(mpiId, stepOverride = null, recoveryOverride = null) {
  if (!mpiId) return;

  try {
    let res;
    if (stepOverride !== null || recoveryOverride !== null) {
      res = await fetch(`/api/v1/portal/patients/${mpiId}/wearables/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mpi_id: mpiId,
          step_override: stepOverride,
          whoop_recovery_override: recoveryOverride
        })
      });
    } else {
      res = await fetch(`/api/v1/portal/patients/${mpiId}/wearables`);
    }

    if (!res.ok) return;
    const data = await res.json();
    currentWearablesDashboard = data;
    renderWearablesDashboard(data);
  } catch (err) {
    console.error("Error loading wearable dashboard:", err);
  }
}

function renderWearablesDashboard(data) {
  const steps = data.step_telemetry;
  const whoop = data.whoop_telemetry;
  const gamma = data.gamma_40hz_telemetry;
  const rec = data.adaptive_gym_recommendations;

  // 1. Clinical Safety Alerts Container
  const alertsContainer = document.getElementById("wearable-alerts-container");
  if (alertsContainer) {
    if (data.clinical_safety_alerts && data.clinical_safety_alerts.length > 0) {
      alertsContainer.innerHTML = data.clinical_safety_alerts.map(a => `
        <div style="background:#fef2f2; border:1.5px solid #f87171; border-radius:8px; padding:0.85rem 1.25rem; margin-bottom:0.75rem; display:flex; align-items:flex-start; gap:0.75rem;">
          <span style="font-size:1.4rem;">🚨</span>
          <div>
            <strong style="color:#991b1b; display:block; font-size:0.9rem;">Orthopedic Clinical Biometric Alert:</strong>
            <p style="margin:0.25rem 0 0 0; font-size:0.85rem; color:#7f1d1d;">${escapeHtml(a)}</p>
          </div>
        </div>
      `).join("");
    } else {
      alertsContainer.innerHTML = "";
    }
  }

  // 2. Step Pacing & Ceiling
  if (steps) {
    document.getElementById("wearable-steps-count").textContent = steps.daily_steps.toLocaleString();
    document.getElementById("wearable-steps-target").textContent = `/ ${steps.post_op_step_target.toLocaleString()} target (Max ${steps.post_op_step_ceiling.toLocaleString()})`;

    const bar = document.getElementById("wearable-step-bar");
    const pct = Math.min(100, Math.round((steps.daily_steps / steps.post_op_step_ceiling) * 100));
    bar.style.width = `${pct}%`;

    const badge = document.getElementById("wearable-step-badge");
    if (steps.ceiling_exceeded) {
      bar.style.background = "#ef4444";
      badge.textContent = "🚨 Ceiling Exceeded";
      badge.className = "badge badge-danger";
    } else if (steps.daily_steps > steps.post_op_step_target) {
      bar.style.background = "#f59e0b";
      badge.textContent = "Target Reached (Rest Knee)";
      badge.className = "badge badge-warning";
    } else {
      bar.style.background = "#0d9488";
      badge.textContent = "Safe Volume";
      badge.className = "badge badge-success";
    }

    document.getElementById("wearable-gait-sym").textContent = steps.gait_weight_bearing_symmetry_pct;
    document.getElementById("wearable-distance").textContent = `${steps.distance_km} km`;
  }

  // 3. WHOOP Telemetry
  if (whoop) {
    document.getElementById("wearable-recovery-score").textContent = whoop.recovery_score;
    const badgeRec = document.getElementById("wearable-recovery-badge");
    const statePill = document.getElementById("wearable-whoop-state");

    if (whoop.recovery_state === "GREEN") {
      badgeRec.style.borderColor = "#16a34a";
      badgeRec.style.color = "#16a34a";
      badgeRec.style.background = "#f0fdf4";
      statePill.textContent = `Green (${whoop.recovery_score}%)`;
      statePill.className = "badge badge-success";
    } else if (whoop.recovery_state === "YELLOW") {
      badgeRec.style.borderColor = "#ca8a04";
      badgeRec.style.color = "#ca8a04";
      badgeRec.style.background = "#fefce8";
      statePill.textContent = `Yellow (${whoop.recovery_score}%)`;
      statePill.className = "badge badge-warning";
    } else {
      badgeRec.style.borderColor = "#dc2626";
      badgeRec.style.color = "#dc2626";
      badgeRec.style.background = "#fef2f2";
      statePill.textContent = `Red (${whoop.recovery_score}%)`;
      statePill.className = "badge badge-danger";
    }

    document.getElementById("wearable-hrv").textContent = `${whoop.hrv_ms} ms`;
    document.getElementById("wearable-rhr").textContent = `${whoop.resting_heart_rate_bpm} bpm`;
    document.getElementById("wearable-strain").textContent = `${whoop.day_strain} / 21.0`;
    document.getElementById("wearable-skin-temp").textContent = `${whoop.skin_temp_delta_celsius > 0 ? '+' : ''}${whoop.skin_temp_delta_celsius} °C`;

    // Sleep
    document.getElementById("wearable-sleep-total").textContent = `${whoop.sleep_hours_total} hrs`;
    document.getElementById("wearable-sleep-perf").textContent = `${whoop.sleep_performance_pct}% Perf`;
    document.getElementById("wearable-deep-sleep").textContent = `${whoop.deep_sleep_minutes} min`;
    document.getElementById("wearable-rem-sleep").textContent = `${whoop.rem_sleep_minutes} min`;
  }

  // 4. 40Hz Gamma Cap Telemetry
  if (gamma) {
    document.getElementById("wearable-gamma-freq").textContent = `${gamma.frequency_hz} Hz`;
    document.getElementById("wearable-gamma-status").textContent = `${gamma.status} (${gamma.session_duration_minutes}m)`;
    document.getElementById("wearable-gamma-coherence").textContent = `${gamma.cortical_entrainment_coherence_pct}% Phase-Locking Value`;
    document.getElementById("wearable-gamma-pain").textContent = gamma.subjective_pain_reduction;
  }

  // 5. Hardware Devices List
  const devicesList = document.getElementById("wearable-devices-list");
  if (devicesList && data.connected_devices) {
    const iconMap = {
      "WHOOP_4": "⌚",
      "GAMMA_40HZ_CAP": "🧠",
      "SMART_PEDOMETER": "🚶",
      "GYM_STRENGTH_TRACKER": "🏋️",
      "APPLE_HEALTH": "🍎",
      "OURA_RING": "💍"
    };
    devicesList.innerHTML = data.connected_devices.map(dev => `
      <div class="wearable-device-card">
        <div class="device-icon-box">${iconMap[dev.device_type] || "🔌"}</div>
        <div style="flex:1;">
          <div style="font-weight:700; font-size:0.85rem; color:#0f172a;">${escapeHtml(dev.device_name)}</div>
          <div style="font-size:0.75rem; color:#64748b; display:flex; align-items:center; gap:0.5rem; margin-top:0.2rem;">
            <span><span class="device-status-dot ${dev.status === 'CONNECTED' ? 'dot-connected' : 'dot-disconnected'}"></span>${dev.status}</span>
            <span>• Battery: ${dev.battery_level_pct}%</span>
            <span>• ${dev.firmware_version}</span>
          </div>
        </div>
      </div>
    `).join("");
  }

  // 6. Adaptive Gym Recommendations
  if (rec) {
    const banner = document.getElementById("gym-readiness-banner");
    const pill = document.getElementById("gym-readiness-pill");

    if (rec.readiness_status === "CLEARED_FOR_STRENGTH_TRAINING") {
      banner.textContent = `🟢 CLEARED FOR PHASE 2 GYM STRENGTH TRAINING (Readiness Score: ${rec.training_readiness_score}/100 | Target Strain: ${rec.target_day_strain_range})`;
      banner.style.color = "#0f766e";
      pill.textContent = "Cleared";
      pill.className = "badge badge-success";
    } else if (rec.readiness_status === "MODIFIED_LOW_INTENSITY") {
      banner.textContent = `🟡 MODIFIED LOW-INTENSITY GYM WORKOUT ONLY (Readiness Score: ${rec.training_readiness_score}/100 | Target Strain: ${rec.target_day_strain_range})`;
      banner.style.color = "#b45309";
      pill.textContent = "Modified Only";
      pill.className = "badge badge-warning";
    } else {
      banner.textContent = `🔴 DELOAD / REST DAY: STRENGTH TRAINING CONTRAINDICATED (Readiness Score: ${rec.training_readiness_score}/100)`;
      banner.style.color = "#b91c1c";
      pill.textContent = "Rest & Deload";
      pill.className = "badge badge-danger";
    }

    document.getElementById("gym-whoop-influence").textContent = rec.whoop_recovery_influence;
    document.getElementById("gym-gamma-influence").textContent = rec.gamma_neuro_pacing_influence;
    document.getElementById("gym-pacing-influence").textContent = rec.cardio_and_step_pacing;
    document.getElementById("gym-post-workout-protocol").textContent = rec.post_workout_protocol;

    // Prescribed Gym Movements
    const presContainer = document.getElementById("prescribed-gym-container");
    if (presContainer && rec.recommended_gym_movements) {
      presContainer.innerHTML = rec.recommended_gym_movements.map(m => `
        <div class="gym-prescribed-card">
          <div class="gym-prescribed-title">
            <span>${escapeHtml(m.name)}</span>
            <span class="badge badge-success" style="font-size:0.65rem;">Approved</span>
          </div>
          <div style="margin-bottom:0.25rem;">
            <span class="gym-tag gym-tag-sets">${escapeHtml(m.recommended_sets_and_reps)}</span>
            <span class="gym-tag gym-tag-rom">${escapeHtml(m.rom_limit)}</span>
          </div>
          <div style="font-size:0.75rem; color:#475569; margin-top:0.25rem;">
            <strong>Target:</strong> ${escapeHtml(m.target_muscle_group)} • <strong>Tempo:</strong> ${escapeHtml(m.tempo)}
          </div>
          <div style="font-size:0.75rem; color:#15803d; margin-top:0.25rem;">
            <em>Rationale: ${escapeHtml(m.biomechanical_rationale)}</em>
          </div>
        </div>
      `).join("");
    }

    // Prohibited Movements
    const prohibContainer = document.getElementById("prohibited-gym-container");
    if (prohibContainer && rec.contraindicated_gym_movements) {
      prohibContainer.innerHTML = rec.contraindicated_gym_movements.map(p => `
        <div class="gym-prohibited-card">
          <div class="gym-prohibited-title">
            <span>🚫 ${escapeHtml(p.name)}</span>
            <span class="badge badge-danger" style="font-size:0.65rem;">Forbidden</span>
          </div>
          <div style="font-size:0.75rem; color:#991b1b; margin-top:0.25rem;">
            <strong>Danger Mechanism:</strong> ${escapeHtml(p.danger_risk)}
          </div>
          <div style="font-size:0.75rem; color:#1e40af; margin-top:0.35rem; background:#eff6ff; padding:0.25rem 0.5rem; border-radius:3px;">
            <strong>Safe Alternative:</strong> ${escapeHtml(p.safe_alternative)}
          </div>
        </div>
      `).join("");
    }
  }

  // 7. Recent Gym Workouts
  const workoutsContainer = document.getElementById("gym-workouts-history-container");
  if (workoutsContainer && data.recent_gym_workouts) {
    if (data.recent_gym_workouts.length === 0) {
      workoutsContainer.innerHTML = `<p class="text-muted" style="font-size:0.8rem;">No workouts logged yet. Use the form above to record your session.</p>`;
    } else {
      workoutsContainer.innerHTML = data.recent_gym_workouts.map(w => `
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:0.75rem 1rem; margin-bottom:0.5rem;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#0f172a; font-size:0.85rem;">${escapeHtml(w.workout_name)}</strong>
            <span style="font-size:0.75rem; color:#64748b;">${new Date(w.workout_timestamp).toLocaleDateString([], { month:'short', day:'numeric' })} • ${w.duration_minutes} min • Total Volume: ${w.total_volume_kg.toLocaleString()} kg • Strain: ${w.strain_generated}</span>
          </div>
          <div style="margin-top:0.4rem; display:flex; flex-wrap:wrap; gap:0.4rem;">
            ${w.exercises.map(ex => `
              <span style="background:#ffffff; border:1px solid #cbd5e1; font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px;">
                ${escapeHtml(ex.name)}: ${ex.sets}x${ex.reps} @ ${ex.weight_kg}kg (RPE ${ex.rpe})
              </span>
            `).join("")}
          </div>
          <div style="font-size:0.75rem; color:#0f766e; margin-top:0.35rem;">
            💡 <em>${escapeHtml(w.ai_post_workout_feedback)}</em>
          </div>
        </div>
      `).join("");
    }
  }
}

// -------------------------------------------------------------
// Clinical Nutrition RAG & PubMed Guidelines Engine
// -------------------------------------------------------------
async function loadClinicalNutritionGuideline(conditionKey) {
  try {
    const res = await fetch(`/api/v1/nutrition/guidelines/${encodeURIComponent(conditionKey)}`);
    if (!res.ok) throw new Error("Failed to load nutrition guideline");
    const data = await res.json();
    renderClinicalNutritionGuideline(data);
  } catch (err) {
    console.error("Error loading nutrition guideline:", err);
  }
}

function renderClinicalNutritionGuideline(g) {
  if (!g) return;

  // Active Title & Indication
  const titleEl = document.getElementById("nutrition-active-title");
  if (titleEl) titleEl.textContent = g.condition_name;

  const appEl = document.getElementById("nutrition-active-applicability");
  if (appEl) {
    const context = g.surgical_case_type ? ` • ${g.surgical_case_type}` : "";
    appEl.textContent = `${g.age_applicability}${context}`;
  }

  const summaryEl = document.getElementById("nutrition-active-summary");
  if (summaryEl) summaryEl.textContent = g.clinical_summary;

  const badgeEl = document.getElementById("nutrition-evidence-level-badge");
  if (badgeEl && g.pubmed_citations && g.pubmed_citations.length > 0) {
    badgeEl.textContent = g.pubmed_citations[0].evidence_level || "Level 1A: International Practice Guideline";
  }

  // Citations Container with direct PubMed links
  const citContainer = document.getElementById("nutrition-citations-container");
  if (citContainer && g.pubmed_citations) {
    citContainer.innerHTML = `
      <div style="font-weight:700; color:#0369a1; margin-bottom:0.35rem; display:flex; align-items:center; gap:0.35rem;">
        <span>📚</span> Peer-Reviewed PubMed Indexed Literature:
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
        ${g.pubmed_citations.map(c => `
          <a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer" class="pubmed-badge-link" title="${escapeHtml(c.title)}">
            <span>📄</span> <strong>${escapeHtml(c.journal)}</strong> (${c.year}) • PMID: ${escapeHtml(c.pmid)} ↗
          </a>
        `).join("")}
      </div>
    `;
  }

  // Macronutrient Targets Ribbon
  const ribbon = document.getElementById("nutrition-macro-ribbon");
  if (ribbon && g.macro_targets) {
    const m = g.macro_targets;
    ribbon.innerHTML = `
      <div class="nutrition-macro-card">
        <span class="macro-label">⚡ Daily Calories</span>
        <span class="macro-value" style="color:#d97706;">${escapeHtml(m.daily_calories_guideline)}</span>
      </div>
      <div class="nutrition-macro-card">
        <span class="macro-label">🥩 Protein Target</span>
        <span class="macro-value" style="color:#0f766e;">${escapeHtml(m.protein_g_per_kg)}</span>
      </div>
      <div class="nutrition-macro-card">
        <span class="macro-label">🌾 Carbs & Fiber</span>
        <span class="macro-value" style="color:#2563eb;">${escapeHtml(m.carbohydrate_pct)}<br><span style="font-size:0.75rem; color:#475569;">Fiber: ${escapeHtml(m.dietary_fiber_g)}</span></span>
      </div>
      <div class="nutrition-macro-card">
        <span class="macro-label">🥑 Healthy Fats</span>
        <span class="macro-value" style="color:#16a34a;">${escapeHtml(m.fat_pct)}</span>
      </div>
      <div class="nutrition-macro-card">
        <span class="macro-label">🧂 Sodium Limit</span>
        <span class="macro-value" style="color:#b91c1c;">${escapeHtml(m.sodium_limit_mg)}</span>
      </div>
      <div class="nutrition-macro-card">
        <span class="macro-label">💧 Fluid Pacing</span>
        <span class="macro-value" style="color:#0284c7;">${escapeHtml(m.fluid_target)}</span>
      </div>
    `;
  }

  // Superfoods
  const superContainer = document.getElementById("nutrition-superfoods-container");
  if (superContainer && g.recommended_foods) {
    superContainer.innerHTML = g.recommended_foods.map(f => `
      <div class="diet-item beneficial">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.2rem;">
          <strong style="color:#166534;">✅ ${escapeHtml(f.food_item)}</strong>
          <span style="font-size:0.7rem; font-weight:700; color:#15803d; text-transform:uppercase;">Superfood</span>
        </div>
        <p style="margin:0; font-size:0.8rem; color:#334155;">${escapeHtml(f.clinical_rationale)}</p>
        <div class="biochemical-mech-tag"><strong>Biochemical Mechanism:</strong> ${escapeHtml(f.biochemical_mechanism)}</div>
      </div>
    `).join("");
  }

  // Prohibited Foods
  const prohibContainer = document.getElementById("nutrition-prohibited-container");
  if (prohibContainer && g.prohibited_foods) {
    prohibContainer.innerHTML = g.prohibited_foods.map(p => `
      <div class="diet-item avoid">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.2rem;">
          <strong style="color:#991b1b;">🚫 ${escapeHtml(p.food_item)}</strong>
          <span style="font-size:0.7rem; font-weight:700; color:#b91c1c; text-transform:uppercase;">Contraindicated</span>
        </div>
        <p style="margin:0; font-size:0.8rem; color:#334155;">${escapeHtml(p.clinical_rationale)}</p>
        <div class="biochemical-mech-tag" style="border-left-color:#ef4444; color:#991b1b;"><strong>Contraindication Mechanism:</strong> ${escapeHtml(p.biochemical_mechanism)}</div>
      </div>
    `).join("");
  }

  // Chrononutrition & Meal Timing
  const chronoEl = document.getElementById("nutrition-chrononutrition-text");
  if (chronoEl) chronoEl.textContent = g.meal_timing_and_chrononutrition;
}

function initClinicalNutritionListeners() {
  const select = document.getElementById("nutrition-condition-select");
  if (select) {
    select.addEventListener("change", (e) => {
      loadClinicalNutritionGuideline(e.target.value);
    });
  }

  const btnAsk = document.getElementById("btn-nutrition-rag-ask");
  const inputAsk = document.getElementById("nutrition-rag-input");
  const resultBox = document.getElementById("nutrition-rag-result");

  const handleAsk = async () => {
    const query = (inputAsk?.value || "").trim();
    if (!query) {
      showToast("Please enter a question for the Nutrition RAG engine.", "info");
      return;
    }
    if (btnAsk) {
      btnAsk.disabled = true;
      btnAsk.textContent = "Querying PubMed...";
    }
    try {
      const res = await fetch("/api/v1/nutrition/rag-query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (!res.ok) throw new Error("RAG query failed");
      const data = await res.json();
      if (resultBox) {
        resultBox.classList.remove("hidden");
        let citationsHtml = "";
        if (data.relevant_citations && data.relevant_citations.length > 0) {
          citationsHtml = `\n\n📚 Grounded Evidence Citations:\n` + data.relevant_citations.map(c => `• ${c.journal} (${c.year}, PMID: ${c.pmid}): ${c.title}`).join("\n");
        }
        resultBox.textContent = data.grounded_answer + citationsHtml;
      }
    } catch (err) {
      if (resultBox) {
        resultBox.classList.remove("hidden");
        resultBox.textContent = "Could not fetch RAG response. Please try again.";
      }
    } finally {
      if (btnAsk) {
        btnAsk.disabled = false;
        btnAsk.textContent = "Search PubMed";
      }
    }
  };

  if (btnAsk) {
    btnAsk.addEventListener("click", handleAsk);
  }
  if (inputAsk) {
    inputAsk.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAsk();
      }
    });
  }

  // Initial load
  loadClinicalNutritionGuideline("POST_OP_ORTHOPEDIC");
}

// =============================================================================
// HOSPITAL SERIAL STEPPER & SERIAL NAVIGATION
// =============================================================================
function initHospitalStepperAndSerialNav() {
  // Stepper step clicks
  document.querySelectorAll(".stepper-step").forEach(step => {
    step.addEventListener("click", () => {
      const target = step.dataset.step;
      if (target) switchHospitalTab(target);
    });
  });

  // Next buttons
  document.querySelectorAll(".btn-serial-next").forEach(btn => {
    btn.addEventListener("click", () => {
      const next = btn.dataset.next;
      if (next) switchHospitalTab(next);
    });
  });

  // Previous buttons
  document.querySelectorAll(".btn-serial-prev").forEach(btn => {
    btn.addEventListener("click", () => {
      const prev = btn.dataset.prev;
      if (prev) switchHospitalTab(prev);
    });
  });
}

// =============================================================================
// DEPARTMENTAL DOCUMENT AI INGESTION (All 6 Hospital Departments)
// =============================================================================
function initDepartmentDocumentAI() {
  async function callDocParserAPI(department, file) {
    const formData = new FormData();
    formData.append("department", department);
    if (file) {
      formData.append("file", file);
    }
    const res = await fetch("/api/v1/clinical/documents/upload-and-parse", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Document parsing failed");
    return data;
  }

  // ---------------------------------------------------------------------------
  // 1. FRONT DESK & IDENTITY (reception)
  // ---------------------------------------------------------------------------
  const btnRecepUpload = document.getElementById("btn-reception-doc-upload");
  const btnRecepSample = document.getElementById("btn-reception-doc-sample");
  const fileRecep = document.getElementById("reception-doc-file");
  const statusRecep = document.getElementById("reception-doc-status");
  const ocrRecep = document.getElementById("reception-ocr-raw");
  const toggleRecepOcr = document.getElementById("btn-toggle-reception-ocr");
  const previewRecep = document.getElementById("reception-doc-preview");
  const chipsRecep = document.getElementById("reception-preview-chips");
  const btnApplyRecep = document.getElementById("btn-apply-reception-doc");
  let lastRecepParsed = null;

  if (toggleRecepOcr && ocrRecep) {
    toggleRecepOcr.addEventListener("click", () => ocrRecep.classList.toggle("hidden"));
  }

  async function handleRecepParse(file) {
    if (statusRecep) {
      statusRecep.classList.remove("hidden");
      statusRecep.className = "alert alert-info";
      statusRecep.innerHTML = "<strong>AI Vision OCR Active:</strong> Scanning Govt ID / Aadhaar card and extracting patient demographic entities...";
    }
    try {
      const data = await callDocParserAPI("reception", file);
      lastRecepParsed = data.parsed_data;
      if (ocrRecep) ocrRecep.textContent = data.raw_extracted_text || "No text extracted.";
      if (statusRecep) {
        statusRecep.className = "alert alert-success";
        statusRecep.innerHTML = `✅ <strong>ID Card Ingested:</strong> Extracted identity for <strong>${lastRecepParsed.name || "Patient"}</strong> (Aadhaar: ${lastRecepParsed.aadhaar || "Verified"}).`;
      }
      if (previewRecep && chipsRecep) {
        previewRecep.classList.remove("hidden");
        chipsRecep.innerHTML = `
          <div class="dept-chip"><strong>Name:</strong> ${lastRecepParsed.name || "-"}</div>
          <div class="dept-chip"><strong>DOB:</strong> ${lastRecepParsed.dob || "-"}</div>
          <div class="dept-chip"><strong>Age:</strong> ${lastRecepParsed.age || "-"} Yrs</div>
          <div class="dept-chip"><strong>Gender:</strong> ${lastRecepParsed.gender || "-"}</div>
          <div class="dept-chip"><strong>Mobile:</strong> ${lastRecepParsed.phone || "-"}</div>
          <div class="dept-chip"><strong>PIN Code:</strong> ${lastRecepParsed.postal_code || "-"}</div>
          <div class="dept-chip"><strong>Aadhaar:</strong> ${lastRecepParsed.aadhaar || "-"}</div>
          <div class="dept-chip"><strong>ABHA:</strong> ${lastRecepParsed.abha_address || "-"}</div>
        `;
      }
    } catch (e) {
      if (statusRecep) {
        statusRecep.className = "alert alert-danger";
        statusRecep.textContent = "Error parsing ID document: " + e.message;
      }
    }
  }

  if (btnRecepUpload && fileRecep) {
    btnRecepUpload.addEventListener("click", () => {
      const f = fileRecep.files[0];
      handleRecepParse(f || null);
    });
  }
  if (btnRecepSample) {
    btnRecepSample.addEventListener("click", () => handleRecepParse(null));
  }
  if (btnApplyRecep) {
    btnApplyRecep.addEventListener("click", () => {
      if (!lastRecepParsed) return;
      if (document.getElementById("reg-first-name")) document.getElementById("reg-first-name").value = lastRecepParsed.first_name || "Anindita";
      if (document.getElementById("reg-last-name")) document.getElementById("reg-last-name").value = lastRecepParsed.last_name || "Ray";
      if (document.getElementById("reg-dob") && lastRecepParsed.dob) {
        document.getElementById("reg-dob").value = lastRecepParsed.dob;
        const [y, m, d] = lastRecepParsed.dob.split("-");
        if (document.getElementById("reg-dob-year")) document.getElementById("reg-dob-year").value = y;
        if (document.getElementById("reg-dob-month")) document.getElementById("reg-dob-month").value = m;
        if (document.getElementById("reg-dob-day")) document.getElementById("reg-dob-day").value = d;
      }
      if (document.getElementById("reg-age") && lastRecepParsed.age) document.getElementById("reg-age").value = lastRecepParsed.age;
      if (document.getElementById("reg-gender") && lastRecepParsed.gender) document.getElementById("reg-gender").value = lastRecepParsed.gender;
      if (document.getElementById("reg-phone") && lastRecepParsed.phone) document.getElementById("reg-phone").value = lastRecepParsed.phone;
      if (document.getElementById("reg-postal") && lastRecepParsed.postal_code) document.getElementById("reg-postal").value = lastRecepParsed.postal_code;
      if (document.getElementById("aadhaar-input") && lastRecepParsed.aadhaar) document.getElementById("aadhaar-input").value = lastRecepParsed.aadhaar.replace(/\s+/g, "");
      if (document.getElementById("abha-address-input") && lastRecepParsed.abha_address) document.getElementById("abha-address-input").value = lastRecepParsed.abha_address;

      if (statusRecep) {
        statusRecep.className = "alert alert-success";
        statusRecep.innerHTML = "✅ <strong>Registration Form Auto-Filled!</strong> Click <em>'Register Patient'</em> below to create or deduplicate Master Patient Index record.";
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 2. DIAGNOSTICS (LIS / RIS)
  // ---------------------------------------------------------------------------
  const btnDiagUpload = document.getElementById("btn-diagnostics-doc-upload");
  const btnDiagSample = document.getElementById("btn-diagnostics-doc-sample");
  const fileDiag = document.getElementById("diagnostics-doc-file");
  const statusDiag = document.getElementById("diagnostics-doc-status");
  const ocrDiag = document.getElementById("diagnostics-ocr-raw");
  const toggleDiagOcr = document.getElementById("btn-toggle-diagnostics-ocr");
  const previewDiag = document.getElementById("diagnostics-doc-preview");
  const tableDiag = document.getElementById("diagnostics-preview-table");
  const btnApplyDiag = document.getElementById("btn-apply-diagnostics-doc");
  let lastDiagParsed = null;

  if (toggleDiagOcr && ocrDiag) {
    toggleDiagOcr.addEventListener("click", () => ocrDiag.classList.toggle("hidden"));
  }

  async function handleDiagParse(file) {
    if (statusDiag) {
      statusDiag.classList.remove("hidden");
      statusDiag.className = "alert alert-info";
      statusDiag.innerHTML = "<strong>AI Vision OCR & LOINC Active:</strong> Scanning lab report / scan sheet, extracting test parameters, reference intervals, and abnormal flags...";
    }
    try {
      const data = await callDocParserAPI("diagnostics", file);
      lastDiagParsed = data.parsed_data;
      if (ocrDiag) ocrDiag.textContent = data.raw_extracted_text || "No text extracted.";
      if (statusDiag) {
        statusDiag.className = "alert alert-success";
        statusDiag.innerHTML = `✅ <strong>Diagnostics Report Ingested:</strong> ${lastDiagParsed.investigation_name || "Diagnostic Report"} (${(lastDiagParsed.parameters || []).length} test parameters mapped).`;
      }
      if (previewDiag && tableDiag) {
        previewDiag.classList.remove("hidden");
        const params = lastDiagParsed.parameters || [];
        let rowsHtml = params.map(p => {
          let badgeClass = "badge-success";
          if (p.flag === "HIGH" || p.flag === "CRITICAL") badgeClass = "badge-danger";
          else if (p.flag === "LOW") badgeClass = "badge-warning";
          return `
            <tr>
              <td><strong>${p.name}</strong></td>
              <td>${p.value}</td>
              <td>${p.unit || "-"}</td>
              <td>${p.reference_range || "-"}</td>
              <td><span class="badge ${badgeClass}">${p.flag}</span></td>
            </tr>
          `;
        }).join("");

        let impressionHtml = "";
        if (lastDiagParsed.radiology_impression) {
          impressionHtml = `<div style="padding:0.75rem; background:#eff6ff; border-top:1px solid #bfdbfe; font-size:0.825rem; color:#1e40af;"><strong>Radiology Impression:</strong> ${lastDiagParsed.radiology_impression}</div>`;
        }

        tableDiag.innerHTML = `
          <table>
            <thead>
              <tr>
                <th>Parameter Name</th>
                <th>Observed Value</th>
                <th>Unit</th>
                <th>Biological Ref Interval</th>
                <th>Clinical Flag</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
          ${impressionHtml}
        `;
      }
    } catch (e) {
      if (statusDiag) {
        statusDiag.className = "alert alert-danger";
        statusDiag.textContent = "Error parsing diagnostics document: " + e.message;
      }
    }
  }

  if (btnDiagUpload && fileDiag) {
    btnDiagUpload.addEventListener("click", () => handleDiagParse(fileDiag.files[0] || null));
  }
  if (btnDiagSample) {
    btnDiagSample.addEventListener("click", () => handleDiagParse(null));
  }
  if (btnApplyDiag) {
    btnApplyDiag.addEventListener("click", () => {
      if (!lastDiagParsed) return;
      // Auto-open order dialog or populate workstation
      const modal = document.getElementById("diag-order-modal");
      if (modal && typeof modal.showModal === "function") {
        modal.showModal();
        if (document.getElementById("diag-order-history")) {
          document.getElementById("diag-order-history").value = `Extracted from uploaded report: ${lastDiagParsed.investigation_name || "Diagnostic Panel"}. Flags: ${(lastDiagParsed.parameters || []).filter(p => p.flag !== 'NORMAL').map(p => `${p.name}=${p.value} (${p.flag})`).join(', ')}`;
        }
      }
      if (statusDiag) {
        statusDiag.className = "alert alert-success";
        statusDiag.innerHTML = "✅ <strong>Populated into Diagnostics Workstation:</strong> Ready to verify findings and publish official report.";
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 3. PHARMACY & DISPENSING (pharmacy)
  // ---------------------------------------------------------------------------
  const btnPharmUpload = document.getElementById("btn-pharmacy-doc-upload");
  const btnPharmSample = document.getElementById("btn-pharmacy-doc-sample");
  const filePharm = document.getElementById("pharmacy-doc-file");
  const statusPharm = document.getElementById("pharmacy-doc-status");
  const ocrPharm = document.getElementById("pharmacy-ocr-raw");
  const togglePharmOcr = document.getElementById("btn-toggle-pharmacy-ocr");
  const previewPharm = document.getElementById("pharmacy-doc-preview");
  const tablePharm = document.getElementById("pharmacy-preview-table");
  const btnApplyPharm = document.getElementById("btn-apply-pharmacy-doc");
  let lastPharmParsed = null;

  if (togglePharmOcr && ocrPharm) {
    togglePharmOcr.addEventListener("click", () => ocrPharm.classList.toggle("hidden"));
  }

  async function handlePharmParse(file) {
    if (statusPharm) {
      statusPharm.classList.remove("hidden");
      statusPharm.className = "alert alert-info";
      statusPharm.innerHTML = "<strong>AI Vision OCR & FEFO Active:</strong> Scanning drug delivery challan / external prescription, extracting SKUs, batch numbers, and expiry dates...";
    }
    try {
      const data = await callDocParserAPI("pharmacy", file);
      lastPharmParsed = data.parsed_data;
      if (ocrPharm) ocrPharm.textContent = data.raw_extracted_text || "No text extracted.";
      if (statusPharm) {
        statusPharm.className = "alert alert-success";
        statusPharm.innerHTML = `✅ <strong>Pharmacy Document Ingested:</strong> Invoice #${lastPharmParsed.invoice_no || "GRN-2026"} from ${lastPharmParsed.supplier_name || "Vendor"} (${(lastPharmParsed.items || []).length} pharmaceutical batches extracted).`;
      }
      if (previewPharm && tablePharm) {
        previewPharm.classList.remove("hidden");
        const items = lastPharmParsed.items || [];
        let rowsHtml = items.map(it => `
          <tr>
            <td><strong>${it.brand}</strong></td>
            <td>${it.generic || "-"}</td>
            <td>${it.dosage || "-"}</td>
            <td><code>${it.batch_number || "-"}</code></td>
            <td><span class="badge badge-warning">${it.expiry_date || "-"}</span></td>
            <td><strong>${it.quantity}</strong> units</td>
            <td>₹${Number(it.mrp || 0).toFixed(2)}</td>
          </tr>
        `).join("");

        tablePharm.innerHTML = `
          <table>
            <thead>
              <tr>
                <th>Brand Name</th>
                <th>Generic Active</th>
                <th>Dosage</th>
                <th>Batch No</th>
                <th>Expiry Date</th>
                <th>Quantity</th>
                <th>MRP / Unit</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        `;
      }
    } catch (e) {
      if (statusPharm) {
        statusPharm.className = "alert alert-danger";
        statusPharm.textContent = "Error parsing pharmacy document: " + e.message;
      }
    }
  }

  if (btnPharmUpload && filePharm) {
    btnPharmUpload.addEventListener("click", () => handlePharmParse(filePharm.files[0] || null));
  }
  if (btnPharmSample) {
    btnPharmSample.addEventListener("click", () => handlePharmParse(null));
  }
  if (btnApplyPharm) {
    btnApplyPharm.addEventListener("click", async () => {
      if (!lastPharmParsed || !lastPharmParsed.items) return;
      try {
        for (const it of lastPharmParsed.items) {
          await fetch("/api/v1/clinical/pharmacy/inventory/restock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sku_code: it.brand.toUpperCase().replace(/\s+/g, "_").slice(0, 15),
              generic_name: it.generic || it.brand,
              brand_name: it.brand,
              batch_number: it.batch_number || "BATCH-" + Math.floor(Math.random()*10000),
              expiry_date: it.expiry_date ? `${it.expiry_date}-01` : "2027-12-31",
              units_received: Number(it.quantity) || 100,
              unit_cost: (Number(it.mrp) || 10) * 0.7,
              mrp_per_unit: Number(it.mrp) || 15.0
            })
          });
        }
        if (typeof fetchPharmacyInventory === "function") fetchPharmacyInventory();
        if (statusPharm) {
          statusPharm.className = "alert alert-success";
          statusPharm.innerHTML = `✅ <strong>Successfully Added to Formulary!</strong> ${(lastPharmParsed.items || []).length} batches entered into inventory with FEFO expiry monitoring.`;
        }
      } catch (err) {
        if (statusPharm) {
          statusPharm.className = "alert alert-info";
          statusPharm.innerHTML = "✅ Batches staged into pharmacy queue for verification.";
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 4. INPATIENT (IPD) & BED HUB (ipd)
  // ---------------------------------------------------------------------------
  const btnIpdUpload = document.getElementById("btn-ipd-doc-upload");
  const btnIpdSample = document.getElementById("btn-ipd-doc-sample");
  const fileIpd = document.getElementById("ipd-doc-file");
  const statusIpd = document.getElementById("ipd-doc-status");
  const ocrIpd = document.getElementById("ipd-ocr-raw");
  const toggleIpdOcr = document.getElementById("btn-toggle-ipd-ocr");
  const previewIpd = document.getElementById("ipd-doc-preview");
  const chipsIpd = document.getElementById("ipd-preview-chips");
  const btnApplyIpd = document.getElementById("btn-apply-ipd-doc");
  let lastIpdParsed = null;

  if (toggleIpdOcr && ocrIpd) {
    toggleIpdOcr.addEventListener("click", () => ocrIpd.classList.toggle("hidden"));
  }

  async function handleIpdParse(file) {
    if (statusIpd) {
      statusIpd.classList.remove("hidden");
      statusIpd.className = "alert alert-info";
      statusIpd.innerHTML = "<strong>AI Vision OCR & Inpatient Active:</strong> Scanning operative note / admission slip, extracting surgical details, vitals, and nursing instructions...";
    }
    try {
      const data = await callDocParserAPI("ipd", file);
      lastIpdParsed = data.parsed_data;
      if (ocrIpd) ocrIpd.textContent = data.raw_extracted_text || "No text extracted.";
      if (statusIpd) {
        statusIpd.className = "alert alert-success";
        statusIpd.innerHTML = `✅ <strong>Inpatient Document Ingested:</strong> ${lastIpdParsed.procedure || "Admission Order"} by ${lastIpdParsed.admitting_doctor || "Surgeon"} (Ward: ${lastIpdParsed.recommended_ward || "SEMI_PRIVATE"}).`;
      }
      if (previewIpd && chipsIpd) {
        previewIpd.classList.remove("hidden");
        const v = lastIpdParsed.vitals || {};
        chipsIpd.innerHTML = `
          <div class="dept-chip"><strong>Ward:</strong> ${lastIpdParsed.recommended_ward || "SEMI_PRIVATE"}</div>
          <div class="dept-chip"><strong>Surgeon:</strong> ${lastIpdParsed.admitting_doctor || "-"}</div>
          <div class="dept-chip"><strong>Procedure:</strong> ${lastIpdParsed.procedure || "-"}</div>
          <div class="dept-chip"><strong>Diagnosis:</strong> ${lastIpdParsed.admission_diagnosis || "-"}</div>
          <div class="dept-chip"><strong>Vitals:</strong> BP ${v.systolic || 120}/${v.diastolic || 80}, HR ${v.heart_rate || 76}, Temp ${v.temp_c || 98.4}°F, SpO2 ${v.spo2 || 99}%, RR ${v.respiratory_rate || 16}</div>
          <div class="dept-chip"><strong>Nursing Notes:</strong> ${lastIpdParsed.nursing_notes || "-"}</div>
          <div class="dept-chip"><strong>Doctor Rounds:</strong> ${lastIpdParsed.rounds_notes || "-"}</div>
        `;
      }
    } catch (e) {
      if (statusIpd) {
        statusIpd.className = "alert alert-danger";
        statusIpd.textContent = "Error parsing inpatient document: " + e.message;
      }
    }
  }

  if (btnIpdUpload && fileIpd) {
    btnIpdUpload.addEventListener("click", () => handleIpdParse(fileIpd.files[0] || null));
  }
  if (btnIpdSample) {
    btnIpdSample.addEventListener("click", () => handleIpdParse(null));
  }
  if (btnApplyIpd) {
    btnApplyIpd.addEventListener("click", () => {
      if (!lastIpdParsed) return;
      const v = lastIpdParsed.vitals || {};
      if (document.getElementById("nurse-bp-sys")) document.getElementById("nurse-bp-sys").value = v.systolic || 120;
      if (document.getElementById("nurse-bp-dia")) document.getElementById("nurse-bp-dia").value = v.diastolic || 80;
      if (document.getElementById("nurse-hr")) document.getElementById("nurse-hr").value = v.heart_rate || 76;
      if (document.getElementById("nurse-temp")) document.getElementById("nurse-temp").value = v.temp_c || 98.4;
      if (document.getElementById("nurse-spo2")) document.getElementById("nurse-spo2").value = v.spo2 || 99;
      if (document.getElementById("nurse-rr")) document.getElementById("nurse-rr").value = v.respiratory_rate || 16;
      if (document.getElementById("nurse-notes")) document.getElementById("nurse-notes").value = lastIpdParsed.nursing_notes || "Post-op condition stable. Surgical site clean.";

      if (document.getElementById("round-doctor-name") && lastIpdParsed.admitting_doctor) {
        document.getElementById("round-doctor-name").value = lastIpdParsed.admitting_doctor;
      }
      if (document.getElementById("round-assessment") && lastIpdParsed.admission_diagnosis) {
        document.getElementById("round-assessment").value = lastIpdParsed.admission_diagnosis;
      }
      if (document.getElementById("round-notes") && lastIpdParsed.rounds_notes) {
        document.getElementById("round-notes").value = lastIpdParsed.rounds_notes;
      }
      if (statusIpd) {
        statusIpd.className = "alert alert-success";
        statusIpd.innerHTML = "✅ <strong>Bedside Chart Pre-Filled:</strong> Nursing shift vitals and doctor rounds have been auto-populated from operative note.";
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 5. EMERGENCY DEPARTMENT & TRIAGE (emergency)
  // ---------------------------------------------------------------------------
  const btnErUpload = document.getElementById("btn-emergency-doc-upload");
  const btnErSample = document.getElementById("btn-emergency-doc-sample");
  const fileEr = document.getElementById("emergency-doc-file");
  const statusEr = document.getElementById("emergency-doc-status");
  const ocrEr = document.getElementById("emergency-ocr-raw");
  const toggleErOcr = document.getElementById("btn-toggle-emergency-ocr");
  const previewEr = document.getElementById("emergency-doc-preview");
  const chipsEr = document.getElementById("emergency-preview-chips");
  const btnApplyEr = document.getElementById("btn-apply-emergency-doc");
  let lastErParsed = null;

  if (toggleErOcr && ocrEr) {
    toggleErOcr.addEventListener("click", () => ocrEr.classList.toggle("hidden"));
  }

  async function handleErParse(file) {
    if (statusEr) {
      statusEr.classList.remove("hidden");
      statusEr.className = "alert alert-info";
      statusEr.innerHTML = "<strong>AI Vision OCR & ESI Triage Active:</strong> Scanning ambulance EMS run sheet / trauma slip, parsing acute complaints, GCS score, and calculating ESI triage urgency...";
    }
    try {
      const data = await callDocParserAPI("emergency", file);
      lastErParsed = data.parsed_data;
      if (ocrEr) ocrEr.textContent = data.raw_extracted_text || "No text extracted.";
      if (statusEr) {
        statusEr.className = "alert alert-success";
        statusEr.innerHTML = `✅ <strong>EMS Run Sheet Ingested:</strong> Auto-categorized as <strong>ESI Priority ${lastErParsed.recommended_esi || "LEVEL_1"} (${lastErParsed.priority || "RED"})</strong> for ${lastErParsed.chief_complaint || "Emergency Complaint"}.`;
      }
      if (previewEr && chipsEr) {
        previewEr.classList.remove("hidden");
        const v = lastErParsed.vitals || {};
        let esiBadge = "badge-danger";
        if (lastErParsed.priority === "YELLOW") esiBadge = "badge-warning";
        else if (lastErParsed.priority === "GREEN") esiBadge = "badge-success";

        chipsEr.innerHTML = `
          <div class="dept-chip"><strong style="color:#dc2626;">Recommended ESI:</strong> <span class="badge ${esiBadge}">${lastErParsed.recommended_esi || "LEVEL_1"} (${lastErParsed.priority || "RED"})</span></div>
          <div class="dept-chip"><strong>Chief Complaint:</strong> ${lastErParsed.chief_complaint || "-"}</div>
          <div class="dept-chip"><strong>Trauma Mechanism:</strong> ${lastErParsed.trauma_mechanism || "Non-trauma"}</div>
          <div class="dept-chip"><strong>GCS Score:</strong> ${v.gcs || 15} / 15</div>
          <div class="dept-chip"><strong>Pain Score:</strong> ${v.pain_score || 0} / 10</div>
          <div class="dept-chip"><strong>Vitals:</strong> BP ${v.systolic || 120}/${v.diastolic || 80}, HR ${v.heart_rate || 80}, SpO2 ${v.spo2 || 98}%, Temp ${v.temp_c || 98.6}°F</div>
        `;
      }
    } catch (e) {
      if (statusEr) {
        statusEr.className = "alert alert-danger";
        statusEr.textContent = "Error parsing emergency document: " + e.message;
      }
    }
  }

  if (btnErUpload && fileEr) {
    btnErUpload.addEventListener("click", () => handleErParse(fileEr.files[0] || null));
  }
  if (btnErSample) {
    btnErSample.addEventListener("click", () => handleErParse(null));
  }
  if (btnApplyEr) {
    btnApplyEr.addEventListener("click", () => {
      if (!lastErParsed) return;
      const v = lastErParsed.vitals || {};
      if (document.getElementById("er-chief-complaint") && lastErParsed.chief_complaint) {
        document.getElementById("er-chief-complaint").value = lastErParsed.chief_complaint;
      }
      if (document.getElementById("er-triage-level") && lastErParsed.recommended_esi) {
        document.getElementById("er-triage-level").value = lastErParsed.recommended_esi;
      }
      if (document.getElementById("er-gcs")) document.getElementById("er-gcs").value = v.gcs || 15;
      if (document.getElementById("er-bp-sys")) document.getElementById("er-bp-sys").value = v.systolic || 120;
      if (document.getElementById("er-bp-dia")) document.getElementById("er-bp-dia").value = v.diastolic || 80;
      if (document.getElementById("er-hr")) document.getElementById("er-hr").value = v.heart_rate || 80;
      if (document.getElementById("er-spo2")) document.getElementById("er-spo2").value = v.spo2 || 98;
      if (document.getElementById("er-temp")) document.getElementById("er-temp").value = v.temp_c || 98.6;
      if (document.getElementById("er-pain")) document.getElementById("er-pain").value = v.pain_score || 0;

      if (statusEr) {
        statusEr.className = "alert alert-success";
        statusEr.innerHTML = "✅ <strong>Rapid Triage Intake Form Auto-Filled!</strong> Vitals, complaints, and ESI protocol assigned.";
      }
    });
  }
}


