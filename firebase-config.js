// Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBcfOdEz27q1qbDBUmuOotXWDJQt-_W-bM",
  authDomain: "ai-anylsis-dashboard-d7123.firebaseapp.com",
  databaseURL: "https://ai-anylsis-dashboard-d7123-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "ai-anylsis-dashboard-d7123",
  storageBucket: "ai-anylsis-dashboard-d7123.firebasestorage.app",
  messagingSenderId: "559631936536",
  appId: "1:559631936536:web:533e1f88f0e01e5aec276d",
  measurementId: "G-K2FYB9L968"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize Firebase services
const auth = firebase.auth();
const db = firebase.firestore();

// Make services globally available
window.auth = auth;
window.db = db;

// Authentication methods - use the auth instance directly
window.createUserWithEmailAndPassword = function(email, password) {
  return auth.createUserWithEmailAndPassword(email, password);
};
window.signInWithEmailAndPassword = function(email, password) {
  return auth.signInWithEmailAndPassword(email, password);
};
window.signOut = function() {
  return auth.signOut();
};
window.onAuthStateChanged = function(callback) {
  return auth.onAuthStateChanged(callback);
};
window.updateProfile = function(user, profile) {
  return user.updateProfile(profile);
};
window.sendEmailVerification = function(user) {
  return user.sendEmailVerification();
};
window.sendPasswordResetEmail = function(email) {
  return auth.sendPasswordResetEmail(email);
};

// Firestore methods (compat API)
window.doc = (dbInstance, collection, id) => dbInstance.collection(collection).doc(id);
window.setDoc = (docRef, data) => docRef.set(data);
window.getDoc = (docRef) => docRef.get();
window.updateDoc = (docRef, data) => docRef.update(data);

// Firestore collection methods for direct access
window.getCollection = (collectionName) => db.collection(collectionName);
window.addDoc = (collectionName, data) => db.collection(collectionName).add(data);
window.getDocs = (collectionRef) => collectionRef.get();

// Debug logging
console.log('Firebase initialized successfully');
console.log('Auth available:', !!window.auth);
console.log('Firestore available:', !!window.db);
console.log('Firestore type:', typeof window.db);
console.log('createUserWithEmailAndPassword available:', !!window.createUserWithEmailAndPassword);
