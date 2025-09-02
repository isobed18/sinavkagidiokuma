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
import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor

# Ollama'daki modelin API adresi
OLLAMA_API_URL = "http://localhost:11434/api/chat"

# Kullanılacak modellerin adları
VISION_MODEL_NAME = "llama3.2-vision:11b"
TEXT_MODEL_NAME = "llama-3p1-8b"


# API 1: Llama Vision + Llama 3 Tek Soruluk Değerlendirme
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
        image_bytes = handwritten_image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        return Response({"detail": f"Error processing image file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 1: Transcribe handwritten text in the image with Llama Vision
    start_time_vision = time.time()
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
    end_time_vision = time.time()
    vision_duration = (end_time_vision - start_time_vision) * 1000

    # Step 2: Grade with Llama-3p1-8b
    start_time_grading = time.time()
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
        
        try:
            grading_result_json = json.loads(grading_result_str)
        except json.JSONDecodeError:
            grading_result_json = {"error": "Invalid JSON format from LLM", "raw_response": grading_result_str}
    except requests.exceptions.RequestException as e:
        return Response(
            {"detail": f"Grading model connection error or not ready. Error: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response({"detail": f"An unexpected error occurred during grading: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    end_time_grading = time.time()
    grading_duration = (end_time_grading - start_time_grading) * 1000

    final_response = {
        "transcribed_answer": student_answer_text,
        "grading": grading_result_json,
        "processing_times_ms": {
            "llama_vision": round(vision_duration, 2),
            "llama_grading": round(grading_duration, 2),
        }
    }
    return Response(final_response, status=status.HTTP_200_OK)

# API 2: Llama Vision + Llama 3 Tam Sayfa İşleme
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def grade_full_page_answers(request):
    """
    Tüm sayfanın fotoğrafını Llama Vision ile ham metne çevirir,
    ardından Llama-3p1-8b ile soruları ve cevapları ayırır.
    """
    full_page_image = request.FILES.get('image')

    if not full_page_image:
        return Response(
            {"detail": "Please provide an 'image' file."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        image_bytes = full_page_image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        return Response({"detail": f"Error processing image file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 1: Llama Vision ile sadece ham metni çevir
    start_time_vision = time.time()
    try:
        extraction_prompt = "Transcribe all text from the image, including questions and answers. Do not add any new text, formatting, or analysis. Just the raw text."
        
        extraction_data = {
            "model": VISION_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": extraction_prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }
        extraction_response = requests.post(OLLAMA_API_URL, json=extraction_data, timeout=240)
        extraction_response.raise_for_status()
        extraction_output = json.loads(extraction_response.text)
        raw_text = extraction_output['message']['content'].strip()
    except Exception as e:
        return Response(
            {"detail": f"Ham metin çevirme (Llama Vision) hatası: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    end_time_vision = time.time()
    vision_duration = (end_time_vision - start_time_vision) * 1000

    # Step 2: Llama-3p1-8b ile ham metni yapılandır
    start_time_structuring = time.time()
    structuring_prompt = f"""
    You are an AI assistant that structures text from an exam paper. Given the raw text from a scanned exam page, your task is to identify and separate the questions and their corresponding answers.
    
    Provide the output in a clear, numbered list format. For each item, use the keys 'question' and 'answer'. Your response should be a JSON array.
    
    Example format:
    [
      {{
        "question": "Question text here.",
        "answer": "Answer text here."
      }},
      {{
        "question": "Another question text.",
        "answer": "Another answer text."
      }}
    ]
    
    Raw text from the page:
    ---
    {raw_text}
    ---
    
    Please provide the JSON array now:
    """

    structuring_data = {
        "model": TEXT_MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": structuring_prompt,
            }
        ],
        "stream": False
    }

    try:
        structuring_response = requests.post(OLLAMA_API_URL, json=structuring_data, timeout=180)
        structuring_response.raise_for_status()
        llm_output = json.loads(structuring_response.text)
        structured_content_str = llm_output['message']['content'].strip()
        
        try:
            structured_content_json = json.loads(structured_content_str)
        except json.JSONDecodeError:
            structured_content_json = {"error": "Invalid JSON format from LLM", "raw_response": structured_content_str}
        
    except requests.exceptions.RequestException as e:
        return Response(
            {"detail": f"Yapılandırma modeli (Llama) bağlantı hatası veya hazır değil. Hata: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response({"detail": f"İşlem sırasında beklenmedik bir hata oluştu: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    end_time_structuring = time.time()
    structuring_duration = (end_time_structuring - start_time_structuring) * 1000

    final_response = {
        "raw_text_from_vision": raw_text,
        "structured_content": structured_content_json,
        "processing_times_ms": {
            "llama_vision": round(vision_duration, 2),
            "llama_structuring": round(structuring_duration, 2),
        }
    }
    return Response(final_response, status=status.HTTP_200_OK)




@api_view(['POST'])
@permission_classes([AllowAny])
def grade_text_answer(request):
    """
    Doğrudan metin olarak verilen öğrenci cevabını, soru ve kriterlere göre
    Llama-3p1-8b ile notlandırır. Kriterler opsiyoneldir.
    """
    question_text = request.data.get('question')
    reference_text = request.data.get('reference_text')
    grading_criteria = request.data.get('criteria', '').strip() # Opsiyonel hale getirildi
    student_answer_text = request.data.get('answer')

    if not all([question_text, reference_text, student_answer_text]):
        return Response(
            {"detail": "Lütfen 'question', 'reference_text' ve 'answer' alanlarını doldurun."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Notlandırma prompt'unu kriter olup olmamasına göre oluştur
    if grading_criteria:
        prompt_criteria_part = f"""
    Grading Criteria:
    ---
    {grading_criteria}
    ---
        """
    else:
        prompt_criteria_part = f"""
    Kriterler sağlanmamıştır, lütfen öğrenci cevabını referans metin ve soruyla karşılaştırarak kendi değerlendirmenizi yapın. Notu, referans metnine ne kadar yaklaştığına göre verin.
        """

    grading_prompt = f"""
    You are a teacher grading an exam paper. Your task is to grade the student's answer based on the provided reference text, question, and if available, grading criteria.
    
    You must provide your answer in a JSON format with 'grade' and 'reason' keys.
    
    Reference Text:
    ---
    {reference_text}
    ---
    
    Question:
    ---
    {question_text}
    ---
    
    {prompt_criteria_part}
    
    Student's Answer:
    ---
    {student_answer_text}
    ---
    
    Grading (JSON Only):
    """
    
    # Llama-3p1-8b ile notlandırma adımı (geri kalan kod aynı kalır)
    # ... (buraya önceki yanıttaki kodun geri kalanını ekleyin)
    start_time_grading = time.time()
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
        
        try:
            grading_result_json = json.loads(grading_result_str)
        except json.JSONDecodeError:
            grading_result_json = {"error": "Invalid JSON format from LLM", "raw_response": grading_result_str}
    except requests.exceptions.RequestException as e:
        return Response(
            {"detail": f"Grading model connection error or not ready. Error: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response({"detail": f"An unexpected error occurred during grading: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    end_time_grading = time.time()
    grading_duration = (end_time_grading - start_time_grading) * 1000

    final_response = {
        "transcribed_answer": student_answer_text,
        "grading": grading_result_json,
        "processing_times_ms": {
            "llama_grading": round(grading_duration, 2),
        }
    }
    return Response(final_response, status=status.HTTP_200_OK)