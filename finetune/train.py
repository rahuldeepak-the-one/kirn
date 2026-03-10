"""finetune/train.py — QLoRA fine-tuning of Qwen2.5-0.5B-Instruct for Kirn.

Uses 4-bit quantization + LoRA adapters via bitsandbytes + peft + trl.
Designed to run on a single NVIDIA RTX 3060 (6GB VRAM).
"""

import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# LoRA hyperparameters
LORA_R = 16           # rank — higher = more capacity, more VRAM
LORA_ALPHA = 32       # scaling factor
LORA_DROPOUT = 0.05

# Training hyperparameters
EPOCHS = 3
LR = 2e-4
BATCH_SIZE = 2
GRAD_ACCUM = 4        # effective batch = BATCH_SIZE * GRAD_ACCUM = 8
MAX_SEQ_LEN = 1024
WARMUP_RATIO = 0.03


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_dataset_from_jsonl(path: str) -> Dataset:
    """Load a JSONL file into a HuggingFace Dataset."""
    examples = []
    with open(path, "r") as f:
        for line in f:
            examples.append(json.loads(line.strip()))
    return Dataset.from_list(examples)


def format_chat(example: dict, tokenizer) -> dict:
    """Convert a messages list into the chat template string."""
    messages = example["messages"]

    # Filter out tool_calls with None content for the template
    clean_messages = []
    for msg in messages:
        if msg["role"] == "assistant" and msg.get("content") is None:
            # Convert tool call into text representation for training
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                tc = tool_calls[0]
                func = tc.get("function", tc)
                content = f'<tool_call>\n{json.dumps({"name": func["name"], "arguments": func["arguments"]})}\n</tool_call>'
                clean_messages.append({"role": "assistant", "content": content})
        else:
            clean_messages.append({"role": msg["role"], "content": msg.get("content", "")})

    text = tokenizer.apply_chat_template(
        clean_messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"🔧 Loading base model: {BASE_MODEL}")

    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Prepare model for QLoRA training
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load datasets
    train_path = os.path.join(DATASET_DIR, "train.jsonl")
    eval_path = os.path.join(DATASET_DIR, "eval.jsonl")

    if not os.path.exists(train_path):
        print("❌ Dataset not found. Run generate_dataset.py first!")
        return

    train_dataset = load_dataset_from_jsonl(train_path)
    eval_dataset = load_dataset_from_jsonl(eval_path) if os.path.exists(eval_path) else None

    # Format using chat template
    train_dataset = train_dataset.map(lambda x: format_chat(x, tokenizer))
    if eval_dataset:
        eval_dataset = eval_dataset.map(lambda x: format_chat(x, tokenizer))

    print(f"📊 Training examples: {len(train_dataset)}")
    if eval_dataset:
        print(f"📊 Evaluation examples: {len(eval_dataset)}")

    # Print a sample
    print(f"\n📝 Sample training text:\n{train_dataset[0]['text'][:500]}...\n")

    # Training config
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_ratio=WARMUP_RATIO,
        logging_steps=5,
        save_strategy="epoch",
        eval_strategy="epoch" if eval_dataset else "no",
        fp16=True,
        max_seq_length=MAX_SEQ_LEN,
        dataset_text_field="text",
        report_to="none",
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        seed=42,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    print("🚀 Starting fine-tuning...")
    trainer.train()

    # Save
    print(f"💾 Saving LoRA adapter to {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("✅ Fine-tuning complete!")
    print(f"   Adapter saved to: {OUTPUT_DIR}")
    print(f"   To merge + export, run: python finetune/export_to_ollama.py")


if __name__ == "__main__":
    main()
