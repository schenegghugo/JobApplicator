# src/utils/paths.py
import os

BASE_DIR = os.getcwd()

def get_profile_paths(profile_name):
    """
    Returns a dictionary of paths specific to the user profile.
    """
    return {
        # Configs
        "profile_dir": os.path.join(BASE_DIR, "config", "profiles", profile_name),
        "targets_file": os.path.join(BASE_DIR, "config", "profiles", profile_name, "targets.yaml"),
        "identity_file": os.path.join(BASE_DIR, "config", "profiles", profile_name, "identity.yaml"),
        "strategy_file": os.path.join(BASE_DIR, "config", "profiles", profile_name, "strategy.yaml"),
        
        # Data
        "db_file": os.path.join(BASE_DIR, "data", "db", f"{profile_name}.db"),
        "raw_html_dir": os.path.join(BASE_DIR, "data", "raw_jobs", profile_name),
        "output_dir": os.path.join(BASE_DIR, "data", "applications", profile_name),
    }

def ensure_dirs(paths):
    """Creates necessary directories if they don't exist."""
    os.makedirs(os.path.dirname(paths["db_file"]), exist_ok=True)
    os.makedirs(paths["raw_html_dir"], exist_ok=True)
    os.makedirs(paths["output_dir"], exist_ok=True)
