# Fact Verifier Extension

A browser extension that verifies facts and news claims using the Cortensor decentralized inference network.  
It checks statements against multiple independent nodes, aggregates results, and returns a consensus-backed verdict with citations.

## Features
- ✅ Consensus-based truth checking (multiple nodes verify claims)
- 📊 Confidence score (% agreement across nodes)
- 🔗 Source citations for transparency
- 🌐 Easy-to-use browser extension (highlight → verify → result)

## How It Uses Cortensor
This project integrates with the **Cortensor Decentralized Inference API**.  
Each verification request is processed by multiple nodes, and their responses are aggregated to ensure reliability and reduce hallucinations.

## Installation (Dev Mode)
1. Clone this repo.
2. Navigate to `apps/fact-verifier-extension/`.
3. Load the extension in Chrome/Brave via `chrome://extensions` → **Load unpacked**.
4. Select the extension folder.

## Roadmap
- [ ] Backend middleware to call Cortensor API
- [ ] Consensus logic (aggregate responses)
- [ ] Browser extension UI
- [ ] Confidence scoring + citations
- [ ] (Optional) On-chain notarization of results
