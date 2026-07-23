"""
train_biomechanics_llm.py — QLoRA Fine-Tuning for Biomechanics & Motion Diagnostics

Fine-tunes Llama-3-8B-Instruct / Mistral-7B on structured 3D kinematic data using QLoRA.
Inputs: Kinematic JSON datasets (angles, velocities, asymmetry, phase events)
Outputs: Clinical diagnostic reports, risk assessment, and corrective exercise prescriptions.

Requirements:
    pip install torch transformers datasets trl peft bitsandbytes accelerate
"""

import os
import json
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# Config
MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"  # or "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "./biomechanics_llama3_qlora"


def prepare_dataset(jsonl_path: str):
    """Load JSONL dataset containing 'input' and 'output' fields."""
    data = []
    with open(jsonl_path, "r") as f:
        for line in f:
            item = json.loads(line)
            # Format as Llama-3 Instruct Prompt
            prompt = (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                f"You are an expert biomechanics researcher and clinical sports scientist.<|eot_id|>\n"
                f"<|start_header_id|>user<|end_header_id|>\n"
                f"{item['input']}<|eot_id|>\n"
                f"<|start_header_id|>assistant<|end_header_id|>\n"
                f"{item['output']}<|eot_id|>"
            )
            data.append({"text": prompt})
    return Dataset.from_list(data)


def train_llm(jsonl_path: str):
    print("[*] Loading 4-bit Quantization Config...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"[*] Loading Base Model: {MODEL_ID}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    model = prepare_model_for_kbit_training(model)

    # QLoRA Target Modules
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    dataset = prepare_dataset(jsonl_path)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        num_train_epochs=3,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        fp16=True,
        save_strategy="epoch",
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("[*] Starting QLoRA Fine-Tuning...")
    trainer.train()

    print(f"[✓] Fine-tuning Complete! Saved adapter model to {OUTPUT_DIR}")
    trainer.model.save_pretrained(OUTPUT_DIR)


if __name__ == "__main__":
    sample_data = "backend/pipeline/biomechanics_training_data.jsonl"
    if os.path.exists(sample_data):
        train_llm(sample_data)
    else:
        print(f"[*] Create training dataset at {sample_data} before training.")
