from typing import List, Dict
from src.models.strategy import Strategy

def process_hooks(job_description: str, strategy: Strategy) -> Dict[str, List[str]]:
    """
    Returns a dictionary of injections, e.g.:
    {
      "bio": ["Has driver's license"],
      "skills": ["SAP Expert"]
    }
    """
    job_lower = job_description.lower()
    injections = {
        "bio": [],
        "skills": [],
        "experience": [],
        "cover_letter": []
    }

    for hook in strategy.hooks:
        # Check if ANY trigger word exists in the job description
        if any(trigger.lower() in job_lower for trigger in hook.triggers):
            injections[hook.inject_into].append(hook.content)
            print(f"   🪝 Hook Triggered: {hook.name}")

    return injections
