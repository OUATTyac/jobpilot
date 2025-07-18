# main.py
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import textwrap

# --- Configuration ---
app = FastAPI()

# Configuration CORS pour autoriser les requêtes de votre app Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de l'API Gemini
# IMPORTANT: Mettez votre clé API dans les variables d'environnement de Render
# Clé : GEMINI_API_KEY, Valeur : VOTRE_VRAIE_CLE
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
    print("Gemini API configurée avec succès.")
except Exception as e:
    print(f"Erreur de configuration Gemini: {e}")
    model = None # Gérer le cas où la clé n'est pas trouvée

# Création des dossiers pour les fichiers générés
PDF_DIR = "generated_pdfs"
IMG_DIR = "generated_images"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


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
    
# --- Endpoints de l'API ---

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l’API JobpilotAI V2 🚀 - Prête pour le hackathon !"}

@app.post("/generate-devis", response_class=FileResponse)
async def generate_devis(req: DevisRequest):
    pdf_id = f"devis_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 800, "🧾 Devis Professionnel")
    c.setFont("Helvetica", 10)
    c.drawString(72, 785, f"Généré par JobpilotAI pour {req.artisan}")
    c.line(72, 780, 520, 780)

    c.setFont("Helvetica", 12)
    c.drawString(72, 740, f"Client : {req.client}")
    c.drawString(72, 715, f"Produit / Service : {req.produit}")
    c.drawString(72, 690, f"Prix : {req.prix} FCFA")
    c.drawString(72, 665, f"Date prévue : {req.date}")

    c.setFont("Helvetica-Oblique", 11)
    c.drawString(72, 620, "Merci pour votre confiance 🙏")
    c.showPage()
    c.save()

    return FileResponse(path=pdf_path, media_type='application/pdf', filename=f"Devis_{req.client}.pdf")

@app.post("/generate-message")
async def generate_message(req: MessageRequest):
    if not model:
        return {"message_text": "Erreur: L'API IA n'est pas configurée."}
        
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

@app.post("/generate-promo-image", response_class=FileResponse)
async def generate_promo_image(req: PromoRequest):
    # 1. Générer le texte avec Gemini
    promo_text = "Erreur IA"
    if model:
        prompt = f"""
        Tu es JobpilotAI. Crée une accroche marketing très courte et puissante (5 à 10 mots max) pour une promotion.
        - Artisan: {req.nom}
        - Promotion: {req.promo}
        - Fin de l'offre: {req.date}
        Rédige uniquement l'accroche.
        """
        response = model.generate_content(prompt)
        promo_text = response.text.strip().replace('"', '')

    # 2. Créer l'image avec Pillow
    img_id = f"promo_{uuid.uuid4()}.png"
    img_path = os.path.join(IMG_DIR, img_id)
    
    # Création de l'image de fond
    img = Image.new('RGB', (1080, 1080), color = '#FFD700') # Or jaune
    draw = ImageDraw.Draw(img)

    # Chargement de la police (s'assurer qu'une police est disponible)
    try:
        title_font = ImageFont.truetype("font/Roboto-Bold.ttf", 90)
        subtitle_font = ImageFont.truetype("font/Roboto-Regular.ttf", 50)
    except IOError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        print("Police personnalisée non trouvée, utilisation de la police par défaut.")

    # 3. Écrire le texte sur l'image
    # Wrapper le texte pour qu'il ne dépasse pas
    wrapped_text = "\n".join(textwrap.wrap(promo_text, width=25))
    
    # Positionnement
    draw.text((540, 450), wrapped_text, font=title_font, fill='black', anchor='mm', align='center')
    draw.text((540, 700), f"Chez {req.nom}", font=subtitle_font, fill='black', anchor='mm', align='center')
    draw.text((540, 980), f"Offre valable jusqu'au {req.date}", font=subtitle_font, fill='black', anchor='ms', align='center')
    draw.text((540, 100), "✨ PROMO SPÉCIALE ✨", font=subtitle_font, fill='black', anchor='ms', align='center')

    img.save(img_path)

    return FileResponse(path=img_path, media_type='image/png', filename=f"Promo_{req.nom}.png")
