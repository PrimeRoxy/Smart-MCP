import streamlit as st
import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(
    page_title="Neo‑MCP Chat",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Neon Cyberpunk CSS
st.markdown("""
<style>
/* Slim sidebar overlay */
.sidebar-hidden { width: 0; opacity: 0; transition: width 0.3s, opacity 0.3s; }
.sidebar-show:hover { width: 250px; opacity:1; }

/* Center chat container */
.main .block-container { max-width: 800px; margin: auto; }

/* Input panel styling */
.chat-input-wrapper {
  position: fixed; bottom: 20px; width: calc(100% - 400px);
  left: 50%; transform: translateX(-50%);
  background: #12162a; border: 2px solid #00ccff; border-radius: 30px;
}
.chat-input-wrapper input { color: #cc00ff; }

/* Message styling */
[data-testid="stChatMessageContainer"] div.stChatMessage:nth-child(even) {
    background: rgba(204, 0, 255, 0.05);
    border-left: 3px solid #00ccff;
    border-radius: 10px;
}
[data-testid="stChatMessageContainer"] div.stChatMessage:nth-child(odd) {
    background: rgba(0, 204, 255, 0.05);
    border-right: 3px solid #cc00ff;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title(" Neo‑MCP Chat Interface")

# Sidebar: display tools/resources/prompts
with st.sidebar:
    st.header("🔧 Tools / 📦 Resources / 🧠 Prompts")

    if "lists_fetched" not in st.session_state:
        async def _fetch_metadata():
            async with sse_client(url="http://localhost:8000/sse") as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    tools_resp = await session.list_tools()
                    res_resp = await session.list_resources()
                    prom_resp = await session.list_prompts()
                    return tools_resp.tools, res_resp.resources, prom_resp.prompts

        loop = asyncio.new_event_loop()
        tools_list, res_list, prom_list = loop.run_until_complete(_fetch_metadata())
        st.session_state["tools_list"] = tools_list
        st.session_state["res_list"] = res_list
        st.session_state["prom_list"] = prom_list
        st.session_state["lists_fetched"] = True
    else:
        tools_list = st.session_state["tools_list"]
        res_list = st.session_state["res_list"]
        prom_list = st.session_state["prom_list"]

    st.subheader("Tools")
    for t in tools_list:
        st.markdown(f"- **{t.name}** — _{t.description}_")

    st.subheader("Resources")
    for r in res_list:
        st.markdown(f"- `{r.uri}` — _{r.description or '–'}_")

    st.subheader("Prompts")
    for p in prom_list:
        st.markdown(f"- **{p.name}** — _{p.description or '–'}_")

# Initialize chat history
if "history" not in st.session_state:
    st.session_state.history = []

def append_chat(role, content, meta=None):
    st.session_state.history.append({"role": role, "content": content, "meta": meta or {}})

def render_history():
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

async def parse_query_with_ai(query, tools, resources):
    tools_desc = [{"type":"tool","name":t.name,"description":t.description,"parameters":t.inputSchema}
                  for t in tools]
    res_desc = [{"type":"resource","uri":r.uri,"name":(r.name or r.uri),
                 "description":r.description,"mimeType":r.mimeType} for r in resources]
    prompt = (
        "Given the user query and available tools/resources, determine which to use and extract parameters.\n\n"
        f"User Query: {query}\n\nAvailable Tools:\n{json.dumps(tools_desc, indent=2)}\n\n"
        f"Available Resources:\n{json.dumps(res_desc, indent=2)}\n\n"
        "Respond with JSON: {\"type\":… , \"name\":… , \"parameters\":… , \"reasoning\":…}"
    )
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content": "You parse user queries to tool/resource calls."},
            {"role":"user","content": prompt}
        ],
        response_format={"type": "json_object"},
    )
    parsed = json.loads(resp.choices[0].message.content)
    return parsed

async def handle_query_and_response(user_input):
    async with sse_client(url="http://localhost:8000/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            tools_resp = await session.list_tools()
            res_resp = await session.list_resources()
            tools = {t.name: t for t in tools_resp.tools}
            resources = res_resp.resources

            parsed = await parse_query_with_ai(user_input, tools_resp.tools, resources)

            if parsed.get("type") is None:
                return (None, parsed.get("reasoning", "Unmatched"))

            name = parsed["name"]
            typ = parsed["type"]
            params = parsed.get("parameters", {})
            reasoning = parsed.get("reasoning", "")

            if typ == "tool":
                result = await session.call_tool(name, arguments=params)
                return (result.content[0].text, reasoning)

            elif typ == "resource":
                if "greeting://" in name and params.get("name"):
                    name = f"greeting://{params['name']}"
                result = await session.read_resource(name)
                return (result.contents[0].text, reasoning)

            return (None, f"Unknown type: {typ}")

# Chat input processing
user_input = st.chat_input("Type your query…")

if user_input:
    append_chat("user", user_input, {})
    render_history()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_text, reasoning = loop.run_until_complete(handle_query_and_response(user_input))

    reasoning_line = f"> **Reasoning**: {reasoning}" if reasoning else ""
    if bot_text:
        append_chat("assistant", f"{bot_text}\n\n{reasoning_line}")
    else:
        append_chat("assistant", f"❌ {reasoning_line}")

    render_history()
