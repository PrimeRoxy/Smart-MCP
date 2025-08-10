# core/reasoning/agent.py
import logging
import os
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import re
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def format_search_response(raw_content: str) -> tuple[str, List[str]]:
    """
    Format the search response by:
    1. Removing markdown links
    2. Extracting sources separately
    3. Creating a clean, readable summary
    """
    # Extract URLs from markdown links
    url_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    sources = []
    
    # Find all markdown links
    matches = re.findall(url_pattern, raw_content)
    for text, url in matches:
        # Clean up the URL (remove utm_source parameters)
        clean_url = url.split('?')[0]
        if clean_url not in sources:
            sources.append(clean_url)
    
    # Remove markdown links from the content
    clean_content = re.sub(url_pattern, r'\1', raw_content)
    
    # Remove parentheses that contained sources
    clean_content = re.sub(r'\s*\([^)]*https?://[^)]+\)', '', clean_content)
    
    # Clean up extra spaces and punctuation
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    clean_content = re.sub(r'\s+([.,;])', r'\1', clean_content)
    
    return clean_content, sources

def perform_search(user_query: str) -> tuple[str, List[str]]:
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        web_search_options={"search_context_size": "low"},
        messages=[
            {
                "role": "system",
                "content": """Answer the user's query with accurate, real-time web results. 
                Format your response as a clear, concise paragraph without any markdown formatting.
                Include source citations naturally in the text."""
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
    )
    
    raw_content = response.choices[0].message.content.strip()
    summary, sources = format_search_response(raw_content)
    
    return summary, sources

class TaskType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    CREATION = "creation"
    VALIDATION = "validation"
    FORMATTING = "formatting"
    CALCULATION = "calculation"
    DIRECT_SOLVE = "direct_solve"
    REASONING = "reasoning"
    VERBAL_REASONING = "verbal_reasoning"
    NON_VERBAL_REASONING = "non_verbal_reasoning"
    CODING = "coding"

class TaskState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    type: TaskType
    description: str
    dependencies: List[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    goal: str
    tasks: List[Task]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

class ReasoningAgent:
    def __init__(self):
        self.model = "gpt-4o"
        self.executor = ThreadPoolExecutor(max_workers=4)


    def _detect_problem_type(self, query: str) -> Dict[str, Any]:
        """AI-powered problem type detection with same return structure"""
        
        prompt = f"""
        Analyze this query and classify it comprehensively. You must return ONLY a valid JSON object with no markdown formatting.

        Query: "{query}"

        Return ONLY the JSON object in this exact structure (no code blocks, no markdown):
        {{
            "is_mathematical": boolean,
            "is_logical_reasoning": boolean,
            "is_analytical": boolean,
            "is_creative": boolean,
            "is_factual": boolean,
            "is_verbal_reasoning": boolean,
            "is_non_verbal_reasoning": boolean,
            "is_simple_solvable": boolean,
            "is_coding": boolean,
            "domain": string,
            "requires_calculation": boolean,
            "requires_research": boolean,
            "requires_multi_step_reasoning": boolean,
            "complexity": string,
            "calculation_type": string or null,
            "reasoning_type": string or null,
            "reasoning_subtype": string or null,
            "coding_type": string or null,
            "parameters": object,
            "query_intent": string,
            "confidence_level": number
        }}

        ## CLASSIFICATION METHODOLOGY

        ### STEP 1: INTENT IDENTIFICATION
        **Primary Query Intents:**
        - "solve": Mathematical problems, calculations, logical puzzles
        - "explain": Definitions, concepts, how-to explanations
        - "analyze": Comparisons, evaluations, assessments
        - "create": Writing, design, brainstorming, code generation
        - "research": Information gathering, fact-checking, current events
        - "debug": Code troubleshooting, error resolution
        - "optimize": Performance improvement, efficiency enhancement
        - "transform": Data conversion, format changes, translations
        - "identity": Questions about AI capabilities, identity, creator
        - "procedure": Step-by-step instructions, workflows

        ### STEP 2: COMPLEXITY ASSESSMENT
        **Refined Complexity Scale:**

        **SIMPLE (1-2 steps, < 30 seconds mental processing):**
        - Single arithmetic operations (basic +, -, *, /)
        - Direct fact lookups or definitions
        - Basic code syntax questions
        - Simple yes/no questions
        - Elementary analogies or relations
        - Straightforward percentage calculations
        - Examples: "What's 15 + 23?", "Define recursion", "A is B's father. What is B to A?"

        **MEDIUM (3-5 steps, 30 seconds - 2 minutes processing):**
        - Multi-step calculations (2-4 operations)
        - Moderate reasoning chains
        - Algorithm implementations
        - Word problems requiring setup
        - Analysis with multiple factors
        - Code debugging or optimization
        - Examples: "Calculate 20% compound interest over 3 years", "Implement binary search", "Blood relation with 3+ people"

        **COMPLEX (6+ steps, 2+ minutes processing):**
        - Advanced mathematical proofs or complex formulas
        - System design problems
        - Multi-constraint optimization
        - Research requiring synthesis
        - Advanced algorithms or data structures
        - Deep analytical reasoning with multiple premises
        - Examples: "Design a scalable distributed system", "Prove mathematical theorems", "Optimize complex algorithms"

        ### STEP 3: DOMAIN CLASSIFICATION
        **Enhanced Domain Categories:**
        - "mathematics": Problems with numbers, calculations, formulas, mathematical concepts
        - "verbal_reasoning": Blood relations, analogies, coding-decoding, letter series, word problems
        - "non_verbal_reasoning": Spatial, visual, pattern-based reasoning
        - "programming": Code, algorithms, software development
        - "logic": Formal logic, arguments, deductive reasoning
        - "analysis": Comparison, evaluation, critical thinking
        - "creative": Writing, design, artistic tasks
        - "factual": Information requests, definitions, explanations
        - "conversational": Greetings, casual chat, personal questions
        - "procedural": Instructions, workflows, tutorials
        - "scientific": Physics, chemistry, biology, research
        - "business": Economics, finance, management, strategy
        - "general": Miscellaneous or hybrid queries

        ### STEP 4: RESEARCH REQUIREMENTS
        **Always requires_research: true for:**
        - AI identity/capability questions
        - Current events (after knowledge cutoff)
        - Factual information about real entities
        - Historical events and dates
        - Scientific facts and discoveries
        - Company/product information
        - Biographical information
        - Technical specifications
        - Legal/regulatory information
        - Medical/health information
        - Geographic/demographic data

        **Never requires_research (pure reasoning):**
        - Mathematical calculations
        - Logical deductions
        - Code implementation
        - Creative writing
        - Hypothetical scenarios
        - Pattern recognition
        - Spatial reasoning

        ### STEP 5: CALCULATION TYPES (Extended)
        - "basic_arithmetic": Addition, subtraction, multiplication, division
        - "percentage": Percentage calculations, ratios, proportions
        - "compound_interest": Financial calculations with compounding
        - "simple_interest": Linear interest calculations
        - "profit_loss": Business math, margins, breakeven
        - "speed_distance_time": Motion problems, rates
        - "work_time": Efficiency, productivity calculations
        - "probability": Probability, statistics, combinations
        - "geometry": Area, volume, perimeter, angles
        - "algebra": Equations, inequalities, factoring
        - "calculus": Derivatives, integrals, limits
        - "statistics": Mean, median, mode, distributions
        - "trigonometry": Sin, cos, tan, triangles
        - "logarithms": Log calculations, exponentials
        - "mixture": Alligation, concentration problems
        - "age_problems": Age-related word problems
        - "general_math": Other mathematical operations

        ### STEP 6: REASONING SUBTYPES (Extended)
        **Verbal Reasoning:**
        - "blood_relation": Family relationships, kinship, not age related calculations
        - "analogy": Word relationships, analogies
        - "classification": Odd one out, categorization
        - "coding_decoding": Cipher, code languages
        - "statement_argument": Logical arguments, assumptions
        - "syllogism": Formal logical reasoning
        - "theme_detection": Main ideas, central themes
        - "letter_series": Alphabetical patterns
        - "input_output": Transformation rules
        - "venn_diagram": Set operations
        - "critical_reasoning": Argument evaluation

        **Non-Verbal Reasoning:**
        - "calendar_clock": Date/time calculations
        - "direction_distance": Navigation, spatial orientation
        - "pattern_recognition": Visual patterns, sequences
        - "spatial_reasoning": 3D visualization, rotation
        - "data_interpretation": Charts, graphs, tables
        - "image_analysis": Visual pattern recognition
        - "cube_folding": 3D spatial manipulation
        - "mirror_images": Reflection, symmetry
        - "series_completion": Number/figure patterns

        ### STEP 7: CODING TYPES (Extended)
        - "data_structures": Arrays, trees, graphs, stacks, queues
        - "algorithms": Sorting, searching, dynamic programming
        - "web_development": HTML, CSS, JavaScript, frameworks
        - "system_design": Architecture, scalability, distributed systems
        - "database": SQL, NoSQL, data modeling
        - "machine_learning": AI/ML algorithms, models
        - "debugging": Error resolution, troubleshooting
        - "optimization": Performance improvement
        - "api_development": REST, GraphQL, microservices
        - "mobile_development": iOS, Android, cross-platform
        - "devops": CI/CD, deployment, infrastructure
        - "security": Encryption, authentication, vulnerabilities
        - "testing": Unit tests, integration tests, TDD
        - "general_programming": Basic programming concepts

        ### STEP 8: PARAMETER EXTRACTION
        Extract and structure relevant information:
        - Numbers and mathematical values
        - Names and entities
        - Locations and directions
        - Time and date information
        - Programming languages and technologies
        - Units of measurement
        - Constraints and conditions
        - Context clues

        ## CRITICAL VALIDATION RULES

        1. **Research Flag Priority**: If query asks about real-world facts, current events, or AI identity, requires_research MUST be true
        2. **Complexity Consistency**: Ensure complexity rating matches the actual cognitive load
        3. **Domain Specificity**: Choose the most specific domain that captures the query's essence
        4. **Intent Clarity**: The query_intent should clearly indicate what the user wants
        5. **Parameter Relevance**: Only extract parameters that are genuinely relevant to the query

        ## EDGE CASES TO HANDLE

        - **Hybrid queries**: Combine multiple classification types appropriately
        - **Implicit requirements**: Infer unstated but necessary requirements
        - **Cultural/contextual sensitivity**: Consider different interpretations
        - **Technical jargon**: Handle domain-specific terminology
        - **Conversational queries**: Distinguish between casual chat and specific requests
        - **Multi-part queries**: Handle compound questions appropriately

        Return ONLY valid JSON without any markdown formatting or code blocks.
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content.strip()
            
            problem_type = json.loads(response_content)
            print("Parsed problem type:", problem_type)
            
            # Ensure complexity is properly set if missing (fallback only)
            if "complexity" not in problem_type or not problem_type["complexity"]:
                problem_type["complexity"] = "medium"  # Safe fallback
            
            return problem_type
            
        except Exception as e:
            print("Error occurred while detecting problem type:", e)
            print("Raw response content:", response.choices[0].message.content if 'response' in locals() else "No response")
            
            # Enhanced fallback with better detection
            query_lower = query.lower()
            
            # Check for mathematical problems
            math_keywords = ["calculate", "solve", "find", "determine", "compute", "percentage", "profit", "loss", "speed", "distance", "time", "interest", "mixture", "work", "efficiency"]
            has_math = any(word in query_lower for word in math_keywords) and any(char.isdigit() for char in query)
            
            # Check for verbal reasoning
            verbal_keywords = ["father", "mother", "son", "daughter", "brother", "sister", "relation", "related", "photograph", "pointing"]
            has_verbal = any(word in query_lower for word in verbal_keywords)
            
            # Check for coding
            coding_keywords = ["code", "program", "implement", "algorithm", "python", "java", "javascript", "function", "class", "array", "list"]
            has_coding = any(word in query_lower for word in coding_keywords)
            
            # Check for factual questions
            factual_keywords = ["what is", "who is", "define", "explain", "describe", "tell me about"]
            has_factual = any(phrase in query_lower for phrase in factual_keywords)
            
            # Determine domain and type
            if has_math:
                domain = "mathematics"
                calculation_type = "general_math"
                if "percentage" in query_lower:
                    calculation_type = "percentage"
                elif "mixture" in query_lower:
                    calculation_type = "mixture"
                elif "profit" in query_lower or "loss" in query_lower:
                    calculation_type = "profit_loss"
                elif "speed" in query_lower or "distance" in query_lower or "time" in query_lower:
                    calculation_type = "speed_distance_time"
                elif "work" in query_lower or "efficiency" in query_lower:
                    calculation_type = "work_time"
                elif "interest" in query_lower:
                    calculation_type = "simple_interest" if "simple" in query_lower else "compound_interest"
            elif has_verbal:
                domain = "verbal_reasoning"
                calculation_type = None
            elif has_coding:
                domain = "programming"
                calculation_type = None
            elif has_factual:
                domain = "factual"
                calculation_type = None
            else:
                domain = "general"
                calculation_type = None
            
            # Create the problem type dictionary
            problem_type = {
                "is_mathematical": has_math,
                "is_logical_reasoning": has_verbal,
                "is_analytical": False,
                "is_creative": False,
                "is_factual": has_factual,
                "is_verbal_reasoning": has_verbal,
                "is_non_verbal_reasoning": False,
                "is_simple_solvable": True,
                "is_coding": has_coding,
                "domain": domain,
                "requires_calculation": has_math,
                "requires_research": has_factual,
                "requires_multi_step_reasoning": has_math or has_verbal,
                "complexity": self._determine_complexity(query, {
                    "is_mathematical": has_math,
                    "is_coding": has_coding,
                    "is_verbal_reasoning": has_verbal,
                    "requires_calculation": has_math,
                    "requires_research": has_factual,
                    "requires_multi_step_reasoning": has_math or has_verbal
                }),
                "calculation_type": calculation_type,
                "reasoning_type": "verbal" if has_verbal else None,
                "reasoning_subtype": "blood_relation" if has_verbal and any(word in query_lower for word in ["father", "mother", "son", "daughter", "relation", "related"]) else None,
                "coding_type": "general_programming" if has_coding else None,
                "parameters": {}
            }
            
            return problem_type

    def _determine_complexity(self, query: str, problem_type: Dict[str, Any]) -> str:
        """Helper method to determine complexity based on query and problem type"""
        
        word_count = len(query.split())
        
        if problem_type.get("is_coding", False):
            # Coding problems are typically medium complexity
            coding_type = problem_type.get("coding_type", "")
            if word_count > 50 or coding_type in ["system_design", "algorithms"]:
                return "complex"
            elif coding_type in ["data_structures", "web_development"]:
                return "medium"
            else:
                return "simple"
        
        elif problem_type.get("is_verbal_reasoning", False) or problem_type.get("is_non_verbal_reasoning", False):
            # Reasoning problems are typically simple to medium complexity
            reasoning_subtype = problem_type.get("reasoning_subtype", "")
            if word_count > 50 or reasoning_subtype in ["syllogism", "statement_argument"]:
                return "medium"
            else:
                return "simple"
        
        else:
            # General complexity logic for other types
            complexity_indicators = 0
            if problem_type.get("requires_calculation", False): 
                complexity_indicators += 1
            if problem_type.get("requires_research", False): 
                complexity_indicators += 1
            if problem_type.get("requires_multi_step_reasoning", False): 
                complexity_indicators += 1
            if word_count > 30: 
                complexity_indicators += 1
            
            if complexity_indicators <= 1:
                return "simple"
            elif complexity_indicators <= 3:
                return "medium"
            else:
                return "complex"
 
    
    async def process_request(self, query: str, max_depth: int = 5, 
                            include_sources: bool = True) -> Dict[str, Any]:
        """Universal entry point for processing any type of request"""
        start_time = time.time()
        sources_used = []
        execution_plan = None
        
        try:
            problem_info = self._detect_problem_type(query)
            if problem_info["requires_research"] and not problem_info["is_mathematical"] and not problem_info["is_coding"]:
                result = await self._research_and_answer(query, problem_info, sources_used)
                execution_plan = self._create_research_plan(query, problem_info)
            else:
                result = await self._solve_directly(query, problem_info)
                execution_plan = self._create_direct_solve_plan(query, problem_info)

            execution_time = time.time() - start_time
            return {
                "success": True,
                "result": result,
                "execution_plan": self._plan_to_dict(execution_plan),
                "execution_time": execution_time,
                "sources_used": sources_used if include_sources else [],
                "problem_type": problem_info
            }
            
        except Exception as e:
            logging.error(f"Error in reasoning agent: {str(e)}")
            return {
                "success": False,
                "result": {"error": str(e)},
                "execution_plan": {},
                "execution_time": time.time() - start_time,
                "sources_used": []
            }
    
    def _create_direct_solve_plan(self, query: str, problem_info: Dict[str, Any]) -> ExecutionPlan:
        """Create a simple execution plan for direct solving"""
        task_type = TaskType.DIRECT_SOLVE
        
        if problem_info["is_coding"]:
            task_type = TaskType.CODING
        elif problem_info["is_verbal_reasoning"]:
            task_type = TaskType.VERBAL_REASONING
        elif problem_info["is_non_verbal_reasoning"]:
            task_type = TaskType.NON_VERBAL_REASONING
        
        direct_task = Task(
            id="direct_solve",
            type=task_type,
            description=f"Solve the {problem_info.get('coding_type', problem_info.get('reasoning_subtype', 'problem'))}: {query}",
            state=TaskState.COMPLETED,
            parameters=problem_info.get("parameters", {})
        )
        
        return ExecutionPlan(
            goal=query,
            tasks=[direct_task],
            context={
                "approach": "direct_solving",
                "problem_type": problem_info,
                "complexity": problem_info.get("complexity", "medium")
            }
        )
    
    def _create_research_plan(self, query: str, problem_info: Dict[str, Any]) -> ExecutionPlan:
        """Create a simple execution plan for research-based answers"""
        research_task = Task(
            id="research_and_answer",
            type=TaskType.RESEARCH,
            description=f"Research and answer: {query}",
            state=TaskState.COMPLETED,
            parameters=problem_info.get("parameters", {})
        )
        
        return ExecutionPlan(
            goal=query,
            tasks=[research_task],
            context={
                "approach": "research_based",
                "problem_type": problem_info,
                "complexity": problem_info.get("complexity", "simple")
            }
        )
    
    async def _solve_directly(self, query: str, problem_info: Dict[str, Any]) -> Dict[str, Any]:
        """Universal direct solver for all types of problems"""
        
        reasoning_type = problem_info.get("reasoning_type", "general")
        reasoning_subtype = problem_info.get("reasoning_subtype", "general")
        calculation_type = problem_info.get("calculation_type", "general")
        coding_type = problem_info.get("coding_type", "general")
        domain = problem_info.get("domain", "general")
        
        # Create comprehensive solving framework
        solving_framework = self._get_solving_framework(reasoning_type, reasoning_subtype, calculation_type, coding_type, domain)
        print(" ******* Generated solving framework:", solving_framework)
        
        prompt = f"""
        You are an expert problem solver with deep knowledge across all domains, especially programming, verbal and non-verbal reasoning. Solve this problem with clarity and precision.
        
        PROBLEM: {query}
        
        PROBLEM ANALYSIS:
        - Domain: {domain}
        - Reasoning Type: {reasoning_type}
        - Reasoning Subtype: {reasoning_subtype}
        - Calculation Type: {calculation_type}
        - Coding Type: {coding_type}
        - Coding: {problem_info.get('is_coding', False)}
        - Verbal Reasoning: {problem_info.get('is_verbal_reasoning', False)}
        - Non-Verbal Reasoning: {problem_info.get('is_non_verbal_reasoning', False)}
        - Mathematical: {problem_info.get('is_mathematical', False)}
        - Logical Reasoning: {problem_info.get('is_logical_reasoning', False)}
        - Analytical: {problem_info.get('is_analytical', False)}
        - Creative: {problem_info.get('is_creative', False)}
        - Factual: {problem_info.get('is_factual', False)}
        - Parameters: {problem_info.get('parameters', {})}
        
        {solving_framework}
        
        UNIVERSAL SOLUTION REQUIREMENTS:
        1. Start with "SOLUTION:" as the header
        2. Show your approach and reasoning clearly
        3. For coding problems: Show complete, working code implementation
        4. For reasoning problems: Show step-by-step logical analysis
        5. For mathematical problems: Show step-by-step calculations
        6. For analytical problems: Show analysis process
        7. For creative problems: Show creative process
        8. For factual problems: Provide comprehensive information
        9. Use appropriate notation, formulas, or code structures
        10. Explain each step briefly but clearly
        11. End with "FINAL ANSWER:" followed by a direct, complete answer
        
        CRITICAL GUIDELINES:
        - Be precise and accurate in all reasoning
        - Show all work for mathematical problems
        - Provide complete, working code for programming problems
        - Use proper logical structure for reasoning problems
        - Provide evidence for factual claims
        - Always address exactly what was asked
        - Double-check your work
        - If information is insufficient, state that clearly
        
        SOLUTION FORMAT:
        SOLUTION:
        
        Step 1: Understanding the Problem
        [Clearly state what needs to be solved and identify the type of problem]
        
        Step 2: Approach/Method
        [Explain your approach or method specific to this type of problem]
        
        Step 3: Implementation/Analysis/Reasoning
        [Show detailed work - code implementation, reasoning steps, calculations, analysis, pattern recognition, etc.]
        
        Step 4: Verification (if applicable)
        [Test your solution/answer if possible]
        
        FINAL ANSWER: [Direct, complete answer to the original question]
        
        Now solve the problem following this format:
        """
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 if problem_info.get('is_mathematical') else 0.2,
            max_tokens=3000
        )
        
        solution = response.choices[0].message.content
        print("Solution generated:", solution)
        
        # Extract the final answer
        final_answer_match = re.search(r'FINAL ANSWER:\s*(.+?)(?:\n\n|\n$|$)', solution, re.IGNORECASE | re.DOTALL)
        final_answer = final_answer_match.group(1).strip() if final_answer_match else "Answer not clearly identified"
        return {
            "type": "direct_solution",
            "content": solution,
            "final_answer": final_answer,
            "problem_type": coding_type or reasoning_subtype or calculation_type or domain,
            "complexity": problem_info.get("complexity", "simple"),
            "solved_directly": True,
            "reasoning_type": reasoning_type,
            "reasoning_subtype": reasoning_subtype,
            "coding_type": coding_type
        }

    def _get_solving_framework(self, reasoning_type: str, reasoning_subtype: str, calculation_type: str, coding_type: str, domain: str) -> str:
        """Get appropriate solving framework based on problem type using OpenAI"""
        
        # Build the prompt for OpenAI to generate the framework
        prompt = f"""Generate a comprehensive problem-solving framework for the following problem characteristics:

    Domain: {domain}
    Reasoning Type: {reasoning_type}
    Reasoning Subtype: {reasoning_subtype}
    Calculation Type: {calculation_type}
    Coding Type: {coding_type}

    Please provide a structured framework following this exact format:

    [FRAMEWORK_NAME] FRAMEWORK:
    1. STEP_NAME: Brief description of what to do in this step
    2. STEP_NAME: Brief description of what to do in this step
    3. STEP_NAME: Brief description of what to do in this step
    4. STEP_NAME: Brief description of what to do in this step
    5. STEP_NAME: Brief description of what to do in this step
    6. STEP_NAME: Brief description of what to do in this step

    SOLVING APPROACH:
    - Specific guideline or technique
    - Specific guideline or technique
    - Specific guideline or technique
    - Specific guideline or technique
    - Specific guideline or technique

    The framework should be tailored specifically to the problem type and domain provided. Make it practical, actionable, and comprehensive for solving problems in this category."""

        try:
            # Call OpenAI API to generate the framework
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Extract and return the generated framework
            framework = response.choices[0].message.content.strip()
            return framework
            
        except Exception as e:
            return f"""GENERAL PROBLEM SOLVING FRAMEWORK:
    1. PROBLEM ANALYSIS: Understand the specific requirements and constraints
    2. APPROACH SELECTION: Choose the most appropriate method for this problem type
    3. SYSTEMATIC EXECUTION: Apply the chosen approach step by step
    4. VERIFICATION: Check that the solution meets all requirements
    5. OPTIMIZATION: Refine the solution for better performance or clarity
    6. VALIDATION: Ensure the final answer is correct and complete

    SOLVING APPROACH:
    - Break down complex problems into manageable parts
    - Apply domain-specific knowledge and techniques
    - Verify each step before proceeding to the next
    - Consider alternative approaches if needed
    - Present the solution clearly and comprehensively

    Note: Framework generated for {domain} domain with {reasoning_type} reasoning."""
    

    async def _research_and_answer(self, query: str, problem_info: Dict[str, Any], 
                                 sources_used: List[str]) -> Dict[str, Any]:
        """Research-focused approach for factual questions"""
        
        # Gather information from multiple sources
        research_data = {}
        
        # # Try RAG first
        # try:
        #     rag_context = get_similar_docs(query)
        #     research_data["rag_context"] = rag_context
        # except Exception as e:
        #     logging.warning(f"RAG search failed: {e}")
        #     research_data["rag_context"] = None
        
        # Try web search
        try:
            web_summary, web_sources = perform_search(query)
            research_data["web_search"] = web_summary
            sources_used.extend(web_sources)
        except Exception as e:
            logging.warning(f"Web search failed: {e}")
            research_data["web_search"] = None
        
        prompt = f"""
        You are an expert researcher and information synthesizer. Provide a comprehensive answer based on available information.
        
        QUESTION: {query}
        
        AVAILABLE INFORMATION:
        RAG Context: {research_data.get('rag_context', 'Not available')}
        Web Search Results: {research_data.get('web_search', 'Not available')}
        
        RESEARCH REQUIREMENTS:
        1. Provide accurate, comprehensive information
        2. Organize the answer logically
        3. Include specific details and examples
        4. Cite sources when available
        5. Indicate if information is limited or uncertain
        
        ANSWER FORMAT:
        RESEARCH SUMMARY:
        
        Overview: [Brief overview of the topic]
        
        Detailed Information:
        [Comprehensive details organized logically]
        
        Key Points:
        [Important facts and highlights]
        
        Additional Context:
        [Relevant background or related information]
        
        FINAL ANSWER: [Direct, complete answer to the original question]
        
        Be thorough but concise, accurate, and well-organized.
        """
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        research_result = response.choices[0].message.content
        
        # Extract final answer
        final_answer_match = re.search(r'FINAL ANSWER:\s*(.+?)(?:\n\n|\n$|$)', research_result, re.IGNORECASE | re.DOTALL)
        final_answer = final_answer_match.group(1).strip() if final_answer_match else "Answer not clearly identified"
        
        return {
            "type": "research_based_answer",
            "content": research_result,
            "final_answer": final_answer,
            "sources_used": len(sources_used),
            "research_quality": "high" if research_data.get('web_search') or research_data.get('rag_context') else "limited"
        }
    
    def _plan_to_dict(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Convert ExecutionPlan to dictionary for response"""
        return {
            "goal": plan.goal,
            "tasks": [
                {
                    "id": task.id,
                    "type": task.type,
                    "description": task.description,
                    "state": task.state,
                    "dependencies": task.dependencies,
                    "parameters": task.parameters,
                    "error": task.error
                }
                for task in plan.tasks
            ],
            "context": plan.context,
            "created_at": plan.created_at
        }

# Initialize the enhanced reasoning agent
reasoning_agent = ReasoningAgent()