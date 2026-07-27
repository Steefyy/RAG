from pydantic import BaseModel
from typing import List

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    studentId: int
    cursId: int
    maxSaptamanaParcursa: int
    intrebare: str
    istoricConversatie: List[Message] = []

class ChatResponse(BaseModel):
    raspuns: str
    surseFolosite: List[int] = []
