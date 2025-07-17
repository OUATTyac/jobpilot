from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route d'accueil
@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API JobPilot 🚀"}

# Modèle pour la génération de devis
class DevisRequest(BaseModel):
    client: str
    produit: str
    prix: str
    artisan: str
    date: str

@app.post("/generate-devis")
async def generate_devis(req: DevisRequest):
    return {
        "pdf_url": f"https://fake-pdf-storage.com/{uuid.uuid4()}.pdf"
    }

@app.post("/generate-message")
async def generate_message(data: dict):
    msg = f"{data['nom']} vous propose {data['service']} ! {data['offre']} Contactez-le !"
    return {"message_text": msg}

@app.post("/generate-promo")
async def generate_promo(data: dict):
    return {
        "promo_text": f"Promo spéciale de {data['nom']}: {data['promo']} - Offre valable jusqu’au {data['date']}."
    }
