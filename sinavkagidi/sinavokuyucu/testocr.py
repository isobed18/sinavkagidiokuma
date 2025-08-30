from transformers import pipeline
from PIL import Image

# 1. Pipeline'ı oluşturun
pipe = pipeline("image-to-text", model="microsoft/trocr-base-handwritten")

# 2. Görüntüyü yükleyin (örnek olarak bir resim dosyası kullanıyoruz)
# Bu satırı kendi dosya yolunuzla değiştirin
image = Image.open("elyazisideneme.jpeg")

# 3. Pipeline'ı çalıştırın ve sonucu alın
result = pipe(image)

# 4. Sonucu yazdırın
print(result[0]['generated_text'])