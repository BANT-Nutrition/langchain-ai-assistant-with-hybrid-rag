#!/usr/bin/env python

# v6: load JSON items only from DB on disk

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# This AI (Artificial Intelligence) assistant allows you to ask all kinds of questions regarding art  #
# and the Belgian monarchy. To answer, the assistant queries the graphic databases BALaT of the IRPA  #
# (Royal Institute of Artistic Heritage), Belgica of the KBR (Royal Library) and Wikimedia Commons.   #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import dotenv, jq, time
import streamlit as st
from PIL import Image
from langchain_community.document_loaders import JSONLoader
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain.chains import create_history_aware_retriever # To create the retriever chain (predefined chain)
from langchain.chains import create_retrieval_chain # To create the main chain (predefined chain)
from langchain.chains.combine_documents import create_stuff_documents_chain # To create a predefined chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from langchain.memory import ConversationBufferWindowMemory

dotenv.load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-large"
MODEL = "gpt-4-turbo-2024-04-09"
COLLECTION_NAME = "bmae"

@st.cache_data
def load_files(json_file_paths):
    # Loads and chunks files into a list of documents

    documents = []

    for json_file_path in json_file_paths:
        loader = JSONLoader(file_path=json_file_path, jq_schema=".[]", text_content=False) # 1 JSON item per chunk
        docs = loader.load()
        documents = documents + docs

    return documents

@st.cache_resource
def instanciate_vector_db():
    # Instantiates Vector DB and loads documents from disk
    
    embedding_model = OpenAIEmbeddings(model=EMBEDDING_MODEL) # 3072 dimensions vectors used to embed the JSON items and the questions
    vector_db = Chroma(embedding_function=embedding_model, collection_name=COLLECTION_NAME, persist_directory="./chromadb")
        
    return vector_db

@st.cache_resource
def instanciate_retrievers_and_chains(_vector_db):
    # Instantiate retrievers and chains and return the main chain (AI Assistant)
    # Retrieve and generate

    docs = vector_db.get()
    documents = docs["documents"]

    llm = ChatOpenAI(model=MODEL, temperature=0)

    vector_retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    keyword_retriever = BM25Retriever.from_texts(documents)
    keyword_retriever.k = 5

    ensemble_retriever = EnsembleRetriever(retrievers=[keyword_retriever, vector_retriever], weights=[0.5, 0.5])

    contextualize_q_system_prompt = """
    Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.
    """

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        llm, ensemble_retriever, contextualize_q_prompt 
    )

    qa_system_prompt = """
    You are an artwork specialist. You must assist the users in finding, describing, and displaying artworks related to the Belgian monarchy. \
    You first have to search answers in the "Knowledge Base". If no answers are found in the "Knowledge Base", then answer with your own knowledge. \
    You have to answer in the same language as the question.
    At the end of the answer:
    - At a new line, display an image of the artwork (see the "og:image" field).
    - At a new line, write "Reference: " (in the language of the question) followed by the link to the web page about the artwork (see the "url" field). \
    For Wikimedia Commons, the text of the link has to be the title of the web page WITHOUT the word "File" at the beginning (see "og:title").

    Knowledge Base:

    {context}
    """

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    ai_assistant_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    return ai_assistant_chain

# Load, index, retrieve and generate

vector_db = instanciate_vector_db()
       
ai_assistant_chain = instanciate_retrievers_and_chains(vector_db)

# Streamlit

logo = Image.open("./crown.jpg")
st.image(logo, use_column_width=True)

#st.set_page_config(page_title="BMAE", page_icon="👑")
#st.title("Belgian Monarchy Artworks Explorer")
st.markdown("## Belgian Monarchy Artworks Explorer")
st.caption("💬 A chatbot powered by OpenAI, Langchain and Streamlit")

