import { createPublicClient, http, type Abi } from 'viem';
import { config } from '@/lib/config';
import SessionV2ABI from '@/abi/SessionV2.json';
import { FormattedSession, RawSession } from '@/types';
import { privateKeyToAccount } from 'viem/accounts';

const publicClient = createPublicClient({ chain: config.chain, transport: http(config.rpc.http) });
const account = privateKeyToAccount(config.privateKey);

function formatSession(session: RawSession): FormattedSession {
  return {
    id: session.id.toString(),
    sid: session.sid,
    name: session.name,
    metadata: session.metadata,
    state: session.state,
    createdAt: new Date(Number(session.createdAt) * 1000).toISOString(),
    updatedAt: new Date(Number(session.updatedAt) * 1000).toISOString(),
    owner: session.owner,
    ephemeralNodes: session.ephemeralNodes,
    dedicatedNodes: session.dedicatedNodes,
    mode: Number(session.mode),
    redundant: Number(session.redundant),
    minNumOfNodes: Number(session.minNumOfNodes),
    maxNumOfNodes: Number(session.maxNumOfNodes),
    numOfValidatorNodes: Number(session.numOfValidatorNodes),
    routerMetadatas: session.routerMetadatas,
    routerAddresses: session.routerAddresses,
  };
}

/**
 * Fetches the most recent session for the application's backend wallet.
 * In a real-world scenario, you might want to fetch a specific active session.
 * @returns The ID of the latest session as a string.
 */
export async function getLatestSessionIdForWallet(): Promise<FormattedSession> {
  try {
    const sessions = await publicClient.readContract({
      address: config.contracts.sessionV2.address,
      abi: SessionV2ABI as Abi,
      functionName: 'getSessionsByAddressByPage',
      args: [
        account.address,
        0,
        999,
      ],
    }) as RawSession[];

    if (!sessions || sessions.length === 0) {
      // In a real application, you might want to automatically create a new session here.
      // For now, we throw an error if no sessions exist for the backend wallet.
      throw new Error(`No sessions found for the backend wallet address: ${account.address}`);
    }

    const latestSession = sessions[sessions.length - 1];
    return formatSession(latestSession);
  } catch (error) {
    console.error('[SessionService] Failed to get latest session ID:', error);
    throw new Error('Could not retrieve a valid session from the blockchain.');
  }
}