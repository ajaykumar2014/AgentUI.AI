import os
import time
from typing import Optional,List

from PyPDF2 import PdfReader
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA

# ✅ Choose a free chat model
# Option 1: Use Hugging Face Inference API (requires a free HF token)
from langchain_community.chat_models import ChatHuggingFace
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langsmith import traceable
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Option 2 (if installed): use Ollama locally
# from langchain_community.chat_models import ChatOllama

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "API_KEY"
os.environ["LANGCHAIN_PROJECT"] = "customer-rag-demo"
os.environ[
    "OPENAI_API_KEY"] = "sk-proj-API_KEY"

class VectorRAG_V1:
    """
    MCP tool using local
    """

    def __init__(self, pdf_path: Optional[List[str]] = None, pdf_dir: Optional[str] = None, persist_dir: str = "./chroma_store_v1"):
        self.pdf_path = self._collect_pdfs(pdf_path,pdf_dir=pdf_dir)
        self.persist_dir = persist_dir
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        # self.llm = self._init_llm()
        self.retriever = None
        self.rag_chain = None
        self.text_chunks = []
        self.memory = None
        #self._load_pdf()
        self._load_all_pdfs()
        self._build_vectorstore()
        self._build_retriever_chain()

    def _collect_pdfs(self, pdf_paths, pdf_dir):
        if pdf_paths:
            return pdf_paths

        if pdf_dir:
            return [
                os.path.join(pdf_dir, f)
                for f in os.listdir(pdf_dir)
                if f.lower().endswith(".pdf")
            ]

        raise ValueError("Provide either pdf_paths or pdf_dir to load PDFs.")

    # --- ✅ Load ALL PDFs and split text ---
    def _load_all_pdfs(self):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )

        for path in self.pdf_path:
            if not os.path.exists(path):
                raise FileNotFoundError(f"PDF not found: {path}")

            print(f"📄 Reading: {path}")
            reader = PdfReader(path)

            text = "".join([page.extract_text() or "" for page in reader.pages])
            chunks = splitter.split_text(text)

            print(f"✅ Loaded {len(chunks)} chunks from {os.path.basename(path)}")
            self.text_chunks.extend(chunks)

        print(f"📦 Total text chunks: {len(self.text_chunks)}")

    def _load_pdf(self):
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        reader = PdfReader(self.pdf_path)
        text = "".join([page.extract_text() or "" for page in reader.pages])
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        self.text_chunks = splitter.split_text(text)
        print(f"✅ Loaded {len(self.text_chunks)} text chunks from {self.pdf_path}")

    def _build_vectorstore(self):
        if not os.path.exists(self.persist_dir):
            print("⚙️ Building new Chroma vectorstore...")
            self.vectorstore = Chroma.from_texts(
                self.text_chunks,
                embedding=self.embeddings,
                persist_directory=self.persist_dir,
            )
        else:
            print("📂 Loading existing Chroma vectorstore...")
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )

    @traceable(run_type="chain")
    def _build_retriever_chain(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="question",
            output_key="result",  # ✅ tell memory which output to save
            return_messages=True
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        self.rag_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            output_key="result",  # ✅ required
        )
        print("🔗 RAG chain ready.")

    def run(self, query: str):
        return self.rag_chain.invoke({"question": query})

    # def run(self, query: str):
    #     print(f"\n🧠 Query: {query}")
    #     result = self.rag_chain.invoke({"query": query})
    #     print(f"✅ Answer: {result['result']}")
    #     for i, doc in enumerate(result["source_documents"], 1):
    #         print(f"\n📄 Source {i}:\n{doc.page_content[:300]}...")
    #     return result