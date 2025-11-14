import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

# List all available models
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)