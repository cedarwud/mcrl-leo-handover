# How to run the two Astra Pro reviews

Use two independent fresh chats so the second review is not anchored by the first.

## Chat 1 — ordinary Q&A

1. Upload the final ZIP.
2. Select Astra Pro with its strongest available reasoning setting.
3. Paste the complete contents of `CHATGPT-ASTRA-PRO-QA-PROMPT.md`.
4. Save the complete answer as `ASTRA-PRO-QA-REPLY.md`.

This chat is package-only. Do not enable Deep Research or give it conclusions from the current Codex/Claude sessions.

## Chat 2 — Deep Research

1. Start a separate fresh chat and upload the same ZIP.
2. Select Astra Pro and enable Deep Research.
3. Paste the complete contents of `CHATGPT-ASTRA-PRO-DEEP-RESEARCH-PROMPT.md`.
4. Save the complete answer, with live source links intact, as `ASTRA-PRO-DEEP-RESEARCH-REPLY.md`.

Return both files together. Do not summarize them first; the controller needs the exact wording, citations, discrepancies, and final decision tokens. Do not paste the answer from Chat 1 into Chat 2: their independence is part of the review design.
