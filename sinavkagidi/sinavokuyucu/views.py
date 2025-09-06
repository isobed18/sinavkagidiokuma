import time
import json
import requests
import base64
import csv
import io
import re  # Regex kütüphanesi eklendi
import traceback
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse

# --- Ayarlar ---
OLLAMA_API_URL = "http://localhost:11434/api/chat"
VISION_MODEL_NAME = "llama3.2-vision:11b"
TEXT_MODEL_NAME = "llama3.1:8b"

# --- Çekirdek Fonksiyon: LLM ile Notlandırma ---


def get_llm_grading(question_text, reference_text, student_answer_text, grading_criteria=None):
    """
    LLM'den notlandırma yanıtı almak için tasarlanmış merkezi fonksiyon.
    Prompt engineering, JSON temizleme ve detaylı loglama içerir.
    """
    # Detaylı Loglama: Hangi cevabın işlendiğini net olarak gösterir.
    print("\n" + "="*80)
    print(f"DEĞERLENDİRİLEN ÖĞRENCİ CEVABI: '{student_answer_text}'")
    print("="*80)
    
    print(f"ADIM: Notlandırma için {TEXT_MODEL_NAME} modeli çağrılıyor...")
    start_time_grading = time.time()

    prompt_criteria_part = ""
    if grading_criteria:
        prompt_criteria_part = f"""
    3. Değerlendirmeyi yaparken aşağıdaki özel kriterleri de göz önünde bulundur:
    ---
    {grading_criteria}
    ---
        """

    grading_prompt = f"""
You are a fair and strict teacher. Your task is to grade the given "Student Answer" by comparing it with the "Reference Text".

STRICT RULES YOU MUST FOLLOW:
1. Base your reasoning ("reason") ONLY and ONLY on the text written by the student. Do not evaluate topics the student did not mention or add your own interpretations.
2. State any missing points that are in the reference text but not in the student's answer.
3. If the student's answer is completely wrong or irrelevant, state this clearly in the reasoning.
4. The response MUST be a valid JSON object containing ONLY the "grade" and "reason" keys. NEVER add Markdown (```), additional explanations, or any other text.

Reference Text (The Story):
---
{reference_text}
---

Question:
---
{question_text}
---

{prompt_criteria_part}

Student Answer:
---
{student_answer_text}
---

Grading (Only in JSON format, without any other text):
"""
    
    grading_data = {
        "model": TEXT_MODEL_NAME,
        "messages": [{"role": "user", "content": grading_prompt}],
        "stream": False,
        "format": "json" 
    }
    
    try:
        grading_response = requests.post(OLLAMA_API_URL, json=grading_data, timeout=45) # Timeout artırıldı
        grading_response.raise_for_status()
        llm_output = grading_response.json()
        
        grading_result_str = llm_output.get('message', {}).get('content', '{}')
        
        print(f"ADIM BAŞARILI: {TEXT_MODEL_NAME} modelinden dönen ham yanıt: {grading_result_str}")
        
        # YENİ: Yanıttaki olası Markdown bloğunu temizleme (Regex ile)
        match = re.search(r'\{.*\}', grading_result_str, re.DOTALL)
        if match:
            cleaned_str = match.group(0)
            print(f"TEMİZLENMİŞ YANIT: {cleaned_str}")
            try:
                grading_result_json = json.loads(cleaned_str)
            except json.JSONDecodeError:
                print("UYARI: Temizlenmiş yanıtta JSON formatı bozuk. Ham yanıt saklanıyor.")
                grading_result_json = {"grade": "JSON Hatası", "reason": f"Geçersiz JSON: {cleaned_str}"}
        else:
            print("UYARI: Yanıtta JSON nesnesi bulunamadı.")
            grading_result_json = {"grade": "JSON Bulunamadı", "reason": f"Geçersiz Yanıt: {grading_result_str}"}

    except requests.exceptions.RequestException as e:
        print(f"HATA: Notlandırma modeli bağlantı hatası veya hazır değil. Hata: {e}")
        raise
    except Exception as e:
        print(f"HATA: Notlandırma sırasında beklenmedik bir hata oluştu: {e}")
        raise
    
    end_time_grading = time.time()
    grading_duration = (end_time_grading - start_time_grading) * 1000
    
    grade_log = grading_result_json.get('grade', 'N/A')
    reason_log = grading_result_json.get('reason', 'N/A')
    print(f"VERİLEN NOT: {grade_log} | GEREKÇE: {reason_log}")
    print(f"{TEXT_MODEL_NAME} işlem süresi: {grading_duration:.2f} ms")

    return {
        "grading": grading_result_json,
        "processing_time": round(grading_duration, 2)
    }


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

    if not all([handwritten_image, question_text, reference_text]):
        return Response(
            {"detail": "Lütfen 'image', 'question' ve 'reference_text' alanlarını doldurun."},
            status=status.HTTP_400_BAD_REQUEST
        )
    print("API ÇAĞRISI: grade_handwritten_answer")
    try:
        image_bytes = handwritten_image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"HATA: Resim dosyası işlenirken bir hata oluştu: {e}")
        return Response({"detail": f"Error processing image file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 1: Transcribe handwritten text in the image with Llama Vision
    print("ADIM 1: Llama Vision modeli el yazısını metne çevirmek için çağrılıyor...")
    start_time_vision = time.time()
    try:
        ocr_prompt = "Transcribe the handwritten text in the image. Do not add any extra information or analysis. Just return the raw text. As you can see there some questions and handwritten answers of a student"
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
        ocr_response = requests.post(OLLAMA_API_URL, json=ocr_data, timeout=20)
        ocr_response.raise_for_status()
        ocr_output = json.loads(ocr_response.text)
        student_answer_text = ocr_output['message']['content'].strip()
        print(f"ADIM 1 BAŞARILI: Llama Vision'dan dönen metin: {student_answer_text}")
    except Exception as e:
        print(f"HATA: Llama Vision OCR başarısız oldu. Hata: {e}")
        return Response(
            {"detail": f"Handwritten text transcription failed. Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    end_time_vision = time.time()
    vision_duration = (end_time_vision - start_time_vision) * 1000
    print(f"Llama Vision işlem süresi: {vision_duration:.2f} ms")

    # Step 2: Grade with Llama-3p1-8b
    try:
        grading_result = get_llm_grading(question_text, reference_text, student_answer_text, grading_criteria)
    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    final_response = {
        "transcribed_answer": student_answer_text,
        "grading": grading_result['grading'],
        "processing_times_ms": {
            "llama_vision": round(vision_duration, 2),
            "llama_grading": grading_result['processing_time'],
        }
    }
    print(f"SONUÇ: Son yanıt döndürülüyor: {json.dumps(final_response, indent=2)}")
    return Response(final_response, status=status.HTTP_200_OK)

# API 2: Llama Vision + Llama 3 Tam Sayfa İşleme
# API 2: Llama Vision + Llama 3 Tam Sayfa İşleme
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def grade_full_page_answers(request):
    """
    Tüm sayfanın fotoğrafını TEK BİR Llama Vision çağrısı ile ham metne çevirir,
    ardından soruları ve cevapları notlandırır ve JSON olarak döner.
    """
    full_page_image = request.FILES.get('image')

    if not full_page_image:
        return Response(
            {"detail": "Lütfen 'image' dosyasını sağlayın."},
            status=status.HTTP_400_BAD_REQUEST
        )
    print("API ÇAĞRISI: grade_full_page_answers (TAMAMEN LLAMA VISION)")

    try:
        image_bytes = full_page_image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"HATA: Resim dosyası işlenirken bir hata oluştu: {e}")
        return Response({"detail": f"Resim dosyası işleme hatası: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Adım 1: Llama Vision ile hem metin çıkarma hem de notlandırma
    print("ADIM 1: Llama Vision modeli hem metin çevirme hem de notlandırma için çağrılıyor...")
    start_time_vision_and_grading = time.time()
    try:
        # PROMPT GÜNCELLEMESİ: Tek Llama Vision çağrısında hem OCR hem notlandırma
        # Burada Llama Vision'ın hem görseli anlayıp hem de karmaşık JSON üretmesini istiyoruz.
        # Bu, model için oldukça zorlayıcı bir prompt'tur.
        vision_grading_prompt = f"""
You are an AI assistant specialized in analyzing handwritten exam papers. Your task is to accurately grade a student's performance based on the provided image.

Your process should be as follows:
1. **Identify the exam questions** and their corresponding point values (e.g., "Question 6 (12 points)").
2. **Identify the student's handwritten answers** for each question. Pay extremely close attention to the handwriting and **do not mistake any printed text** (like a story or a passage) as the student's answer. The student's answer is always the handwritten text that appears directly after the question.
3. For each question, **determine the correct answer** based on the question's content and general knowledge.
4. **Compare the student's handwritten answer** to the correct answer you determined.
5. **Assign a numerical grade** based on the question's point value. For example, if a question is worth 12 points, a correct answer is '12/12', a partially correct answer might be '7/12', and a completely wrong answer is '0/12'.
6. **Provide a detailed reason** for the grade, explaining what parts of the student's answer were correct, what was missing, or what was incorrect.

Your final output MUST be a valid JSON array containing objects. Each object MUST have ONLY the following keys:
- 'question': The full text of the question, including its point value.
- 'answer': The exact transcribed text of the **student's handwritten answer**.
- 'grade': The numerical score (e.g., '12/12').
- 'reason': The detailed explanation for the grade.

DO NOT include any text, notes, or descriptions outside of the JSON array. The response must start with '[' and end with ']'.

Now, analyze the image and return the JSON.
"""
        
        vision_grading_data = {
            "model": VISION_MODEL_NAME, # Sadece Vision modelini kullanıyoruz
            "messages": [
                {
                    "role": "user",
                    "content": vision_grading_prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }
        vision_grading_response = requests.post(OLLAMA_API_URL, json=vision_grading_data, timeout=90) # Timeout artırıldı
        vision_grading_response.raise_for_status()
        llm_output = json.loads(vision_grading_response.text)
        graded_content_str = llm_output['message']['content'].strip()
        print(f"ADIM 1 BAŞARILI: Llama Vision'dan dönen ham yanıt: {graded_content_str}")

        # Sağlam JSON temizleme ve ayrıştırma
        # NOT: Llama Vision bu kadar karmaşık bir JSON'ı her zaman düzgün döndüremeyebilir.
        # Regex ile sadece ilk ve son köşeli parantez arasındaki bloğu yakalamaya çalışıyoruz.
        match = re.search(r'\[.*\]', graded_content_str, re.DOTALL)
        if match:
            cleaned_str = match.group(0)
            print(f"TEMİZLENMİŞ YANIT (Regex ile): {cleaned_str}")
            try:
                final_graded_content = json.loads(cleaned_str)
            except json.JSONDecodeError:
                print("UYARI: Temizlenmiş yanıtta JSON formatı bozuk. Ham yanıt olduğu gibi dönülecek.")
                # JSON bozuksa, ham çıktıyı "raw_llm_output" olarak dönüyoruz.
                return Response(
                    {
                        "error": "Llama Vision JSON formatını bozuk döndürdü.",
                        "raw_llm_output": graded_content_str,
                        "processing_times_ms": {
                            "llama_vision_and_grading": round((time.time() - start_time_vision_and_grading) * 1000, 2)
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            print("UYARI: Yanıtta JSON dizisi bulunamadı. Ham yanıt olduğu gibi dönülecek.")
            # JSON dizisi bulunamazsa, ham çıktıyı "raw_llm_output" olarak dönüyoruz.
            return Response(
                {
                    "error": "Llama Vision yanıtında geçerli bir JSON dizisi bulunamadı.",
                    "raw_llm_output": graded_content_str,
                    "processing_times_ms": {
                        "llama_vision_and_grading": round((time.time() - start_time_vision_and_grading) * 1000, 2)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except requests.exceptions.RequestException as e:
        print(f"HATA: Llama Vision bağlantı hatası veya hazır değil. Hata: {e}")
        return Response(
            {"detail": f"Llama Vision modeli bağlantı hatası veya hazır değil. Hata: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        print(f"HATA: İşlem sırasında beklenmedik bir hata oluştu: {e}")
        return Response({"detail": f"İşlem sırasında beklenmedik bir hata oluştu: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    end_time_vision_and_grading = time.time()
    vision_and_grading_duration = (end_time_vision_and_grading - start_time_vision_and_grading) * 1000

    # Nihai yanıtı oluştur
    final_response = {
        "graded_content": final_graded_content,
        "processing_times_ms": {
            "llama_vision_and_grading": round(vision_and_grading_duration, 2),
        }
    }

    print(f"SONUÇ: Son yanıt döndürülüyor: {json.dumps(final_response, indent=2)}")
    return Response(final_response, status=status.HTTP_200_OK)

# --- API View: Tek Metin Cevap ---

@api_view(['POST'])
@permission_classes([AllowAny])
def grade_text_answer(request):
    """
    Doğrudan metin olarak verilen öğrenci cevabını notlandırır.
    """
    question_text = request.data.get('question')
    reference_text = request.data.get('reference_text')
    grading_criteria = request.data.get('criteria', '').strip()
    student_answer_text = request.data.get('answer')

    if not all([question_text, reference_text, student_answer_text]):
        return Response(
            {"detail": "Lütfen 'question', 'reference_text' ve 'answer' alanlarını doldurun."},
            status=status.HTTP_400_BAD_REQUEST
        )
    print("\nAPI ÇAĞRISI: grade_text_answer")
    try:
        grading_result = get_llm_grading(question_text, reference_text, student_answer_text, grading_criteria)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    final_response = {
        "transcribed_answer": student_answer_text,
        "grading": grading_result['grading'],
        "processing_times_ms": {"llama_grading": grading_result['processing_time']}
    }
    print(f"SONUÇ: Son yanıt döndürülüyor: {json.dumps(final_response, indent=2)}")
    return Response(final_response, status=status.HTTP_200_OK)


# --- API View: Çoklu Cevap (CSV) ---

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def grade_multiple_text_answers(request):
    """
    CSV dosyası olarak gelen çoklu cevapları notlandırır ve sonuçları CSV olarak döndürür.
    """
    csv_file = request.FILES.get('csv_file')
    question = request.data.get('question')
    reference_text = request.data.get('reference_text')
    grading_criteria = request.data.get('criteria')

    if not all([csv_file, question, reference_text]):
        return Response(
            {"detail": "Lütfen 'csv_file', 'question' ve 'reference_text' alanlarını doldurun."},
            status=status.HTTP_400_BAD_REQUEST
        )
    print("\nAPI ÇAĞRISI: grade_multiple_text_answers")

    try:
        file_data = csv_file.read().decode('utf-8-sig')
        
        reader = csv.DictReader(io.StringIO(file_data), delimiter=';')
        
        print(f"DEBUG: CSV'den okunan başlıklar: {reader.fieldnames}")
        
        rows = list(reader)
        fieldnames = reader.fieldnames

        if not rows:
            print("UYARI: CSV dosyasından hiçbir veri satırı okunamadı.")
            return Response({"detail": "CSV'de işlenecek veri bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            print(f"BİLGİ: CSV dosyasından {len(rows)} adet veri satırı okundu.")

        if not fieldnames:
            return Response({"detail": "CSV dosyası boş veya başlık satırı eksik."}, status=status.HTTP_400_BAD_REQUEST)
        
        new_fieldnames = list(fieldnames)
        for field in ['llm_grade', 'llm_reason', 'processing_time_ms']:
            if field not in new_fieldnames:
                new_fieldnames.append(field)

        temp_output = io.StringIO()
        writer = csv.DictWriter(temp_output, fieldnames=new_fieldnames, delimiter=';')
        writer.writeheader()

        for i, row in enumerate(rows):
            print(f"\n--- Satır {i+1}/{len(rows)} işleniyor ---")
            
            print(f"DEBUG: Okunan satır verisi: {row}")
            
            student_answer = row.get('student_answer')

            if not student_answer:
                print(f"UYARI: Satır {i+1} 'student_answer' sütunu boş, atlanıyor.")
                row['llm_grade'] = 'Eksik Veri'
                row['llm_reason'] = 'CSV satırında student_answer sütunu boş veya bulunamadı.'
                row['processing_time_ms'] = 0
            else:
                try:
                    print(f"--> get_llm_grading fonksiyonu çağrılıyor...")
                    grading_result = get_llm_grading(question, reference_text, student_answer, grading_criteria)
                    row['llm_grade'] = grading_result['grading'].get('grade', 'N/A')
                    row['llm_reason'] = grading_result['grading'].get('reason', 'N/A')
                    row['processing_time_ms'] = grading_result['processing_time']
                except Exception as e:
                    print(f"!!! HATA: Satır {i+1} işlenirken bir istisna (exception) oluştu.")
                    traceback.print_exc() 
                    
                    row['llm_grade'] = 'API Hatası'
                    row['llm_reason'] = str(e)
                    row['processing_time_ms'] = 0
            
            if None in row:
                del row[None]
            writer.writerow(row)
        
        print("\nBİLGİ: Tüm satırların işlenmesi tamamlandı. Yanıt dosyası oluşturuluyor.")
        
        output_buffer = io.BytesIO()
        output_buffer.write(temp_output.getvalue().encode('utf-8'))
        output_buffer.seek(0)
        
        return FileResponse(output_buffer, as_attachment=True, filename=f"graded_{csv_file.name}", content_type='text/csv')

    except Exception as e:
        print(f"HATA: Çoklu notlandırma sırasında beklenmedik bir hata oluştu: {e}")
        traceback.print_exc()
        return Response(
            {"detail": f"Dosya işlenirken bir hata oluştu: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

