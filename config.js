// Backend de produccion en Vercel.
// Si cambias el dominio del proyecto en Vercel, cambia solo esta linea.
const MEDICG_VERCEL_BACKEND = "https://medic-g-git-main-medicgs-projects.vercel.app";

// En GitHub Pages se usa Vercel como backend. En Vercel se usa /api del mismo dominio.
window.MEDICG_API_BASE = location.hostname.endsWith("github.io") ? MEDICG_VERCEL_BACKEND : "";
window.MEDICG_REQUIRE_BACKEND = true;
