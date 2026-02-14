// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/ICOR.sol";

/**
 * @title ReputationRegistry
 * @dev Maintains on-chain reputation records for miners, judges, and challengers
 * Implements ERC-8004 compatible agent identity and reputation tracking
 * 
 * Features:
 * - Tracks historical verdicts and outcomes
 * - Calculates reputation scores dynamically
 * - Manages agent badges and certifications
 * - Integrates with Justice contract for verdict updates
 */
contract ReputationRegistry {

    // ==================== Type Definitions ====================

    enum AgentType {
        MINER,
        JUDGE,
        CHALLENGER
    }

    enum BadgeType {
        TRUSTED_MINER,           // >80% accuracy
        ELITE_JUDGE,             // >90% accuracy, high reputation
        BOUNTY_HUNTER,           // Successful challenger
        SAFETY_VALIDATOR,        // Specialized in safety checks
        CONSENSUS_VALIDATOR      // Multiple correct verdicts
    }

    struct AgentRecord {
        address agent;
        AgentType agentType;
        string agentMetadata;    // IPFS hash or URL to agent info
        uint256 createdAt;
        uint256 successCount;
        uint256 failureCount;
        uint256 totalVerdicts;
        uint256 reputationScore;  // 0-10000
        mapping(BadgeType => bool) badges;
        bool isActive;
    }

    struct VerdictRecord {
        uint256 disputeId;
        address agent;
        VerdictOutcome outcome;
        uint256 timestamp;
        string reasoning; // IPFS hash
    }

    enum VerdictOutcome {
        CORRECT,
        INCORRECT,
        INSUFFICIENT_DATA,
        APPEALED
    }

    // ==================== State Variables ====================

    address public owner;
    address public justiceContract;
    ICOR public corToken;

    // Agent records
    mapping(address => AgentRecord) public agents;
    address[] public registeredAgents;

    // Verdict history
    mapping(address => VerdictRecord[]) public agentVerdicts;
    
    // Badge requirements
    uint256 public trustedMinerThreshold = 8000;        // 80% accuracy
    uint256 public eliteJudgeThreshold = 9000;          // 90% accuracy
    uint256 public bountyHunterThreshold = 5;           // 5 successful challenges

    // Reputation calculations
    uint256 public successWeight = 10;
    uint256 public failureWeight = 5;
    uint256 public baseReputation = 5000;

    // ==================== Events ====================

    event AgentRegistered(
        address indexed agent,
        AgentType agentType,
        string metadata
    );

    event VerdictRecorded(
        address indexed agent,
        uint256 indexed disputeId,
        VerdictOutcome outcome
    );

    event BadgeAwarded(
        address indexed agent,
        BadgeType badge
    );

    event BadgeRevoked(
        address indexed agent,
        BadgeType badge
    );

    event ReputationUpdated(
        address indexed agent,
        uint256 newScore,
        uint256 successCount,
        uint256 failureCount
    );

    event AgentDeactivated(
        address indexed agent,
        string reason
    );

    // ==================== Modifiers ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyJusticeContract() {
        require(msg.sender == justiceContract, "Only Justice contract");
        _;
    }

    modifier onlyRegistered(address _agent) {
        require(agents[_agent].agent != address(0), "Agent not registered");
        _;
    }

    // ==================== Constructor ====================

    constructor(address _corToken) {
        require(_corToken != address(0), "Invalid token address");
        corToken = ICOR(_corToken);
        owner = msg.sender;
    }

    // ==================== Agent Registration ====================

    /**
     * @dev Register a new agent (miner, judge, or challenger)
     * @param _agentType Type of agent
     * @param _metadata IPFS hash or metadata URL
     */
    function registerAgent(
        AgentType _agentType,
        string calldata _metadata
    ) external returns (address) {
        require(agents[msg.sender].agent == address(0), "Already registered");
        require(bytes(_metadata).length > 0, "Metadata required");

        AgentRecord storage record = agents[msg.sender];
        record.agent = msg.sender;
        record.agentType = _agentType;
        record.agentMetadata = _metadata;
        record.createdAt = block.timestamp;
        record.reputationScore = baseReputation;
        record.isActive = true;

        registeredAgents.push(msg.sender);

        emit AgentRegistered(msg.sender, _agentType, _metadata);
        return msg.sender;
    }

    /**
     * @dev Register agent via Justice contract (only during challenge)
     */
    function registerAgentViaJustice(
        address _agent,
        AgentType _agentType,
        string calldata _metadata
    ) external onlyJusticeContract {
        if (agents[_agent].agent == address(0)) {
            AgentRecord storage record = agents[_agent];
            record.agent = _agent;
            record.agentType = _agentType;
            record.agentMetadata = _metadata;
            record.createdAt = block.timestamp;
            record.reputationScore = baseReputation;
            record.isActive = true;
            registeredAgents.push(_agent);

            emit AgentRegistered(_agent, _agentType, _metadata);
        }
    }

    // ==================== Verdict Recording ====================

    /**
     * @dev Record a verdict outcome for an agent
     * Called by Justice contract after verdict is issued
     */
    function recordVerdict(
        address _agent,
        uint256 _disputeId,
        VerdictOutcome _outcome,
        string calldata _reasoning
    ) external onlyJusticeContract onlyRegistered(_agent) {
        AgentRecord storage record = agents[_agent];

        VerdictRecord memory verdict = VerdictRecord({
            disputeId: _disputeId,
            agent: _agent,
            outcome: _outcome,
            timestamp: block.timestamp,
            reasoning: _reasoning
        });

        agentVerdicts[_agent].push(verdict);

        // Update counts
        if (_outcome == VerdictOutcome.CORRECT) {
            record.successCount++;
        } else if (_outcome == VerdictOutcome.INCORRECT) {
            record.failureCount++;
        }
        record.totalVerdicts++;

        // Recalculate reputation
        _updateReputation(_agent);

        // Check and award badges
        _evaluateAndAwardBadges(_agent);

        emit VerdictRecorded(_agent, _disputeId, _outcome);
    }

    // ==================== Reputation Management ====================

    /**
     * @dev Update reputation score based on success/failure ratio
     */
    function _updateReputation(address _agent) internal {
        AgentRecord storage record = agents[_agent];
        
        if (record.totalVerdicts == 0) return;

        // Scale to 0-10000 range
        uint256 accuracy = (record.successCount * 10000) / record.totalVerdicts;
        record.reputationScore = (baseReputation + accuracy) / 2;

        // Cap at 10000
        if (record.reputationScore > 10000) {
            record.reputationScore = 10000;
        }

        emit ReputationUpdated(
            _agent,
            record.reputationScore,
            record.successCount,
            record.failureCount
        );
    }

    /**
     * @dev Evaluate and award badges to agents
     */
    function _evaluateAndAwardBadges(address _agent) internal {
        AgentRecord storage record = agents[_agent];

        // Trusted Miner Badge
        if (
            record.agentType == AgentType.MINER &&
            record.reputationScore >= trustedMinerThreshold &&
            !record.badges[BadgeType.TRUSTED_MINER]
        ) {
            record.badges[BadgeType.TRUSTED_MINER] = true;
            emit BadgeAwarded(_agent, BadgeType.TRUSTED_MINER);
        }

        // Elite Judge Badge
        if (
            record.agentType == AgentType.JUDGE &&
            record.reputationScore >= eliteJudgeThreshold &&
            !record.badges[BadgeType.ELITE_JUDGE]
        ) {
            record.badges[BadgeType.ELITE_JUDGE] = true;
            emit BadgeAwarded(_agent, BadgeType.ELITE_JUDGE);
        }

        // Bounty Hunter Badge
        if (
            record.agentType == AgentType.CHALLENGER &&
            record.successCount >= bountyHunterThreshold &&
            !record.badges[BadgeType.BOUNTY_HUNTER]
        ) {
            record.badges[BadgeType.BOUNTY_HUNTER] = true;
            emit BadgeAwarded(_agent, BadgeType.BOUNTY_HUNTER);
        }

        // Safety Validator Badge
        if (
            record.agentType == AgentType.JUDGE &&
            record.successCount >= 10 &&
            record.reputationScore >= 7500 &&
            !record.badges[BadgeType.SAFETY_VALIDATOR]
        ) {
            record.badges[BadgeType.SAFETY_VALIDATOR] = true;
            emit BadgeAwarded(_agent, BadgeType.SAFETY_VALIDATOR);
        }

        // Consensus Validator Badge
        if (
            record.agentType == AgentType.JUDGE &&
            record.successCount >= 20 &&
            !record.badges[BadgeType.CONSENSUS_VALIDATOR]
        ) {
            record.badges[BadgeType.CONSENSUS_VALIDATOR] = true;
            emit BadgeAwarded(_agent, BadgeType.CONSENSUS_VALIDATOR);
        }
    }

    /**
     * @dev Revoke a badge from an agent
     */
    function revokeBadge(address _agent, BadgeType _badge) 
        external 
        onlyOwner 
        onlyRegistered(_agent) 
    {
        agents[_agent].badges[_badge] = false;
        emit BadgeRevoked(_agent, _badge);
    }

    // ==================== View Functions ====================

    /**
     * @dev Get agent reputation record
     */
    function getAgentRecord(address _agent) 
        external 
        view 
        returns (
            address agent,
            AgentType agentType,
            uint256 successCount,
            uint256 failureCount,
            uint256 totalVerdicts,
            uint256 reputationScore,
            bool isActive
        ) 
    {
        AgentRecord storage record = agents[_agent];
        return (
            record.agent,
            record.agentType,
            record.successCount,
            record.failureCount,
            record.totalVerdicts,
            record.reputationScore,
            record.isActive
        );
    }

    /**
     * @dev Get agent's verdict history
     */
    function getAgentVerdicts(address _agent) 
        external 
        view 
        returns (VerdictRecord[] memory) 
    {
        return agentVerdicts[_agent];
    }

    /**
     * @dev Check if agent has specific badge
     */
    function hasBadge(address _agent, BadgeType _badge) 
        external 
        view 
        returns (bool) 
    {
        return agents[_agent].badges[_badge];
    }

    /**
     * @dev Get agent's accuracy percentage
     */
    function getAccuracy(address _agent) 
        external 
        view 
        returns (uint256) 
    {
        AgentRecord storage record = agents[_agent];
        if (record.totalVerdicts == 0) return 0;
        return (record.successCount * 100) / record.totalVerdicts;
    }

    /**
     * @dev Get list of all registered agents
     */
    function getRegisteredAgents() 
        external 
        view 
        returns (address[] memory) 
    {
        return registeredAgents;
    }

    /**
     * @dev Check if agent is active
     */
    function isAgentActive(address _agent) 
        external 
        view 
        returns (bool) 
    {
        return agents[_agent].isActive;
    }

    // ==================== Admin Functions ====================

    /**
     * @dev Set Justice contract address
     */
    function setJusticeContract(address _justice) external onlyOwner {
        require(_justice != address(0), "Invalid address");
        justiceContract = _justice;
    }

    /**
     * @dev Update badge thresholds
     */
    function updateBadgeThresholds(
        uint256 _trustedMiner,
        uint256 _eliteJudge,
        uint256 _bountyHunter
    ) external onlyOwner {
        trustedMinerThreshold = _trustedMiner;
        eliteJudgeThreshold = _eliteJudge;
        bountyHunterThreshold = _bountyHunter;
    }

    /**
     * @dev Deactivate an agent
     */
    function deactivateAgent(address _agent, string calldata _reason) 
        external 
        onlyOwner 
        onlyRegistered(_agent) 
    {
        agents[_agent].isActive = false;
        emit AgentDeactivated(_agent, _reason);
    }

    /**
     * @dev Reactivate an agent
     */
    function reactivateAgent(address _agent) 
        external 
        onlyOwner 
        onlyRegistered(_agent) 
    {
        agents[_agent].isActive = true;
    }
}
