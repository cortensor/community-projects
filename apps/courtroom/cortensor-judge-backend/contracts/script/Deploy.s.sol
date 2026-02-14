// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../Justice.sol";
import "../ReputationRegistry.sol";

/**
 * @title DeployJudge
 * @dev Deployment script for The Cortensor Judge system
 * 
 * Usage:
 * forge script script/Deploy.s.sol:DeployJudge --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast
 */
contract DeployJudge is Script {

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);

        // Get COR token address from environment or use mock
        address corTokenAddress = vm.envAddress("COR_TOKEN_ADDRESS");
        require(corTokenAddress != address(0), "COR_TOKEN_ADDRESS not set");

        // Deploy Justice contract
        Justice justice = new Justice(corTokenAddress);
        console.log("Justice contract deployed at:", address(justice));

        // Deploy Reputation Registry
        ReputationRegistry reputationRegistry = new ReputationRegistry(corTokenAddress);
        console.log("ReputationRegistry deployed at:", address(reputationRegistry));

        // Link contracts
        reputationRegistry.setJusticeContract(address(justice));
        console.log("ReputationRegistry linked to Justice contract");

        // Register initial validators
        address validatorAddress = vm.envAddress("INITIAL_VALIDATOR_ADDRESS");
        if (validatorAddress != address(0)) {
            justice.registerValidator(validatorAddress, 8000);
            console.log("Initial validator registered at:", validatorAddress);
        }

        vm.stopBroadcast();

        console.log("\n=== Deployment Complete ===");
        console.log("Justice:", address(justice));
        console.log("ReputationRegistry:", address(reputationRegistry));
    }
}
