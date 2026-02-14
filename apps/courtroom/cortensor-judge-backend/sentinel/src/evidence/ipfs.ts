/**
 * IPFS Integration (Pinata)
 * Stores evidence bundles permanently on IPFS
 */

import axios, { AxiosInstance } from 'axios';
import { config } from '../config/env';
import { EvidenceBundle } from '../types/evidence';

export interface PinataPinResponse {
  IpfsHash: string;
  PinSize: number;
  Timestamp: string;
}

/**
 * Pinata IPFS Service
 */
export class PinataService {
  private client: AxiosInstance;

  constructor(
    private apiKey: string = config.PINATA_API_KEY,
    private apiSecret: string = config.PINATA_API_SECRET,
    private gatewayUrl: string = config.PINATA_GATEWAY_URL
  ) {
    this.client = axios.create({
      baseURL: 'https://api.pinata.cloud',
      headers: {
        pinata_api_key: apiKey,
        pinata_secret_api_key: apiSecret,
      },
    });
  }

  /**
   * Pin evidence bundle to IPFS
   */
  async pinEvidenceBundle(bundle: EvidenceBundle): Promise<string> {
    try {
      const bundleJson = JSON.stringify(bundle, null, 2);

      const response = await this.client.post<PinataPinResponse>(
        '/pinning/pinJSONToIPFS',
        bundle,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const ipfsHash = response.data.IpfsHash;
      console.log(`Evidence pinned to IPFS: ${ipfsHash}`);

      return ipfsHash;
    } catch (error) {
      console.error('Failed to pin evidence to IPFS:', error);
      throw error;
    }
  }

  /**
   * Pin file to IPFS
   */
  async pinFile(fileBuffer: Buffer, fileName: string): Promise<string> {
    try {
      const formData = new FormData();
      const blob = new Blob([fileBuffer]);
      formData.append('file', blob, fileName);

      const response = await axios.post<PinataPinResponse>(
        'https://api.pinata.cloud/pinning/pinFileToIPFS',
        formData,
        {
          headers: {
            pinata_api_key: this.apiKey,
            pinata_secret_api_key: this.apiSecret,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data.IpfsHash;
    } catch (error) {
      console.error('Failed to pin file to IPFS:', error);
      throw error;
    }
  }

  /**
   * Retrieve from IPFS via gateway
   */
  async retrieveFromIPFS(ipfsHash: string): Promise<any> {
    try {
      const response = await axios.get(
        `${this.gatewayUrl}/ipfs/${ipfsHash}`,
        {
          timeout: 10000,
        }
      );

      return response.data;
    } catch (error) {
      console.error(`Failed to retrieve ${ipfsHash} from IPFS:`, error);
      throw error;
    }
  }

  /**
   * Unpin from IPFS
   */
  async unpinFromIPFS(ipfsHash: string): Promise<void> {
    try {
      await this.client.delete('/pinning/unpin/{ipfsHash}', {
        params: { hashToDelete: ipfsHash },
      });

      console.log(`Unpinned ${ipfsHash} from IPFS`);
    } catch (error) {
      console.error(`Failed to unpin ${ipfsHash}:`, error);
      throw error;
    }
  }

  /**
   * Check if content is pinned
   */
  async isPinned(ipfsHash: string): Promise<boolean> {
    try {
      const response = await this.client.get('/data/pinList', {
        params: { hashContains: ipfsHash },
      });

      const rows = response.data.rows || [];
      return rows.some((row: any) => row.ipfs_pin_hash === ipfsHash);
    } catch (error) {
      console.error(`Failed to check pin status for ${ipfsHash}:`, error);
      return false;
    }
  }

  /**
   * Pin with metadata
   */
  async pinWithMetadata(
    bundle: EvidenceBundle,
    metadata: Record<string, string>
  ): Promise<string> {
    try {
      const response = await this.client.post<PinataPinResponse>(
        '/pinning/pinJSONToIPFS',
        bundle,
        {
          params: {
            pinataMetadata: JSON.stringify(metadata),
            pinataOptions: JSON.stringify({
              cidVersion: 1,
            }),
          },
        }
      );

      return response.data.IpfsHash;
    } catch (error) {
      console.error('Failed to pin with metadata:', error);
      throw error;
    }
  }

  /**
   * Create gateway URL for IPFS content
   */
  getGatewayUrl(ipfsHash: string): string {
    return `${this.gatewayUrl}/ipfs/${ipfsHash}`;
  }
}

/**
 * Mock IPFS Service for testing (no actual IPFS calls)
 */
export class MockIPFSService {
  private storage: Map<string, any> = new Map();

  async pinEvidenceBundle(bundle: EvidenceBundle): Promise<string> {
    const hash = `Qm_${Math.random().toString(36).slice(2)}`;
    this.storage.set(hash, bundle);
    console.log(`[MOCK] Evidence pinned: ${hash}`);
    return hash;
  }

  async pinFile(fileBuffer: Buffer, fileName: string): Promise<string> {
    const hash = `Qm_file_${Math.random().toString(36).slice(2)}`;
    this.storage.set(hash, fileBuffer);
    return hash;
  }

  async retrieveFromIPFS(ipfsHash: string): Promise<any> {
    return this.storage.get(ipfsHash);
  }

  async unpinFromIPFS(ipfsHash: string): Promise<void> {
    this.storage.delete(ipfsHash);
  }

  async isPinned(ipfsHash: string): Promise<boolean> {
    return this.storage.has(ipfsHash);
  }

  async pinWithMetadata(
    bundle: EvidenceBundle,
    metadata: Record<string, string>
  ): Promise<string> {
    return this.pinEvidenceBundle(bundle);
  }

  getGatewayUrl(ipfsHash: string): string {
    return `ipfs://${ipfsHash}`;
  }

  // Clear all stored data
  clear(): void {
    this.storage.clear();
  }
}

// Export based on environment
export const ipfsService = process.env.USE_MOCK_IPFS === 'true'
  ? new MockIPFSService()
  : new PinataService();
