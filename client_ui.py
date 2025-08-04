import streamlit as st
import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(
    page_title="Smart‑MCP Chat",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modern Chat Interface CSS matching your image
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global styling */
.stApp { 
    background: #1e2329;
    font-family: 'Inter', sans-serif;
}

/* Hide streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar styling */
.css-1d391kg { 
    background: #1a1d29;
    border-right: 1px solid #3a4553;
}

/* Main container */
.main .block-container { 
    max-width: none;
    padding: 0;
    margin: 0;
}

/* Chat container */
.chat-container {
    display: flex;
    height: 100vh;
    background: #1e2329;
}

.chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #1e2329;
    position: relative;
}

/* Header */
.chat-header {
    padding: 16px 24px;
    border-bottom: 1px solid #3a4553;
    background: #1a1d29;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.chat-title {
    color: #e1e5e9;
    font-size: 18px;
    font-weight: 600;
    margin: 0;
}

.chat-subtitle {
    color: #8b949e;
    font-size: 14px;
    margin: 0;
}

/* Messages area */
.messages-container {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    background: #1e2329;
}

/* Message styling */
.message {
    margin-bottom: 20px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}

.message.user {
    flex-direction: row-reverse;
    justify-content: flex-start;
}

.message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 2px;
}

.user-avatar {
    background: #4a9eff;
    color: white;
}

.assistant-avatar {
    background: #d946ef;
    color: white;
}

.message-content {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 14px;
    line-height: 1.5;
}

.user-message {
    background: #4a9eff;
    color: white;
    border-bottom-right-radius: 4px;
}

.assistant-message {
    background: #2a3441;
    color: #e1e5e9;
    border: 1px solid #3a4553;
    border-bottom-left-radius: 4px;
}

/* Processing status */
.processing-status {
    background: #2a3441;
    border: 1px solid #3a4553;
    border-radius: 12px;
    padding: 16px;
    margin: 10px 0;
    color: #e1e5e9;
    font-size: 13px;
    font-family: 'Monaco', monospace;
}

.processing-step {
    margin: 4px 0;
    opacity: 0.8;
}

.processing-step.active {
    color: #4a9eff;
    opacity: 1;
}

.processing-step.complete {
    color: #00d26a;
    opacity: 1;
}

.processing-step.error {
    color: #ff6b6b;
    opacity: 1;
}

/* Input area */
.input-container {
    position: fixed;
    bottom: 0;
    left: 252px;
    right: 0;
    background: #1e2329;
    border-top: 1px solid #3a4553;
    padding: 20px;
}

.input-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: 800px;
    margin: 0 auto;
}

.stTextInput > div > div > input {
    background: #2a3441 !important;
    border: 1px solid #3a4553 !important;
    border-radius: 24px !important;
    color: #e1e5e9 !important;
    padding: 12px 20px !important;
    font-size: 14px !important;
    width: 100% !important;
}

.stTextInput > div > div > input:focus {
    border-color: #4a9eff !important;
    box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2) !important;
}

.stTextInput > div > div > input::placeholder {
    color: #8b949e !important;
}

/* Send button */
.send-button {
    background: #4a9eff !important;
    border: none !important;
    border-radius: 50% !important;
    width: 44px !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: white !important;
    cursor: pointer !important;
    flex-shrink: 0;
}

.send-button:hover {
    background: #3a8ce8 !important;
}

/* Sidebar tool styling */
.tool-card {
    background: #2a3441;
    border: 1px solid #3a4553;
    border-radius: 12px;
    padding: 16px;
    margin: 12px 0;
    color: #e1e5e9;
    transition: all 0.2s ease;
}

.tool-card:hover {
    border-color: #4a9eff;
    background: #2f3b49;
}

.tool-name {
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 8px;
    color: #4a9eff;
}

.tool-desc {
    font-size: 13px;
    color: #b8bcc8;
    line-height: 1.4;
}

/* Sidebar headers */
.sidebar-header {
    color: #e1e5e9;
    font-size: 16px;
    font-weight: 600;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #3a4553;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
}

::-webkit-scrollbar-track {
    background: #1a1d29;
}

::-webkit-scrollbar-thumb {
    background: #3a4553;
    border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
    background: #4a5563;
}

/* Loading animation */
.loading-dots {
    display: inline-block;
}

.loading-dots::after {
    content: '●';
    animation: dots 1.5s steps(3, end) infinite;
    color: #4a9eff;
}

