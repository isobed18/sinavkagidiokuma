import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  Button,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import axios from 'axios';
import { FontAwesome } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

// API yanıtlarının arayüzleri
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

// API URL'lerini merkezi bir yerden yönetmek daha iyidir.
// Kendi IP adresinizle veya sunucu adresinizle güncelleyin.
const BASE_API_URL = "http://192.168.1.14:8000"; 
const API_URLS = {
  singleGrade: `${BASE_API_URL}/api/sinav/grade-text/`,
  multipleGrade: `${BASE_API_URL}/api/sinav/grade-multiple-text/`,
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
      const docResult = await DocumentPicker.getDocumentAsync({
        type: 'text/csv',
        copyToCacheDirectory: true,
      });

      if (!docResult.canceled && docResult.assets && docResult.assets.length > 0) {
        setCsvFile(docResult.assets[0]);
        setDownloadUri(null); // Yeni dosya seçildiğinde eski indirme linkini temizle
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
          responseType: 'blob', // 'blob' kullanmak dosya işlemleri için daha güvenilirdir
        });

        // Blob'dan Base64'e dönüştürme
        const reader = new FileReader();
        reader.readAsDataURL(response.data);
        reader.onloadend = async () => {
            const base64data = (reader.result as string).split(',')[1];
            const downloadedFileUri = FileSystem.documentDirectory + `graded_${csvFile?.name}`;
            await FileSystem.writeAsStringAsync(downloadedFileUri, base64data, {
                encoding: FileSystem.EncodingType.Base64,
            });
            setDownloadUri(downloadedFileUri);
            Alert.alert("Başarılı", "CSV dosyası başarıyla notlandırıldı ve indirilmeye hazır.");
        };

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
        try {
            await Sharing.shareAsync(downloadUri, {
                mimeType: 'text/csv',
                dialogTitle: 'Notlandırılmış dosyayı paylaş',
                UTI: 'public.comma-separated-values-text'
            });
        } catch (error) {
            console.error('Dosya paylaşım hatası:', error);
            Alert.alert("Hata", "Dosya paylaşılırken bir sorun oluştu.");
        }
    }
  };

  const renderSingleGrading = () => (
    <>
      <Text style={styles.formLabel}>Soru Metni</Text>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Lütfen soruyu giriniz..." placeholderTextColor="gray" value={question} onChangeText={setQuestion} multiline />
        <TouchableOpacity onPress={() => handleClear(setQuestion)} style={styles.clearButton}>
          <FontAwesome name="times-circle" size={20} color="gray" />
        </TouchableOpacity>
      </View>

      <Text style={styles.formLabel}>Referans Metni</Text>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Örnek cevap için referans metnini giriniz..." placeholderTextColor="gray" value={referenceText} onChangeText={setReferenceText} multiline />
        <TouchableOpacity onPress={() => handleClear(setReferenceText)} style={styles.clearButton}>
          <FontAwesome name="times-circle" size={20} color="gray" />
        </TouchableOpacity>
      </View>

      <Text style={styles.formLabel}>Notlandırma Kriterleri</Text>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Puanlandırma neye göre yapılacak (Opsiyonel)" placeholderTextColor="gray" value={criteria} onChangeText={setCriteria} multiline />
        <TouchableOpacity onPress={() => handleClear(setCriteria)} style={styles.clearButton}>
          <FontAwesome name="times-circle" size={20} color="gray" />
        </TouchableOpacity>
      </View>

      <Text style={styles.formLabel}>Öğrenci Cevabı</Text>
      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="Öğrencinin cevabını giriniz..." placeholderTextColor="gray" value={answer} onChangeText={setAnswer} multiline />
        <TouchableOpacity onPress={() => handleClear(setAnswer)} style={styles.clearButton}>
          <FontAwesome name="times-circle" size={20} color="gray" />
        </TouchableOpacity>
      </View>
      
      <View style={styles.buttonWrapper}>
        <Button title={loading ? "Yükleniyor..." : "Notlandır"} onPress={handleGrade} disabled={loading} />
      </View>
    </>
  );

  const renderMultipleGrading = () => (
    <>
        <Text style={styles.formLabel}>Soru Metni</Text>
        <View style={styles.inputContainer}>
            <TextInput style={styles.input} placeholder="Lütfen soruyu giriniz..." placeholderTextColor="gray" value={question} onChangeText={setQuestion} multiline />
            <TouchableOpacity onPress={() => handleClear(setQuestion)} style={styles.clearButton}>
                <FontAwesome name="times-circle" size={20} color="gray" />
            </TouchableOpacity>
        </View>

        <Text style={styles.formLabel}>Referans Metni</Text>
        <View style={styles.inputContainer}>
            <TextInput style={styles.input} placeholder="Örnek cevap için referans metnini giriniz..." placeholderTextColor="gray" value={referenceText} onChangeText={setReferenceText} multiline />
            <TouchableOpacity onPress={() => handleClear(setReferenceText)} style={styles.clearButton}>
                <FontAwesome name="times-circle" size={20} color="gray" />
            </TouchableOpacity>
        </View>

        <Text style={styles.formLabel}>Notlandırma Kriterleri</Text>
        <View style={styles.inputContainer}>
            <TextInput style={styles.input} placeholder="Puanlandırma neye göre yapılacak (Opsiyonel)" placeholderTextColor="gray" value={criteria} onChangeText={setCriteria} multiline />
            <TouchableOpacity onPress={() => handleClear(setCriteria)} style={styles.clearButton}>
                <FontAwesome name="times-circle" size={20} color="gray" />
            </TouchableOpacity>
        </View>
        
        <Text style={styles.csvInfo}>Lütfen içinde "student_answer" sütunu bulunan bir CSV dosyası yükleyin.</Text>
        
        <View style={styles.buttonWrapper}>
            <Button title="CSV Dosyası Seç" onPress={handleDocumentPick} />
        </View>

        {csvFile && <Text style={styles.fileName}>Seçilen Dosya: {csvFile.name}</Text>}
        
        <View style={styles.buttonWrapper}>
            <Button title={loading ? "İşleniyor..." : "Dosyayı İşle ve Notlandır"} onPress={handleGrade} disabled={loading || !csvFile} />
        </View>

        {downloadUri && (
            <View style={styles.downloadContainer}>
            <Text style={styles.downloadText}>Notlandırılmış dosya hazır!</Text>
            <Button title="Dosyayı İndir/Paylaş" onPress={handleDownload} />
            </View>
        )}
    </>
  );

  const handleToggle = (type: 'single' | 'multiple') => {
      setGradingType(type);
      setResult(null);
      setCsvFile(null);
      setDownloadUri(null);
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Metin Tabanlı Notlandırma</Text>
        
        <View style={styles.toggleContainer}>
            <TouchableOpacity
                style={[styles.toggleButton, gradingType === 'single' && styles.toggleButtonActive]}
                onPress={() => handleToggle('single')}
            >
                <Text style={[styles.toggleButtonText, gradingType === 'single' && styles.toggleButtonTextActive]}>Tek Cevap</Text>
            </TouchableOpacity>
            <TouchableOpacity
                style={[styles.toggleButton, gradingType === 'multiple' && styles.toggleButtonActive]}
                onPress={() => handleToggle('multiple')}
            >
                <Text style={[styles.toggleButtonText, gradingType === 'multiple' && styles.toggleButtonTextActive]}>Çoklu Cevap (CSV)</Text>
            </TouchableOpacity>
        </View>

        {gradingType === 'single' ? renderSingleGrading() : renderMultipleGrading()}
        
        {result && gradingType === 'single' && (
          <View style={styles.resultContainer}>
            <Text style={styles.resultTitle}>Notlandırma Sonucu:</Text>
            <Text style={styles.resultText}><Text style={styles.bold}>Not:</Text> {result.grading?.grade}</Text>
            <Text style={styles.resultText}><Text style={styles.bold}>Gerekçe:</Text> {result.grading?.reason}</Text>
            <Text style={[styles.resultText, { marginTop: 10 }]}><Text style={styles.bold}>İşleme Süresi:</Text> {result.processing_times_ms?.llama_grading} ms</Text>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// STYLES - Eski kodun daha düzenli stil yapısı baz alındı ve yeni bileşenler için stiller eklendi.
const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
    backgroundColor: '#f5f5f5', // Arka plan rengi biraz daha yumuşatıldı
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
    marginBottom: 20,
  },
  toggleContainer: {
    flexDirection: 'row',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#007AFF',
    borderRadius: 8,
    overflow: 'hidden',
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  toggleButtonActive: {
    backgroundColor: '#007AFF',
  },
  toggleButtonText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  toggleButtonTextActive: {
    color: '#fff',
  },
  formLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#444',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    marginBottom: 15,
  },
  input: {
    flex: 1,
    minHeight: 100,
    paddingHorizontal: 15,
    paddingVertical: 10,
    fontSize: 16,
    color: '#000',
    textAlignVertical: 'top',
  },
  clearButton: {
    padding: 10,
    justifyContent: 'center',
  },
  buttonWrapper: {
    marginTop: 10,
    marginBottom: 15,
  },
  resultContainer: {
    marginTop: 20,
    padding: 20,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    width: '100%',
  },
  resultTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  resultText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#555',
  },
  bold: {
    fontWeight: 'bold',
  },
  csvInfo: {
    textAlign: 'center',
    fontSize: 14,
    color: '#666',
    marginVertical: 15,
    paddingHorizontal: 10,
    fontStyle: 'italic',
  },
  fileName: {
    marginTop: 10,
    textAlign: 'center',
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '500',
  },
  downloadContainer: {
    marginTop: 20,
    alignItems: 'center',
    padding: 15,
    backgroundColor: '#E8F5E9', // Yeşil tonu
    borderRadius: 8,
  },
  downloadText: {
    marginBottom: 10,
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E7D32', // Koyu yeşil
  },
});