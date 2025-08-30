export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Cortensor API Server</h1>
        <p className="text-lg text-gray-600 mb-8">
          API server running on localhost:3002
        </p>
        <div className="bg-gray-100 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Available Endpoints:</h2>
          <ul className="text-left">
            <li className="mb-1">
              <code className="bg-gray-200 px-2 py-1 rounded">POST /api/chat</code>
              <span className="ml-2">- Chat API endpoint</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}