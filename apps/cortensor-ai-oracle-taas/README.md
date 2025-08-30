# AI Oracle TaaS

A decentralized truth-as-a-service platform that eliminates AI hallucinations through consensus-based verification across multiple independent miners in the Cortensor network.

This is a platform that addresses one of the most critical challenges in AI: hallucinations and misinformation. By leveraging the Cortensor decentralized inference network, we create a consensus-based truth verification system that ensures accurate, reliable AI responses.

## Architecture

### System Components

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui
- **Backend**: Node.js/Express with TypeScript
- **Database**: PostgreSQL with Redis caching
- **Network**: Cortensor decentralized AI miners
- **Consensus**: Multi-algorithm truth verification
- **Deployment**: Docker containers with Nginx load balancing

### Key Features

- **Hallucination Detection**: Advanced algorithms detect and eliminate AI hallucinations
- **Decentralized Consensus**: Multiple independent AI miners provide responses
- **Multi-Algorithm Verification**: Semantic similarity, reputation weighting, confidence analysis
- **Real-time Processing**: Get verified answers in seconds
- **Reputation System**: Miners ranked by accuracy and reliability
- **Blockchain Logging**: Immutable truth verification records
- **Global Network**: Distributed miners worldwide
- **Quality Assurance**: Multi-layer verification system

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for development)
- PostgreSQL 15+ (if running locally)
- Redis 7+ (if running locally)
- Cortensor Installer

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://ai_oracle_user:ai_oracle_pass@localhost:5432/ai_oracle

# Redis
REDIS_URL=redis://localhost:6379

# Cortensor Network
CORTENSOR_API_ENDPOINT=http://localhost:8080
CORTENSOR_API_KEY=your_cortensor_api_key

# JWT
JWT_SECRET=your-super-secret-jwt-key

# Web3 (Optional)
WEB3_PROVIDER_URL=https://mainnet.infura.io/v3/your-project-id
BLOCKCHAIN_PRIVATE_KEY=your_private_key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_WS_URL=ws://localhost:4000
```

### Downloading the Installer

```bash
curl -L https://github.com/cortensor/installer/archive/main.tar.gz -o cortensor-installer-latest.tar.gz
tar xzfv cortensor-installer-latest.tar.gz
cd installer-main
```

### Running with Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-oracle-taas
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:4000
   - Database: localhost:5432
   - Redis: localhost:6379

4. **Check service health**
   ```bash
   curl http://localhost:4000/health
   ```

### Running for Development

1. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Install and run backend**
   ```bash
   cd backend
   npm install
   npm run dev
   ```

3. **Install and run frontend**
   ```bash
   npm install
   npm run dev
   ```

## 📊 API Documentation

### Router Connection

Our application seamlessly integrates with the Cortensor network through multiple layers:

```typescript
const CORTENSOR_ENDPOINT = "http://127.0.0.1:5010"
const API_TOKEN = "default-dev-token"

async function queryMiner(prompt: string, sessionId: number) {
  return fetch(`${CORTENSOR_ENDPOINT}/api/v1/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_id: sessionId,
      prompt,
      stream: false,
      timeout: 60
    })
  })
}
```

### Multi-Miner Strategy

```typescript
async function getConsensusResponse(query: string) {
  const minerPromises = Array.from({length: 4}, (_, i) => 
    queryMiner(query, i + session_id)
  )
  
  const responses = await Promise.allSettled(minerPromises)
  return analyzeConsensus(responses)
}
```

### Oracle Endpoints

#### Submit Query
```http
POST /api/oracle/query
Content-Type: application/json

{
  "query": "What is the current population of Tokyo?",
  "queryType": "fact",
  "minerCount": 3,
  "consensusThreshold": 0.8,
  "timeoutMs": 30000
}
```

#### Get Query Result
```http
GET /api/oracle/result/{queryId}
```

#### Check Query Status
```http
GET /api/oracle/status/{queryId}
```

### Response Format

```json
{
  "query": {
    "id": "uuid",
    "text": "What is the current population of Tokyo?",
    "type": "fact",
    "status": "completed",
    "createdAt": "2024-01-01T00:00:00Z",
    "completedAt": "2024-01-01T00:00:30Z"
  },
  "truthRecord": {
    "consensusAnswer": "The current population of Tokyo is approximately 14 million people in the city proper and 38 million in the greater metropolitan area.",
    "truthScore": 0.92,
    "consensusAlgorithm": "multi_algorithm",
    "verificationStatus": "verified",
    "consensusDetails": {...}
  },
  "minerResponses": [
    {
      "minerId": "miner_001",
      "response": "Tokyo's population is approximately 14 million...",
      "confidence": 0.89,
      "responseTime": 2500,
      "sources": ["https://example.com/source1"],
      "createdAt": "2024-01-01T00:00:15Z"
    }
  ]
}
```

## Configuration

### Consensus Algorithms

The system uses multiple consensus algorithms:

1. **Semantic Similarity Consensus** (30% weight)
   - Analyzes response similarity using NLP
   - Identifies common themes and facts

2. **Reputation Weighted Voting** (40% weight)
   - Weights responses by miner reputation
   - Prioritizes historically accurate miners

3. **Confidence Based Aggregation** (20% weight)
   - Considers miner confidence scores
   - Filters low-confidence responses

4. **Outlier Detection** (10% weight)
   - Identifies and removes outlier responses
   - Prevents manipulation and errors

### Miner Selection

Miners are selected based on:
- Reputation score (0.0 - 1.0)
- Specialization match
- Response time history
- Geographic distribution
- Current availability

## Testing (TBD)

### Unit Tests
```bash
cd backend
npm test
```

### Integration Tests
```bash
cd backend
npm run test:integration
```

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Run load tests
artillery run tests/load-test.yml
```

## Monitoring

### Health Checks

- Backend: `GET /health`
- Database: Automatic health checks in Docker
- Redis: Automatic health checks in Docker

### Metrics

The system tracks:
- Query volume and response times
- Consensus accuracy rates
- Miner participation and reputation
- Hallucination detection rates
- System resource utilization

### Logs

Logs are available in:
- Backend: `backend/logs/`
- Docker: `docker-compose logs [service]`

## Security

### Rate Limiting

- General API: 100 requests/15 minutes
- Oracle queries: 5 requests/minute
- Admin endpoints: 10 requests/minute

### Authentication

- JWT-based authentication
- Web3 wallet integration
- API key support for enterprise

### Data Protection

- All queries encrypted in transit
- Sensitive data hashed in database
- GDPR compliance features

## Deployment

### Production Deployment

1. **Set production environment variables**
2. **Build and deploy with Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```
3. **Configure SSL certificates**
4. **Set up monitoring and alerting**
5. **Configure backup strategies**

### Scaling

- Horizontal scaling with load balancers
- Database read replicas
- Redis clustering
- CDN for static assets
- Auto-scaling based on query volume

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines

- Follow TypeScript best practices
- Write comprehensive tests
- Document API changes
- Follow semantic versioning

## 🆘 Support

**Built with ❤️ for the decentralized AI future**
