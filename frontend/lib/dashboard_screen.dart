// lib/dashboard_screen.dart
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class DashboardScreen extends StatelessWidget {
  final FirebaseFirestore _db = FirebaseFirestore.instance;
  final User? _user = FirebaseAuth.instance.currentUser;

  DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    if (_user == null) {
      return const Scaffold(body: Center(child: Text("Utilisateur non connecté.")));
    }

    return Scaffold(
      appBar: AppBar(title: const Text("📊 Tableau de Bord")),
      body: StreamBuilder<QuerySnapshot>(
        stream: _db.collection('users').doc(_user!.uid).collection('logs').orderBy('date', descending: true).snapshots(),
        builder: (context, snapshot) {
          if (snapshot.hasError) return Center(child: Text('Erreur: ${snapshot.error}'));
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          
          final docs = snapshot.data?.docs ?? [];
          
          double totalRevenue = 0;
          int devisCount = 0;
          int messageCount = 0;
          int promoCount = 0;

          for (var doc in docs) {
            final data = doc.data() as Map<String, dynamic>;
            if (data['type'] == 'Devis') {
              totalRevenue += (data['price'] ?? 0.0);
              devisCount++;
            } else if (data['type'] == 'Message') {
              messageCount++;
            } else if (data['type'] == 'Affiche') {
              promoCount++;
            }
          }

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(8.0),
                child: Wrap(
                  spacing: 8.0,
                  runSpacing: 8.0,
                  alignment: WrapAlignment.center,
                  children: [
                    StatCard(title: "Revenu Total", value: "${totalRevenue.toStringAsFixed(0)} FCFA", icon: Icons.monetization_on, color: Colors.green),
                    StatCard(title: "Devis Créés", value: devisCount.toString(), icon: Icons.receipt_long, color: Colors.blue),
                    StatCard(title: "Messages Créés", value: messageCount.toString(), icon: Icons.chat, color: Colors.orange),
                    StatCard(title: "Affiches Créées", value: promoCount.toString(), icon: Icons.image, color: Colors.purple),
                  ],
                ),
              ),
              const Divider(height: 24, indent: 16, endIndent: 16),
              if (docs.isEmpty)
                const Expanded(
                  child: Center(
                    child: Text("Aucune activité pour le moment.\nCommencez à créer !", textAlign: TextAlign.center, style: TextStyle(fontSize: 16, color: Colors.grey)),
                  ),
                )
              else
                Expanded(
                  child: ListView.builder(
                    itemCount: docs.length,
                    itemBuilder: (context, index) {
                      final data = docs[index].data() as Map<String, dynamic>;
                      IconData iconData = Icons.help_outline;
                      switch(data['type']){
                         case 'Devis': iconData = Icons.receipt_long_outlined; break;
                         case 'Message': iconData = Icons.message_outlined; break;
                         case 'Affiche': iconData = Icons.palette_outlined; break;
                      }
                      return ListTile(
                        leading: CircleAvatar(child: Icon(iconData, size: 20)),
                        title: Text("${data['type']} - ${data['artisan'] ?? 'n/a'}"),
                        subtitle: Text(data['content'] ?? '', maxLines: 2, overflow: TextOverflow.ellipsis),
                        trailing: Text((data['date'] as Timestamp).toDate().toString().substring(0, 10)),
                      );
                    },
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const StatCard({Key? key, required this.title, required this.value, required this.icon, required this.color}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      color: color.withOpacity(0.1),
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: color.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Container(
        padding: const EdgeInsets.all(16),
        width: 160,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(title, style: TextStyle(fontWeight: FontWeight.bold, color: color), textAlign: TextAlign.center,),
            const SizedBox(height: 4),
            Text(value, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: color, fontWeight: FontWeight.bold), textAlign: TextAlign.center,),
          ],
        ),
      ),
    );
  }
}