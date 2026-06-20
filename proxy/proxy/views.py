from rest_framework.views import APIView
from rest_framework.response import Response
from langserve import RemoteRunnable
from django.http import StreamingHttpResponse
import json
from .models import AIModel
from .auth import KeycloakAuthentication
from rest_framework.permissions import IsAuthenticated

# /v1/models returns the active models from the database that the user is authorized to see
class getModels(APIView):
    authentication_classes = [KeycloakAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # asks django for models instead of Ollama
        active_models = AIModel.objects.filter(is_active=True)

        # allowed models are those that match the user's keycloak roles
        if "system" in user.roles:
            allowed_models = {m.name for m in active_models}
        else:
            allowed_models = {m.name for m in active_models if m.name in user.roles} #role name = accessible model from the user

        filtered_models = []

        for m in active_models:
            if m.name in allowed_models:
                filtered_models.append({
                    "id": m.name,
                    "object": "model",
                    "created": 123456789,
                    "owned_by": "django-proxy"
                })
        return Response({"object": "list", "data": filtered_models})

# /v1/chat/completions forwards the request to the correct Langserve agent based on DB mapping and permissions
class chat(APIView):
    authentication_classes = [KeycloakAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # reads the last user message
        lastMessage = request.data["messages"][-1]
        #chat_history = request.data["messages"] # sends all the messages instead of just the latest one
        messageContent = lastMessage["content"]

        # reads the model selected in OpenWebUI
        requested_model = request.data.get("model", "qwen3.5:2b")

        # Allowed models are those that match the user's Keycloak roles
        if "system" in user.roles:
            active_models = AIModel.objects.filter(is_active=True)
            allowed_models = {m.name for m in active_models}
        else:
            active_models = AIModel.objects.filter(is_active=True)
            allowed_models = {m.name for m in active_models if m.name in user.roles}

        #if user chats with models he shouldn't chat with, he gets an error
        if requested_model not in allowed_models:
            return Response({"error": f"You don't have permission to use the model '{requested_model}'."}, status=403)

        # checks if stream is true
        is_streaming = request.data.get("stream", False)

        # route to the dedicated agent service for this model dynamically from DB
        try:
            model_entry = AIModel.objects.get(name=requested_model, is_active=True)
            agent_url = model_entry.agent_url
            print(f"[proxy] Routing request for model '{requested_model}' to agent URL: {agent_url}", flush=True)
        except AIModel.DoesNotExist:
            return Response({"error": f"Model '{requested_model}' is not configured/active in the database"}, status = 503)

        remoteAgent = RemoteRunnable(agent_url)

        # if stream is false, send all the text at once
        if is_streaming:
            def generate_stream():
                for chunk in remoteAgent.stream({
                    "input": messageContent,
                    "model": requested_model,
                    "thread_id": "session_1" }):

                    if chunk:  # for each small piece of text
                        # delta is used to append new chunks instead of overwriting each one
                        data = {"choices": [{"delta": {"content": chunk}}]}

                        # dumps() converts the dictionary to a json string for openwebui
                        yield f"data: {json.dumps(data)}\n\n"  # waits for more chunks

                yield "data: [DONE]\n\n"  # ends the message loading

            # django prepares openwebui to receive a stream
            return StreamingHttpResponse(generate_stream(), content_type="text/event-stream")
        else:
            response = remoteAgent.invoke({
                "input": messageContent,
                "model": requested_model,
                "thread_id": "session_1"
            })

            return Response({"choices": [{"message": {"role": "assistant", "content": response}}]})
        # must be able to communicate in synchronous or streaming mode with LangServe
