# api/views.py
import requests
from django.db import connection
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re

from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import Page, PageEmbedding

# OpenAI API key - ideally, load from environment variable in production
# OPENAI_API_KEY = ""
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def split_markdown_by_header(markdown_text):
    # Use regex to match headers (e.g., # Header, ## Header, ### Header, etc.)
    # Assumes headers are followed by their content until the next header
    pattern = r'(^#{1,6} .+)(?:\n|$)'

    # Split based on headers, keeping headers in the result
    parts = re.split(pattern, markdown_text, flags=re.MULTILINE)

    # Combine headers with their content
    sections = []
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append(f"{header}\n{content}")

    return sections


def get_embedding(url, title, text):
    # Prepare data for embedding generation
    content_for_embedding = f"URL:{url}\n\n TITLE:{title}\n\n CONTENT: {text}"
    return get_embedding_raw(content_for_embedding)


def get_embedding_raw(content_for_embedding):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    embedding_request_data = {
        "input": content_for_embedding,
        "model": "text-embedding-ada-002"
    }

    try:
        # Make a POST request to OpenAI's API for embedding
        embedding_response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=embedding_request_data
        )

        return (False, embedding_response)
    except Exception as e:
        return (True, e)


def generate_embeddings(url, title, sections):
    with ThreadPoolExecutor() as executor:
        futures = []
        results = []
        for i in range(0, len(sections)):
            text = '\n'.join(sections[i:i])
            futures.append(executor.submit(get_embedding, url, title, text))

        for future in as_completed(futures):
            (error, result) = future.result()
            if error:
                return (error, result)
            results.append(result)
        return (False, results)


@csrf_exempt
def add_page(request):
    if request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)

            # Validate required fields
            url = data.get("url")
            title = data.get("title")
            text = data.get("content")
            if not url or not title or not text:
                return JsonResponse({"error": "Missing required fields: url, title, content"}, status=400)

            page = Page.objects.create(url=url, title=title, text=text)

            sections = split_markdown_by_header(text)
            print(f'Creating entries for {url} in sections {len(sections)}')
            with connection.cursor() as cursor:

                (error, embeddings) = generate_embeddings(url, title, sections)
                if error:
                    return JsonResponse({"error": f"Error getting embedding, {embeddings}"}, status=500)

                for embedding_response in embeddings:
                    # Check for a successful response
                    if embedding_response.status_code == 200:
                        embedding_text = embedding_response.json()['data'][0]['embedding']
                    else:
                        # Rollback if embedding generation fails
                        page.delete()
                        error_message = embedding_response.json().get("error", {}).get("message", "Unknown error")
                        return JsonResponse({"error": f"OpenAI API error: {error_message}"}, status=500)

                    cursor.execute(
                        f"""
                        INSERT INTO api_pageembedding (page_id, embedding)
                        VALUES (%s, VEC_FromText('{embedding_text}'))
                        """,
                        [page.id]
                    )

                return JsonResponse({"message": "Page and embedding saved successfully."}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


def chat_gpt_request(system_content="", user_content=""):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}],
        "stream": True
    }

    # Make a request to OpenAI API with streaming enabled
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        )

        # Stream each chunk of data as it arrives from OpenAI
        def event_stream():
            for chunk in response.iter_lines():
                if not chunk:
                    continue

                # Process each line and send it to the client
                line = chunk.decode('utf-8').replace("data: ", "")
                if line == "[DONE]":
                    break
                try:
                    content = json.loads(line)["choices"][0]["delta"].get("content", "")
                    yield f"{content}"
                except json.JSONDecodeError:
                    continue

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    except requests.exceptions.RequestException as e:
        print('Error connecting to OpenAI')
        return JsonResponse({"error": f"Error connecting to OpenAI API {e}"}, status=500)


def get_relevant_content(prompt):
    (error, embedding_response) = get_embedding_raw(prompt)
    if error:
        return None
    embedding_text = embedding_response.json()['data'][0]['embedding']

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT page_id
            FROM api_pageembedding
            ORDER BY VEC_Distance(embedding, Vec_FromText('{embedding_text}'))
            LIMIT 15
            """
        )

        ids = [row[0] for row in cursor.fetchall()]
        print('Fetched X empedding pages:', len(ids))

        print(ids)
        pages = Page.objects.filter(id__in=ids)
        print(pages.query)
        return list(pages)


SYSTEM_PROMPT_DUMB = '''
You are an assistant with access to your general training knowledge about MariaDB. The questions should pertain to MariaDB. Decline to answer anything else.
Provide references if you have them available.

Answer the user's question as accurately as possible.

1. The answers you provide should use only simple HTML. Do not use any syntax similar to markdown. Convert it to HTML.
2. Backquotes should use <pre> tags.
3. The reference should be enclused with an <a href> tag pointing to the correct URL.
4. Separate the reference in a separate <p>paragraph</p>. List all used references in an unordered list.

If the user's question cannot be answered using this information, respond by indicating that the information is not available in the provided resources.
'''.strip()

SYSTEM_PROMPT_SMART = '''
You are an assistant with access to relevant pages from a knowledge base. Answer questions based only on the information within these pages. Do not make assumptions or provide information outside of the content provided.

Each page includes:
- Title: The title of the page
- URL: The URL of the page
- Text: The text content of the page

Use the text content of each relevant page to answer the user's question as accurately as possible, referring to specific information only as it appears in the provided text.
Make sure to provide the URL referenced primarily in your response at the end of your answer.

1. The answers you provide should use only simple HTML. Do not use any syntax similar to markdown. Convert it to HTML.
2. Backquotes should use <pre> tags.
3. The reference should be enclused with an <a href> tag pointing to the correct URL.
4. Separate the reference in a separate <p>paragraph</p>. List all used references in an unordered list.

If the user's question cannot be answered using this information, only respond if the information can be inferred otherwise decline to answer stating that there is not enough information in your knowledge base.
'''.strip()
#respond by indicating that the information is not available in the provided resources.


@csrf_exempt
def chatgpt_context_stream(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_question = data.get("prompt", "")

        pages = get_relevant_content(user_question)
        if not pages:
            return JsonResponse({"error": "Unable to get relevant content"},
                                status=500)

        user_prompt = f"""
        User question: {user_question}

        Relevant pages:
        """ + "\n\n".join([f"Title: {page.title}\nURL: {page.url}\nText: {page.text}" for page in pages])

        user_prompt = user_prompt[:20000] # Limit length

        print(len(user_prompt), len(pages))

        return chat_gpt_request(system_content=SYSTEM_PROMPT_SMART,
                                user_content=user_prompt)
    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)
    return JsonResponse({"error": "Invalid request method"}, status=405)



@csrf_exempt
def chatgpt_stream(request):
    if request.method == "POST":
        data = json.loads(request.body)
        prompt = data.get("prompt", "")

        return chat_gpt_request(system_content=SYSTEM_PROMPT_DUMB, user_content=prompt)

    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)
    return JsonResponse({"error": "Invalid request method"}, status=405)

