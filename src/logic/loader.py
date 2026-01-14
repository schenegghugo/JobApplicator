import yaml
import os
from src.models.user_profile import Identity
from src.models.strategy import Strategy

def load_profile(profile_name: str):
    base_path = f"config/profiles/{profile_name}"
    
    # Load Identity
    with open(f"{base_path}/identity.yaml", "r", encoding="utf-8") as f:
        identity_data = yaml.safe_load(f)
    identity = Identity(**identity_data)

    # Load Strategy
    with open(f"{base_path}/strategy.yaml", "r", encoding="utf-8") as f:
        strategy_data = yaml.safe_load(f)
    strategy = Strategy(**strategy_data)

    return identity, strategy
