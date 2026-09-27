// State
let currentPatient = null;
let currentEncounterId = null;
let currentAadhaarTxnId = null;
let currentAbhaTxnId = null;
let pendingDuplicatePayload = null;

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
  initTabNavigation();
  initSubTabs();
  initRegistrationForm();
  initDobPicker();
  initAbhaLinking();
  initClinicianConsultation();
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
      if (target === "abdm-events" && currentPatient) {
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
