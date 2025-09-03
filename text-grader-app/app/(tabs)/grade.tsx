import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, Button, Alert, ScrollView, KeyboardAvoidingView, Platform, TouchableOpacity } from 'react-native';
import axios from 'axios';
import { FontAwesome } from '@expo/vector-icons';

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

const API_URL = "http://192.168.1.14:8000/api/sinav/grade-text/";

export default function GradeScreen() {
  const [question, setQuestion] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [criteria, setCriteria] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GradingResponse | null>(null);

  const handleClear = (setter: React.Dispatch<React.SetStateAction<string>>) => {
    setter("");
  };

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
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Metin Tabanlı Notlandırma</Text>
        
        <Text style={styles.formLabel}>Referans Metni</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Örnek cevap için referans metnini giriniz..."
            placeholderTextColor="gray"
            value={referenceText}
            onChangeText={setReferenceText}
            multiline
          />
          <TouchableOpacity onPress={() => handleClear(setReferenceText)} style={styles.clearButton}>
            <FontAwesome name="times-circle" size={24} color="gray" />
          </TouchableOpacity>
        </View>

        <Text style={styles.formLabel}>Soru Metni</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Lütfen soruyu giriniz..."
            placeholderTextColor="gray"
            value={question}
            onChangeText={setQuestion}
            multiline
          />
          <TouchableOpacity onPress={() => handleClear(setQuestion)} style={styles.clearButton}>
            <FontAwesome name="times-circle" size={24} color="gray" />
          </TouchableOpacity>
        </View>

        <Text style={styles.formLabel}>Notlandırma Kriterleri</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Puanlandırma neye göre yapılacak giriniz (Opsiyonel)"
            placeholderTextColor="gray"
            value={criteria}
            onChangeText={setCriteria}
            multiline
          />
          <TouchableOpacity onPress={() => handleClear(setCriteria)} style={styles.clearButton}>
            <FontAwesome name="times-circle" size={24} color="gray" />
          </TouchableOpacity>
        </View>

        <Text style={styles.formLabel}>Öğrenci Cevabı</Text>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Öğrencinin cevabını giriniz..."
            placeholderTextColor="gray"
            value={answer}
            onChangeText={setAnswer}
            multiline
          />
          <TouchableOpacity onPress={() => handleClear(setAnswer)} style={styles.clearButton}>
            <FontAwesome name="times-circle" size={24} color="gray" />
          </TouchableOpacity>
        </View>
        
        <Button
          title={loading ? "Yükleniyor..." : "Notlandır"}
          onPress={handleGrade}
          disabled={loading}
        />
        
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
    </KeyboardAvoidingView>
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
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    marginBottom: 10,
    borderColor: 'gray',
    borderWidth: 1,
    borderRadius: 5,
    backgroundColor: '#f9f9f9',
  },
  formLabel: {
    alignSelf: 'flex-start',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 10,
    marginBottom: 5,
  },
  input: {
    flex: 1,
    minHeight: 80,
    padding: 10,
    textAlignVertical: 'top',
    color: '#000',
  },
  clearButton: {
    padding: 10,
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