from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import TaskSerializer
from .scoring import compute_scores, detect_cycles
from datetime import date

@api_view(['POST'])
def analyze_tasks(request):
    """
    POST /api/tasks/analyze/
    body: { "tasks": [...], "weights": {"urgency":0.3,...} }
    Returns tasks sorted with score and explanation.
    """
    payload = request.data
    tasks = payload.get('tasks') or payload.get('data') or []
    weights = payload.get('weights', None)
    # Validate tasks via serializer (allow partial)
    serialized = []
    errors = []
    for idx, t in enumerate(tasks):
        s = TaskSerializer(data=t)
        if not s.is_valid():
            errors.append({'index': idx, 'errors': s.errors})
        else:
            serialized.append(s.validated_data)
    if errors:
        return Response({'error': 'invalid_tasks', 'details': errors}, status=status.HTTP_400_BAD_REQUEST)

    scored, meta = compute_scores(serialized, weights=weights, today=date.today())
    return Response({'tasks': scored, 'meta': meta})

@api_view(['GET'])
def suggest_tasks(request):
    """
    GET /api/tasks/suggest/?strategy=smart&top=3
    Accepts tasks via query param 'tasks' (json encoded) OR for convenience expects a POST-like JSON body.
    For this demo we'll accept tasks in request body if present (GET with body is allowed here for convenience),
    otherwise return 400 if no tasks provided.
    """
    # Allow JSON body on GET for convenience (or in production use POST)
    if request.method == 'GET' and request.data:
        tasks = request.data.get('tasks', [])
        weights = request.data.get('weights', None)
        strategy = request.data.get('strategy', request.query_params.get('strategy', 'smart'))
    else:
        # try query param 'tasks' (URL-encoded JSON)
        tasks = request.query_params.get('tasks')
        if tasks:
            import json
            try:
                tasks = json.loads(tasks)
            except Exception:
                return Response({'error': 'invalid tasks JSON in query param'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'no_tasks_provided'}, status=status.HTTP_400_BAD_REQUEST)
        weights = None
        strategy = request.query_params.get('strategy', 'smart')

    # Validate
    serialized = []
    errors = []
    for idx, t in enumerate(tasks):
        s = TaskSerializer(data=t)
        if not s.is_valid():
            errors.append({'index': idx, 'errors': s.errors})
        else:
            serialized.append(s.validated_data)
    if errors:
        return Response({'error': 'invalid_tasks', 'details': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Strategy switch
    strategy = strategy.lower()
    if strategy == 'fastest':
        weights = {'urgency': 0.2, 'importance': 0.2, 'effort': 0.6, 'dependencies': 0.0}
    elif strategy == 'highimpact':
        weights = {'urgency': 0.2, 'importance': 0.7, 'effort': 0.05, 'dependencies': 0.05}
    elif strategy == 'deadline':
        weights = {'urgency': 0.8, 'importance': 0.1, 'effort': 0.05, 'dependencies': 0.05}
    else:
        # smart balance default
        weights = weights or {'urgency': 0.35, 'importance': 0.35, 'effort': 0.15, 'dependencies': 0.15}

    scored, meta = compute_scores(serialized, weights=weights)
    # top N
    try:
        top = int(request.query_params.get('top', 3))
    except:
        top = 3
    top_tasks = scored[:top]
    # Add short human explanation for each choice
    for t in top_tasks:
        reasons = []
        d = t['details']
        if d['days_to_due'] is not None and d['days_to_due'] <= 0:
            reasons.append('Past-due or due today')
        if d['dependents'] > 0:
            reasons.append(f'Blocks {d["dependents"]} other task(s)')
        if d['importance_norm'] >= 0.75:
            reasons.append('High importance')
        if d['effort_score'] >= 0.75:
            reasons.append('Quick win (low effort)')
        if not reasons:
            reasons.append('Balanced priority based on score')
        t['suggestion_reason'] = '; '.join(reasons)
    return Response({'suggestions': top_tasks, 'meta': meta})
