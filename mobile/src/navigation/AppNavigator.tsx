/**
 * App Navigator
 */
import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';

import {useAuthStore} from '../store/authStore';
import {LoginScreen} from '../screens/LoginScreen';
// Import other screens here (not created for brevity)

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const AuthStack = () => (
  <Stack.Navigator screenOptions={{headerShown: false}}>
    <Stack.Screen name="Login" component={LoginScreen} />
    {/* Add Register, ForgotPassword screens */}
  </Stack.Navigator>
);

const MainTabs = () => (
  <Tab.Navigator>
    {/* Add Home, Scan, Jobs, Profile tabs */}
  </Tab.Navigator>
);

const AppNavigator = () => {
  const {isAuthenticated} = useAuthStore();

  return isAuthenticated ? <MainTabs /> : <AuthStack />;
};

export default AppNavigator;
