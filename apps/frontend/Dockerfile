# ============================================================
# SQA KB Frontend — Multi-stage Dockerfile para Azure Container Apps
# ============================================================
# Construye desde la raíz del monorepo para poder resolver pnpm-workspace.
#   docker build -f apps/frontend/Dockerfile -t sqa-kb-frontend .
# ============================================================

FROM node:20-alpine AS deps
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
WORKDIR /repo

# Copy minimal files for dep resolution to maximize layer cache
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/frontend/package.json apps/frontend/
RUN pnpm install --frozen-lockfile --filter @sqa/frontend...

# ------------------------------------------------------------
FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/frontend/node_modules ./apps/frontend/node_modules
COPY . .
ENV NEXT_BUILD_STANDALONE=true
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @sqa/frontend build

# ------------------------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /repo/apps/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/frontend/.next/static ./apps/frontend/.next/static
COPY --from=builder --chown=nextjs:nodejs /repo/apps/frontend/public ./apps/frontend/public

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/login || exit 1

CMD ["node", "apps/frontend/server.js"]
