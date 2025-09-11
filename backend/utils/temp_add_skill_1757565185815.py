
import sys
import os
sys.path.append('C:\Users\Ashok\My_Intern\CVALIGN\CV_Align')

try:
    from kg_manager import add_node_with_neighbors
    
    # Add the skill node
    neighbors = []
    
    # Add related skills
    for skill in []:
        neighbors.append(f"skill_{skill}")
    
    # Add related jobs
    for job in ["68c19da979172b669f864356"]:
        neighbors.append(f"job_{job}")
    
    # Add the skill to the knowledge graph
    success = add_node_with_neighbors(f"skill_{skillName}", "skill", neighbors)
    
    if success:
        print("SUCCESS: Skill added to knowledge graph")
        sys.exit(0)
    else:
        print("ERROR: Failed to add skill to knowledge graph")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
