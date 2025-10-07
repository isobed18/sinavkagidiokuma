# Sinav Kagidi Okuma

LLM-powered exam grading prototype built during the final week of an internship. The backend uses Django + DRF to orchestrate text grading with local Ollama-hosted Llama 3 models, while an Expo mobile client surfaces single-response, bulk CSV, and experimental image flows.
---

## Demonstration Video

This is a comprehensive, in-depth demo of the prototype's core functionality, including the stable **text/CSV grading APIs** and a look at the experimental **image grading flow**.

> **Important Note:** This video provides detailed context on the current status, including the **known limitations** (e.g., Turkish OCR challenges) and the technical constraints that prevented the full development of certain features as noted in the "Known Limitations & Next Steps" section.

[Watch the Full Prototype Demo and Technical Deep Dive Here](<https://youtu.be/gWGrbw9MuVY>)

---
## Architecture
- Backend: Django 5 project (`sinavkagidi/`) exposing REST endpoints via Django REST Framework.
- Model runner: Local Ollama server that hosts `llama3.1:8b` for grading prompts and `llama3.2-vision:11b` for OCR / structuring attempts.
- Frontend: Expo Router app (`text-grader-app/`) targeting Android/iOS/web with text and image grading tabs.

## Features
- Text grading API (`/api/sinav/grade-text/`) that returns a strict JSON with `grade` and `reason`.
- Bulk CSV grading API (`/api/sinav/grade-multiple-text/`) that appends model feedback for every `student_answer`.
- Experimental handwritten answer grading (`/api/sinav/grade/`) that chains OCR and grading models.
- Full-page ingestion (`/api/sinav/grade-full-page/`) that tries to separate questions and answers from a scanned sheet.
- Robust logging, Markdown-to-JSON cleanup, and helper scripts (`test_grade.py`, `test_full_page.py`) for manual QA.

## Requirements
- Python 3.12+ and pip for the Django project.
- Node.js 20+ and npm for the Expo app.
- Expo CLI (`npx expo`) for local development.
- Ollama 0.3+ running locally with access to Llama 3.1 8B and Llama 3.2 Vision 11B models.
- (Optional) A device or emulator for testing the mobile client.

## Backend Setup
```bash
cd sinavkagidiokuma
python -m venv .venv
.\\.venv\\Scripts\\activate
pip install -r reqs.txt
# ensure .env contains SECRET_KEY (repository includes a dev value)
python sinavkagidi\\manage.py migrate
python sinavkagidi\\manage.py runserver 0.0.0.0:8000
```

- The backend assumes the Ollama API is reachable at `http://localhost:11434/api/chat`. Adjust `OLLAMA_API_URL`, `VISION_MODEL_NAME`, or `TEXT_MODEL_NAME` inside `sinavkagidi/sinavokuyucu/views.py` if you host models elsewhere.
- Update `ALLOWED_HOSTS` in `sinavkagidi/otosinavkagidi/settings.py` when serving over the network.

## Local LLM Setup
```bash
ollama pull llama3.1:8b
ollama pull llama3.2-vision:11b
ollama serve
```

- The grading pipeline relies on JSON-formatted answers (`format: "json"`) from the text model.
- Vision outputs are parsed into structured prompts; inconsistent OCR may require retries.

## Frontend Setup
```bash
cd text-grader-app
npm install
npx expo start
```

- Ensure the backend URL matches your network IP. Update the constants in `text-grader-app/constants/constants.ts`, `app/(tabs)/grade.tsx`, and `app/(tabs)/image-grade.tsx`.
- The Grade tab supports single-answer JSON calls and CSV uploads (using Expo DocumentPicker). The Image tab targets the OCR flow but is currently experimental.

## API Reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/sinav/grade-text/` | Grade a single textual answer. |
| POST | `/api/sinav/grade-multiple-text/` | Grade many answers supplied via CSV (`;` delimiter). |
| POST | `/api/sinav/grade/` | Upload a handwriting photo; runs OCR then grading. |
| POST | `/api/sinav/grade-full-page/` | Upload a full page; returns raw OCR text and LLM-structured Q/A pairs. |

### Example: grade-text
```bash
curl -X POST http://localhost:8000/api/sinav/grade-text/ \
  -H "Content-Type: application/json" \
  -d '{
        "question": "Metni ozetle.",
        "reference_text": "Dogru cevap ornegi...",
        "criteria": "Tam yanit 10, kismi 5, hatali 0",
        "answer": "Ogrenci cevabi burada."
      }'
```

### Example: grade-multiple-text
- Upload `text_answers.csv` with `;` delimiter and a `student_answer` column:
```bash
curl -X POST http://localhost:8000/api/sinav/grade-multiple-text/ \
  -F "csv_file=@text_answers.csv" \
  -F "question=..." \
  -F "reference_text=..." \
  -F "criteria=..."
```
- The response downloads a CSV that adds `llm_grade`, `llm_reason`, and `processing_time_ms`.

### Example: grade (handwritten image)
```bash
curl -X POST http://localhost:8000/api/sinav/grade/ \
  -F "image=@sample_answer.jpeg" \
  -F "question=..." \
  -F "reference_text=..." \
  -F "criteria=..."
```

### Example: grade-full-page
```bash
curl -X POST http://localhost:8000/api/sinav/grade-full-page/ \
  -F "image=@scanned_sheet.jpeg"
```

## CSV Format
- The pipeline expects a semicolon-delimited file with a header row.
- Required column: `student_answer`. Additional metadata columns are preserved.
- The output CSV is encoded in UTF-8 and streamed back via `FileResponse`.

## Manual Test Scripts
- `test_grade.py` exercises the handwritten grading endpoint with configurable prompts.
- `test_full_page.py` tests full-page ingestion.
- Both scripts assume the backend runs on `http://127.0.0.1:8000` and that sample images are present in the repository root.

## Known Limitations & Next Steps
- Turkish handwriting OCR remains the weakest link. Available public models (e.g., Microsoft TrOCR, Llama Vision) lack accuracy without domain-specific fine-tuning.
- Planned direction: build or source a Turkish handwritten dataset, generate synthetic samples, and train an OCR model tailored to the target exams.
- Current focus is therefore on text-based grading and CSV batch processing, which are stable and production-ready prototypes.

## Background Notes
- **Video description recap:** The project currently grades answers with `llama3.1:8b`. Image support is unreliable because a mixed printed/handwritten Turkish OCR model is missing; synthetic dataset generation is planned, and contributions of Turkish handwriting datasets are welcome.
- **Internship week 4 recap:** Work began with the goal of dual-mode grading (handwritten + digital). Backend and LLM integration landed early, but OCR obstacles and time constraints forced a scope change. After aligning with the mentor, the week closed with a pragmatic focus on text grading and bulk CSV processing, delivering a functional prototype aligned with institutional needs.
