# Modified rag_engine.py with improved path handling
import os
import re
import sys
import traceback
from typing import Tuple, List, Dict, Any
import numpy as np
import logging
from rag_app.logging_config import logger

# Configure tensor operations before imports
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# Import large models in a try-except block
try:
    import lancedb
    import google.generativeai as genai
    from sentence_transformers import SentenceTransformer
    # Flag to indicate imports succeeded
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    logger.error(f"Failed to import required libraries: {str(e)}")
    IMPORTS_SUCCESSFUL = False

# Function to get proper paths with permission handling
def get_kb_path():
    """Get knowledge base path with fallback for permission issues"""
    # Check environment variable first (set by run_app.py if permission issues)
    if "RAG_PATH_CHAT_DATA_KNOWLEDGE_BASE" in os.environ:
        return os.environ["RAG_PATH_CHAT_DATA_KNOWLEDGE_BASE"]
    
    # Default path
    kb_path = os.path.join("chat_data", "knowledge_base")
    
    # If we can't write to the default path, use /tmp
    if not os.access("chat_data", os.W_OK):
        tmp_path = os.path.join("/tmp", "chat_data", "knowledge_base")
        os.makedirs(tmp_path, exist_ok=True)
        logger.warning(f"Using alternative knowledge base path: {tmp_path}")
        return tmp_path
        
    return kb_path

# Constants for settings
VECTOR_TABLE_NAME = "documents"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 5

# Ensure API key is available
if "GEMINI_API_KEY" not in os.environ:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the application.")

# Global model variable
model = None

# Initialize in a function to better handle errors
def initialize_embedding_model():
    global model
    
    if not IMPORTS_SUCCESSFUL:
        logger.error("Cannot initialize embedding model due to import failures")
        return False
        
    try:
        # Load the model with minimal settings
        logger.info("Attempting to load SentenceTransformer model...")
        
        # Suppress stdout/stderr during model loading
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            # Test the model with a simple encoding
            test_embedding = model.encode("Test sentence for embedding.")
            logger.info(f"SentenceTransformer model loaded successfully. Embedding shape: {test_embedding.shape}")
            return True
        finally:
            # Restore stdout/stderr
            sys.stdout, sys.stderr = old_stdout, old_stderr
            
    except Exception as e:
        logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
        logger.error(traceback.format_exc())
        model = None
        logger.warning("Embedding model unavailable. RAG functionality will be limited.")
        return False

# Try to initialize the model
initialize_embedding_model()

# Configure Gemini API if imports succeeded
if IMPORTS_SUCCESSFUL:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

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
        # Check if imports succeeded
        if not IMPORTS_SUCCESSFUL:
            logger.error("Required libraries not available, cannot create vector store")
            return False
            
        # Get knowledge base path with permission handling
        kb_path = get_kb_path()
        
        # Ensure directory exists
        os.makedirs(kb_path, exist_ok=True)
        logger.info(f"Using knowledge base path: {kb_path}")
        
        # Check if we have a valid model
        if model is None:
            logger.error("Embedding model not available, cannot create vector store")
            return False
        
        # Connect to LanceDB
        logger.info(f"Connecting to LanceDB at: {kb_path}")
        db = lancedb.connect(kb_path)
        
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
    """Check if the knowledge base exists and has data
    
    Returns:
        Boolean indicating if knowledge base exists and has data
    """
    try:
        # Check if required imports succeeded
        if not IMPORTS_SUCCESSFUL:
            logger.error("Required libraries not available, cannot check knowledge base")
            return False
            
        # Get knowledge base path with permission handling
        kb_path = get_kb_path()
        
        # First check if the directory exists
        if not os.path.exists(kb_path):
            logger.info(f"Knowledge base directory does not exist: {kb_path}")
            return False
            
        # Then check if it contains proper LanceDB files
        db_files = os.listdir(kb_path)
        if not db_files:
            logger.info(f"Knowledge base directory is empty: {kb_path}")
            return False
        
        logger.info(f"Found files in knowledge base directory: {db_files}")
            
        # Try connecting to the database
        try:
            db = lancedb.connect(kb_path)
            
            # Check if our table exists
            tables = db.table_names()
            logger.info(f"Available tables in database: {tables}")
            
            if VECTOR_TABLE_NAME not in tables:
                logger.info(f"Knowledge base table {VECTOR_TABLE_NAME} does not exist")
                return False
                
            # Verify the table has data
            try:
                table = db.open_table(VECTOR_TABLE_NAME)
                # Check if table has at least one entry
                count = len(table.to_pandas().head(1))
                
                if count == 0:
                    logger.info(f"Knowledge base table {VECTOR_TABLE_NAME} exists but has no data")
                    return False
                    
                logger.info(f"Knowledge base verified with data")
                return True
            except Exception as e:
                logger.error(f"Error checking table data: {str(e)}")
                return False
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
        
        # Check if required imports succeeded
        if not IMPORTS_SUCCESSFUL:
            logger.error("Required libraries not available, cannot retrieve context")
            return "Error: Required libraries not available"
            
        # Check if model is available
        if model is None:
            logger.error("Embedding model not available, cannot retrieve context")
            return "Error: Embedding model not available"
        
        # Get knowledge base path with permission handling
        kb_path = get_kb_path()
            
        # Get query embedding
        query_embedding = model.encode(query).tolist()
        
        # Connect to database
        db = lancedb.connect(kb_path)
        
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
        # Check if required imports succeeded
        if not IMPORTS_SUCCESSFUL:
            logger.error("Required libraries not available, cannot answer question")
            return "I'm sorry, but the required AI libraries are not available. Please check the application logs."
            
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