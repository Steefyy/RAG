from fastapi import FastAPI, HTTPException, Header, Depends
import os
import secrets
from models import ChatRequest, ChatResponse
from llm_service import genereaza_raspuns, verifica_conexiune
from prompt_builder import construieste_prompt
from retrieval_service import cauta_context
from reranker_service import reordoneaza_contexte
from security_guard import valideaza_intrebare

app = FastAPI(title="RAG Chatbot Service")

RAG_SHARED_SECRET = os.environ.get("RAG_SHARED_SECRET", "")

def verify_internal_token(x_internal_token: str = Header(None, alias="X-Internal-Token")):
    if not RAG_SHARED_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Serviciul RAG nu este configurat corect. Variabila RAG_SHARED_SECRET lipseste."
        )
    if not x_internal_token or not secrets.compare_digest(x_internal_token, RAG_SHARED_SECRET):
        raise HTTPException(
            status_code=401,
            detail="Acces neautorizat. Token intern invalid sau lipsa."
        )

@app.get("/health")
def health():
    connected = verifica_conexiune()
    status = "ok" if connected else "degraded"
    return {
        "status": status,
        "llm_provider": "gemini",
        "llm_connected": connected
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, token: str = Depends(verify_internal_token)):
    # 0. Rulam filtrul de securitate local (Prompt Injection Guard) - 100% Gratuit si Offline
    status_securitate = valideaza_intrebare(request.intrebare)
    if not status_securitate.safe:
        return ChatResponse(
            raspuns=(
                f"Cerere respinsă din motive de securitate. Întrebarea conține instrucțiuni nepermise. "
                f"Motiv: {status_securitate.reason}"
            ),
            surseFolosite=[]
        )

    # 1. Cautam si filtram contextul semantic din Qdrant
    context_chunks_brute = cauta_context(
        request.intrebare, request.cursId, request.maxSaptamanaParcursa
    )

    # 2. Reordonam si selectam cele mai relevante 5 propozitii prin Reranker (Persoana C)
    context_chunks = reordoneaza_contexte(request.intrebare, context_chunks_brute)

    # 3. Construim promptul cu contextul si istoricul trimis de monolit
    prompt = construieste_prompt(request.intrebare, request.istoricConversatie, context_chunks)

    # 4. Apelam LLM-ul (Gemini) cu parametrii de temperatura aplicati
    try:
        raspuns_text = genereaza_raspuns(prompt)
    except Exception:
        raise HTTPException(
            status_code=503, 
            detail="Serviciul LLM este momentan indisponibil. Incearca din nou in cateva momente."
        )

    # 5. Extragem document_id-urile ca surse folosite
    surse_folosite = list(set([c["document_id"] for c in context_chunks]))

    return ChatResponse(raspuns=raspuns_text, surseFolosite=surse_folosite)
