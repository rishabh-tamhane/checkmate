const DEBOUNCE_MILLISECONDS = 300;
const CALCULATION_ENDPOINT = "/api/splits/calculate";
const EXTRACTION_ENDPOINT = "/api/receipts/extract";
const PDF_ENDPOINT = "/api/splits/pdf";

const elements = {
  addItem: document.querySelector("[data-add-item]"),
  addParticipant: document.querySelector("[data-add-participant]"),
  calculatedSubtotal: document.querySelector("[data-calculated-subtotal]"),
  calculatedTotal: document.querySelector("[data-calculated-total]"),
  calculationStatus: document.querySelector("[data-calculation-status]"),
  enteredSubtotal: document.querySelector("[data-entered-subtotal]"),
  enteredTotal: document.querySelector("[data-entered-total]"),
  errorList: document.querySelector("[data-error-list]"),
  errorSummary: document.querySelector("[data-error-summary]"),
  extractionNoticeList: document.querySelector("[data-extraction-notice-list]"),
  extractionNotices: document.querySelector("[data-extraction-notices]"),
  generatePdf: document.querySelector("[data-generate-pdf]"),
  participantList: document.querySelector("[data-participant-list]"),
  participantsEmpty: document.querySelector("[data-participants-empty]"),
  pdfNote: document.querySelector("[data-pdf-note]"),
  receiptBody: document.querySelector("[data-receipt-body]"),
  receiptHead: document.querySelector("[data-receipt-head]"),
  retry: document.querySelector("[data-retry]"),
  subtotalDifference: document.querySelector("[data-subtotal-difference]"),
  summaryBody: document.querySelector("[data-summary-body]"),
  summaryEmpty: document.querySelector("[data-summary-empty]"),
  totalDifference: document.querySelector("[data-total-difference]"),
  uploadButton: document.querySelector("[data-upload-button]"),
  uploadFile: document.querySelector("[data-upload-file]"),
  uploadForm: document.querySelector("[data-upload-form]"),
  uploadRetry: document.querySelector("[data-upload-retry]"),
  uploadStatus: document.querySelector("[data-upload-status]"),
};

const fieldRegistry = new Map();
let debounceTimer;
let lastUploadFile;
let latestCalculationResult;

