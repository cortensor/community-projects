/**
 * Justice Contract Client
 * Interacts with the Justice smart contract
 */

import { ethers } from 'ethers';
import { config } from '../config/env';
import { EvidenceBundle, DisputeStatus, VerdictType } from '../types/evidence';

const JUSTICE_ABI = [
  'function initiateChallenge((string,string,string,string,string,uint256,address,uint256) _evidence, uint256 _bond) external returns (uint256)',
  'function submitVerdict(uint256 _disputeId, uint8 _verdict, string _verdictReasoning) external',
  'function settleDispute(uint256 _disputeId) external',
  'function getDispute(uint256 _disputeId) external view returns (tuple(uint256 id, tuple(string,string,string,string,string,uint256,address,uint256) evidence, address challenger, uint256 challengeBond, uint8 status, uint8 verdict, address judge, string verdictReasoning, uint256 startTime, uint256 settlementTime, uint256 slashAmount, uint256 rewardAmount))',
  'function registerValidator(address _validator, uint256 _initialReputation) external',
  'function getMinerTrustScore(address _miner) external view returns (uint256)',
  'event DisputeInitiated(uint256 indexed disputeId, address indexed challenger, address indexed miner, uint256 bond, string ipfsHash)',
  'event VerdictSubmitted(uint256 indexed disputeId, address indexed judge, uint8 verdict, uint256 slashAmount, uint256 rewardAmount)',
  'event DisputeSettled(uint256 indexed disputeId, address indexed miner, address indexed challenger, uint256 slashAmount, uint256 rewardAmount)',
];

const COR_TOKEN_ABI = [
  'function approve(address spender, uint256 amount) external returns (bool)',
  'function allowance(address owner, address spender) external view returns (uint256)',
  'function transfer(address to, uint256 amount) external returns (bool)',
  'function balanceOf(address account) external view returns (uint256)',
];

/**
 * Justice Contract Client
 */
export class JusticeClient {
  private provider: ethers.Provider;
  private signer: ethers.Signer;
  private justiceContract: ethers.Contract;
  private corTokenContract: ethers.Contract;

  constructor(
    private rpcUrl: string = config.BLOCKCHAIN_RPC_URL,
    private justiceAddress: string = config.JUSTICE_CONTRACT_ADDRESS,
    private corTokenAddress: string = config.COR_TOKEN_ADDRESS,
    private validatorPrivateKey: string = config.VALIDATOR_PRIVATE_KEY
  ) {
    this.provider = new ethers.JsonRpcProvider(rpcUrl);
    this.signer = new ethers.Wallet(validatorPrivateKey, this.provider);

    this.justiceContract = new ethers.Contract(
      justiceAddress,
      JUSTICE_ABI,
      this.signer
    );

    this.corTokenContract = new ethers.Contract(
      corTokenAddress,
      COR_TOKEN_ABI,
      this.signer
    );
  }

  /**
   * Initiate challenge on-chain
   */
  async initiateChallenge(
    evidence: EvidenceBundle,
    bondAmount: string // in wei
  ): Promise<string> {
    try {
      // Convert evidence to contract format
      const chainEvidence = {
        promptHash: evidence.promptHash,
        minerResult: evidence.minerResult,
        logicTrace: JSON.stringify(evidence.logicTrace),
        poiHash: evidence.poiHash,
        ipfsHash: evidence.ipfsHash,
        modelId: evidence.modelId,
        miner: evidence.miner,
        timestamp: evidence.timestamp,
      };

      // Approve COR token transfer
      const approveTx = await this.corTokenContract.approve(
        this.justiceAddress,
        bondAmount
      );
      await approveTx.wait();
      console.log('Bond approval successful');

      // Initiate challenge
      const tx = await this.justiceContract.initiateChallenge(
        chainEvidence,
        bondAmount,
        {
          gasLimit: 500000,
        }
      );

      const receipt = await tx.wait();
      console.log('Challenge initiated, tx hash:', receipt.hash);

      // Extract dispute ID from event
      const event = receipt.logs
        .map((log: any) => {
          try {
            return this.justiceContract.interface.parseLog(log);
          } catch {
            return null;
          }
        })
        .find((e: any) => e?.name === 'DisputeInitiated');

      if (event) {
        console.log('Dispute ID:', event.args[0]);
        return event.args[0].toString();
      }

      throw new Error('Could not extract dispute ID');
    } catch (error) {
      console.error('Failed to initiate challenge:', error);
      throw error;
    }
  }

  /**
   * Submit verdict as validator
   */
  async submitVerdict(
    disputeId: string,
    verdict: VerdictType,
    verdictReasoning: string
  ): Promise<string> {
    try {
      const verdictEnum = this.verdictToEnum(verdict);

      const tx = await this.justiceContract.submitVerdict(
        disputeId,
        verdictEnum,
        verdictReasoning,
        {
          gasLimit: 300000,
        }
      );

      const receipt = await tx.wait();
      console.log('Verdict submitted, tx hash:', receipt.hash);

      return receipt.hash;
    } catch (error) {
      console.error('Failed to submit verdict:', error);
      throw error;
    }
  }

