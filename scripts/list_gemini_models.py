#!/usr/bin/env python3
"""
Lista os modelos disponíveis no Gemini.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key: ...{api_key[-8:]}")

genai.configure(api_key=api_key)

print("\n" + "="*60)
print("MODELOS DISPONÍVEIS:")
print("="*60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✓ {model.name}")
        print(f"  Display: {model.display_name}")
        print(f"  Description: {model.description}")
