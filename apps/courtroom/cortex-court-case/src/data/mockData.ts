// Mock data for disputes
export interface Dispute {
  id: string;
  taskId: string;
  status: "pending" | "active" | "resolved" | "slashed";
  challenger: string;
  miner: string;
  similarity: number;
  bondAmount: string;
  timestamp: string;
  model: string;
  description?: string;
  createdAt: Date;
}

export const mockDisputes: Dispute[] = [
  {
    id: "DSP-0x7a3f",
    taskId: "TASK-8291",
    status: "active",
    challenger: "0x742d35Cc6634C0532925a3b844Bc9e7595f21d23",
    miner: "0x9a1c4D3e5F6789012345678901234567890AbCdE",
    similarity: 0.73,
    bondAmount: "500 COR",
    timestamp: "2 min ago",
    model: "gemini-2.5-flash",
    description: "Inconsistent trading strategy output detected",
    createdAt: new Date(Date.now() - 2 * 60 * 1000),
  },
  {
    id: "DSP-0x2b9e",
    taskId: "TASK-8289",
    status: "pending",
    challenger: "0x3f8e12Ab34Cd56Ef78901234567890123456789A",
    miner: "0x1d7c89Ab01234567890123456789012345678901",
    similarity: 0.89,
    bondAmount: "250 COR",
    timestamp: "5 min ago",
    model: "llama-3.3-70b",
    description: "Logic chain verification failed",
    createdAt: new Date(Date.now() - 5 * 60 * 1000),
  },
  {
    id: "DSP-0x5c4d",
    taskId: "TASK-8285",
    status: "resolved",
    challenger: "0x8e2f7c19123456789012345678901234567890Ab",
    miner: "0x4b3a1d67012345678901234567890123456789Cd",
    similarity: 0.91,
    bondAmount: "1000 COR",
    timestamp: "12 min ago",
    model: "gpt-5-mini",
    description: "Resolved: Miner output validated",
    createdAt: new Date(Date.now() - 12 * 60 * 1000),
  },
  {
    id: "DSP-0x1a8b",
    taskId: "TASK-8280",
    status: "slashed",
    challenger: "0x6d4c3f82012345678901234567890123456789Ef",
    miner: "0x2e9a5c71012345678901234567890123456789Gh",
    similarity: 0.45,
    bondAmount: "750 COR",
    timestamp: "18 min ago",
    model: "qwen-2.5-72b",
    description: "Severe hallucination detected - miner slashed",
    createdAt: new Date(Date.now() - 18 * 60 * 1000),
  },
  {
    id: "DSP-0x9f2e",
    taskId: "TASK-8275",
    status: "active",
    challenger: "0xAb12Cd34Ef56789012345678901234567890AbCd",
    miner: "0x5678901234567890123456789012345678901234",
    similarity: 0.67,
    bondAmount: "800 COR",
    timestamp: "25 min ago",
    model: "claude-3-opus",
    description: "Cross-validation mismatch detected",
    createdAt: new Date(Date.now() - 25 * 60 * 1000),
  },
  {
    id: "DSP-0x3c7a",
    taskId: "TASK-8270",
    status: "pending",
    challenger: "0xDef012345678901234567890123456789012345A",
    miner: "0x8901234567890123456789012345678901234567",
    similarity: 0.82,
    bondAmount: "350 COR",
    timestamp: "32 min ago",
    model: "gemini-2.5-pro",
    description: "Awaiting validator consensus",
    createdAt: new Date(Date.now() - 32 * 60 * 1000),
  },
  {
    id: "DSP-0x8d5b",
    taskId: "TASK-8265",
    status: "resolved",
    challenger: "0x234567890123456789012345678901234567890B",
    miner: "0xCdef012345678901234567890123456789012345",
    similarity: 0.96,
    bondAmount: "200 COR",
    timestamp: "45 min ago",
    model: "llama-3.3-405b",
    description: "Challenge dismissed - output valid",
    createdAt: new Date(Date.now() - 45 * 60 * 1000),
  },
  {
    id: "DSP-0x4e9c",
    taskId: "TASK-8260",
    status: "slashed",
    challenger: "0x567890123456789012345678901234567890123C",
    miner: "0x90123456789012345678901234567890123456Ef",
    similarity: 0.38,
    bondAmount: "1200 COR",
    timestamp: "1 hr ago",
    model: "mistral-large",
    description: "Critical reasoning error - full slash",
    createdAt: new Date(Date.now() - 60 * 60 * 1000),
  },
];

