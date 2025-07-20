// lib/generator_screen.dart (VERSION FINALE PRO - CORRIGÉE)
import 'dart:typed_data';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;

import 'package:universal_html/html.dart' as html;
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:open_file/open_file.dart';

import 'package:jobpilotai/dashboard_screen.dart';
import 'package:jobpilotai/chat_screen.dart';


const String backendUrl = 'https://jobpilot-pnui.onrender.com';

class GeneratorScreen extends StatefulWidget {
  const GeneratorScreen({super.key});

  @override
  _GeneratorScreenState createState() => _GeneratorScreenState();
}

class _GeneratorScreenState extends State<GeneratorScreen> {
  final User? _user = FirebaseAuth.instance.currentUser;

  @override
  Widget build(BuildContext context) {
    final userName = _user?.displayName ?? _user?.email?.split('@')[0] ?? 'Artisan';
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Image.asset('assets/logo.png', height: 32),
            const SizedBox(width: 8),
            const Text("JobpilotAI", style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        centerTitle: false,
        actions: [
          IconButton(icon: const Icon(Icons.dashboard_rounded), tooltip: "Statistiques complètes", onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => DashboardScreen()))),
          IconButton(icon: const Icon(Icons.logout), tooltip: "Déconnexion", onPressed: () => FirebaseAuth.instance.signOut()),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Bonjour, $userName !", style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text("L'assistant intelligent pour votre entreprise.", style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.grey[600])),
            const SizedBox(height: 24),
            _buildActionCard(context: context, icon: Icons.add_circle_outline_rounded, title: "Créer une nouvelle tâche", subtitle: "Générez un devis, une facture, un message ou une affiche.", color: Theme.of(context).primaryColor, onTap: () => _showNewTaskForm(context)),
            const SizedBox(height: 16),
            _buildActionCard(context: context, icon: Icons.chat_bubble_outline_rounded, title: "Discuter avec l'Assistant", subtitle: "Demandez des conseils, des slogans, des idées...", color: Colors.orange.shade700, onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const ChatScreen()))),
            const SizedBox(height: 32),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text("Activité Récente", style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600)), TextButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => DashboardScreen())), child: const Text("Voir tout"))]),
            const SizedBox(height: 8),
            _buildRecentActivity(),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard({required BuildContext context, required IconData icon, required String title, required String subtitle, required Color color, required VoidCallback onTap}) {
    return Card(clipBehavior: Clip.antiAlias, child: InkWell(onTap: onTap, child: Container(padding: const EdgeInsets.all(20), decoration: BoxDecoration(border: Border(left: BorderSide(color: color, width: 5))), child: Row(children: [Icon(icon, size: 40, color: color), const SizedBox(width: 16), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)), const SizedBox(height: 4), Text(subtitle, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]))])), const Icon(Icons.arrow_forward_ios_rounded, color: Colors.grey)]))));
  }

  Widget _buildRecentActivity() {
    if (_user == null) return const Center(child: Text("Utilisateur non connecté"));
    return StreamBuilder<QuerySnapshot>(
      stream: FirebaseFirestore.instance.collection('users').doc(_user!.uid).collection('logs').orderBy('date', descending: true).limit(3).snapshots(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
        if (!snapshot.hasData || snapshot.data!.docs.isEmpty) return Card(child: Container(width: double.infinity, padding: const EdgeInsets.all(24.0), child: const Text("Aucune activité pour le moment.", textAlign: TextAlign.center)));
        final docs = snapshot.data!.docs;
        return Card(
          child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: docs.length,
            separatorBuilder: (context, index) => const Divider(height: 1, indent: 16, endIndent: 16),
            itemBuilder: (context, index) {
              final data = docs[index].data() as Map<String, dynamic>;
              IconData iconData = Icons.help_outline;
              switch(data['type']) {
                case 'Devis': iconData = Icons.receipt_long_outlined; break;
                case 'Facture': iconData = Icons.receipt_long_outlined; break;
                case 'Message': iconData = Icons.message_outlined; break;
                case 'Affiche': iconData = Icons.palette_outlined; break;
              }
              return ListTile(
                leading: CircleAvatar(child: Icon(iconData, size: 20)),
                title: Text("${data['type']} - ${data['artisan'] ?? 'n/a'}", style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text(data['content'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
              );
            },
          ),
        );
      },
    );
  }

  void _showNewTaskForm(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 16),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(color: Theme.of(context).scaffoldBackgroundColor, borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom, left: 16, right: 16, top: 20),
          child: _TaskForm(),
        ),
      ),
    );
  }
}

