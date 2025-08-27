import anthropic
from typing import List, Optional, Dict, Any

class TerminationResult:
    """Result of checking termination conditions"""
    def __init__(self, should_terminate: bool, final_response: Optional[str] = None, reason: Optional[str] = None):
        self.should_terminate = should_terminate
        self.final_response = final_response
        self.reason = reason

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content**: Search course materials for specific content and detailed information
2. **get_course_outline**: Get complete course outlines with lesson lists, course links, and structure

Tool Usage Guidelines:
- Use **search_course_content** for questions about specific course content or detailed educational materials
- Use **get_course_outline** for questions about course structure, lesson lists, course overviews, or "what's in this course"
- You can make UP TO 2 TOOL CALLS across multiple rounds to gather comprehensive information
- **First round**: Use tools to gather initial information (e.g., search for basic content)
- **Second round**: Use tools for follow-up searches if needed (e.g., get detailed outline, search related content)
- **Sequential strategy**: Use first tool call results to inform second tool call decisions
- Examples of sequential usage:
  * Round 1: search_course_content("machine learning basics")
  * Round 2: get_course_outline("Machine Learning Course") (based on first results)
  * Round 1: get_course_outline("Course X") to find lesson 4 title
  * Round 2: search_course_content("lesson 4 title") to find related courses
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course outline questions**: Use get_course_outline tool, return course title, course link, and complete lesson list with lesson numbers and titles
- **Complex course questions**: May require multiple searches to provide comprehensive answers
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "in my first/second search"
 - Present information as unified knowledge

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value  
3. **Clear** - Use accessible language
4. **Comprehensive** - Utilize multiple tool calls when beneficial for complete answers
5. **Example-supported** - Include relevant examples when they aid understanding

Provide only the direct answer to what was asked, synthesizing information from all tool calls into a cohesive response.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_rounds: int = 2) -> str:
        """
        Generate AI response with sequential tool calling support.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default: 2)
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Initialize conversation with user query
        messages = [{"role": "user", "content": query}]
        
        # Execute sequential rounds if tools are available
        if tools and tool_manager:
            return self._execute_sequential_rounds(
                messages=messages,
                system_content=system_content,
                tools=tools,
                tool_manager=tool_manager,
                max_rounds=max_rounds
            )
        
        # Fallback to single API call without tools
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        
        response = self.client.messages.create(**api_params)
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
    
    def _execute_sequential_rounds(self, messages: List[Dict], 
                                  system_content: str,
                                  tools: List[Dict],
                                  tool_manager,
                                  max_rounds: int = 2) -> str:
        """
        Execute up to max_rounds of tool calling rounds.
        
        Args:
            messages: Initial conversation messages
            system_content: System prompt with context
            tools: Available tools
            tool_manager: Tool execution manager
            max_rounds: Maximum rounds to execute
            
        Returns:
            Final response text
        """
        
        current_messages = messages.copy()
        
        for round_num in range(1, max_rounds + 1):
            try:
                # Prepare API call with tools
                api_params = {
                    **self.base_params,
                    "messages": current_messages,
                    "system": system_content,
                    "tools": tools,
                    "tool_choice": {"type": "auto"}
                }
                
                # Make API call
                response = self.client.messages.create(**api_params)
                
                # Check termination conditions
                termination_result = self._check_termination_conditions(
                    response, round_num, max_rounds
                )
                
                if termination_result.should_terminate:
                    return termination_result.final_response
                
                # Execute tools and update conversation
                current_messages = self._execute_round_tools(
                    current_messages, response, tool_manager
                )
                
            except Exception as e:
                # Tool execution error - terminate gracefully
                error_msg = f"Tool execution failed in round {round_num}: {str(e)}"
                return self._handle_tool_execution_error(error_msg, current_messages, system_content)
        
        # Max rounds reached - make final call without tools
        return self._make_final_call_without_tools(current_messages, system_content)
    
    def _check_termination_conditions(self, response, round_num: int, max_rounds: int) -> TerminationResult:
        """
        Check if we should terminate the sequential calling.
        
        Termination conditions:
        1. No tool_use blocks in Claude's response
        2. Maximum rounds reached (checked in caller)
        3. API error (handled in caller)
        
        Args:
            response: Claude's API response
            round_num: Current round number
            max_rounds: Maximum allowed rounds
            
        Returns:
            TerminationResult indicating whether to terminate and final response
        """
        
        # Check if response contains tool use
        has_tool_use = any(
            hasattr(block, 'type') and block.type == "tool_use" 
            for block in response.content
        )
        
        if not has_tool_use:
            # No tools used - extract text response and terminate
            text_content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    text_content += block.text
            
            return TerminationResult(
                should_terminate=True,
                final_response=text_content,
                reason=f"No tool use in round {round_num}"
            )
        
        # Continue with tool execution
        return TerminationResult(should_terminate=False)
    
    def _execute_round_tools(self, current_messages: List[Dict], 
                            response, tool_manager) -> List[Dict]:
        """
        Execute tools for current round and update conversation messages.
        
        Args:
            current_messages: Current conversation messages
            response: Claude's response with tool use
            tool_manager: Tool manager for execution
            
        Returns:
            Updated messages list with tool results
        """
        
        # Add Claude's response (with tool use) to messages
        updated_messages = current_messages.copy()
        updated_messages.append({"role": "assistant", "content": response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
                    
                except Exception as e:
                    # Individual tool failure
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Tool execution error: {str(e)}"
                    })
        
        # Add tool results as user message
        if tool_results:
            updated_messages.append({"role": "user", "content": tool_results})
        
        return updated_messages
    
    def _handle_tool_execution_error(self, error_msg: str, 
                                    current_messages: List[Dict],
                                    system_content: str) -> str:
        """
        Handle tool execution errors gracefully by making final call without tools.
        
        Args:
            error_msg: Error message to include
            current_messages: Current conversation state
            system_content: System prompt
            
        Returns:
            Error response or best-effort response without tools
        """
        
        # Add error context to conversation
        error_messages = current_messages.copy()
        error_messages.append({
            "role": "user", 
            "content": f"Tool execution failed: {error_msg}. Please provide the best answer you can without using tools."
        })
        
        return self._make_final_call_without_tools(error_messages, system_content)

    def _make_final_call_without_tools(self, messages: List[Dict], 
                                      system_content: str) -> str:
        """
        Make final API call without tools enabled.
        
        Args:
            messages: Complete conversation messages
            system_content: System prompt
            
        Returns:
            Final response text
        """
        
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        
        try:
            response = self.client.messages.create(**api_params)
            return response.content[0].text
        except Exception as e:
            return f"Failed to generate final response: {str(e)}"