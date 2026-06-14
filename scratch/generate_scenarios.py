import json
import os

def generate_scenarios():
    categories = [
        "Word", "Excel", "PPT", "Legal", "CUA", 
        "Security", "Memory", "Offline", "Degradation", "Performance"
    ]
    
    scenarios = []
    
    # Generate 20 scenarios per category to reach exactly 200 scenarios
    for cat in categories:
        for i in range(1, 21):
            scen_id = f"{cat.upper()}_{i:03d}"
            
            # First 5 of each category are marked "active", others "pending" or "excluded"
            if i <= 5:
                status = "active"
            elif i <= 15:
                status = "pending"
            else:
                status = "excluded"
                
            prompt = f"Run validation for {cat} scenario {i:02d}: testing specialized criteria."
            description = f"Scaffolded test case for {cat} domain. Verifies domain-specific handling of release gates."
            
            scenarios.append({
                "id": scen_id,
                "category": cat,
                "name": f"{cat} Scenario {i:02d}",
                "description": description,
                "prompt": prompt,
                "status": status,
                "fix_budget": 3 if status == "active" else 0
            })
            
    target_file = os.path.join(os.path.dirname(__file__), "..", "scenarios.json")
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)
        
    print(f"Generated {len(scenarios)} scenarios in {target_file}")

if __name__ == "__main__":
    generate_scenarios()
