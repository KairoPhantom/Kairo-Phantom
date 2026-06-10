#!/usr/bin/env bash
# ==============================================================================
# Kairo Phantom - LlamaFactory LoRA Fine-Tuning Pipeline
# ==============================================================================
# This script automates:
# 1. Bootstrapping dependencies (LlamaFactory, PyTorch, llama.cpp, etc.)
# 2. Registering the dataset inside LlamaFactory
# 3. Running LoRA SFT on Qwen2.5-3B-Instruct
# 4. Merging LoRA adapters with the base model weights
# 5. Converting the merged weights to GGUF format and quantizing to Q4_K_M
# 6. Registering the final model in local Ollama instance
# 7. Initiating the evaluation benchmark suite
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TRAINING_DATA_DIR="${PROJECT_ROOT}/training_data"
MODEL_DIR="${PROJECT_ROOT}/models"

echo "🚀 Starting KairoDocWriter-3B Fine-Tuning Pipeline..."

# 1. Dependency Validation & Bootstrap
echo "📦 Step 1: Bootstrapping dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found in PATH." >&2
    exit 1
fi

python3 -m venv "${SCRIPT_DIR}/.venv"
source "${SCRIPT_DIR}/.venv/bin/activate"

pip install --upgrade pip
pip install "llamafactory[torch,metrics]>=0.9.1"
pip install openpyxl python-docx python-pptx pydantic

# 2. Register Dataset
echo "📝 Step 2: Registering custom dataset..."
# Locate LlamaFactory site-packages directory to write to its dataset_info.json
LF_PATH=$(python -c "import os, llamafactory; print(os.path.dirname(llamafactory.__file__))")
LF_DATA_DIR="${LF_PATH}/data"

echo "Copying training dataset to ${LF_DATA_DIR}..."
cp "${TRAINING_DATA_DIR}/kairo_docops_3500.jsonl" "${LF_DATA_DIR}/"

echo "Updating LlamaFactory dataset_info.json..."
python3 -c "
import json
path = '${LF_DATA_DIR}/dataset_info.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['kairo_docops_3500'] = {
    'file_name': 'kairo_docops_3500.jsonl',
    'columns': {
        'prompt': 'instruction',
        'query': 'input',
        'response': 'output'
    }
}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"

# 3. Execute LoRA Fine-Tuning
echo "🔥 Step 3: Triggering LlamaFactory SFT training..."
mkdir -p "${MODEL_DIR}"
llamafactory-cli train "${SCRIPT_DIR}/kairo_lora_config.yaml"

# 4. Merge LoRA Adapters
echo "🔄 Step 4: Merging LoRA adapters with base model..."
llamafactory-cli export \
    --model_name_or_path Qwen/Qwen2.5-3B-Instruct \
    --adapter_name_or_path "${MODEL_DIR}/kairo-docwriter-3b-lora" \
    --export_dir "${MODEL_DIR}/kairo-docwriter-3b-merged" \
    --export_size 2 \
    --export_device cpu \
    --export_legacy_format false

# 5. GGUF Compilation & Quantization (llama.cpp)
echo "🧱 Step 5: Compiling merged HF weights to GGUF..."
if [ ! -d "${SCRIPT_DIR}/llama.cpp" ]; then
    echo "Cloning llama.cpp for model compilation..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "${SCRIPT_DIR}/llama.cpp"
    pip install -r "${SCRIPT_DIR}/llama.cpp/requirements.txt"
fi

python3 "${SCRIPT_DIR}/llama.cpp/convert_hf_to_gguf.py" \
    "${MODEL_DIR}/kairo-docwriter-3b-merged" \
    --outfile "${MODEL_DIR}/kairo-docwriter-3b-unquantized.gguf"

echo "Quantizing GGUF to Q4_K_M..."
# Build llama.cpp quantize tool if not built
if [ ! -f "${SCRIPT_DIR}/llama.cpp/llama-quantize" ]; then
    echo "Building llama.cpp utilities..."
    make -C "${SCRIPT_DIR}/llama.cpp" llama-quantize
fi

"${SCRIPT_DIR}/llama.cpp/llama-quantize" \
    "${MODEL_DIR}/kairo-docwriter-3b-unquantized.gguf" \
    "${MODEL_DIR}/kairo-docwriter-3b-Q4_K_M.gguf" \
    Q4_K_M

# 6. Register with Ollama
echo "🦙 Step 6: Registering model with Ollama..."
cat <<EOF > "${MODEL_DIR}/Modelfile"
FROM ${MODEL_DIR}/kairo-docwriter-3b-Q4_K_M.gguf
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
EOF

if command -v ollama &> /dev/null; then
    ollama create kairo-docwriter-3b -f "${MODEL_DIR}/Modelfile"
    echo "✅ Successfully registered kairo-docwriter-3b in Ollama!"
else
    echo "⚠️ Warning: Ollama not found in PATH. Please run: ollama create kairo-docwriter-3b -f ${MODEL_DIR}/Modelfile manually once Ollama is installed."
fi

# 7. Run Verification Benchmark Suite
echo "📊 Step 7: Triggering verification benchmark suite..."
python3 "${SCRIPT_DIR}/eval_model.py"

echo "🎉 All SPRINT 7 tasks completed successfully!"
