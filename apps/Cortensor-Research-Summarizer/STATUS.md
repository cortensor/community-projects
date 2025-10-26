## Roadmap

### Short-Term
- Stabilize Cortensor summarization calls for long multi-source inputs.
- Ship mobile-responsive history panel with diff-friendly layout.
- Land rate-limit integration tests for `api/summarize` endpoint.

### Long-Term
- Introduce researcher workspaces with shareable summary bundles.
- Add pluggable retrievers for private knowledge base ingestion.
- Automate quality scoring pipeline with human-in-the-loop review hooks.

### Known Issues
- Citation validator can lag on corpora above 40k tokens; progress UI flickers.
- History panel occasionally reorders entries when local storage is cleared.
- Summaries time out if URL pre-fetch hits more than three slow domains.
