# AgentAuditor: Decentralized AI Compliance Oracle

> **The Trust Layer for Decentralized AI Agents**  
> A Client-Side Verification Oracle that validates AI task execution through independent PoI/PoUW consensus verification and generates cryptographically signed audit proofs.

[![Cortensor](https://img.shields.io/badge/Built%20on-Cortensor-blue)](https://cortensor.ai)
[![Arbitrum](https://img.shields.io/badge/Deployed%20on-Arbitrum%20Sepolia-orange)](https://sepolia.arbiscan.io)
[![IPFS](https://img.shields.io/badge/Storage-IPFS-green)](https://ipfs.io)

---

Video Demo - https://youtu.be/GhqxvqlBqbM

## 🎯 The Problem: The AI Trust Gap

As decentralized AI scales toward enterprise adoption, three critical barriers emerge:

### 1. **Opaque Execution**
When miners execute AI tasks (like "generate a function to calculate X" or "analyze data Y"), how do external parties verify the work was done correctly and not hallucinated or manipulated?

### 2. **Ephemeral Consensus**
Cortensor validators perform real-time consensus through PoI (embedding similarity checks across 3+ validators) and PoUW (quality scoring by 1 validator across 3 criteria). But once a session closes, this validation signal becomes difficult to audit or present to third parties.

### 3. **Enterprise Compliance Gap**
Organizations need **verifiable receipts** before they can:
- Integrate AI agents into regulated workflows
- Trigger smart contract payments based on AI outputs
- Maintain audit trails for compliance (GDPR, SOX, etc.)
- Build liability frameworks around AI decisions

**Current Reality**: Decentralized AI networks excel at execution and consensus but lack portable proof mechanisms for downstream consumers.

---

## 💡 The Solution: AgentAuditor

AgentAuditor is a **Decentralized AI Oracle** and **Client-Side Verification Layer** that bridges the gap between Cortensor's network consensus and enterprise-grade trust.

### We Ask a Different Question

Traditional oracles ask: *"What is the truth?"* (e.g., "What's the BTC price?")  
**AgentAuditor asks**: *"Did miners execute this AI task correctly according to network consensus?"*

### How It Works

```
User Request → Miners Execute Task → Network Validates (PoI/PoUW) → AgentAuditor Verifies → Proof-of-Audit
```

**The Verification Process:**

1. **Task Execution**: User submits a task (e.g., "Generate Python function to calculate Fibonacci sequence" or "Analyze this dataset for outliers")

2. **Miner Inference**: Multiple miners execute the AI inference task independently

3. **Network Consensus**:
   - **PoI (Proof of Inference)**: 3+ validators check embedding vector similarity between miner outputs using cosine similarity/Euclidean distance (threshold typically 0.85+)
   - **PoUW (Proof of Useful Work)**: 1 validator scores output across 3 criteria: semantic consistency, logical coherence, and practical applicability

4. **Client-Side Verification**: AgentAuditor independently:
   - Retrieves raw outputs and validation scores from all miners/validators
   - Re-computes embedding similarities using local sentence-transformer models
   - Validates that consensus thresholds were actually met
   - Checks for anomalies (single-miner dominance, suspiciously uniform responses)

5. **Evidence Generation**: Bundles everything into a signed, immutable audit artifact

**Output**: A portable, tamper-proof **Proof-of-Audit** certificate—the "receipt" that enterprises need.

---

## 🏗️ Architecture

AgentAuditor operates as a **Layer-2 Application** on Cortensor, adding independent verification and notarization:

```mermaid
graph TD
    User[Enterprise Client / dApp] -->|Submit Audit Task| UI[AgentAuditor Dashboard]
    UI -->|REST API| Backend[FastAPI Orchestrator]
    
    subgraph "AgentAuditor Verification Layer"
        Backend -->|1. Task Submission| Router[Cortensor Router]
        Backend -->|2. Retrieve Raw Data| Router
        Backend -->|3. Independent Verification| Verify[PoI/PoUW Verification Engines]
        Backend -->|4. Evidence Generation| Gen[Evidence Generator]
        Backend -->|5. Audit Storage| DB[(PostgreSQL)]
    end
    
    subgraph "Cortensor Consensus Layer"
        Router -->|Interact via SessionV2| Session[SessionV2 Contract]
        Session -->|Queue Tasks| Queue[SessionQueueV2 Contract]
        Queue -->|Broadcast| Blockchain[Arbitrum Sepolia]
        Blockchain -->|Assign to Miners| Miners[Multiple Miner Nodes]
        Miners -->|Submit Outputs| Validators[PoI/PoUW Validators]
        Validators -->|Consensus Scores| Router
    end
    
    subgraph "Trust Infrastructure"
        Gen -->|Upload Bundle| IPFS[IPFS via Pinata]
        Gen -->|Cryptographic Signing| Wallet[Web3 Wallet]
    end
    
    Router -->|Raw Outputs + Scores| Backend
    Verify -->|Validated ✓| Gen
    
    style Session fill:#4a90e2
    style Queue fill:#4a90e2
    style Router fill:#50c878
    style Validators fill:#e74c3c
```

**Key Insight**: AgentAuditor doesn't deploy custom smart contracts or replace consensus. Instead, it acts as an independent auditor that retrieves, verifies, and notarizes the network's existing validation results using Cortensor's native **SessionV2** and **SessionQueueV2** contracts.

---

## 🔍 Understanding PoI and PoUW in AgentAuditor

### Proof of Inference (PoI) - Consistency Verification

PoI validates that miners used the correct models and produced consistent outputs by measuring embedding vector distance. When miners execute the same task, their outputs should be semantically similar even if syntactically different.

**How AgentAuditor Verifies PoI:**
1. Retrieves outputs from all miners (e.g., 3+ miners)
2. Converts each output to embeddings using sentence-transformers
3. Computes similarity matrix using cosine similarity
4. Validates that similarity scores meet threshold (typically >0.85)
5. Flags outputs that deviate significantly from consensus

**Example**: If 3 miners generate functions for Fibonacci calculation, the embedding vectors should show high cosine similarity even if variable names or syntax differ.

### Proof of Useful Work (PoUW) - Quality Verification

PoUW validates the correctness, usefulness, and semantic quality of outputs using additional LLM models. A validator scores the output across multiple dimensions.

**How AgentAuditor Verifies PoUW:**
1. Retrieves validator scores across 3 criteria:
   - **Semantic Consistency**: Does the output make logical sense?
   - **Logical Coherence**: Is the reasoning sound?
   - **Practical Applicability**: Is the result actually useful?
2. Validates score authenticity and checks for manipulation
3. Records all scoring data in the audit bundle

**Why Independent Verification Matters**: AgentAuditor doesn't blindly trust the Router's reported consensus. It independently re-computes PoI similarities and validates PoUW scores, protecting against:
- Compromised Router nodes
- API manipulation attacks
- False consensus reporting
- Lazy validation

---

## 🚀 Core Features

### 1. **Protocol-Native Integration**

AgentAuditor showcases **production-grade Cortensor integration** by using the protocol's native smart contracts:

**SessionV2 Contract Integration:**
- Manages AI task lifecycle through state machine (Request → Precommit → Commit → End)
- Handles $COR token deposits and payment flows automatically
- Provides cryptographic proofs (TaskRoot per task, SessionRoot for history)
- Configurable accuracy and validation levels for different use cases

**SessionQueueV2 Contract Integration:**
- Decentralized job scheduler for optimal miner assignment
- Manages ephemeral and dedicated miner selection from Node Pool
- Validates task integrity with per-task Merkle roots
- Ensures reliable task distribution across the network

**Why This Approach Wins:**
- ✅ No custom smart contract deployment (reduced attack surface)
- ✅ Automatic compatibility with protocol upgrades
- ✅ Gas-efficient operations using battle-tested code
- ✅ Demonstrates deep understanding of Cortensor architecture

### 2. **Independent Consensus Verification**

AgentAuditor's verification engines provide defense-in-depth:

**PoI Engine:**
- Downloads raw miner outputs from Router/IPFS
- Generates embeddings using local sentence-transformer models
- Computes full similarity matrix independently
- Compares client-side results against reported network consensus
- Detects anomalies like single-miner dominance or fake consensus

**PoUW Engine:**
- Retrieves validator scoring data
- Validates score authenticity and reasonable distributions
- Checks for score manipulation patterns
- Records all quality metrics in audit bundle

**Value**: Provides cryptographic proof that consensus was achieved honestly, not just reported by the Router.

### 3. **Immutable Evidence Bundles**

Every audit generates a comprehensive JSON bundle stored on IPFS:

```json
{
  "audit_id": "uuid-here",
  "timestamp": "2025-12-28T10:30:00Z",
  "agent_id": "code-generator-bot",
  "task": {
    "prompt": "Generate a Python function to calculate Fibonacci sequence",
    "input_data": {"max_n": 100},
    "task_type": "code_generation"
  },
  "miner_outputs": [
    {
      "miner_id": "0xMiner1...",
      "output": "def fibonacci(n):\n  if n <= 1: return n\n  return fibonacci(n-1) + fibonacci(n-2)",
      "embedding": [0.234, -0.567, ...]
    },
    {...}
  ],
  "consensus_verification": {
    "poi_validation": {
      "similarity_matrix": [[1.0, 0.92, 0.89], [0.92, 1.0, 0.91], [0.89, 0.91, 1.0]],
      "threshold": 0.85,
      "passed": true,
      "validator_count": 3
    },
    "pouw_validation": {
      "semantic_consistency": 0.94,
      "logical_coherence": 0.91,
      "practical_applicability": 0.88,
      "overall_score": 0.91,
      "validator_id": "0xValidator1..."
    }
  },
  "cortensor_session": {
    "session_id": 147,
    "session_v2_address": "0x...",
    "block_number": 12345
  },
  "signature": {
    "auditor_address": "0x...",
    "signature": "0x...",
    "message_hash": "0x..."
  },
  "ipfs_cid": "Qm..."
}
```

**Value**: Creates a legal-grade, tamper-proof audit trail that survives beyond the network's operational lifetime.

### 4. **Compliance Dashboard**

React-based explorer enabling:

- **Agent Registry**: Browse registered AI agents with reputation scores
- **Audit History**: View complete task execution history with filtering
- **Evidence Inspection**: Drill into raw IPFS bundles with JSON viewer
- **Consensus Visualization**: See similarity matrices and validator scores
- **Signature Verification**: On-chain verification of cryptographic signatures
- **Compliance Reports**: Export audit trails for regulatory review

**Value**: Makes decentralized AI observable, transparent, and auditable for enterprise stakeholders.

### 5. **Smart Contract Integration (Roadmap)**

Future capability to trigger on-chain logic based on audit results:

```solidity
function releasePayment(bytes32 auditHash, bytes signature) external {
    require(AgentAuditor.verifyAudit(auditHash, signature), "Audit failed");
    require(AgentAuditor.poiPassed(auditHash), "PoI consensus not met");
    require(AgentAuditor.pouwScore(auditHash) >= 0.85, "Quality below threshold");
    // Release escrowed payment
}
```

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.9+** and **Node.js 18+**
- **Cortensor Router Binary** (running locally)
- **Cortensor Miner Node** (for local testing)
- **Arbitrum Sepolia Wallet** with test $ETH and $COR
- **Pinata Account** (optional for IPFS; can use local node)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/AgentAuditor.git
cd AgentAuditor
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

**Environment Configuration** (`.env` file):

```bash
# Cortensor Infrastructure
CORTENSOR_API_URL=http://127.0.0.1:5010
CORTENSOR_SESSION_ID=147  # From Cortensor Dashboard

# Blockchain (Cortensor Protocol Contracts)
ARBITRUM_SEPOLIA_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
PRIVATE_KEY=your_wallet_private_key_here

# Native Cortensor Smart Contracts (Testnet Addresses)
# Using protocol's native contracts instead of custom deployment
SESSION_V2_ADDRESS=0x...  # Cortensor SessionV2 - manages task lifecycle & payments
SESSION_QUEUE_V2_ADDRESS=0x...  # Cortensor SessionQueueV2 - handles miner orchestration
# Check latest addresses: https://docs.cortensor.network/

# Storage (Required for Evidence features)
PINATA_API_KEY=your_pinata_api_key
PINATA_SECRET_KEY=your_pinata_secret_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/agentauditor
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run the Complete Stack

**Terminal 1 - Cortensor Router:**
```bash
./cortensor-router
# Wait for: "* Found active session: 147"
```

**Terminal 2 - Cortensor Miner:**
```bash
./cortensor-node --mode ephemeral
```

**Terminal 3 - Backend:**
```bash
cd backend
uvicorn backend.main:app --reload --port 8000
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

Access dashboard at: `http://localhost:3000`

---

## 📖 Usage Guide

### Step 1: Dashboard Session Setup

1. Visit [Cortensor Dashboard](https://dashboard.cortensor.ai)
2. Create a new Session and deposit test $COR
3. Copy the Session ID to your `.env` file

### Step 2: Submit an Audit

1. Navigate to `http://localhost:3000/submit`
2. Enter:
   - **Agent ID**: `code-generator-bot` (or your registered agent)
   - **Task Type**: Select from dropdown (code generation, data analysis, text generation)
   - **Task Prompt**: `"Generate a Python function to calculate factorial"`
   - **Input Data**: Optional JSON parameters
3. Click **Submit Audit**

### Step 3: Monitor Execution

The system executes the following workflow:

1. **Task Broadcast**: Router receives task via SessionV2 contract
2. **Miner Assignment**: SessionQueueV2 assigns task to 3+ ephemeral miners
3. **Inference Execution**: Miners independently execute AI inference
4. **Network Validation**:
   - PoI validators compute embedding similarities
   - PoUW validator scores quality across 3 criteria
5. **Client-Side Verification**:
   - AgentAuditor retrieves all raw outputs
   - Re-computes embeddings locally
   - Validates consensus independently
6. **Evidence Generation**:
   - Bundles all data into JSON
   - Signs with auditor's private key
   - Uploads to IPFS

**Real-time status updates appear in the dashboard.**

### Step 4: Verify Evidence

1. Navigate to **Audit Explorer**
2. Click on your completed audit
3. Review:
   - PoI similarity matrix (should show >0.85 across miners)
   - PoUW scores (semantic/logical/practical)
   - Individual miner outputs
   - Consensus validation status
4. Click **View on IPFS** to inspect raw signed bundle
5. Use **Verify Signature** to cryptographically validate authenticity

---

## 🏆 Hackathon Alignment

**How AgentAuditor Addresses Hackathon Goals:**

| Requirement | Implementation |
|-------------|----------------|
| **Novel Router Usage** | Uses Router as data source for independent consensus verification |
| **Oracle Functionality** | Provides deterministic answers to "Did miners execute this task correctly?" |
| **Enterprise Value** | Creates legally-admissible audit trails for compliance |
| **Protocol Understanding** | Leverages SessionV2/SessionQueueV2 contracts natively (best practice) |
| **Consensus Innovation** | Client-side verification of PoI/PoUW adds trust layer above network |

### Differentiation

**Unlike typical submissions:**

- ❌ **Not just a chat interface**: We build trust infrastructure, not UX sugar
- ❌ **Not a trivia oracle**: We verify AI task execution, not static facts
- ❌ **Not consensus-replacement**: We're an independent auditor that validates existing consensus
- ❌ **Not reinventing contracts**: We use SessionV2/SessionQueueV2 properly (best practice)
- ❌ **Not blindly trusting**: We independently re-compute PoI and validate PoUW

**Our Unique Value:**

✅ **First** to create independent client-side verification of Cortensor consensus  
✅ **First** to generate cryptographically signed audit artifacts for AI tasks  
✅ **First** to solve the enterprise compliance gap for decentralized AI  
✅ **Best Practice**: Building *with* protocol contracts and *validating* network consensus  
✅ **True Oracle**: Answers verifiable questions about AI agent behavior, not just data retrieval

---

## 🔮 Roadmap

### Phase 1: Foundation (Current)
- ✅ Independent PoI embedding verification
- ✅ PoUW score validation
- ✅ Evidence bundle generation
- ✅ IPFS storage with Pinata
- ✅ Cryptographic signing

### Phase 2: Smart Contract Integration (Q1 2025)
- 🔨 On-chain audit verification contract
- 🔨 Payment escrow triggered by PoI/PoUW thresholds
- 🔨 Multi-signature auditor network

### Phase 3: Privacy Layer (Q2 2025)
- 🔮 ZK-SNARK proofs for private audits
- 🔮 Homomorphic encryption for sensitive task data
- 🔮 Selective disclosure of evidence bundles

### Phase 4: Decentralized Auditor Network (Q3 2025)
- 🔮 Multi-router consensus aggregation
- 🔮 Reputation-weighted auditor selection
- 🔮 Slashing for fraudulent audit reports

---

## 🤝 Contributing

We welcome contributions! Key areas:

- **Verification Algorithms**: Improve PoI embedding similarity checks
- **PoUW Validation**: Enhanced quality scoring mechanisms
- **Smart Contracts**: Help build on-chain verification
- **Privacy Features**: Implement ZK-proof systems

---

## 📄 License

MIT License - See `LICENSE` file for details

---

## 🙏 Acknowledgments

- **Cortensor Team**: For building the decentralized AI infrastructure and comprehensive documentation
- **Arbitrum**: For providing a scalable L2 for smart contracts
- **IPFS/Pinata**: For decentralized storage infrastructure

---

## 📞 Contact

- **GitHub**: [github.com/yourusername/AgentAuditor](https://github.com/Shreshtthh/AgentAuditor)
- **Demo Video**: [Link to demo]

---

**Built with ❤️ for the Cortensor Hackathon**
