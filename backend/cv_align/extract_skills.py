import sys
import json
import re
from kg_manager import G, embeddings

def extract_skills_from_text(text):
    text = text.lower()
    found_skills = set()
    # Iterate over all skill nodes in the KG
    for node in G.nodes:
        if G.nodes[node].get('type') == 'skill':
            skill_name = node.replace('skill_', '').lower()
            # Simple keyword match (can be improved with NLP)
            if re.search(r'\b' + re.escape(skill_name) + r'\b', text):
                found_skills.add(skill_name)
    return list(found_skills)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No text provided"}))
        sys.exit(1)
    input_text = sys.argv[1]
    skills = extract_skills_from_text(input_text)
    print(json.dumps({"skills": skills}))
