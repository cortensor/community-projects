import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "@nomicfoundation/hardhat-ethers";
import "hardhat-gas-reporter";
import "solidity-coverage";
import * as dotenv from "dotenv";

dotenv.config();

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
      accounts: ["0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"],
    },
    base: {
      url: process.env.BLOCKCHAIN_RPC_URL || "https://mainnet.base.org",
      accounts: process.env.VALIDATOR_PRIVATE_KEY ? [process.env.VALIDATOR_PRIVATE_KEY] : [],
      chainId: 8453,
    },
    "base-sepolia": {
      url: "https://sepolia.base.org",
      accounts: process.env.VALIDATOR_PRIVATE_KEY ? [process.env.VALIDATOR_PRIVATE_KEY] : [],
      chainId: 84532,
    },
    arbitrum: {
      url: process.env.BLOCKCHAIN_RPC_URL || "https://arb1.arbitrum.io/rpc",
      accounts: process.env.VALIDATOR_PRIVATE_KEY ? [process.env.VALIDATOR_PRIVATE_KEY] : [],
      chainId: 42161,
    },
    "arbitrum-sepolia": {
      url: "https://sepolia-rollup.arbitrum.io/rpc",
      accounts: process.env.VALIDATOR_PRIVATE_KEY ? [process.env.VALIDATOR_PRIVATE_KEY] : [],
      chainId: 421614,
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
    exclude: ["node_modules"],
  },
  typechain: {
    outDir: "typechain-types",
    target: "ethers-v6",
  },
};

export default config;
