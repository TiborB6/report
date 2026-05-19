from google import genai
from google.genai import types

def query_gemini(
    prompt: str,
    model_name: str = "gemini-2.5-pro",
    enable_web_search: bool = True
) -> str:
    """
    Send a prompt to Gemini and return the text response.
    Optionally, if enable_web_search is True, the model will use Google Search
    to provide real-time, grounded answers from the web.

    Args:
        prompt: The input text/question for Gemini.
        model_name: Which Gemini model to use (default: "gemini-2.5-flash-preview").
        enable_web_search: Whether to enable Google Search grounding.

    Returns:
        The generated text as a string.
    """
    client = genai.Client()

    if enable_web_search:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[google_search_tool])
    else:
        config = None

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )

    return response.text