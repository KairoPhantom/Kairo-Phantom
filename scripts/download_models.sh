#!/usr/bin/env bash
#
# scripts/download_models.sh
#
# Phase 0.6: Pre-download the fastembed all-MiniLM-L6-v2 model for air-gapped
# / offline use. The model is 80MB ONNX, CPU-only, MIT license.
#
# Once cached in ~/.cache/, subsequent runs of phantom-core with
# --features local-embeddings work fully offline.
#
# Usage:
#   ./scripts/download_models.sh           # download to default cache
#   CACHE_DIR=/custom/path ./scripts/download_models.sh  # custom location
#
set -euo pipefail

CACHE_DIR="${CACHE_DIR:-$HOME/.cache}"

echo "=== Kairo Phantom — Model Download Script ==="
echo "Target: fastembed all-MiniLM-L6-v2 (384-dim ONNX, ~80MB, CPU, MIT)"
echo "Cache:  ${CACHE_DIR}"
echo ""

# Method 1: Use fastembed-rs to download via a tiny Rust program
# Method 2: Direct HuggingFace download (fallback)
#
# We try Method 1 first (most reliable, uses the same code path as production),
# then fall back to Method 2 (direct download from HuggingFace).

# ── Method 1: fastembed-rs download ──
download_via_fastembed() {
    echo "[1/2] Attempting download via fastembed-rs…"
    local tmpdir
    tmpdir=$(mktemp -d)
    cat > "${tmpdir}/Cargo.toml" << 'CARGO_TOML'
[package]
name = "model_downloader"
version = "0.1.0"
edition = "2021"

[dependencies]
fastembed = "4"
CARGO_TOML

    cat > "${tmpdir}/src/main.rs" << 'RUST_SRC'
use fastembed::{EmbeddingModel, InitOptions, TextEmbedding};

fn main() {
    println!("Downloading all-MiniLM-L6-v2 model…");
    let model = TextEmbedding::try_new(InitOptions {
        model_name: EmbeddingModel::AllMiniLML6V2,
        show_download_progress: true,
        ..Default::default()
    }).expect("Failed to init fastembed model");

    // Generate a test embedding to confirm the model works
    let result = model.embed(vec!["test embedding"], None)
        .expect("Failed to generate embedding");
    println!("✅ Model downloaded and verified: {} dims", result[0].len());
}
RUST_SRC
    mkdir -p "${tmpdir}/src"

    if cargo run --manifest-path "${tmpdir}/Cargo.toml" 2>&1; then
        echo "✅ Model downloaded via fastembed-rs"
        rm -rf "${tmpdir}"
        return 0
    else
        echo "⚠️  fastembed-rs download failed, trying direct HuggingFace download…"
        rm -rf "${tmpdir}"
        return 1
    fi
}

# ── Method 2: Direct HuggingFace download ──
download_via_huggingface() {
    echo "[2/2] Attempting direct HuggingFace download…"
    local model_dir="${CACHE_DIR}/fastembed/models--Qdrant--all-MiniLM-L6-v2-onnx"
    mkdir -p "${model_dir}"

    local base_url="https://huggingface.co/Qdrant/all-MiniLM-L6-v2-onnx/resolve/main"

    # Download model.onnx (the main model file)
    local onnx_file="${model_dir}/model.onnx"
    if [ ! -f "${onnx_file}" ]; then
        echo "  Downloading model.onnx (~80MB)…"
        if curl -L -o "${onnx_file}" "${base_url}/model.onnx"; then
            echo "  ✅ model.onnx downloaded"
        else
            echo "  ❌ Failed to download model.onnx"
            return 1
        fi
    else
        echo "  model.onnx already exists, skipping"
    fi

    # Download tokenizer files
    for f in tokenizer.json tokenizer_config.json config.json special_tokens_map.json vocab.txt; do
        local dest="${model_dir}/${f}"
        if [ ! -f "${dest}" ]; then
            echo "  Downloading ${f}…"
            curl -sL -o "${dest}" "${base_url}/${f}" || true
        fi
    done

    echo "✅ Model files downloaded to ${model_dir}"
    echo ""
    echo "NOTE: For fastembed to find these files, you may need to set:"
    echo "  export FASTEMBED_CACHE_DIR=${model_dir}"
    echo ""
    echo "Verify with:"
    echo "  cargo test --lib -p phantom-core embedding --features local-embeddings"
    return 0
}

# ── Main ──
if download_via_fastembed; then
    echo ""
    echo "=== Model download complete ==="
    echo "The model is cached in ${CACHE_DIR}"
    echo "phantom-core with --features local-embeddings will now work offline."
    echo ""
    echo "Verify:"
    echo "  cargo test --lib -p phantom-core embedding --features local-embeddings"
    exit 0
fi

if download_via_huggingface; then
    echo ""
    echo "=== Model download complete (via HuggingFace) ==="
    exit 0
fi

echo ""
echo "❌ Both download methods failed."
echo "   Check your network connection and try again."
echo "   If you are behind a proxy, set HTTPS_PROXY and retry."
exit 1