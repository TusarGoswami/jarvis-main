import os
import re
from typing import List, Dict

class LocalRAGStore:
    def __init__(self):
        self.documents: List[Dict[str, str]] = [
            {
                "id": "system_info",
                "title": "Vocalis AI System Manual",
                "content": "Vocalis AI is a multimodal voice and vision operating system. It features screen context analysis, real-time audio waveforms, multilingual neural speech (English, Hindi, Bengali), and automated tool execution."
            },
            {
                "id": "features_doc",
                "title": "Supported Features",
                "content": "Vocalis AI supports desktop application launching, active window switching, YouTube search, web navigation, Android ADB automation, live system telemetry monitoring, and screen understanding."
            },
            {
                "id": "hackathon_brief",
                "title": "2026 Hackathon Criteria",
                "content": "Originality, technical depth, multimodal co-operation, graceful degradation, evaluation harness with 20 test cases, confidence scoring, and Next.js + FastAPI stack."
            }
        ]

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, str]]:
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return []

        scored = []
        for doc in self.documents:
            content_words = set(re.findall(r'\w+', doc["content"].lower() + " " + doc["title"].lower()))
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((overlap, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

rag_store = LocalRAGStore()