// Mock validators
export interface Validator {
  rank: number;
  address: string;
  name?: string;
  disputes: number;
  accuracy: number;
  stake: string;
  status: "online" | "offline";
  uptime: number;
  joinedAt: Date;
}

export const mockValidators: Validator[] = [
  { rank: 1, address: "0x742d35Cc6634C0532925a3b844Bc9e7595f21d23", name: "SentinelNode", disputes: 847, accuracy: 99.4, stake: "125,000", status: "online", uptime: 99.9, joinedAt: new Date('2024-01-15') },
  { rank: 2, address: "0x9a1c4D3e5F6789012345678901234567890AbCdE", name: "JusticeKeeper", disputes: 721, accuracy: 98.9, stake: "98,500", status: "online", uptime: 99.7, joinedAt: new Date('2024-02-20') },
  { rank: 3, address: "0x3f8e12Ab34Cd56Ef78901234567890123456789A", name: "TruthSeeker", disputes: 654, accuracy: 98.7, stake: "87,200", status: "online", uptime: 99.5, joinedAt: new Date('2024-03-10') },
  { rank: 4, address: "0x1d7c89Ab01234567890123456789012345678901", name: "ValidatorPrime", disputes: 598, accuracy: 98.2, stake: "76,800", status: "online", uptime: 99.3, joinedAt: new Date('2024-04-05') },
  { rank: 5, address: "0x8e2f7c19123456789012345678901234567890Ab", name: "ConsensusHub", disputes: 542, accuracy: 97.9, stake: "68,400", status: "offline", uptime: 95.2, joinedAt: new Date('2024-05-12') },
  { rank: 6, address: "0x4b3a1d67012345678901234567890123456789Cd", disputes: 487, accuracy: 97.5, stake: "59,200", status: "online", uptime: 98.8, joinedAt: new Date('2024-06-08') },
  { rank: 7, address: "0x6d4c3f82012345678901234567890123456789Ef", disputes: 432, accuracy: 97.1, stake: "52,100", status: "online", uptime: 98.5, joinedAt: new Date('2024-07-15') },
  { rank: 8, address: "0x2e9a5c71012345678901234567890123456789Gh", disputes: 398, accuracy: 96.8, stake: "47,600", status: "online", uptime: 98.1, joinedAt: new Date('2024-08-20') },
];

// Mock network stats
export const networkStats = {
  totalDisputes: 12847,
  activeDisputes: 127,
  resolvedDisputes: 11892,
  slashedMiners: 828,
  totalValidators: 342,
  onlineValidators: 318,
  totalMiners: 1247,
  corStaked: 2400000,
  corValue: 1.75,
  averageResolutionTime: "4.2 hrs",
  successRate: 99.2,
};

// Mock verdicts
export interface Verdict {
  id: string;
  disputeId: string;
  result: "slashed" | "cleared";
  amount: string;
  timestamp: string;
  validator: string;
}

export const mockVerdicts: Verdict[] = [
  { id: "VRD-8291", disputeId: "DSP-0x1a8b", result: "slashed", amount: "-500 COR", timestamp: "2m ago", validator: "0x742d...8f21" },
  { id: "VRD-8290", disputeId: "DSP-0x5c4d", result: "cleared", amount: "+50 COR", timestamp: "5m ago", validator: "0x9a1c...3e45" },
  { id: "VRD-8289", disputeId: "DSP-0x4e9c", result: "slashed", amount: "-750 COR", timestamp: "8m ago", validator: "0x3f8e...2a91" },
  { id: "VRD-8288", disputeId: "DSP-0x8d5b", result: "cleared", amount: "+75 COR", timestamp: "15m ago", validator: "0x1d7c...9b32" },
  { id: "VRD-8287", disputeId: "DSP-0x2b9e", result: "slashed", amount: "-1200 COR", timestamp: "22m ago", validator: "0x742d...8f21" },
];