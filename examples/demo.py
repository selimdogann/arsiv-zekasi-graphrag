"""
Uçtan uca demo — GraphRAGCore'un tüm yeteneklerini gerçek belgelerle gösterir.

Çalıştırma:
    PYTHONPATH=. python3 examples/demo.py
"""
import os

from graphrag.composition import build_core

_HERE = os.path.dirname(os.path.abspath(__file__))
_DOC1 = os.path.join(_HERE, "documents", "sozlesme_a.txt")
_DOC2 = os.path.join(_HERE, "documents", "sozlesme_b.txt")


def main() -> None:
    core = build_core()

    print("=== BELGE YÜKLEME (INGEST) ===")
    doc1 = core.ingest(_DOC1)
    print(f"{os.path.basename(_DOC1)} -> {doc1.state}")
    doc2 = core.ingest(_DOC2)
    print(f"{os.path.basename(_DOC2)} -> {doc2.state}")

    print("\n=== SORU-CEVAP (RAG) ===")
    soru = "Proje Zeus kimin projesi?"
    print(f"Soru: {soru}")
    print(core.answer(soru))

    print("\n=== GRAF KÖPRÜ BULMA ===")
    print(core.find_connection("Acme Holding", "Gamma Danışmanlık"))


if __name__ == "__main__":
    main()
