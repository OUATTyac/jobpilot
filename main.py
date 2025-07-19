# main.py - VERSION FINALE ET STABLE
import os
import uuid
import textwrap
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- Configuration ---
app = FastAPI(title="JobpilotAI API", version="4.1.0 - Stable")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Initialisation Gemini (Uniquement pour le texte) ---
text_model = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        text_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("✅ Gemini API (texte) configurée avec gemini-1.5-flash-latest.")
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
def read_root(): return {"message": "API JobpilotAI v4.1 - Prête pour la victoire !"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
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
    prompt = f"""Tu es un expert en marketing digital pour les petites entreprises africaines. Rédige un message court et percutant pour une publication WhatsApp et Facebook. Ne te contente pas du modèle, soit créatif. Le ton doit être joyeux, professionnel et donner envie. - Artisan: {req.nom} ({req.metier}) - Service/Produit: {req.service} - Offre Spéciale: {req.offre}. Termine par un appel à l'action clair. Utilise 2-3 emojis pertinents. ✨📞🎉"""
    response = text_model.generate_content(prompt)
    return {"message_text": response.text}

@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    if not text_model:
        raise HTTPException(status_code=503, detail="Le service IA n'est pas configuré.")
        
    promo_text = "Offre Spéciale !"
    prompt = f"""Crée une accroche marketing très courte (5-10 mots max) pour cette promotion : Artisan: {req.nom}, Promotion: {req.promo}, Fin: {req.date}. Rédige uniquement l'accroche."""
    try:
        response = text_model.generate_content(prompt)
        promo_text = response.text.strip().replace('"', '')
    except Exception as e:
        print(f"Erreur génération texte pour affiche: {e}")
    
    img_id = f"promo_{uuid.uuid4()}.png"
    img_path = os.path.join(IMG_DIR, img_id)
    
    try:
        img = Image.open("font/background.jpg")
    except FileNotFoundError:
        print("⚠️ background.jpg non trouvé, utilisation d'un fond jaune.")
        img = Image.new('RGB', (1080, 1080), color='#FFD700')

    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("font/Poppins-Bold.ttf", 110)
        subtitle_font = ImageFont.truetype("font/Poppins-Regular.ttf", 60)
        promo_font = ImageFont.truetype("font/Poppins-Bold.ttf", 70)
    except IOError:
        title_font, subtitle_font, promo_font = ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()
    
    draw.text((540, 400), "\n".join(textwrap.wrap(promo_text, width=20)), font=title_font, fill='white', anchor='mm', align='center')
    draw.text((540, 600), f"Chez {req.nom}", font=subtitle_font, fill='#FFD700', anchor='mm', align='center')
    draw.text((540, 100), "✨ PROMO SPÉCIALE ✨", font=promo_font, fill='white', anchor='ms', align='center')
    draw.text((540, 980), f"Valable jusqu'au {req.date}", font=subtitle_font, fill='white', anchor='ms', align='center')
    
    img = img.convert("RGB")
    img.save(img_path)
    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")

@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not text_model: return {"reply": "Désolé, le service IA est indisponible."}
    prompt = f"""Tu es "JobpilotAI", un assistant expert pour artisans en Afrique. Ton rôle : donner des conseils pratiques (slogans, messages, promos), formattés en Markdown simple (gras avec **, listes avec -). Ton ton: simple, positif. Question: "{req.message}". Réponse:"""
    try:
        response = text_model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"❌ Erreur Gemini: {e}")
        return {"reply": "Oups, une erreur est survenue."}

@app.post("/log-feedback", tags=["Assistant IA"])
async def log_feedback(req: FeedbackRequest):
    print(f"--- FEEDBACK: {req.rating} --- | Message: {req.message} | Réponse: {req.response}")
    return {"status": "Feedback reçu"}
