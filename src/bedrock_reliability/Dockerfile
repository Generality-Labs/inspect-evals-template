# IMAGE_NAME=bedrock-reliability
# Pinned to the current Playwright release (matches the `playwright` PyPI
# version this image ships) so Chromium and its system deps are the exact
# pair Playwright expects — avoids the dependency drift of
# `playwright install --with-deps` on a generic base image.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

# The image bundles the browser binaries but not the Python bindings — pinned
# to match the image tag exactly, since a mismatched playwright package can
# expect a different browser build than what's actually on disk.
RUN pip install --no-cache-dir playwright==1.62.0

WORKDIR /opt/bedrock

COPY site/ /opt/bedrock/site/
COPY site_server.py control_server.py entrypoint.sh /opt/bedrock/
RUN chmod +x /opt/bedrock/entrypoint.sh

# Documentation only — compose.yaml does not publish these. Both services are
# reached from inside the container via sandbox().exec(), so the sandbox has
# no route to the outside network at all, which is the point: the pages it
# serves are pinned, not fetched live.
EXPOSE 8080 8000

CMD ["/opt/bedrock/entrypoint.sh"]
