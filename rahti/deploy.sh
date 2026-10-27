#!/bin/bash
set -e

# Usage: rahti/deploy.sh [--rebuild]
#   --rebuild   build both images from the local source before rolling out
#
# The visualizations image is built from a checkout of
# jakobytes/filter-visualizations (branch filter-visualizations-parquet), by default
# next to this repository; override with FILTER_VISUALIZATIONS_DIR.
#
# Needs the Secret livonia-allas-reader (AWS_ACCESS_KEY_ID,
# AWS_SECRET_ACCESS_KEY) with read access to the livonia-parquet bucket.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VIS_DIR="${FILTER_VISUALIZATIONS_DIR:-$(dirname "$REPO_ROOT")/filter-visualizations}"

oc whoami &>/dev/null || { echo "Not logged in to Rahti. Run: oc login https://api.2.rahti.csc.fi:6443"; exit 1; }
echo "Deploying to project: $(oc project -q)"
oc get secret livonia-allas-reader &>/dev/null || \
  echo "WARNING: Secret livonia-allas-reader is missing; the parquet download will fail."

echo "Applying manifests..."
for f in imagestreams buildconfigs deployment services routes; do
  oc apply -f "$SCRIPT_DIR/$f.yaml"
done

if [[ "$1" == "--rebuild" ]]; then
  [[ -f "$VIS_DIR/app.R" ]] || { echo "filter-visualizations not found in $VIS_DIR"; exit 1; }
  # Upload only what the images need (not .git or a local parquet copy)
  BUILD_DIR="$(mktemp -d)"
  trap 'rm -rf "$BUILD_DIR"' EXIT
  rsync -a --exclude-from="$REPO_ROOT/.dockerignore" "$REPO_ROOT/" "$BUILD_DIR/runoregi/"
  rsync -a --exclude-from="$VIS_DIR/.dockerignore" "$VIS_DIR/" "$BUILD_DIR/visualizations/"
  oc start-build dhh26-runoregi --from-dir="$BUILD_DIR/runoregi" --follow
  oc start-build dhh26-visualizations --from-dir="$BUILD_DIR/visualizations" --follow
fi

echo ""
oc get route dhh26-runoregi dhh26-visualizations -o custom-columns='NAME:.metadata.name,HOST:.spec.host'
