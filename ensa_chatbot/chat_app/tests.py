from django.test import TestCase

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch


from pathlib import Path

# Go up 2 levels
current_path = Path.cwd()
target_file = current_path.parents[1]


base_model = "mistralai/Mistral-7B-Instruct-v0.2"
lora_path = target_file / "Models" / "mistral-school-finetuned"
tokenizer = AutoTokenizer.from_pretrained(base_model)

model = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype=torch.float16,
    device_map="auto"
)

model = PeftModel.from_pretrained(model, lora_path.as_posix())
model.eval()

prompt = "Explain the timetable of the Computer Science department"

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    output = model.generate(
        **inputs,
        max_length=300,
        temperature=0.3,
        do_sample=True
    )

print(tokenizer.decode(output[0], skip_special_tokens=True))
