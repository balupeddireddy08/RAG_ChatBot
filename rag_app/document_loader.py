# rag_app/document_loader.py
import streamlit as st
import os
import sys
import traceback
from io import BytesIO
from rag_app.logging_config import logger

# Import potentially problematic libraries in try-except blocks
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    logger.warning("Microsoft Word document support unavailable: docx library not found")
    DOCX_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    logger.warning("PDF support unavailable: PyPDF2 library not found")
    PDF_AVAILABLE = False

try:
    from langchain_community.document_loaders import WebBaseLoader
    import requests
    from bs4 import BeautifulSoup
    import html2text
    URL_LOADERS_AVAILABLE = True
except ImportError:
    logger.warning("URL loading support unavailable: required libraries not found")
    URL_LOADERS_AVAILABLE = False

def get_input_data(input_type):
    """Main function to get data based on selected input type"""
    logger.info(f"Getting input data for type: {input_type}")
    
    if input_type == "Link":
        if not URL_LOADERS_AVAILABLE:
            st.error("URL loading functionality is not available. Required libraries not installed.")
            return ""
        return input_links()
    elif input_type == "Text":
        return input_text()
    elif input_type == "PDF":
        if not PDF_AVAILABLE:
            st.error("PDF processing functionality is not available. PyPDF2 library not installed.")
            return ""
        return input_file("pdf")
    elif input_type == "DOCX":
        if not DOCX_AVAILABLE:
            st.error("Word document processing functionality is not available. python-docx library not installed.")
            return ""
        return input_file("docx")
    elif input_type == "TXT":
        return input_file("txt")
    else:
        st.error("Unsupported input type")
        return ""

