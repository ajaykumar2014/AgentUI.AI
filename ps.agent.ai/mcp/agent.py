import asyncio
import os, json, re
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated, Dict, Any
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START
from langgraph.managed import RemainingSteps
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent, ToolNode
from langsmith import traceable
from pydantic import BaseModel
from guardrails import Guard

from client.mcp_tools import get_mcp_tool,decide_tool,get_jira_tool
from vectorReg_v1 import VectorRAG_V1
load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "customer-rag-demo"
os.environ[
    "OPENAI_API_KEY"] = "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"
                        # "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"

# Define chat state
class ChatState(TypedDict):
    #messages: Annotated[list[BaseMessage], add_messages]
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: RemainingSteps = 25

class JiraIssueSpec(BaseModel):
    summary: str
    description: str
    priority: str = "Medium"
    issue_type: str = "Task"
    labels: list[str] | None = None
    assignee: str | None = None

class SmartChatAgent:
    def __init__(self):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = "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"
        os.environ["LANGCHAIN_PROJECT"] = "customer-rag-demo"
        os.environ[
            "OPENAI_API_KEY"] = "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"

        # ---------------------------------------------------------------------------
        # 2️⃣  Initialize LLM + MCP tool
        # ---------------------------------------------------------------------------
        self.config = {'configurable': {'thread_id': 'thread-1'}}
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.mcp_tool = get_mcp_tool()
        self.jira_tool = get_jira_tool()
        # llm_with_tools = llm.bind_tools([mcp_tool])
        self.chatbot = create_react_agent(self.llm, tools=[self.mcp_tool,self.jira_tool],state_schema=ChatState)

        # Compile LangGraph
        self.graph = self._build_graph()
        self.guard = Guard.for_rail("guardrail/render_issue_validation.rail")

    async def dispatcher_node(self,state: ChatState):
        last_msg: BaseMessage = state['messages'][-1]
        query_text = last_msg.content

        # Ask MCP server which tool to use
        tool_decision = await decide_tool(query_text)

        if tool_decision == "rag":
            # Call RAG node
            reg_tool = VectorRAG_V1(pdf_path=["docs/MasteringInKafka.pdf", "docs/JavaDS.pdf"])
            result = await asyncio.to_thread(reg_tool.run, query_text)
            ai_msg = AIMessage(content=result["result"])
        elif tool_decision == "tool":
            # Call MCP tool directly
            result = await self.mcp_tool.run(query_text)
            ai_msg = AIMessage(content=result)
        elif tool_decision == "jira":
            # result = await self.create_issue_from_user_text(query_text)
            llm_prompt = await self.get_input_prompt_action(query_text)
            payload = {"payload": llm_prompt}
            result = await self.jira_tool.run(payload)
            if result.get("action") == "jira.fetch_issue":
                html_response_message = await self.get_issue_prompt_action(result.get("result"))
                html_message = f"""{html_response_message.content}"""
            else:
                html_message = format_jira_response_html(result)
            ai_msg = AIMessage(content=html_message)
        else:
            # Default to Chat LLM
            response = await self.chatbot.ainvoke({"messages": [{"role": "user", "content": query_text}]})
            ai_msg = response['messages'][-1]

        return {
            "messages": state["messages"] + [ai_msg],
            "remaining_steps": state.get("remaining_steps", 25) - 1
        }

    async def rag_node(self,state: ChatState):
        last_msg: BaseMessage = state['messages'][-1]
        query_text = last_msg.content

        print(f"🔥 RAG node triggered with query: {query_text}")
        # Call your free RAG tool
        result = await asyncio.to_thread(self.rag_tool.run, query_text)


        # Wrap output as AIMessage
        ai_msg = AIMessage(content=result["result"])

        # Append to existing messages
        return {
            "messages": state["messages"] + [ai_msg],
            "remaining_steps": state.get("remaining_steps", 25) - 1
        }

    # Define node logic
    async def chat_node(self,state: ChatState):
        messages = state['messages']
        print(f"🔥 Chat node triggered with query: {messages[-1].content}")
        response = await self.chatbot.ainvoke({"messages": [{"role": "user", "content": messages[-1].content}]})

        print(f"chatbot response is {response}")
        return {"messages": response['messages']}