class LineItem {
  final TextEditingController descriptionController = TextEditingController();
  final TextEditingController priceController = TextEditingController();
}

class _TaskForm extends StatefulWidget {
  @override
  __TaskFormState createState() => __TaskFormState();
}

class __TaskFormState extends State<_TaskForm> {
  final _formKey = GlobalKey<FormState>();
  final _clientController = TextEditingController();
  final _artisanController = TextEditingController();
  final _dateController = TextEditingController();
  List<LineItem> _lineItems = [LineItem()];
  String _docType = 'Devis';

  final SpeechToText _speechToText = SpeechToText();
  bool _speechEnabled = false;
  TextEditingController? _targetController;
  bool _isGeneratingDevis = false;
  bool _isGeneratingMessage = false;
  bool _isGeneratingPromo = false;
  final FirebaseFirestore _db = FirebaseFirestore.instance;
  final User? _user = FirebaseAuth.instance.currentUser;

  @override
  void initState() {
    super.initState();
    _initSpeech();
    _artisanController.text = _user?.displayName ?? _user?.email?.split('@')[0] ?? '';
  }

  @override
  void dispose() {
    _clientController.dispose();
    _artisanController.dispose();
    _dateController.dispose();
    for (var item in _lineItems) {
      item.descriptionController.dispose();
      item.priceController.dispose();
    }
    super.dispose();
  }

  void _initSpeech() async {
    try {
      _speechEnabled = await _speechToText.initialize();
    } catch (e) {
      print("Erreur vocale: $e");
    }
    if (mounted) setState(() {});
  }

  void _startListening(TextEditingController controller) {
    if (!_speechEnabled || _speechToText.isListening) return;
    setState(() => _targetController = controller);
    _speechToText.listen(onResult: (result) {
      if (mounted) setState(() => controller.text = result.recognizedWords);
    }, localeId: 'fr_FR');
  }

