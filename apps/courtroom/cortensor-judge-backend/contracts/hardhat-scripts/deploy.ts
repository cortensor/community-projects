import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
  console.log("🚀 Deploying Cortensor Judge contracts to localhost...\n");

  const [deployer] = await ethers.getSigners();
  console.log("📝 Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.provider?.getBalance(deployer.address))?.toString());

  // Deploy Mock COR Token first (if not already deployed)
  console.log("\n1️⃣ Deploying Mock COR Token...");
  const CorToken = await ethers.getContractFactory("MockCORToken");
  const corToken = await CorToken.deploy();
  await corToken.waitForDeployment();
  const corTokenAddress = await corToken.getAddress();
  console.log("✅ COR Token deployed at:", corTokenAddress);

  // Mint tokens to deployer
  const mintAmount = ethers.parseUnits("1000000", 18);
  await corToken.mint(deployer.address, mintAmount);
  console.log("💰 Minted 1,000,000 COR tokens to deployer");

  // Deploy Justice contract
  console.log("\n2️⃣ Deploying Justice contract...");
  const Justice = await ethers.getContractFactory("Justice");
  const justice = await Justice.deploy(corTokenAddress);
  await justice.waitForDeployment();
  const justiceAddress = await justice.getAddress();
  console.log("✅ Justice contract deployed at:", justiceAddress);

  // Deploy ReputationRegistry contract
  console.log("\n3️⃣ Deploying ReputationRegistry contract...");
  const ReputationRegistry = await ethers.getContractFactory("ReputationRegistry");
  const reputationRegistry = await ReputationRegistry.deploy(corTokenAddress);
  await reputationRegistry.waitForDeployment();
  const reputationRegistryAddress = await reputationRegistry.getAddress();
  console.log("✅ ReputationRegistry deployed at:", reputationRegistryAddress);

  // Link contracts
  console.log("\n4️⃣ Linking contracts...");
  await reputationRegistry.setJusticeContract(justiceAddress);
  console.log("✅ ReputationRegistry linked to Justice");

  // Register initial validator
  console.log("\n5️⃣ Registering validator...");
  const validatorAddress = deployer.address;
  const initialReputation = ethers.parseUnits("8000", 0);
  await justice.registerValidator(validatorAddress, initialReputation);
  console.log("✅ Validator registered:", validatorAddress);

  // Approve bond tokens
  console.log("\n6️⃣ Approving COR tokens for bonds...");
  const bondApprovalAmount = ethers.parseUnits("1000000", 18);
  await corToken.approve(justiceAddress, bondApprovalAmount);
  console.log("✅ Approved 1,000,000 COR for bonds");

  // Save deployment addresses
  const deploymentInfo = {
    network: "localhost",
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      CORToken: corTokenAddress,
      Justice: justiceAddress,
      ReputationRegistry: reputationRegistryAddress,
    },
    initialized: {
      validatorRegistered: true,
      tokensApproved: true,
      contractsLinked: true,
    },
  };

  const deploymentPath = path.join(__dirname, "../deployments.json");
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("\n📄 Deployment info saved to:", deploymentPath);

  // Print environment variables for .env
  console.log("\n================================");
  console.log("📋 Add these to your .env file:");
  console.log("================================");
  console.log(`BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545`);
  console.log(`JUSTICE_CONTRACT_ADDRESS=${justiceAddress}`);
  console.log(`REPUTATION_REGISTRY_ADDRESS=${reputationRegistryAddress}`);
  console.log(`COR_TOKEN_ADDRESS=${corTokenAddress}`);
  console.log(`VALIDATOR_ADDRESS=${validatorAddress}`);
  console.log(`VALIDATOR_PRIVATE_KEY=0x${deployer.privateKey}`);
  console.log("================================\n");

  console.log("✨ Deployment complete!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
