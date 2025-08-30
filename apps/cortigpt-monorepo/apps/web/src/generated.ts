import {
  createUseReadContract,
  createUseWriteContract,
  createUseSimulateContract,
  createUseWatchContractEvent,
} from 'wagmi/codegen'

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// SessionQueueV2
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const sessionQueueV2Abi = [
  { type: 'constructor', inputs: [], stateMutability: 'nonpayable' },
  {
    type: 'error',
    inputs: [{ name: 'owner', internalType: 'address', type: 'address' }],
    name: 'OwnableInvalidOwner',
  },
  {
    type: 'error',
    inputs: [{ name: 'account', internalType: 'address', type: 'address' }],
    name: 'OwnableUnauthorizedAccount',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'previousOwner',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
      {
        name: 'newOwner',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
    ],
    name: 'OwnershipTransferred',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miner',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
    ],
    name: 'TaskAcked',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miners',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
    ],
    name: 'TaskAllCommitted',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miners',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
    ],
    name: 'TaskAllPrecommitted',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miners',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
    ],
    name: 'TaskAssigned',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
    ],
    name: 'TaskCommitEnded',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miner',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
    ],
    name: 'TaskCommitted',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miners',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
    ],
    name: 'TaskEnded',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
    ],
    name: 'TaskPrecommitEnded',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'miner',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
    ],
    name: 'TaskPrecommitted',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'globalId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskData',
        internalType: 'string',
        type: 'string',
        indexed: false,
      },
    ],
    name: 'TaskQueued',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'ack',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'addrs', internalType: 'address[]', type: 'address[]' },
    ],
    name: 'assignTask',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'data', internalType: 'string', type: 'string' },
    ],
    name: 'commit',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'forceEnd', internalType: 'bool', type: 'bool' },
    ],
    name: 'end',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'forceEnd', internalType: 'bool', type: 'bool' },
    ],
    name: 'end2',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'endAck',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'emitAllCommitted', internalType: 'bool', type: 'bool' },
    ],
    name: 'endCommit',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'emitAllPrecommitted', internalType: 'bool', type: 'bool' },
    ],
    name: 'endPrecommit',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskData', internalType: 'string', type: 'string' },
      { name: 'promptType', internalType: 'uint256', type: 'uint256' },
      { name: 'promptTemplate', internalType: 'string', type: 'string' },
      { name: 'llmParams', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    name: 'enqueueTask',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getACLAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getAllTaskResultAckedTimestamps',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getAllTaskResultCommitTimestamps',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getAllTaskResultPrecommitTimestamps',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getAllTaskResults',
    outputs: [
      { name: '', internalType: 'address[][]', type: 'address[][]' },
      { name: '', internalType: 'string[][]', type: 'string[][]' },
      { name: '', internalType: 'bytes32[][]', type: 'bytes32[][]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'str', internalType: 'string', type: 'string' }],
    name: 'getHash',
    outputs: [{ name: '', internalType: 'bytes32', type: 'bytes32' }],
    stateMutability: 'pure',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getIAMAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getLatestTask',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'addr', internalType: 'address', type: 'address' }],
    name: 'getNodeId',
    outputs: [{ name: '', internalType: 'bytes32', type: 'bytes32' }],
    stateMutability: 'pure',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getNodePoolAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getNodeReputationAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getNodeStatsAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionQueueValidationAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionReputationAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionStatsAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getTaskCountBySessionId',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionIds', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    name: 'getTaskCountBySessionIds',
    outputs: [{ name: '', internalType: 'uint256[]', type: 'uint256[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskData',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecoration',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionQueueV2.TaskDecoration',
        type: 'tuple',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
          { name: 'taskId', internalType: 'uint256', type: 'uint256' },
          { name: 'promptType', internalType: 'uint256', type: 'uint256' },
          { name: 'promptTemplate', internalType: 'string', type: 'string' },
          { name: 'maxTokens', internalType: 'uint256', type: 'uint256' },
          { name: 'temperature', internalType: 'uint256', type: 'uint256' },
          { name: 'topP', internalType: 'uint256', type: 'uint256' },
          { name: 'topK', internalType: 'uint256', type: 'uint256' },
          { name: 'presencePenalty', internalType: 'uint256', type: 'uint256' },
          {
            name: 'frequencyPenalty',
            internalType: 'uint256',
            type: 'uint256',
          },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationFrequencyPenalty',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationMaxTokens',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationPresencePenalty',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationPromptTemplate',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationPromptType',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationTemperature',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationTopK',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskDecorationTopP',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'miner', internalType: 'address', type: 'address' },
    ],
    name: 'getTaskResultCommitTimestamp',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'miner', internalType: 'address', type: 'address' },
    ],
    name: 'getTaskResultData',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskResultHashes',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'bytes32[]', type: 'bytes32[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'miner', internalType: 'address', type: 'address' },
    ],
    name: 'getTaskResultPrecommitTimestamp',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'addr', internalType: 'address', type: 'address' },
    ],
    name: 'getTaskResultState',
    outputs: [
      {
        name: '',
        internalType: 'enum SessionQueueV2.TaskState',
        type: 'uint8',
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskResults',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'string[]', type: 'string[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskStatus',
    outputs: [
      {
        name: '',
        internalType: 'enum SessionQueueV2.TaskStatus',
        type: 'uint8',
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getTasksBySessionId',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionQueueV2.Task[]',
        type: 'tuple[]',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'gid', internalType: 'uint256', type: 'uint256' },
          { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
          { name: 'data', internalType: 'string', type: 'string' },
          {
            name: 'assignedMiners',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'ended', internalType: 'bool', type: 'bool' },
          {
            name: 'status',
            internalType: 'enum SessionQueueV2.TaskStatus',
            type: 'uint8',
          },
          { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
          { name: 'lastPrecommitAt', internalType: 'uint256', type: 'uint256' },
          { name: 'lastCommitAt', internalType: 'uint256', type: 'uint256' },
          { name: 'finishedAt', internalType: 'uint256', type: 'uint256' },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getUseSessionStats',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'isAcked',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'addr', internalType: 'address', type: 'address' }],
    name: 'isOracleNode',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'addr', internalType: 'address', type: 'address' }],
    name: 'isPrimaryModule',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'owner',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'pop',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'popSpecificTask',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'hash', internalType: 'bytes32', type: 'bytes32' },
      { name: 'data', internalType: 'string', type: 'string' },
    ],
    name: 'precommit',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [],
    name: 'renounceOwnership',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    name: 'sessionTaskCount',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: '', internalType: 'uint256', type: 'uint256' },
      { name: '', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'sessionTaskDecorations',
    outputs: [
      { name: 'id', internalType: 'uint256', type: 'uint256' },
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
      { name: 'promptType', internalType: 'uint256', type: 'uint256' },
      { name: 'promptTemplate', internalType: 'string', type: 'string' },
      { name: 'maxTokens', internalType: 'uint256', type: 'uint256' },
      { name: 'temperature', internalType: 'uint256', type: 'uint256' },
      { name: 'topP', internalType: 'uint256', type: 'uint256' },
      { name: 'topK', internalType: 'uint256', type: 'uint256' },
      { name: 'presencePenalty', internalType: 'uint256', type: 'uint256' },
      { name: 'frequencyPenalty', internalType: 'uint256', type: 'uint256' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: '', internalType: 'uint256', type: 'uint256' },
      { name: '', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'sessionTaskResults',
    outputs: [
      { name: 'id', internalType: 'uint256', type: 'uint256' },
      { name: 'gid', internalType: 'uint256', type: 'uint256' },
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'precommitCounter', internalType: 'uint256', type: 'uint256' },
      { name: 'commitCounter', internalType: 'uint256', type: 'uint256' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: '', internalType: 'uint256', type: 'uint256' },
      { name: '', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'sessionTasks',
    outputs: [
      { name: 'id', internalType: 'uint256', type: 'uint256' },
      { name: 'gid', internalType: 'uint256', type: 'uint256' },
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'data', internalType: 'string', type: 'string' },
      { name: 'ended', internalType: 'bool', type: 'bool' },
      {
        name: 'status',
        internalType: 'enum SessionQueueV2.TaskStatus',
        type: 'uint8',
      },
      { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
      { name: 'lastPrecommitAt', internalType: 'uint256', type: 'uint256' },
      { name: 'lastCommitAt', internalType: 'uint256', type: 'uint256' },
      { name: 'finishedAt', internalType: 'uint256', type: 'uint256' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: '_aclContract', internalType: 'address', type: 'address' },
    ],
    name: 'setACL',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_iamContract', internalType: 'address', type: 'address' },
    ],
    name: 'setIAM',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_nodePoolContract', internalType: 'address', type: 'address' },
    ],
    name: 'setNodePool',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      {
        name: '_nodeReputationContract',
        internalType: 'address',
        type: 'address',
      },
    ],
    name: 'setNodeReputation',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_nodeStatsContract', internalType: 'address', type: 'address' },
    ],
    name: 'setNodeStats',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      {
        name: '_sessionQueueValidationContract',
        internalType: 'address',
        type: 'address',
      },
    ],
    name: 'setSessionQueueValidation',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      {
        name: '_sessionReputationContract',
        internalType: 'address',
        type: 'address',
      },
    ],
    name: 'setSessionReputation',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      {
        name: '_sessionStatsContract',
        internalType: 'address',
        type: 'address',
      },
    ],
    name: 'setSessionStats',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: '_useSessionStats', internalType: 'bool', type: 'bool' }],
    name: 'setUseSessionStats',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [],
    name: 'subversion',
    outputs: [{ name: '', internalType: 'uint8', type: 'uint8' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'newOwner', internalType: 'address', type: 'address' }],
    name: 'transferOwnership',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [],
    name: 'useSessionStats',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'str', internalType: 'string', type: 'string' },
      { name: 'expectedHash', internalType: 'bytes32', type: 'bytes32' },
    ],
    name: 'verifyHash',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'pure',
  },
  {
    type: 'function',
    inputs: [],
    name: 'version',
    outputs: [{ name: '', internalType: 'uint8', type: 'uint8' }],
    stateMutability: 'view',
  },
] as const

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const sessionQueueV2Address = {
  421614: '0x2fCC55699048eD2e22fe46b1dD45557024fD1836',
} as const

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const sessionQueueV2Config = {
  address: sessionQueueV2Address,
  abi: sessionQueueV2Abi,
} as const

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// SessionV2
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const sessionV2Abi = [
  { type: 'constructor', inputs: [], stateMutability: 'nonpayable' },
  {
    type: 'error',
    inputs: [{ name: 'owner', internalType: 'address', type: 'address' }],
    name: 'OwnableInvalidOwner',
  },
  {
    type: 'error',
    inputs: [{ name: 'account', internalType: 'address', type: 'address' }],
    name: 'OwnableUnauthorizedAccount',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: true,
      },
    ],
    name: 'AllRoutersRemoved',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'nodeAddress',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
    ],
    name: 'DedicatedNodeAdded',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'nodeAddress',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
    ],
    name: 'DedicatedNodeRemoved',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: true,
      },
      {
        name: 'nodeAddresses',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
      {
        name: 'newNodeCount',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'assignmentType',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
    ],
    name: 'NewNodeAssignedToSession',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'nodeId',
        internalType: 'bytes32',
        type: 'bytes32',
        indexed: false,
      },
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
    ],
    name: 'NodeReleased',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'previousOwner',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
      {
        name: 'newOwner',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
    ],
    name: 'OwnershipTransferred',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'routerAddress',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
      {
        name: 'routerInfo',
        internalType: 'string',
        type: 'string',
        indexed: false,
      },
    ],
    name: 'RouterAdded',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'routerAddress',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
    ],
    name: 'RouterRemoved',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'routerAddress',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
      {
        name: 'routerInfo',
        internalType: 'string',
        type: 'string',
        indexed: false,
      },
    ],
    name: 'RouterUpdated',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      { name: 'sid', internalType: 'bytes32', type: 'bytes32', indexed: false },
      {
        name: 'owner',
        internalType: 'address',
        type: 'address',
        indexed: false,
      },
      {
        name: 'miners',
        internalType: 'address[]',
        type: 'address[]',
        indexed: false,
      },
    ],
    name: 'SessionCreated',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: true,
      },
      {
        name: 'deactivator',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
    ],
    name: 'SessionDeactivated',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: true,
      },
      {
        name: 'updater',
        internalType: 'address',
        type: 'address',
        indexed: true,
      },
      {
        name: 'minNumOfNodes',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'maxNumOfNodes',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'redundant',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
    ],
    name: 'SessionUpdated',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'nodeIds',
        internalType: 'bytes32[]',
        type: 'bytes32[]',
        indexed: false,
      },
    ],
    name: 'TaskAssigned',
  },
  {
    type: 'event',
    anonymous: false,
    inputs: [
      {
        name: 'sessionId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskId',
        internalType: 'uint256',
        type: 'uint256',
        indexed: false,
      },
      {
        name: 'taskData',
        internalType: 'string',
        type: 'string',
        indexed: false,
      },
      {
        name: 'clientReference',
        internalType: 'string',
        type: 'string',
        indexed: false,
      },
    ],
    name: 'TaskSubmitted',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'nodeAddress', internalType: 'address', type: 'address' },
    ],
    name: 'addDedicatedNode',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'routerAddress', internalType: 'address', type: 'address' },
      { name: 'metadata', internalType: 'string', type: 'string' },
    ],
    name: 'addRouter',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    name: 'allNodeAddresses',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'name', internalType: 'string', type: 'string' },
      { name: 'metadata', internalType: 'string', type: 'string' },
      { name: 'variableAddress', internalType: 'address', type: 'address' },
      { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'redundant', internalType: 'uint256', type: 'uint256' },
      { name: 'numOfValidatorNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'mode', internalType: 'uint256', type: 'uint256' },
      { name: 'reserveEphemeralNodes', internalType: 'bool', type: 'bool' },
      { name: 'sla', internalType: 'uint256', type: 'uint256' },
      { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
      { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
      {
        name: 'maxTaskExecutionCount',
        internalType: 'uint256',
        type: 'uint256',
      },
    ],
    name: 'create',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'deactivateSession',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'doesSessionExist',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getACLAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getActiveSessionsByAddress',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.Session[]',
        type: 'tuple[]',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'sid', internalType: 'bytes32', type: 'bytes32' },
          { name: 'name', internalType: 'string', type: 'string' },
          { name: 'metadata', internalType: 'string', type: 'string' },
          {
            name: 'state',
            internalType: 'enum SessionV2.SessionState',
            type: 'uint8',
          },
          { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
          { name: 'updatedAt', internalType: 'uint256', type: 'uint256' },
          { name: 'owner', internalType: 'address', type: 'address' },
          {
            name: 'ephemeralNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          {
            name: 'dedicatedNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'mode', internalType: 'uint256', type: 'uint256' },
          { name: 'redundant', internalType: 'uint256', type: 'uint256' },
          { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
          { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
          {
            name: 'numOfValidatorNodes',
            internalType: 'uint256',
            type: 'uint256',
          },
          {
            name: 'routerMetadatas',
            internalType: 'string[]',
            type: 'string[]',
          },
          {
            name: 'routerAddresses',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'sla', internalType: 'uint256', type: 'uint256' },
          { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
          { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
          {
            name: 'maxTaskExecutionCount',
            internalType: 'uint256',
            type: 'uint256',
          },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getIAMAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getLatestRouterAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getLatestRouterIndex',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getLatestRouterInfo',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getLatestSessionId',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getLatestTaskRequest',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.TaskRequest',
        type: 'tuple',
        components: [
          { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'gid', internalType: 'uint256', type: 'uint256' },
          { name: 'requestDate', internalType: 'uint256', type: 'uint256' },
          { name: 'completed', internalType: 'bool', type: 'bool' },
          { name: 'data', internalType: 'string', type: 'string' },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'nodeAddress', internalType: 'address', type: 'address' }],
    name: 'getNodeAssignedTimestamp',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'addr', internalType: 'address', type: 'address' }],
    name: 'getNodeId',
    outputs: [{ name: '', internalType: 'bytes32', type: 'bytes32' }],
    stateMutability: 'pure',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getNodePoolAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'nodeAddress', internalType: 'address', type: 'address' }],
    name: 'getNodeSessionId',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'index', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getRouterAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getRouterCount',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'routerAddress', internalType: 'address', type: 'address' },
    ],
    name: 'getRouterIndex',
    outputs: [{ name: '', internalType: 'int256', type: 'int256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'routerAddress', internalType: 'address', type: 'address' },
    ],
    name: 'getRouterInfo',
    outputs: [{ name: '', internalType: 'string', type: 'string' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getRouterMetadatasByAddress',
    outputs: [{ name: '', internalType: 'string[]', type: 'string[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionIds', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    name: 'getRouterMetadatasBySessionIds',
    outputs: [{ name: '', internalType: 'string[]', type: 'string[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'getSession',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.Session',
        type: 'tuple',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'sid', internalType: 'bytes32', type: 'bytes32' },
          { name: 'name', internalType: 'string', type: 'string' },
          { name: 'metadata', internalType: 'string', type: 'string' },
          {
            name: 'state',
            internalType: 'enum SessionV2.SessionState',
            type: 'uint8',
          },
          { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
          { name: 'updatedAt', internalType: 'uint256', type: 'uint256' },
          { name: 'owner', internalType: 'address', type: 'address' },
          {
            name: 'ephemeralNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          {
            name: 'dedicatedNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'mode', internalType: 'uint256', type: 'uint256' },
          { name: 'redundant', internalType: 'uint256', type: 'uint256' },
          { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
          { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
          {
            name: 'numOfValidatorNodes',
            internalType: 'uint256',
            type: 'uint256',
          },
          {
            name: 'routerMetadatas',
            internalType: 'string[]',
            type: 'string[]',
          },
          {
            name: 'routerAddresses',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'sla', internalType: 'uint256', type: 'uint256' },
          { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
          { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
          {
            name: 'maxTaskExecutionCount',
            internalType: 'uint256',
            type: 'uint256',
          },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionAuthAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionCount',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getSessionCountByAddress',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getSessionIdAndNameAndMetadataByAddress',
    outputs: [
      { name: '', internalType: 'uint256[]', type: 'uint256[]' },
      { name: '', internalType: 'string[]', type: 'string[]' },
      { name: '', internalType: 'string[]', type: 'string[]' },
      { name: '', internalType: 'uint256[]', type: 'uint256[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getSessionIds',
    outputs: [{ name: '', internalType: 'uint256[]', type: 'uint256[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionPaymentAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionQueueAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'getSessionStatsAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getSessionsByAddress',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.Session[]',
        type: 'tuple[]',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'sid', internalType: 'bytes32', type: 'bytes32' },
          { name: 'name', internalType: 'string', type: 'string' },
          { name: 'metadata', internalType: 'string', type: 'string' },
          {
            name: 'state',
            internalType: 'enum SessionV2.SessionState',
            type: 'uint8',
          },
          { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
          { name: 'updatedAt', internalType: 'uint256', type: 'uint256' },
          { name: 'owner', internalType: 'address', type: 'address' },
          {
            name: 'ephemeralNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          {
            name: 'dedicatedNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'mode', internalType: 'uint256', type: 'uint256' },
          { name: 'redundant', internalType: 'uint256', type: 'uint256' },
          { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
          { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
          {
            name: 'numOfValidatorNodes',
            internalType: 'uint256',
            type: 'uint256',
          },
          {
            name: 'routerMetadatas',
            internalType: 'string[]',
            type: 'string[]',
          },
          {
            name: 'routerAddresses',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'sla', internalType: 'uint256', type: 'uint256' },
          { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
          { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
          {
            name: 'maxTaskExecutionCount',
            internalType: 'uint256',
            type: 'uint256',
          },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'userAddr', internalType: 'address', type: 'address' },
      { name: 'offset', internalType: 'uint256', type: 'uint256' },
      { name: 'amount', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getSessionsByAddressByPage',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.Session[]',
        type: 'tuple[]',
        components: [
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'sid', internalType: 'bytes32', type: 'bytes32' },
          { name: 'name', internalType: 'string', type: 'string' },
          { name: 'metadata', internalType: 'string', type: 'string' },
          {
            name: 'state',
            internalType: 'enum SessionV2.SessionState',
            type: 'uint8',
          },
          { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
          { name: 'updatedAt', internalType: 'uint256', type: 'uint256' },
          { name: 'owner', internalType: 'address', type: 'address' },
          {
            name: 'ephemeralNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          {
            name: 'dedicatedNodes',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'mode', internalType: 'uint256', type: 'uint256' },
          { name: 'redundant', internalType: 'uint256', type: 'uint256' },
          { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
          { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
          {
            name: 'numOfValidatorNodes',
            internalType: 'uint256',
            type: 'uint256',
          },
          {
            name: 'routerMetadatas',
            internalType: 'string[]',
            type: 'string[]',
          },
          {
            name: 'routerAddresses',
            internalType: 'address[]',
            type: 'address[]',
          },
          { name: 'sla', internalType: 'uint256', type: 'uint256' },
          { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
          { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
          {
            name: 'maxTaskExecutionCount',
            internalType: 'uint256',
            type: 'uint256',
          },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'userAddr', internalType: 'address', type: 'address' }],
    name: 'getSessionsIdsByAddress',
    outputs: [{ name: '', internalType: 'uint256[]', type: 'uint256[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskRequset',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.TaskRequest',
        type: 'tuple',
        components: [
          { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'gid', internalType: 'uint256', type: 'uint256' },
          { name: 'requestDate', internalType: 'uint256', type: 'uint256' },
          { name: 'completed', internalType: 'bool', type: 'bool' },
          { name: 'data', internalType: 'string', type: 'string' },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskId', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'getTaskResults',
    outputs: [
      { name: '', internalType: 'address[]', type: 'address[]' },
      { name: '', internalType: 'string[]', type: 'string[]' },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'user', internalType: 'address', type: 'address' }],
    name: 'getUserSessions',
    outputs: [{ name: '', internalType: 'uint256[]', type: 'uint256[]' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'nodeAddress', internalType: 'address', type: 'address' }],
    name: 'isNodeAssignedToAnySession',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'address', type: 'address' }],
    name: 'isNodeInSessions',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'addr', internalType: 'address', type: 'address' }],
    name: 'isOracleNode',
    outputs: [{ name: '', internalType: 'bool', type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'bytes32', type: 'bytes32' }],
    name: 'nodeIdToAddress',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'address', type: 'address' }],
    name: 'nodeToSessionId',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [],
    name: 'owner',
    outputs: [{ name: '', internalType: 'address', type: 'address' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'nodeId', internalType: 'bytes32', type: 'bytes32' }],
    name: 'releaseByNodeId',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'nodeAddress', internalType: 'address', type: 'address' },
    ],
    name: 'removeDedicatedNode',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'routerAddress', internalType: 'address', type: 'address' },
    ],
    name: 'removeRouter',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [],
    name: 'renounceOwnership',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: 'sessionId', internalType: 'uint256', type: 'uint256' }],
    name: 'resetAllRouters',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    name: 'sessionTaskRequestCount',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    name: 'sessions',
    outputs: [
      { name: 'id', internalType: 'uint256', type: 'uint256' },
      { name: 'sid', internalType: 'bytes32', type: 'bytes32' },
      { name: 'name', internalType: 'string', type: 'string' },
      { name: 'metadata', internalType: 'string', type: 'string' },
      {
        name: 'state',
        internalType: 'enum SessionV2.SessionState',
        type: 'uint8',
      },
      { name: 'createdAt', internalType: 'uint256', type: 'uint256' },
      { name: 'updatedAt', internalType: 'uint256', type: 'uint256' },
      { name: 'owner', internalType: 'address', type: 'address' },
      { name: 'mode', internalType: 'uint256', type: 'uint256' },
      { name: 'redundant', internalType: 'uint256', type: 'uint256' },
      { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'numOfValidatorNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'sla', internalType: 'uint256', type: 'uint256' },
      { name: 'modelIdentifier', internalType: 'uint256', type: 'uint256' },
      { name: 'reservePeriod', internalType: 'uint256', type: 'uint256' },
      {
        name: 'maxTaskExecutionCount',
        internalType: 'uint256',
        type: 'uint256',
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [
      { name: '_aclContract', internalType: 'address', type: 'address' },
    ],
    name: 'setACL',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_iamContract', internalType: 'address', type: 'address' },
    ],
    name: 'setIAM',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [{ name: '_nodePool', internalType: 'address', type: 'address' }],
    name: 'setNodePool',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_sessionAuth', internalType: 'address', type: 'address' },
    ],
    name: 'setSessionAuth',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_sessionPayment', internalType: 'address', type: 'address' },
    ],
    name: 'setSessionPayment',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      {
        name: '_sessionQueueContrat',
        internalType: 'address',
        type: 'address',
      },
    ],
    name: 'setSessionQueue',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '_sessionStats', internalType: 'address', type: 'address' },
    ],
    name: 'setSessionStats',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'taskData', internalType: 'string', type: 'string' },
    ],
    name: 'storeTaskRequest',
    outputs: [
      {
        name: '',
        internalType: 'struct SessionV2.TaskRequest',
        type: 'tuple',
        components: [
          { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
          { name: 'id', internalType: 'uint256', type: 'uint256' },
          { name: 'gid', internalType: 'uint256', type: 'uint256' },
          { name: 'requestDate', internalType: 'uint256', type: 'uint256' },
          { name: 'completed', internalType: 'bool', type: 'bool' },
          { name: 'data', internalType: 'string', type: 'string' },
        ],
      },
    ],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'nodeType', internalType: 'uint256', type: 'uint256' },
      { name: 'taskData', internalType: 'string', type: 'string' },
      { name: 'promptType', internalType: 'uint256', type: 'uint256' },
      { name: 'promptTemplate', internalType: 'string', type: 'string' },
      { name: 'llmParams', internalType: 'uint256[]', type: 'uint256[]' },
      { name: 'clientReference', internalType: 'string', type: 'string' },
    ],
    name: 'submit',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '', internalType: 'uint256', type: 'uint256' },
      { name: '', internalType: 'address', type: 'address' },
    ],
    name: 'taskCountPerNode',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    inputs: [{ name: 'newOwner', internalType: 'address', type: 'address' }],
    name: 'transferOwnership',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'name', internalType: 'string', type: 'string' },
      { name: 'metadata', internalType: 'string', type: 'string' },
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'minNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'maxNumOfNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'redundant', internalType: 'uint256', type: 'uint256' },
      { name: 'numOfValidatorNodes', internalType: 'uint256', type: 'uint256' },
      { name: 'mode', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'update',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'newOwner', internalType: 'address', type: 'address' },
    ],
    name: 'updateOwner',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: 'sessionId', internalType: 'uint256', type: 'uint256' },
      { name: 'routerAddress', internalType: 'address', type: 'address' },
      { name: 'newRouterInfo', internalType: 'string', type: 'string' },
    ],
    name: 'updateRouter',
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    inputs: [
      { name: '', internalType: 'address', type: 'address' },
      { name: '', internalType: 'uint256', type: 'uint256' },
    ],
    name: 'userSessions',
    outputs: [{ name: '', internalType: 'uint256', type: 'uint256' }],
    stateMutability: 'view',
  },
] as const

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const sessionV2Address = {
  421614: '0x2f1380ba4eFBE866C811862e50923585b31EA03B',
} as const

