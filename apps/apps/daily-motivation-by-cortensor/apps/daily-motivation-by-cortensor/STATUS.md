🟢 Current Status  
**Version:** 1.0.0  
**Status:** Active  
**Description:**  
The project is stable and under active development. Core features—daily motivational messages, mood-based prompt handling, and timezone-aware scheduling—are functional. Work is ongoing to improve response variation, error handling, and scalability.

---

🗺️ Roadmap  
Here is a high-level overview of our planned features and improvements, organized by upcoming versions.

### v1.1.0 — Stability & Engagement Update
- **Randomized Output Handling:** Improve variation in Cortensor API prompts to reduce repeated responses.
- **Error Messaging:** Provide more user-friendly feedback if Cortensor API fails or times out.
- **User Feedback Collection:** Let users rate or react to motivation received.

### v1.2.0 — Interaction Expansion
- **Motivational Theme Selection:** Allow users to choose tone (e.g., cheerful, serious, sarcastic).
- **Mood History:** Store previous moods to provide more personalized quotes over time.
- **Silent Mode:** Add `/dailyon` and `/dailyoff` commands to manage daily message preference.

### v2.0.0 — Scalability and Personalization
- **Database Integration:** Persist user preferences, moods, and history across sessions.
- **Multi-language Support:** Let users receive motivational quotes in Bahasa Indonesia or English.
- **Admin Dashboard:** View user stats, active sessions, and quote popularity.

---

🐛 Known Issues  

**Output Repetition**  
- **Description:** On similar prompts, the Cortensor API occasionally returns identical or near-identical quotes.  
- **Impact:** Users may receive duplicate motivation messages.  
- **Priority:** Medium – being addressed with randomized prompt templates in v1.1.0.

**No Persistent Storage**  
- **Description:** User mood and timezone data are stored in memory only.  
- **Impact:** All user data resets on bot restart.  
- **Priority:** Medium – planned to be fixed with DB support in v2.0.0.
