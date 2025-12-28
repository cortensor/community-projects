// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Justice.sol";
import "./ReputationRegistry.sol";

/**
 * @title DeployJudge
 * @dev Deployment helper for The Cortensor Judge system
 * 
 * This contract helps with deployment of Justice and ReputationRegistry contracts
 * 
 * Usage:
 * 1. With Foundry (recommended):
 *    forge script script/Deploy.s.sol:DeployJudge --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast
 * 
 * 2. Manual deployment:
 *    - Deploy Justice.sol with COR token address
 *    - Deploy ReputationRegistry.sol with COR token address
 *    - Call ReputationRegistry.setJusticeContract(justice_address)
 *    - Call Justice.registerValidator(validator_address, 8000)
 */
contract DeployJudge {
    
    address public justiceAddress;
    address public reputationRegistryAddress;
    address public corTokenAddress;
    address public initialValidatorAddress;

    event JusticeDeployed(address indexed justice);
    event ReputationRegistryDeployed(address indexed registry);
    event ValidatorRegistered(address indexed validator);

    /**
     * @dev Deploy both contracts and link them
     * @param _corTokenAddress Address of the COR token contract
     * @param _initialValidatorAddress Address of the initial validator
     */
    function deploy(
        address _corTokenAddress,
        address _initialValidatorAddress
    ) external returns (address, address) {
        require(_corTokenAddress != address(0), "COR_TOKEN_ADDRESS not set");

        // Deploy Justice contract
        Justice justice = new Justice(_corTokenAddress);
        justiceAddress = address(justice);
        emit JusticeDeployed(justiceAddress);

        // Deploy Reputation Registry
        ReputationRegistry reputationRegistry = new ReputationRegistry(_corTokenAddress);
        reputationRegistryAddress = address(reputationRegistry);
        emit ReputationRegistryDeployed(reputationRegistryAddress);

        // Link contracts
        reputationRegistry.setJusticeContract(justiceAddress);

        // Register initial validator if provided
        if (_initialValidatorAddress != address(0)) {
            justice.registerValidator(_initialValidatorAddress, 8000);
            emit ValidatorRegistered(_initialValidatorAddress);
        }

        corTokenAddress = _corTokenAddress;
        initialValidatorAddress = _initialValidatorAddress;

        return (justiceAddress, reputationRegistryAddress);
    }

    /**
     * @dev Get deployed contract addresses
     */
    function getDeployedAddresses()
        external
        view
        returns (
            address _justice,
            address _reputationRegistry,
            address _corToken
        )
    {
        return (justiceAddress, reputationRegistryAddress, corTokenAddress);
    }
}
