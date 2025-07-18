from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer le dossier s’il n'existe pas
PDF_DIR = "generated_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# Données envoyées depuis Flutter
class DevisRequest(BaseModel):
    client: str
    produit: str
    prix: str
    artisan: str
    date: str

@app.post("/generate-devis")
async def generate_devis(req: DevisRequest):
    pdf_id = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_id)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(100, 800, "🧾 Devis professionnel généré par JobpilotAI")
    c.line(100, 795, 500, 795)

    c.setFont("Helvetica", 12)
    c.drawString(100, 760, f"Client : {req.client}")
    c.drawString(100, 735, f"Produit / Service : {req.produit}")
    c.drawString(100, 710, f"Prix : {req.prix} FCFA")
    c.drawString(100, 685, f"Artisan : {req.artisan}")
    c.drawString(100, 660, f"Date prévue : {req.date}")

    c.drawString(100, 620, "Merci pour votre confiance 🙏")
    c.showPage()
    c.save()

    # URL complète sur Render (ajuste avec ton domaine)
    base_url = "https://jobpilot-pnui.onrender.com"
    return {"pdf_url": f"{base_url}/pdf/{pdf_id}"}

@app.get("/pdf/{pdf_name}")
async def get_pdf(pdf_name: str):
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    if os.path.exists(pdf_path):
        return FileResponse(path=pdf_path, media_type='application/pdf', filename=pdf_name)
    return {"detail": "Fichier introuvable"}

@app.post("/generate-message")
async def generate_message(data: dict):
    msg = f"{data['nom']} vous propose {data['service']} ! {data['offre']} Contactez-le !"
    return {"message_text": msg}

@app.post("/generate-promo")
async def generate_promo(data: dict):
    return {"promo_text": f"Promo spéciale de {data['nom']}: {data['promo']} - Offre valable jusqu’au {data['date']}."}
