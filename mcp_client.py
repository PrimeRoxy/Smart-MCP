from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def parse_query_with_ai(query, available_tools, available_resources):
    """Use OpenAI to determine which tool to use and extract parameters"""
    
    tools_desc = []
    for name, tool in available_tools.items():
        tools_desc.append({
            "type": "tool",
            "name": name,
            "description": tool.description,
            "parameters": tool.inputSchema
        })
    
    resources_desc = []
    for resource in available_resources:
        resources_desc.append({
            "type": "resource",
            "uri": resource.uri,
            "name": resource.name or resource.uri,
            "description": resource.description,
            "mimeType": resource.mimeType
        })
    
    prompt = f"""Given the user query and available tools/resources, determine which to use and extract the required parameters.

User Query: {query}

Available Tools:
{json.dumps(tools_desc, indent=2)}

Available Resources:
{json.dumps(resources_desc, indent=2)}

Respond with a JSON object containing:
- "type": "tool" or "resource" or null if no appropriate option
- "name": the name of the tool or resource URI to use
- "parameters": an object with the required parameters (for tools) or URI parameters (for resources)
- "reasoning": brief explanation of your choice

Example responses:
{{"type": "tool", "name": "add", "parameters": {{"a": 5, "b": 3}}, "reasoning": "User wants to add two numbers"}}
{{"type": "resource", "name": "greeting://John", "parameters": {{"name": "John"}}, "reasoning": "User wants a greeting for John"}}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that parses user queries to determine which tool or resource to use."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

async def mcpclient():
    async with sse_client(url='http://localhost:8000/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            
            # Get available tools
            tools_response = await session.list_tools()
            tools = {tool.name: tool for tool in tools_response.tools}
            
            # Get available resources
            resources_response = await session.list_resources()
            resources = resources_response.resources
            
            # Get available prompts
            prompts_response = await session.list_prompts()
            prompts = prompts_response.prompts
            
            print("=== Connected to MCP Server with AI-powered query parsing ===\n")
            
            print("Available tools:")
            for name, tool in tools.items():
                print(f"  - {name}: {tool.description}")
            
            print("\nAvailable resources:")
            for resource in resources:
                print(f"  - {resource.uri}: {resource.description or 'No description'}")
            
            print("\nAvailable prompts:")
            for prompt in prompts:
                print(f"  - {prompt.name}: {prompt.description or 'No description'}")
            
            print("\nType 'quit' to exit")
            print("Type 'help' for usage examples\n")
            
            while True:
                # Get user input
                query = input("Enter your query: ").strip()
                
                if query.lower() == 'quit':
                    print("Goodbye!")
                    break
                
                if query.lower() == 'help':
                    print("\nExample queries:")
                    print("  - 'Search for the latest AI news'")
                    print("  - 'Add 25 and 30'")
                    print("  - 'Get a greeting for Alice'")
                    print("  - 'Show me the greeting resource for Bob'\n")
                    continue
                
                try:
                    # Use AI to parse the query
                    print("Analyzing query...")
                    parsed = await parse_query_with_ai(query, tools, resources)
                    
                    if parsed.get("type") is None:
                        print(f"AI: {parsed.get('reasoning', 'No appropriate tool or resource found for this query')}\n")
                        continue
                    
                    item_type = parsed["type"]
                    item_name = parsed["name"]
                    parameters = parsed.get("parameters", {})
                    
                    print(f"AI decided to use '{item_name}' ({item_type})")
                    print(f"Reasoning: {parsed.get('reasoning', '')}")
                    
                    if item_type == "tool":
                        print(f"Parameters: {parameters}")
                        # Execute the tool
                        result = await session.call_tool(item_name, arguments=parameters)
                        print(f"\nResult: {result.content[0].text}\n")
                    
                    elif item_type == "resource":
                        # For resources, we need to construct the URI with parameters
                        if "greeting://" in item_name and parameters.get("name"):
                            resource_uri = f"greeting://{parameters['name']}"
                        else:
                            resource_uri = item_name
                        
                        print(f"Fetching resource: {resource_uri}")
                        # Read the resource
                        resource_result = await session.read_resource(resource_uri)
                        print(f"\nResource content: {resource_result.contents[0].text}\n")
                    
                except json.JSONDecodeError:
                    print("Error: AI response was not valid JSON\n")
                except Exception as e:
                    print(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(mcpclient())