# Cortensor Chatbot

A Next.js-based web application that provides a chat interface for interacting with Cortensor's Web3 infrastructure and AI services.

## Features

- Real-time chat interface with Server-Sent Events (SSE)
- Web3 integration with Cortensor network
- Persona-based conversations
- Memory-enabled chat sessions
- Responsive design with sidebar navigation
- Task queue management
- Session management

## Tech Stack

- **Frontend**: Next.js 15.3.2, React 19, TypeScript
- **Styling**: Tailwind CSS
- **Web3**: Viem for blockchain integration
- **Icons**: Lucide React
- **Deployment**: Docker with Node.js 20 Alpine

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables (see `.env-example`)
4. Run the development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Development

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Docker Deployment

```bash
docker build -t tensorme .
docker run -p 3000:3000tensorme 
```

## Architecture

- **Frontend**: Next.js App Router with React hooks
- **Backend**: Next.js API routes
- **Blockchain**: Cortensor network integration
- **Database**: Session-based storage

## License

MIT

