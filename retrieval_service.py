import os
import requests
from dotenv import load_dotenv
from logging_ctx import request_id_var, user_var

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
            auth=(
                os.environ.get("RAG_SERVICE_USERNAME", "akadion-spring-backend"),
                os.environ.get("RAG_SERVICE_PASSWORD", "parola_spring_rag"),
            ),
            headers={"X-Request-ID": request_id_var.get(), "X-User": user_var.get()},
            timeout=30.0,
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

                client = QdrantClient(host=host, port=port, timeout=10.0)

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

def cauta_contexte_scroll(curs_id: int, max_saptamana: int, document_id: int = None, limit: int = 15) -> list[dict]:
    """
    Recuperează fragmente brute de text (chunks) din Qdrant fără căutare vectorială semantică.
    Folosește metoda de scroll pe baza ID-ului de curs/săptămână sau document_id.
    Pentru diversitate, face scroll la un număr mai mare de fragmente, le amestecă (shuffle) 
    și selectează un subset de dimensiune `limit`.
    """
    use_mock = os.environ.get("USE_QDRANT_MOCK", "true").lower() in ("true", "1", "yes")
    import random

    if not use_mock:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            host = os.environ.get("QDRANT_HOST", "localhost")
            port = int(os.environ.get("QDRANT_PORT", 6333))
            collection = os.environ.get("QDRANT_COLLECTION", "course_chunks")

            client = QdrantClient(host=host, port=port, timeout=10.0)

            # Construire filtre
            must_conditions = []
            if document_id is not None:
                must_conditions.append(models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)))
            else:
                must_conditions.append(models.FieldCondition(key="week_id", range=models.Range(lte=max_saptamana)))
                must_conditions.append(models.Filter(
                    should=[
                        models.FieldCondition(key="course_id", match=models.MatchValue(value=curs_id)),
                        models.FieldCondition(key="curs_id", match=models.MatchValue(value=curs_id))
                    ]
                ))

            scroll_filter = models.Filter(must=must_conditions)

            # Scroll pe mai multe puncte pentru a permite diversitatea prin amestecare
            scroll_results, _ = client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=100,
                with_payload=True,
                with_vectors=False
            )

            contexte_qdrant = []
            for pt in scroll_results:
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
                random.shuffle(contexte_qdrant)
                return contexte_qdrant[:limit]

        except Exception as e:
            print(f"[QDRANT WARNING] Nu s-a putut efectua scroll pe Qdrant: {e}. Folosim fallback mock.")

    # Mock Fallback
    contexte_gasite = []
    for doc in MOCK_DOCUMENTS:
        if document_id is not None:
            if doc.get("document_id") == document_id:
                contexte_gasite.append(doc)
        else:
            if doc["curs_id"] == curs_id and doc["week_id"] <= max_saptamana:
                contexte_gasite.append(doc)
    
    random.shuffle(contexte_gasite)
    return contexte_gasite[:limit]