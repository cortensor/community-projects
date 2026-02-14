import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/services/api";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

const TestConnection = () => {
  const [backendStatus, setBackendStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [backendResponse, setBackendResponse] = useState<any>(null);
  const [blockchainStatus, setBlockchainStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [blockchainResponse, setBlockchainResponse] = useState<any>(null);

  const testBackend = async () => {
    setBackendStatus("loading");
    try {
      const result = await apiClient.healthCheck();
      if (result.success) {
        setBackendStatus("success");
        setBackendResponse(result.data);
      } else {
        setBackendStatus("error");
        setBackendResponse({ error: result.error });
      }
    } catch (error: any) {
      setBackendStatus("error");
      setBackendResponse({ error: error.message });
    }
  };

  const testBlockchain = async () => {
    setBlockchainStatus("loading");
    try {
      const response = await fetch("http://127.0.0.1:8545", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "eth_blockNumber",
          params: [],
          id: 1,
        }),
      });
      const data = await response.json();
      if (data.result) {
        setBlockchainStatus("success");
        setBlockchainResponse(data);
      } else {
        setBlockchainStatus("error");
        setBlockchainResponse(data);
      }
    } catch (error: any) {
      setBlockchainStatus("error");
      setBlockchainResponse({ error: error.message });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Connection Test</h1>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Backend Test */}
        <Card>
          <CardHeader>
            <CardTitle>Backend Connection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={testBackend} disabled={backendStatus === "loading"}>
              {backendStatus === "loading" && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Test Backend (http://localhost:3001)
            </Button>
            
            {backendStatus === "success" && (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="w-5 h-5" />
                <span>Backend is connected!</span>
              </div>
            )}
            
            {backendStatus === "error" && (
              <div className="flex items-center gap-2 text-destructive">
                <XCircle className="w-5 h-5" />
                <span>Backend connection failed</span>
              </div>
            )}
            
            {backendResponse && (
              <pre className="bg-muted p-4 rounded text-xs overflow-auto">
                {JSON.stringify(backendResponse, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>

        {/* Blockchain Test */}
        <Card>
          <CardHeader>
            <CardTitle>Blockchain Connection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={testBlockchain} disabled={blockchainStatus === "loading"}>
              {blockchainStatus === "loading" && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Test Blockchain (http://127.0.0.1:8545)
            </Button>
            
            {blockchainStatus === "success" && (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="w-5 h-5" />
                <span>Blockchain is connected!</span>
              </div>
            )}
            
            {blockchainStatus === "error" && (
              <div className="flex items-center gap-2 text-destructive">
                <XCircle className="w-5 h-5" />
                <span>Blockchain connection failed</span>
              </div>
            )}
            
            {blockchainResponse && (
              <pre className="bg-muted p-4 rounded text-xs overflow-auto">
                {JSON.stringify(blockchainResponse, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TestConnection;

