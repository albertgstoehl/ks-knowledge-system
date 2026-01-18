// Start workout - called from idle state
async function startWorkout() {
  const templateKey = prompt('Workout template (e.g., Push, Pull, Legs):', 'Push');
  if (!templateKey) return;

  await fetch(`${basePath}/api/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      template_key: templateKey
    })
  });

  window.location.reload();
}
