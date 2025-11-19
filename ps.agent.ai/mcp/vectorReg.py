import os
import time
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA

# ✅ Choose a free chat model
# Option 1: Use Hugging Face Inference API (requires a free HF token)
from langchain_community.chat_models import ChatHuggingFace
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Option 2 (if installed): use Ollama locally
# from langchain_community.chat_models import ChatOllama

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "customer-rag-demo"
os.environ[
    "OPENAI_API_KEY"] = "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"

class VectorRAG:
    """
    MCP tool using local
    """

    def __init__(self, pdf_path: str, persist_dir: str = "./chroma_store_free"):
        self.pdf_path = pdf_path
        self.persist_dir = persist_dir
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        # self.llm = self._init_llm()
        self.retriever = None
        self.rag_chain = None

        self._load_pdf()
        self._build_vectorstore()
        self._build_retriever_chain()



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

    def _build_retriever_chain(self):
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        self.rag_chain = RetrievalQA.from_chain_type(
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0),
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
        )
        print("🔗 RAG chain ready.")

    def run(self, query: str):
        return self.rag_chain.invoke({"query": query})

    # def run(self, query: str):
    #     print(f"\n🧠 Query: {query}")
    #     result = self.rag_chain.invoke({"query": query})
    #     print(f"✅ Answer: {result['result']}")
    #     for i, doc in enumerate(result["source_documents"], 1):
    #         print(f"\n📄 Source {i}:\n{doc.page_content[:300]}...")
    #     return result