# Project Status

## Roadmap

### Short-Term
- Polish admin publishing flow and add audit logging for catalog changes.
- Improve chatbot UX with streaming progress indicator and conversational presets.
- Expand automated image handling (thumbnails, compression) during uploads.

### Long-Term
- Integrate live analytics dashboard to visualize clicks, searches, and user engagement.
- Add localization support for multi-language showcases.
- Build CI/CD pipeline for automated deployments to preferred static hosts.

### Known Issues
- Chatbot depends on a working Cortensor router; proxy configuration may need manual tweaks across environments.
- RAG index must be regenerated manually when docs change; automate the crawler in future iterations.