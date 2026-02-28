/**
 * PinataCompiler.ts
 * Compiles the final DAG execution topological memory into a verifiable JSON artifact.
 * Hashes the payload locally via SHA-256 before uploading to the IPFS network via Pinata.
 */

import { createHash } from "crypto";

export interface IPFSEvidenceBundle {
  swarmId: string;
  execution_hash: string;
  timestamp: string;
  payload: Record<string, string>;
}

export class PinataCompiler {
  private jwt: string;

  constructor(jwt: string) {
    this.jwt = jwt;
  }

  /**
   * Hashes the terminal memory state and uploads the verifiable JSON to IPFS.
   * Returns the IPFS CID string.
   */
  public async pinEvidence(swarmId: string, memoryState: Record<string, string>): Promise<{ cid: string; hash: string }> {
    if (!this.jwt || this.jwt === "mock_jwt") {
      console.warn("[PINATA_WARN] Missing JWT. Bypassing upload and returning mock CID.");
      return this._mockUpload(swarmId, memoryState);
    }

    // 1. Compile the Bundle
    const payloadString = JSON.stringify(memoryState);
    
    // 2. Cryptographic Anchor Hashing (SHA-256)
    // This hash must match the state submitted to the ERC-8004 smart contract
    const executionHash = "0x" + createHash("sha256").update(payloadString).digest("hex");

    const evidenceBundle: IPFSEvidenceBundle = {
      swarmId,
      execution_hash: executionHash,
      timestamp: new Date().toISOString(),
      payload: memoryState
    };

    // 3. Pin to IPFS
    try {
      console.log(`[PINATA_EXEC] Uploading bundle (Hash: ${executionHash.substring(0, 10)}...) to IPFS...`);
      
      const response = await fetch("https://api.pinata.cloud/pinning/pinJSONToIPFS", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.jwt}`
        },
        body: JSON.stringify({
          pinataContent: evidenceBundle,
          pinataMetadata: { name: `Cortex_Auditor_Execution_${swarmId}` }
        })
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error(`[PINATA_ERROR_BODY] ${errorBody}`);
        throw new Error(`Pinata API Failure: ${response.statusText} - ${errorBody}`);
      }

      const uploadResult = await response.json();
      return { cid: uploadResult.IpfsHash, hash: executionHash };

    } catch (error: any) {
      console.error("[PINATA_FATAL_ERROR]", error.message);
      throw error;
    }
  }

  private _mockUpload(swarmId: string, memoryState: Record<string, string>) {
    const mockHash = "0x" + createHash("sha256").update(JSON.stringify(memoryState)).digest("hex");
    return {
      cid: `QmMock${Math.random().toString(36).substring(7).toUpperCase()}EvidenceCID`,
      hash: mockHash
    };
  }
}
