# main.py - VERSION FINALE PRO
import os
import uuid
import textwrap
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import qrcode
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- Configuration ---
app = FastAPI(title="JobpilotAI API", version="5.0.0 - Pro")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Gemini Config
text_model = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key); text_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("✅ Gemini API (texte) configurée.")
    else:
        print("⚠️ GEMINI_API_KEY non définie.")
except Exception as e:
    print(f"❌ Erreur config Gemini: {e}")

# Dossiers & Polices
PDF_DIR, IMG_DIR = "generated_pdfs", "generated_images"
os.makedirs(PDF_DIR, exist_ok=True); os.makedirs(IMG_DIR, exist_ok=True)
FONT_NAME, FONT_BOLD_NAME = 'Helvetica', 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('Poppins', 'font/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'font/Poppins-Bold.ttf'))
    FONT_NAME, FONT_BOLD_NAME = 'Poppins', 'Poppins-Bold'; print("✅ Polices Poppins enregistrées.")
except Exception as e:
    print(f"⚠️ Polices Poppins non trouvées. Erreur: {e}")


# --- Modèles Pydantic ---
class LineItem(BaseModel): description: str; price: str
class DevisRequest(BaseModel): type: str; client: str; artisan: str; date: str; items: List[LineItem]
class PromoRequest(BaseModel): nom: str; promo: str; date: str
class ChatRequest(BaseModel): message: str
class FeedbackRequest(BaseModel): message: str; response: str; rating: str


# --- Endpoints ---

@app.get("/", tags=["Status"])
def read_root(): return {"message": "API JobpilotAI v5.0 - Prête pour la victoire !"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    pdf_id = f"doc_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Couleurs
    primary_color = colors.HexColor("#4F46E5") # Indigo
    grey_color = colors.HexColor("#6B7280")

    # En-tête
    try: c.drawImage("font/logo.png", 40, height - 100, width=60, height=60, preserveAspectRatio=True, mask='auto')
    except Exception: print("⚠️ Logo non trouvé.")
    c.setFont(FONT_BOLD_NAME, 10); c.setFillColor(grey_color); c.drawRightString(width - 50, height - 60, "Document préparé par :"); c.setFont(FONT_BOLD_NAME, 12); c.setFillColor(colors.black); c.drawRightString(width - 50, height - 75, req.artisan.upper())
    
    # Titre (Devis ou Facture)
    c.setFont(FONT_BOLD_NAME, 28); c.setFillColor(primary_color); c.drawString(40, height - 150, req.type.upper())
    c.line(40, height - 155, width - 40, height - 155)

    # Infos Client
    c.setFont(FONT_NAME, 11); c.drawString(40, height - 190, "CLIENT :"); c.drawString(40, height - 210, "DATE :"); c.setFont(FONT_BOLD_NAME, 11); c.drawString(120, height - 190, req.client); c.drawString(120, height - 210, req.date)
    
    # Table des prestations
    table_y_start = height - 260
    c.setFillColor(primary_color); c.rect(40, table_y_start - 25, width - 80, 25, fill=1, stroke=0)
    c.setFont(FONT_BOLD_NAME, 11); c.setFillColor(colors.white); c.drawString(50, table_y_start - 18, "Description"); c.drawRightString(width - 50, table_y_start - 18, "Montant (FCFA)")
    
    current_y = table_y_start - 50; total = 0
    c.setFont(FONT_NAME, 11); c.setFillColor(colors.black)
    for i, item in enumerate(req.items):
        if i % 2 == 1: c.setFillColor(colors.HexColor("#F3F4F6")); c.rect(40, current_y - 5, width - 80, 20, fill=1, stroke=0); c.setFillColor(colors.black)
        c.drawString(50, current_y, item.description)
        c.drawRightString(width - 50, current_y, item.price)
        current_y -= 20; total += float(item.price.replace(',', '.')) if item.price.replace('.', '', 1).isdigit() else 0

    # Total
    c.setFillColor(primary_color); c.rect(width / 2, current_y - 50, width / 2 - 40, 40, fill=1, stroke=0)
    c.setFont(FONT_BOLD_NAME, 16); c.setFillColor(colors.white); c.drawRightString(width - 50, current_y - 40, f"TOTAL : {total:.0f} FCFA")
    
    # Pied de page
    c.setFont(FONT_NAME, 9); c.setFillColor(grey_color); c.drawCentredString(width / 2, 60, "Ce document a été généré avec JobpilotAI, l'assistant intelligent pour votre entreprise."); c.setFont(FONT_BOLD_NAME, 10); c.setFillColor(colors.black); c.drawCentredString(width / 2, 40, "Merci pour votre confiance !")

    c.showPage(); c.save()
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"{req.type}_{req.client}.pdf")


@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    if not text_model: raise HTTPException(status_code=503, detail="Service IA indisponible.")
        
    prompt = f"""Crée une accroche marketing très courte et percutante (5-8 mots max) pour cette promotion : '{req.promo}'. Rédige uniquement l'accroche."""
    try:
        response = text_model.generate_content(prompt); promo_text = response.text.strip().replace('"', '')
    except Exception as e:
        print(f"Erreur génération texte: {e}"); promo_text = req.promo
    
    img_id = f"promo_{uuid.uuid4()}.png"; img_path = os.path.join(IMG_DIR, img_id)
    try: img = Image.open("font/background.jpg").resize((1080, 1080))
    except FileNotFoundError: print("⚠️ background.jpg non trouvé."); img = Image.new('RGB', (1080, 1080), color='#4F46E5')
    
    if img.mode != 'RGBA': img = img.convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 150)); img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    try:
        font_heavy = ImageFont.truetype("font/Poppins-Bold.ttf", 130)
        font_medium = ImageFont.truetype("font/Poppins-Regular.ttf", 70)
        font_light = ImageFont.truetype("font/Poppins-Regular.ttf", 40)
    except IOError: font_heavy, font_medium, font_light = [ImageFont.load_default()]*3

    # QR CODE
    qr = qrcode.QRCode(box_size=8, border=2); qr.add_data(f"https://wa.me/22501020304?text=Bonjour,%20je%20suis%20intéressé(e)%20par%20votre%20promotion.")
    qr_img = qr.make_image(fill_color="white", back_color="transparent").convert('RGBA')
    img.paste(qr_img, (int(1080 - qr_img.width * 1.2), 60), qr_img)

    # Textes
    draw.text((540, 350), "\n".join(textwrap.wrap(promo_text.upper(), width=15)), font=font_heavy, fill='white', anchor='mm', align='center')
    draw.text((540, 550), f"par {req.nom}", font=font_medium, fill='#FFD700', anchor='mm', align='center')
    draw.text((540, 980), f"Offre valable jusqu'au {req.date}", font=font_light, fill='white', anchor='ms', align='center')
    draw.text((120, 100), "Scannez pour commander !", font=font_light, fill='white', anchor='ms', align='center')

    img = img.convert("RGB"); img.save(img_path)
    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")

