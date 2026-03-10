"""finetune/export_to_ollama.py — Merge LoRA adapter and create Ollama model.

Merges the fine-tuned LoRA adapter back into the base model, saves as
full-precision, then creates an Ollama Modelfile and registers it as 'kirn:0.5b'.
"""

import os
import sys
import subprocess
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = os.path.join(os.path.dirname(__file__), "output")
MERGED_DIR = os.path.join(os.path.dirname(__file__), "merged_model")
OLLAMA_MODEL_NAME = "kirn:0.5b"


def main():
    print(f"🔧 Loading base model: {BASE_MODEL}")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    if not os.path.exists(ADAPTER_DIR):
        print(f"❌ No adapter found at {ADAPTER_DIR}. Run train.py first!")
        sys.exit(1)

    print(f"🔗 Loading LoRA adapter from {ADAPTER_DIR}")
    model = PeftModel.from_pretrained(model, ADAPTER_DIR)

    print("🔀 Merging LoRA weights into base model...")
    model = model.merge_and_unload()

    print(f"💾 Saving merged model to {MERGED_DIR}")
    os.makedirs(MERGED_DIR, exist_ok=True)
    model.save_pretrained(MERGED_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_DIR)

    # Create Ollama Modelfile
    modelfile_path = os.path.join(os.path.dirname(__file__), "Modelfile")
    modelfile_content = f"""# Kirn Fine-tuned Model
FROM {os.path.abspath(MERGED_DIR)}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048

SYSTEM \"\"\"You are Kirn, a sharp and capable offline AI assistant running on the user's device. You have a confident, no-fluff personality — you get things done. You are capable of executing any task by writing and running shell commands. When asked to achieve a goal, use the run_terminal_command tool. If a command fails, interpret the error and run corrected commands until the goal is achieved. Do not use sudo or interactive commands. Take small, logical steps.\"\"\"
"""

    with open(modelfile_path, "w") as f:
        f.write(modelfile_content)

    print(f"📝 Created Ollama Modelfile at {modelfile_path}")
    print(f"\n🚀 To register with Ollama, run:")
    print(f"   ollama create {OLLAMA_MODEL_NAME} -f {modelfile_path}")
    print(f"\n   Then update kirn/config.py:")
    print(f"   MODEL = '{OLLAMA_MODEL_NAME}'")

    # Try to auto-register
    try:
        print(f"\n⏳ Attempting to register with Ollama...")
        result = subprocess.run(
            ["ollama", "create", OLLAMA_MODEL_NAME, "-f", modelfile_path],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print(f"✅ Model registered as '{OLLAMA_MODEL_NAME}' in Ollama!")
            print(f"   Test it: ollama run {OLLAMA_MODEL_NAME}")
        else:
            print(f"⚠️  Ollama registration failed: {result.stderr}")
            print(f"   Try manually: ollama create {OLLAMA_MODEL_NAME} -f {modelfile_path}")
    except FileNotFoundError:
        print("⚠️  Ollama not found. Register manually after installing Ollama.")
    except subprocess.TimeoutExpired:
        print("⚠️  Ollama registration timed out. Try manually.")


if __name__ == "__main__":
    main()
