import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, Button, Alert, ScrollView, KeyboardAvoidingView, Platform, TouchableOpacity } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import axios from 'axios';
import { FontAwesome } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

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

const API_URLS = {
  singleGrade: "http://192.168.1.14:8000/api/sinav/grade-text/",
  multipleGrade: "http://192.168.1.14:8000/api/sinav/grade-multiple-text/",
};

export default function GradeScreen() {
  const [gradingType, setGradingType] = useState<'single' | 'multiple'>('single');
  const [question, setQuestion] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [criteria, setCriteria] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GradingResponse | null>(null);
  const [csvFile, setCsvFile] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [downloadUri, setDownloadUri] = useState<string | null>(null);

  const handleClear = (setter: React.Dispatch<React.SetStateAction<string>>) => {
    setter("");
  };

  const handleDocumentPick = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'text/csv',
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setCsvFile(result.assets[0]);
        setDownloadUri(null);
      } else {
        setCsvFile(null);
      }
    } catch (e) {
      console.error(e);
      Alert.alert("Hata", "Dosya seçilirken bir sorun oluştu.");
    }
  };

  const handleGrade = async () => {
    if (gradingType === 'single') {
      if (!question || !referenceText || !answer) {
        Alert.alert("Hata", "Lütfen 'Soru', 'Referans' ve 'Cevap' alanlarını doldurun.");
        return;
      }
    } else { // Multiple grading
      if (!csvFile || !question || !referenceText) {
        Alert.alert("Hata", "Lütfen 'Soru', 'Referans' ve CSV dosyasını seçin.");
        return;
      }
    }

    setLoading(true);
    setResult(null);
    setDownloadUri(null);

    try {
      if (gradingType === 'single') {
        const data = {
          question,
          reference_text: referenceText,
          criteria,
          answer,
        };
        const response = await axios.post<GradingResponse>(API_URLS.singleGrade, data, {
          headers: {
            'Content-Type': 'application/json',
          },
        });
        setResult(response.data);
      } else { // Multiple grading
        const formData = new FormData();
        formData.append('csv_file', {
          uri: csvFile?.uri,
          name: csvFile?.name,
          type: 'text/csv',
        } as any);
        formData.append('question', question);
        formData.append('reference_text', referenceText);
        formData.append('criteria', criteria);

        const response = await axios.post(API_URLS.multipleGrade, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          responseType: 'arraybuffer',
        });

        const downloadedFileUri = FileSystem.documentDirectory + `graded_${csvFile?.name}`;
        await FileSystem.writeAsStringAsync(downloadedFileUri, response.data, {
          encoding: FileSystem.EncodingType.Base64,
        });

        setDownloadUri(downloadedFileUri);
        Alert.alert("Başarılı", "CSV dosyası başarıyla notlandırıldı ve indirilmeye hazır.");
      }
    } catch (error) {
      console.error("API'ye bağlanırken bir hata oluştu:", error);
      Alert.alert("Hata", "API'ye bağlanırken bir sorun oluştu veya yanıt alınamadı. Lütfen sunucunun çalıştığından emin olun.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (downloadUri) {
      if (Platform.OS === 'android') {
        const contentUri = await FileSystem.getContentUriAsync(downloadUri);
        await Sharing.shareAsync(contentUri);
      } else {
        await Sharing.shareAsync(downloadUri);
      }
      Alert.alert("Dosya Hazır", "Notlandırılmış dosyayı paylaştığınızda indirebilirsiniz.");
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Metin Tabanlı Notlandırma</Text>
        
        <View style={styles.buttonGroup}>
          <Button
            title="Tek Cevap"
            onPress={() => {
              setGradingType('single');
              setResult(null);
              setCsvFile(null);
              setDownloadUri(null);
            }}
            disabled={gradingType === 'single'}
          />
          <View style={{ width: 10 }} />
          <Button
            title="Çoklu Cevap"
            onPress={() => {
              setGradingType('multiple');
              setResult(null);
              setCsvFile(null);
              setDownloadUri(null);
            }}
            disabled={gradingType === 'multiple'}
          />
        </View>

        {gradingType === 'single' ? (
          <View style={styles.formContainer}>
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
          </View>
        ) : (
          <View style={styles.formContainer}>
            <Text style={styles.formTitle}>Çoklu Cevap Notlandırma (CSV Yükleme)</Text>
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

            <Text style={styles.csvInfo}>
              Lütfen içinde "student_answer" sütunu bulunan bir CSV dosyası yükleyin.
            </Text>
            <Button title="CSV Dosyası Seç" onPress={handleDocumentPick} />
            {csvFile && <Text style={styles.fileName}>Seçilen Dosya: {csvFile.name}</Text>}
            <Button
              title={loading ? "İşleniyor..." : "Dosyayı İşle ve Notlandır"}
              onPress={handleGrade}
              disabled={loading || !csvFile || !question || !referenceText}
            />
            {downloadUri && (
              <View style={styles.downloadContainer}>
                <Text style={styles.downloadText}>Notlandırılmış dosya hazır!</Text>
                <Button title="Dosyayı İndir" onPress={handleDownload} />
              </View>
            )}
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
    textAlign: 'center',
  },
  formLabel: {
    alignSelf: 'flex-start',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 10,
    marginBottom: 5,
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
  csvInfo: {
    marginBottom: 15,
    textAlign: 'center',
    fontSize: 14,
    color: '#555',
  },
  fileName: {
    marginTop: 10,
    fontSize: 14,
    fontStyle: 'italic',
    textAlign: 'center',
  },
  downloadContainer: {
    marginTop: 20,
    alignItems: 'center',
  },
  downloadText: {
    marginBottom: 10,
    fontSize: 16,
    fontWeight: 'bold',
  },
});