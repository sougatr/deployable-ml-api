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
  initBillingAndPayment();
  fetchHealthStatus();
});

// Viewport Tab Navigation
function initTabNavigation() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.tab;
      document.querySelectorAll(".viewport-panel").forEach(panel => {
        panel.classList.remove("active");
      });
      document.getElementById(`panel-${target}`).classList.add("active");
      if (target === "ipd") {
        fetchBedMatrix();
      } else if (target === "diagnostics") {
        fetchDiagnosticsCatalog();
        fetchDiagnosticsWorklist();
      } else if (target === "pharmacy") {
        fetchPharmacyInventory();
        populatePrescriptionDispenseQueue();
      } else if (target === "abdm-events" && currentPatient) {
        refreshAbdmAndOutbox();
      }
    });
  });
}

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

      // 1. Column 1: Chief Complaints & Symptoms
      const colComplaints = document.getElementById("col-complaints-content");
      if (colComplaints) {
        colComplaints.innerHTML = `
          <div class="parsed-item-badge">
            <span>🩺</span>
            <span>${parsed.chief_complaint || "Patient clinical consultation"}</span>
          </div>
        `;
      }
      if (parsed.chief_complaint) {
        const el = document.getElementById("consult-complaint");
        el.value = parsed.chief_complaint;
        highlightEls.push(el);
      }
      if (parsed.clinical_narrative) {
        const el = document.getElementById("consult-narrative");
        el.value = parsed.clinical_narrative;
        highlightEls.push(el);
      }

      // 2. Column 2: Coded Diagnoses (ICD-10 & SNOMED CT)
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

      // 3. Column 3: Vitals (LOINC Standard)
      const colVitals = document.getElementById("col-vitals-content");
      if (colVitals) colVitals.innerHTML = "";

      if (parsed.vitals && parsed.vitals.length > 0) {
        for (const v of parsed.vitals) {
          if (colVitals) {
            const badge = document.createElement("div");
            badge.className = "parsed-item-badge";
            const isNorm = v.interpretation === "NORMAL";
            badge.innerHTML = `<strong>${v.display}:</strong> ${v.value} ${v.unit} <span class="badge ${isNorm ? 'badge-success' : 'badge-warning'}" style="font-size:0.65rem; padding: 0.1rem 0.35rem;">${v.interpretation}</span>`;
            colVitals.appendChild(badge);
          }

          if (v.code_loinc === "8480-6") {
            const el = document.getElementById("vital-sbp");
            el.value = v.value;
            highlightEls.push(el);
          } else if (v.code_loinc === "8867-4") {
            const el = document.getElementById("vital-hr");
            el.value = v.value;
            highlightEls.push(el);
          }
        }
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


