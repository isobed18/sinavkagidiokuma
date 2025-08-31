from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny # Şimdilik kimlik doğrulaması yok
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from PIL import Image
import requests
import json
import time
import torch

# Modelimizi apps.py dosyasından alıyoruz
from .apps import SinavokuyucuConfig

@api_view(['POST'])
@permission_classes([AllowAny]) # Herkese açık endpoint
@parser_classes([MultiPartParser, FormParser]) # Resim dosyası alabilmek için
def grade_handwritten_answer(request):
    """
    El yazısı ile yazılmış bir cevabı resim olarak alır, metne çevirir
    ve Llama modeli ile notlandırır.
    """
    # Gerekli modellerin yüklenip yüklenmediğini kontrol et
    if not SinavokuyucuConfig.trocr_model or not SinavokuyucuConfig.trocr_processor:
        return Response(
            {"detail": "AI modelleri henüz hazır değil, lütfen sunucuyu kontrol edin."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    # İstekten verileri al
    handwritten_image = request.FILES.get('image')
    question_text = request.data.get('question')
    reference_text = request.data.get('reference_text')
    grading_criteria = request.data.get('criteria')

    if not all([handwritten_image, question_text, reference_text, grading_criteria]):
        return Response(
            {"detail": "Lütfen 'image', 'question', 'reference_text' ve 'criteria' alanlarını sağlayın."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --- 1. Adım: TrOCR ile El Yazısını Metne Çevirme ---
    student_answer_text = ""
    try:
        image = Image.open(handwritten_image).convert("RGB")
        
        processor = SinavokuyucuConfig.trocr_processor
        model = SinavokuyucuConfig.trocr_model
        device = model.device

        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
        generated_ids = model.generate(pixel_values)
        student_answer_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        print(f"TrOCR Çıktısı: {student_answer_text}")

    except Exception as e:
        return Response({"detail": f"El yazısı tanıma hatası: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 2. Adım: Llama için Prompt Hazırlama ---
    prompt = f"""
    Sen bir sınav kağıdı okuyan bir öğretmensin. Görevin, öğrencinin cevabını sana verilen referans metin, soru ve değerlendirme kriterlerine göre notlandırmaktır. Cevabını sadece ve sadece JSON formatında, 'grade' ve 'reason' anahtarlarıyla vermelisin.

    Referans Metin:
    ---
    {reference_text}
    ---

    Soru:
    ---
    {question_text}
    ---

    Değerlendirme Kriterleri:
    ---
    {grading_criteria}
    ---

    Öğrencinin Cevabı:
    ---
    {student_answer_text}
    ---

    Değerlendirme (Sadece JSON formatında):
    """

    # --- 3. Adım: Llama'ya İstek Gönderme ---
    ollama_api_url = "http://localhost:11434/api/generate"
    try:
        ollama_response = requests.post(
            ollama_api_url,
            json={"model": "llama-3p1-8b", "prompt": prompt, "stream": False}
        )
        ollama_response.raise_for_status()

        llm_output = json.loads(ollama_response.text)
        grading_result_str = llm_output['response']
        grading_result_json = json.loads(grading_result_str)
        
        final_response = {
            "transcribed_answer": student_answer_text,
            "grading": grading_result_json
        }
        return Response(final_response, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return Response(
            {"detail": "Llama modeli geçerli bir JSON formatında cevap vermedi.", "raw_response": grading_result_str},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response({"detail": f"Notlandırma sırasında hata: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
