# Codex capacity recovery watcher

This watcher polls the current rollout every three minutes. It is silent unless
the structured terminal error message is exactly:

`Selected model is at capacity. Please try a different model.`

On that event it queues one continuation message to thread
`01a02ee2-3a25-7c03-aa70-5ad81bdfb765`. User text, assistant commentary, tool
inputs, historical events, and a task that has already restarted cannot trigger
it. A lock prevents overlapping cron invocations.

The installed crontab block is bounded by the marker `codex capacity recovery`.
Remove that block when the user says to stop.
