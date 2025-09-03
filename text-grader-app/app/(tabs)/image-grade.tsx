import React, { useState } from 'react';
import { StyleSheet, Text, View, Button, Alert, ScrollView, TextInput, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

// API yanıtları için TypeScript arayüzleri
interface SingleGradingResponse {
  transcribed_answer: string;
  grading: {
    grade: string;
    reason: string;
  };
  processing_times_ms: {
    llama_vision: number;
    llama_grading: number;
  };
}

interface FullPageGradingResponse {
  raw_text_from_vision: string;
  structured_content: Array<{
    question: string;
    answer: string;
  }>;
  processing_times_ms: {
    llama_vision: number;
    llama_structuring: number;
  };
}

// API URL'leri
const API_URLS = {
  singleGrade: "http://192.168.1.14:8000/api/sinav/grade/",
  fullPage: "http://192.168.1.14:8000/api/sinav/grade-full-page/",
};

export default function ImageGradeScreen() {
  const [gradingType, setGradingType] = useState<'single' | 'fullPage'>('single');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Tek notlandırma için state'ler
  const [question, setQuestion] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [criteria, setCriteria] = useState("");

  const pickImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 1,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
      setResult(null); // Yeni bir resim seçildiğinde önceki sonucu temizle
    }
  };

  const handleGrade = async () => {
    if (!imageUri) {
      Alert.alert("Hata", "Lütfen bir resim seçin.");
      return;
    }

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('image', {
      uri: imageUri,
      name: `image.jpeg`,
      type: 'image/jpeg',
    } as any);

    let apiUrl = '';
    
    if (gradingType === 'single') {
      if (!question || !referenceText) {
        Alert.alert("Hata", "Lütfen Soru ve Referans Metni alanlarını doldurun.");
        setLoading(false);
        return;
      }
      formData.append('question', question);
      formData.append('reference_text', referenceText);
      formData.append('criteria', criteria);
      apiUrl = API_URLS.singleGrade;
    } else {
      apiUrl = API_URLS.fullPage;
    }

    try {
      const response = await axios.post(apiUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setResult(response.data);
    } catch (error) {
      console.error("API'ye bağlanırken bir hata oluştu:", error);
      Alert.alert("Hata", "API'ye bağlanırken bir sorun oluştu. Lütfen sunucunun çalıştığından emin olun.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Görsel Notlandırma</Text>
      
      <View style={styles.buttonGroup}>
        <Button
          title="Tek Soru"
          onPress={() => {
            setGradingType('single');
            setResult(null);
            setImageUri(null);
          }}
          disabled={gradingType === 'single'}
        />
        <View style={{ width: 10 }} />
        <Button
          title="Tüm Sayfa"
          onPress={() => {
            setGradingType('fullPage');
            setResult(null);
            setImageUri(null);
          }}
          disabled={gradingType === 'fullPage'}
        />
      </View>

      {gradingType === 'single' && (
        <View style={styles.formContainer}>
          <Text style={styles.formTitle}>Tek Soru Notlandırma (Görsel Cevap)</Text>
          <TextInput
            style={styles.input}
            placeholder="Soru Metni"
            value={question}
            onChangeText={setQuestion}
            multiline
          />
          <TextInput
            style={styles.input}
            placeholder="Referans Metni"
            value={referenceText}
            onChangeText={setReferenceText}
            multiline
          />
          <TextInput
            style={styles.input}
            placeholder="Notlandırma Kriterleri (Opsiyonel)"
            value={criteria}
            onChangeText={setCriteria}
            multiline
          />
        </View>
      )}

      <Button title="Galeriden Resim Seç" onPress={pickImage} />
      {imageUri && <Image source={{ uri: imageUri }} style={styles.imagePreview} />}
      
      <Button
        title={loading ? "Yükleniyor..." : "Notlandır"}
        onPress={handleGrade}
        disabled={loading || !imageUri || (gradingType === 'single' && (!question || !referenceText))}
      />

      {result && (
        <View style={styles.resultContainer}>
          <Text style={styles.resultTitle}>Sonuç:</Text>
          {gradingType === 'single' ? (
            <>
              <Text style={styles.resultText}>
                <Text style={{ fontWeight: 'bold' }}>Transkripsiyon:</Text> {result.transcribed_answer}
              </Text>
              <Text style={styles.resultText}>
                <Text style={{ fontWeight: 'bold' }}>Not:</Text> {result.grading.grade}
              </Text>
              <Text style={styles.resultText}>
                <Text style={{ fontWeight: 'bold' }}>Gerekçe:</Text> {result.grading.reason}
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.resultText}>
                <Text style={{ fontWeight: 'bold' }}>Ham Metin:</Text> {result.raw_text_from_vision}
              </Text>
              <Text style={styles.resultText}>
                <Text style={{ fontWeight: 'bold' }}>Yapılandırılmış İçerik:</Text>
              </Text>
              {result.structured_content.map((item: any, index: number) => (
                <View key={index} style={styles.structuredItem}>
                  <Text style={{ fontWeight: 'bold' }}>Soru {index + 1}:</Text>
                  <Text>{item.question}</Text>
                  <Text style={{ fontWeight: 'bold', marginTop: 5 }}>Cevap {index + 1}:</Text>
                  <Text>{item.answer}</Text>
                </View>
              ))}
            </>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
    backgroundColor: '#fff',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  buttonGroup: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  formContainer: {
    width: '100%',
    marginBottom: 20,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  input: {
    width: '100%',
    minHeight: 80,
    borderColor: 'gray',
    borderWidth: 1,
    borderRadius: 5,
    marginBottom: 10,
    padding: 10,
    textAlignVertical: 'top',
  },
  imagePreview: {
    width: 200,
    height: 200,
    resizeMode: 'contain',
    marginVertical: 20,
  },
  resultContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    width: '100%',
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  resultText: {
    marginBottom: 5,
  },
  structuredItem: {
    marginTop: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 5,
  },
});