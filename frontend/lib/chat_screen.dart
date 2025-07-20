// lib/chat_screen.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

const String backendUrl = 'https://jobpilot-pnui.onrender.com';
var uuid = const Uuid();

class ChatMessage {
  final String id;
  final String text;
  final bool isUser;
  bool feedbackSent;

  ChatMessage({required this.text, required this.isUser, String? id})
      : id = id ?? uuid.v4(),
        feedbackSent = false;
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<ChatMessage> _messages = [];
  bool _isLoading = false;
  final SpeechToText _speechToText = SpeechToText();
  bool _speechEnabled = false;

  @override
  void initState() {
    super.initState();
    _initSpeech();
    _messages = [ChatMessage(
      text: "Bonjour ! Je suis votre assistant JobpilotAI. Comment puis-je vous aider ?",
      isUser: false
    )];
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _initSpeech() async {
    try { _speechEnabled = await _speechToText.initialize(); } catch (e) { print("Erreur vocale: $e"); }
    if (mounted) setState(() {});
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(_scrollController.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _controller.text;
    if (text.isEmpty || _isLoading) return;
    _controller.clear();
    setState(() { _messages.add(ChatMessage(text: text, isUser: true)); _isLoading = true; });
    _scrollToBottom();
    try {
      final response = await http.post(Uri.parse('$backendUrl/chat'), headers: {'Content-Type': 'application/json'}, body: jsonEncode({'message': text}));
      if (response.statusCode == 200) {
        final reply = jsonDecode(utf8.decode(response.bodyBytes))['reply'];
        if (mounted) setState(() => _messages.add(ChatMessage(text: reply, isUser: false)));
      } else { _addError(); }
    } catch (e) { _addError();
    } finally { if (mounted) setState(() => _isLoading = false); _scrollToBottom(); }
  }
  
  void _addError() { if (mounted) { setState(() => _messages.add(ChatMessage(text: "Désolé, une erreur est survenue. Veuillez réessayer.", isUser: false))); } }

  void _toggleListening() async {
    if (!_speechEnabled) return;
    if (_speechToText.isListening) {
      await _speechToText.stop();
    } else {
      await _speechToText.listen(onResult: (result) { if (mounted) setState(() => _controller.text = result.recognizedWords); }, localeId: 'fr_FR');
    }
    if (mounted) setState(() {});
  }

  Future<void> _sendFeedback(ChatMessage message, String rating) async {
    final userMessage = _messages.lastWhere((m) => m.isUser, orElse: () => ChatMessage(text: "N/A", isUser: true));
    
    setState(() => message.feedbackSent = true);
    
    try {
      await http.post(
        Uri.parse('$backendUrl/log-feedback'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': userMessage.text, 'response': message.text, 'rating': rating}),
      );
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Merci pour votre retour !"), backgroundColor: Colors.green, duration: Duration(seconds: 1)));
    } catch (e) { print("Erreur envoi feedback: $e"); }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Assistant JobpilotAI")),
      body: Column(children: [
        Expanded(
          child: ListView.builder(
            controller: _scrollController, padding: const EdgeInsets.all(16.0),
            itemCount: _messages.length + (_isLoading ? 1 : 0),
            itemBuilder: (context, index) {
              if (_isLoading && index == _messages.length) return _ChatBubble(message: ChatMessage(text: "...", isUser: false), isTyping: true, onFeedback: (rating) {});
              final message = _messages[index];
              return _ChatBubble(message: message, onFeedback: (rating) => _sendFeedback(message, rating));
            },
          ),
        ),
        _buildInputField(),
      ]),
    );
  }

  Widget _buildInputField() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
      decoration: BoxDecoration(color: Theme.of(context).cardColor, boxShadow: [BoxShadow(offset: const Offset(0, -1), blurRadius: 4, color: Colors.black.withOpacity(0.05))]),
      child: SafeArea(
        child: Row(children: [
          Expanded(child: TextField(controller: _controller, textCapitalization: TextCapitalization.sentences, decoration: const InputDecoration(hintText: 'Posez votre question...', border: InputBorder.none, filled: false), onSubmitted: _isLoading ? null : (_) => _sendMessage())),
          IconButton(icon: Icon(_speechToText.isListening ? Icons.mic : Icons.mic_none), onPressed: _toggleListening, color: _speechToText.isListening ? Theme.of(context).primaryColor : Colors.grey, tooltip: "Saisie vocale"),
          IconButton(icon: const Icon(Icons.send_rounded), onPressed: _isLoading ? null : _sendMessage, color: Theme.of(context).primaryColor),
        ]),
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message, this.isTyping = false, required this.onFeedback});
  final ChatMessage message;
  final bool isTyping;
  final Function(String) onFeedback;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
          margin: const EdgeInsets.symmetric(vertical: 4.0),
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
          decoration: BoxDecoration(
            color: message.isUser ? theme.primaryColor : Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: !message.isUser ? [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4, offset: const Offset(1,1))] : null
          ),
          child: isTyping
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.grey))
              : MarkdownBody(data: message.text, styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(p: theme.textTheme.bodyMedium?.copyWith(color: message.isUser ? Colors.white : Colors.black87))),
        ),
        if (!message.isUser && !isTyping)
          Padding(
            padding: const EdgeInsets.only(top: 2.0, left: 8.0, right: 8.0),
            child: message.feedbackSent
                ? const Icon(Icons.check_circle, color: Colors.green, size: 18)
                : Row(mainAxisSize: MainAxisSize.min, children: [
                    IconButton(icon: const Icon(Icons.thumb_up_outlined, size: 18), onPressed: () => onFeedback('good'), padding: EdgeInsets.zero, constraints: const BoxConstraints()),
                    const SizedBox(width: 8),
                    IconButton(icon: const Icon(Icons.thumb_down_outlined, size: 18), onPressed: () => onFeedback('bad'), padding: EdgeInsets.zero, constraints: const BoxConstraints()),
                  ]),
          ),
      ],
    );
  }
}