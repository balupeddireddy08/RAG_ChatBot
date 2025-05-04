# Modified rag_engine.py with improvements
import os
import re
import sys
import traceback
from typing import Tuple, List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import lancedb
import google.generativeai as genai
from rag_app.logging_config import logger

# Constants for file paths and settings
DB_DIR = "chat_data"
KNOWLEDGE_BASE_PATH = os.path.join(DB_DIR, "knowledge_base")
VECTOR_TABLE_NAME = "documents"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 5

# Ensure API key is available
if "GEMINI_API_KEY" not in os.environ:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the application.")

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Initialize the embedding model with improved error handling
try:
    # Disable some tensor ops that might cause issues
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Load the model with minimal settings
    logger.info("Attempting to load SentenceTransformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    
    # Test the model with a simple encoding to make sure it works
    test_embedding = model.encode("Test sentence for embedding.")
    logger.info(f"SentenceTransformer model loaded successfully. Embedding shape: {test_embedding.shape}")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
    logger.error(traceback.format_exc())
    # Set a flag to indicate we should use a simpler approach
    model = None
    logger.warning("Embedding model unavailable. RAG functionality will be limited.")

def text_to_chunks(text: str) -> List[str]:
    """Split text into overlapping chunks for processing"""
    logger.info(f"Splitting text into chunks of size {CHUNK_SIZE} with overlap {CHUNK_OVERLAP}")
    
    # Clean the text - remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Simple chunking by character count with overlap
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = text[i:i + CHUNK_SIZE]
        if len(chunk) > 50:  # Avoid too small chunks
            chunks.append(chunk)
    
    logger.info(f"Created {len(chunks)} text chunks")
    return chunks

def create_vector_store(chunks: List[str]) -> bool:
    """Create a vector store from text chunks"""
    try:
        # Ensure directory exists with absolute path
        abs_path = os.path.abspath(KNOWLEDGE_BASE_PATH)
        os.makedirs(abs_path, exist_ok=True)
        logger.info(f"Knowledge base directory ensured: {abs_path}")
        
        # Check if we have a valid model
        if model is None:
            logger.error("Embedding model not available, cannot create vector store")
            return False
        
        # Connect to LanceDB with absolute path
        logger.info(f"Connecting to LanceDB at: {abs_path}")
        db = lancedb.connect(abs_path)
        
        # Generate embeddings for each chunk
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                # Process chunks individually to avoid memory issues
                embedding = model.encode(chunk)
                embeddings.append(embedding)
                # Log progress for large datasets
                if i % 20 == 0 and i > 0:
                    logger.info(f"Processed {i}/{len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error encoding chunk {i}: {str(e)}")
                # Use a zero vector as fallback (with correct dimensions)
                embeddings.append(np.zeros(384))  # MiniLM-L6 uses 384 dimensions
        
        # Create data for the table
        data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data.append({
                "id": i,
                "text": chunk,
                "vector": embedding.tolist()
            })
        
        # Create or overwrite the table
        logger.info(f"Creating LanceDB table: {VECTOR_TABLE_NAME}")
        
        # Check if table exists and drop it
        if VECTOR_TABLE_NAME in db.table_names():
            logger.info(f"Dropping existing table: {VECTOR_TABLE_NAME}")
            db.drop_table(VECTOR_TABLE_NAME)
        
        # Create new table with explicit schema
        table = db.create_table(
            VECTOR_TABLE_NAME,
            data=data,
            mode="overwrite"
        )
        
        # Verify table creation
        if VECTOR_TABLE_NAME in db.table_names():
            logger.info(f"Vector store created successfully with {len(data)} entries")
            return True
        else:
            logger.error("Table creation failed: table not found in database")
            return False
            
    except Exception as e:
        logger.error(f"Failed to create vector store: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def process_documents(text: str) -> Tuple[bool, str]:
    """Process input documents and create knowledge base
    
    Args:
        text: The input text to process
        
    Returns:
        Tuple of (success, message)
    """
    try:
        logger.info("Starting document processing")
        if not text or len(text) < 100:
            logger.warning("Text too short for processing")
            return False, "Text too short for processing. Please provide more content."
        
        # Split text into chunks
        chunks = text_to_chunks(text)
        if not chunks:
            logger.warning("No chunks created from text")
            return False, "Could not create chunks from the provided text."
        
        # Create vector store
        if create_vector_store(chunks):
            logger.info("Knowledge base created successfully")
            return True, f"Knowledge base created successfully with {len(chunks)} text chunks."
        else:
            logger.error("Failed to create knowledge base")
            return False, "Failed to create knowledge base. Check logs for details."
    except Exception as e:
        logger.error(f"Error in document processing: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error processing documents: {str(e)}"

def check_knowledge_base_exists() -> bool:
    """Check if the knowledge base exists
    
    Returns:
        Boolean indicating if knowledge base exists
    """
    try:
        # Get absolute path for consistency
        abs_path = os.path.abspath(KNOWLEDGE_BASE_PATH)
        
        # First check if the directory exists
        if not os.path.exists(abs_path):
            logger.info(f"Knowledge base directory does not exist: {abs_path}")
            return False
            
        # Then check if it contains proper LanceDB files
        db_files = os.listdir(abs_path)
        if not db_files:
            logger.info(f"Knowledge base directory is empty: {abs_path}")
            return False
        
        logger.info(f"Found files in knowledge base directory: {db_files}")
            
        # Finally try connecting to the database
        try:
            db = lancedb.connect(abs_path)
            
            # Check if our table exists
            tables = db.table_names()
            logger.info(f"Available tables in database: {tables}")
            
            exists = VECTOR_TABLE_NAME in tables
            logger.info(f"Knowledge base table exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error connecting to LanceDB: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error checking knowledge base: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def retrieve_context(query: str) -> str:
    """Retrieve relevant context for a query
    
    Args:
        query: The user query
        
    Returns:
        String containing relevant context
    """
    try:
        logger.info(f"Retrieving context for query: {query}")
        # Check if model is available
        if model is None:
            logger.error("Embedding model not available, cannot retrieve context")
            return "Error: Embedding model not available"
            
        # Get query embedding
        query_embedding = model.encode(query).tolist()
        
        # Connect to database
        abs_path = os.path.abspath(KNOWLEDGE_BASE_PATH)
        db = lancedb.connect(abs_path)
        
        if VECTOR_TABLE_NAME not in db.table_names():
            logger.error(f"Table {VECTOR_TABLE_NAME} not found in database")
            return "Error: Knowledge base table not found"
        
        table = db.open_table(VECTOR_TABLE_NAME)
        
        # Search for similar chunks
        search_results = table.search(query_embedding).limit(TOP_K_RESULTS).to_list()
        
        # Extract and concatenate the text from results
        context_chunks = [result["text"] for result in search_results]
        context = "\n\n".join(context_chunks)
        
        logger.info(f"Retrieved {len(context_chunks)} context chunks")
        
        # If context is too long, truncate it
        max_context_length = 5000  # Gemini has token limits
        if len(context) > max_context_length:
            logger.warning(f"Context too long ({len(context)} chars), truncating")
            context = context[:max_context_length] + "..."
            
        return context
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error retrieving context: {str(e)}"

def answer_question(query: str) -> str:
    """Answer a question using RAG
    
    Args:
        query: The user's question
        
    Returns:
        Answer string
    """
    try:
        # Check if knowledge base exists
        if not check_knowledge_base_exists():
            logger.error("Knowledge base does not exist")
            return "I don't have any knowledge base to answer from. Please process documents first."
        
        # Retrieve relevant context
        context = retrieve_context(query)
        if not context or context.startswith("Error:"):
            logger.warning("No relevant context found or error retrieving context")
            return "I couldn't find relevant information to answer your question or encountered an error retrieving context."
        
        # Prepare prompt for the model
        prompt = f"""
        Answer the following question based on the provided context. 
        If the context doesn't contain information to answer the question, say so honestly.
        
        CONTEXT:
        {context}
        
        QUESTION:
        {query}
        
        ANSWER:
        """
        logger.info(f"Prompt length: {len(prompt)} characters")
        # Generate response using Gemini
        logger.info("Generating response with Gemini")
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text'):
            logger.error("No response from Gemini API")
            return "I'm having trouble generating a response. Please try again."
            
        answer = response.text.strip()
        logger.info(f"Generated response of length {len(answer)}")
        
        return answer
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error generating answer: {str(e)}"