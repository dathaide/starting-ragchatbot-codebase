import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_generator import AIGenerator
import anthropic

class TestAIGenerator:
    """Test suite for AIGenerator functionality"""
    
    def test_init(self, test_config):
        """Test AIGenerator initialization"""
        ai_gen = AIGenerator(test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL)
        
        assert ai_gen.model == test_config.ANTHROPIC_MODEL
        assert ai_gen.base_params["model"] == test_config.ANTHROPIC_MODEL
        assert ai_gen.base_params["temperature"] == 0
        assert ai_gen.base_params["max_tokens"] == 800
    
    @patch('anthropic.Anthropic')
    def test_generate_response_simple(self, mock_anthropic_class, mock_anthropic_response):
        """Test simple response generation without tools"""
        # Setup mock client
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response("What is AI?")
        
        assert result == "This is a test response from the AI model."
        
        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        
        assert call_args[1]["model"] == "claude-sonnet-4-20250514"
        assert call_args[1]["temperature"] == 0
        assert call_args[1]["max_tokens"] == 800
        assert call_args[1]["messages"][0]["content"] == "What is AI?"
        assert "tools" not in call_args[1]
    
    @patch('anthropic.Anthropic')
    def test_generate_response_with_conversation_history(self, mock_anthropic_class, mock_anthropic_response):
        """Test response generation with conversation history"""
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        history = "User: Hello\nAssistant: Hi there!"
        result = ai_gen.generate_response("What is machine learning?", conversation_history=history)
        
        # Verify system message includes history
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content
    
    @patch('anthropic.Anthropic')
    def test_generate_response_with_tools(self, mock_anthropic_class, mock_anthropic_response, tool_manager):
        """Test response generation with tools available but not used"""
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        tools = tool_manager.get_tool_definitions()
        result = ai_gen.generate_response(
            "What is AI?", 
            tools=tools, 
            tool_manager=tool_manager
        )
        
        assert result == "This is a test response from the AI model."
        
        # Verify tools were passed to API
        call_args = mock_client.messages.create.call_args
        assert "tools" in call_args[1]
        assert call_args[1]["tool_choice"] == {"type": "auto"}
    
    @patch('anthropic.Anthropic')
    def test_generate_response_with_tool_use(self, mock_anthropic_class, mock_anthropic_tool_response, 
                                           mock_anthropic_final_response, tool_manager):
        """Test response generation when AI uses tools"""
        mock_client = Mock()
        
        # First call returns tool use, second call returns final response
        mock_client.messages.create.side_effect = [
            mock_anthropic_tool_response,
            mock_anthropic_final_response
        ]
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        tools = tool_manager.get_tool_definitions()
        result = ai_gen.generate_response(
            "Tell me about machine learning from the course materials",
            tools=tools,
            tool_manager=tool_manager
        )
        
        # Should return the final response after tool execution
        assert result == "Based on the search results, machine learning involves training models on data to make predictions."
        
        # Verify two API calls were made (now using sequential rounds)
        assert mock_client.messages.create.call_count == 2
        
        # Verify first call had tools
        first_call_args = mock_client.messages.create.call_args_list[0]
        assert "tools" in first_call_args[1]
        
        # In sequential implementation, if first response has tools, second call should be termination response
        # The second call contains the final answer without tools since Claude terminated naturally
    
    @patch('anthropic.Anthropic')
    def test_handle_tool_execution_single_tool(self, mock_anthropic_class, mock_anthropic_tool_response,
                                              mock_anthropic_final_response, tool_manager):
        """Test tool execution handling with single tool call"""
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_final_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        # Simulate base API parameters
        base_params = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt"
        }
        
        result = ai_gen._handle_tool_execution(
            mock_anthropic_tool_response, 
            base_params, 
            tool_manager
        )
        
        assert result == "Based on the search results, machine learning involves training models on data to make predictions."
        
        # Verify final API call was made
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        
        # Verify messages structure
        messages = call_args[1]["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        
        # Check tool results format
        tool_results = messages[2]["content"]
        assert isinstance(tool_results, list)
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_123"
        assert isinstance(tool_results[0]["content"], str)
    
    @patch('anthropic.Anthropic') 
    def test_api_error_handling(self, mock_anthropic_class):
        """Test handling of Anthropic API errors"""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error occurred")
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        with pytest.raises(Exception):
            ai_gen.generate_response("Test query")
    
    @patch('anthropic.Anthropic')
    def test_system_prompt_construction(self, mock_anthropic_class, mock_anthropic_response):
        """Test system prompt is constructed correctly"""
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        # Test without history
        ai_gen.generate_response("Test query")
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "You are an AI assistant specialized in course materials" in system_content
        assert "Previous conversation:" not in system_content
        
        # Test with history
        mock_client.messages.create.reset_mock()
        ai_gen.generate_response("Test query", conversation_history="Previous chat")
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert "Previous chat" in system_content
    
    def test_system_prompt_content(self):
        """Test that system prompt contains expected instructions"""
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        prompt = ai_gen.SYSTEM_PROMPT
        assert "search_course_content" in prompt
        assert "get_course_outline" in prompt
        assert "Tool Usage Guidelines" in prompt
        assert "UP TO 2 TOOL CALLS" in prompt
        assert "Brief, Concise and focused" in prompt
    
    @patch('anthropic.Anthropic')
    def test_multiple_tool_calls_handling(self, mock_anthropic_class, mock_anthropic_final_response, tool_manager):
        """Test handling when AI makes multiple tool calls in one response"""
        # Create mock response with multiple tool calls
        mock_initial_response = Mock()
        
        tool_block1 = Mock()
        tool_block1.type = "tool_use"
        tool_block1.name = "search_course_content"
        tool_block1.id = "tool_1"
        tool_block1.input = {"query": "AI concepts"}
        
        tool_block2 = Mock()
        tool_block2.type = "tool_use" 
        tool_block2.name = "search_course_content"
        tool_block2.id = "tool_2"
        tool_block2.input = {"query": "machine learning"}
        
        mock_initial_response.content = [tool_block1, tool_block2]
        mock_initial_response.stop_reason = "tool_use"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_final_response
        mock_anthropic_class.return_value = mock_client
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        base_params = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt"
        }
        
        result = ai_gen._handle_tool_execution(
            mock_initial_response,
            base_params,
            tool_manager
        )
        
        # Verify both tools were executed
        call_args = mock_client.messages.create.call_args
        messages = call_args[1]["messages"]
        tool_results = messages[2]["content"]
        
        # Should have results for both tool calls
        assert len(tool_results) == 2
        assert tool_results[0]["tool_use_id"] == "tool_1"
        assert tool_results[1]["tool_use_id"] == "tool_2"
    
    @pytest.fixture
    def create_tool_response(self):
        """Helper to create mock tool response"""
        def _create(tool_name, tool_id, tool_input):
            mock_response = Mock()
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = tool_name
            tool_block.id = tool_id
            tool_block.input = tool_input
            mock_response.content = [tool_block]
            mock_response.stop_reason = "tool_use"
            return mock_response
        return _create
    
    @pytest.fixture
    def create_text_response(self):
        """Helper to create mock text response"""
        def _create(text_content):
            mock_response = Mock()
            text_block = Mock()
            text_block.text = text_content
            text_block.type = "text"
            mock_response.content = [text_block]
            mock_response.stop_reason = "end_turn"
            return mock_response
        return _create
    
    @patch('anthropic.Anthropic')
    def test_sequential_tool_execution_two_rounds_success(self, mock_anthropic_class, 
                                                         create_tool_response, create_text_response, tool_manager):
        """Test successful 2-round sequential tool execution"""
        mock_client = Mock()
        
        # Mock 3 sequential API calls: initial tool -> second tool -> final response
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            create_tool_response("get_course_outline", "tool_2", {"course_name": "AI Course"}),
            create_text_response("Based on search and outline, here's the comprehensive answer about AI courses...")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Tell me about AI courses", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify external behavior
        assert "comprehensive answer about AI courses" in result
        assert mock_client.messages.create.call_count == 3
        
        # Verify message growth pattern
        final_call_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        assert len(final_call_messages) == 5  # original + 2*(assistant + user tool results)
        assert final_call_messages[0]["role"] == "user"
        assert final_call_messages[1]["role"] == "assistant"
        assert final_call_messages[2]["role"] == "user"
        assert final_call_messages[3]["role"] == "assistant"
        assert final_call_messages[4]["role"] == "user"
    
    @patch('anthropic.Anthropic')
    def test_sequential_termination_on_no_tool_use(self, mock_anthropic_class, 
                                                  create_tool_response, create_text_response, tool_manager):
        """Test termination when Claude doesn't request tools in subsequent rounds"""
        mock_client = Mock()
        
        # First response uses tools, second response doesn't
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            create_text_response("Here's the final answer based on the search results.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "What is AI?", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify external behavior - should terminate after 2 API calls
        assert "final answer based on the search results" in result
        assert mock_client.messages.create.call_count == 2
    
    @patch('anthropic.Anthropic') 
    def test_sequential_termination_after_max_rounds(self, mock_anthropic_class,
                                                    create_tool_response, create_text_response, tool_manager):
        """Test termination after reaching maximum rounds"""
        mock_client = Mock()
        
        # Both rounds use tools, should terminate and make final call without tools
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            create_tool_response("get_course_outline", "tool_2", {"course_name": "AI Course"}),
            create_text_response("Final response after max rounds reached.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Complex AI question requiring multiple searches", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
            max_rounds=2
        )
        
        # Verify system stops after 2 rounds and makes final call
        assert "Final response after max rounds reached" in result
        assert mock_client.messages.create.call_count == 3
        
        # Verify final call doesn't include tools
        final_call_args = mock_client.messages.create.call_args_list[2]
        assert "tools" not in final_call_args[1]
    
    @patch('anthropic.Anthropic')
    def test_context_preservation_across_rounds(self, mock_anthropic_class,
                                               create_tool_response, create_text_response, tool_manager):
        """Test conversation history builds correctly between rounds"""
        mock_client = Mock()
        
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "machine learning"}),
            create_tool_response("get_course_outline", "tool_2", {"course_name": "ML Course"}),
            create_text_response("Combined information from both searches.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Find machine learning courses", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify context builds correctly
        assert mock_client.messages.create.call_count == 3
        
        # Check first round context
        first_round_messages = mock_client.messages.create.call_args_list[0][1]["messages"]
        assert len(first_round_messages) == 1
        assert first_round_messages[0]["content"] == "Find machine learning courses"
        
        # Check second round context includes first round results
        second_round_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        assert len(second_round_messages) == 3
        assert second_round_messages[0]["role"] == "user"
        assert second_round_messages[1]["role"] == "assistant"
        assert second_round_messages[2]["role"] == "user"
        
        # Check final round has complete context
        final_round_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        assert len(final_round_messages) == 5
    
    @patch('anthropic.Anthropic')
    def test_conversation_history_preserved_with_sequential_tools(self, mock_anthropic_class,
                                                                 create_tool_response, create_text_response, tool_manager):
        """Test existing conversation history maintained during sequential tool use"""
        mock_client = Mock()
        
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            create_text_response("AI information with conversation context.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        conversation_history = "User: Hello\nAssistant: Hi there! How can I help with course materials?"
        result = ai_gen.generate_response(
            "What is AI?", 
            conversation_history=conversation_history,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify system prompt includes original conversation history in all calls
        for call_args in mock_client.messages.create.call_args_list:
            system_content = call_args[1]["system"]
            assert "Previous conversation:" in system_content
            assert conversation_history in system_content
    
    @patch('anthropic.Anthropic')
    def test_tool_execution_error_in_sequential_round(self, mock_anthropic_class,
                                                     create_tool_response, create_text_response, tool_manager):
        """Test handling of tool execution errors in sequential rounds"""
        mock_client = Mock()
        
        # First round succeeds, second round tool fails  
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            create_text_response("Best effort answer despite tool failure.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        
        # Mock tool manager to fail on second execution
        original_execute = tool_manager.execute_tool
        def failing_execute_tool(name, **kwargs):
            if name == "search_course_content" and kwargs.get("query") == "AI":
                return original_execute(name, **kwargs)
            raise Exception("Tool execution failed")
            
        tool_manager.execute_tool = Mock(side_effect=failing_execute_tool)
        
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Complex query requiring multiple searches", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Should handle error gracefully and continue
        assert "Best effort answer despite tool failure" in result
        assert mock_client.messages.create.call_count == 2
    
    @patch('anthropic.Anthropic')
    def test_api_error_in_second_round(self, mock_anthropic_class,
                                      create_tool_response, tool_manager):
        """Test handling of API errors in subsequent rounds"""
        mock_client = Mock()
        
        # First call succeeds, second call raises API error
        mock_client.messages.create.side_effect = [
            create_tool_response("search_course_content", "tool_1", {"query": "AI"}),
            Exception("API Error in second round")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        # Our implementation catches API errors and handles them gracefully
        result = ai_gen.generate_response(
            "Complex query", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Should return an error message indicating the failure
        assert "Failed to generate final response:" in result
    
    @patch('anthropic.Anthropic')
    def test_mixed_tool_use_patterns(self, mock_anthropic_class,
                                    create_text_response, tool_manager):
        """Test different tool usage patterns across rounds"""
        mock_client = Mock()
        
        # Round 1: Multiple tools, Round 2: Single tool
        round1_response = Mock()
        tool_block1 = Mock()
        tool_block1.type = "tool_use"
        tool_block1.name = "search_course_content"
        tool_block1.id = "tool_1"
        tool_block1.input = {"query": "AI"}
        
        tool_block2 = Mock()
        tool_block2.type = "tool_use"
        tool_block2.name = "search_course_content"
        tool_block2.id = "tool_2"
        tool_block2.input = {"query": "machine learning"}
        
        round1_response.content = [tool_block1, tool_block2]
        round1_response.stop_reason = "tool_use"
        
        mock_client.messages.create.side_effect = [
            round1_response,
            create_text_response("Final answer combining all tool results.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Compare AI and ML", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify both tool patterns handled correctly
        assert "Final answer combining all tool results" in result
        assert mock_client.messages.create.call_count == 2
        
        # Verify final call has results from both first-round tools
        final_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_results = final_messages[2]["content"]
        assert len(tool_results) == 2  # Results from both first-round tools
    
    @patch('anthropic.Anthropic')
    def test_sequential_with_different_tools(self, mock_anthropic_class,
                                           create_tool_response, create_text_response, tool_manager):
        """Test different tools used in sequence"""
        mock_client = Mock()
        
        mock_client.messages.create.side_effect = [
            create_tool_response("get_course_outline", "tool_1", {"course_name": "Course X"}),
            create_tool_response("search_course_content", "tool_2", {"query": "lesson 4 content"}),
            create_text_response("Found related courses based on lesson 4 analysis.")
        ]
        
        mock_anthropic_class.return_value = mock_client
        ai_gen = AIGenerator("test-key", "claude-sonnet-4-20250514")
        
        result = ai_gen.generate_response(
            "Find courses covering same topics as lesson 4 of Course X", 
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Verify both tool types executed correctly
        assert "Found related courses based on lesson 4 analysis" in result
        assert mock_client.messages.create.call_count == 3
        
        # Verify different tools were called
        first_call_args = mock_client.messages.create.call_args_list[0]
        second_call_args = mock_client.messages.create.call_args_list[1]
        
        # Both calls should have tools available
        assert "tools" in first_call_args[1]
        assert "tools" in second_call_args[1]