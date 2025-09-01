from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from PIL import Image
import requests
import json
import base64
import os
import io

# Ollama'daki modelin API adresi
OLLAMA_API_URL = "http://localhost:11434/api/chat"

# Kullanılacak modellerin adları
VISION_MODEL_NAME = "llama3.2-vision:11b"
TEXT_MODEL_NAME = "llama-3p1-8b"

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def grade_handwritten_answer(request):
    """
    Gelen el yazısı resmini Llama Vision ile metne çevirir,
    ardından Llama-3p1-8b ile notlandırır.
    """
    handwritten_image = request.FILES.get('image')
    question_text = request.data.get('question')
    reference_text = request.data.get('reference_text')
    grading_criteria = request.data.get('criteria')

    if not all([handwritten_image, question_text, reference_text, grading_criteria]):
        return Response(
            {"detail": "Please provide 'image', 'question', 'reference_text', and 'criteria'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Gelen resmi base64 formatına çevir
        image_bytes = handwritten_image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        return Response({"detail": f"Error processing image file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 1. Adım: Llama Vision ile el yazısını metne çevir ---
    try:
        ocr_prompt = "Transcribe the handwritten text in the image. Do not add any extra information or analysis. Just return the raw text."
        ocr_data = {
            "model": VISION_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": ocr_prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }
        ocr_response = requests.post(OLLAMA_API_URL, json=ocr_data, timeout=120)
        ocr_response.raise_for_status()
        ocr_output = json.loads(ocr_response.text)
        student_answer_text = ocr_output['message']['content'].strip()
    except Exception as e:
        return Response(
            {"detail": f"Handwritten text transcription failed. Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # --- 2. Adım: Llama-3p1-8b ile notlandırma yap ---
    grading_prompt = f"""
    You are a teacher grading an exam paper. Your task is to grade the student's answer based on the provided reference text, question, and grading criteria.
    
    You must provide your answer in a JSON format with 'grade' and 'reason' keys.
    
    Reference Text:
    ---
    {reference_text}
    ---
    
    Question:
    ---
    {question_text}
    ---
    
    Grading Criteria:
    ---
    {grading_criteria}
    ---
    
    Student's Answer:
    ---
    {student_answer_text}
    ---
    
    Grading (JSON Only):
    """

    grading_data = {
        "model": TEXT_MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": grading_prompt,
            }
        ],
        "stream": False
    }

    try:
        grading_response = requests.post(OLLAMA_API_URL, json=grading_data, timeout=180)
        grading_response.raise_for_status()
        llm_output = json.loads(grading_response.text)
        grading_result_str = llm_output['message']['content']
        
        # JSON çıktısını doğrulamayı deneyelim
        try:
            grading_result_json = json.loads(grading_result_str)
        except json.JSONDecodeError:
            grading_result_json = {"error": "Invalid JSON format from LLM", "raw_response": grading_result_str}

        final_response = {
            "transcribed_answer": student_answer_text,
            "grading": grading_result_json,
        }
        
        return Response(final_response, status=status.HTTP_200_OK)

    except requests.exceptions.RequestException as e:
        return Response(
            {"detail": f"Grading model connection error or not ready. Error: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response({"detail": f"An unexpected error occurred during grading: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)