# The MCP server as an image, for the MCP Registry. Built by .github/workflows/mcp-image.yml.
# The server reads a git repository on the host: mount it, e.g. -v "$PWD:/repo" and pass "/repo".
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* && git config --system --add safe.directory '*'
LABEL io.modelcontextprotocol.server.name="io.github.luizfnsilva/closure_drift"
LABEL org.opencontainers.image.source="https://github.com/luizfnsilva/closure_drift"
LABEL org.opencontainers.image.licenses="Apache-2.0"
WORKDIR /app
COPY closure_drift.py closure_drift_mcp.py ./
ENTRYPOINT ["python3", "/app/closure_drift_mcp.py"]
