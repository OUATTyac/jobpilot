# main.py
import os
import uuid
import textwrap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from google.genai import types

# --- Configuration ---
app = FastAPI(title="JobpilotAI API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Initialisations Gemini ---
text_model = None
image_client = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        # Modèle pour le TEXTE (Chat, Messages, etc.)
        text_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        # Client pour l'IMAGE (spécifique pour la génération d'images)
        image_client = genai.Client()
        print("✅ Modèles Gemini Texte et Image configurés.")
    else:
        print("⚠️ GEMINI_API_KEY non définie.")
except Exception as e:
    print(f"❌ Erreur configuration Gemini: {e}")

# Dossiers & Polices
PDF_DIR, IMG_DIR = "generated_pdfs", "generated_images"
os.makedirs(PDF_DIR, exist_ok=True); os.makedirs(IMG_DIR, exist_ok=True)
FONT_NAME, FONT_BOLD_NAME = 'Helvetica', 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('Poppins', 'font/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'font/Poppins-Bold.ttf'))
    FONT_NAME, FONT_BOLD_NAME = 'Poppins', 'Poppins-Bold'
    print("✅ Polices Poppins enregistrées.")
except Exception as e:
    print(f"⚠️ Polices Poppins non trouvées. Erreur: {e}")


# --- Modèles Pydantic ---
class LineItem(BaseModel): description: str; price: str
class DevisRequest(BaseModel): client: str; artisan: str; date: str; items: List[LineItem]
class MessageRequest(BaseModel): nom: str; metier: str; service: str; offre: str
class PromoRequest(BaseModel): nom: str; promo: str; date: str
class ChatRequest(BaseModel): message: str
class FeedbackRequest(BaseModel): message: str; response: str; rating: str


# --- Endpoints ---

@app.get("/", tags=["Status"])
def read_root(): return {"message": "API JobpilotAI v4.0"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    # ... (La logique du devis reste la même que la version précédente, elle est déjà bonne)
    pdf_id = f"devis_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    try: c.drawImage("font/logo.png", 50, height - 100, width=70, height=70, preserveAspectRatio=True, mask='auto')
    except Exception: print("⚠️ Logo non trouvé pour le PDF.")
    c.setFont(FONT_NAME, 10); c.drawRightString(width - 50, height - 60, "Devis préparé par :"); c.setFont(FONT_BOLD_NAME, 12); c.drawRightString(width - 50, height - 75, req.artisan.upper())
    c.setFont(FONT_BOLD_NAME, 22); c.drawString(50, height - 150, "Devis Professionnel"); c.line(50, height - 155, width - 50, height - 155)
    c.setFont(FONT_NAME, 11); c.drawString(50, height - 190, "CLIENT :"); c.drawString(50, height - 230, "DATE :"); c.setFont(FONT_BOLD_NAME, 11); c.drawString(150, height - 190, req.client); c.drawString(150, height - 230, req.date)
    c.roundRect(50, height - 550, width - 100, 300, 5, stroke=1, fill=0); c.setFont(FONT_BOLD_NAME, 11); c.drawString(60, height - 270, "Description"); c.drawRightString(width - 60, height - 270, "Montant (FCFA)"); c.line(50, height - 280, width - 50, height - 280)
    c.setFont(FONT_NAME, 11); current_y = height - 300; total = 0
    for item in req.items:
        c.drawString(60, current_y, item.description); c.drawRightString(width - 60, current_y, item.price)
        current_y -= 20; total += float(item.price.replace(',', '.')) if item.price.replace('.', '', 1).isdigit() else 0
    c.setFont(FONT_BOLD_NAME, 14); c.drawRightString(width - 60, height - 580, f"TOTAL : {total:.0f} FCFA")
    c.setFont(FONT_NAME, 9); c.drawString(50, 100, "Pourquoi nous choisir ? Qualité, respect des délais et service client irréprochable."); c.drawString(50, 85, "Ce devis est valable 30 jours.")
    c.setFont(FONT_BOLD_NAME, 10); c.drawCentredString(width / 2, 50, f"Merci pour votre confiance ! 🙏 - JobpilotAI")
    c.showPage(); c.save()
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"Devis_{req.client}.pdf")

@app.post("/generate-message", tags=["Générateurs"])
async def generate_message(req: MessageRequest):
    if not text_model: return {"message_text": f"Promo chez {req.nom}: {req.service} ! {req.offre}. Contactez-nous !"}
    # PROMPT AMÉLIORÉ
    prompt = f"""
Tu es un expert en marketing digital pour les petites entreprises africaines.
Rédige un message court et percutant pour une publication WhatsApp et Facebook.
Le ton doit être joyeux, professionnel et donner envie.
- Artisan: {req.nom} ({req.metier})
- Service/Produit: {req.service}
- Offre Spéciale: {req.offre}
Termine par un appel à l'action clair (ex: "Contactez-nous vite !", "Profitez-en !").
Utilise 2-3 emojis pertinents. ✨📞🎉
"""
    response = text_model.generate_content(prompt)
    return {"message_text": response.text}

@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    if not image_client or not text_model:
        raise HTTPException(status_code=503, detail="Le service IA n'est pas configuré.")

    # 1. Générer un prompt en ANGLAIS pour l'image
    prompt_for_image_prompt = f"Create a short, descriptive, vibrant, and optimistic advertising poster prompt for an image generation AI. The style should be modern African. The ad is for '{req.promo}'. The prompt should be in English."
    try:
        image_prompt_response = text_model.generate_content(prompt_for_image_prompt)
        image_prompt = image_prompt_response.text.strip().replace('"', '')
        print(f"🖼️ Prompt pour l'image: {image_prompt}")
    except Exception:
        image_prompt = f"vibrant promotional poster for an african artisan, for a promotion about {req.promo}"

    # 2. Générer l'image avec Gemini
    try:
        response = image_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=image_prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        image_part = response.candidates[0].content.parts[0]
        image_bytes = image_part.inline_data.data
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        img_id = f"promo_ai_{uuid.uuid4()}.png"
        img_path = os.path.join(IMG_DIR, img_id)
        img.save(img_path)
        return FileResponse(path=img_path, media_type="image/png", filename=f"Promo_{req.nom}.png")
    except Exception as e:
        print(f"❌ Erreur de génération d'image Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération de l'image : {e}")


@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not text_model: return {"reply": "Désolé, le service IA est indisponible."}
    prompt = f"""Tu es "JobpilotAI", un assistant IA expert, amical et encourageant, conçu spécifiquement pour les artisans et petits entrepreneurs en Afrique.

Ton rôle est de fournir des conseils pratiques et des idées créatives. Tu peux :
- Aider à trouver des slogans publicitaires percutants.
- Rédiger des messages professionnels pour des clients (remerciements, relances, annonces).
- Donner des idées de promotions ou de nouveaux services.
- Proposer des stratégies simples pour améliorer la visibilité sur les réseaux sociaux.
- Aider à structurer des devis ou des factures.

Règles importantes :
1. Ton ton doit être simple, positif et facile à comprendre.
2. Utilise des emojis de manière pertinente pour rendre la conversation plus vivante. ✨👍
3. Si on te pose une question hors de ton domaine (politique, science, etc.), réponds poliment que tu es spécialisé dans l'aide aux entrepreneurs et propose de revenir au sujet.
4. Garde tes réponses concises et directes. Question: "{req.message}". Réponse:"""
    try:
        response = text_model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"❌ Erreur Gemini: {e}")
        return {"reply": "Oups, une erreur est survenue."}

@app.post("/log-feedback", tags=["Assistant IA"])
async def log_feedback(req: FeedbackRequest):
    print("--- NOUVEAU FEEDBACK UTILISATEUR ---")
    print(f"Message: {req.message}")
    print(f"Réponse: {req.response}")
    print(f"Note: {req.rating}")
    print("---------------------------------")
    # Dans une vraie application, on sauvegarderait ça dans une base de données.
    return {"status": "Feedback reçu avec succès"}
