# main.py
import os
import uuid
import textwrap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- Configuration ---
app = FastAPI(title="JobpilotAI API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Gemini Config
model = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        # CORRECTION DU NOM DU MODÈLE
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        print("✅ Gemini API configurée avec gemini-2.0-flash.")
    else:
        print("⚠️ GEMINI_API_KEY non définie.")
except Exception as e:
    print(f"❌ Erreur configuration Gemini: {e}")

# Dossiers & Polices
PDF_DIR, IMG_DIR = "generated_pdfs", "generated_images"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)
FONT_NAME, FONT_BOLD_NAME = 'Helvetica', 'Helvetica-Bold'
try:
    # Utilisation de Poppins pour un meilleur rendu
    pdfmetrics.registerFont(TTFont('Poppins', 'font/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'font/Poppins-Bold.ttf'))
    FONT_NAME, FONT_BOLD_NAME = 'Poppins', 'Poppins-Bold'
    print("✅ Polices Poppins enregistrées pour PDF.")
except Exception as e:
    print(f"⚠️ Polices Poppins non trouvées. Erreur: {e}")


# --- Modèles Pydantic mis à jour pour le devis multi-lignes ---
class LineItem(BaseModel):
    description: str
    price: str

class DevisRequest(BaseModel):
    client: str
    artisan: str
    date: str
    items: List[LineItem] # NOUVEAU: Accepte une liste d'items

class MessageRequest(BaseModel): nom: str; metier: str; service: str; offre: str
class PromoRequest(BaseModel): nom: str; promo: str; date: str
class ChatRequest(BaseModel): message: str


# --- Endpoints ---

@app.get("/", tags=["Status"])
def read_root(): return {"message": "API JobpilotAI v3.0"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    pdf_id = f"devis_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # 1. Logo
    try:
        c.drawImage("font/logo.png", 50, height - 100, width=70, height=70, preserveAspectRatio=True, mask='auto')
    except Exception:
        print("⚠️ Logo non trouvé pour le PDF.")

    # 2. Informations Artisan
    c.setFont(FONT_NAME, 10)
    c.drawRightString(width - 50, height - 60, "Devis préparé par :")
    c.setFont(FONT_BOLD_NAME, 12)
    c.drawRightString(width - 50, height - 75, req.artisan.upper())

    # 3. Titre
    c.setFont(FONT_BOLD_NAME, 22)
    c.drawString(50, height - 150, "Devis Professionnel")
    c.line(50, height - 155, width - 50, height - 155)

    # 4. Informations Client
    c.setFont(FONT_NAME, 11)
    c.drawString(50, height - 190, "CLIENT :")
    c.drawString(50, height - 230, "DATE :")
    c.setFont(FONT_BOLD_NAME, 11)
    c.drawString(150, height - 190, req.client)
    c.drawString(150, height - 230, req.date)

    # 5. Tableau des prestations
    c.roundRect(50, height - 550, width - 100, 300, 5, stroke=1, fill=0)
    c.setFont(FONT_BOLD_NAME, 11)
    c.drawString(60, height - 270, "Description")
    c.drawRightString(width - 60, height - 270, "Montant (FCFA)")
    c.line(50, height - 280, width - 50, height - 280)

    # Boucle sur les items
    c.setFont(FONT_NAME, 11)
    current_y = height - 300
    total = 0
    for item in req.items:
        c.drawString(60, current_y, item.description)
        c.drawRightString(width - 60, current_y, item.price)
        current_y -= 20
        total += float(item.price) if item.price.replace('.', '', 1).isdigit() else 0


    # 6. Total
    c.setFont(FONT_BOLD_NAME, 14)
    c.drawRightString(width - 60, height - 580, f"TOTAL : {total:.0f} FCFA")

    # 7. Pied de page
    c.setFont(FONT_NAME, 9)
    c.drawString(50, 100, "Pourquoi nous choisir ? Nous garantissons un travail de qualité, un respect des délais et un service client irréprochable.")
    c.drawString(50, 85, "Ce devis est valable 30 jours.")
    c.setFont(FONT_BOLD_NAME, 10)
    c.drawCentredString(width / 2, 50, f"Merci pour votre confiance ! 🙏 - JobpilotAI")

    c.showPage()
    c.save()
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"Devis_{req.client}.pdf")


@app.post("/generate-message", tags=["Générateurs"])
async def generate_message(req: MessageRequest):
    if not model: return {"message_text": f"Super promo chez {req.nom} ! Profitez de '{req.service}' avec {req.offre}. Contactez-nous !"}
    prompt = f"""Tu es JobpilotAI. Rédige un message WhatsApp court, amical et percutant en français simple. Utilise 1-2 emojis. Artisan: {req.nom} ({req.metier}), Service: {req.service}, Offre: {req.offre}. Rédige uniquement le message."""
    response = model.generate_content(prompt)
    return {"message_text": response.text}


@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    promo_text = "Offre Spéciale !"
    if model:
        prompt = f"""Crée une accroche marketing très courte (5-10 mots max) pour cette promotion : Artisan: {req.nom}, Promotion: {req.promo}, Fin: {req.date}. Rédige uniquement l'accroche."""
        try:
            response = model.generate_content(prompt)
            promo_text = response.text.strip().replace('"', '')
        except Exception: pass

    img_id = f"promo_{uuid.uuid4()}.png"
    img_path = os.path.join(IMG_DIR, img_id)
    try: img = Image.open("font/background.jpg").convert("RGBA")
    except FileNotFoundError: img = Image.new('RGB', (1080, 1080), color='#FFD700')
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    try:
        title_font, subtitle_font, promo_font = ImageFont.truetype("font/Poppins-Bold.ttf", 110), ImageFont.truetype("font/Poppins-Regular.ttf", 60), ImageFont.truetype("font/Poppins-Bold.ttf", 70)
    except IOError: title_font, subtitle_font, promo_font = ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()
    draw.text((540, 400), "\n".join(textwrap.wrap(promo_text, width=20)), font=title_font, fill='white', anchor='mm', align='center')
    draw.text((540, 600), f"Chez {req.nom}", font=subtitle_font, fill='#FFD700', anchor='mm', align='center')
    draw.text((540, 100), "✨ PROMO SPÉCIALE ✨", font=promo_font, fill='white', anchor='ms', align='center')
    draw.text((540, 980), f"Valable jusqu'au {req.date}", font=subtitle_font, fill='white', anchor='ms', align='center')
    img = img.convert("RGB")
    img.save(img_path)
    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")


@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not model: return {"reply": "Désolé, le service IA est indisponible."}
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
4. Garde tes réponses concises et directes. Question de l'artisan : "{req.message}". Réponse :"""
    try:
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"❌ Erreur Gemini: {e}")
        return {"reply": "Oups, une erreur est survenue. Pourriez-vous reformuler ?"}
