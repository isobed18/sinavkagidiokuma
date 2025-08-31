from django.apps import AppConfig
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import os

class SinavokuyucuConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sinavokuyucu'
    trocr_processor = None
    trocr_model = None
    
    # Hugging Face modellerinin indirileceği özel bir klasör belirleyelim
    MODEL_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "huggingface_models_sinav")

    def ready(self):
        """
        Bu fonksiyon Django sunucusu başladığında sadece bir kere çalışır.
        TrOCR modelini ve işlemcisini hafızaya yükler.
        """
        if not SinavokuyucuConfig.trocr_model:
            print("TrOCR modeli uygulama başlangıcında yükleniyor...")
            
            # CUDA destekli ekran kartı varsa onu, yoksa işlemciyi (CPU) kullan
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Kullanılacak Cihaz: {device}")
            
            model_name = 'microsoft/trocr-base-handwritten'
            
            try:
                # Modeli ve işlemciyi belirtilen cache dizinine indirip/yükle
                SinavokuyucuConfig.trocr_processor = TrOCRProcessor.from_pretrained(
                    model_name, cache_dir=self.MODEL_CACHE_DIR
                )
                SinavokuyucuConfig.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                    model_name, cache_dir=self.MODEL_CACHE_DIR
                ).to(device)
                
                print("TrOCR modeli başarıyla yüklendi ve kullanıma hazır.")
            except Exception as e:
                print(f"KRİTİK HATA: TrOCR modeli yüklenemedi. Hata: {e}")
                print("Lütfen internet bağlantınızı ve gerekli kütüphanelerin kurulu olduğundan emin olun.")
