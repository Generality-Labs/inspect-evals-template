"""MMLU subject -> broad-category mapping.

Embedded from the official MMLU repo (``hendrycks/test/categories.py``): the
``subcategories`` mapping (subject -> fine-grained domain) and the four broad
``categories``. The mapping is stable across MMLU releases, so it is embedded
here rather than fetched at runtime. Broad-category display names follow the
TEE data spec (STEM / Humanities / Social Sciences / Other).
"""

from __future__ import annotations

SUBCATEGORIES: dict[str, str] = {
    "abstract_algebra": "math",
    "anatomy": "health",
    "astronomy": "physics",
    "business_ethics": "business",
    "clinical_knowledge": "health",
    "college_biology": "biology",
    "college_chemistry": "chemistry",
    "college_computer_science": "computer science",
    "college_mathematics": "math",
    "college_medicine": "health",
    "college_physics": "physics",
    "computer_security": "computer science",
    "conceptual_physics": "physics",
    "econometrics": "economics",
    "electrical_engineering": "engineering",
    "elementary_mathematics": "math",
    "formal_logic": "philosophy",
    "global_facts": "other",
    "high_school_biology": "biology",
    "high_school_chemistry": "chemistry",
    "high_school_computer_science": "computer science",
    "high_school_european_history": "history",
    "high_school_geography": "geography",
    "high_school_government_and_politics": "politics",
    "high_school_macroeconomics": "economics",
    "high_school_mathematics": "math",
    "high_school_microeconomics": "economics",
    "high_school_physics": "physics",
    "high_school_psychology": "psychology",
    "high_school_statistics": "math",
    "high_school_us_history": "history",
    "high_school_world_history": "history",
    "human_aging": "health",
    "human_sexuality": "culture",
    "international_law": "law",
    "jurisprudence": "law",
    "logical_fallacies": "philosophy",
    "machine_learning": "computer science",
    "management": "business",
    "marketing": "business",
    "medical_genetics": "health",
    "miscellaneous": "other",
    "moral_disputes": "philosophy",
    "moral_scenarios": "philosophy",
    "nutrition": "health",
    "philosophy": "philosophy",
    "prehistory": "history",
    "professional_accounting": "other",
    "professional_law": "law",
    "professional_medicine": "health",
    "professional_psychology": "psychology",
    "public_relations": "politics",
    "security_studies": "politics",
    "sociology": "culture",
    "us_foreign_policy": "politics",
    "virology": "health",
    "world_religions": "philosophy",
}

_SUBCATEGORY_TO_CATEGORY: dict[str, str] = {
    "physics": "STEM",
    "chemistry": "STEM",
    "biology": "STEM",
    "computer science": "STEM",
    "math": "STEM",
    "engineering": "STEM",
    "history": "Humanities",
    "philosophy": "Humanities",
    "law": "Humanities",
    "politics": "Social Sciences",
    "culture": "Social Sciences",
    "economics": "Social Sciences",
    "geography": "Social Sciences",
    "psychology": "Social Sciences",
    "other": "Other",
    "business": "Other",
    "health": "Other",
}

SUBJECT_TO_CATEGORY: dict[str, str] = {
    subject: _SUBCATEGORY_TO_CATEGORY[subcategory]
    for subject, subcategory in SUBCATEGORIES.items()
}

# Default 8 subjects (2 per broad category), chosen to avoid high
# ground-truth-error subjects (Gema et al. 2024) and US-centric framing that
# would confound the EN/FR contrast. Order matters: within a category the
# first-listed subject receives the larger share when a per-category quota does
# not divide evenly.
DEFAULT_SUBJECTS_BY_CATEGORY: dict[str, list[str]] = {
    "STEM": ["high_school_mathematics", "college_computer_science"],
    "Humanities": ["world_religions", "philosophy"],
    "Social Sciences": ["sociology", "high_school_macroeconomics"],
    "Other": ["marketing", "nutrition"],
}

DEFAULT_SUBJECTS: list[str] = [
    subject
    for subjects in DEFAULT_SUBJECTS_BY_CATEGORY.values()
    for subject in subjects
]

# French names for the default study subjects, so French prompts read naturally.
# Subjects outside this map fall back to the de-underscored slug at render time.
FR_SUBJECT_NAMES: dict[str, str] = {
    "high_school_mathematics": "les mathématiques de niveau lycée",
    "college_computer_science": "l'informatique de niveau universitaire",
    "world_religions": "les religions du monde",
    "philosophy": "la philosophie",
    "sociology": "la sociologie",
    "high_school_macroeconomics": "la macroéconomie de niveau lycée",
    "marketing": "le marketing",
    "nutrition": "la nutrition",
}
