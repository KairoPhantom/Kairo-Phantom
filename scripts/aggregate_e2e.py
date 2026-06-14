import json
import os

def get_tier(app):
    app_lower = app.lower()
    if app_lower in ["word", "excel", "powerpoint", "notepad"]:
        return "Tier 1 (Desktop)"
    elif app_lower in ["browser", "chrome"]:
        return "Tier 2 (Web)"
    else:
        return "Other"

def main():
    if not os.path.exists("report.json"):
        print("report.json not found")
        return

    with open("report.json", "r") as f:
        data = json.load(f)

    groups = data.get("groups", [])
    flat_results = []
    for g in groups:
        if isinstance(g, list):
            flat_results.extend(g)
        else:
            flat_results.append(g)

    app_stats = {}
    tier_stats = {}
    total = 0
    passed = 0

    for res in flat_results:
        app = res.get("app", "Unknown")
        status = res.get("status", "FAILED")
        is_passed = (status == "PASSED")
        
        tier = get_tier(app)
        
        # App stats
        if app not in app_stats:
            app_stats[app] = {"total": 0, "passed": 0}
        app_stats[app]["total"] += 1
        if is_passed:
            app_stats[app]["passed"] += 1

        # Tier stats
        if tier not in tier_stats:
            tier_stats[tier] = {"total": 0, "passed": 0}
        tier_stats[tier]["total"] += 1
        if is_passed:
            tier_stats[tier]["passed"] += 1

        # Overall
        total += 1
        if is_passed:
            passed += 1

    report = {
        "overall": {
            "total": total,
            "passed": passed,
            "rate": passed / total if total > 0 else 0.0
        },
        "by_application": {
            app: {
                "total": stats["total"],
                "passed": stats["passed"],
                "rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            }
            for app, stats in app_stats.items()
        },
        "by_tier": {
            tier: {
                "total": stats["total"],
                "passed": stats["passed"],
                "rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            }
            for tier, stats in tier_stats.items()
        }
    }

    with open("task_completion_rate.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Task completion rate report generated: task_completion_rate.json")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
