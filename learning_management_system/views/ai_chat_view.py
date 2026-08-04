# learning_management_system/views/ai_chat_view.py
import json
import re
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from openai import OpenAI
from .rag_utils import query_course_documents, format_context_for_llm


def get_ollama_client():
    """
    Initialize OpenAI-compatible client for Ollama.
    """
    base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1')
    api_key = getattr(settings, 'OLLAMA_API_KEY', 'ollama')

    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )

def get_gemini_client():
    """
    Initialize OpenAI-compatible client for Gemini.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


def _extract_page_target(query_text: str) -> int:
    """
    Extract desired page count from user query (e.g., '6 pages').
    Returns 0 if no explicit page target found.
    """
    m = re.search(r"(\d+)\s*page", query_text.lower())
    if not m:
        return 0
    try:
        return max(0, int(m.group(1)))
    except Exception:
        return 0


def _chat_with_retries(client, model, messages, max_tokens, temperature=0.4, retries=2):
    """
    Retry wrapper for transient 5xx/timeout style failures.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.2 * (attempt + 1))
            else:
                raise last_error


@csrf_exempt
@require_POST
def ai_chat_view(request, course_id):
    """
    Handle AI chat requests from students.

    Expects JSON body with:
        - query: The student's question

    Returns JSON with:
        - success: Boolean
        - response: AI response text
        - sources: List of source documents used (optional)
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
            user_query = data.get('query', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)

        if not user_query:
            return JsonResponse({
                'success': False,
                'error': 'Query cannot be empty'
            }, status=400)

        print(f"[AI Chat] Course: {course_id}, Query: {user_query[:100]}...")

        # Step 1: Query RAG for relevant documents
        q_lower = user_query.lower()
        long_mode_markers = [
            "long answer", "detailed", "in detail", "elaborate", "notes",
            "6 pages", "5 pages", "4 pages", "3 pages", "pages of", "essay"
        ]
        is_long_mode = any(m in q_lower for m in long_mode_markers)
        page_target = _extract_page_target(user_query)
        rag_k = 14 if (is_long_mode or page_target >= 4) else 6
        chunks = query_course_documents(course_id, user_query, k=rag_k)
        context = format_context_for_llm(chunks)

        # Step 2: Prepare messages for LLM
        system_prompt = """You are an AI learning assistant helping students understand course materials.
You have been provided with relevant excerpts from the course documents.
Your task is to answer the student's question based on the provided context.

Guidelines:
1. Answer ONLY from the provided context; do not fabricate details.
2. If context is insufficient, explicitly say what is missing.
3. Write in a student-friendly style similar to ChatGPT/Gemini:
   - clear headings
   - numbered steps
   - examples where available in context
   - concise summary at the end
4. For long-answer requests, provide a comprehensive, well-structured explanation.
5. Keep factual grounding to the uploaded documents.
6. Mention relevant source titles when useful.

Always be helpful and encouraging to the student."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Context from course materials:
{context}

---
Student's Question: {user_query}