function createId(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function createItem() {
  return {
    id: createId("item"),
    name: "",
    quantity: "",
    lineTotal: "",
  };
}

const draft = {
  revision: 0,
  receipt: {
    restaurantName: "",
    date: "",
    items: [createItem()],
    subtotal: "",
    tax: "",
    tip: "",
    total: "",
  },
  participants: [],
  assignments: {},
};

function requireElement(element, name) {
  if (!(element instanceof HTMLElement)) {
    throw new Error(`Missing application element: ${name}`);
  }
  return element;
}

Object.entries(elements).forEach(([name, element]) => requireElement(element, name));

function beginDraftChange(immediate) {
  draft.revision += 1;
  markPending();
  window.clearTimeout(debounceTimer);
  if (immediate) {
    void sendCalculation(draft.revision);
    return;
  }
  debounceTimer = window.setTimeout(() => {
    void sendCalculation(draft.revision);
  }, DEBOUNCE_MILLISECONDS);
}

function registerField(path, element) {
  fieldRegistry.set(path, element);
  element.dataset.fieldPath = path;
}

function setReceiptField(field, value) {
  draft.receipt[field] = value;
  renderRawEnteredValues();
  beginDraftChange(false);
}

function configureReceiptFields() {
  document.querySelectorAll("[data-receipt-field]").forEach((element) => {
    if (!(element instanceof HTMLInputElement)) {
      return;
    }
    const field = element.dataset.receiptField;
    if (!field || !(field in draft.receipt) || field === "items") {
      return;
    }
    element.value = draft.receipt[field];
    const path = field === "restaurantName" ? "restaurant_name" : field;
    registerField(`receipt.${path}`, element);
    element.addEventListener("input", () => setReceiptField(field, element.value));
  });
}

function syncReceiptFields() {
  document.querySelectorAll("[data-receipt-field]").forEach((element) => {
    if (!(element instanceof HTMLInputElement)) {
      return;
    }
    const field = element.dataset.receiptField;
    if (field && field in draft.receipt && field !== "items") {
      element.value = draft.receipt[field];
    }
  });
}

function renderExtractionNotices(notices) {
  elements.extractionNoticeList.replaceChildren();
  notices.forEach((notice) => {
    const item = document.createElement("li");
    item.textContent = notice;
    elements.extractionNoticeList.append(item);
  });
  elements.extractionNotices.hidden = notices.length === 0;
}

function applyExtraction(result) {
  draft.receipt = result.receipt;
  draft.assignments = Object.fromEntries(
    result.receipt.items.map((item) => [item.id, []]),
  );
  syncReceiptFields();
  renderReceiptTable();
  renderExtractionNotices(result.notices);
  renderRawEnteredValues();
  beginDraftChange(true);
}

async function uploadReceipt(file) {
  lastUploadFile = file;
  elements.uploadButton.disabled = true;
  elements.uploadRetry.hidden = true;
  elements.uploadStatus.textContent = "Extracting receipt…";
  const form = new FormData();
  form.append("receipt", file);
  try {
    const response = await fetch(EXTRACTION_ENDPOINT, {
      method: "POST",
      headers: {"X-Checkmate-Request": "1"},
      body: form,
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(
        result.error?.message || "Receipt extraction failed. Enter it manually.",
      );
    }
    applyExtraction(result);
    lastUploadFile = undefined;
    elements.uploadFile.value = "";
    elements.uploadStatus.textContent =
      "Extraction complete. Review and correct every field.";
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Receipt extraction failed. Enter it manually.";
    elements.uploadStatus.textContent = `${message} Your current draft is unchanged.`;
    elements.uploadRetry.hidden = false;
  } finally {
    elements.uploadButton.disabled = elements.uploadFile.disabled;
  }
}

function renderParticipants() {
  elements.participantList.replaceChildren();
  elements.participantsEmpty.hidden = draft.participants.length > 0;

  draft.participants.forEach((participant, index) => {
    const row = document.createElement("div");
    row.className = "participant-row";

    const field = document.createElement("div");
    field.className = "field participant-field";
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.id = `participant-name-${participant.id}`;
    input.type = "text";
    input.maxLength = 200;
    input.value = participant.name;
    label.htmlFor = input.id;
    label.textContent = `Participant ${index + 1} name`;
    registerField(`participants.${participant.id}.name`, input);
    input.addEventListener("input", () => {
      participant.name = input.value;
      updateParticipantPresentation(participant);
      beginDraftChange(false);
    });
    field.append(label, input);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "text-button danger-button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove participant ${index + 1}`);
    remove.addEventListener("click", () => removeParticipant(participant.id));

    row.append(field, remove);
    elements.participantList.append(row);
  });
}

function updateParticipantPresentation(participant) {
  const displayName = participant.name.trim() || "Unnamed participant";
  document
    .querySelectorAll(`[data-participant-heading="${participant.id}"]`)
    .forEach((heading) => {
      heading.textContent = displayName;
    });
  document
    .querySelectorAll(`[data-assignment-participant="${participant.id}"]`)
    .forEach((checkbox) => {
      if (checkbox instanceof HTMLInputElement) {
        checkbox.setAttribute(
          "aria-label",
          `Share item ${checkbox.dataset.assignmentItemNumber} with ${displayName}`,
        );
      }
    });
}

function addParticipant() {
  draft.participants.push({id: createId("person"), name: ""});
  renderParticipants();
  renderReceiptTable();
  beginDraftChange(true);
  const newest = draft.participants.at(-1);
  document.querySelector(`#participant-name-${newest.id}`)?.focus();
}

function removeParticipant(participantId) {
  draft.participants = draft.participants.filter(
    (participant) => participant.id !== participantId,
  );
  Object.keys(draft.assignments).forEach((itemId) => {
    draft.assignments[itemId] = draft.assignments[itemId].filter(
      (assignedId) => assignedId !== participantId,
    );
  });
  renderParticipants();
  renderReceiptTable();
  beginDraftChange(true);
}

function renderReceiptTable() {
  fieldRegistry.forEach((element, path) => {
    if (path.startsWith("receipt.items.") || path.startsWith("assignments.")) {
      fieldRegistry.delete(path);
    }
  });
  elements.receiptHead.replaceChildren();
  elements.receiptBody.replaceChildren();

  const headingRow = document.createElement("tr");
  ["Item", "Quantity", "Line total"].forEach((text, index) => {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.textContent = text;
    if (index === 0) {
      heading.className = "sticky-column";
    }
    headingRow.append(heading);
  });
  draft.participants.forEach((participant) => {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.dataset.participantHeading = participant.id;
    heading.textContent = participant.name.trim() || "Unnamed participant";
    headingRow.append(heading);
  });
  const actionHeading = document.createElement("th");
  actionHeading.scope = "col";
  actionHeading.textContent = "Action";
  headingRow.append(actionHeading);
  elements.receiptHead.append(headingRow);

  draft.receipt.items.forEach((item, itemIndex) => {
    const row = document.createElement("tr");
    row.dataset.itemId = item.id;

    const nameCell = document.createElement("th");
    nameCell.scope = "row";
    nameCell.className = "sticky-column";
    const nameInput = document.createElement("input");
    nameInput.id = `item-name-${item.id}`;
    nameInput.type = "text";
    nameInput.maxLength = 200;
    nameInput.value = item.name;
    nameInput.placeholder = "Item name";
    nameInput.setAttribute("aria-label", `Item ${itemIndex + 1} name`);
    registerField(`receipt.items.${item.id}.name`, nameInput);
    nameInput.addEventListener("input", () => {
      item.name = nameInput.value;
      beginDraftChange(false);
    });
    nameCell.append(nameInput);
    row.append(nameCell);

    const quantityCell = document.createElement("td");
    const quantityInput = document.createElement("input");
    quantityInput.id = `item-quantity-${item.id}`;
    quantityInput.inputMode = "decimal";
    quantityInput.value = item.quantity;
    quantityInput.placeholder = "Optional";
    quantityInput.setAttribute("aria-label", `Item ${itemIndex + 1} quantity`);
    registerField(`receipt.items.${item.id}.quantity`, quantityInput);
    quantityInput.addEventListener("input", () => {
      item.quantity = quantityInput.value;
      beginDraftChange(false);
    });
    quantityCell.append(quantityInput);
    row.append(quantityCell);

    const totalCell = document.createElement("td");
    const moneyWrap = document.createElement("div");
    moneyWrap.className = "table-money-field";
    const prefix = document.createElement("span");
    prefix.textContent = "$";
    prefix.setAttribute("aria-hidden", "true");
    const totalInput = document.createElement("input");
    totalInput.id = `item-total-${item.id}`;
    totalInput.inputMode = "decimal";
    totalInput.value = item.lineTotal;
    totalInput.setAttribute("aria-label", `Item ${itemIndex + 1} line total`);
    registerField(`receipt.items.${item.id}.line_total`, totalInput);
    totalInput.addEventListener("input", () => {
      item.lineTotal = totalInput.value;
      beginDraftChange(false);
    });
    moneyWrap.append(prefix, totalInput);
    totalCell.append(moneyWrap);
    row.append(totalCell);

    draft.participants.forEach((participant) => {
      const assignmentCell = document.createElement("td");
      assignmentCell.className = "assignment-cell";
      const checkbox = document.createElement("input");
      checkbox.id = `assignment-${item.id}-${participant.id}`;
      checkbox.type = "checkbox";
      checkbox.checked = (draft.assignments[item.id] || []).includes(participant.id);
      checkbox.dataset.assignmentParticipant = participant.id;
      checkbox.dataset.assignmentItemNumber = String(itemIndex + 1);
      checkbox.setAttribute(
        "aria-label",
        `Share item ${itemIndex + 1} with ${participant.name.trim() || "unnamed participant"}`,
      );
      const assignmentPath = `assignments.${item.id}`;
      if (!fieldRegistry.has(assignmentPath)) {
        registerField(assignmentPath, checkbox);
      }
      checkbox.addEventListener("change", () => {
        updateAssignment(item.id, participant.id, checkbox.checked);
      });
      assignmentCell.append(checkbox);
      row.append(assignmentCell);
    });

    const actionCell = document.createElement("td");
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "text-button danger-button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove item ${itemIndex + 1}`);
    remove.addEventListener("click", () => removeItem(item.id));
    actionCell.append(remove);
    row.append(actionCell);
    elements.receiptBody.append(row);
  });
}

function addItem() {
  const item = createItem();
  draft.receipt.items.push(item);
  draft.assignments[item.id] = [];
  renderReceiptTable();
  beginDraftChange(true);
  document.querySelector(`#item-name-${item.id}`)?.focus();
}

function removeItem(itemId) {
  draft.receipt.items = draft.receipt.items.filter((item) => item.id !== itemId);
  delete draft.assignments[itemId];
  renderReceiptTable();
  beginDraftChange(true);
}

function updateAssignment(itemId, participantId, checked) {
  const assigned = new Set(draft.assignments[itemId] || []);
  if (checked) {
    assigned.add(participantId);
  } else {
    assigned.delete(participantId);
  }
  draft.assignments[itemId] = draft.participants
    .map((participant) => participant.id)
    .filter((id) => assigned.has(id));
  beginDraftChange(true);
}

function displayRawMoney(value) {
  return value.trim() || "Blank";
}

function renderRawEnteredValues() {
  elements.enteredSubtotal.textContent = displayRawMoney(draft.receipt.subtotal);
  elements.enteredTotal.textContent = displayRawMoney(draft.receipt.total);
}

function markPending() {
  latestCalculationResult = undefined;
  clearIssues();
  elements.calculationStatus.textContent = "Pending";
  elements.calculationStatus.dataset.state = "pending";
  elements.retry.hidden = true;
  elements.generatePdf.disabled = true;
  elements.pdfNote.textContent = "Waiting for the latest calculation.";
  elements.summaryBody.replaceChildren();
  elements.summaryEmpty.hidden = false;
  elements.summaryEmpty.textContent = "Calculation pending…";
  elements.calculatedSubtotal.textContent = "Unavailable";
  elements.subtotalDifference.textContent = "Unavailable";
  elements.calculatedTotal.textContent = "Unavailable";
  elements.totalDifference.textContent = "Unavailable";
  renderRawEnteredValues();
}

async function sendCalculation(revision) {
  try {
    const response = await fetch(CALCULATION_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Checkmate-Request": "1",
      },
      body: JSON.stringify({...draft, revision}),
    });
    if (!response.ok) {
      throw new Error("Calculation request failed.");
    }
    const result = await response.json();
    if (result.revision !== draft.revision) {
      return;
    }
    renderCalculation(result);
  } catch {
    if (revision !== draft.revision) {
      return;
    }
    renderNetworkFailure();
  }
}

