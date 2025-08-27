FROM python:3.11-slim as builder

# Set work directory
WORKDIR /app

# Install build system and build tools
RUN pip install hatchling build

# Copy project files
COPY pyproject.toml README.md /app/
COPY src /app/src

# Build the project wheel
RUN python -m build

# Use a separate environment for the final image
FROM python:3.11-slim

WORKDIR /app

# Copy the built wheel from builder stage
COPY --from=builder /app/dist/*.whl /app/

# Install the package and Flask for HTTP wrapper
 RUN pip install --no-cache-dir /app/*.whl flask

# Add debugging info
RUN pip show mcp-server-reddit

# Copy HTTP wrapper
COPY mcp_http_wrapper.py /app/

# Run HTTP wrapper instead of direct MCP server
ENTRYPOINT ["python", "mcp_http_wrapper.py"]
