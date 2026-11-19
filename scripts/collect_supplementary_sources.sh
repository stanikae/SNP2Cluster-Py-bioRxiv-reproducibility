#!/usr/bin/env bash
set -euo pipefail

OUT="supplementary_source_bundle"
ZIP="supplementary_source_bundle.zip"
REPRO="${REPRO:-../SNP2Cluster-Py-bioRxiv-reproducibility}"
FIGURE3_ROOT="${FIGURE3_ROOT:-manuscript_v1.1.2_outputs/figure3}"
FIGURE4_ROOT="${FIGURE4_ROOT:-manuscript_v1.1.2_outputs/figure4}"

required_vars=(
  KP_FULL_ST_RUN
  KP_FULL_FACILITY_ST_RUN
  KP_HOSPITAL_C_ST_RUN
  KP_HOSPITAL_C_FACILITY_ST_RUN
  SP_GHANA_ST_RUN
  SP_GHANA_COMMUNITY_RUN
)

for var in "${required_vars[@]}"; do
  value="${!var:-}"
  if [[ -z "$value" || "$value" == *PASTE* ]]; then
    echo "ERROR: Set $var to the exact completed v1.1.2 run directory." >&2
    exit 1
  fi
  if [[ ! -d "$value" ]]; then
    echo "ERROR: Directory not found for $var: $value" >&2
    exit 1
  fi
done

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT/runs" "$OUT/manuscript_figures" "$OUT/reproducibility_scripts"

copy_run() {
  local label="$1"
  local src="$2"
  local dst="$OUT/runs/$label"
  mkdir -p "$dst"
  for sub in audit tables figures report; do
    if [[ -d "$src/$sub" ]]; then
      cp -R "$src/$sub" "$dst/"
    fi
  done
}

copy_run "01_kpneumoniae_full_st_core" "$KP_FULL_ST_RUN"
copy_run "02_kpneumoniae_full_facility_st" "$KP_FULL_FACILITY_ST_RUN"
copy_run "03_kpneumoniae_hospital_c_st" "$KP_HOSPITAL_C_ST_RUN"
copy_run "04_kpneumoniae_hospital_c_facility_st" "$KP_HOSPITAL_C_FACILITY_ST_RUN"
copy_run "05_spneumoniae_ghana_st_core" "$SP_GHANA_ST_RUN"
copy_run "06_spneumoniae_ghana_community" "$SP_GHANA_COMMUNITY_RUN"

for root in "$FIGURE3_ROOT" "$FIGURE4_ROOT"; do
  if [[ -d "$root" ]]; then
    cp -R "$root" "$OUT/manuscript_figures/"
  fi
done

configs=(
  biorxiv/data/south-africa-baby-germs/configs/core-with-ST-context-only_config.yaml
  biorxiv/data/south-africa-baby-germs/configs/transmission-with-core-context_config.yaml
  biorxiv/data/hospitalC_kpneumo/transmission-with-core-context_config-ST.yaml
  biorxiv/data/hospitalC_kpneumo/transmission-with-core-context_config-Facility-ST.yaml
  biorxiv/data/ghana-spneumo-study/configs/core-with-ST-context-only_config.yaml
  biorxiv/data/ghana-spneumo-study/configs/community-context_config.yaml
)
mkdir -p "$OUT/configs"
for cfg in "${configs[@]}"; do
  if [[ ! -f "$cfg" ]]; then
    echo "ERROR: Missing configuration: $cfg" >&2
    exit 1
  fi
  cp "$cfg" "$OUT/configs/"
done

if [[ -d "$REPRO/scripts" ]]; then
  find "$REPRO/scripts" -maxdepth 1 -type f \
    \( -name '*.py' -o -name '*instructions*.txt' \) \
    -exec cp {} "$OUT/reproducibility_scripts/" \;
fi

cat > "$OUT/SOURCE_MANIFEST.txt" <<EOF
SNP2Cluster-Py supplementary source bundle
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Software version: $(python -m src.snp2cluster.cli version)
Git commit: $(git rev-parse HEAD)

Runs:
01 $KP_FULL_ST_RUN
02 $KP_FULL_FACILITY_ST_RUN
03 $KP_HOSPITAL_C_ST_RUN
04 $KP_HOSPITAL_C_FACILITY_ST_RUN
05 $SP_GHANA_ST_RUN
06 $SP_GHANA_COMMUNITY_RUN

Figure roots:
Figure 3: $FIGURE3_ROOT
Figure 4: $FIGURE4_ROOT
EOF

find "$OUT" -name '.DS_Store' -delete
zip -rq "$ZIP" "$OUT"
echo "Created: $ZIP"
du -h "$ZIP"
