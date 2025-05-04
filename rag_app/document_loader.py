# rag_app/document_loader.py
import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
from io import BytesIO
from langchain_community.document_loaders import WebBaseLoader
import requests
from bs4 import BeautifulSoup
import html2text
from rag_app.logging_config import logger

def get_input_data(input_type):
    """Main function to get data based on selected input type"""
    logger.info(f"Getting input data for type: {input_type}")
    
    if input_type == "Link":
        return input_links()
    elif input_type == "Text":
        return input_text()
    elif input_type == "PDF":
        return input_file("pdf")
    elif input_type == "DOCX":
        return input_file("docx")
    elif input_type == "TXT":
        return input_file("txt")
    else:
        st.error("Unsupported input type")
        return ""

def input_links():
    """Handle URL input and loading"""
    with st.form("url_form"):
        st.subheader("Load content from URLs")
        url = st.text_input("Enter URL (must start with http:// or https://)")
        additional_urls = st.text_area("Additional URLs (one per line)", "", height=100)
        
        submit_button = st.form_submit_button("Load URLs")
    
    content = ""  # Initialize content outside the conditional block
    
    if submit_button:
        urls = [url.strip()]
        if additional_urls:
            urls.extend([u.strip() for u in additional_urls.split('\n') if u.strip()])
        
        valid_urls = [u for u in urls if u and (u.startswith("http://") or u.startswith("https://"))]
        
        if not valid_urls:
            st.error("Please enter at least one valid URL starting with http:// or https://.")
            return ""
        
        with st.spinner("Loading content from URLs..."):
            try:
                h = html2text.HTML2Text()
                h.ignore_links = False
                
                for url in valid_urls:
                    try:
                        # First try using requests + BeautifulSoup + html2text for better control
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.extract()
                            
                        # Convert to markdown
                        text = h.handle(str(soup))
                        content += f"\n\nSource: {url}\n{text}\n"
                        
                        # Debug log to check content
                        logger.info(f"Content retrieved from {url}: {len(text)} characters")
                    except Exception as e:
                        # Fall back to WebBaseLoader
                        st.warning(f"Using fallback loader for {url}: {str(e)}")
                        try:
                            loader = WebBaseLoader([url])
                            docs = loader.load()
                            content += f"\n\nSource: {url}\n{docs[0].page_content}\n"
                            logger.info(f"Content retrieved via fallback from {url}: {len(docs[0].page_content)} characters")
                        except Exception as e2:
                            st.error(f"Failed to load {url}: {str(e2)}")
                            logger.error(f"Failed to load {url}: {str(e2)}")
                
                if content:
                    st.success(f"Successfully loaded content from {len(valid_urls)} URL(s)")
                    logger.info(f"Total content from URLs: {len(content)} characters")
                else:
                    st.error("No content could be extracted from the provided URLs")
                    logger.error("No content extracted from URLs")
                    content = ""  # Ensure empty string is returned
            except Exception as e:
                st.error(f"Error loading URLs: {str(e)}")
                logger.error(f"Error loading URLs: {str(e)}")
                content = ""  # Ensure empty string is returned
    
    # Important: Store content in session state to persist it
    if content:
        st.session_state['url_content'] = content
        return content
    elif 'url_content' in st.session_state:
        # Return previously stored content
        return st.session_state['url_content']
    return ""

def input_text():
    """Handle direct text input"""
    with st.form("text_form"):
        text = st.text_area("Paste your text here", height=300)
        submit_button = st.form_submit_button("Process Text")
    
    if submit_button and text:
        logger.info(f"Text input received: {len(text)} characters")
        # Store in session state to persist
        st.session_state['text_content'] = text
        return text
    elif 'text_content' in st.session_state:
        # Return previously stored content
        return st.session_state['text_content']
    return ""

def input_file(file_type):
    """Handle file uploads for different file types"""
    file = st.file_uploader(f"Upload your {file_type.upper()} file", type=[file_type])
    
    content = ""  # Initialize content outside the conditional block
    
    if file is not None:
        with st.spinner(f"Processing {file_type.upper()} file..."):
            try:
                if file_type == "pdf":
                    reader = PdfReader(BytesIO(file.read()))
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:  # Only add if text was successfully extracted
                            content += text + "\n\n"
                elif file_type == "docx":
                    doc = Document(BytesIO(file.read()))
                    content = "\n".join([p.text for p in doc.paragraphs if p.text])
                elif file_type == "txt":
                    content = file.read().decode("utf-8")
                
                if content:
                    st.success(f"Successfully processed {file.name}")
                    logger.info(f"File content extracted: {len(content)} characters")
                    # Store in session state
                    st.session_state[f'{file_type}_content'] = content
                else:
                    st.error(f"No text could be extracted from {file.name}")
                    logger.error(f"No text extracted from {file.name}")
                    content = ""
            except Exception as e:
                st.error(f"Failed to process {file_type.upper()} file: {str(e)}")
                logger.error(f"Failed to process {file_type.upper()} file: {str(e)}")
                content = ""
    
    # Return content from this run or from session state if available
    if content:
        return content
    elif f'{file_type}_content' in st.session_state:
        return st.session_state[f'{file_type}_content']
    return ""