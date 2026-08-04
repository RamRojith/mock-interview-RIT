# learning_management_system/rag_utils.py
import os
import shutil
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# 1. Initialize the Embedding Function
# We use 'all-MiniLM-L6-v2' which is fast, free, and runs locally.
def get_embedding_function():
    try:
        # Preferred (new package)
        from langchain_huggingface import HuggingFaceEmbeddings
    except Exception:
        # Backward compatible fallback
        from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Initialize the Vector Database Client
def get_vector_store():
    persist_directory = getattr(
        settings,
        "CHROMA_DB_PATH",
        os.path.join(getattr(settings, "BASE_DIR", "."), "chroma_db"),
    )
    # Ensure the directory exists
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)
    
    return Chroma(
        persist_directory=persist_directory, 
        embedding_function=get_embedding_function(),
        collection_name="faculty_documents"
    )

def process_document_embedding(document_instance):
    """
    Reads a PDF, splits it, embeds it, and stores it with STRICT METADATA.
    """
    file_path = document_instance.file.path
    
    # Check if file actually exists on disk
    if not os.path.exists(file_path):
        print(f"[RAG Error] File not found at: {file_path}")
        return

    print(f"[RAG] Processing: {document_instance.document_title}")

    # A. Load the PDF
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
    except Exception as e:
        print(f"[RAG Error] Failed to load PDF: {e}")
        return

    # B. Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        length_function=len
    )
    splits = text_splitter.split_documents(docs)

    # C. Prepare STRICT METADATA for every chunk
    # This ensures no mix-up between courses or folders.
    metadatas = []
    for i, split in enumerate(splits):
        metadatas.append({
            "doc_id": str(document_instance.id),       # Link to Django DB
            "folder_id": str(document_instance.folder.id),
            "course_id": str(document_instance.folder.course_id),
            "faculty_id": str(document_instance.uploaded_by.faculty_id),
            "academic_year": str(document_instance.academic_year),
            "semester": str(document_instance.semester),
            "title": document_instance.document_title,
            "chunk_index": i, # To track which part of the doc this is
            "source_type": "pdf"
        })

    # D. Store in Vector DB
    try:
        vector_store = get_vector_store()
        # We add texts and their corresponding metadata
        vector_store.add_texts(texts=[split.page_content for split in splits], metadatas=metadatas)
        print(f"[RAG] Success: Stored {len(splits)} chunks for Doc ID {document_instance.id}.")
    except Exception as e:
        print(f"[RAG Error] Failed to store embeddings: {e}")

def delete_document_embeddings(document_id):
    """
    Deletes all chunks associated with a specific Document ID from the Vector DB.
    Crucial for updates/deletes.
    """
    try:
        vector_store = get_vector_store()
        # ChromaDB allows deleting by metadata filter
        vector_store.delete(where={"doc_id": str(document_id)})
        print(f"[RAG] Deleted embeddings for Doc ID: {document_id}")
    except Exception as e:
        print(f"[RAG Error] Failed to delete embeddings: {e}")


def query_course_documents(course_id, query, k=5):
    """
    Query the vector database for documents related to a specific course.
    
    Args:
        course_id: The course ID to filter documents by
        query: The user's question/query
        k: Number of relevant chunks to retrieve (default: 5)
    
    Returns:
        List of relevant document chunks with their metadata
    """
    try:
        vector_store = get_vector_store()
        
        # Perform similarity search with metadata filter
        # ChromaDB supports filtering by metadata
        results = vector_store.similarity_search(
            query=query,
            k=k,
            filter={"course_id": str(course_id)}
        )
        
        print(f"[RAG] Found {len(results)} relevant chunks for course_id={course_id}")
        
        # Format results for context
        context_chunks = []
        for doc in results:
            context_chunks.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return context_chunks
    
    except Exception as e:
        print(f"[RAG Error] Failed to query documents: {e}")
        return []


def format_context_for_llm(chunks):
    """
    Format retrieved chunks into a context string for the LLM.
    
    Args:
        chunks: List of chunk dictionaries with content and metadata
    
    Returns:
        Formatted context string
    """
    if not chunks:
        return "No relevant course materials found."
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get('metadata', {}).get('title', 'Unknown Document')
        content = chunk.get('content', '')
        context_parts.append(f"[Document {i}: {title}]\n{content}")
    
    return "\n\n".join(context_parts)
