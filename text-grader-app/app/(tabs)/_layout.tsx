import { Tabs } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { StyleSheet } from 'react-native';

export default function TabLayout() {
  return (
    <Tabs>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Ana Sayfa',
          tabBarIcon: ({ color }) => <FontAwesome size={28} name="home" color={color} />,
        }}
      />
      <Tabs.Screen
        name="grade"
        options={{
          title: 'Metin Notlandırma',
          tabBarIcon: ({ color }) => <FontAwesome size={28} name="file-text" color={color} />,
        }}
      />
      <Tabs.Screen
        name="image-grade"
        options={{
          title: 'Görsel Notlandırma',
          tabBarIcon: ({ color }) => <FontAwesome size={28} name="camera" color={color} />,
        }}
      />
    </Tabs>
  );
}