FROM python:3.11-slim

WORKDIR /app

# Install the package (including its runtime dependencies from pyproject.toml).
COPY . .
RUN python -m pip install --no-cache-dir .

# Mount a host directory here to persist the SQLite index.
VOLUME ["/data"]
ENV GITHUB_TOOL_DB=/data/github-tool.db

ENTRYPOINT ["github-tool"]
