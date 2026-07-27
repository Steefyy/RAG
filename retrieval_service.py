import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Documente simulate pe cursuri si saptamani (metadate)
MOCK_DOCUMENTS = [
    {
        "document_id": 101,
        "curs_id": 45,
        "week_id": 1,
        "text": "Introducere in ORM si Java Persistence API. Entity-urile sunt clase simple POJO mapate pe tabele.",
    },
    {
        "document_id": 102,
        "curs_id": 45,
        "week_id": 3,
        "text": "EntityManager este interfata principala care gestioneaza ciclul de viata al entity-urilor. Operatii: persist, merge, remove, find.",
    },
    {
        "document_id": 103,
        "curs_id": 45,
        "week_id": 5,
        "text": "Relatiile in JPA: OneToOne, OneToMany, ManyToOne, ManyToMany. FetchType.LAZY vs FetchType.EAGER.",
    },
    {
        "document_id": 201,
        "curs_id": 10,
        "week_id": 2,
        "text": "Structuri de date fundamentale: Liste inlatuite, Stive, Cozi. Complexitatea operatiilor este O(1) la capete.",
    }
]

def obtine_embedding_intrebare(intrebare: str) -> list[float] | None:
    """
    Apeleaza Embedder Service (POST /api/query/embed) pentru a obtine vectorul de embedding al intrebarii.
    """
    embedder_url = os.environ.get("EMBEDDER_URL", "http://localhost:8001/api/query/embed")
    try:
        response = requests.post(
            embedder_url,
            json={"text": intrebare},
            timeout=5.0
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("embedding")
        else:
            print(f"[EMBEDDER WARNING] Status code {response.status_code} primit de la Embedder Service.")
    except Exception as e:
        print(f"[EMBEDDER WARNING] Nu s-a putut obtine embedding-ul de la Embedder Service ({embedder_url}): {e}")
    return None

def cauta_context(intrebare: str, curs_id: int, max_saptamana: int) -> list[dict]:
    """
    Filtreaza documentele conform regulilor din contract:
    - cursId == curs_id
    - nrSaptamana <= max_saptamana (in cazul nostru week_id <= max_saptamana)

    Daca USE_QDRANT_MOCK=false in .env:
    1. Obține vectorul întrebării apelând Embedder Service (POST /api/query/embed)
    2. Efectuează o căutare semantică vectorială pe serverul Qdrant filtrată pe curs și săptămână.
    """
    use_mock = os.environ.get("USE_QDRANT_MOCK", "true").lower() in ("true", "1", "yes")

    if not use_mock:
        try:
            # 1. Preluare vector embedding pentru intrebare de la Embedder Service
            query_vector = obtine_embedding_intrebare(intrebare)

            if query_vector:
                from qdrant_client import QdrantClient
                from qdrant_client.http import models

                host = os.environ.get("QDRANT_HOST", "localhost")
                port = int(os.environ.get("QDRANT_PORT", 6333))
                collection = os.environ.get("QDRANT_COLLECTION", "course_chunks")

                client = QdrantClient(host=host, port=port, timeout=5.0)

                # Filtru de metadate pe curs si saptamana parcursa
                scroll_filter = models.Filter(
                    should=[
                        models.FieldCondition(key="course_id", match=models.MatchValue(value=curs_id)),
                        models.FieldCondition(key="curs_id", match=models.MatchValue(value=curs_id))
                    ],
                    must=[
                        models.FieldCondition(key="week_id", range=models.Range(lte=max_saptamana))
                    ]
                )

                # Cautare vectorială semantică
                if hasattr(client, "search"):
                    search_results = client.search(
                        collection_name=collection,
                        query_vector=query_vector,
                        query_filter=scroll_filter,
                        limit=10
                    )
                else:
                    response_qp = client.query_points(
                        collection_name=collection,
                        query=query_vector,
                        query_filter=scroll_filter,
                        limit=10
                    )
                    search_results = response_qp.points

                contexte_qdrant = []
                for pt in search_results:
                    payload = pt.payload or {}
                    text_content = payload.get("chunk_text") or payload.get("text", "")
                    c_id = payload.get("course_id") or payload.get("curs_id", curs_id)
                    doc_id = payload.get("document_id", 999)
                    w_id = payload.get("week_id", max_saptamana)

                    contexte_qdrant.append({
                        "document_id": int(doc_id) if str(doc_id).isdigit() else 999,
                        "curs_id": int(c_id),
                        "week_id": int(w_id),
                        "text": str(text_content)
                    })

                if contexte_qdrant:
                    return contexte_qdrant
            else:
                print("[QDRANT WARNING] Vectorul de interogare nu a putut fi extras. Folosim fallback mock.")
        except Exception as e:
            print(f"[QDRANT WARNING] Nu s-a putut efectua interogarea pe Qdrant: {e}. Folosim fallback mock.")

    # Cautare pe date simulate (Mock Fallback)
    contexte_gasite = []
    cuvinte_intrebare = set([w for w in intrebare.lower().split() if len(w) > 2])

    for doc in MOCK_DOCUMENTS:
        if doc["curs_id"] == curs_id and doc["week_id"] <= max_saptamana:
            cuvinte_doc = set([w for w in doc["text"].lower().split() if len(w) > 2])
            if cuvinte_intrebare.intersection(cuvinte_doc):
                contexte_gasite.append(doc)

    return contexte_gasite
