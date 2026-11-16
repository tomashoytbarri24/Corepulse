import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// `npm run build` ejecuta OpenNext, y OpenNext compila Next con este comando
// (así Cloudflare Workers Builds funciona con su configuración por defecto).
const config = { ...defineCloudflareConfig(), buildCommand: "npx next build" };

export default config;
