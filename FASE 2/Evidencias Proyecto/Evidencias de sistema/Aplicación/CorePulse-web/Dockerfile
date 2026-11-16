# CorePulse Web · Imagen para ejecutar el sitio en local con Docker.
# En producción el sitio se publica en Cloudflare (npm run deploy); esta imagen usa
# el servidor de Next.js para levantarlo en cualquier equipo con Docker.

FROM node:22-bookworm-slim AS dependencias
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-bookworm-slim AS compilacion
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# Las variables NEXT_PUBLIC_* se incorporan al compilar, por eso llegan como argumentos.
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=$NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
COPY --from=dependencias /app/node_modules ./node_modules
COPY . .
RUN npx next build

FROM node:22-bookworm-slim AS ejecucion
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
COPY --from=compilacion /app ./
EXPOSE 3000
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
