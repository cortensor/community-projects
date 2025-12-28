// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/ICOR.sol";

/**
 * @title Justice
 * @dev The core smart contract for The Cortensor Judge
 * Handles dispute initiation, verdict submission, bond management, and slashing/rewards
 * 
 * Core Features:
 * - Initiates challenges with $COR bond escrow
 * - Manages the dispute window (challenge period)
 * - Executes verdict logic (slash miners, reward challengers)
 * - Stores IPFS hashes of evidence bundles
 * - Integrates with Reputation Registry
 * - ERC-8004 compatibility for Agent Identity
 */
contract Justice {
    
    // ==================== Type Definitions ====================
    
    enum DisputeStatus {
        PENDING,          // Waiting for challenge period to end
        CHALLENGED,       // Challenged by a sentinel or user
        UNDER_REVIEW,     // Under validator review (PoUW)
        VERDICT_REACHED,  // Judge has ruled
        SETTLED,          // Rewards/slashes executed
        DISMISSED         // Challenge rejected or timed out
    }

    enum VerdictType {
        NONE,
        MINER_CORRECT,    // Miner was right, challenger loses bond
        MINER_WRONG,      // Miner was wrong, slashed, challenger rewarded
        INSUFFICIENT_EVIDENCE
    }

    struct EvidenceBundle {
        string promptHash;        // Hash of original prompt
        string minerResult;       // The AI output being disputed
        string logicTrace;        // Chain-of-Thought explanation
        string poiHash;           // Proof of Inference signature
        string ipfsHash;          // IPFS hash of the full bundle
        uint256 modelId;          // Which model was used
        address miner;            // Who provided the inference
        uint256 timestamp;        // When the evidence was submitted
    }

    struct Dispute {
        uint256 id;
        EvidenceBundle evidence;
        address challenger;       // Who initiated the challenge
        uint256 challengeBond;    // $COR amount locked as bond
        DisputeStatus status;
        VerdictType verdict;
        address judge;            // Validator who issued verdict
        string verdictReasoning;  // IPFS hash of judge's reasoning
        uint256 startTime;        // When dispute was created
        uint256 settlementTime;   // When it was settled
        uint256 slashAmount;      // Amount slashed from miner
        uint256 rewardAmount;     // Amount rewarded to challenger
    }

    // ==================== State Variables ====================

    ICOR public corToken;
    address public owner;
    address public reputationRegistry;
    
    // Dispute management
    uint256 public disputeCounter;
    uint256 public challengeWindowDuration = 5 minutes;  // Production: 24 hours
    uint256 public minBond = 100 * 10**18;               // Min $COR bond (100 tokens)
    uint256 public maxBond = 10000 * 10**18;             // Max $COR bond (10k tokens)
    uint256 public slashPercentage = 20;                 // 20% of miner stake slashed
    uint256 public challengerRewardPercentage = 50;      // 50% of slashed amount to challenger
    
    // Authorized validators for PoUW verification
    mapping(address => bool) public validatorRegistry;
    mapping(address => uint256) public validatorReputation;
    
    // Core disputes storage
    mapping(uint256 => Dispute) public disputes;
    mapping(address => uint256[]) public minerDisputes;
    mapping(address => uint256[]) public challengerDisputes;
    
    // Miner trust scores (ERC-8004 integration)
    mapping(address => uint256) public minerTrustScore;  // 0-10000 scale
    mapping(address => bool) public isAgentIdentity;     // ERC-8004 registered
    
    // Fee management
    uint256 public platformFeePercentage = 2;            // 2% of rewards
    uint256 public accumulatedFees;

    // ==================== Events ====================

    event DisputeInitiated(
        uint256 indexed disputeId,
        address indexed challenger,
        address indexed miner,
        uint256 bond,
        string ipfsHash
    );

    event ChallengeWindowed(
        uint256 indexed disputeId,
        uint256 windowEndTime
    );

    event VerdictSubmitted(
        uint256 indexed disputeId,
        address indexed judge,
        VerdictType verdict,
        uint256 slashAmount,
        uint256 rewardAmount
    );

    event DisputeSettled(
        uint256 indexed disputeId,
        address indexed miner,
        address indexed challenger,
        uint256 slashAmount,
        uint256 rewardAmount
    );

    event BondRefunded(
        uint256 indexed disputeId,
        address indexed challenger,
        uint256 amount
    );

    event MinerSlashed(
        address indexed miner,
        uint256 amount,
        uint256 newTrustScore
    );

    event ValidatorRegistered(
        address indexed validator,
        uint256 initialReputation
    );

    event AgentIdentityRegistered(
        address indexed agent,
        string agentType // "miner", "judge", "challenger"
    );

    event FeeWithdrawn(
        address indexed owner,
        uint256 amount
    );

    // ==================== Modifiers ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    modifier onlyValidator() {
        require(validatorRegistry[msg.sender], "Not a registered validator");
        _;
    }

    modifier onlyValidDispute(uint256 _disputeId) {
        require(_disputeId > 0 && _disputeId <= disputeCounter, "Invalid dispute ID");
        _;
    }

    // ==================== Constructor ====================

    constructor(address _corToken) {
        require(_corToken != address(0), "Invalid COR token address");
        corToken = ICOR(_corToken);
        owner = msg.sender;
        minerTrustScore[address(0)] = 5000; // Default trust score
    }

    // ==================== Core Functions ====================

    /**
     * @dev Initiate a dispute/challenge against a miner's output
     * @param _evidence The evidence bundle containing prompt, result, logic trace, etc.
     * @param _bond The amount of $COR to lock as a challenge bond
     * @return disputeId The ID of the newly created dispute
     */
    function initiateChallenge(
        EvidenceBundle calldata _evidence,
        uint256 _bond
    ) external returns (uint256) {
        require(_bond >= minBond && _bond <= maxBond, "Bond amount out of range");
        require(bytes(_evidence.ipfsHash).length > 0, "IPFS hash required");
        require(bytes(_evidence.logicTrace).length > 0, "Logic trace required");
        require(_evidence.miner != address(0), "Invalid miner address");
        require(_evidence.miner != msg.sender, "Cannot challenge own evidence");

        // Transfer bond from challenger to contract
        require(
            corToken.transferFrom(msg.sender, address(this), _bond),
            "Bond transfer failed"
        );

        // Create new dispute
        uint256 disputeId = ++disputeCounter;
        Dispute storage dispute = disputes[disputeId];
        
        dispute.id = disputeId;
        dispute.evidence = _evidence;
        dispute.challenger = msg.sender;
        dispute.challengeBond = _bond;
        dispute.status = DisputeStatus.CHALLENGED;
        dispute.startTime = block.timestamp;

        // Track dispute relationships
        minerDisputes[_evidence.miner].push(disputeId);
        challengerDisputes[msg.sender].push(disputeId);

        emit DisputeInitiated(
            disputeId,
            msg.sender,
            _evidence.miner,
            _bond,
            _evidence.ipfsHash
        );

        emit ChallengeWindowed(
            disputeId,
            block.timestamp + challengeWindowDuration
        );

        return disputeId;
    }

    /**
     * @dev Submit verdict as an authorized validator (PoUW verification)
     * Uses deterministic policy testing to validate AI output quality
     * @param _disputeId The dispute ID
     * @param _verdict The verdict (MINER_CORRECT or MINER_WRONG)
     * @param _verdictReasoning IPFS hash of detailed reasoning
     */
    function submitVerdict(
        uint256 _disputeId,
        VerdictType _verdict,
        string calldata _verdictReasoning
    ) external onlyValidator onlyValidDispute(_disputeId) {
        Dispute storage dispute = disputes[_disputeId];
        
        require(
            dispute.status == DisputeStatus.CHALLENGED,
            "Dispute not in challenged status"
        );
        require(
            block.timestamp >= dispute.startTime + challengeWindowDuration,
            "Challenge window still open"
        );
        require(
            _verdict == VerdictType.MINER_CORRECT || _verdict == VerdictType.MINER_WRONG,
            "Invalid verdict type"
        );

        dispute.status = DisputeStatus.UNDER_REVIEW;
        dispute.judge = msg.sender;
        dispute.verdict = _verdict;
        dispute.verdictReasoning = _verdictReasoning;

        // Calculate rewards and slashes
        (uint256 slashAmount, uint256 rewardAmount) = _calculateOutcomes(dispute);
        dispute.slashAmount = slashAmount;
        dispute.rewardAmount = rewardAmount;

        emit VerdictSubmitted(
            _disputeId,
            msg.sender,
            _verdict,
            slashAmount,
            rewardAmount
        );
    }

    /**
     * @dev Execute the verdict and settle the dispute
     * Transfers slashed amount to challenger and updates trust scores
     * @param _disputeId The dispute ID to settle
     */
    function settleDispute(uint256 _disputeId) external onlyValidDispute(_disputeId) {
        Dispute storage dispute = disputes[_disputeId];
        
        require(
            dispute.status == DisputeStatus.UNDER_REVIEW,
            "Dispute not ready for settlement"
        );

        address miner = dispute.evidence.miner;

        if (dispute.verdict == VerdictType.MINER_WRONG) {
            // Slash the miner
            require(
                corToken.transfer(dispute.challenger, dispute.rewardAmount),
                "Reward transfer failed"
            );

            // Update miner trust score (decrease)
            uint256 newScore = (minerTrustScore[miner] > 1000) ? minerTrustScore[miner] - 1000 : 0;
            minerTrustScore[miner] = newScore;

            emit MinerSlashed(miner, dispute.slashAmount, newScore);
        } else if (dispute.verdict == VerdictType.MINER_CORRECT) {
            // Refund challenger bond (or partial if fee deducted)
            uint256 refundAmount = dispute.challengeBond;
            require(
                corToken.transfer(dispute.challenger, refundAmount),
                "Refund transfer failed"
            );

            // Update miner trust score (increase)
            uint256 newScore = (minerTrustScore[miner] < 9000) ? minerTrustScore[miner] + 500 : 10000;
            minerTrustScore[miner] = newScore;

            emit BondRefunded(_disputeId, dispute.challenger, refundAmount);
        }

        dispute.status = DisputeStatus.SETTLED;
        dispute.settlementTime = block.timestamp;

        emit DisputeSettled(
            _disputeId,
            miner,
            dispute.challenger,
            dispute.slashAmount,
            dispute.rewardAmount
        );
    }

    /**
     * @dev Register a validator node for PoUW verification
     * @param _validator The validator address
     * @param _initialReputation Starting reputation score
     */
    function registerValidator(
        address _validator,
        uint256 _initialReputation
    ) external onlyOwner {
        require(_validator != address(0), "Invalid validator address");
        validatorRegistry[_validator] = true;
        validatorReputation[_validator] = _initialReputation;
        emit ValidatorRegistered(_validator, _initialReputation);
    }

    /**
     * @dev Register an agent identity (ERC-8004 compatible)
     * Creates an on-chain identity with reputation tracking
     * @param _agentType Type of agent: "miner", "judge", "challenger"
     */
    function registerAgentIdentity(string calldata _agentType) external {
        require(
            keccak256(bytes(_agentType)) == keccak256(bytes("miner")) ||
            keccak256(bytes(_agentType)) == keccak256(bytes("judge")) ||
            keccak256(bytes(_agentType)) == keccak256(bytes("challenger")),
            "Invalid agent type"
        );

        isAgentIdentity[msg.sender] = true;
        minerTrustScore[msg.sender] = 5000; // Default starting score

        emit AgentIdentityRegistered(msg.sender, _agentType);
    }

    // ==================== View Functions ====================

    /**
     * @dev Get complete dispute details
     */
    function getDispute(uint256 _disputeId) 
        external 
        view 
        onlyValidDispute(_disputeId) 
        returns (Dispute memory) 
    {
        return disputes[_disputeId];
    }

    /**
     * @dev Get all disputes initiated by a miner
     */
    function getMinerDisputes(address _miner) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return minerDisputes[_miner];
    }

    /**
     * @dev Get all disputes initiated by a challenger
     */
    function getChallengerDisputes(address _challenger) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return challengerDisputes[_challenger];
    }

    /**
     * @dev Get miner's trust score (0-10000)
     */
    function getMinerTrustScore(address _miner) 
        external 
        view 
        returns (uint256) 
    {
        return minerTrustScore[_miner];
    }

    /**
     * @dev Check if an address is a registered validator
     */
    function isValidator(address _address) 
        external 
        view 
        returns (bool) 
    {
        return validatorRegistry[_address];
    }

    /**
     * @dev Check if an address has ERC-8004 identity
     */
    function hasAgentIdentity(address _agent) 
        external 
        view 
        returns (bool) 
    {
        return isAgentIdentity[_agent];
    }

    /**
     * @dev Calculate dispute outcomes (slash and reward amounts)
     */
    function calculateOutcomes(uint256 _disputeId) 
        external 
        view 
        onlyValidDispute(_disputeId) 
        returns (uint256 slashAmount, uint256 rewardAmount) 
    {
        return _calculateOutcomes(disputes[_disputeId]);
    }

    // ==================== Internal Functions ====================

    function _calculateOutcomes(Dispute storage _dispute) 
        internal 
        view 
        returns (uint256 slashAmount, uint256 rewardAmount) 
    {
        if (_dispute.verdict == VerdictType.MINER_WRONG) {
            // Slash comes from protocol collateral (in production, from staking)
            slashAmount = (1000 * 10**18); // Fixed slash amount for MVP
            rewardAmount = (slashAmount * challengerRewardPercentage) / 100;
        } else {
            slashAmount = 0;
            rewardAmount = 0;
        }
    }

    // ==================== Admin Functions ====================

    /**
     * @dev Update challenge window duration
     */
    function setChallengeWindowDuration(uint256 _duration) external onlyOwner {
        require(_duration > 0, "Duration must be positive");
        challengeWindowDuration = _duration;
    }

    /**
     * @dev Update bond limits
     */
    function setBondLimits(uint256 _minBond, uint256 _maxBond) external onlyOwner {
        require(_minBond < _maxBond, "Min must be less than max");
        minBond = _minBond;
        maxBond = _maxBond;
    }

    /**
     * @dev Update slash and reward percentages
     */
    function setSlashParameters(
        uint256 _slashPercentage,
        uint256 _challengerRewardPercentage
    ) external onlyOwner {
        require(_slashPercentage <= 100, "Slash percentage invalid");
        require(_challengerRewardPercentage <= 100, "Reward percentage invalid");
        slashPercentage = _slashPercentage;
        challengerRewardPercentage = _challengerRewardPercentage;
    }

    /**
     * @dev Withdraw accumulated platform fees
     */
    function withdrawFees() external onlyOwner {
        uint256 amount = accumulatedFees;
        accumulatedFees = 0;
        require(corToken.transfer(owner, amount), "Fee withdrawal failed");
        emit FeeWithdrawn(owner, amount);
    }

    /**
     * @dev Set reputation registry address (future integration)
     */
    function setReputationRegistry(address _registry) external onlyOwner {
        require(_registry != address(0), "Invalid registry address");
        reputationRegistry = _registry;
    }

    /**
     * @dev Emergency pause validator
     */
    function revokeValidator(address _validator) external onlyOwner {
        validatorRegistry[_validator] = false;
    }
}
