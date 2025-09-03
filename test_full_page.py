import requests
import json
import os

# API'nin URL'sini ve resim dosyasının yolunu belirle
API_URL = "http://127.0.0.1:8000/api/sinav/grade-full-page/"  # Kendi API URL'nizle güncelleyin
IMAGE_PATH = "sample_answer.jpeg"  # Yüklü resim dosyasının yolu

# Dosyanın varlığını kontrol et
if not os.path.exists(IMAGE_PATH):
    print(f"HATA: '{IMAGE_PATH}' dosyası bulunamadı. Lütfen dosya yolunu kontrol edin.")
else:
    # Resim dosyasını aç ve "files" objesi olarak hazırla
    with open(IMAGE_PATH, "rb") as image_file:
        files = {
            'image': (os.path.basename(IMAGE_PATH), image_file, 'image/jpeg')
        }

        # İsteği gönder
        try:
            print("API'ye istek gönderiliyor...")
            response = requests.post(API_URL, files=files, timeout=300)
            response.raise_for_status()  # HTTP hatalarını kontrol et

            # Yanıtı JSON formatında al
            result = response.json()
            
            # Sonuçları ekrana yazdır
            print("İstek başarıyla tamamlandı!")
            print("--- API Yanıtı ---")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        except requests.exceptions.RequestException as e:
            print(f"İstek sırasında bir hata oluştu: {e}")
            if e.response:
                print(f"Sunucudan gelen yanıt: {e.response.text}")