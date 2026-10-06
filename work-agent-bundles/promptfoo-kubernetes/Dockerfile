# Connected-side build. Verify/import this image into the internal registry.
# The OCI index includes linux/amd64 and linux/arm64.
FROM ghcr.io/promptfoo/promptfoo:0.122.2@sha256:e0eb45e5fd4ae8243f01c307b455285eb4ce9b420134bdc43a573c667e80e709
ENV PROMPTFOO_DISABLE_TELEMETRY=1 \
    PROMPTFOO_DISABLE_UPDATE=1 \
    PROMPTFOO_OFFICIAL_DOCKER_IMAGE=0 \
    PROMPTFOO_CONFIG_DIR=/data \
    NODE_PATH=/app/node_modules
COPY --chown=1000:1000 work-agent-bundles/aks-skills-specialists /opt/aks-evals
COPY --chmod=0555 work-agent-bundles/promptfoo-kubernetes/scripts/run-aks-evaluation /usr/local/bin/run-aks-evaluation
# Verify the dependency used by Microsoft's router provider before export.
RUN node -e "require('js-yaml')" && python3 --version && PROMPTFOO_CONFIG_DIR=/tmp/promptfoo-build-check promptfoo --version
USER 1000:1000
# Inherit the official web-server command. Kubernetes Jobs override it.
