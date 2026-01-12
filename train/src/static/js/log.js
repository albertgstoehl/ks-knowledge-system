const form = document.getElementById("set-form");
const list = document.getElementById("sets");

// Get base path from current URL
const basePath = window.location.pathname.split("/log")[0];

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = {
    session_id: 1, // TODO: get from active session
    exercise_name: data.get("exercise"),
    weight: Number(data.get("weight")),
    reps: Number(data.get("reps")),
    rir: data.get("rir") ? Number(data.get("rir")) : null,
  };
  const response = await fetch(basePath + "/api/sets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const set = await response.json();
  const item = document.createElement("div");
  item.className = "set-entry";
  item.textContent = `${set.exercise_name} ${set.weight}kg x ${set.reps} (RIR ${set.rir ?? "-"})`;
  list.prepend(item);
  form.reset();
});
