import os
import time

from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from openai import RateLimitError

load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "customer-rag-demo"
os.environ["OPENAI_API_KEY"]="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"
# ---------------------------
# 1️⃣ Load PDF document
# ---------------------------
pdf_path = os.path.join(os.getcwd(), "docs", "output.pdf")
if not os.path.exists(pdf_path):
    raise FileNotFoundError(f"File not found: {pdf_path}")

reader = PdfReader(pdf_path)
text = "".join([page.extract_text() or "" for page in reader.pages])

# ---------------------------
# 2️⃣ Split text into chunks
# ---------------------------
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
texts = text_splitter.split_text(text)

# ---------------------------
# 3️⃣ Create embeddings + vectorstore
# ---------------------------
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
persist_dir = "./chroma_store"

if not os.path.exists(persist_dir):
    vectorstore = Chroma.from_texts(texts, embedding=embeddings, persist_directory=persist_dir)
    print("✅ Created new Chroma vectorstore.")
else:
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    print("✅ Loaded existing Chroma vectorstore.")

# ---------------------------
# 4️⃣ Setup retriever and LLM
# ---------------------------
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ---------------------------
# 5️⃣ RAG QA chain
# ---------------------------
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

def safe_invoke_chain(chain, query, retries=3):
    for i in range(retries):
        try:
            return chain.invoke({"query": query})
        except RateLimitError as e :
            wait = (2 ** i)
            print(f"Rate limit hit, retrying in {wait}s...{e}")
            time.sleep(wait)
    raise RuntimeError(f"Failed after retries due to rate limit.")


query = "Explain Kafka producer delivery guarantees."
result = safe_invoke_chain(rag_chain, "What is the process for loan approval?")

print("\n🧠 Answer:", result["result"])
for i, doc in enumerate(result["source_documents"], 1):
    print(f"\n📄 Source {i}:\n", doc.page_content[:300], "...")
