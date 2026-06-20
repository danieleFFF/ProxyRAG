from django.db import migrations

# forward function
def seed_default_models(apps, schema_editor):
    AIModel = apps.get_model('proxy', 'AIModel')
    
    # default models mapping
    default_models = [
        {
            "name": "qwen3.5:2b",
            "agent_url": "http://agent-qwen-2b:8001/agent/",
            "is_active": True
        },
        {
            "name": "qwen3.5:4b",
            "agent_url": "http://agent-qwen-4b:8002/agent/",
            "is_active": True
        },
        {
            "name": "llama3.2:3b",
            "agent_url": "http://agent-llama-3b:8003/agent/",
            "is_active": True
        },
        {
            "name": "llama3.2:1b-instruct-q5_K_M",
            "agent_url": "http://agent-llama-1b:8004/agent/",
            "is_active": True
        }
    ]

    for model_data in default_models:
        AIModel.objects.update_or_create(
            name=model_data["name"],
            defaults={
                "agent_url": model_data["agent_url"],
                "is_active": model_data["is_active"]
            }
        )

# rollback function
def reverse_seed_default_models(apps, schema_editor):
    AIModel = apps.get_model('proxy', 'AIModel')
    AIModel.objects.all().delete()


# tells django that this is a migration that needs to be executed after step 2
class Migration(migrations.Migration):

    dependencies = [
        ('proxy', '0002_aimodel'),
    ]

    operations = [
        migrations.RunPython(seed_default_models, reverse_code=reverse_seed_default_models),
    ]
