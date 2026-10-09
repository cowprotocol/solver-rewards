#!/usr/bin/env bash
# Interactive wrapper around `python -m src.verification.compare_output_files`.
#
# Fetches solver-rewards, protocol-fee, and partner-fees data directly from
# Dune for the given accounting period, then collects the three Safe multisend
# calldata blobs (COW transfers, native transfers, overdrafts) via your
# clipboard - NOT by pasting into the terminal - and runs the verification.
#
# Why the clipboard: these calldata blobs are huge single "lines" of hex.
# Terminals read a line of typed/pasted input in canonical mode, which on
# most systems silently truncates a single line past ~1024 bytes - so pasting
# a multi-thousand-character blob directly into a `read` prompt gets cut off
# well before the end, no matter how the prompt loop is written. Reading the
# clipboard directly (pbpaste/xclip/wl-paste) bypasses that entirely.
#
# Usage:
#   scripts/verify_payout.sh --start 2026-09-08 --network bnb
#
# At each prompt, copy the relevant calldata (or its full JSON, as copied
# from the Safe UI) to your clipboard, then press Enter. If no clipboard tool
# is found, you'll instead be asked for a path to a file containing it.

set -euo pipefail

usage() {
    echo "Usage: $0 --start YYYY-MM-DD --network NAME [-- EXTRA_ARGS...]" >&2
    exit 2
}

START=""
NETWORK=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)
            START="$2"
            shift 2
            ;;
        --network)
            NETWORK="$2"
            shift 2
            ;;
        --)
            shift
            EXTRA_ARGS=("$@")
            break
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

[[ -z "$START" || -z "$NETWORK" ]] && usage

detect_clipboard_cmd() {
    if command -v pbpaste >/dev/null 2>&1; then
        echo "pbpaste"
    elif command -v wl-paste >/dev/null 2>&1; then
        echo "wl-paste"
    elif command -v xclip >/dev/null 2>&1; then
        echo "xclip -selection clipboard -o"
    elif command -v xsel >/dev/null 2>&1; then
        echo "xsel --clipboard --output"
    fi
}

CLIPBOARD_CMD="$(detect_clipboard_cmd)"

# Writes one calldata blob to $2, sourced from the clipboard (preferred) or a
# file path (fallback) - never from a paste into this terminal. $1 is a label
# used in the prompt text.
collect_calldata() {
    local label="$1"
    local dest="$2"

    if [[ -n "$CLIPBOARD_CMD" ]]; then
        read -r -p "Copy the $label calldata (or its full JSON) to your clipboard, then press Enter: " _
        $CLIPBOARD_CMD > "$dest"
    else
        echo "No clipboard tool found (pbpaste/xclip/xsel/wl-paste)."
        read -r -p "Path to a file containing the $label calldata (or its full JSON): " path
        if [[ -z "$path" ]]; then
            echo "error: a file path is required" >&2
            exit 2
        fi
        cp "$path" "$dest"
    fi
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

COW_CALLDATA_FILE="$WORKDIR/cow_transfers.txt"
NATIVE_CALLDATA_FILE="$WORKDIR/native_transfers.txt"
OVERDRAFT_CALLDATA_FILE="$WORKDIR/overdraft.txt"

collect_calldata "COW-transfers" "$COW_CALLDATA_FILE"
echo
collect_calldata "native-transfers" "$NATIVE_CALLDATA_FILE"

OVERDRAFT_ARGS=()
echo
read -r -p "Any overdraft transactions to verify this period? [y/N] " has_overdraft
if [[ "$has_overdraft" =~ ^[Yy] ]]; then
    collect_calldata "overdrafts" "$OVERDRAFT_CALLDATA_FILE"
    OVERDRAFT_ARGS=(--overdraft-calldata-file "$OVERDRAFT_CALLDATA_FILE")
fi

echo
echo "Running verification for network=$NETWORK start=$START ..."
echo

python3 -m src.verification.compare_output_files \
    --start "$START" \
    --network "$NETWORK" \
    --cow-transfers-calldata-file "$COW_CALLDATA_FILE" \
    --native-transfers-calldata-file "$NATIVE_CALLDATA_FILE" \
    ${OVERDRAFT_ARGS[@]+"${OVERDRAFT_ARGS[@]}"} \
    --out-dir . \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
