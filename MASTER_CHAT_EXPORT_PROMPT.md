# 9REALMS MASTER CHAT EXPORT PROMPT
## Paste this into any Claude chat to export its contents to the master file

---

**COPY EVERYTHING BELOW THIS LINE AND PASTE INTO OTHER CHATS:**

---

I need you to export the entire contents of this chat into a master research file on my local machine. Here's exactly what to do:

## INSTRUCTIONS

1. **Read the existing master file** at this path on my computer (use Filesystem tools):
   `C:\Users\dcmoo\Documents\Python\9realms\CHAT_MIGRATION_2026-05-05_AACR_RESEARCH.md`

2. **APPEND (do not overwrite)** a new section to the bottom of that file with ALL content from this chat session. Use the Filesystem:write_file tool, but first read the existing file content, then write back the original content PLUS the new section appended.

3. **Format the new section as follows:**

```
---

## CHAT EXPORT: [Brief title describing this chat's topic]
### Exported: [today's date and time]
### Source Chat: [paste the chat URL if visible, otherwise "Claude Project Chat"]
### Topic Summary: [1-2 sentence summary of what was discussed]

### KEY FINDINGS:
[Bullet points of every important finding, data point, decision, or conclusion from this chat]

### RAW CONTENT:
[Complete summary of the entire conversation — every question I asked, every answer you gave, every tool call result, every search result, every file created. Be exhaustive. Include specific numbers, tickers, dates, URLs, and code snippets.]

### FILES CREATED/MODIFIED:
[List every file that was created, modified, or referenced in this chat with full paths]

### ACTION ITEMS:
[Any TODO items, next steps, or unfinished work from this chat]

### SEARCH RESULTS:
[Summarize all web searches, MCP queries, and tool calls with their key results]
```

4. **IMPORTANT RULES:**
   - Do NOT truncate or summarize — capture EVERYTHING
   - Include all specific numbers (stock prices, market caps, dates, percentages)
   - Include all ticker symbols mentioned
   - Include all URLs found in searches
   - Include code snippets if any were written
   - If the file is too large for a single write, split into multiple appends
   - The master file path is: `C:\Users\dcmoo\Documents\Python\9realms\CHAT_MIGRATION_2026-05-05_AACR_RESEARCH.md`

5. **After writing**, confirm what you appended and the new file size.

This is for my ODIN/9realms biotech trading research system. The master file aggregates research across all my Claude chat sessions. Do this now — read the existing file, append this chat's contents, write it back.
