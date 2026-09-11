import json 
import torch 
from transformers import AutoModelForCausalLM, AutoTokenizer 
from peft import PeftModel 

BASE_MODEL_ID = "Qwen/Qwen3-0.6B"
LORA_ADAPTER_ID = "sandeeppanem/qwen3-0.6b-resume-json"
TORCH_DTYPE = torch.float16

def load_model():
    base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL_ID, 
                                                      torch_dtype = TORCH_DTYPE,
                                                      device_map = 'auto',
                                                      trust_remote_code = True,)
    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_ID)
    model.eval()
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(LORA_ADAPTER_ID, trust_remote_code = True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    return model, tokenizer 


def parse_resume(model, tokenizer, resume_text: str) -> dict:
    system_prompt = (
    "You are an expert resume parser. Extract structured information from "
    "resumes and return ONLY valid JSON. Do not include explanations or extra text."
)

    user_prompt = f"Resume:\n{resume_text}"


    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt = True,
        tokenize = False,
        enable_thinking = False
    )
    inputs = tokenizer(prompt, return_tensors = 'pt').to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample = False,
            pad_token_id= tokenizer.eos_token_id
        )
    assistant_response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    try:
        parsed_json = json.loads(assistant_response)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Invalid JSON returned: {e}")
        print(f"Raw response:\n{assistant_response}")
        return {"error": "Failed to parse JSON", "raw": assistant_response}


if __name__ == "__main__":
    sample_resume = """
    John Doe
    Senior Software Engineer
    Email: john@example.com
    Phone: 555-1234
    
    EXPERIENCE
    Senior Software Engineer at Tech Corp (2020 - Present)
    - Built high-performance REST APIs using FastAPI
    - Led a team of 5 engineers
    - Implemented Redis caching to improve response times
    
    Software Engineer at Startup Inc (2017 - 2020)
    - Developed backend services with Python and PostgreSQL
    - Wrote unit and integration tests
    
    EDUCATION
    BS Computer Science, State University (2013 - 2017)
    
    SKILLS
    Python, FastAPI, Redis, PostgreSQL, Docker, Kubernetes
    """
    print("=" * 60)
    print("Loading model...")
    print("=" * 60)
    model, tokenizer = load_model()
    print("\n" + "=" * 60)
    print("Parsing resume...")
    print("=" * 60)
    result = parse_resume(model, tokenizer, sample_resume)
    print("\n" + "=" * 60)
    print("Result:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    


