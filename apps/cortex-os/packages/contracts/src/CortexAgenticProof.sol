// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CortexAgenticProof
 * @dev Implements a custom ERC-8004 compatible truth bond registry.
 * Anchors the localized SHA-256 swarm execution hash with the remote Pinata IPFS CID.
 */
contract CortexAgenticProof {

    struct ExecutionProof {
        string ipfsCid;           // The Pinata JSON payload pointer
        bytes32 executionHash;    // The local cryptographically verified schema hash
        address validator;        // The user/wallet that confirmed the consensus
        uint256 timestamp;        // Immutable block creation time
    }

    uint256 public proofCounter;
    mapping(uint256 => ExecutionProof) public proofRegistry;

    event ProofMinted(uint256 indexed proofId, string ipfsCid, bytes32 executionHash, address indexed validator);

    /**
     * @dev Called by the frontend UI after the Swarm SSE completes and IPFS string generates.
     */
    function mintVerificationArtifact(string memory _ipfsCid, bytes32 _executionHash) external returns (uint256) {
        proofCounter++;
        
        proofRegistry[proofCounter] = ExecutionProof({
            ipfsCid: _ipfsCid,
            executionHash: _executionHash,
            validator: msg.sender,
            timestamp: block.timestamp
        });

        emit ProofMinted(proofCounter, _ipfsCid, _executionHash, msg.sender);
        
        return proofCounter;
    }

    /**
     * @dev Validates if a specific proof exists by iterating the mapping.
     */
    function verifyProof(uint256 _proofId) external view returns (ExecutionProof memory) {
        require(_proofId > 0 && _proofId <= proofCounter, "Proof ID does not exist.");
        return proofRegistry[_proofId];
    }
}
