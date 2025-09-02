import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, Button, Alert, ScrollView } from 'react-native';
import axios from 'axios';

// API yanıtının yapısını tanımlayan TypeScript arayüzleri
interface GradingResult {
  grade: string;
  reason: string;
}

interface ProcessingTimes {
  llama_grading: number;
}

interface GradingResponse {
  transcribed_answer: string;
  grading: GradingResult;
  processing_times_ms: ProcessingTimes;
}

const API_URL = "http://192.168.1.14:8000/api/sinav/grade-text/"; // Kendi IP adresinizle güncelleyin

export default function GradeScreen() {
  const [question, setQuestion] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [criteria, setCriteria] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  // 'result' state'inin tipini GradingResponse veya null olarak belirtiyoruz
  const [result, setResult] = useState<GradingResponse | null>(null);

  const handleGrade = async () => {
    if (!question || !referenceText || !answer) {
      Alert.alert("Hata", "Lütfen 'Soru', 'Referans' ve 'Cevap' alanlarını doldurun.");
      return;
    }

    setLoading(true);
    setResult(null);

    const data = {
      question,
      reference_text: referenceText,
      criteria,
      answer,
    };

    try {
      const response = await axios.post<GradingResponse>(API_URL, data, {
        headers: {
          'Content-Type': 'application/json',
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
      <Text style={styles.title}>Metin Tabanlı Notlandırma</Text>
      
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
      <TextInput
        style={styles.input}
        placeholder="Öğrenci Cevabı"
        value={answer}
        onChangeText={setAnswer}
        multiline
      />
      
      <Button
        title={loading ? "Yükleniyor..." : "Notlandır"}
        onPress={handleGrade}
        disabled={loading}
      />
      
      {/* Opsiyonel zincirleme ile güvenli erişim sağlıyoruz */}
      {result && (
        <View style={styles.resultContainer}>
          <Text style={styles.resultTitle}>Notlandırma Sonucu:</Text>
          <Text>
            <Text style={{ fontWeight: 'bold' }}>Not:</Text> {result.grading?.grade}
          </Text>
          <Text>
            <Text style={{ fontWeight: 'bold' }}>Gerekçe:</Text> {result.grading?.reason}
          </Text>
          <Text style={{ marginTop: 10 }}>
            <Text style={{ fontWeight: 'bold' }}>İşleme Süresi:</Text> {result.processing_times_ms?.llama_grading} ms
          </Text>
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
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
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
});