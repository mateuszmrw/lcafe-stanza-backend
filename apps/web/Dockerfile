# Build context must be the monorepo root (npm workspaces — lockfile lives there).
# In docker-compose: context: ./ (repo root), dockerfile: apps/web/Dockerfile

# --- deps: install node_modules via root workspace lockfile ---
FROM node:20-alpine AS deps
WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/
# All deps are declared at root — npm ci puts everything in /repo/node_modules
RUN npm ci

# --- builder: compile the Next.js app ---
FROM node:20-alpine AS builder
WORKDIR /repo

# All packages are in root node_modules (no workspace-level split)
COPY --from=deps /repo/node_modules ./node_modules
COPY apps/web ./apps/web

# NEXT_PUBLIC_API_URL is baked into the client bundle at build time.
# It must be the URL the *browser* can reach (backend port is published on host).
ARG NEXT_PUBLIC_API_URL=http://localhost:8678
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /repo/apps/web
RUN npm run build

# --- runner: minimal production image ---
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

# standalone output bundles only what's needed to run the server
COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone/apps/web ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
