const API_BASE = ''; // empty means same origin. If backend served on different port, set e.g. 'http://localhost:8000'
const analyzeBtn = document.getElementById('analyzeBtn');
const suggestBtn = document.getElementById('suggestBtn');
const tasksInput = document.getElementById('tasksInput');
const results = document.getElementById('results');
const errorBox = document.getElementById('error');
const strategySelect = document.getElementById('strategy');

function showError(msg){
  errorBox.textContent = msg;
  setTimeout(()=> errorBox.textContent = '', 5000);
}

function renderTasks(tasks){
  results.innerHTML = '';
  if(!tasks || tasks.length===0){
    results.textContent = 'No tasks to show.';
    return;
  }
  tasks.forEach(t => {
    const div = document.createElement('div');
    div.className = 'task-card';
    const score = t.score ?? t.score;
    let pri = 'priority-low';
    if(score >= 0.75) pri='priority-high';
    else if(score >= 0.45) pri='priority-medium';
    div.classList.add(pri);
    div.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><strong>${t.title || t.raw?.title || t.id}</strong><div class="small">${t.raw?.due_date ? 'Due: '+t.raw.due_date : 'No due date'}</div></div>
        <div><strong>${(t.score*100).toFixed(0)}%</strong></div>
      </div>
      <div class="explanation">${t.explanation || t.suggestion_reason || ''}</div>
      <div class="small">Details: importance ${t.details?.importance_norm}, effort ${t.details?.effort_score}, dependents ${t.details?.dependents}</div>
    `;
    results.appendChild(div);
  });
}

analyzeBtn.addEventListener('click', async ()=>{
  let raw = tasksInput.value.trim();
  if(!raw){
    showError('Paste tasks JSON into the textarea.');
    return;
  }
  let tasks;
  try {
    tasks = JSON.parse(raw);
    if(!Array.isArray(tasks)){
      showError('JSON must be an array of tasks.');
      return;
    }
  } catch(e){
    showError('Invalid JSON: ' + e.message);
    return;
  }

  const payload = { tasks };
  try {
    const resp = await fetch(API_BASE + '/api/tasks/analyze/', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if(!resp.ok) {
      showError(data.error || 'API Error');
      return;
    }
    renderTasks(data.tasks);
  } catch (err){
    showError('Network error: ' + err.message);
  }
});

suggestBtn.addEventListener('click', async ()=>{
  let raw = tasksInput.value.trim();
  if(!raw){
    showError('Paste tasks JSON into the textarea.');
    return;
  }
  let tasks;
  try {
    tasks = JSON.parse(raw);
    if(!Array.isArray(tasks)){
      showError('JSON must be an array of tasks.');
      return;
    }
  } catch(e){
    showError('Invalid JSON: ' + e.message);
    return;
  }
  const strategy = strategySelect.value;
  try {
    const resp = await fetch(API_BASE + '/api/tasks/suggest/', {
      method: 'GET',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tasks, strategy})
    });
    const data = await resp.json();
    if(!resp.ok) {
      showError(data.error || 'API Error');
      return;
    }
    // suggestions is array
    if(data.suggestions) renderTasks(data.suggestions);
    else showError('No suggestions returned');
  } catch (err){
    showError('Network error: ' + err.message);
  }
});