@keyframes dots {
    0%, 20% { content: '●'; }
    40% { content: '●●'; }
    60%, 100% { content: '●●●'; }
}
</style>
""", unsafe_allow_html=True)

# Custom HTML structure for the chat interface
st.markdown("""
<div class="chat-container">
    <div class="chat-main">
        <div class="chat-header">
            <div>
                <div class="chat-title">Smart-MCP Chat Interface</div>
                <div class="chat-subtitle">Powered by advanced AI reasoning</div>
            </div>
        </div>
        <div class="messages-container" id="messages-container">
            <!-- Messages will be populated here -->
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar: Tool display
with st.sidebar:
    st.markdown('<div class="sidebar-header">🛠️ Available Tools</div>', unsafe_allow_html=True)

    if "lists_fetched" not in st.session_state:
        with st.spinner("Initializing connections..."):
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

    # Display tools
    tool_icons = {
        'insight_scope': '🔍',
        'quickclarity': '⚡',
        'web_search': '🌐',
        'database': '🗄️',
        'file_manager': '📁',
        'default': '⚙️'
    }
    
    for tool in tools_list:
        icon = tool_icons.get(tool.name, tool_icons['default'])
        st.markdown(f"""
        <div class="tool-card">
            <div class="tool-name">{icon} {tool.name}</div>
            <div class="tool-desc">{tool.description}</div>
        </div>
        """, unsafe_allow_html=True)

    # Resources section
    if res_list:
        st.markdown('<div class="sidebar-header">📦 Resources</div>', unsafe_allow_html=True)
        for resource in res_list:
            resource_name = resource.name or resource.uri.split('/')[-1]
            st.markdown(f"""
            <div class="tool-card">
                <div class="tool-name">📄 {resource_name}</div>
                <div class="tool-desc">{resource.description or 'No description available'}</div>
            </div>
            """, unsafe_allow_html=True)

    # Prompts section
    if prom_list:
        st.markdown('<div class="sidebar-header">🧠 AI Prompts</div>', unsafe_allow_html=True)
        for prompt in prom_list:
            st.markdown(f"""
            <div class="tool-card">
                <div class="tool-name">💭 {prompt.name}</div>
                <div class="tool-desc">{prompt.description or 'Custom AI prompt template'}</div>
            </div>
            """, unsafe_allow_html=True)

# Initialize chat history
if "history" not in st.session_state:
    st.session_state.history = []

if "processing_status" not in st.session_state:
    st.session_state.processing_status = []

def add_message(role, content):
    st.session_state.history.append({"role": role, "content": content, "timestamp": time.time()})

def update_processing_status(step, status="active"):
    if not hasattr(st.session_state, 'processing_container'):
        return
    
    steps = [
        f"<div class='processing-step {status}'>→ {step}</div>"
    ]
    
    processing_html = f"""
    <div class="processing-status">
        {''.join(steps)}
    </div>
    """
    st.session_state.processing_container.markdown(processing_html, unsafe_allow_html=True)

def render_messages():
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="message user">
                <div class="message-avatar user-avatar">👤</div>
                <div class="message-content user-message">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message">
                <div class="message-avatar assistant-avatar">🤖</div>
                <div class="message-content assistant-message">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)

async def parse_query_with_ai(query, tools, resources):
    tools_desc = [{"type":"tool","name":t.name,"description":t.description,"parameters":t.inputSchema}
                  for t in tools]
    res_desc = [{"type":"resource","uri":r.uri,"name":(r.name or r.uri),
                 "description":r.description,"mimeType":r.mimeType} for r in resources]
    
    prompt = (
        "Given the user query and available tools/resources, determine which to use and extract parameters.\n\n"
        f"User Query: {query}\n\nAvailable Tools:\n{json.dumps(tools_desc, indent=2)}\n\n"
        f"Available Resources:\n{json.dumps(res_desc, indent=2)}\n\n"
        "Instructions:\n"
        "- Choose EXACTLY ONE item to use\n"
        "- Set 'type' to either 'tool' OR 'resource' (never both)\n"
        "- Provide the exact name/uri of the chosen item\n"
        "- Extract appropriate parameters if needed\n"
        "- Give clear reasoning for your choice\n\n"
        "Respond with JSON: {\"type\":\"tool\" OR \"resource\" , \"name\":\"exact_name_or_uri\" , \"parameters\":{} , \"reasoning\":\"brief explanation\"}"
    )
    
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content": "You are an intelligent query parser that matches user requests to available tools and resources. Always respond with valid JSON and choose exactly one type: 'tool' or 'resource'."},
                {"role":"user","content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Lower temperature for more consistent responses
        )
        
        parsed = json.loads(resp.choices[0].message.content)
        
        # Validate and clean the response
        if "type" not in parsed:
            return {"type": None, "name": "", "parameters": {}, "reasoning": "AI response missing 'type' field"}
        
        # Clean up the type field - remove any invalid characters
        type_value = str(parsed["type"]).strip().lower()
        if type_value not in ["tool", "resource"]:
            # Try to infer from available options
            if tools_desc and "tool" in type_value:
                parsed["type"] = "tool"
            elif res_desc and "resource" in type_value:
                parsed["type"] = "resource"
            else:
                # Default to tool if we have tools available
                parsed["type"] = "tool" if tools_desc else "resource"
        else:
            parsed["type"] = type_value
        
        return parsed
        
    except json.JSONDecodeError as e:
        return {"type": None, "name": "", "parameters": {}, "reasoning": f"Failed to parse AI response as JSON: {str(e)}"}
    except Exception as e:
        return {"type": None, "name": "", "parameters": {}, "reasoning": f"Error in AI query parsing: {str(e)}"}