  /**
   * Settle dispute and execute rewards/slashes
   */
  async settleDispute(disputeId: string): Promise<string> {
    try {
      const tx = await this.justiceContract.settleDispute(disputeId, {
        gasLimit: 300000,
      });

      const receipt = await tx.wait();
      console.log('Dispute settled, tx hash:', receipt.hash);

      return receipt.hash;
    } catch (error) {
      console.error('Failed to settle dispute:', error);
      throw error;
    }
  }

  /**
   * Get dispute details
   */
  async getDispute(disputeId: string) {
    try {
      const dispute = await this.justiceContract.getDispute(disputeId);
      return this.formatDisputeData(dispute);
    } catch (error) {
      console.error('Failed to fetch dispute:', error);
      throw error;
    }
  }

  /**
   * Get miner trust score
   */
  async getMinerTrustScore(minerAddress: string): Promise<number> {
    try {
      const score = await this.justiceContract.getMinerTrustScore(minerAddress);
      return Number(score);
    } catch (error) {
      console.error('Failed to fetch trust score:', error);
      throw error;
    }
  }

  /**
   * Register validator (admin only)
   */
  async registerValidator(
    validatorAddress: string,
    initialReputation: number
  ): Promise<string> {
    try {
      const tx = await this.justiceContract.registerValidator(
        validatorAddress,
        initialReputation,
        {
          gasLimit: 200000,
        }
      );

      const receipt = await tx.wait();
      console.log('Validator registered, tx hash:', receipt.hash);

      return receipt.hash;
    } catch (error) {
      console.error('Failed to register validator:', error);
      throw error;
    }
  }

  /**
   * Get validator address
   */
  getValidatorAddress(): string {
    return this.signer.getAddress() as any;
  }

  /**
   * Check COR token balance
   */
  async checkTokenBalance(address: string): Promise<string> {
    try {
      const balance = await this.corTokenContract.balanceOf(address);
      return ethers.formatUnits(balance, 18);
    } catch (error) {
      console.error('Failed to check balance:', error);
      throw error;
    }
  }

  /**
   * Listen for dispute events
   */
  async listenForDisputeEvents(
    callback: (event: any) => void
  ): Promise<void> {
    try {
      this.justiceContract.on('DisputeInitiated', (disputeId: any, challenger: any, miner: any, bond: any, ipfsHash: any) => {
        callback({
          event: 'DisputeInitiated',
          disputeId: disputeId.toString(),
          challenger,
          miner,
          bond: bond.toString(),
          ipfsHash,
        });
      });

      this.justiceContract.on('VerdictSubmitted', (disputeId: any, judge: any, verdict: any, slashAmount: any, rewardAmount: any) => {
        callback({
          event: 'VerdictSubmitted',
          disputeId: disputeId.toString(),
          judge,
          verdict: verdict.toString(),
          slashAmount: slashAmount.toString(),
          rewardAmount: rewardAmount.toString(),
        });
      });

      console.log('Listening for dispute events...');
    } catch (error) {
      console.error('Failed to set up event listeners:', error);
      throw error;
    }
  }

  /**
   * Private helpers
   */

  private verdictToEnum(verdict: VerdictType): number {
    switch (verdict) {
      case VerdictType.NONE:
        return 0;
      case VerdictType.MINER_CORRECT:
        return 1;
      case VerdictType.MINER_WRONG:
        return 2;
      case VerdictType.INSUFFICIENT_EVIDENCE:
        return 3;
      default:
        return 0;
    }
  }

  private formatDisputeData(dispute: any) {
    return {
      id: dispute.id.toString(),
      challenger: dispute.challenger,
      miner: dispute.evidence.miner,
      challengeBond: dispute.challengeBond.toString(),
      status: this.statusFromEnum(dispute.status),
      verdict: this.verdictFromEnum(dispute.verdict),
      judge: dispute.judge,
      startTime: dispute.startTime.toNumber(),
      settlementTime: dispute.settlementTime?.toNumber(),
      slashAmount: dispute.slashAmount?.toString(),
      rewardAmount: dispute.rewardAmount?.toString(),
    };
  }

  private statusFromEnum(status: number): DisputeStatus {
    const statuses = Object.values(DisputeStatus);
    return (statuses[status] || DisputeStatus.PENDING) as DisputeStatus;
  }

  private verdictFromEnum(verdict: number): VerdictType {
    const verdicts = Object.values(VerdictType);
    return (verdicts[verdict] || VerdictType.NONE) as VerdictType;
  }
}

// Export singleton
export const justiceClient = new JusticeClient();
