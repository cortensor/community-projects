// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {console} from "forge-std/console.sol";
import {CortexAgenticProof} from "../src/CortexAgenticProof.sol";

contract DeployScript is Script {
    function run() external {
        // Pull the deployer private key securely
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Broadcast tx on Base Sepolia
        vm.startBroadcast(deployerPrivateKey);

        CortexAgenticProof proofContract = new CortexAgenticProof();

        vm.stopBroadcast();

        // Print deployment address for frontend insertion
        console.log("CortexAgenticProof deployed at:", address(proofContract));
    }
}
