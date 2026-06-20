from django.db import models

# in order to add models in the system:
# - pull it from ollama 
# - add django table with its info via migration or from django admin panel
# - add new docker agent with its dedicated port
# - create keycloak role with model's name 

# django translates this python into sql
class AIModel(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the model used by Open WebUI (es. 'qwen3.5:2b')"
    )

    agent_url = models.CharField(
        max_length=500,
        help_text="Complete associated langserve agent's URL (es. 'http://agent-qwen-2b:8001/agent/')"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Able or disable this model at runtime"
    )

    # shows better texts
    def __str__(self):
        return f"{self.name} -> {self.agent_url} ({'Enabled' if self.is_active else 'Disabled'})"
