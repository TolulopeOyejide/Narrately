// Narrately — frontend logic.
// Talks to the FastAPI backend in src/narrately/api.py.
// If the frontend is served BY that API (the default), same-origin
// relative paths just work. Override API_BASE if hosting separately.
const API_BASE = "";

const els = {
  apiStatus: document.getElementById("apiStatus"),
  tabUpload: document.getElementById("tabUpload"),
  tabWebpage: document.getElementById("tabWebpage"),
  panelUpload: document.getElementById("panelUpload"),
  panelWebpage: document.getElementById("panelWebpage"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("fileInput"),
  previewImg: document.getElementById("previewImg"),
  viewfinderEmpty: document.getElementById("viewfinderEmpty"),
  uploadReadout: document.getElementById("uploadReadout"),
  uploadReadoutText: document.getElementById("uploadReadoutText"),
  webpageForm: document.getElementById("webpageForm"),
  webpageUrl: document.getElementById("webpageUrl"),
  webpageLimit: document.getElementById("webpageLimit"),
  webpageSubmit: document.getElementById("webpageSubmit"),
  webpageStatus: document.getElementById("webpageStatus"),
  webpageStatusText: document.getElementById("webpageStatusText"),
  webpageResults: document.getElementById("webpageResults"),
};

// ---------------------------------------------------------------- //
// Tabs
// ---------------------------------------------------------------- //
function activateTab(name) {
  const isUpload = name === "upload";
  els.tabUpload.classList.toggle("is-active", isUpload);
  els.tabWebpage.classList.toggle("is-active", !isUpload);
  els.tabUpload.setAttribute("aria-selected", String(isUpload));
  els.tabWebpage.setAttribute("aria-selected", String(!isUpload));
  els.panelUpload.hidden = !isUpload;
  els.panelWebpage.hidden = isUpload;
}
els.tabUpload.addEventListener("click", () => activateTab("upload"));
els.tabWebpage.addEventListener("click", () => activateTab("webpage"));

// ---------------------------------------------------------------- //
// Readout helper — typewriter effect into a mono "sensor readout"
// ---------------------------------------------------------------- //
function setReadout(readoutEl, textEl, state, message) {
  readoutEl.dataset.state = state;
  if (state !== "done") {
    textEl.textContent = message;
    return;
  }
  // Typewriter reveal for the finished caption.
  textEl.textContent = "";
  let i = 0;
  const interval = setInterval(() => {
    textEl.textContent = message.slice(0, i + 1);
    i += 1;
    if (i >= message.length) clearInterval(interval);
  }, 18);
}

// ---------------------------------------------------------------- //
// Health check
// ---------------------------------------------------------------- //
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error();
    els.apiStatus.dataset.state = "ready";
    els.apiStatus.lastChild.textContent = "model ready";
  } catch {
    els.apiStatus.dataset.state = "error";
    els.apiStatus.lastChild.textContent = "backend unreachable";
  }
}
checkHealth();

// ---------------------------------------------------------------- //
// Upload panel
// ---------------------------------------------------------------- //
function showPreview(file) {
  const url = URL.createObjectURL(file);
  els.previewImg.src = url;
  els.previewImg.hidden = false;
  els.viewfinderEmpty.hidden = true;
}

async function captionFile(file) {
  if (!file.type.startsWith("image/")) {
    setReadout(els.uploadReadout, els.uploadReadoutText, "error", "That doesn't look like an image file.");
    return;
  }
  showPreview(file);
  els.dropzone.classList.add("is-busy");
  setReadout(els.uploadReadout, els.uploadReadoutText, "busy", "Reading image");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/api/caption/image`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Captioning failed.");
    setReadout(els.uploadReadout, els.uploadReadoutText, "done", data.caption);
  } catch (err) {
    setReadout(els.uploadReadout, els.uploadReadoutText, "error", err.message || "Something went wrong.");
  } finally {
    els.dropzone.classList.remove("is-busy");
  }
}

els.dropzone.addEventListener("click", () => els.fileInput.click());
els.dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    els.fileInput.click();
  }
});
els.fileInput.addEventListener("change", () => {
  if (els.fileInput.files[0]) captionFile(els.fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("is-dragging");
  })
);
["dragleave", "drop"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("is-dragging");
  })
);
els.dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) captionFile(file);
});

// ---------------------------------------------------------------- //
// Webpage panel
// ---------------------------------------------------------------- //
els.webpageForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = els.webpageUrl.value.trim();
  const limit = Number(els.webpageLimit.value) || 8;
  if (!url) return;

  els.webpageSubmit.disabled = true;
  els.webpageResults.hidden = true;
  els.webpageResults.innerHTML = "";
  setReadout(els.webpageStatus, els.webpageStatusText, "busy", "Scanning page for images");

  try {
    const res = await fetch(`${API_BASE}/api/caption/webpage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, limit }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not scan that page.");

    if (data.results.length === 0) {
      setReadout(els.webpageStatus, els.webpageStatusText, "done", "No captionable images found on that page.");
      return;
    }

    setReadout(
      els.webpageStatus,
      els.webpageStatusText,
      "done",
      `Captioned ${data.results.length} image${data.results.length === 1 ? "" : "s"}.`
    );
    renderResults(data.results);
  } catch (err) {
    setReadout(els.webpageStatus, els.webpageStatusText, "error", err.message || "Something went wrong.");
  } finally {
    els.webpageSubmit.disabled = false;
  }
});

function renderResults(results) {
  els.webpageResults.hidden = false;
  for (const { image_url, caption } of results) {
    const card = document.createElement("div");
    card.className = "result-card";

    const img = document.createElement("img");
    img.src = image_url;
    img.alt = caption;
    img.loading = "lazy";

    const cap = document.createElement("p");
    cap.className = "result-card__caption";
    cap.textContent = caption;

    card.appendChild(img);
    card.appendChild(cap);
    els.webpageResults.appendChild(card);
  }
}