function clearIssues() {
  document.querySelectorAll("[data-field-issue]").forEach((issue) => issue.remove());
  fieldRegistry.forEach((field) => field.removeAttribute("aria-describedby"));
  elements.errorList.replaceChildren();
  elements.errorSummary.hidden = true;
}

function renderIssues(issues) {
  clearIssues();
  if (issues.length === 0) {
    return;
  }
  issues.forEach((issue, index) => {
    const target = fieldRegistry.get(issue.path);
    const listItem = document.createElement("li");
    if (target instanceof HTMLElement) {
      const message = document.createElement("p");
      const messageId = `field-issue-${index}`;
      message.id = messageId;
      message.className = "field-issue";
      message.dataset.fieldIssue = "true";
      message.textContent = issue.message;
      target.setAttribute("aria-describedby", messageId);
      target.insertAdjacentElement("afterend", message);

      const link = document.createElement("a");
      link.href = `#${target.id}`;
      link.textContent = issue.message;
      listItem.append(link);
    } else {
      listItem.textContent = issue.message;
    }
    elements.errorList.append(listItem);
  });
  elements.errorSummary.hidden = false;
}

function renderCalculation(result) {
  latestCalculationResult = result;
  renderIssues(result.issues);
  elements.calculationStatus.textContent = result.finalized ? "Ready" : "Needs attention";
  elements.calculationStatus.dataset.state = result.finalized ? "ready" : "invalid";
  elements.retry.hidden = true;

  if (result.reconciliation) {
    elements.enteredSubtotal.textContent = result.reconciliation.subtotal.entered;
    elements.calculatedSubtotal.textContent = result.reconciliation.subtotal.calculated;
    elements.subtotalDifference.textContent = result.reconciliation.subtotal.difference;
    elements.enteredTotal.textContent = result.reconciliation.total.entered;
    elements.calculatedTotal.textContent = result.reconciliation.total.calculated;
    elements.totalDifference.textContent = result.reconciliation.total.difference;
  } else {
    renderRawEnteredValues();
    elements.calculatedSubtotal.textContent = "Unavailable";
    elements.subtotalDifference.textContent = "Unavailable";
    elements.calculatedTotal.textContent = "Unavailable";
    elements.totalDifference.textContent = "Unavailable";
  }

  elements.summaryBody.replaceChildren();
  result.participantTotals.forEach((participant) => {
    const row = document.createElement("tr");
    [
      participant.name,
      participant.itemSubtotal,
      participant.tax,
      participant.tip,
      participant.total,
    ].forEach((value, index) => {
      const cell = document.createElement(index === 0 ? "th" : "td");
      if (index === 0) {
        cell.scope = "row";
      }
      cell.textContent = value;
      row.append(cell);
    });
    elements.summaryBody.append(row);
  });
  elements.summaryEmpty.hidden = result.participantTotals.length > 0;
  if (result.participantTotals.length === 0) {
    elements.summaryEmpty.textContent = "Correct the listed issues to calculate shares.";
  }

  const canGeneratePdf = result.finalized && result.nonZero;
  elements.generatePdf.disabled = !canGeneratePdf;
  elements.pdfNote.textContent = canGeneratePdf
    ? "The split is ready to download as a PDF."
    : "Complete a valid non-zero split to enable PDF export.";
}

