const applicationStatus = document.querySelector("[data-application-status]");

if (applicationStatus instanceof HTMLElement) {
  applicationStatus.dataset.javascript = "available";
}
