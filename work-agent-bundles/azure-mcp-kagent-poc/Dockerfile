FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c
RUN apt-get update && apt-get install -y --no-install-recommends libicu72 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN npm install --global @azure/mcp@3.0.0-beta.48 && npm cache clean --force
USER node
ENV AZURE_MCP_COLLECT_TELEMETRY=false AZURE_MCP_COLLECT_TELEMETRY_MICROSOFT=false
ENTRYPOINT ["azmcp"]
