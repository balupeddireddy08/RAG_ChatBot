import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file
load_dotenv()

# 1. Load a pretrained Sentence Transformer model
print("Attempting to load model 'all-MiniLM-L6-v2'...")
try:
    # Use the token from the environment variable
    token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("--- HUGGING_FACE_HUB_TOKEN not found in .env file ---")
    
    model = SentenceTransformer("all-MiniLM-L6-v2", use_auth_token=token)
    print("Model loaded successfully!")
except Exception as e:
    print(f"--- FAILED TO LOAD MODEL ---")
    print(f"Error: {e}")
    exit()

# The sentences to encode
sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]
print("\nSentences to encode:")
for s in sentences:
    print(f"- {s}")

# 2. Calculate embeddings by calling model.encode()
print("\nEncoding sentences...")
embeddings = model.encode(sentences)
print("Encoding complete!")
print("Shape of embeddings:", embeddings.shape)


# 3. Calculate the embedding similarities
print("\nCalculating similarities...")
similarities = model.similarity(embeddings, embeddings)
print("Similarities calculated!")
print(similarities) 