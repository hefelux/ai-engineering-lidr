import argparse
import math
import sys
from pathlib import Path

# para poder importar "app" corriendo el script desde la carpeta del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embedding_pipeline.embedder import OpenAIEmbedder


# Similitud coseno a mano: producto punto dividido por el producto de las normas
def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


def main():
    parser = argparse.ArgumentParser(description="Similitud coseno entre dos textos")
    parser.add_argument("--text-a", required=True)
    parser.add_argument("--text-b", required=True)
    args = parser.parse_args()

    embedder = OpenAIEmbedder()
    vector_a = embedder.embed_one(args.text_a)
    vector_b = embedder.embed_one(args.text_b)

    print(f"Text A: {args.text_a}")
    print(f"Text B: {args.text_b}")
    print(f"Cosine similarity: {cosine_similarity(vector_a, vector_b):.4f}")


if __name__ == "__main__":
    main()
