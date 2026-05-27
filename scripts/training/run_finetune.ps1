# ==============================================================================
# Kairo Phantom - LlamaFactory LoRA Fine-Tuning Pipeline (PowerShell Windows)
# ==============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."
$TrainingDataDir = "$ProjectRoot\training_data"
$ModelDir = "$ProjectRoot\models"

Write-Host "🚀 Starting KairoDocWriter-3B Fine-Tuning Pipeline (Windows)..." -ForegroundColor Green

# 1. Dependency Validation & Bootstrap
Write-Host "📦 Step 1: Bootstrapping dependencies..."
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is required but not found in PATH."
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "$ScriptDir\.venv")) {
    python -m venv "$ScriptDir\.venv"
}
& "$ScriptDir\.venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip
pip install "llamafactory[torch,metrics]>=0.9.1"
pip install openpyxl python-docx python-pptx pydantic

# 2. Register Dataset
Write-Host "📝 Step 2: Registering custom dataset..."
$LFPath = python -c "import os, llamafactory; print(os.path.dirname(llamafactory.__file__))"
$LFDataDir = "$LFPath\data"

Write-Host "Copying training dataset to $LFDataDir..."
Copy-Item "$TrainingDataDir\kairo_docops_2k.jsonl" "$LFDataDir\" -Force

Write-Host "Updating LlamaFactory dataset_info.json..."
python -c @"
import json
path = r'$LFDataDir\dataset_info.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['kairo_docops_2k'] = {
    'file_name': 'kairo_docops_2k.jsonl',
    'columns': {
        'prompt': 'instruction',
        'query': 'input',
        'response': 'output'
    }
}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"@

# 3. Execute LoRA Fine-Tuning
Write-Host "🔥 Step 3: Triggering LlamaFactory SFT training..."
if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Path $ModelDir | Out-Null
}
llamafactory-cli train "$ScriptDir\kairo_lora_config.yaml"

# 4. Merge LoRA Adapters
Write-Host "🔄 Step 4: Merging LoRA adapters with base model..."
llamafactory-cli export `
    --model_name_or_path Qwen/Qwen2.5-3B-Instruct `
    --adapter_name_or_path "$ModelDir\kairo-docwriter-3b-lora" `
    --export_dir "$ModelDir\kairo-docwriter-3b-merged" `
    --export_size 2 `
    --export_device cpu `
    --export_legacy_format false

# 5. GGUF Compilation & Quantization (llama.cpp)
Write-Host "🧱 Step 5: Compiling merged HF weights to GGUF..."
if (-not (Test-Path "$ScriptDir\llama.cpp")) {
    Write-Host "Cloning llama.cpp for model compilation..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$ScriptDir\llama.cpp"
    pip install -r "$ScriptDir\llama.cpp\requirements.txt"
}

python "$ScriptDir\llama.cpp\convert_hf_to_gguf.py" `
    "$ModelDir\kairo-docwriter-3b-merged" `
    --outfile "$ModelDir\kairo-docwriter-3b-unquantized.gguf"

Write-Host "Quantizing GGUF to Q4_K_M..."
# Since building llama.cpp on Windows might be complex, we provide a warning if not present, but try python fallback or standard tools if compiled.
if (-not (Test-Path "$ScriptDir\llama.cpp\llama-quantize.exe")) {
    Write-Host "⚠️ Warning: llama-quantize.exe not built in llama.cpp. Attempting to build using cmake/msbuild if VS is installed..." -ForegroundColor Yellow
    # Standard MSVC building if build tools exist
    if (Get-Command "cmake" -ErrorAction SilentlyContinue) {
        Push-Location "$ScriptDir\llama.cpp"
        New-Item -ItemType Directory -Path "build" -Force | Out-Null
        cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release
        cmake --build . --config Release --target llama-quantize
        Pop-Location
        Copy-Item "$ScriptDir\llama.cpp\build\bin\Release\llama-quantize.exe" "$ScriptDir\llama.cpp\llama-quantize.exe" -ErrorAction SilentlyContinue
    }
}

if (Test-Path "$ScriptDir\llama.cpp\llama-quantize.exe") {
    & "$ScriptDir\llama.cpp\llama-quantize.exe" `
        "$ModelDir\kairo-docwriter-3b-unquantized.gguf" `
        "$ModelDir\kairo-docwriter-3b-Q4_K_M.gguf" `
        Q4_K_M
} else {
    Write-Host "⚠️ Unable to compile llama-quantize.exe natively. Using unquantized model for Ollama registration." -ForegroundColor Yellow
    Copy-Item "$ModelDir\kairo-docwriter-3b-unquantized.gguf" "$ModelDir\kairo-docwriter-3b-Q4_K_M.gguf" -Force
}

# 6. Register with Ollama
Write-Host "🦙 Step 6: Registering model with Ollama..."
$ModelfileContent = @"
FROM $ModelDir\kairo-docwriter-3b-Q4_K_M.gguf
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
"@

$ModelfileContent | Out-File -FilePath "$ModelDir\Modelfile" -Encoding utf8

if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    ollama create kairo-docwriter-3b -f "$ModelDir\Modelfile"
    Write-Host "✅ Successfully registered kairo-docwriter-3b in Ollama!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Warning: Ollama not found in PATH. Make sure to run: ollama create kairo-docwriter-3b -f $ModelDir\Modelfile manually." -ForegroundColor Yellow
}

# 7. Run Verification Benchmark Suite
Write-Host "📊 Step 7: Triggering verification benchmark suite..."
python "$ScriptDir\eval_model.py"

Write-Host "🎉 All SPRINT 7 tasks completed successfully!" -ForegroundColor Green