  void _stopListening() => _speechToText.stop();

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message), backgroundColor: isError ? Colors.redAccent : Colors.green));
  }

  Future<void> logAction(String type, String content, {double? price}) async {
    if (_user == null) return;
    await _db.collection('users').doc(_user!.uid).collection('logs').add({'type': type, 'content': content, 'artisan': _artisanController.text, 'price': price, 'date': Timestamp.now()});
  }

  Future<void> generateDevis() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isGeneratingDevis = true);
    try {
      List<Map<String, String>> itemsPayload = _lineItems.map((item) => {"description": item.descriptionController.text, "price": item.priceController.text}).toList();
      double totalPrice = _lineItems.fold(0, (sum, item) => sum + (double.tryParse(item.priceController.text) ?? 0));
      final uri = Uri.parse('$backendUrl/generate-devis');
      final response = await http.post(uri, headers: {"Content-Type": "application/json"}, body: jsonEncode({"type": _docType, "client": _clientController.text, "artisan": _artisanController.text, "date": _dateController.text, "items": itemsPayload}));
      if (response.statusCode == 200) {
        final bytes = response.bodyBytes;
        if (kIsWeb) {
          final blob = html.Blob([bytes], 'application/pdf');
          final url = html.Url.createObjectUrlFromBlob(blob);
          html.AnchorElement(href: url)..setAttribute("download", "${_docType}_${_clientController.text}.pdf")..click();
          html.Url.revokeObjectUrl(url);
        } else {
          final dir = await getApplicationDocumentsDirectory();
          final filePath = '${dir.path}/doc.pdf';
          final file = File(filePath);
          await file.writeAsBytes(bytes);
          await OpenFile.open(filePath);
        }
        await logAction(_docType, 'Génération PDF pour ${_clientController.text}', price: totalPrice);
        _showSnackBar('$_docType PDF généré avec succès !');
      } else {
        final errorBody = jsonDecode(response.body);
        throw Exception('Erreur serveur: ${errorBody['detail'] ?? response.reasonPhrase}');
      }
    } catch (e) {
      _showSnackBar('Erreur: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isGeneratingDevis = false);
    }
  }

  Future<void> generateMessage() async {
    if (!_formKey.currentState!.validate() || _lineItems.isEmpty) return;
    setState(() => _isGeneratingMessage = true);
    try {
      final firstItem = _lineItems.first;
      final uri = Uri.parse('$backendUrl/generate-message');
      final response = await http.post(uri, headers: {"Content-Type": "application/json"}, body: jsonEncode({"nom": _artisanController.text, "metier": "Artisan(e)", "service": firstItem.descriptionController.text, "offre": "une offre spéciale !"}));
      if (response.statusCode == 200) {
        final message = jsonDecode(utf8.decode(response.bodyBytes))['message_text'];
        _showResultDialog("Message Suggéré", message);
        await logAction('Message', message);
      } else {
        final errorBody = jsonDecode(response.body);
        throw Exception('Erreur serveur: ${errorBody['detail'] ?? response.reasonPhrase}');
      }
    } catch (e) {
      _showSnackBar('Erreur: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isGeneratingMessage = false);
    }
  }

  Future<void> generatePromoImage() async {
    if (!_formKey.currentState!.validate() || _lineItems.isEmpty) return;
    setState(() => _isGeneratingPromo = true);
    try {
      final firstItem = _lineItems.first;
      final uri = Uri.parse('$backendUrl/generate-promo-image');
      final response = await http.post(
        uri,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "nom": _artisanController.text,
          "product": firstItem.descriptionController.text,
          "price": firstItem.priceController.text,
          "date": _dateController.text
        })
      );
      if (response.statusCode == 200) {
        final imageBytes = response.bodyBytes;
        _showImageResultDialog(imageBytes);
        await logAction('Affiche', 'Génération d\'une affiche pour ${firstItem.descriptionController.text}');
      } else {
        final errorBody = jsonDecode(response.body);
        throw Exception('Erreur serveur: ${errorBody['detail'] ?? response.reasonPhrase}');
      }
    } catch (e) {
      _showSnackBar('Erreur: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isGeneratingPromo = false);
    }
  }

  void _showResultDialog(String title, String content, {Uint8List? imageBytes}) {
    showDialog(context: context, builder: (context) => AlertDialog(title: Text(title), content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [if (imageBytes != null) Image.memory(imageBytes), if (content.isNotEmpty) SelectableText(content)])), actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Fermer")), TextButton(onPressed: () { if (imageBytes != null) { Share.shareXFiles([XFile.fromData(imageBytes, name: 'Promo.png', mimeType: 'image/png')]); } else { Share.share(content); } }, child: const Text("Partager"))]));
  }

  void _showImageResultDialog(Uint8List imageBytes) {
    showDialog(context: context, builder: (context) => AlertDialog(title: const Text("Affiche Promotionnelle"), content: SingleChildScrollView(child: Image.memory(imageBytes)), actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Fermer")), TextButton(onPressed: () { if (kIsWeb) { final blob = html.Blob([imageBytes], 'image/png'); final url = html.Url.createObjectUrlFromBlob(blob); html.AnchorElement(href: url)..setAttribute("download", "promo.png")..click(); html.Url.revokeObjectUrl(url); } else { /* Logique mobile */ } }, child: const Text("Télécharger")), TextButton(onPressed: () => Share.shareXFiles([XFile.fromData(imageBytes, name: 'Promo.png', mimeType: 'image/png')]), child: const Text("Partager"))]));
  }
  
  Widget _buildVoiceIcon(TextEditingController controller) {
    bool isListening = _speechToText.isListening && _targetController == controller;
    return IconButton(icon: Icon(isListening ? Icons.mic : Icons.mic_none, color: Theme.of(context).primaryColor), onPressed: _speechEnabled ? () => isListening ? _stopListening() : _startListening(controller) : null, tooltip: "Saisie vocale");
  }

  @override
  Widget build(BuildContext context) {
    double totalPrice = _lineItems.fold(0, (sum, item) => sum + (double.tryParse(item.priceController.text) ?? 0));
    return SingleChildScrollView(
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text("Créer une Tâche", style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            SegmentedButton<String>(
              segments: const [ButtonSegment(value: 'Devis', label: Text('Devis')), ButtonSegment(value: 'Facture', label: Text('Facture'))],
              selected: {_docType},
              onSelectionChanged: (newSelection) => setState(() => _docType = newSelection.first),
            ),
            const SizedBox(height: 16),
            TextFormField(controller: _artisanController, decoration: InputDecoration(labelText: "Nom Entreprise / Responsable", prefixIcon: const Icon(Icons.store_mall_directory_outlined)), validator: (v) => v!.isEmpty ? 'Champ requis' : null),
            const SizedBox(height: 16),
            TextFormField(controller: _clientController, decoration: InputDecoration(labelText: "Nom du client", prefixIcon: const Icon(Icons.person_outline)), validator: (v) => v!.isEmpty ? 'Champ requis' : null),
            const SizedBox(height: 16),
            TextFormField(controller: _dateController, decoration: InputDecoration(labelText: "Date", prefixIcon: const Icon(Icons.calendar_today_outlined)), validator: (v) => v!.isEmpty ? 'Champ requis' : null),
            const Divider(height: 32),
            ..._lineItems.asMap().entries.map((entry) {
              int idx = entry.key;
              LineItem item = entry.value;
              return Padding(
                padding: const EdgeInsets.only(bottom: 16.0),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(flex: 3, child: TextFormField(controller: item.descriptionController, decoration: InputDecoration(labelText: "Produit / Service", suffixIcon: _buildVoiceIcon(item.descriptionController)), validator: (v) => v!.isEmpty ? 'Requis' : null)),
                  const SizedBox(width: 8),
                  Expanded(flex: 2, child: TextFormField(controller: item.priceController, decoration: InputDecoration(labelText: "Prix (FCFA)"), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Requis' : null, onChanged: (_) => setState(() {}))),
                  if (_lineItems.length > 1) IconButton(icon: const Icon(Icons.remove_circle_outline, color: Colors.red), onPressed: () => setState(() => _lineItems.removeAt(idx))) else const SizedBox(width: 48)
                ]),
              );
            }).toList(),
            TextButton.icon(icon: const Icon(Icons.add), label: const Text("Ajouter une ligne"), onPressed: () => setState(() => _lineItems.add(LineItem()))),
            const Divider(height: 32),
            Text("TOTAL : ${totalPrice.toStringAsFixed(0)} FCFA", style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold), textAlign: TextAlign.right),
            const SizedBox(height: 24),
            Text("Actions IA", style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton.icon(onPressed: _isGeneratingDevis ? null : generateDevis, icon: _isGeneratingDevis ? const SizedBox.square(dimension: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2,)) : const Icon(Icons.receipt_long_outlined), label: Text("Générer le ${_docType} PDF")),
            const SizedBox(height: 12),
            ElevatedButton.icon(onPressed: _isGeneratingMessage ? null : generateMessage, icon: _isGeneratingMessage ? const SizedBox.square(dimension: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2,)) : const Icon(Icons.chat_bubble_outline), label: const Text("Générer message Pub")),
            const SizedBox(height: 12),
            ElevatedButton.icon(onPressed: _isGeneratingPromo ? null : generatePromoImage, style: ElevatedButton.styleFrom(backgroundColor: Colors.amber[700]), icon: _isGeneratingPromo ? const SizedBox.square(dimension: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2,)) : const Icon(Icons.image_outlined), label: const Text("Créer une Affiche Promo")),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}