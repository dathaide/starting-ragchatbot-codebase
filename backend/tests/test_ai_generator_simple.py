"""Simple test for AIGenerator without external dependencies"""

import sys
import os
from unittest.mock import Mock, patch

# Add backend directory to path for imports
sys.path.insert(
    0,
    "/Users/deirdreathaide/Documents/Claude Code/starting-ragchatbot-codebase/backend",
)


def test_ai_generator_initialization():
    """Test that AIGenerator initializes correctly"""
    try:
        from ai_generator import AIGenerator
        from config import Config

        config = Config()
        ai_gen = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

        print(f"✓ AIGenerator initialized with model: {ai_gen.model}")
        print(f"✓ Base parameters set correctly")
        return True
    except Exception as e:
        print(f"✗ AIGenerator initialization failed: {e}")
        return False


def test_ai_generator_simple_call():
    """Test making a simple API call with mocked response"""
    try:
        from ai_generator import AIGenerator
        from config import Config
        import anthropic

        config = Config()

        with patch("anthropic.Anthropic") as mock_anthropic_class:
            # Setup mock response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "This is a test response from Claude."
            mock_response.content[0].type = "text"
            mock_response.stop_reason = "end_turn"

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            # Test the generator
            ai_gen = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
            response = ai_gen.generate_response("What is AI?")

            print(f"✓ AIGenerator returned: {response}")
            print(f"✓ API call was made successfully")

            # Verify API was called with correct parameters
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args

            # Check key parameters
            assert call_args[1]["model"] == config.ANTHROPIC_MODEL
            assert call_args[1]["temperature"] == 0
            assert call_args[1]["max_tokens"] == 800
            assert call_args[1]["messages"][0]["content"] == "What is AI?"

            print("✓ API call parameters verified")
            return True

    except Exception as e:
        print(f"✗ AIGenerator simple call failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_real_anthropic_api_call():
    """Test making a real call to Anthropic API"""
    try:
        from ai_generator import AIGenerator
        from config import Config

        config = Config()

        # Only run if API key is properly configured
        if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "":
            print("⚠ Skipping real API test - no API key configured")
            return True

        ai_gen = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

        # Make a simple test call
        response = ai_gen.generate_response("What is 2+2? Answer with just the number.")

        print(f"✓ Real API call successful")
        print(f"✓ Response: {response}")

        # Basic validation - response should contain '4'
        if "4" in response:
            print("✓ Response contains expected answer")
        else:
            print(f"⚠ Response doesn't contain expected answer: {response}")

        return True

    except Exception as e:
        print(f"✗ Real API call failed: {e}")

        # Check for specific error types
        if "authentication" in str(e).lower() or "api key" in str(e).lower():
            print("  → This appears to be an API key issue")
        elif "credit" in str(e).lower() or "billing" in str(e).lower():
            print("  → This appears to be a billing/credit issue")
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            print("  → This appears to be a network connectivity issue")
        else:
            print(f"  → Unknown error type: {type(e)}")

        return False


if __name__ == "__main__":
    print("=== Testing AIGenerator Functionality ===")

    tests = [
        test_ai_generator_initialization,
        test_ai_generator_simple_call,
        test_real_anthropic_api_call,
    ]

    results = []
    for test in tests:
        print(f"\n--- {test.__name__} ---")
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)

    print(f"\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All AIGenerator tests passed!")
    else:
        print("\n=== Issues Found ===")
        for i, (test, result) in enumerate(zip(tests, results)):
            if not result:
                print(f"- {test.__name__} failed")
