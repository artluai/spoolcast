#!/usr/bin/env bash
# render_with_audit.sh — wrapper that renders a spoolcast session, runs the
# render audit, and retries (up to N times) if the audit fails. "Done" is
# defined as "audit passed," not "render command returned 0."
#
# Usage:
#   scripts/render_with_audit.sh <session> [<output.mp4>] [--max-retries N]
#
# Behavior:
#   - Invokes `npx remotion render spoolcast-pilot <output>` for the session.
#   - On success, runs `scripts/audit_render.py --session <s> --mp4 <out>`.
#   - If the audit passes, exits 0.
#   - If the audit fails, exits 2 WITHOUT auto-retrying — an agent reviewing
#     the output decides whether to adjust and re-invoke. (A pure loop-forever
#     retry is a waste of kie/compute budget. The retry budget is explicit.)
#   - --max-retries lets an autonomous caller enable the retry loop with a
#     bounded count. Between retries, the caller is expected to diagnose and
#     apply a fix (this script doesn't fix anything itself).
#
# Exit codes:
#   0 — render + audit passed
#   2 — render ran but audit failed
#   3 — render itself failed
#   4 — hit the retry limit without a passing audit

set -u

SESSION="${1:-}"
if [[ -z "$SESSION" ]]; then
    echo "usage: $0 <session> [<output.mp4>] [--max-retries N]" >&2
    exit 1
fi
shift

OUTPUT=""
MAX_RETRIES=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-retries)
            MAX_RETRIES="${2:-1}"
            shift 2
            ;;
        -*)
            echo "unknown flag: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$OUTPUT" ]]; then
                OUTPUT="$1"
                shift
            else
                echo "unexpected arg: $1" >&2
                exit 1
            fi
            ;;
    esac
done

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)"
CONTENT_ROOT="$(cd -- "$REPO_ROOT/.." && pwd)/spoolcast-content"
SESSION_DIR="$CONTENT_ROOT/sessions/$SESSION"

if [[ -z "$OUTPUT" ]]; then
    OUTPUT="$SESSION_DIR/renders/${SESSION}-1.0x.mp4"
fi

echo "[render-with-audit] session=$SESSION mp4=$OUTPUT max_retries=$MAX_RETRIES"

attempt=1
last_failure_sig=""
while [[ $attempt -le $MAX_RETRIES ]]; do
    echo "[render-with-audit] attempt $attempt/$MAX_RETRIES"

    echo "[render-with-audit] rendering..."
    ( cd "$REPO_ROOT" && npx remotion render spoolcast-pilot "$OUTPUT" ) || {
        echo "[render-with-audit] render failed" >&2
        exit 3
    }

    echo "[render-with-audit] running audit..."
    audit_out=$( "$REPO_ROOT/scripts/.venv/bin/python" "$REPO_ROOT/scripts/audit_render.py" --session "$SESSION" --mp4 "$OUTPUT" )
    audit_rc=$?
    echo "$audit_out"

    if [[ $audit_rc -eq 0 ]]; then
        echo "[render-with-audit] PASS"
        exit 0
    fi

    # Same-failure short-circuit: if the failure signature hasn't changed
    # from last attempt, retrying is a waste.
    sig=$( echo "$audit_out" | grep -E '^  - ' | sort | shasum | awk '{print $1}' )
    if [[ -n "$last_failure_sig" && "$sig" == "$last_failure_sig" ]]; then
        echo "[render-with-audit] same failures as previous attempt — short-circuiting retry loop" >&2
        exit 4
    fi
    last_failure_sig="$sig"

    attempt=$((attempt + 1))
done

echo "[render-with-audit] retry limit ($MAX_RETRIES) reached without a passing audit" >&2
exit 4
