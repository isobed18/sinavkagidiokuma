import requests
import os
import json
# --- AYARLAR ---
# Test için kullanacağın el yazısı resminin tam yolunu buraya yaz
IMAGE_PATH = "sample_answer.jpeg" # Proje ana dizininde bu isimde bir resim olmalı

# Django sunucunun adresi
API_URL = "http://127.0.0.1:8000/api/sinav/grade/"

# Llama modeline gönderilecek veriler
QUESTION = "Bu parçadaki olay örgüsü ve zaman unsuru düşünüldüğünde Nuri Efendi'nin nasıl bir ruh hâline sahip olması beklenir? Sebebiyle birlikte yazınız. (12 puan)"

REFERENCE_TEXT = """
Nuri Efendi, asılılıktan şemsiyesini aldı, paltosunu giydi, yavaşça sokağa çıktı. 
Sokak lambalarının yarı aydınlığında yürümeye başladı. Birkaç hayvan ve yolları süpürenler dışında sokakta kimsecikler yoktu.
Sabahın köründe insanlar sıcacık yataklarında uyurken işe gitmek ne acı, diye düşündü. Ayakları, onu dört yol ağzındaki durağa götürdü.
Sokak bomboştu ama durak kendisi gibi işe gitmek için bekleyen insanlarla doluydu.
"""

CRITERIA = """
Öğrencilerden, bu parçanın olay örgüsünü ve zamanını belirleyip bu unsurların parçanın kahramanı Nuri Efendi'nin ruh hâline etkilerinin neler olabileceğini ve bunun sebebini yazmaları beklenmektedir.
Örnek cevaplar:
Soğuk havada ve sabahın köründe işe gitmek zorunda olduğu için usanmıştır.
Çok erken saatte işe gittiği için üzülmektedir.
Soğuk havada işe gittiği için hoşnut değildir.
Erken saatte işe gitmekten dolayı bıkmıştır.
Soğuk havada işe gittiği için mutlu değildir.
Notlandırma örnekleri:
10 puan: Ruh halini anlatıyor ve sebebi de var.
5 puan: Ruh halini anlatıyor ama sebebi yok.
0 puan: Ruh halini anlatmıyor.

"""

def test_api():
    """
    Belirtilen resim ve metinlerle API'yi test eder.
    """
    if not os.path.exists(IMAGE_PATH):
        print(f"HATA: Resim dosyası bulunamadı: '{IMAGE_PATH}'")
        print("Lütfen proje ana dizinine 'sample_answer.png' adında bir resim dosyası ekleyin.")
        return

    # Gönderilecek verileri hazırla
    data = {
        'question': QUESTION,
        'reference_text': REFERENCE_TEXT,
        'criteria': CRITERIA,
    }

    print(f"'{IMAGE_PATH}' dosyası API'ye gönderiliyor...")
    
    try:
        # Resmi binary olarak aç ve isteği gönder
        with open(IMAGE_PATH, 'rb') as image_file:
            files = {'image': (os.path.basename(IMAGE_PATH), image_file, 'image/png')}
            
            response = requests.post(API_URL, files=files, data=data)
            
            # Yanıtı kontrol et
            response.raise_for_status()  # 200 OK değilse hata fırlat
            
            print("\n--- API YANITI ---")
            # Gelen JSON yanıtını güzel bir formatta yazdır
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    except requests.exceptions.RequestException as e:
        print(f"\nAPI'ye bağlanırken bir hata oluştu: {e}")
    except Exception as e:
        print(f"\nBeklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    test_api()
