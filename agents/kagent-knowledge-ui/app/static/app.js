const messages = document.querySelector("#messages");
const form = document.querySelector("#query-form");
const input = document.querySelector("#question");
const refresh = document.querySelector("#refresh");

function addMessage(text, type, data) {
  const node = document.createElement("article");
  node.className = `message ${type}`;
  if (data && data.fallback) {
    node.classList.add("fallback");
  }
  node.textContent = text;

  if (data && data.sources && data.sources.length) {
    const sources = document.createElement("div");
    sources.className = "sources";
    data.sources.forEach((source) => {
      const link = document.createElement("a");
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `${source.path} - ${source.heading}`;
      sources.appendChild(link);
    });
    node.appendChild(sources);
  }

  if (data) {
    const actions = document.createElement("div");
    actions.className = "actions";

    const ticket = document.createElement("a");
    ticket.href = data.ticket_url;
    ticket.target = "_blank";
    ticket.rel = "noopener noreferrer";
    const ticketButton = document.createElement("button");
    ticketButton.type = "button";
    ticketButton.className = "secondary";
    ticketButton.textContent = "Raise ticket";
    ticket.appendChild(ticketButton);
    actions.appendChild(ticket);

    if (!data.fallback) {
      const stale = document.createElement("button");
      stale.type = "button";
      stale.className = "secondary";
      stale.textContent = "Wrong or outdated";
      stale.addEventListener("click", () => reportStale(data));
      actions.appendChild(stale);
    }
    node.appendChild(actions);
  }

  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

async function reportStale(data) {
  const sourcePath = data.sources && data.sources[0] ? data.sources[0].path : "";
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: data.question,
      source_path: sourcePath,
      reason: "User marked this K-Agent answer as wrong or outdated.",
      simulate: false
    })
  });
  const result = await response.json();
  addMessage(`Knowledge update PR: ${result.pr_url}`, "agent");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  addMessage(question, "user");

  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  const data = await response.json();
  addMessage(data.answer, "agent", data);
});

refresh.addEventListener("click", async () => {
  const response = await fetch("/api/refresh", { method: "POST" });
  const data = await response.json();
  addMessage(`Knowledge index refreshed. ${data.chunks} chunks indexed.`, "agent");
});

addMessage("Ask an AKS platform question to start.", "agent");

