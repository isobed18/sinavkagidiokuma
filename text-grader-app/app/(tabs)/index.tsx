import { Text, View, StyleSheet } from 'react-native';

export default function TabHomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Hoş Geldiniz!</Text>
      <Text style={styles.text}>Aşağıdaki sekmeleri kullanarak farklı notlandırma yöntemlerine erişebilirsiniz.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  text: {
    fontSize: 16,
    textAlign: 'center',
  },
});