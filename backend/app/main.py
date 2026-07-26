from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # pour autoriser les requêtes provenant du frontend. CORSMiddleware est un middleware qui gère les en-têtes CORS (Cross-Origin Resource Sharing) pour permettre à votre API d'accepter des requêtes provenant de différents domaines, ce qui est souvent nécessaire lorsque le frontend et le backend sont hébergés sur des domaines différents.
#import uvicorn

from app.chat.router import router as chat_router
from app.config import settings # s il ne trouve pas une variable d environnement, il donne ValidationError 


app = FastAPI(title="Document Copilot API") #Toutes les routes, middlewares, dépendances, etc., seront enregistrés dans cet objet app.

app.add_middleware(
    CORSMiddleware,#Un middleware est un composant qui intercepte toutes les requêtes avant qu'elles n'atteignent vos routes.
    allow_origins=settings.allowed_origins,# Ainsi seul ce frontend pourra appeler votre API.
    allow_credentials=True,#Autorise l'envoi :cookies, Authorization Header, Bearer Token. Sans cela, un navigateur peut bloquer certaines requêtes.
    allow_methods=["*"],#Toutes les méthodes HTTP sont autorisées(GET, POST, PUT, DELETE, PATCH, OPTIONS). Cela signifie que votre API peut accepter des requêtes de n'importe quelle méthode HTTP.
    allow_headers=["*"],#Tous les headers sont acceptés.
)

app.include_router(chat_router)

#Les services comme Docker, Kubernetes ou un load balancer peuvent régulièrement appeler Get /health
@app.get("/health") #quand on fait un GET sur /health, on appelle la fonction health() qui renvoie un dictionnaire avec le statut de l'API. C'est une route de santé pour vérifier si l'API est en ligne et fonctionne correctement.
async def health() -> dict[str, str]:#FastAPI est basé sur asyncio. Même si cette fonction ne fait rien d'asynchrone, on utilise souvent async pour être cohérent avec les futures routes qui feront des appels à une base de données, à des API, etc.
    return {"status": "ok"}


#dans la pratique on n utilise pas ce bloc if __name__ == "__main__": pour lancer l application. On utilise uvicorn directement depuis la ligne de commande: uvicorn app.main:app --reload au lieu de uv run main.py 
# if __name__ == "__main__":
#     uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
