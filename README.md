# Battery Datasheet Extraction Project

This project extracts information from battery PDFs using LLMs. It then puts the data in a knowledge graph and validates it.

## How it works

1. PDF text extraction
2. LLM extraction (using Gemini, OpenAI, or local Ollama)
3. Evaluate results
4. Build knowledge graph
5. Validate data (hallucination detection)

## Files

- main.py: start the script
- config.py: settings and api keys
- requirements.txt: libraries needed
- documents/: pdf files
- src/: source code
- outputs/: result files

## Setup

1. Install requirements:
   pip install -r requirements.txt

2. Configure provider in .env:
   - Gemini: set GEMINI_API_KEY and use a model like gemini-2.5-flash
   - OpenAI: set OPENAI_API_KEY and use a model like gpt-4o-mini
   - Ollama local: no cloud key needed

## Ollama local setup (macOS)

1. Install Ollama:
   brew install --cask ollama

2. Start Ollama service:
   ollama serve

3. In another terminal, pull a local model:
   ollama pull llama3.1:8b

4. Set .env for Ollama:
   LLM_MODEL=ollama/llama3.1:8b
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_API_KEY=ollama

## Usage

Run everything:
python main.py --all

Run only extraction:
python main.py --extract

Run only validation:
python main.py --validate

You can choose the model:
python main.py --all --model gemini-2.5-flash

With Ollama local:
python main.py --all --model ollama/llama3.1:8b