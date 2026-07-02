FROM stonebranch/universal-agent:8.0.0.0-debian

# Pre-bake the runtime user so ua_entrypoint has nothing to write to /etc/passwd at startup.
# The pod runs as UID 10010, GID 0 (root group — standard for OpenShift/hardened K8s).
# Replace the useradd line below if inspection of ua_entrypoint reveals a different username.
#
# To find the exact entry ua_entrypoint writes, run:
#   docker run --rm --entrypoint cat stonebranch/universal-agent:8.0.0.0-debian /bin/ua_entrypoint

USER root

RUN useradd \
    --uid 10010 \
    --gid 0 \
    --no-create-home \
    --shell /sbin/nologin \
    --comment "Stonebranch UAG runtime user" \
    uaguser

# Switch back to the runtime user
USER 10010
