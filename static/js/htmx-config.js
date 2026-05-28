// SafraLog — HTMX global config
document.body.addEventListener("htmx:configRequest", (event) => {
  event.detail.headers["X-CSRFToken"] = getCookie("csrftoken");
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}