with st.sidebar:

    st.markdown("""
    (Version française disponible plus bas)

    ### About this assistant
    
    This AI (Artificial Intelligence) assistant allows you to ask all kinds of questions regarding art and the Belgian monarchy. To answer, the assistant \
    queries the graphic databases BALaT of the IRPA (Royal Institute of Artistic Heritage), Belgica of the KBR (Royal Library) and Wikimedia Commons.

    The questions can be in any language, but French and Dutch give the best results. Here are some examples of questions:

    - When did King Leopold I die? Do you have pictures of the funeral?
    - Can you show me the canvas 'The School Parade'? *Or:*
    - Can you show me the canvas 'La revue des écoles'? *And then you can ask the question:*
    - Who painted that canvas? *And then:*
    - What is the size of the canvas? *And then:*
    - Who is on the canvas? *And then:*
    - Can you show me that canvas with a picture from Wikimedia Commons and another picture from BALaT?
    - When did the fire at Laeken Castle take place? Do you have pictures of that event?
    - When did King Leopold I get married? *The assistant will show you a picture of the wedding.*
    - Can you show me pictures of Queen Marie-Henriette? Can you give me the authors of the pictures?
    - Can you show me a portrait of King Leopol I? It has to be an engraving.
    - Can you show me pictures of King Leopold II?
    - Can you show me pictures of King Leopold II during his accession to the throne in 1865?
    - Do you have artworks created by Aimable Dutrieux? *And then you can ask the question:*
    - Who was this sculptor?
    - Can you show me two pictures of the patriotic celebration of Belgium's fiftieth anniversary made by Martin Claverie? Who is in these pictures? What newspaper do they come from?

    If you don't get a correct answer, try rephrasing the question. For example, the following question does not receive a correct answer: *Do you have a bust of Louis-Philipe, son of \
    King Leopold I?*, but the following question receives a correct answer: *Do you have a bust of Louis-Philipe?*

    The assistant takes about 30 seconds to respond.

    The assistant has a memory of the question and answer session. The questions you ask may therefore refer to previous questions and answers. For example: *Who painted that canvas?*
    """)

    st.markdown("""
    
    FRANCAIS:

    ### Informations concernant cet assistant
    
    Cet assistant IA (Intelligence Artificielle) vous permet de poser toutes sortes de questions concernant l'art et la monarchie belge. Pour répondre, l'assistant \
    questionne les bases de données graphiques BALaT de l'IRPA (Institut royal du Patrimoine artistique), Belgica de la KBR (Bibliothèque royale) et Wikimedia Commons.

    Les questions peuvent-être posées en diférentes langues, mais le français et le néerlandais donnent les meilleurs résultats. Voici quelques exemples de questions: 

    - Quand est mort le roi Léopold Ier ? Avez-vous des images des funérailles ?
    - Avez-vous des images de la reine Elisabeth pendant la guerre ?
    - Pouvez-vous me montrer le tableau 'La revue des écoles' ? *Et ensuite vous pouvez poser la question :* 
    - Qui a peint ce tableau ? *Et encore ensuite :* 
    - Quelle est la dimension du tableau ? *Et encore ensuite :*
    - Qui est présent sur le tableau ? *Et encore ensuite :* 
    - Pouvez-vous me montrer ce tableau avec une photo de la Wikimedia Commons et une autre photo de BALaT ?
    - Quand a eu lieu l'incendie du château de Laeken ? Avez-vous plusieurs images de cet événement ?
    - Quand s'est marié le roi Léopold Ier ? *L'assistant vous montrera une image du mariage.*
    - Pouvez-vous me montrer des images sur lesquelles ce trouve la reine Marie-Henriette ? Pouvez-vous me donner les auteurs des images ?
    - Pouvez-vous me montrer un portrait du roi Léopol Ier ? Il faut que ce soit une gravure.
    - Pouvez-vous me montrer plusieurs images du roi Léopold II ?
    - Pouvez-vous me montrer des images du roi Léopold II lors de son avènement en 1865 ?
    - Avez-vous des oeuvres réalisées par Aimable Dutrieux ? *Et ensuite vous pouvez poser la question :*
    - Qui était ce sculteur ?
    - Pouvez-vous me montrer deux images de la fête patriotique du cinquantenaire de la Belgique réalisées par Martin Claverie ? Qui est présent sur ces images ? De quel journal proviennent-elles ?

    Si vous n'obtenez pas une réponse correcte, essayez de reformuler la question. Par exemple la question suivante ne reçois pas de réponse correcte : *Avez-vous un buste de Louis-Philipe, fils du \
    roi Léopold Ier ?*, mais la question suivante reçoit elle une réponse correcte : *Avez-vous un buste de Louis-Philipe ?*

    L'assistant prend environ 30 secondes pour répondre.

    L'assistant possède une mémoire de la session de questions et réponses. Les questions que vous posez peuvent donc faire référence aux questions et réponses précédentes. Par exemple : *Qui a peint ce tableau ?*
    """)

    st.markdown("""
    _________
    AI Model: OpenAI GPT4 Turbo. Vector size: 3072. Hybrid RAG with memory powered by Langchain. Web interface powered by Streamlit. *(c) Eric Dodémont, 2024.*
    """)

# Initialize chat history (chat_history) for LangChain
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.chat_history2 = ConversationBufferWindowMemory(k=4, return_messages=True)   # Max k Q/A in the chat history for Langchain 

# Initialize chat history (messages) for Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.chat_message("assistant"):
    st.write("Hello! Bonjour! Hallo! 👋")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if question := st.chat_input("Enter your question / Entrez votre question / Voer uw vraag in"):
    # Display user message in chat message container
    st.chat_message("user").markdown(question)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": question})

    output = ai_assistant_chain.invoke({"input": question, "chat_history": st.session_state.chat_history}) # output is a dictionary. output["answer"] is the LLM answer in markdown format.
    
    st.session_state.chat_history2.save_context({"input": question}, {"output": output["answer"]})
    load_memory = st.session_state.chat_history2.load_memory_variables({})
    st.session_state.chat_history = load_memory["history"]
        
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(output["answer"])
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": output["answer"]})

# $ streamlit run assistant.py &
# $ sudo streamlit run assistant.py --server.port 80 > assistant.log 2>&1 &
