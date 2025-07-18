from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DevisRequest(BaseModel):
    client: str
    produit: str
    prix: str
    artisan: str
    date: str

@app.post("/generate-devis")
async def generate_devis(req: DevisRequest):
    # Génération du PDF en mémoire
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 800, f"Devis pour {req.client}")
    c.drawString(100, 780, f"Produit / Service : {req.produit}")
    c.drawString(100, 760, f"Prix : {req.prix} FCFA")
    c.drawString(100, 740, f"Artisan : {req.artisan}")
    c.drawString(100, 720, f"Date prévue : {req.date}")
    c.drawString(100, 700, "Merci de faire confiance à JobpilotAI !")
    c.showPage()
    c.save()
    buffer.seek(0)

    # Renvoi du PDF en tant que flux binaire
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=devis_{uuid.uuid4().hex}.pdf"
    })

@app.post("/generate-message")
async def generate_message(data: dict):
    msg = f"{data['nom']} vous propose {data['service']} ! {data['offre']} Contactez-le !"
    return {"message_text": msg}

@app.post("/generate-promo")
async def generate_promo(data: dict):
    return {
        "promo_text": f"Promo spéciale de {data['nom']}: {data['promo']} - Offre valable jusqu’au {data['date']}."
    }