/**
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const sessionV2Config = {
  address: sessionV2Address,
  abi: sessionV2Abi,
} as const

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// React
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2 = /*#__PURE__*/ createUseReadContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getACLAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetAclAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getACLAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getAllTaskResultAckedTimestamps"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetAllTaskResultAckedTimestamps =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getAllTaskResultAckedTimestamps',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getAllTaskResultCommitTimestamps"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetAllTaskResultCommitTimestamps =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getAllTaskResultCommitTimestamps',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getAllTaskResultPrecommitTimestamps"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetAllTaskResultPrecommitTimestamps =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getAllTaskResultPrecommitTimestamps',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getAllTaskResults"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetAllTaskResults =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getAllTaskResults',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getHash"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetHash = /*#__PURE__*/ createUseReadContract(
  {
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getHash',
  },
)

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getIAMAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetIamAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getIAMAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getLatestTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetLatestTask =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getLatestTask',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getNodeId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetNodeId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getNodeId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getNodePoolAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetNodePoolAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getNodePoolAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getNodeReputationAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetNodeReputationAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getNodeReputationAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getNodeStatsAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetNodeStatsAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getNodeStatsAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getSessionQueueValidationAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetSessionQueueValidationAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getSessionQueueValidationAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getSessionReputationAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetSessionReputationAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getSessionReputationAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getSessionStatsAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetSessionStatsAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getSessionStatsAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskCountBySessionId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskCountBySessionId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskCountBySessionId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskCountBySessionIds"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskCountBySessionIds =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskCountBySessionIds',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskData"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskData =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskData',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecoration"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecoration =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecoration',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationFrequencyPenalty"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationFrequencyPenalty =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationFrequencyPenalty',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationMaxTokens"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationMaxTokens =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationMaxTokens',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationPresencePenalty"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationPresencePenalty =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationPresencePenalty',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationPromptTemplate"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationPromptTemplate =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationPromptTemplate',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationPromptType"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationPromptType =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationPromptType',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationTemperature"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationTemperature =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationTemperature',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationTopK"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationTopK =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationTopK',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskDecorationTopP"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskDecorationTopP =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskDecorationTopP',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResultCommitTimestamp"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResultCommitTimestamp =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResultCommitTimestamp',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResultData"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResultData =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResultData',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResultHashes"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResultHashes =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResultHashes',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResultPrecommitTimestamp"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResultPrecommitTimestamp =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResultPrecommitTimestamp',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResultState"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResultState =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResultState',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskResults"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskResults =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskResults',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTaskStatus"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTaskStatus =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTaskStatus',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getTasksBySessionId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetTasksBySessionId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getTasksBySessionId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"getUseSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2GetUseSessionStats =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'getUseSessionStats',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"isAcked"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2IsAcked = /*#__PURE__*/ createUseReadContract(
  {
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'isAcked',
  },
)

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"isOracleNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2IsOracleNode =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'isOracleNode',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"isPrimaryModule"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2IsPrimaryModule =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'isPrimaryModule',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"owner"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2Owner = /*#__PURE__*/ createUseReadContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
  functionName: 'owner',
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"sessionTaskCount"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2SessionTaskCount =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'sessionTaskCount',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"sessionTaskDecorations"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2SessionTaskDecorations =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'sessionTaskDecorations',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"sessionTaskResults"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2SessionTaskResults =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'sessionTaskResults',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"sessionTasks"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2SessionTasks =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'sessionTasks',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"subversion"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2Subversion =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'subversion',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"useSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2UseSessionStats =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'useSessionStats',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"verifyHash"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2VerifyHash =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'verifyHash',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"version"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useReadSessionQueueV2Version = /*#__PURE__*/ createUseReadContract(
  {
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'version',
  },
)

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2 = /*#__PURE__*/ createUseWriteContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"ack"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2Ack = /*#__PURE__*/ createUseWriteContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
  functionName: 'ack',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"assignTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2AssignTask =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'assignTask',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"commit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2Commit =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'commit',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"end"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2End = /*#__PURE__*/ createUseWriteContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
  functionName: 'end',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"end2"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2End2 = /*#__PURE__*/ createUseWriteContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
  functionName: 'end2',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endAck"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2EndAck =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endAck',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endCommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2EndCommit =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endCommit',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endPrecommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2EndPrecommit =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endPrecommit',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"enqueueTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2EnqueueTask =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'enqueueTask',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"pop"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2Pop = /*#__PURE__*/ createUseWriteContract({
  abi: sessionQueueV2Abi,
  address: sessionQueueV2Address,
  functionName: 'pop',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"popSpecificTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2PopSpecificTask =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'popSpecificTask',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"precommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2Precommit =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'precommit',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"renounceOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2RenounceOwnership =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'renounceOwnership',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setACL"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetAcl =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setACL',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setIAM"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetIam =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setIAM',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodePool"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetNodePool =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodePool',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodeReputation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetNodeReputation =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodeReputation',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodeStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetNodeStats =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodeStats',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionQueueValidation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetSessionQueueValidation =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionQueueValidation',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionReputation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetSessionReputation =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionReputation',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetSessionStats =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionStats',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setUseSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2SetUseSessionStats =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setUseSessionStats',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"transferOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWriteSessionQueueV2TransferOwnership =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'transferOwnership',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2 =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"ack"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2Ack =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'ack',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"assignTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2AssignTask =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'assignTask',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"commit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2Commit =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'commit',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"end"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2End =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'end',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"end2"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2End2 =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'end2',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endAck"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2EndAck =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endAck',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endCommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2EndCommit =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endCommit',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"endPrecommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2EndPrecommit =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'endPrecommit',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"enqueueTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2EnqueueTask =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'enqueueTask',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"pop"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2Pop =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'pop',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"popSpecificTask"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2PopSpecificTask =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'popSpecificTask',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"precommit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2Precommit =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'precommit',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"renounceOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2RenounceOwnership =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'renounceOwnership',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setACL"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetAcl =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setACL',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setIAM"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetIam =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setIAM',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodePool"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetNodePool =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodePool',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodeReputation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetNodeReputation =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodeReputation',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setNodeStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetNodeStats =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setNodeStats',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionQueueValidation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetSessionQueueValidation =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionQueueValidation',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionReputation"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetSessionReputation =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionReputation',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetSessionStats =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setSessionStats',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"setUseSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2SetUseSessionStats =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'setUseSessionStats',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `functionName` set to `"transferOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useSimulateSessionQueueV2TransferOwnership =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    functionName: 'transferOwnership',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2Event =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"OwnershipTransferred"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2OwnershipTransferredEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'OwnershipTransferred',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskAcked"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskAckedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskAcked',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskAllCommitted"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskAllCommittedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskAllCommitted',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskAllPrecommitted"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskAllPrecommittedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskAllPrecommitted',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskAssigned"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskAssignedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskAssigned',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskCommitEnded"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskCommitEndedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskCommitEnded',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskCommitted"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskCommittedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskCommitted',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskEnded"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskEndedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskEnded',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskPrecommitEnded"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskPrecommitEndedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskPrecommitEnded',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskPrecommitted"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskPrecommittedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskPrecommitted',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionQueueV2Abi}__ and `eventName` set to `"TaskQueued"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2fCC55699048eD2e22fe46b1dD45557024fD1836)
 */
export const useWatchSessionQueueV2TaskQueuedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionQueueV2Abi,
    address: sessionQueueV2Address,
    eventName: 'TaskQueued',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2 = /*#__PURE__*/ createUseReadContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"allNodeAddresses"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2AllNodeAddresses =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'allNodeAddresses',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"doesSessionExist"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2DoesSessionExist =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'doesSessionExist',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getACLAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetAclAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getACLAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getActiveSessionsByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetActiveSessionsByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getActiveSessionsByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getIAMAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetIamAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getIAMAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getLatestRouterAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetLatestRouterAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getLatestRouterAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getLatestRouterIndex"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetLatestRouterIndex =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getLatestRouterIndex',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getLatestRouterInfo"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetLatestRouterInfo =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getLatestRouterInfo',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getLatestSessionId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetLatestSessionId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getLatestSessionId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getLatestTaskRequest"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetLatestTaskRequest =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getLatestTaskRequest',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getNodeAssignedTimestamp"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetNodeAssignedTimestamp =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getNodeAssignedTimestamp',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getNodeId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetNodeId = /*#__PURE__*/ createUseReadContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'getNodeId',
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getNodePoolAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetNodePoolAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getNodePoolAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getNodeSessionId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetNodeSessionId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getNodeSessionId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterCount"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterCount =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterCount',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterIndex"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterIndex =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterIndex',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterInfo"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterInfo =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterInfo',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterMetadatasByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterMetadatasByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterMetadatasByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getRouterMetadatasBySessionIds"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetRouterMetadatasBySessionIds =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getRouterMetadatasBySessionIds',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSession"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSession = /*#__PURE__*/ createUseReadContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'getSession',
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionAuthAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionAuthAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionAuthAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionCount"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionCount =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionCount',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionCountByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionCountByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionCountByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionIdAndNameAndMetadataByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionIdAndNameAndMetadataByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionIdAndNameAndMetadataByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionIds"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionIds =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionIds',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionPaymentAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionPaymentAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionPaymentAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionQueueAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionQueueAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionQueueAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionStatsAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionStatsAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionStatsAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionsByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionsByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionsByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionsByAddressByPage"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionsByAddressByPage =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionsByAddressByPage',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getSessionsIdsByAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetSessionsIdsByAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getSessionsIdsByAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getTaskRequset"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetTaskRequset =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getTaskRequset',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getTaskResults"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetTaskResults =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getTaskResults',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"getUserSessions"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2GetUserSessions =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'getUserSessions',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"isNodeAssignedToAnySession"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2IsNodeAssignedToAnySession =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'isNodeAssignedToAnySession',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"isNodeInSessions"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2IsNodeInSessions =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'isNodeInSessions',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"isOracleNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2IsOracleNode = /*#__PURE__*/ createUseReadContract(
  {
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'isOracleNode',
  },
)

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"nodeIdToAddress"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2NodeIdToAddress =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'nodeIdToAddress',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"nodeToSessionId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2NodeToSessionId =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'nodeToSessionId',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"owner"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2Owner = /*#__PURE__*/ createUseReadContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'owner',
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"sessionTaskRequestCount"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2SessionTaskRequestCount =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'sessionTaskRequestCount',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"sessions"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2Sessions = /*#__PURE__*/ createUseReadContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'sessions',
})

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"taskCountPerNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2TaskCountPerNode =
  /*#__PURE__*/ createUseReadContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'taskCountPerNode',
  })

/**
 * Wraps __{@link useReadContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"userSessions"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useReadSessionV2UserSessions = /*#__PURE__*/ createUseReadContract(
  {
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'userSessions',
  },
)

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2 = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"addDedicatedNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2AddDedicatedNode =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'addDedicatedNode',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"addRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2AddRouter = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'addRouter',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"create"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2Create = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'create',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"deactivateSession"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2DeactivateSession =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'deactivateSession',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"releaseByNodeId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2ReleaseByNodeId =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'releaseByNodeId',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"removeDedicatedNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2RemoveDedicatedNode =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'removeDedicatedNode',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"removeRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2RemoveRouter =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'removeRouter',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"renounceOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2RenounceOwnership =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'renounceOwnership',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"resetAllRouters"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2ResetAllRouters =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'resetAllRouters',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setACL"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetAcl = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'setACL',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setIAM"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetIam = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'setIAM',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setNodePool"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetNodePool =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setNodePool',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionAuth"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetSessionAuth =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionAuth',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionPayment"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetSessionPayment =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionPayment',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionQueue"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetSessionQueue =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionQueue',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2SetSessionStats =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionStats',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"storeTaskRequest"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2StoreTaskRequest =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'storeTaskRequest',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"submit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2Submit = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'submit',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"transferOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2TransferOwnership =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'transferOwnership',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"update"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2Update = /*#__PURE__*/ createUseWriteContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
  functionName: 'update',
})

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"updateOwner"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2UpdateOwner =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'updateOwner',
  })

/**
 * Wraps __{@link useWriteContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"updateRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWriteSessionV2UpdateRouter =
  /*#__PURE__*/ createUseWriteContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'updateRouter',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2 = /*#__PURE__*/ createUseSimulateContract({
  abi: sessionV2Abi,
  address: sessionV2Address,
})

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"addDedicatedNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2AddDedicatedNode =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'addDedicatedNode',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"addRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2AddRouter =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'addRouter',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"create"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2Create =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'create',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"deactivateSession"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2DeactivateSession =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'deactivateSession',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"releaseByNodeId"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2ReleaseByNodeId =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'releaseByNodeId',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"removeDedicatedNode"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2RemoveDedicatedNode =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'removeDedicatedNode',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"removeRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2RemoveRouter =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'removeRouter',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"renounceOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2RenounceOwnership =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'renounceOwnership',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"resetAllRouters"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2ResetAllRouters =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'resetAllRouters',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setACL"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetAcl =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setACL',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setIAM"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetIam =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setIAM',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setNodePool"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetNodePool =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setNodePool',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionAuth"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetSessionAuth =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionAuth',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionPayment"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetSessionPayment =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionPayment',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionQueue"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetSessionQueue =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionQueue',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"setSessionStats"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2SetSessionStats =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'setSessionStats',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"storeTaskRequest"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2StoreTaskRequest =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'storeTaskRequest',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"submit"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2Submit =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'submit',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"transferOwnership"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2TransferOwnership =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'transferOwnership',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"update"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2Update =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'update',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"updateOwner"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2UpdateOwner =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'updateOwner',
  })

/**
 * Wraps __{@link useSimulateContract}__ with `abi` set to __{@link sessionV2Abi}__ and `functionName` set to `"updateRouter"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useSimulateSessionV2UpdateRouter =
  /*#__PURE__*/ createUseSimulateContract({
    abi: sessionV2Abi,
    address: sessionV2Address,
    functionName: 'updateRouter',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2Event = /*#__PURE__*/ createUseWatchContractEvent(
  { abi: sessionV2Abi, address: sessionV2Address },
)

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"AllRoutersRemoved"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2AllRoutersRemovedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'AllRoutersRemoved',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"DedicatedNodeAdded"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2DedicatedNodeAddedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'DedicatedNodeAdded',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"DedicatedNodeRemoved"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2DedicatedNodeRemovedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'DedicatedNodeRemoved',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"NewNodeAssignedToSession"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2NewNodeAssignedToSessionEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'NewNodeAssignedToSession',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"NodeReleased"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2NodeReleasedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'NodeReleased',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"OwnershipTransferred"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2OwnershipTransferredEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'OwnershipTransferred',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"RouterAdded"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2RouterAddedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'RouterAdded',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"RouterRemoved"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2RouterRemovedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'RouterRemoved',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"RouterUpdated"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2RouterUpdatedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'RouterUpdated',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"SessionCreated"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2SessionCreatedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'SessionCreated',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"SessionDeactivated"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2SessionDeactivatedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'SessionDeactivated',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"SessionUpdated"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2SessionUpdatedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'SessionUpdated',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"TaskAssigned"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2TaskAssignedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'TaskAssigned',
  })

/**
 * Wraps __{@link useWatchContractEvent}__ with `abi` set to __{@link sessionV2Abi}__ and `eventName` set to `"TaskSubmitted"`
 *
 * [__View Contract on Arbitrum Sepolia Arbiscan__](https://sepolia.arbiscan.io/address/0x2f1380ba4eFBE866C811862e50923585b31EA03B)
 */
export const useWatchSessionV2TaskSubmittedEvent =
  /*#__PURE__*/ createUseWatchContractEvent({
    abi: sessionV2Abi,
    address: sessionV2Address,
    eventName: 'TaskSubmitted',
  })