Please answer the student's question based on the provided context from the course materials."""}
        ]

        # For explicit long requests like "6 pages", force a target length.
        if page_target:
            approx_words = page_target * 350  # rough A4 estimate
            messages[1]["content"] += f"""

Length requirement:
- Generate approximately {approx_words} to {approx_words + 250} words.
- Use detailed notes format with headings/subheadings.
- If the answer is long, continue naturally without abrupt ending.
"""

        print("done")
        print(chunks)

        # Step 3: Call AI with fallback (Ollama -> Gemini)
        ai_response = None
        provider_used = None
        last_error = None

        # Provider 1: Ollama
        try:
            client = get_ollama_client()
            model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
            response = _chat_with_retries(
                client=client,
                model=model_name,
                messages=messages,
                temperature=0.4,
                max_tokens=2200 if (is_long_mode or page_target) else 1200,
                retries=1
            )
            ai_response = response.choices[0].message.content
            provider_used = f"ollama:{model_name}"
        except Exception as api_error:
            last_error = api_error
            print(f"[AI Chat Warning] Ollama failed, trying Gemini fallback: {api_error}")

        # Provider 2: Gemini fallback
        if not ai_response:
            try:
                client = get_gemini_client()
                primary_model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
                gemini_models = [primary_model, 'gemini-2.0-flash', 'gemini-1.5-flash']
                gemini_models = list(dict.fromkeys(gemini_models))

                gemini_error = None
                for gm in gemini_models:
                    try:
                        response = _chat_with_retries(
                            client=client,
                            model=gm,
                            messages=messages,
                            temperature=0.4,
                            max_tokens=2200 if (is_long_mode or page_target) else 1200,
                            retries=1
                        )
                        ai_response = response.choices[0].message.content
                        provider_used = f"gemini:{gm}"
                        break
                    except Exception as g_err:
                        gemini_error = g_err
                        print(f"[AI Chat Warning] Gemini model {gm} failed: {g_err}")

                if not ai_response:
                    raise gemini_error or Exception("All Gemini fallback models failed")
            except Exception as gemini_error:
                print(f"[AI Chat Error] Gemini fallback failed: {gemini_error}")
                # Final emergency fallback: very short request with trimmed context
                try:
                    short_context = format_context_for_llm(chunks[:4])
                    emergency_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Context:\n{short_context}\n\nQuestion: {user_query}\n\nGive a concise answer from context."}
                    ]
                    em_client = get_gemini_client()
                    em_model = 'gemini-1.5-flash'
                    em_resp = _chat_with_retries(
                        client=em_client,
                        model=em_model,
                        messages=emergency_messages,
                        temperature=0.3,
                        max_tokens=600,
                        retries=1
                    )
                    ai_response = em_resp.choices[0].message.content
                    provider_used = f"gemini:{em_model}:emergency"
                except Exception as em_err:
                    msg = f"Ollama error: {last_error} | Gemini error: {gemini_error} | Emergency error: {em_err}"
                    return JsonResponse({
                        'success': False,
                        'error': msg
                    }, status=500)

        # Multi-pass continuation for explicit long-page requests.
        if page_target and ai_response:
            target_words = page_target * 350
            current_words = len(ai_response.split())
            part_no = 1
            max_parts = 4  # bounded safeguard

            while current_words < target_words and part_no < max_parts:
                part_no += 1
                continuation_prompt = f"""Continue the same answer from where it stopped.
Do not repeat previous content.
Keep continuity and structure.
Add approximately {min(900, target_words - current_words)} more words.

Current partial answer:
{ai_response[-4000:]}
"""
                cont_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": continuation_prompt},
                ]
                try:
                    # Continue with same successful provider first.
                    if provider_used and provider_used.startswith("ollama:"):
                        cont_client = get_ollama_client()
                        cont_model = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
                    else:
                        cont_client = get_gemini_client()
                        cont_model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')

                    cont_resp = cont_client.chat.completions.create(
                        model=cont_model,
                        messages=cont_messages,
                        temperature=0.4,
                        max_tokens=1800
                    )
                    cont_text = (cont_resp.choices[0].message.content or "").strip()
                    if not cont_text:
                        break
                    ai_response = f"{ai_response}\n\n{cont_text}"
                    current_words = len(ai_response.split())
                except Exception as cont_error:
                    print(f"[AI Chat Warning] Continuation part {part_no} failed: {cont_error}")
                    break

        # Step 4: Prepare sources info
        sources = []
        seen_titles = set()
        for chunk in chunks:
            title = chunk.get('metadata', {}).get('title', 'Unknown')
            if title not in seen_titles:
                seen_titles.add(title)
                sources.append(title)

        print(f"[AI Chat] Success via {provider_used} - Response length: {len(ai_response)} chars")

        return JsonResponse({
            'success': True,
            'response': ai_response,
            'sources': sources[:3] if sources else []  # Limit to 3 sources
        })

    except Exception as e:
        print(f"[AI Chat Error] Unexpected error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }, status=500)
