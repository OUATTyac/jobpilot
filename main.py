# main.py
import os
import uuid
import textwrap
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import qrcode
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from google.generativeai import types

# --- Configuration ---
app = FastAPI(title="JobpilotAI API", version="5.1.1 - Pro")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Gemini Config
text_model = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key); text_model = genai.GenerativeModel('models/gemini-2.5-flash')
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


# --- Modèles Pydantic
class LineItem(BaseModel):
    description: str
    price: str

class DevisRequest(BaseModel):
    type: str
    client: str
    artisan: str
    date: str
    items: List[LineItem]

class MessageRequest(BaseModel):
    nom: str
    metier: str
    service: str
    offre: str

class PromoRequest(BaseModel):
    nom: str
    product: str # On attend "product"
    price: str   # On attend "price"
    date: str

class ChatRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    message: str
    response: str
    rating: str


# --- Endpoints

@app.get("/", tags=["Status"])
def read_root():
    return {"message": "API JobpilotAI v5.1"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    pdf_id = f"doc_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)
    c = canvas.Canvas(pdf_path, pagesize=A4); width, height = A4
    primary_color = colors.HexColor("#4F46E5"); grey_color = colors.HexColor("#6B7280")
    try: c.drawImage("font/logo.png", 40, height - 100, width=60, height=60, preserveAspectRatio=True, mask='auto')
    except Exception: print("⚠️ Logo non trouvé.")
    c.setFont(FONT_BOLD_NAME, 10); c.setFillColor(grey_color); c.drawRightString(width - 50, height - 60, "Document préparé par :"); c.setFont(FONT_BOLD_NAME, 12); c.setFillColor(colors.black); c.drawRightString(width - 50, height - 75, req.artisan.upper())
    c.setFont(FONT_BOLD_NAME, 28); c.setFillColor(primary_color); c.drawString(40, height - 150, req.type.upper()); c.line(40, height - 155, width - 40, height - 155)
    c.setFont(FONT_NAME, 11); c.drawString(40, height - 190, "CLIENT :"); c.drawString(40, height - 210, "DATE :"); c.setFont(FONT_BOLD_NAME, 11); c.drawString(120, height - 190, req.client); c.drawString(120, height - 210, req.date)
    table_y_start = height - 260; c.setFillColor(primary_color); c.rect(40, table_y_start - 25, width - 80, 25, fill=1, stroke=0)
    c.setFont(FONT_BOLD_NAME, 11); c.setFillColor(colors.white); c.drawString(50, table_y_start - 18, "Description"); c.drawRightString(width - 50, table_y_start - 18, "Montant (FCFA)")
    current_y = table_y_start - 50; total = 0; c.setFont(FONT_NAME, 11); c.setFillColor(colors.black)
    for i, item in enumerate(req.items):
        if i % 2 == 1: c.setFillColor(colors.HexColor("#F3F4F6")); c.rect(40, current_y - 5, width - 80, 20, fill=1, stroke=0); c.setFillColor(colors.black)
        c.drawString(50, current_y, item.description); c.drawRightString(width - 50, current_y, item.price); current_y -= 20
        # CORRECTION ANTI-CRASH
        try:
            total += float(item.price.replace(',', '.'))
        except (ValueError, AttributeError):
            continue # On ignore si le prix n'est pas un nombre valide
    c.setFillColor(primary_color); c.rect(width / 2, current_y - 50, width / 2 - 40, 40, fill=1, stroke=0); c.setFont(FONT_BOLD_NAME, 16); c.setFillColor(colors.white); c.drawRightString(width - 50, current_y - 40, f"TOTAL : {total:.0f} FCFA")
    c.setFont(FONT_NAME, 9); c.setFillColor(grey_color); c.drawCentredString(width / 2, 60, "Document généré avec JobpilotAI."); c.setFont(FONT_BOLD_NAME, 10); c.setFillColor(colors.black); c.drawCentredString(width / 2, 40, "Merci pour votre confiance !")
    c.showPage(); c.save()
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"{req.type}_{req.client}.pdf")

@app.post("/generate-message", tags=["Générateurs"])
async def generate_message(req: MessageRequest):
    if not text_model: return {"message_text": f"Promo chez {req.nom}: {req.service} ! {req.offre}. Contactez-nous !"}
    prompt = f"""Tu es un expert en marketing digital en contexte Ivoirien pour les petites entreprises africaines. Rédige un message et percutant pour une publication WhatsApp et Facebook. Soit persuasif, libre et créatif. Le ton doit être joyeux, professionnel et donner envie. - Artisan: {req.nom} ({req.metier}) - Service/Produit: {req.service} - Offre Spéciale: {req.offre}. Termine par un appel à l'action clair. Utilise 2-3 emojis pertinents. ✨📞🎉"""
    response = text_model.generate_content(prompt); return {"message_text": response.text}