#
# #agent_executor = AgentExecutor(agent=chatbot,tools=[mcp_tool])
# # ---------------------------------------------------------------------------
# # 3️⃣  Build the agent using LangGraph’s prebuilt ReAct agent
# # ---------------------------------------------------------------------------
# rag_tool = VectorRAG_V1(pdf_path=["docs/MasteringInKafka.pdf","docs/JavaDS.pdf"])

    def _build_graph(self):
        checkpointer = InMemorySaver()
        graph = StateGraph(state_schema=ChatState, async_mode=True)

        graph.add_node("dispatcher_node", self.dispatcher_node)
        graph.add_edge(START, "dispatcher_node")
        graph.add_edge("dispatcher_node", END)

        return graph.compile(checkpointer=checkpointer)

    async def run(self, query):
        initial_state = {
            'messages': [HumanMessage(content=query)],
            'remaining_steps': 25
        }
        return await self.graph.ainvoke(initial_state,config=self.config if hasattr(self, "config") else None)

    @traceable(name="agent.get_input_prompt_action", tags=["jira"])
    async def get_input_prompt_action(self, user_query: str):
        with open("prompt/router_prompt.txt", "r") as f:
            router_prompt = f.read()
        print(f"router_prompt==>{router_prompt}")
        resp = self.llm.invoke([
            SystemMessage(content=router_prompt),  # router behavior
            HumanMessage(content=user_query)  # dynamic user request
        ])
        print(f"getInputToPromptAction=>> {resp.content}")
        return json.loads(resp.content)

    @traceable(name="agent.get_issue_prompt_action", tags=["jira"])
    async def get_issue_prompt_action(self, user_query: dict):
        with open("prompt/fetch_issue_prompt.txt", "r") as f:
            router_prompt = f.read()

        resp = self.llm.invoke([
            SystemMessage(content=router_prompt),  # router behavior
            HumanMessage(content=json.dumps(user_query.get("response"), indent=2))  # dynamic user request
        ])

        print(f"get_issue_prompt_action response =>> {resp}")
        return resp

    @traceable(name="agent.create_jira_task", tags=["jira", "mcp", "tool"])
    async def create_issue_from_user_text(self, user_text: str) -> Dict[str, Any]:
        """
        High level pipeline:
        user_text → LLM JSON → JiraIssueSpec → MCP Jira tool → Jira ticket
        """
        try:

            spec: JiraIssueSpec = await asyncio.to_thread(self.extract_spec_from_text, user_text)
            print(f"Calling create_jira_task - {spec.model_dump()}")

        except Exception as e:
            return {"success": False, "error": str(e)}

        payload = {"payload":spec.model_dump()}
        # Now call MCP tool → this hits Jira API through your MCP server
        try:
            print(f"Before Calling create_jira_task - {payload}")
            result = await self.jira_tool.run(payload)
            print(f"After Calling create_jira_task - {spec}")
        except AttributeError:
            # fallback if tool provides async-callable differently
            # maybe it exposes a call method that is async; try awaiting run() if it is coroutine
            print(f"AttributeError Calling create_jira_task - {payload}")
            res = self.jira_tool.run(payload)
            if asyncio.iscoroutine(res):
                result = await res
            else:
                result = res
        return result

    @traceable(name="llm.extract_jira_spec", tags=["llm", "jira", "parser"])
    def extract_spec_from_text(self, user_text: str) -> JiraIssueSpec:
        """
        Converts user natural text → strict JiraIssueSpec JSON using LLM.
        """
        prompt = f"""
        You are a JSON producer. Given user request, produce a JSON object exactly matching:
    
        {{
          'summary': '<one-line>',
          'description': '<paragraph>',
          'priority': 'Low|Medium|High',
          'issue_type': 'Task|Bug|Story',
          'labels': ['a','b''],
          'assignee': '<email or accountId>',
        }}
    
        User request:
        \"\"\"{user_text}\"\"\"
    
        Return ONLY the JSON object.
        """

        print("user prompt", prompt)
        # structure_llm = self.llm.with_structured_output(JiraIssueSpec)
        resp = self.llm.invoke([HumanMessage(content=prompt)])

        # Extract JSON text
        try:
            # print(f"LLM response is resp.content *************************************{resp.content}")
            llm_text = resp.content
            # print(f"LLM response is  llm_text *************************************{llm_text}")
        except Exception:
            llm_text = str(resp)

        match = re.search(r"(\{[\s\S]*\})", llm_text)
        if not match:
            raise RuntimeError("LLM did not return JSON: " + llm_text)
        # print(f"LLM response is match *************************************{match}")
        obj = json.loads(match.group(1))
        # print(f"LLM response is obj *************************************{obj}")
        return JiraIssueSpec(**obj)

def format_jira_response_html(jira_response: dict) -> str:
    """
    Convert MCP Jira tool response into interactive HTML message.
    Expects response in the format:
    {
        'success': True,
        'issue_key': 'AG-5',
        'response': {'id': '10045', 'key': 'AG-5', 'self': 'https://agent-ui-ai.atlassian.net/rest/api/3/issue/10045'}
    }
    """
    if jira_response["action"] == "jira.add_comment":
        result = jira_response.get("result")
        if not result.get("success"):
            return f"<p style='color:red;'>❌ Failed to create Jira ticket: {result.get('error')}</p>"

        issue_key = result["issue_key"]
        issue_url = result.get("self", "N/A")
        content = text = (
                    result.get("response", {})
                        .get("content", [{}])[0]
                        .get("content", [{}])[0]
                        .get("text", "")
        )
        print(text)

        html_message = f"""
        <div style="font-family: sans-serif; line-height:1.5;">
            <h3 style="color: #2E7D32;">🎉 Your Jira Comment has been successfully added!</h3>
            <p><strong>Ticket Key:</strong> <a href="{issue_url}" target="_blank">{issue_key}</a></p>
            <hr>
            <div style="margin: 10px 0; padding: 10px; background: #ffffff; border-left: 4px solid #4CAF50; border-radius: 6px;">
            <strong>Your Comment is here - </strong><p style="margin: 5px 0px;">{content}</p></div>
            <p>Click the link above to open your ticket directly in Jira.</p>
        </div>
        """
    if jira_response["action"] == "jira.create_issue":
        result = jira_response.get("result")
        if not result.get("success"):
            return f"<p style='color:red;'>❌ Failed to create Jira ticket: {result.get('error')}</p>"

        issue = result["response"]
        issue_key = issue.get("key", "N/A")
        issue_url = issue.get("self", "#")

        html_message = f"""
        <div style="font-family: sans-serif; line-height:1.5;">
            <h3 style="color: #2E7D32;">🎉 Your Jira Ticket has been successfully created!</h3>
            <p><strong>Ticket Key:</strong> <a href="{issue_url}" target="_blank">{issue_key}</a></p>
            <p>Click the link above to open your ticket directly in Jira.</p>
            <hr>
        </div>
        """
    return html_message






