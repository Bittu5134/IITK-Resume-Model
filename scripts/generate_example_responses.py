"""Script to evaluate all example resumes and generate model JSON response txt files in example_responses/."""
from __future__ import annotations

import json
from pathlib import Path
from resume_engine.pipeline import ResumeEngine
from resume_engine.api.app import VALID_ROLES

def generate_responses_for_all_examples(output_dir: str | Path = "example_responses"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    engine = ResumeEngine()
    
    # Collect all sample PDF files from temp/ and examples/
    pdf_sources = []
    temp_dir = Path("temp")
    if temp_dir.exists():
        pdf_sources.extend(sorted(temp_dir.glob("*.pdf")))
    
    examples_dir = Path("examples")
    if examples_dir.exists():
        pdf_sources.extend(sorted(examples_dir.glob("*.pdf")))

    print(f"Found {len(pdf_sources)} example PDF resumes.")

    saved_files = []
    for pdf_file in pdf_sources:
        print(f"Processing: {pdf_file.name}...")
        results = {}
        best_role = "sde"
        max_score = -1.0

        for role_id in sorted(VALID_ROLES):
            res = engine.analyze(pdf_file, role_id)
            dump = res.model_dump()
            results[role_id] = dump
            score_val = dump.get("score", {}).get("score", 0.0)
            if score_val > max_score:
                max_score = score_val
                best_role = role_id

        results["best_fit_role"] = best_role

        # Format clean txt output
        stem = pdf_file.stem
        # Clean stem for readability if needed
        txt_filename = f"{stem}_response.txt"
        txt_path = out_path / txt_filename

        with open(txt_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"  -> Saved model JSON response to: {txt_path}")
        saved_files.append(txt_path)

    return saved_files


if __name__ == "__main__":
    generate_responses_for_all_examples()
