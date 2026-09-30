"use strict";

const state = {
  offers: [],
  tab: "pending",
  query: "",
  editingId: null,
  busyId: null,
};

const elements = {
  grid: document.querySelector("#offer-grid"),
  search: document.querySelector("#search"),
  tabs: [...document.querySelectorAll("[data-tab]")],
  pendingCount: document.querySelector("#pending-count"),
  sentCount: document.querySelector("#sent-count"),
  averageDiscount: document.querySelector("#average-discount"),
  pendingBadge: document.querySelector("#pending-badge"),
  demoBanner: document.querySelector("#demo-banner"),
  notice: document.querySelector("#notice"),
  noticeText: document.querySelector("#notice span"),
  modal: document.querySelector("#modal-backdrop"),
  affiliateUrl: document.querySelector("#affiliate-url"),
  message: document.querySelector("#message"),
  saveEdit: document.querySelector(".save-edit"),
};

const icons = {
  clock: '<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>',
  send: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"></path><path d="M22 2 11 13"></path></svg>',
  close: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m6 6 12 12"></path><path d="m18 6-12 12"></path></svg>',
  external: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 3h6v6"></path><path d="m10 14 11-11"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg>',
  check: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"></path></svg>',
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function safeUrl(value) {
  try {
    const url = new URL(value, window.location.origin);
    return url.protocol === "https:" || url.origin === window.location.origin ? url.href : "";
  } catch {
    return "";
  }
}

function formatMoney(value) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency", currency: "MXN", maximumFractionDigits: 0,
  }).format(value);
}

function relativeDate(value) {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 60) return `Hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Hace ${hours} h`;
  return `Hace ${Math.round(hours / 24)} d`;
}

function buildMessage(offer, link) {
  const before = offer.original_price ? `Antes: ${formatMoney(offer.original_price)}\n` : "";
  const discount = offer.discount > 0 ? `🔥 ${offer.discount}% de descuento\n` : "";
  return `⚡ OFERTA EN MERCADO LIBRE\n\n${offer.title}\n\n${discount}${before}💛 Ahora: ${formatMoney(offer.price)}\n🚚 ${offer.shipping}\n\n👉 Ver oferta: ${link}\n\nPrecio y disponibilidad pueden cambiar.`;
}

function showNotice(message) {
  elements.noticeText.textContent = message;
  elements.notice.hidden = false;
}

function renderStats() {
  const pending = state.offers.filter((offer) => ["pending", "approved"].includes(offer.status)).length;
  const sent = state.offers.filter((offer) => offer.status === "sent").length;
  const average = state.offers.length
    ? Math.round(state.offers.reduce((total, offer) => total + offer.discount, 0) / state.offers.length)
    : 0;
  elements.pendingCount.textContent = pending;
  elements.sentCount.textContent = sent;
  elements.averageDiscount.textContent = `${average}%`;
  elements.pendingBadge.textContent = pending;
}

function offerCard(offer) {
  const isPending = state.tab === "pending";
  const image = safeUrl(offer.image_url);
  const productUrl = safeUrl(offer.product_url);
  const affiliateWarning = !offer.affiliate_url
    ? '<button class="link-warning" data-action="edit">Falta agregar el enlace de afiliado →</button>'
    : "";
  const pendingActions = `
    <button class="icon-button reject" data-action="reject" ${state.busyId === offer.id ? "disabled" : ""} aria-label="Descartar">${icons.close}</button>
    <button class="secondary" data-action="edit">Editar</button>
    <button class="primary" data-action="share" ${state.busyId === offer.id || !offer.affiliate_url ? "disabled" : ""}>${icons.send}${state.busyId === offer.id ? "Preparando…" : "Enviar"}</button>`;
  const historyActions = `
    <a class="secondary full" href="${escapeHtml(productUrl)}" target="_blank" rel="noreferrer">Ver producto ${icons.external}</a>
    ${state.tab === "rejected" ? '<button class="primary" data-action="restore">Restaurar</button>' : ""}`;

  return `
    <article class="offer-card" data-id="${escapeHtml(offer.id)}">
      <div class="product-image">
        <img src="${escapeHtml(image)}" alt="" loading="lazy">
        <span class="discount">-${Number(offer.discount)}%</span>
        <span class="category">${escapeHtml(offer.category)}</span>
      </div>
      <div class="offer-body">
        <div class="found">${icons.clock} ${escapeHtml(relativeDate(offer.found_at))}</div>
        <h2>${escapeHtml(offer.title)}</h2>
        <div class="price-row"><strong>${escapeHtml(formatMoney(offer.price))}</strong>${offer.original_price ? `<del>${escapeHtml(formatMoney(offer.original_price))}</del>` : ""}</div>
        <p class="shipping">✓ ${escapeHtml(offer.shipping)}</p>
        <div class="seller"><span>Vendido por</span><strong>${escapeHtml(offer.seller)}</strong></div>
        ${affiliateWarning}
        <div class="card-actions">${isPending ? pendingActions : historyActions}</div>
      </div>
    </article>`;
}

