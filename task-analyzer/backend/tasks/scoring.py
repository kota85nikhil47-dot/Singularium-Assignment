from datetime import datetime, date
from typing import List, Dict, Tuple, Any, Optional
import math

def parse_date(d):
    if not d:
        return None
    if isinstance(d, date):
        return d
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None

def detect_cycles(tasks: List[Dict[str, Any]]) -> List[List[str]]:
    # Build adjacency using ids (string)
    id_map = {}
    for t in tasks:
        tid = str(t.get('id', t.get('title')))
        id_map[tid] = [str(x) for x in t.get('dependencies', []) or []]

    visited = {}
    stack = []
    cycles = []

    def dfs(node):
        if visited.get(node) == 1:
            # found cycle
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        if visited.get(node) == 2:
            return
        visited[node] = 1
        stack.append(node)
        for neigh in id_map.get(node, []):
            if neigh not in id_map:
                continue
            dfs(neigh)
        stack.pop()
        visited[node] = 2

    for n in list(id_map.keys()):
        if visited.get(n) is None:
            dfs(n)
    return cycles

def compute_scores(tasks: List[Dict[str, Any]],
                   weights: Optional[Dict[str, float]] = None,
                   today: Optional[date] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    tasks: list of dicts with keys id/title/due_date/estimated_hours/importance/dependencies
    weights: dict with keys urgency, importance, effort, dependencies
    returns: (tasks_with_scores, meta) where meta includes cycles found and normalization params
    """

    if today is None:
        today = date.today()

    default_weights = {'urgency': 0.35, 'importance': 0.35, 'effort': 0.15, 'dependencies': 0.15}
    w = default_weights.copy()
    if weights:
        for k in default_weights:
            if k in weights:
                try:
                    v = float(weights[k])
                    w[k] = v
                except Exception:
                    pass
    # Normalize weights to sum 1
    total_w = sum(w.values())
    if total_w == 0:
        total_w = 1.0
    for k in w:
        w[k] = w[k] / total_w

    # Prepare values
    processed = []
    last_date = None
    min_hours, max_hours = math.inf, -math.inf
    min_importance, max_importance = math.inf, -math.inf
    days_to_due_list = []
    for t in tasks:
        tid = str(t.get('id', t.get('title')))
        due = parse_date(t.get('due_date'))
        est = float(t.get('estimated_hours') or 1.0)
        imp = int(t.get('importance') or 5)
        deps = [str(x) for x in (t.get('dependencies') or [])]
        processed.append({'raw': t, 'id': tid, 'due': due, 'est': est, 'imp': imp, 'deps': deps})
        if est < min_hours: min_hours = est
        if est > max_hours: max_hours = est
        if imp < min_importance: min_importance = imp
        if imp > max_importance: max_importance = imp
        if due:
            days = (due - today).days
            days_to_due_list.append(days)
    # urgency normalization: smaller days -> higher urgency; past due negative days -> heavy urgency
    # To avoid division issues if no due dates, use fallback values
    # compute range for effort and importance
    if min_hours == math.inf:
        min_hours, max_hours = 1.0, 1.0
    if min_importance == math.inf:
        min_importance, max_importance = 1, 10

    # compute score components
    id_to_task = {p['id']: p for p in processed}

    # dependencies influence: count how many tasks depend on this one
    dependents = {p['id']: 0 for p in processed}
    for p in processed:
        for d in p['deps']:
            if d in dependents:
                dependents[d] += 1

    # detect cycles
    cycles = detect_cycles([p['raw'] for p in processed])

    scored = []
    # For urgency scaling, map days to a score: if due is None => mid urgency 0.5
    # urgency_raw = clamp(1 - (days / horizon), 0, 1) ; horizon set from data or default 30
    if days_to_due_list:
        min_days = min(days_to_due_list)
        max_days = max(days_to_due_list)
        # set horizon to max absolute days or default 30
        horizon = max(abs(min_days), abs(max_days), 7, 30)
    else:
        horizon = 30

    def clamp(v, a=0.0, b=1.0):
        return max(a, min(b, v))

    for p in processed:
        # urgency
        if p['due'] is None:
            urgency = 0.5
            days = None
        else:
            days = (p['due'] - today).days
            # past due get urgent boost
            if days < 0:
                # convert negative to urgency > 1
                urgency = clamp(1.0 + min(abs(days) / 7.0, 1.0))  # max 2.0 before clamp
                urgency = clamp(urgency, 0.0, 1.5)
            else:
                urgency = 1.0 - (days / horizon)
                urgency = clamp(urgency, 0.0, 1.0)
        # importance normalized 0..1
        if max_importance == min_importance:
            importance_norm = 0.5
        else:
            importance_norm = (p['imp'] - min_importance) / (max_importance - min_importance)
        # effort: prefer lower effort -> higher score. invert and normalize.
        if max_hours == min_hours:
            effort_norm = 0.5
        else:
            # lower estimated_hours => higher quick-win score
            effort_norm = 1.0 - ((p['est'] - min_hours) / (max_hours - min_hours))
            effort_norm = clamp(effort_norm, 0.0, 1.0)
        # dependencies: more dependents => higher score
        deps_count = dependents.get(p['id'], 0)
        # normalize dependents by max dependents
        max_dep = max(dependents.values()) if dependents else 0
        deps_norm = (deps_count / max_dep) if max_dep > 0 else 0.0

        # Weighted sum
        raw_score = (w['urgency'] * urgency) + (w['importance'] * importance_norm) + (w['effort'] * effort_norm) + (w['dependencies'] * deps_norm)

        # Some heuristic: boost tasks that are past due or block many tasks
        bonus = 0.0
        if days is not None and days < 0:
            # Past due: add relative bonus proportional to days overdue (capped)
            bonus += min(abs(days) / 30.0, 0.2)  # up to +0.2
        if deps_count > 0:
            bonus += min(deps_count * 0.02, 0.1)  # small boost per dependent

        score = clamp(raw_score + bonus, 0.0, 1.0)

        # Build explanation
        expl = []
        expl.append(f"urgency={urgency:.2f}")
        expl.append(f"importance={importance_norm:.2f}")
        expl.append(f"effort_quickwin={effort_norm:.2f}")
        expl.append(f"dependencies_impact={deps_norm:.2f}")
        if days is not None:
            expl.append(f"due_in={days}d")
        else:
            expl.append("no_due_date")
        explanation = "; ".join(expl)

        scored.append({
            'id': p['id'],
            'title': p['raw'].get('title'),
            'raw': p['raw'],
            'score': round(score, 4),
            'details': {
                'urgency': round(urgency, 4) if isinstance(urgency, (int,float)) else urgency,
                'importance_norm': round(importance_norm,4),
                'effort_score': round(effort_norm,4),
                'dependencies_norm': round(deps_norm,4),
                'dependents': deps_count,
                'days_to_due': days
            },
            'explanation': explanation
        })

    # sort descending by score
    scored_sorted = sorted(scored, key=lambda x: x['score'], reverse=True)
    meta = {'weights': w, 'cycles': cycles, 'horizon_days': horizon}
    return scored_sorted, meta
