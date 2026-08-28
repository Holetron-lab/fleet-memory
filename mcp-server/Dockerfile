# Container image for the fleet-memory MCP server (stdio transport).
#
# This image exists for directory listings (Glama and friends) that require a
# buildable Dockerfile and start the server to introspect its tool list. It
# packages ONLY mcp-server/, not the RCLL backend: the MCP server is a thin
# stdio client that talks to a self-hosted backend over FLEET_URL.
#
# Introspection works with no backend reachable — the five tools are registered
# at module load, before any HTTP call. Actual tool calls need FLEET_URL to
# point at a running RCLL API (see docker-compose.rcll.yml at the repo root).
#
#   build:  docker build -t fleet-memory-mcp mcp-server/
#   run:    docker run --rm -i -e FLEET_URL=http://host.docker.internal:5100 fleet-memory-mcp

FROM node:22-alpine

WORKDIR /app

# Dependencies first so the layer caches independently of server.js edits.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY server.js README.md LICENSE ./

# Backend location. Overridden at run time; the default matches the local
# docker-compose stack. The pre-rebrand name HINDSIGHT_URL is still read.
ENV FLEET_URL=http://127.0.0.1:5100

# stdio transport: the container talks MCP over stdin/stdout, so it must be run
# with -i and must not print anything but protocol frames on stdout.
ENTRYPOINT ["node", "server.js"]
