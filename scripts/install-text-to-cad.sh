#!/bin/sh
# Install text-to-cad (https://github.com/earthtojake/text-to-cad) for Claude Code and Codex.
#
# It downloads the installer attached to a pinned release, checks it against the SHA-256
# recorded here, and runs it. Agents that are not installed on this machine are skipped.
# Telemetry is turned off; turn it back on with `cad telemetry on`.
#
#   sh scripts/install-text-to-cad.sh
#
# To move to a newer release, update CAD_VERSION and INSTALLER_SHA256 from that release's
# SHA256SUMS: https://github.com/earthtojake/text-to-cad/releases
# To remove it: `cad uninstall`.

set -eu

CAD_VERSION="0.11.9"
INSTALLER_SHA256="ac9379a03e6f3f90fd1e68499107e6ebba3abee79fd55623d68caeb9aa481568"
URL="https://github.com/earthtojake/text-to-cad/releases/download/v${CAD_VERSION}/install.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

curl -fsSL "$URL" -o "$tmp/install.sh"

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$tmp/install.sh" | cut -d' ' -f1)
else
  actual=$(shasum -a 256 "$tmp/install.sh" | cut -d' ' -f1)
fi
if [ "$actual" != "$INSTALLER_SHA256" ]; then
  echo "error: text-to-cad installer checksum mismatch (expected $INSTALLER_SHA256, got $actual)" >&2
  exit 1
fi

sh "$tmp/install.sh" --version "$CAD_VERSION" --only claude,codex --no-telemetry "$@"