async def handle_query_and_response(user_input, status_container):
    async with sse_client(url="http://localhost:8000/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            # Step 1: Analyzing query
            status_container.markdown("""
            <div class="processing-status">
                <div class="processing-step active">→ Analyzing query...</div>
            </div>
            """, unsafe_allow_html=True)
            await asyncio.sleep(0.5)

            tools_resp = await session.list_tools()
            res_resp = await session.list_resources()
            tools = {t.name: t for t in tools_resp.tools}
            resources = res_resp.resources

            parsed = await parse_query_with_ai(user_input, tools_resp.tools, resources)

            if parsed.get("type") is None or parsed.get("type") not in ["tool", "resource"]:
                error_msg = parsed.get("reasoning", f"Invalid type returned: {parsed.get('type')}")
                status_container.markdown(f"""
                <div class="processing-status">
                    <div class="processing-step error">❌ {error_msg}</div>
                </div>
                """, unsafe_allow_html=True)
                return (None, error_msg)

            name = parsed["name"]
            typ = parsed["type"]
            params = parsed.get("parameters", {})
            reasoning = parsed.get("reasoning", "")

            # Validate that the chosen tool/resource exists
            if typ == "tool" and name not in tools:
                available_tools = list(tools.keys())
                error_msg = f"Tool '{name}' not found. Available tools: {available_tools}"
                status_container.markdown(f"""
                <div class="processing-status">
                    <div class="processing-step complete">✓ Analyzing query...</div>
                    <div class="processing-step error">❌ {error_msg}</div>
                </div>
                """, unsafe_allow_html=True)
                return (None, error_msg)

            # Step 2: AI Decision
            status_container.markdown(f"""
            <div class="processing-status">
                <div class="processing-step complete">✓ Analyzing query...</div>
                <div class="processing-step active">→ AI decided to use '{name}' ({typ})</div>
                <div class="processing-step">→ Reasoning: {reasoning}</div>
            </div>
            """, unsafe_allow_html=True)
            await asyncio.sleep(0.5)

            # Step 3: Parameters
            status_container.markdown(f"""
            <div class="processing-status">
                <div class="processing-step complete">✓ Analyzing query...</div>
                <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                <div class="processing-step active">→ Parameters: {json.dumps(params)}</div>
            </div>
            """, unsafe_allow_html=True)
            await asyncio.sleep(0.5)

            # Step 4: Execute
            if typ == "tool":
                try:
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step active">→ Executing tool...</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    result = await session.call_tool(name, arguments=params)
                    
                    result_preview = result.content[0].text[:100] + "..." if len(result.content[0].text) > 100 else result.content[0].text
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step complete">✓ Tool executed successfully</div>
                        <div class="processing-step active">→ Result: {result_preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    return (result.content[0].text, reasoning)
                    
                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step error">❌ {error_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    return (None, error_msg)

            elif typ == "resource":
                try:
                    if "greeting://" in name and params.get("name"):
                        name = f"greeting://{params['name']}"
                    
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step active">→ Accessing resource...</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    result = await session.read_resource(name)
                    
                    result_preview = result.contents[0].text[:100] + "..." if len(result.contents[0].text) > 100 else result.contents[0].text
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step complete">✓ Resource accessed successfully</div>
                        <div class="processing-step active">→ Result: {result_preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    return (result.contents[0].text, reasoning)
                    
                except Exception as e:
                    error_msg = f"Resource access failed: {str(e)}"
                    status_container.markdown(f"""
                    <div class="processing-status">
                        <div class="processing-step complete">✓ Analyzing query...</div>
                        <div class="processing-step complete">✓ AI decided to use '{name}' ({typ})</div>
                        <div class="processing-step complete">✓ Reasoning: {reasoning}</div>
                        <div class="processing-step complete">✓ Parameters: {json.dumps(params)}</div>
                        <div class="processing-step error">❌ {error_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    return (None, error_msg)

            return (None, f"Unknown type: {typ}")

# Display chat history
render_messages()

# Input area
st.markdown("""
<div class="input-container">
    <div class="input-wrapper">
""", unsafe_allow_html=True)

# Create columns for input and button
col1, col2 = st.columns([10, 1])
if st.session_state.get("clear_input"):
    st.session_state["user_input"] = ""
    st.session_state["clear_input"] = False
with col1:
    user_input = st.text_input("User input", placeholder="Type your query...", key="user_input", label_visibility="collapsed")

with col2:
    send_clicked = st.button("➤", key="send_btn")

st.markdown("</div></div>", unsafe_allow_html=True)

# Process input
if send_clicked and user_input.strip():
    # Add user message
    add_message("user", user_input)
    
    # Create processing status container
    status_container = st.empty()
    
    # Process the query
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_text, reasoning = loop.run_until_complete(handle_query_and_response(user_input, status_container))
    
    # Remove processing status
    status_container.empty()
    
    # Add response
    if bot_text:
        add_message("assistant", bot_text)
    else:
        add_message("assistant", f"❌ {reasoning}")
    
    # Clear input and rerun
    st.session_state["clear_input"] = True
    st.rerun()

# Auto-scroll to bottom
st.markdown("""
<script>
const container = document.getElementById('messages-container');
if (container) {
    container.scrollTop = container.scrollHeight;
}
</script>
""", unsafe_allow_html=True)