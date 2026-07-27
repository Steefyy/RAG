import os
import httpx
from pydantic import BaseModel

RERANKER_URL = os.environ.get("RERANKER_URL", "http://localhost:8002/api/rerank/chunks")

# Definim modelele contractului de Reranker conform specificatiilor primite de la Persoana C
class Chunk(BaseModel):
    text: str
    score: float
    chunk_id: str

class RerankRequest(BaseModel):
    query: str
    chunks: list[Chunk]
    top_k: int

class RerankedChunk(BaseModel):
    text: str
    rerank_score: float
    chunk_id: str
    original_rank: int

class RerankResponse(BaseModel):
    reranked_chunks: list[RerankedChunk]


def reordoneaza_contexte(intrebare: str, contexte_brute: list) -> list:
    """
    Trimite documentele brute catre serviciul de Reranker (Persoana C).
    Daca serviciul Persoanei C este offline sau neterminat, 
    facem un fallback simulat si pastram primele 5 rezultate.
    """
    if not contexte_brute:
        return []
        
    try:
        # Pregatim datele in formatul cerut de contractul de Reranker (RerankRequest)
        chunks_payload = []
        for doc in contexte_brute:
            chunks_payload.append({
                "text": doc["text"],
                # Deoarece suntem in faza de mock pentru vector search, punem un scor initial simulat de 1.0
                "score": 1.0, 
                "chunk_id": str(doc["document_id"])
            })

        request_body = {
            "query": intrebare,
            "chunks": chunks_payload,
            "top_k": 5
        }

        # Apel HTTP real catre serviciul de Reranker al Persoanei C
        with httpx.Client(timeout=5.0) as client:
            response = client.post(RERANKER_URL, json=request_body)
            
            if response.status_code == 200:
                data = response.json()
                # Parsam raspunsul conform contractului RerankResponse
                reranked_chunks = data.get("reranked_chunks", [])
                
                # Reordonam si refacem structura de documente pentru sistemul nostru
                contexte_ordonate = []
                for rc in reranked_chunks:
                    doc_id = int(rc["chunk_id"]) # convertim inapoi la int pentru compatibilitate cu Java
                    
                    # Gasim documentul original corespunzator din contextul brut pentru a pastra restul metadatelor (week_id, curs_id)
                    original_doc = next((d for d in contexte_brute if d["document_id"] == doc_id), None)
                    if original_doc:
                        contexte_ordonate.append(original_doc)
                    else:
                        # Altfel cream o structura minimala pe baza a ce a returnat Reranker-ul
                        contexte_ordonate.append({
                            "document_id": doc_id,
                            "curs_id": 45,
                            "week_id": 1,
                            "text": rc["text"]
                        })
                return contexte_ordonate
    except Exception as e:
        print(f"[RERANKER WARNING] Serviciul Reranker offline sau eroare: {e}. Folosim fallback simulat.")
        
    # Fallback simulat: luam primele 5 contexte brute
    return contexte_brute[:5]