# ... (Les endpoints /generate-message, /chat, et /log-feedback restent les mêmes que la version précédente) ...
@app.post("/generate-message", tags=["Générateurs"])
async def generate_message(req: MessageRequest):
    if not text_model: return {"message_text": f"Promo chez {req.nom}: {req.service} ! {req.offre}. Contactez-nous !"}
    prompt = f"""Tu es un expert en marketing digital pour les petites entreprises africaines. Rédige un message court et percutant pour une publication WhatsApp et Facebook. soit libre et créatif, ne te contente pas seulement du modèle.  Utilise les techniques de copywriting. Le ton doit être joyeux, professionnel et donner envie. - Artisan: {req.nom} ({req.metier}) - Service/Produit: {req.service} - Offre Spéciale: {req.offre}. Termine par un appel à l'action clair (ex: "Contactez-nous vite !", "Profitez-en !"). Utilise 2-3 emojis pertinents. ✨📞🎉"""
    response = text_model.generate_content(prompt); return {"message_text": response.text}

@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not text_model: return {"reply": "Désolé, service IA indisponible."}
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
    try: response = text_model.generate_content(prompt); return {"reply": response.text}
    except Exception as e: print(f"❌ Erreur Gemini: {e}"); return {"reply": "Oups, une erreur est survenue."}

@app.post("/log-feedback", tags=["Assistant IA"])
async def log_feedback(req: FeedbackRequest):
    print(f"--- FEEDBACK: {req.rating} --- | Message: {req.message} | Réponse: {req.response}"); return {"status": "Feedback reçu"}
