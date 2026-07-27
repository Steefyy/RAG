import requests
import json

# URL-ul serviciului tau de Chat (Persoana A - Port 8000)
url = "http://localhost:8000/chat"

# Payload-ul exact al cererii (conform contractului cu Monolitul Java)
payload = {
    "intrebare": "Care este tema cursului si ce subiecte se discuta?",
    "studentId": 101,
    "cursId": 1,
    "maxSaptamanaParcursa": 5
}

headers = {
    "Content-Type": "application/json"
}

print("[+] Trimitere cerere POST /chat catre Docker...")
try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}\n")
    print("--- Raspuns RAG Primit de la Serviciul din Docker ---")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"[ERR] Eroare la trimiterea cererii: {e}")
