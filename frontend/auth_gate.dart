// lib/auth_gate.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:jobpilotai/generator_screen.dart'; 
import 'package:jobpilotai/login_screen.dart';  

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        // L'utilisateur n'est pas connecté
        if (!snapshot.hasData) {
          return const LoginScreen();
        }

        // L'utilisateur est connecté, on affiche l'écran principal
        return const GeneratorScreen();
      },
    );
  }
}