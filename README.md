# LLM Response Service — RAG & Chat Orchestrator (Persoana A)

Acest proiect reprezintă microserviciul central de **Chat & RAG Orchestrator** dezvoltat în FastAPI pentru o platformă universitara

## 🎓 Ce face acest proiect?
Sistemul funcționează ca un **Asistent Academic Inteligent**:
1. **Prelucrează întrebările studenților** și oferă răspunsuri structurate în limba română.
2. **Previne Halucinațiile (Strict Grounding)**: Răspunde **doar** pe baza fișierelor de curs încărcate de profesori.
3. **Izolează Cunoștințele pe Săptămâni**: Un student din Săptămâna 3 **nu primește** informații din Săptămânile 4 sau 5.
4. **Protejează AI-ul (Prompt Injection Guard)**: Blochează tentativele de manipulare ale prompt-ului (ex: *"ignora regulile..."*).
5. **Integrează Reranker-ul și Baza de Date Vectorială Qdrant** pentru a furniza cele mai relevante surse.

---

> 📘 **Documentația Completă a Proiectului**:  
> Pentru o explicație detaliată a fiecărei componente, digrame de flux și fișiere, deschide [DOCUMENTATIE_RAG.md](DOCUMENTATIE_RAG.md).

---

## 🚀 Rulare Rapidă

### Rulare Locală (Dezvoltare):
```powershell
cd llm-response-service
.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```
Swagger UI: `http://localhost:8000/docs`

### Rulare cu Docker Compose:
```powershell
docker compose up --build
```
