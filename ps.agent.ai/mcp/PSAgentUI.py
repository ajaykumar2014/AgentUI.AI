import asyncio
import time
from datetime import datetime

import streamlit as st
from langchain_core.messages import HumanMessage
import streamlit.web.cli as stcli
import sys
from agent import ChatState, SmartChatAgent

st.set_page_config(page_title="Chat UI")
st.markdown("""
<style>
.chat-container {
    max-width: 1400px;
    margin: auto;
   width: 95% !important;
    font-family: "Arial", sans-serif;
}
.user-msg, .bot-msg {
    display: flex;
    margin: 10px 0;
    width: 100%;
}
.user-msg .msg-box {
    margin-left: auto;
    background-color: #DCF8C6;
    color: #000;
    border-radius: 15px 15px 0 15px;
    padding: 10px 15px;
    max-width: 90%;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}
.bot-msg .msg-box {
    margin-right: auto;
    background-color: #F1F0F0;
    color: #000;
    border-radius: 15px 15px 15px 0;
    padding: 10px 15px;
    max-width: 90%;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}
# .timestamp-line {
#     text-align: center;
#     color: #888;
#     font-size: 12px;
#     margin: 10px 0;
#     position: relative;
# }
.timestamp-line {
    margin-top: 3px;  /* closer to bubble */
    margin-bottom: 10px;
    font-size: 11px;
}
.timestamp-line::before, .timestamp-line::after {
    content: "";
    position: absolute;
    top: 50%;
    width: 40%;
    height: 1px;
    background-color: #ccc;
}
.timestamp-line::before {
    left: 0;
}
.timestamp-line::after {
    right: 0;
}
.timestamp-user {
    text-align: right;
    color: #888;
    font-size: 11px;
    margin-top: 3px;
    margin-bottom: 12px;
    margin-right: 10px;
}

.timestamp-bot {
    text-align: left;
    color: #888;
    font-size: 11px;
    margin-top: 3px;
    margin-bottom: 12px;
    margin-left: 10px;
}
</style>
""", unsafe_allow_html=True)

# st.session_state -> dict ->
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# loading the conversation history
# for message in st.session_state['message_history']:
#     timestamp = message.get('timestamp', datetime.now().strftime('%d %b %Y, %I:%M %p'))
#     st.markdown(f'<div class="timestamp-line">🕒 {timestamp}</div>', unsafe_allow_html=True)
#     role = getattr(message, "type", None) or getattr(message, "role", "user")
#     content = getattr(message, "content", "")
#     print("role=>", role)
#     print("content=>", content)
#     if role in ['human','user']:
#         st.markdown(f'<div class="user-msg"><div class="msg-box">{content}</div></div>', unsafe_allow_html=True)
#     elif role in ['bot','ai','assistant']:
#         st.markdown(f'<div class="bot-msg"><div class="msg-box">{content}</div></div>', unsafe_allow_html=True)
for message in st.session_state['message_history']:
    timestamp = message.get('timestamp')#, datetime.now().strftime('%d %b %Y, %I:%M %p'))
    role = message.get("role")
    content = message.get("content")

    # st.markdown(f'<div class="timestamp-line">🕒 {timestamp}</div>', unsafe_allow_html=True)

    if role in ["user", "human"]:
        st.markdown(
            f'''
                <div class="user-msg">
                    <div class="msg-box">{content}</div>
                </div>
                <div class="timestamp-user">🕒 {timestamp}</div>
                ''',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'''
                <div class="bot-msg"><div class="msg-box">{content}</div></div>
                <div class="timestamp-bot">🕒 {timestamp}</div>
                ''',
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)

user_input = st.chat_input("Write your query")
if user_input:
    now = datetime.now().strftime('%d %b %Y, %I:%M %p')
    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input,'timestamp': now})


    st.markdown(f'<div class="user-msg"><div class="msg-box">{user_input}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="timestamp-user">🕒 {now}</div>', unsafe_allow_html=True)
    bot_placeholder = st.empty()
    frames = ["🤖 AI is typing", "🤖 AI is typing .", "🤖 AI is typing ..", "🤖 AI is typing ..."]
    for i in range(12):  # lasts ~2 seconds
        frame = frames[i % len(frames)]
        bot_placeholder.markdown(
            f"""
            <div class="bot-msg">
                <div class="msg-box"><i>{frame}</i></div>
            </div>
            """,
            unsafe_allow_html=True
        )
        time.sleep(0.10)

    async def get_ai_response():
        agent = SmartChatAgent()
        return await agent.run(user_input)


    # response = asyncio.get_event_loop().run_until_complete(get_ai_response())
    response = asyncio.run(get_ai_response())
    #st.session_state['message_history'].append(response)
    # extract assistant message
    print('response', response)
    ai_message = response['messages'][-1].content
    # print(f'AI Response: {ai_message}')
    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message,'timestamp': now})
    # st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

    # Show AI message
    bot_placeholder.empty()
    st.markdown(f'''
        <div class="bot-msg"><div class="msg-box">{ai_message}</div></div>
        <div class="timestamp-bot">🕒 {now}</div>
    ''', unsafe_allow_html=True)
    # st.markdown(f'<div class="bot-msg"><div class="msg-box">{ai_message}</div></div>', unsafe_allow_html=True)
    # st.markdown(f'<div class="timestamp-bot">🕒 {now}</div>', unsafe_allow_html=True)
    # if __name__ == "__main__":
    #     sys.argv = ["streamlit", "run", "PSAgentUI.py", "--server.port=8501"]
    #     sys.exit(stcli.main())
