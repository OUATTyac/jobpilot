# main.py
import os
import uuid
import textwrap
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- Configuration ---
app = FastAPI(
    title="JobpilotAI API",
    description="API pour l'assistant IA des artisans africains.",
    version="2.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de l'API Gemini
model = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        print("✅ Gemini API configurée avec succès.")
    else:
        print("⚠️  Avertissement: La variable d'environnement GEMINI_API_KEY n'est pas définie.")
except Exception as e:
    print(f"❌ Erreur de configuration Gemini: {e}")

# Création des dossiers et enregistrement des polices
PDF_DIR = "generated_pdfs"
IMG_DIR = "generated_images"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

FONT_NAME = 'Helvetica' # Police de secours
try:
    pdfmetrics.registerFont(TTFont('NotoSans', 'font/NotoSans-Regular.ttf'))
    FONT_NAME = 'NotoSans'
    print("✅ Police NotoSans pour PDF enregistrée.")
except Exception as e:
    print(f"⚠️ Police NotoSans non trouvée, utilisation de Helvetica. Erreur: {e}")


# --- Modèles de données Pydantic ---
class DevisRequest(BaseModel):
    client: str
    produit: str
    prix: str
    artisan: str
    date: str

class MessageRequest(BaseModel):
    nom: str
    metier: str
    service: str
    offre: str

class PromoRequest(BaseModel):
    nom: str
    promo: str
    date: str

class ChatRequest(BaseModel):
    message: str


# --- Endpoints de l'API ---

@app.get("/", tags=["Status"])
def read_root():
    return {"message": "Bienvenue sur l’API JobpilotAI V2 🚀 - Prête pour le hackathon !"}

@app.post("/generate-devis", tags=["Générateurs"], response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    pdf_id = f"devis_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)
    c = canvas.Canvas(pdf_path, pagesize=A4)

    c.setFont(FONT_NAME, 16)
    c.drawString(72, 800, "🧾 Devis Professionnel")
    c.setFont(FONT_NAME, 10)
    c.drawString(72, 785, f"Généré par JobpilotAI pour {req.artisan}")
    c.line(72, 780, 520, 780)
    c.setFont(FONT_NAME, 12)
    c.drawString(72, 740, f"Client : {req.client}")
    c.drawString(72, 715, f"Produit / Service : {req.produit}")
    c.drawString(72, 690, f"Prix : {req.prix} FCFA")
    c.drawString(72, 665, f"Date prévue : {req.date}")
    c.setFont(FONT_NAME, 11)
    c.drawString(72, 620, "Merci pour votre confiance 🙏")
    c.showPage()
    c.save()
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"Devis_{req.client}.pdf")

@app.post("/generate-message", tags=["Générateurs"])
async def generate_message(req: MessageRequest):
    if not model:
        return {"message_text": f"Super promo chez {req.nom} ! Profitez de '{req.service}' avec {req.offre}. Contactez-nous vite ! (Message généré sans IA)"}
    
    # --- L'ERREUR ÉTAIT ICI. MAINTENANT CORRIGÉE ---
    prompt = f"""
Tu es JobpilotAI, un assistant pour artisans africains. Rédige un message WhatsApp court, amical et percutant en français simple.
Utilise un ou deux emojis pertinents.
- Artisan: {req.nom} ({req.metier})
- Service: {req.service}
- Offre: {req.offre}
Rédige uniquement le message pour le client.
"""
    response = model.generate_content(prompt)
    return {"message_text": response.text}

@app.post("/generate-promo-image", tags=["Générateurs"], response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    promo_text = "Offre Spéciale !"
    if model:
        prompt = f"""
Tu es JobpilotAI. Crée une accroche marketing très courte et puissante (5 à 10 mots max) pour une promotion.
- Artisan: {req.nom}
- Promotion: {req.promo}
- Fin de l'offre: {req.date}
Rédige uniquement l'accroche.
"""
        try:
            response = model.generate_content(prompt)
            promo_text = response.text.strip().replace('"', '')
        except Exception:
            pass

    img_id = f"promo_{uuid.uuid4()}.png"
    img_path = os.path.join(IMG_DIR, img_id)
    img = Image.new('RGB', (1080, 1080), color='#FFD700')
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("font/Poppins-Bold.ttf", 90)
        subtitle_font = ImageFont.truetype("font/Poppins-Regular.ttf", 50)
    except IOError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        print("⚠️ Police Poppins non trouvée, utilisation de la police par défaut.")

    wrapped_text = "\n".join(textwrap.wrap(promo_text, width=25))
    draw.text((540, 450), wrapped_text, font=title_font, fill='black', anchor='mm', align='center')
    draw.text((540, 700), f"Chez {req.nom}", font=subtitle_font, fill='black', anchor='mm', align='center')
    draw.text((540, 980), f"Offre valable jusqu'au {req.date}", font=subtitle_font, fill='black', anchor='ms', align='center')
    draw.text((540, 100), "✨ PROMO SPÉCIALE ✨", font=subtitle_font, fill='black', anchor='ms', align='center')
    img.save(img_path)
    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")

@app.post("/chat", tags=["Assistant IA"])
async def handle_chat(req: ChatRequest):
    if not model:
        return {"reply": "Désolé, le service IA est actuellement indisponible."}

    prompt = f"""
Tu es "JobpilotAI", un assistant IA expert, amical et encourageant, conçu spécifiquement pour les artisans et petits entrepreneurs en Afrique.

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
4. Garde tes réponses concises et directes.

Voici la question de l'artisan : "{req.message}"

Ta réponse :
"""
    try:
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"❌ Erreur lors de l'appel à Gemini: {e}")
        return {"reply": "Oups, quelque chose s'est mal passé. Pourriez-vous reformuler votre question ?"}