function renderNetworkFailure() {
  latestCalculationResult = undefined;
  clearIssues();
  elements.calculationStatus.textContent = "Unavailable";
  elements.calculationStatus.dataset.state = "failed";
  elements.retry.hidden = false;
  elements.generatePdf.disabled = true;
  elements.pdfNote.textContent = "The draft is safe in this page. Retry the calculation.";
  elements.summaryBody.replaceChildren();
  elements.summaryEmpty.hidden = false;
  elements.summaryEmpty.textContent = "Totals are unavailable.";
  elements.calculatedSubtotal.textContent = "Unavailable";
  elements.subtotalDifference.textContent = "Unavailable";
  elements.calculatedTotal.textContent = "Unavailable";
  elements.totalDifference.textContent = "Unavailable";
  renderRawEnteredValues();
}

function pdfFilename(response) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = /filename="([^"]+)"/.exec(disposition);
  return match ? match[1] : "checkmate-split.pdf";
}

function restorePdfButton() {
  const currentResult = latestCalculationResult;
  const ready =
    currentResult &&
    currentResult.revision === draft.revision &&
    currentResult.finalized &&
    currentResult.nonZero;
  elements.generatePdf.disabled = !ready;
}

async function generatePdf() {
  const requestedRevision = draft.revision;
  elements.generatePdf.disabled = true;
  elements.pdfNote.textContent = "Generating PDF…";
  try {
    const response = await fetch(PDF_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Checkmate-Request": "1",
      },
      body: JSON.stringify({...draft, revision: requestedRevision}),
    });
    if (response.status === 422) {
      const result = await response.json();
      if (result.revision === draft.revision) {
        renderCalculation(result);
        elements.pdfNote.textContent = "Correct the listed issues before downloading.";
      }
      return;
    }
    if (!response.ok) {
      throw new Error("PDF request failed.");
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = pdfFilename(response);
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
    if (requestedRevision === draft.revision) {
      elements.pdfNote.textContent = "PDF downloaded. Your editable draft is unchanged.";
    }
  } catch {
    if (requestedRevision === draft.revision) {
      elements.pdfNote.textContent =
        "The PDF could not be generated. Your draft is unchanged; please try again.";
    }
  } finally {
    restorePdfButton();
  }
}

elements.addParticipant.addEventListener("click", addParticipant);
elements.addItem.addEventListener("click", addItem);
elements.uploadForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const file = elements.uploadFile.files?.item(0);
  if (!file) {
    elements.uploadStatus.textContent = "Choose a receipt image first.";
    return;
  }
  void uploadReceipt(file);
});
elements.uploadRetry.addEventListener("click", () => {
  if (lastUploadFile) {
    void uploadReceipt(lastUploadFile);
  }
});
elements.retry.addEventListener("click", () => {
  draft.revision += 1;
  markPending();
  void sendCalculation(draft.revision);
});
elements.generatePdf.addEventListener("click", () => void generatePdf());

configureReceiptFields();
renderParticipants();
renderReceiptTable();
renderRawEnteredValues();
draft.revision += 1;
markPending();
void sendCalculation(draft.revision);
