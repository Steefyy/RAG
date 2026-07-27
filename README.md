# Academic RAG System

Sistem integrat de **Asistent Academic Inteligent (RAG)** dezvoltat în FastAPI și bazat pe microservicii pentru o platformă universitară.

## 🎓 Descriere Generală

Sistemul furnizează răspunsuri precise și fundamentate pe suporturile de curs furnizate de profesori:
1. **Prevenirea halucinațiilor (Strict Grounding)**: Răspunde **exclusiv** pe baza documentelor de curs reale (PDF/Word).
2. **Izolarea cunoștințelor pe Săptămâni**: Un student din Săptămâna 3 are acces strict la informațiile din Săptămânile 1–3.
3. **Scut anti-Prompt Injection**: Filtru local offline pentru blocarea tentativelor de manipulare a AI-ului.
4. **Arhitectură duală RAG**: Vectorizare prin Embedder (`BAAI/bge-m3`), căutare vectorială în Qdrant și reclasificare semantică prin CrossEncoder Reranker (`mmarco-mMiniLMv2`).
5. **Integrare LLM**: Generare răspunsuri academice structurate în limba română prin modelul Google Gemini.

---

> 📘 **Documentația Detaliată a Arhitecturii**:  
> Pentru explicații exhaustive ale fiecărui microserviciu, digrame de flux Mermaid și configurări, deschideți [DOCUMENTATIE_RAG.md](DOCUMENTATIE_RAG.md).

---

## 🚀 Pornire Rapidă (Docker Compose)

Porniți întreaga suită de microservicii (Chat Orchestrator, Embedder Service, Reranker Service și Qdrant Vector DB):

```powershell
cd llm-response-service

# 1. Configurați cheia API Gemini în .env
copy .env.example .env

# 2. Lansare containere
docker compose up --build
```

### Dashboard-uri & Interfețe Swagger UI:
- **Chat Orchestrator API**: `http://localhost:8000/docs`
- **Embedder Service API**: `http://localhost:8001/docs`
- **Reranker Service API**: `http://localhost:8002/docs`
- **Qdrant Vector DB**: `http://localhost:6333/dashboard`