@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    if not text_model: raise HTTPException(status_code=503, detail="Service IA indisponible.")

    prompt = f"""Crée UN SEUL slogan court et percutant (3-5 mots max) pour une promotion sur des '{req.product}'. Rédige UNIQUEMENT le slogan, sans aucune phrase d'introduction comme "Voici un slogan". Exemple: 'Le style à vos pieds'."""
    try:
        response = text_model.generate_content(prompt)
        tagline = response.text.strip().replace('"', '').replace('*', '')
    except Exception:
        tagline = "L'Offre à ne pas Manquer !"

    img_id = f"promo_pro_{uuid.uuid4()}.png"; img_path = os.path.join(IMG_DIR, img_id)
    width, height = 1080, 1080
    try:
        background = Image.open("font/background.jpg").resize((width, height), Image.Resampling.LANCZOS)
    except FileNotFoundError:
        background = Image.new("RGB", (width, height))
        draw_bg = ImageDraw.Draw(background)
        for i in range(height):
            color = (int(20 + (i / height) * 30), int(20 + (i / height) * 20), int(80 + (i / height) * 60))
            draw_bg.line([(0, i), (width, i)], fill=color)

    if background.mode != 'RGBA': background = background.convert('RGBA')
    
    txt_layer = Image.new('RGBA', background.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    try:
        font_main = ImageFont.truetype("font/Poppins-Bold.ttf", 150)
        font_price = ImageFont.truetype("font/Poppins-Bold.ttf", 120)
        font_tagline = ImageFont.truetype("font/Poppins-Regular.ttf", 70)
        font_footer = ImageFont.truetype("font/Poppins-Regular.ttf", 40)
    except IOError:
        font_main, font_price, font_tagline, font_footer = [ImageFont.load_default()]*4

    # - DESIGN PROFESSIONNEL ---
    draw.rectangle([(0, 80), (width, 220)], fill="#FFD700")
    draw.text((width/2, 150), "PROMO SPÉCIALE", font=font_tagline, fill="black", anchor="mm")

    draw.text((width/2, 400), "\n".join(textwrap.wrap(req.product.upper(), width=15)), font=font_main, fill="white", anchor="mm", align="center", stroke_width=4, stroke_fill="black")
    draw.text((width/2, 600), f"À {req.price} FCFA", font=font_price, fill="#FFD700", anchor="mm", align="center")
    draw.text((width/2, 750), tagline, font=font_tagline, fill="white", anchor="mm", align="center")
    
    draw.text((width/2, 950), f"Chez {req.nom} - Jusqu'au {req.date}", font=font_footer, fill="white", anchor="mm", align="center")

    out = Image.alpha_composite(background, txt_layer)
    out = out.convert("RGB")
    out.save(img_path)

    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")



@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not text_model: return {"reply": "Désolé, service IA indisponible."}
    prompt = f"""Tu es "JobpilotAI", un assistant IA expert, maîtrisant le marketing digital et le copywriting; amical et encourageant, conçu spécifiquement pour les artisans et petits entrepreneurs en Afrique. Ton rôle est de fournir des conseils pratiques, pertinents et des idées créatives. Tu peux : - Aider à trouver des slogans publicitaires percutants. - Rédiger des messages professionnels pour des clients (remerciements, relances, annonces, publications). - Donner des idées de promotions ou de nouveaux services. - Proposer des stratégies simples pour améliorer la visibilité sur les réseaux sociaux. - Aider à structurer des devis ou des factures. Règles importantes : 1. Ton ton doit être simple, positif et facile à comprendre. 2. Utilise des emojis de manière pertinente pour rendre la conversation plus vivante. ✨👍 3. Si on te pose une question hors de ton domaine (politique, science, etc.), réponds poliment que tu es spécialisé dans l'aide aux entrepreneurs et propose de revenir au sujet. 4. Garde tes réponses concises et directes. Question: "{req.message}". Réponse:"""
    try: response = text_model.generate_content(prompt); return {"reply": response.text}
    except Exception as e: print(f"❌ Erreur Gemini: {e}"); return {"reply": "Oups, une erreur est survenue."}

@app.post("/log-feedback", tags=["Assistant IA"])
async def log_feedback(req: FeedbackRequest):
    print(f"--- FEEDBACK: {req.rating} --- | Message: {req.message} | Réponse: {req.response}"); return {"status": "Feedback reçu"}