def input_links():
    """Handle URL input and loading"""
    if not URL_LOADERS_AVAILABLE:
        st.error("URL loading functionality is not available. Required libraries not installed.")
        return ""
        
    st.markdown("""
    <div style="background-color: #f1f8e9; padding: 0.5rem; border-radius: 5px; margin-bottom: 0.8rem;">
        <p style="margin: 0; padding: 0;">Enter one or more URLs to extract content from websites.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("url_form", clear_on_submit=False):
        st.subheader("Load content from URLs")
        url = st.text_input("Enter URL", 
                          placeholder="https://example.com",
                          help="Must start with http:// or https://")
        
        additional_urls = st.text_area("Additional URLs (one per line)", 
                                     "", 
                                     height=100,
                                     placeholder="https://example1.com\nhttps://example2.com")
        
        # Replace column layout with a full-width button
        submit_button = st.form_submit_button("Load URLs", 
                                            use_container_width=True,
                                            type="primary")
    
    content = ""  # Initialize content outside the conditional block
    
    if submit_button:
        # Double-check URL_LOADERS_AVAILABLE in case it changed during runtime
        if not URL_LOADERS_AVAILABLE:
            st.error("URL loading functionality is not available. Required libraries not installed.")
            return ""
            
        urls = [url.strip()]
        if additional_urls:
            urls.extend([u.strip() for u in additional_urls.split('\n') if u.strip()])
        
        valid_urls = [u for u in urls if u and (u.startswith("http://") or u.startswith("https://"))]
        
        if not valid_urls:
            st.error("Please enter at least one valid URL starting with http:// or https://.")
            return ""
        
        with st.spinner("Loading content from URLs..."):
            progress_bar = st.progress(0)
            try:
                h = html2text.HTML2Text()
                h.ignore_links = False
                
                for i, url in enumerate(valid_urls):
                    try:
                        # Update progress
                        progress_value = (i / len(valid_urls))
                        progress_bar.progress(progress_value, text=f"Loading {url}")
                        
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
                
                # Complete the progress bar
                progress_bar.progress(1.0, text="Loading complete")
                
                if content:
                    st.success(f"Successfully loaded content from {len(valid_urls)} URL(s)")
                    logger.info(f"Total content from URLs: {len(content)} characters")
                    
                    # Show content directly instead of using an expander
                    st.markdown(f"**Total characters:** {len(content)}")
                    if len(content) > 500:
                        st.text(content[:500] + "...")
                    else:
                        st.text(content)
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
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 0.5rem; border-radius: 5px; margin-bottom: 0.8rem;">
        <p style="margin: 0; padding: 0;">Enter text directly for RAG processing.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("text_form", clear_on_submit=False):
        text = st.text_area("Paste your text here", 
                          height=300, 
                          placeholder="Enter or paste your text content here...")
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            submit_button = st.form_submit_button("Process Text", 
                                               type="primary",
                                               use_container_width=True)
    
    if submit_button and text:
        logger.info(f"Text input received: {len(text)} characters")
        # Store in session state to persist
        st.session_state['text_content'] = text
        
        # Show character count and preview
        st.success(f"Text received: {len(text)} characters")
        if len(text) > 100:
            # Show preview directly instead of using an expander
            st.markdown(f"**Preview content:**")
            st.text(text[:500] + ("..." if len(text) > 500 else ""))
        
        return text
    elif 'text_content' in st.session_state:
        # Return previously stored content
        if st.session_state['text_content']:
            # Show character count for persistent content
            st.info(f"Stored text: {len(st.session_state['text_content'])} characters")
        return st.session_state['text_content']
    return ""

def input_file(file_type):
    """Handle file uploads for different file types"""
    file_descriptions = {
        "pdf": "PDF documents with text content",
        "docx": "Microsoft Word documents",
        "txt": "Plain text files"
    }
    
    # Check if required libraries are available
    if file_type == "pdf" and not PDF_AVAILABLE:
        st.error("PDF processing functionality is not available. PyPDF2 library not installed.")
        return ""
    elif file_type == "docx" and not DOCX_AVAILABLE:
        st.error("Word document processing functionality is not available. python-docx library not installed.")
        return ""
    
    st.markdown(f"""
    <div style="background-color: #fff3e0; padding: 0.5rem; border-radius: 5px; margin-bottom: 0.8rem;">
        <p style="margin: 0; padding: 0;">Upload a {file_type.upper()} file to extract its content ({file_descriptions.get(file_type, '')}).</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show file uploader with better styling
    file = st.file_uploader(f"Upload your {file_type.upper()} file", 
                          type=[file_type], 
                          help=f"Select a {file_type} file from your device")
    
    content = ""  # Initialize content outside the conditional block
    
    if file is not None:
        # Display file info
        file_size = file.size / 1024  # Convert to KB
        st.markdown(f"""
        <div style="background-color: #efefef; padding: 0.5rem; border-radius: 5px; margin: 0.5rem 0;">
            <p style="margin: 0; padding: 0;">📄 <b>{file.name}</b> ({file_size:.1f} KB)</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner(f"Processing {file_type.upper()} file..."):
            try:
                # Show progress bar for better UX
                progress = st.progress(0, text="Starting file processing...")
                
                if file_type == "pdf":
                    if not PDF_AVAILABLE:
                        st.error("PDF processing functionality is not available.")
                        return ""
                        
                    try:
                        # Use BytesIO buffer to prevent file reading issues
                        file_bytes = BytesIO(file.read())
                        reader = PdfReader(file_bytes)
                        total_pages = len(reader.pages)
                        
                        if total_pages == 0:
                            st.error(f"No pages found in PDF file: {file.name}")
                            logger.error(f"PDF has no pages: {file.name}")
                            return ""
                        
                        # Flag to track if we extracted any content
                        extraction_success = False
                        
                        for i, page in enumerate(reader.pages):
                            progress.progress((i+1)/total_pages, text=f"Processing page {i+1} of {total_pages}")
                            text = page.extract_text()
                            if text:  # Only add if text was successfully extracted
                                content += text + "\n\n"
                                extraction_success = True
                            else:
                                logger.warning(f"No text extracted from page {i+1} in {file.name}")
                        
                        # Check if we got any content at all
                        if not extraction_success or not content.strip():
                            st.error(f"No text could be extracted from {file.name}. The PDF might be scanned or image-based.")
                            logger.error(f"No text extracted from any page in PDF: {file.name}")
                            # Clear any previous PDF content to prevent using old data
                            if f'{file_type}_content' in st.session_state:
                                del st.session_state[f'{file_type}_content']
                            return ""
                    except Exception as e:
                        st.error(f"Failed to process PDF file: {str(e)}")
                        logger.error(f"Failed to process PDF file: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Clear any previous PDF content to prevent using old data
                        if f'{file_type}_content' in st.session_state:
                            del st.session_state[f'{file_type}_content']
                        return ""
                elif file_type == "docx":
                    if not DOCX_AVAILABLE:
                        st.error("Word document processing functionality is not available.")
                        return ""
                        
                    doc = Document(BytesIO(file.read()))
                    progress.progress(0.5, text="Extracting text...")
                    content = "\n".join([p.text for p in doc.paragraphs if p.text])
                    progress.progress(1.0, text="Processing complete!")
                elif file_type == "txt":
                    progress.progress(0.5, text="Reading text file...")
                    content = file.read().decode("utf-8")
                    progress.progress(1.0, text="Processing complete!")
                
                if content:
                    st.success(f"Successfully processed {file.name}")
                    logger.info(f"File content extracted: {len(content)} characters")
                    
                    # Store file info directly instead of using an expander which causes nesting issues
                    st.markdown(f"**Total characters:** {len(content)}")
                    if len(content) > 500:
                        st.text(content[:500] + "...")
                    else:
                        st.text(content)
                    
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
        if st.session_state[f'{file_type}_content']:
            # Show character count for persistent content
            st.info(f"Stored {file_type.upper()} content: {len(st.session_state[f'{file_type}_content'])} characters")
        return st.session_state[f'{file_type}_content']
    return ""