function renderOffers() {
  const filtered = state.offers.filter((offer) => {
    const matchesTab = state.tab === "pending"
      ? ["pending", "approved"].includes(offer.status)
      : offer.status === state.tab;
    const haystack = `${offer.title} ${offer.category}`.toLowerCase();
    return matchesTab && haystack.includes(state.query.toLowerCase());
  });
  elements.grid.innerHTML = filtered.length
    ? filtered.map(offerCard).join("")
    : `<div class="empty"><span>${icons.check}</span><h2>Todo está al día</h2><p>No hay ofertas en esta sección.</p></div>`;
  renderStats();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "No se pudo completar la operación");
  return data;
}

async function patchOffer(id, changes) {
  state.busyId = id;
  renderOffers();
  try {
    const data = await api(`/api/offers/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
    state.offers = state.offers.map((offer) => offer.id === id ? data.offer : offer);
    return data;
  } catch (error) {
    showNotice(error.message);
    return null;
  } finally {
    state.busyId = null;
    renderOffers();
  }
}

function openEditor(offer) {
  state.editingId = offer.id;
  elements.affiliateUrl.value = offer.affiliate_url || "";
  elements.message.value = offer.message;
  elements.modal.hidden = false;
  document.body.classList.add("modal-open");
  elements.affiliateUrl.focus();
}

function closeEditor() {
  state.editingId = null;
  elements.modal.hidden = true;
  document.body.classList.remove("modal-open");
}

elements.grid.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  const card = event.target.closest("[data-id]");
  if (!button || !card) return;
  const offer = state.offers.find((item) => item.id === card.dataset.id);
  if (!offer) return;

  if (button.dataset.action === "edit") openEditor(offer);
  if (button.dataset.action === "reject") await patchOffer(offer.id, { status: "rejected" });
  if (button.dataset.action === "restore") await patchOffer(offer.id, { status: "pending" });
  if (button.dataset.action === "share") {
    const whatsappWindow = window.open("about:blank", "_blank");
    const data = await patchOffer(offer.id, {
      prepare_share: true,
      affiliate_url: offer.affiliate_url,
      message: offer.message,
    });
    if (data?.whatsappUrl && whatsappWindow) {
      whatsappWindow.opener = null;
      whatsappWindow.location.href = data.whatsappUrl;
    } else {
      whatsappWindow?.close();
      if (data?.whatsappUrl) showNotice("El navegador bloqueó WhatsApp. Permite ventanas emergentes para este sitio.");
    }
  }
});

elements.tabs.forEach((tab) => tab.addEventListener("click", () => {
  state.tab = tab.dataset.tab;
  elements.tabs.forEach((item) => item.classList.toggle("active", item === tab));
  renderOffers();
}));

elements.search.addEventListener("input", () => {
  state.query = elements.search.value;
  renderOffers();
});

elements.affiliateUrl.addEventListener("input", () => {
  const offer = state.offers.find((item) => item.id === state.editingId);
  if (offer) elements.message.value = buildMessage(offer, elements.affiliateUrl.value || "Agrega tu enlace de afiliado");
});

elements.saveEdit.addEventListener("click", async () => {
  if (!state.editingId) return;
  const data = await patchOffer(state.editingId, {
    affiliate_url: elements.affiliateUrl.value.trim() || null,
    message: elements.message.value.trim(),
  });
  if (data) closeEditor();
});

document.querySelectorAll(".modal-close, .cancel-edit").forEach((button) => button.addEventListener("click", closeEditor));
elements.modal.addEventListener("mousedown", (event) => {
  if (event.target === elements.modal) closeEditor();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.modal.hidden) closeEditor();
});
elements.notice.querySelector("button").addEventListener("click", () => { elements.notice.hidden = true; });

async function initialize() {
  try {
    const data = await api("/api/offers");
    state.offers = data.offers;
    elements.demoBanner.hidden = !data.demoMode;
    renderOffers();
  } catch (error) {
    showNotice(error.message);
    elements.grid.innerHTML = '<div class="empty"><h2>No se pudieron cargar las ofertas</h2><p>Revisa la configuración del servidor.</p></div>';
  }
}

initialize();
